#!/usr/bin/env python3
"""
Generate index.md pages for the bld/stl directory tree.

Per-directory pages: one per leaf directory (size+head combination),
with a table of pitch columns × length rows, each cell a direct download
link to the raw STL file.

Master index: bld/stl/index.md with bolt/screw tables (rows=sizes,
cols=heads) and nut sections linking to per-directory pages.
The master index uses GitHub-Flavored Markdown and can be pasted into
a Thingiverse thing description.

All links use full URLs when --base-url is given.

For GitHub hosting, supply the GitHub blob URL of the stl/ directory:
  --base-url https://github.com/username/reponame/blob/branch/bld/stl

STL download links automatically switch to raw.githubusercontent.com so
they trigger a file download rather than showing the GitHub viewer.
Index page links keep the github.com/blob URL so they render as Markdown.
"""

import os
import re
from pathlib import Path
from fractions import Fraction

BLD_STL = Path(__file__).parent / 'stl'


# ── URL helpers ───────────────────────────────────────────────────────────────

def _split_urls(base_url):
    """
    Return (blob_base, raw_base) from a single base_url.

    If base_url looks like a GitHub blob URL, derive the raw URL from it.
    Otherwise use base_url for both (works for local/other hosts).
    """
    b = base_url.rstrip('/')
    if 'github.com' in b and '/blob/' in b:
        r = b.replace('github.com', 'raw.githubusercontent.com')
        r = r.replace('/blob/', '/')
        return b, r
    return b, b


# ── filename decode helpers (same logic as gen_html.py) ──────────────────────

def _length_to_float(s):
    if s.startswith('def'):
        s = s[3:]
    s = s.replace('p', '.').replace('f', '/').replace('_', ' ').strip()
    parts = s.split()
    try:
        if len(parts) == 1:
            return float(Fraction(parts[0]))
        return float(parts[0]) + float(Fraction(parts[1]))
    except Exception:
        return 0.0


def _pitch_to_float(s):
    return float(s.replace('p', '.'))


def _decode_size(s):
    """7f16 → 7/16, M3 → M3, #10 → #10."""
    return re.sub(r'(\d)f(\d)', r'\1/\2', s)


def _file_label(parsed, is_nut):
    """SizeXpitch[-length] with encoding reversed."""
    size      = parsed['size']
    pitch_str = parsed['pitch_str']
    length_str = parsed['length_str']
    raw = f"{size}X{pitch_str}" if is_nut else f"{size}X{pitch_str}-{length_str}"
    return raw.replace('p', '.').replace('f', '/').replace('_', ' ')


def _decode_pitch(s, am_metric):
    decoded = s.replace('p', '.')
    return f"{decoded} mm" if am_metric else f"{decoded} TPI"


def _decode_length(s, am_metric):
    is_default = s.startswith('def')
    if is_default:
        s = s[3:]
    decoded = s.replace('p', '.').replace('f', '/').replace('_', ' ').strip()
    suffix = ' mm' if am_metric else '"'
    label = f"{decoded}{suffix}"
    if is_default:
        label += ' (default)'
    return label


_NUMBER_DIAM_IN = {
    '#5': 0.1250, '#6': 0.1380, '#8': 0.1640,
    '#10': 0.1900, '#12': 0.2160,
}


def _size_sort_key(size_str, am_metric):
    s = _decode_size(size_str)
    if s.startswith('M'):
        try:
            return float(s[1:])
        except Exception:
            pass
    if s in _NUMBER_DIAM_IN:
        return _NUMBER_DIAM_IN[s]
    try:
        return float(Fraction(s))
    except Exception:
        return 0.0


