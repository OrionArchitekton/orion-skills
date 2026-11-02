import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { BoundContext, recoverResults } from '../../skills/author-workflow-fanout/bounded-results.mjs';

function destination(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'bounded-results-test-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}

test('accepted small, large and multibyte results recover exactly after discard', t => {
  const ctx = new BoundContext({ directory: destination(t), budgetBytes: 800, itemCapBytes: 200 });
  const input = ['', 'small\n', '雪🙂é'.repeat(500), '\\"\n\t'.repeat(80)];
  for (const content of input) ctx.add('../same-label', content);
  const view = JSON.parse(ctx.snapshot());
  const recovered = [...recoverResults(view.recovery, view.count)];
  assert.deepEqual(recovered.map(r => r.content), input);
  assert.deepEqual(recovered.map(r => r.label), input.map(() => '../same-label'));
  assert.equal(new Set(recovered.map(r => r.id)).size, input.length);
  assert.equal(view.count, input.length);
  assert.ok(Buffer.byteLength(ctx.snapshot()) <= 800);
  for (const item of view.items) assert.ok(Buffer.byteLength(JSON.stringify(item)) <= 200);
});

test('UTF-8 BOM and Unicode normalization are preserved byte for byte', t => {
  const ctx = new BoundContext({ directory: destination(t), budgetBytes: 800, itemCapBytes: 200 });
  const input = ['\uFEFFleading BOM', 'e\u0301', 'é', '\0\r\n', '🙂雪'];
  for (const text of input) ctx.add('same', text);
  assert.deepEqual([...recoverResults(ctx.recovery, ctx.count)].map(r => r.content), input);
});

test('recovery rejects missing, corrupted, partial, escaping and symlinked artifacts', t => {
  const make = () => {
    const ctx = new BoundContext({ directory: destination(t), budgetBytes: 800, itemCapBytes: 200 });
    ctx.add('one', 'first'); ctx.add('two', 'second');
    return ctx;
  };
  for (const attack of ['missing', 'corrupt', 'partial', 'escape', 'symlink', 'journal-symlink', 'invalid-utf8']) {
    const ctx = make();
    const file = path.join(ctx.recovery, '1.utf8');
    const journal = path.join(ctx.recovery, 'results.jsonl');
    if (attack === 'missing') fs.unlinkSync(file);
    if (attack === 'corrupt') fs.writeFileSync(file, 'wrong');
    if (attack === 'partial') fs.appendFileSync(journal, '{');
    if (attack === 'escape') fs.writeFileSync(journal, fs.readFileSync(journal, 'utf8').replace('"id":"1"', '"id":"../outside"'));
    if (attack === 'symlink') { fs.unlinkSync(file); fs.symlinkSync(path.join(ctx.recovery, '2.utf8'), file); }
    if (attack === 'journal-symlink') { fs.unlinkSync(journal); fs.symlinkSync(file, journal); }
    if (attack === 'invalid-utf8') fs.writeFileSync(journal, Buffer.from([255, 10]));
    assert.throws(() => [...recoverResults(ctx.recovery, ctx.count)], undefined, attack);
  }
});

test('invalid budgets, Unicode and destinations fail explicitly', t => {
  const directory = destination(t);
  for (const value of [undefined, null, 0, -1, 1.5, NaN, Infinity, '800', Number.MAX_SAFE_INTEGER + 1]) {
    assert.throws(() => new BoundContext({ directory, budgetBytes: value, itemCapBytes: 100 }));
    assert.throws(() => new BoundContext({ directory, budgetBytes: 800, itemCapBytes: value }));
  }
  assert.throws(() => new BoundContext({ directory, budgetBytes: 1, itemCapBytes: 10 }), /envelope/);
  const ctx = new BoundContext({ directory, budgetBytes: 800, itemCapBytes: 200 });
  for (const bad of [null, {}, 12, '\uD800', '\uDC00']) {
    assert.throws(() => ctx.add('label', bad), /Unicode/);
    assert.throws(() => ctx.add(bad, 'content'), /Unicode/);
  }
  assert.equal(JSON.parse(ctx.snapshot()).count, 0);
  const link = path.join(directory, 'link');
  fs.symlinkSync(ctx.recovery, link);
  assert.throws(() => new BoundContext({ directory: link, budgetBytes: 800, itemCapBytes: 200 }));
});

test('every persistence stage fails closed and poisons the accumulator', t => {
  for (const stage of ['write', 'readback', 'sync', 'journal']) {
    const ctx = new BoundContext({ directory: destination(t), budgetBytes: 800, itemCapBytes: 200 });
    ctx.add('accepted', 'keep this');
    const method = stage === 'readback' ? 'readFileSync' : stage === 'sync' ? 'fsyncSync' : 'writeFileSync';
    const original = fs[method];
    let calls = 0;
    const mock = t.mock.method(fs, method, function (...args) {
      calls++;
      if (stage !== 'journal' || calls === 2) throw Object.assign(new Error('synthetic disk failure'), { code: 'ENOSPC' });
      return original.apply(fs, args);
    });
    assert.throws(() => ctx.add('must fail', 'large output'.repeat(1000)), /persistence failed/);
    mock.mock.restore();
    assert.throws(() => ctx.snapshot(), /unavailable/);
    assert.throws(() => ctx.add('retry', 'no'), /persistence failed/);
    assert.deepEqual([...recoverResults(ctx.recovery, ctx.count)].map(r => r.content), ['keep this']);
  }
});

test('a silent partial journal write cannot report successful capture', t => {
  const ctx = new BoundContext({ directory: destination(t), budgetBytes: 800, itemCapBytes: 200 });
  const original = fs.writeFileSync;
  let calls = 0;
  const mock = t.mock.method(fs, 'writeFileSync', function (fd, data, ...args) {
    calls++;
    return original.call(fs, fd, calls === 2 ? String(data).slice(0, 5) : data, ...args);
  });
  assert.throws(() => ctx.add('synthetic', 'exact output'), /persistence failed/);
  mock.mock.restore();
  assert.throws(() => ctx.snapshot(), /unavailable/);
  assert.throws(() => [...recoverResults(ctx.recovery, ctx.count)], /partial/);
});

import { spawn } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { runCanary } from './canary.mjs';

test('disabled-control canary overruns, enabled fits, and both retain all results', t => {
  const disabled = runCanary(destination(t), true);
  const enabled = runCanary(destination(t));
  assert.equal(disabled.pass, false);
  assert.equal(enabled.pass, true);
  assert.ok(disabled.inlineBytes > disabled.budgetBytes);
  assert.ok(enabled.inlineBytes < disabled.inlineBytes);
  assert.equal(enabled.recovered, disabled.recovered);
  assert.equal(enabled.recovered, 150);
});

test('a tiny-result flood fits the entire envelope at every addition', t => {
  const ctx = new BoundContext({ directory: destination(t), budgetBytes: 500, itemCapBytes: 100 });
  for (let i = 0; i < 1200; i++) {
    ctx.add('duplicate label', `tiny-${i}`);
    const snapshot = ctx.snapshot();
    assert.equal(ctx.retainedBytes, Buffer.byteLength(snapshot));
    assert.ok(ctx.retainedBytes <= 500);
    for (const item of JSON.parse(snapshot).items) assert.ok(Buffer.byteLength(JSON.stringify(item)) <= 100);
  }
  const recovered = [...recoverResults(ctx.recovery, ctx.count)];
  assert.equal(recovered.length, 1200);
  assert.deepEqual(recovered.map(r => r.content), Array.from({ length: 1200 }, (_, i) => `tiny-${i}`));
  if (process.platform !== 'win32') {
    assert.equal(fs.statSync(ctx.recovery).mode & 0o777, 0o700);
    for (const file of fs.readdirSync(ctx.recovery)) assert.equal(fs.statSync(path.join(ctx.recovery, file)).mode & 0o777, 0o600);
  }
});

test('exact aggregate and per-item JSON byte boundaries include escaping and labels', t => {
  const directory = destination(t);
  const sample = new BoundContext({ directory, budgetBytes: 8000, itemCapBytes: 8000 });
  const label = '雪\\"'; const content = '\n🙂'.repeat(80);
  sample.add(label, content);
  const itemBytes = Buffer.byteLength(JSON.stringify(JSON.parse(sample.snapshot()).items[0]));
  const totalBytes = Buffer.byteLength(sample.snapshot());
  for (const [budgetBytes, itemCapBytes, kept] of [
    [totalBytes, itemBytes, true], [totalBytes - 1, itemBytes, false],
    [8000, itemBytes - 1, false], [8000, itemBytes, true],
  ]) {
    const ctx = new BoundContext({ directory, budgetBytes, itemCapBytes });
    ctx.add(label, content);
    assert.equal(JSON.parse(ctx.snapshot()).items.length, kept ? 1 : 0);
    assert.ok(Buffer.byteLength(ctx.snapshot()) <= budgetBytes);
    assert.deepEqual([...recoverResults(ctx.recovery, ctx.count)].map(r => r.content), [content]);
  }
});

test('independent concurrent processes cannot collide on duplicate labels', async t => {
  const directory = destination(t);
  const moduleURL = new URL('../../skills/author-workflow-fanout/bounded-results.mjs', import.meta.url).href;
  const paths = await Promise.all(Array.from({ length: 6 }, (_, index) => new Promise((resolve, reject) => {
    const code = `import {BoundContext} from ${JSON.stringify(moduleURL)};
      const ctx = new BoundContext({directory:process.argv[1],budgetBytes:800,itemCapBytes:200});
      for(let i=0;i<12;i++)ctx.add('../same',process.argv[2]+':'+i);
      console.log(ctx.recovery);`;
    const child = spawn(process.execPath, ['--input-type=module', '-e', code, directory, String(index)], {
      env: { PATH: process.env.PATH, HOME: directory, TMPDIR: directory, LC_ALL: 'C.UTF-8' },
    });
    let stdout = '', stderr = '';
    child.stdout.on('data', data => { stdout += data; });
    child.stderr.on('data', data => { stderr += data; });
    child.on('error', reject);
    child.on('close', code => code === 0 ? resolve(stdout.trim()) : reject(new Error(stderr)));
  })));
  assert.equal(new Set(paths).size, 6);
  paths.forEach((recovery, index) => {
    assert.equal(path.dirname(recovery), directory);
    assert.deepEqual([...recoverResults(recovery, 12)].map(r => r.content), Array.from({ length: 12 }, (_, i) => `${index}:${i}`));
  });
});

test('a standalone skill copy needs no repository files or installed dependencies', async t => {
  const root = destination(t);
  const copy = path.join(root, 'skill');
  fs.cpSync(new URL('../../skills/author-workflow-fanout/', import.meta.url), copy, { recursive: true });
  const standalone = await import(pathToFileURL(path.join(copy, 'bounded-results.mjs')).href);
  const ctx = new standalone.BoundContext({ directory: root, budgetBytes: 800, itemCapBytes: 100 });
  ctx.add('original', '雪'.repeat(1000));
  assert.deepEqual([...standalone.recoverResults(ctx.recovery, ctx.count)].map(r => r.content), ['雪'.repeat(1000)]);
  assert.match(fs.readFileSync(path.join(copy, 'LICENSE'), 'utf8'), /MIT License/);
});

test('recovery requires the accepted count and detects whole-record journal loss', t => {
  for (const keep of [0, 1]) {
    const ctx = new BoundContext({ directory: destination(t), budgetBytes: 800, itemCapBytes: 200 });
    ctx.add('one', 'first'); ctx.add('two', 'second');
    const view = JSON.parse(ctx.snapshot());
    const journal = path.join(view.recovery, 'results.jsonl');
    const lines = fs.readFileSync(journal, 'utf8').split('\n');
    fs.writeFileSync(journal, keep ? `${lines[0]}\n` : '');
    assert.throws(() => [...recoverResults(view.recovery, view.count)], /count/);
  }
});

test('missing, invalid and stale recovery counts fail before yielding', t => {
  const ctx = new BoundContext({ directory: destination(t), budgetBytes: 800, itemCapBytes: 200 });
  assert.deepEqual([...recoverResults(ctx.recovery, 0)], []);
  ctx.add('one', 'first');
  const before = JSON.parse(ctx.snapshot());
  ctx.add('two', 'second');
  for (const count of [undefined, null, -1, 1.5, '2', Infinity, Number.MAX_SAFE_INTEGER + 1]) {
    assert.throws(() => [...recoverResults(ctx.recovery, count)], /expectedCount/);
  }
  assert.throws(() => [...recoverResults(before.recovery, before.count)], /count mismatch/);
  assert.deepEqual([...recoverResults(ctx.recovery, ctx.count)].map(r => r.content), ['first', 'second']);
});
