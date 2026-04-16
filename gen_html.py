#!/usr/bin/env python3
"""
Generate index.html pages for the bld/stl directory tree.

Per-directory pages: one per leaf directory (size+head combination),
with a table of pitch columns × length rows, each cell a download link.

Master index: bld/stl/index.html with bolt/screw tables (rows=sizes,
cols=heads) and nut sections linking to per-directory pages.
"""

import os
from pathlib import Path
from fractions import Fraction

BLD_STL = Path(__file__).parent / 'stl'


# ── filename decode helpers ───────────────────────────────────────────────────

def _length_to_float(s):
    """Convert encoded length string to float for sorting."""
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
    """7f16 → 7/16, 1f4 → 1/4, M3 → M3, #10 → #10."""
    # Only replace 'f' that is between digits (fraction encoding)
    import re
    return re.sub(r'(\d)f(\d)', r'\1/\2', s)


def _file_label(parsed, is_nut):
    """
    Human-readable label from parsed filename parts:
      size X pitch - length   (e.g. M6X1-25, #10X24-1 1/4)
    For nuts, the length is omitted: M6X1
    Encoding: p→., f→/, _→space  (all safe in this portion of the filename)
    """
    size = parsed['size']
    pitch_str = parsed['pitch_str']
    length_str = parsed['length_str']
    raw = f"{size}X{pitch_str}" if is_nut else f"{size}X{pitch_str}-{length_str}"
    return raw.replace('p', '.').replace('f', '/').replace('_', ' ')


def _decode_pitch(s, am_metric):
    decoded = s.replace('p', '.')
    return f"{decoded} mm" if am_metric else f"{decoded} TPI"


def _decode_length(s, am_metric):
    """Return human-readable length with units."""
    is_default = s.startswith('def')
    if is_default:
        s = s[3:]
    decoded = s.replace('p', '.').replace('f', '/').replace('_', ' ').strip()
    suffix = ' mm' if am_metric else '"'
    label = f"{decoded}{suffix}"
    if is_default:
        label += ' (default)'
    return label


# Actual diameters (inches) for imperial number-size screws, for correct sorting
_NUMBER_DIAM_IN = {
    '#5': 0.1250, '#6': 0.1380, '#8': 0.1640,
    '#10': 0.1900, '#12': 0.2160,
}


def _size_sort_key(size_str, am_metric):
    """Numeric sort key for size directory names."""
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
      mm_srod_M3X0p35-20.stl     (bolt/rod directory)
      mm_rod_M3X0p35-10.stl      (screw/rod directory)

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
    pitch_str = right[:dash]
    length_str = right[dash + 1:]
    parts = left.split('_')
    if len(parts) < 2:
        return None
    unit = parts[0]
    size = parts[-1]
    middle = parts[1:-1]  # e.g. ['cap','bolt'], ['nut'], ['srod'], ['rod']
    return dict(unit=unit, middle=middle, size=size,
                pitch_str=pitch_str, length_str=length_str, fname=fname)


# ── CSS / HTML template ───────────────────────────────────────────────────────

_CSS = """
body { font-family: sans-serif; margin: 2em; color: #222; }
h1   { color: #333; }
h2   { color: #555; margin-top: 2em; }
table { border-collapse: collapse; margin: 1em 0 2em 0; }
th, td { border: 1px solid #ccc; padding: 6px 14px; text-align: center; }
th   { background: #f0f0f0; font-weight: 600; }
td.row-hdr { text-align: right; font-weight: 600; background: #f8f8f8; }
a    { text-decoration: none; color: #0055cc; }
a:hover { text-decoration: underline; }
.empty { color: #bbb; }
"""

def _html_page(title, body):
    return (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        f'<title>{title}</title>\n'
        f'<style>{_CSS}</style>\n'
        '</head>\n'
        '<body>\n'
        f'<h1>{title}</h1>\n'
        f'{body}\n'
        '</body>\n'
        '</html>\n'
    )


# ── per-directory index ───────────────────────────────────────────────────────