def _parse_stl(fname):
    """
    Parse filenames like:
      mm_cap_bolt_M3X0p35-15.stl
      in_cap_bolt_#10X24-1_1f4.stl
      mm_nut_M3X0p35-def2p40.stl

    Returns dict or None.
    """
    if not fname.endswith('.stl'):
        return None
    base = fname[:-4]
    try:
        x = base.index('X')
    except ValueError:
        return None
    left, right = base[:x], base[x + 1:]
    try:
        dash = right.index('-')
    except ValueError:
        return None
    pitch_str  = right[:dash]
    length_str = right[dash + 1:]
    parts = left.split('_')
    if len(parts) < 2:
        return None
    unit   = parts[0]
    size   = parts[-1]
    middle = parts[1:-1]
    return dict(unit=unit, middle=middle, size=size,
                pitch_str=pitch_str, length_str=length_str, fname=fname)


# ── Markdown table helpers ────────────────────────────────────────────────────

def _md_table(headers, rows):
    """Return lines for a GFM table."""
    lines = []
    lines.append('| ' + ' | '.join(headers) + ' |')
    lines.append('|' + '---|' * len(headers))
    for row in rows:
        lines.append('| ' + ' | '.join(str(c) for c in row) + ' |')
    return lines


# ── per-directory index ───────────────────────────────────────────────────────

def gen_dir_index(dirpath, base_url='', use_raw=False):
    """Write index.md (blob links) or index_raw.md (raw links) for one leaf directory."""
    dirpath = Path(dirpath)
    stl_files = [f for f in os.listdir(dirpath) if f.endswith('.stl')]
    if not stl_files:
        return

    parsed = [p for f in stl_files if (p := _parse_stl(f)) is not None]
    if not parsed:
        return

    am_metric  = parsed[0]['unit'] == 'mm'
    size_raw   = parsed[0]['size']
    size_disp  = _decode_size(size_raw)
    middle     = parsed[0]['middle']

    if middle == ['nut']:
        title = f"{size_disp} Nut"
    elif middle in (['srod'], ['rod']):
        title = f"{size_disp} Threaded Rod"
    else:
        title = f"{size_disp} {' '.join(m.capitalize() for m in middle)}"

    is_nut  = middle == ['nut']
    pitches = sorted({p['pitch_str'] for p in parsed}, key=_pitch_to_float)
    lengths = sorted({p['length_str'] for p in parsed}, key=_length_to_float)
    cell    = {(p['pitch_str'], p['length_str']): (p['fname'], _file_label(p, is_nut))
               for p in parsed}

    blob_base, raw_base = _split_urls(base_url)
    stl_base = raw_base if use_raw else blob_base
    rel_dir  = dirpath.relative_to(BLD_STL)   # e.g. mm/bolt/hex/M6

    def stl_url(fname):
        if stl_base:
            return f"{stl_base}/{rel_dir}/{fname}"
        return fname    # relative fallback (local use only)

    headers = ['Length \\ Pitch'] + [_decode_pitch(p, am_metric) for p in pitches]
    rows = []
    for ls in lengths:
        length_label = _decode_length(ls, am_metric)
        row = [f'**{length_label}**']
        for ps in pitches:
            entry = cell.get((ps, ls))
            if entry:
                fn, link_text = entry
                row.append(f'[{link_text}]({stl_url(fn)})')
            else:
                row.append('—')
        rows.append(row)

    index_name = 'index_raw.md' if use_raw else 'index.md'
    subtitle = '## Direct download' if use_raw else '## Preview and download'
    lines = [f'# {title}', '', subtitle, ''] + _md_table(headers, rows) + ['']
    out = dirpath / index_name
    out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'  {out.relative_to(BLD_STL.parent)}')


# ── master index ──────────────────────────────────────────────────────────────

