#!/usr/bin/env python3
"""A small, byte-oriented implementation of GNU join's documented interface."""
import os
import re
import sys


class UsageError(Exception):
    pass


def ascii_fold(s):
    return s.lower()


def records(data, terminator):
    if not data:
        return []
    out = data.split(terminator)
    if data.endswith(terminator):
        out.pop()
    return out


def split_fields(line, sep, zero_terminated):
    if sep == b'':                 # -t '' -- the entire record is one field
        return [line]
    if sep is not None:
        return line.split(sep)
    whitespace = b' \t\n' if zero_terminated else b' \t'
    # GNU join's default fields are separated by one or more blanks and
    # leading blanks are ignored.  An all-blank record has no fields.
    return [x for x in re.split(b'[' + re.escape(whitespace) + b']+', line.lstrip(whitespace)) if x != b'']


def parse_field_number(value):
    if not value.isdigit() or int(value) <= 0:
        raise UsageError('invalid field number')
    return int(value) - 1


def parse_output_list(value):
    if value == 'auto':
        return 'auto'
    pieces = [x for x in re.split(r'[ ,]+', value) if x]
    if not pieces:
        raise UsageError('invalid field list')
    result = []
    for item in pieces:
        if item == '0':
            result.append((0, 0))
            continue
        m = re.fullmatch(r'([12])\.([0-9]+)', item)
        if not m or int(m.group(2)) == 0:
            raise UsageError('invalid field list')
        result.append((int(m.group(1)), int(m.group(2)) - 1))
    return result


def parse_args(argv):
    cfg = {
        'join1': 0, 'join2': 0, 'also': set(), 'only': set(),
        'empty': None, 'ignore_case': False, 'out': None,
        'sep': None, 'zero': False, 'header': False, 'check': None,
    }
    operands = []
    i = 0
    options = True
    value_options = {'-a', '-v', '-e', '-1', '-2', '-j', '-o', '-t'}
    while i < len(argv):
        arg = argv[i]
        if options and arg == '--':
            options = False
            i += 1
            continue
        if options and arg in value_options:
            if i + 1 >= len(argv):
                raise UsageError('missing option argument')
            val = argv[i + 1]
            i += 2
            if arg in ('-a', '-v'):
                if val not in ('1', '2'):
                    raise UsageError('invalid file number')
                cfg['also' if arg == '-a' else 'only'].add(int(val))
            elif arg == '-e':
                cfg['empty'] = os.fsencode(val)
            elif arg == '-1':
                cfg['join1'] = parse_field_number(val)
            elif arg == '-2':
                cfg['join2'] = parse_field_number(val)
            elif arg == '-j':
                n = parse_field_number(val)
                cfg['join1'] = cfg['join2'] = n
            elif arg == '-o':
                parsed = parse_output_list(val)
                if parsed == 'auto':
                    cfg['out'] = 'auto'
                elif cfg['out'] is None:
                    cfg['out'] = parsed
                elif cfg['out'] == 'auto':
                    raise UsageError('incompatible output formats')
                else:
                    cfg['out'].extend(parsed)
            elif arg == '-t':
                if val == '':
                    cfg['sep'] = b''
                elif val == r'\0':
                    cfg['sep'] = b'\0'
                else:
                    encoded = os.fsencode(val)
                    if len(encoded) != 1:
                        raise UsageError('separator must be one byte')
                    cfg['sep'] = encoded
            continue
        if options and arg in ('-i', '--ignore-case'):
            cfg['ignore_case'] = True
        elif options and arg in ('-z', '--zero-terminated'):
            cfg['zero'] = True
        elif options and arg == '--header':
            cfg['header'] = True
        elif options and arg == '--check-order':
            cfg['check'] = True
        elif options and arg == '--nocheck-order':
            cfg['check'] = False
        elif options and arg.startswith('-') and arg != '-':
            raise UsageError('unrecognized option')
        else:
            operands.append(arg)
        i += 1
    if len(operands) != 2 or operands.count('-') > 1:
        raise UsageError('two input files are required')
    cfg['files'] = operands
    return cfg


def read_file(name):
    if name == '-':
        return sys.stdin.buffer.read()
    with open(os.fsencode(name), 'rb') as f:
        return f.read()


