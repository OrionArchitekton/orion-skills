// Copyright (c) 2026 Dan Mercede. MIT; see LICENSE in this directory.
// Node.js local-filesystem helper. No Workflow sandbox or provider integration.
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';

const bytes = text => Buffer.byteLength(text, 'utf8');
const digest = data => createHash('sha256').update(data).digest('hex');
const journalName = 'results.jsonl';

function positiveInteger(value, name) {
  if (!Number.isSafeInteger(value) || value <= 0) throw new TypeError(`${name} must be a positive safe integer`);
}
function unicode(value, name) {
  if (typeof value !== 'string' || !value.isWellFormed()) throw new TypeError(`${name} must be a well-formed Unicode string`);
}
function directoryAt(directory) {
  if (typeof directory !== 'string' || !directory) throw new TypeError('directory is required');
  const resolved = path.resolve(directory);
  if (!fs.lstatSync(resolved).isDirectory()) throw new Error('directory must be a real directory, not a symlink');
  return resolved;
}
function readRegular(filename) {
  const fd = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  try {
    if (!fs.fstatSync(fd).isFile()) throw new Error('artifact must be a regular file');
    return fs.readFileSync(fd);
  } finally { fs.closeSync(fd); }
}
function writeSynced(filename, data, append = false) {
  const flags = fs.constants.O_RDWR | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK |
    (append ? fs.constants.O_APPEND : fs.constants.O_CREAT | fs.constants.O_EXCL);
  const fd = fs.openSync(filename, flags, 0o600);
  try {
    if (!fs.fstatSync(fd).isFile()) throw new Error('artifact must be a regular file');
    const start = fs.fstatSync(fd).size;
    const expected = Buffer.from(data);
    fs.writeFileSync(fd, expected);
    fs.fsyncSync(fd);
    const actual = Buffer.alloc(expected.length);
    if (fs.fstatSync(fd).size !== start + expected.length ||
        fs.readSync(fd, actual, 0, actual.length, start) !== expected.length ||
        !actual.equals(expected)) throw new Error('persistence write verification failed');
  } finally { fs.closeSync(fd); }
}

export class BoundContext {
  #directory; #budget; #itemCap; #items = []; #count = 0; #failed = false;

  constructor({ directory, budgetBytes, itemCapBytes } = {}) {
    positiveInteger(budgetBytes, 'budgetBytes');
    positiveInteger(itemCapBytes, 'itemCapBytes');
    const parent = directoryAt(directory);
    this.#budget = budgetBytes;
    this.#itemCap = itemCapBytes;
    // mkdtemp makes independent runs exclusive; labels never affect paths.
    this.#directory = fs.mkdtempSync(path.join(parent, 'bounded-'));
    fs.chmodSync(this.#directory, 0o700);
    if (bytes(this.#serialize([], Number.MAX_SAFE_INTEGER)) > budgetBytes) {
      throw new RangeError('budgetBytes cannot fit the recovery envelope and maximum count');
    }
    writeSynced(path.join(this.#directory, journalName), '');
  }

  #serialize(items = this.#items, count = this.#count) {
    return JSON.stringify({ version: 1, recovery: this.#directory, count, items });
  }

  add(label, content) {
    if (this.#failed) throw new Error('persistence failed; preserve this run and start a new accumulator');
    unicode(label, 'label');
    unicode(content, 'content');
    if (this.#count === Number.MAX_SAFE_INTEGER) throw new RangeError('result count exhausted');
    const id = String(this.#count + 1);
    const data = Buffer.from(content, 'utf8');
    const record = { id, label, bytes: data.length, sha256: digest(data) };
    try {
      const filename = path.join(this.#directory, `${id}.utf8`);
      writeSynced(filename, data);
      const retained = readRegular(filename);
      if (retained.length !== record.bytes || digest(retained) !== record.sha256) throw new Error('persistence readback mismatch');
      writeSynced(path.join(this.#directory, journalName), `${JSON.stringify(record)}\n`, true);
    } catch (error) {
      this.#failed = true;
      throw new Error('result persistence failed; no bounded success is available', { cause: error });
    }
    this.#count++;
    const item = { id, label, text: content };
    if (bytes(JSON.stringify(item)) <= this.#itemCap) this.#items.push(item);
    while (bytes(this.#serialize()) > this.#budget) this.#items.shift();
    // Return no per-add snapshot: accumulating those would bypass the total cap.
  }

  snapshot() {
    if (this.#failed) throw new Error('persistence failed; snapshot unavailable');
    return this.#serialize();
  }
  get count() { return this.#count; }
  get recovery() { return this.#directory; }
  get retainedBytes() { return bytes(this.snapshot()); }
}

// Offline audit/recovery, deliberately separate from the bounded inline snapshot.
// Iterate results; do not return this unbounded audit stream into agent context.
export function* recoverResults(recovery, expectedCount) {
  if (!Number.isSafeInteger(expectedCount) || expectedCount < 0) throw new TypeError('expectedCount must be a nonnegative safe integer from the snapshot');
  const directory = directoryAt(recovery);
  const raw = readRegular(path.join(directory, journalName));
  const text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(raw);
  if (text && !text.endsWith('\n')) throw new Error('partial recovery journal');
  const lines = text ? text.slice(0, -1).split('\n') : [];
  if (lines.length !== expectedCount) throw new Error('recovery count mismatch');
  for (let index = 0; index < lines.length; index++) {
    const record = JSON.parse(lines[index]);
    if (!record || record.id !== String(index + 1) || typeof record.label !== 'string' ||
        !record.label.isWellFormed() || !Number.isSafeInteger(record.bytes) || record.bytes < 0 ||
        typeof record.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(record.sha256)) {
      throw new Error('invalid recovery record');
    }
    const data = readRegular(path.join(directory, `${record.id}.utf8`));
    if (data.length !== record.bytes || digest(data) !== record.sha256) throw new Error('recovery integrity mismatch');
    const content = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(data);
    yield { id: record.id, label: record.label, bytes: record.bytes, sha256: record.sha256, content };
  }
}