def gen_master_index(base_url='', use_raw=False):
    """
    Write bld/stl/index.md.

    Links to leaf pages point to index.md (blob mode) or index_raw.md (raw mode).
    The master index itself is always written as index.md.
    The output is also suitable for pasting into a Thingiverse description.
    """
    blob_base, raw_base = _split_urls(base_url)
    # Master index page links always use blob URLs so they render on GitHub.
    # The leaf filename varies with use_raw.
    page_base  = blob_base
    index_name = 'index_raw.md' if use_raw else 'index.md'

    def page_url(rel):
        return f"{page_base}/{rel}" if page_base else rel

    subtitle = '## Direct download' if use_raw else '## Preview and download'
    parts = ['# STL Download Index', '', subtitle, '']

    for unit in ['mm', 'in']:
        am_metric  = unit == 'mm'
        unit_label = 'Metric' if am_metric else 'Imperial'

        # ── Bolts and Screws ──────────────────────────────────────────────
        for btype in ['bolt', 'screw']:
            type_dir = BLD_STL / unit / btype
            if not type_dir.is_dir():
                continue

            heads = sorted(d.name for d in type_dir.iterdir() if d.is_dir())
            all_sizes: set[str] = set()
            for head in heads:
                for sd in (type_dir / head).iterdir():
                    if sd.is_dir():
                        all_sizes.add(sd.name)
            sizes = sorted(all_sizes, key=lambda s: _size_sort_key(s, am_metric))

            parts.append(f'## {unit_label} {btype.capitalize()}s')
            parts.append('')

            headers = ['Size'] + [h.capitalize() for h in heads]
            rows = []
            for size in sizes:
                size_disp = _decode_size(size)
                row = [f'**{size_disp}**']
                for head in heads:
                    idx = BLD_STL / unit / btype / head / size / index_name
                    if idx.exists():
                        rel = f"{unit}/{btype}/{head}/{size}/{index_name}"
                        row.append(f'[{size_disp}]({page_url(rel)})')
                    else:
                        row.append('—')
                rows.append(row)

            parts += _md_table(headers, rows)
            parts.append('')

        # ── Nuts ──────────────────────────────────────────────────────────
        nut_dir = BLD_STL / unit / 'nut'
        if nut_dir.is_dir():
            sizes = sorted(
                [d.name for d in nut_dir.iterdir() if d.is_dir()],
                key=lambda s: _size_sort_key(s, am_metric)
            )
            parts.append(f'## {unit_label} Nuts')
            parts.append('')

            headers = [_decode_size(s) for s in sizes]
            row = []
            for s in sizes:
                idx = nut_dir / s / index_name
                size_disp = _decode_size(s)
                if idx.exists():
                    rel = f"{unit}/nut/{s}/{index_name}"
                    row.append(f'[{size_disp}]({page_url(rel)})')
                else:
                    row.append(size_disp)
            parts += _md_table(headers, [row])
            parts.append('')

    out = BLD_STL / index_name
    out.write_text('\n'.join(parts), encoding='utf-8')
    label = f'with base URL: {base_url}' if base_url else '(relative links)'
    print(f'Master index {label}: {out.relative_to(BLD_STL.parent)}')


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Generate index.md pages for the bld/stl tree.'
    )
    parser.add_argument(
        '--base-url', default='',
        metavar='URL',
        help=(
            'Base URL for all links in generated pages.\n'
            'Supply the GitHub blob URL of the stl/ directory, e.g.:\n'
            '  https://github.com/username/reponame/blob/branch/bld/stl\n'
            'STL download links will automatically use raw.githubusercontent.com.\n'
            'Without this flag, relative links are used (local testing only).'
        )
    )
    parser.add_argument(
        '--raw', action='store_true',
        help=(
            'Generate index_raw.md files with raw.githubusercontent.com download\n'
            'links (triggers direct file download). Default generates index.md\n'
            'files with github.com/blob/ links (shows GitHub viewer/preview).'
        )
    )
    parser.add_argument(
        '--master-only', action='store_true',
        help='Regenerate only the master index, skip per-directory pages.'
    )
    args = parser.parse_args()

    if not args.master_only:
        print(f'Walking {BLD_STL} ...')
        for root, dirs, files in os.walk(BLD_STL):
            if any(f.endswith('.stl') for f in files):
                gen_dir_index(root, args.base_url, use_raw=args.raw)

    gen_master_index(base_url=args.base_url, use_raw=args.raw)
    print('Done.')


if __name__ == '__main__':
    main()