def gen_dir_index(dirpath):
    """Write index.html for one leaf directory of .stl files."""
    dirpath = Path(dirpath)
    stl_files = [f for f in os.listdir(dirpath) if f.endswith('.stl')]
    if not stl_files:
        return

    parsed = [p for f in stl_files if (p := _parse_stl(f)) is not None]
    if not parsed:
        return

    am_metric = parsed[0]['unit'] == 'mm'
    size_raw = parsed[0]['size']
    size_disp = _decode_size(size_raw)
    middle = parsed[0]['middle']

    # Title: e.g. "M3 Cap Bolt", "#10 Cap Bolt", "M3 Nut"
    if middle == ['nut']:
        title = f"{size_disp} Nut"
    elif middle in (['srod'], ['rod']):
        title = f"{size_disp} Threaded Rod"
    else:
        title = f"{size_disp} {' '.join(m.capitalize() for m in middle)}"

    is_nut = middle == ['nut']
    pitches = sorted({p['pitch_str'] for p in parsed}, key=_pitch_to_float)
    lengths = sorted({p['length_str'] for p in parsed}, key=_length_to_float)
    # (pitch_str, length_str) → (fname, label)
    cell = {(p['pitch_str'], p['length_str']): (p['fname'], _file_label(p, is_nut))
            for p in parsed}

    rows = ['<table>']
    rows.append(
        '<tr><th>Length \\ Pitch</th>' +
        ''.join(f'<th>{_decode_pitch(p, am_metric)}</th>' for p in pitches) +
        '</tr>'
    )
    for ls in lengths:
        length_label = _decode_length(ls, am_metric)
        cells = [f'<td class="row-hdr">{length_label}</td>']
        for ps in pitches:
            entry = cell.get((ps, ls))
            if entry:
                fn, link_text = entry
                cells.append(
                    f'<td><a href="{fn}" download title="{fn}">'
                    f'{link_text}</a></td>'
                )
            else:
                cells.append('<td class="empty">—</td>')
        rows.append('<tr>' + ''.join(cells) + '</tr>')
    rows.append('</table>')

    html = _html_page(title, '\n'.join(rows))
    out = dirpath / 'index.html'
    out.write_text(html, encoding='utf-8')
    print(f'  {out.relative_to(BLD_STL.parent)}')


# ── master index ──────────────────────────────────────────────────────────────

def gen_master_index(base_url=''):
    """
    Write bld/stl/index.html linking to all per-directory pages.

    base_url: if given, leaf-page hrefs are base_url/unit/type/head/size/index.html
              instead of the relative path.  Trailing slash is optional.
              Example: 'https://username.github.io/reponame/stl'
    """
    base_url = base_url.rstrip('/')

    def href(rel_path):
        return f"{base_url}/{rel_path}" if base_url else rel_path

    parts = []

    for unit in ['mm', 'in']:
        am_metric = unit == 'mm'
        unit_label = 'Metric' if am_metric else 'Imperial'

        # ── Bolts and Screws ──
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

            parts.append(f'<h2>{unit_label} {btype.capitalize()}s</h2>')
            rows = ['<table>']
            rows.append(
                '<tr><th>Size</th>' +
                ''.join(f'<th>{h.capitalize()}</th>' for h in heads) +
                '</tr>'
            )
            for size in sizes:
                size_disp = _decode_size(size)
                cells = [f'<td class="row-hdr">{size_disp}</td>']
                for head in heads:
                    idx = BLD_STL / unit / btype / head / size / 'index.html'
                    if idx.exists():
                        url = href(f"{unit}/{btype}/{head}/{size}/index.html")
                        cells.append(f'<td><a href="{url}">{size_disp}</a></td>')
                    else:
                        cells.append('<td class="empty">—</td>')
                rows.append('<tr>' + ''.join(cells) + '</tr>')
            rows.append('</table>')
            parts.append('\n'.join(rows))

        # ── Nuts ──
        nut_dir = BLD_STL / unit / 'nut'
        if nut_dir.is_dir():
            sizes = sorted(
                [d.name for d in nut_dir.iterdir() if d.is_dir()],
                key=lambda s: _size_sort_key(s, am_metric)
            )
            parts.append(f'<h2>{unit_label} Nuts</h2>')
            cells = []
            for s in sizes:
                idx = nut_dir / s / 'index.html'
                size_disp = _decode_size(s)
                if idx.exists():
                    url = href(f"{unit}/nut/{s}/index.html")
                    cells.append(f'<th><a href="{url}">{size_disp}</a></th>')
                else:
                    cells.append(f'<th>{size_disp}</th>')
            parts.append(f'<table><tr>{"".join(cells)}</tr></table>')

    html = _html_page('STL Download Index', '\n'.join(parts))
    out = BLD_STL / 'index.html'
    out.write_text(html, encoding='utf-8')
    label = f'with base URL: {base_url}' if base_url else '(relative links)'
    print(f'Master index {label}: {out.relative_to(BLD_STL.parent)}')


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description='Generate index.html pages for the bld/stl tree.'
    )
    parser.add_argument(
        '--base-url', default='',
        metavar='URL',
        help=(
            'Base URL for leaf-page links in the master index.\n'
            'Use the URL of the stl/ directory as hosted on GitHub, e.g.:\n'
            '  https://username.github.io/reponame/stl\n'
            'Without this flag, relative links are used (good for local testing).'
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
                gen_dir_index(root)

    gen_master_index(base_url=args.base_url)
    print('Done.')


if __name__ == '__main__':
    main()
