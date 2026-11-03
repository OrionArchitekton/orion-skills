"""Optional bounded local observations. No command or network execution."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import stat

MAX_INPUT = 65536
MAX_FILE = 1048576
MAX_PREMISES = 32


class Unavailable(Exception):
    """A fixed public-safe reason, never an OS exception message."""


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def path_parts(path, absolute=False):
    if not isinstance(path, str) or not path or len(path) > (4096 if absolute else 240):
        raise Unavailable('invalid_path')
    if absolute:
        if not path.startswith('/'):
            raise Unavailable('invalid_root')
        parts = path[1:].split('/') if path != '/' else []
    else:
        if not re.fullmatch(r'[A-Za-z0-9._/-]+', path):
            raise Unavailable('invalid_path')
        parts = path.split('/')
        if len(parts) > 16:
            raise Unavailable('invalid_path')
    if any(part in ('', '.', '..') for part in parts):
        raise Unavailable('invalid_path')
    return parts


def observe(root, relative, content=True, limit=MAX_FILE):
    """Walk held descriptors without following links; return bytes and metadata."""
    required = ('O_NOFOLLOW', 'O_DIRECTORY', 'O_NONBLOCK')
    if os.name != 'posix' or any(not hasattr(os, flag) for flag in required):
        raise Unavailable('unsupported_platform')
    root_parts = path_parts(root, absolute=True)
    parts = path_parts(relative)
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with ExitStack() as stack:
        directories = []

        def directory(name, parent=None, watch_changes=False):
            fd = os.open(name, flags | os.O_DIRECTORY, dir_fd=parent)
            stack.callback(os.close, fd)
            directories.append((fd, signature(os.fstat(fd)), parent, name, watch_changes))
            return fd

        def directories_stable():
            try:
                for fd, before, parent_fd, name, watch in directories:
                    current = signature(os.fstat(fd))
                    # Unrelated siblings in root ancestors do not invalidate a read.
                    if (current if watch else current[:3]) != (before if watch else before[:3]):
                        return False
                    if parent_fd is not None:
                        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                        if signature(named)[:3] != current[:3]:
                            return False
                return True
            except OSError:
                return False

        try:
            parent = directory('/')
            for part in root_parts:
                parent = directory(part, parent)
        except OSError:
            raise Unavailable('unavailable_root') from None
        root_info = os.fstat(parent)
        directories[-1] = (*directories[-1][:4], True)
        opened = False
        try:
            for part in parts[:-1]:
                parent = directory(part, parent, watch_changes=True)
            preliminary = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            if not stat.S_ISREG(preliminary.st_mode):
                raise Unavailable('nonregular_source')
            fd = os.open(parts[-1], flags, dir_fd=parent)
            stack.callback(os.close, fd)
            opened = True
            before = os.fstat(fd)
            if signature(preliminary) != signature(before):
                raise Unavailable('changed_during_read')
            if not stat.S_ISREG(before.st_mode):
                raise Unavailable('nonregular_source')
            data = b''
            if content:
                if before.st_size > limit:
                    raise Unavailable('source_too_large')
                chunks = []
                total = 0
                while total <= limit:
                    chunk = os.read(fd, min(65536, limit + 1 - total))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                if total > limit:
                    raise Unavailable('source_too_large')
                data = b''.join(chunks)
            after = os.fstat(fd)
            named = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            if (signature(before) != signature(after) or signature(after) != signature(named)
                    or not directories_stable()):
                raise Unavailable('changed_during_read')
            source = {'path_sha256': digest(relative.encode()),
                      'root_device': root_info.st_dev, 'root_inode': root_info.st_ino,
                      'device': after.st_dev, 'inode': after.st_ino,
                      'size': after.st_size, 'mtime_ns': after.st_mtime_ns,
                      'ctime_ns': after.st_ctime_ns}
            if content:
                source['sha256'] = digest(data)
            return data, source
        except FileNotFoundError:
            changed = opened or not directories_stable()
            raise Unavailable('changed_during_read' if changed else 'missing_source') from None
        except OSError:
            raise Unavailable('unavailable_source') from None


def public_id(premise):
    value = premise.get('id') if isinstance(premise, dict) else None
    return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value) else None


def unknown(reason, premise=None):
    stamp = now()
    return {'premise_id': public_id(premise), 'premise_sha256':
            digest(json.dumps(premise, sort_keys=True, separators=(',', ':')).encode()),
            'started_at': stamp, 'finished_at': stamp,
            'status': 'unknown', 'reason': reason, 'source': None}


def validate(premise):
    if (not isinstance(premise, dict) or set(premise) != {'id', 'claim', 'probe'}
            or public_id(premise) is None
            or not isinstance(premise['claim'], str) or not 1 <= len(premise['claim']) <= 1024):
        raise Unavailable('invalid_premise')
    probe = premise['probe']
    if not isinstance(probe, dict):
        raise Unavailable('unsupported_operation' if isinstance(probe, str) else 'invalid_probe')
    kind = probe.get('kind')
    if kind not in ('path_exists', 'file_contains', 'file_sha256'):
        raise Unavailable('unsupported_operation')
    keys = {'kind', 'path'} if kind == 'path_exists' else {'kind', 'path', 'expect'}
    if set(probe) != keys:
        raise Unavailable('invalid_probe')
    path_parts(probe['path'])
    if kind != 'path_exists':
        expected = probe['expect']
        if not isinstance(expected, str):
            raise Unavailable('invalid_expectation')
        if kind == 'file_sha256':
            if not re.fullmatch(r'[0-9a-f]{64}', expected):
                raise Unavailable('invalid_expectation')
        elif not 1 <= len(expected) <= 1024:
            raise Unavailable('invalid_expectation')
    return probe


def evaluate(premise, root):
    result = unknown('invalid_probe', premise)
    try:
        probe = validate(premise)
        data, source = observe(root, probe['path'], content=probe['kind'] != 'path_exists')
        if probe['kind'] == 'path_exists':
            matches = True
        elif probe['kind'] == 'file_sha256':
            matches = source['sha256'] == probe['expect']
        else:
            try:
                text = data.decode('utf-8')
            except UnicodeError:
                raise Unavailable('invalid_utf8') from None
            matches = probe['expect'] in text
        result.update(status='confirmed' if matches else 'drifted',
                      reason='matches' if matches else 'differs', source=source)
    except Unavailable as exc:
        reason = str(exc)
        result.update(status='missing' if reason == 'missing_source' else 'unknown', reason=reason)
    result['finished_at'] = now()
    return result


def summarize(results):
    counts = {status: sum(r['status'] == status for r in results)
              for status in ('confirmed', 'drifted', 'missing', 'unknown')}
    return {'schema_version': 1, 'all_confirmed': bool(results) and counts['confirmed'] == len(results),
            'counts': counts, 'results': results}


def report(document, root):
    try:
        if (len(json.dumps(document, ensure_ascii=False, separators=(',', ':')).encode('utf-8')) > MAX_INPUT or not isinstance(document, dict)
                or set(document) != {'schema_version', 'premises'}
                or type(document['schema_version']) is not int or document['schema_version'] != 1
                or not isinstance(document['premises'], list)
                or not 1 <= len(document['premises']) <= MAX_PREMISES):
            raise Unavailable('invalid_document')
        ids = [public_id(p) for p in document['premises'] if public_id(p) is not None]
        if len(set(ids)) != len(ids):
            raise Unavailable('duplicate_id')
        return summarize([evaluate(p, root) for p in document['premises']])
    except (ValueError, TypeError, RecursionError, UnicodeError):
        return summarize([unknown('invalid_document')])
    except Unavailable as exc:
        return summarize([unknown(str(exc))])


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_key')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError('invalid_constant')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--input', required=True)
    args = parser.parse_args(argv)
    try:
        # Preserve original components: abspath would erase symlink/.. evidence.
        absolute = args.input if args.input.startswith('/') else os.getcwd() + '/' + args.input
        data, _ = observe(os.path.dirname(absolute), os.path.basename(absolute), limit=MAX_INPUT)
        document = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object,
                              parse_constant=invalid_constant)
        output = report(document, args.root)
    except Unavailable as exc:
        output = summarize([unknown(str(exc))])
    except OSError:
        output = summarize([unknown('unavailable_input')])
    except (ValueError, RecursionError):
        output = summarize([unknown('invalid_document')])
    rendered = json.dumps(output, separators=(',', ':'))
    if len(rendered.encode()) > MAX_INPUT:
        output = summarize([unknown('output_limit')])
        rendered = json.dumps(output, separators=(',', ':'))
    print(rendered)
    return 0 if output['all_confirmed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
