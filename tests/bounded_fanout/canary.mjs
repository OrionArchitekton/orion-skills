// Test-only disabled control: same capture, replace only inline selection.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { BoundContext, recoverResults } from '../../skills/author-workflow-fanout/bounded-results.mjs';

export function runCanary(directory, disabled = false) {
  const budgetBytes = 900;
  const ctx = new BoundContext({ directory, budgetBytes, itemCapBytes: 200 });
  const input = Array.from({ length: 150 }, (_, i) => i < 8 ? `large-${i}雪🙂`.repeat(400) : `tiny-${i}`);
  for (const value of input) ctx.add('duplicate label', value);
  const saved = [...recoverResults(ctx.recovery, ctx.count)];
  assert.deepEqual(saved.map(r => r.content), input);
  const view = JSON.parse(ctx.snapshot());
  if (disabled) view.items = saved.map(r => ({ id: r.id, label: r.label, text: r.content }));
  const inlineBytes = Buffer.byteLength(JSON.stringify(view));
  return { disabled, budgetBytes, inlineBytes, recovered: saved.length, pass: inlineBytes <= budgetBytes };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'bounded-canary-'));
  try {
    const proof = runCanary(directory, process.argv.includes('--disabled'));
    console.log(JSON.stringify(proof));
    process.exitCode = proof.pass ? 0 : 1;
  } finally { fs.rmSync(directory, { recursive: true, force: true }); }
}