def main(argv):
    try:
        cfg = parse_args(argv)
        term = b'\0' if cfg['zero'] else b'\n'
        raw1 = records(read_file(cfg['files'][0]), term)
        raw2 = records(read_file(cfg['files'][1]), term)
        rows1 = [split_fields(x, cfg['sep'], cfg['zero']) for x in raw1]
        rows2 = [split_fields(x, cfg['sep'], cfg['zero']) for x in raw2]

        # Auto is inferred from the first physical record, including headers.
        if cfg['out'] == 'auto':
            n1 = len(rows1[0]) if rows1 else 0
            n2 = len(rows2[0]) if rows2 else 0
            specs = [(0, 0)]
            specs += [(1, n) for n in range(n1) if n != cfg['join1']]
            specs += [(2, n) for n in range(n2) if n != cfg['join2']]
            cfg['out'] = specs

        header1 = header2 = None
        if cfg['header']:
            if rows1:
                header1, rows1 = rows1[0], rows1[1:]
            if rows2:
                header2, rows2 = rows2[0], rows2[1:]

        def field(row, n):
            return row[n] if row is not None and n < len(row) else b''

        def key(row, which):
            n = cfg['join1'] if which == 1 else cfg['join2']
            v = field(row, n)
            return ascii_fold(v) if cfg['ignore_case'] else v

        if cfg['check']:
            for which, rows in ((1, rows1), (2, rows2)):
                for a, b in zip(rows, rows[1:]):
                    if key(a, which) > key(b, which):
                        raise RuntimeError('input is not in sorted order')

        output_sep = b' ' if cfg['sep'] is None else cfg['sep']
        replacement = cfg['empty'] if cfg['empty'] is not None else b''
        chunks = []

        def emit(r1, r2, key_source=0):
            # key_source selects file 1 or 2 for unpaired/header mismatch keys.
            if cfg['out'] is not None:
                vals = []
                for source, n in cfg['out']:
                    if source == 0:
                        if key_source == 2:
                            present = r2 is not None and cfg['join2'] < len(r2)
                            value = field(r2, cfg['join2'])
                        else:
                            present = r1 is not None and cfg['join1'] < len(r1)
                            value = field(r1, cfg['join1'])
                            if not present and r2 is not None:
                                present = cfg['join2'] < len(r2)
                                value = field(r2, cfg['join2'])
                    elif source == 1:
                        present = r1 is not None and n < len(r1)
                        value = field(r1, n)
                    else:
                        present = r2 is not None and n < len(r2)
                        value = field(r2, n)
                    vals.append(value if present else replacement)
            elif r1 is not None and r2 is not None:
                vals = [field(r1, cfg['join1'])]
                vals += [v for n, v in enumerate(r1) if n != cfg['join1']]
                vals += [v for n, v in enumerate(r2) if n != cfg['join2']]
            else:
                row = r1 if r1 is not None else r2
                jn = cfg['join1'] if r1 is not None else cfg['join2']
                vals = [field(row, jn)] + [v for n, v in enumerate(row) if n != jn]
            chunks.append(output_sep.join(vals) + term)

        # Header records are paired unconditionally; file 1 supplies field 0.
        if cfg['header'] and (header1 is not None or header2 is not None):
            emit(header1, header2, 1 if header1 is not None else 2)

        print_pairs = not cfg['only']
        unpaired = cfg['also'] | cfg['only']
        i = j = 0
        while i < len(rows1) and j < len(rows2):
            k1, k2 = key(rows1[i], 1), key(rows2[j], 2)
            if k1 < k2:
                if 1 in unpaired:
                    emit(rows1[i], None, 1)
                i += 1
            elif k1 > k2:
                if 2 in unpaired:
                    emit(None, rows2[j], 2)
                j += 1
            else:
                i2, j2 = i + 1, j + 1
                while i2 < len(rows1) and key(rows1[i2], 1) == k1:
                    i2 += 1
                while j2 < len(rows2) and key(rows2[j2], 2) == k2:
                    j2 += 1
                if print_pairs:
                    for a in rows1[i:i2]:
                        for b in rows2[j:j2]:
                            emit(a, b, 1)
                i, j = i2, j2
        if 1 in unpaired:
            for row in rows1[i:]:
                emit(row, None, 1)
        if 2 in unpaired:
            for row in rows2[j:]:
                emit(None, row, 2)
        sys.stdout.buffer.write(b''.join(chunks))
        return 0
    except (UsageError, OSError, RuntimeError) as e:
        sys.stderr.write('join: ' + str(e) + '\n')
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
