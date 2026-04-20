#!/usr/bin/env python3
"""
boltgen_gui — GUI for bolt/screw/nut STL generation.
Calls generate_bolt and generate_nut directly.
By Nenad Rijavec.

This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

The code itself was fully written by Claude Code (Sonnet 4.6.), following
a series of prompts and inspection of boltgen.py, nutgen.py and the
code in the underlying facet engine. There were no human changes to the
source.
"""

import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import io
import math
import threading
from fractions import Fraction
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from generate import generate_bolt, generate_nut
from parts import make_build_screw, make_build_nut
from dimensions import (
    metric_screws, imperial_screws,
    metric_nuts, imperial_nuts,
    bolt_thread_length,
)
from facets import write_binary_stl


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def diam_list(am_metric, is_nut=False):
    """Combobox values for diameter: diam:g for metric, desc for imperial."""
    items = (metric_nuts if is_nut else metric_screws) if am_metric \
            else (imperial_nuts if is_nut else imperial_screws)
    if am_metric:
        return [f"{s.diam:g}" for s in items]
    else:
        return [s.desc for s in items]          # '#5', '1/4', etc.


def lookup_screw(am_metric, diam_str):
    return make_build_screw(am_metric, diam_str)   # (orig, bld)


def lookup_nut(am_metric, diam_str):
    """Return (orig, bld). make_build_nut returns [orig, bld]."""
    orig, bld = make_build_nut(am_metric, diam_str)
    return orig, bld


def pitch_options(orig, am_metric):
    """(list_of_display_strings, default_index).
    Metric → mm values; imperial → TPI integers."""
    if am_metric:
        return [f"{p:g}" for p in orig.pitches], orig.defpitch
    else:
        return [str(int(p)) for p in orig.pitches], orig.defpitch


def display_to_mm_pitch(pitch_str, am_metric):
    v = float(pitch_str)
    return v if am_metric else 25.4 / v


def parse_length(s, am_metric):
    """Parse decimal or 'N M/D' fraction string → float in user units."""
    s = s.strip()
    if not am_metric and '/' in s:
        parts = s.split(' ')
        if len(parts) == 1:
            return float(Fraction(parts[0]))
        return int(parts[0]) + float(Fraction(parts[1]))
    return float(s)


def fmt_frac(inches, max_denom=64):
    """Format an inch value as a fraction string: '3/8', '1 1/2', etc."""
    frac = Fraction(inches).limit_denominator(max_denom)
    if frac.denominator == 1:
        return str(int(frac))
    whole = int(frac)
    if whole > 0:
        rem = frac - whole
        return f"{whole} {rem.numerator}/{rem.denominator}"
    return f"{frac.numerator}/{frac.denominator}"


# ---------------------------------------------------------------------------
# Defaults (mirror boltgen.py / nutgen.py logic)
# ---------------------------------------------------------------------------

def default_diam_adj(diam_mm, for_nut=False):
    if for_nut:
        if diam_mm < 8:    return  0.40
        if diam_mm < 9.5:  return  0.70
        return 0.80
    else:
        if diam_mm < 3.75: return -0.15
        if diam_mm < 9:    return -0.30
        return -0.50


def default_cross_adj(diam_mm):
    if diam_mm < 5: return 0.3
    if diam_mm < 7: return 0.5
    return 0.7


def default_hex_adj(diam_mm, head):
    if head == 'cap':
        return 0.3 if diam_mm < 4.5 else 0.5
    return -0.5


def hex_default_mm(bld, head):
    """Hex wrench/key size in mm for given bld and head type."""
    return bld.cap_s if head == 'cap' else bld.hex_a


def fmt_hex(bld, head, am_metric):
    """Format hex size for the GUI field."""
    mm = hex_default_mm(bld, head)
    if am_metric:
        return f"{mm:g}"
    return fmt_frac(mm / 25.4)


def fmt_shank_d(bld, am_metric):
    """Format shank diameter for the GUI field.
    Returns blank if the value is ≤ 0 (sentinel for 'not defined')."""
    if bld.shank_d <= 0:
        return ''
    if am_metric:
        return f"{bld.shank_d:g}"
    return f"{bld.shank_d / 25.4:g}"


# ---------------------------------------------------------------------------
# Filename builders (mirror boltgen.py / nutgen.py)
# ---------------------------------------------------------------------------

def bolt_fname(am_metric, units_str, head, gen_type, bld, pitch_mm, length_str):
    fname = units_str + "_"
    if head != 'none':
        fname += head + "_"
    fname += gen_type + "_"
    fname += bld.desc.replace("/", "f").replace(" converted", "")
    fname += "X"
    tpi = 25.4 / pitch_mm
    fname += f"{pitch_mm:.2f}" if am_metric else (f"{tpi:.2f}" if tpi < 5 else f"{tpi:.0f}")
    fname += f"-{length_str}".replace("/", "f")
    fname  = fname.replace(".", "p").replace(" ", "_")
    fname += ".stl"
    return fname


def nut_fname(am_metric, units_str, bld, pitch_mm, length_orig):
    """length_orig: float in user units, or None for the standard default."""
    fname = units_str + "_nut_"
    fname += bld.desc.replace("/", "f").replace(" converted", "")
    fname += "X"
    tpi = 25.4 / pitch_mm
    fname += f"{pitch_mm:.2f}" if am_metric else (f"{tpi:.2f}" if tpi < 5 else f"{tpi:.0f}")
    if length_orig is None:
        ll = bld.hex_h if am_metric else bld.hex_h / 25.4
        fname += f"-def{ll:.2f}"
    else:
        fname += f"-{length_orig:.2f}"
    fname  = fname.replace(".", "p")
    fname += ".stl"
    return fname


# ---------------------------------------------------------------------------
# Scrollable frame
# ---------------------------------------------------------------------------

def make_scrollable(parent):
    canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0)
    vsb    = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
    canvas.configure(yscrollcommand=vsb.set)
    vsb.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)
    inner  = ttk.Frame(canvas)
    win_id = canvas.create_window((0, 0), window=inner, anchor='nw')

    def _resize(event=None):
        canvas.configure(scrollregion=canvas.bbox('all'))
        canvas.itemconfig(win_id, width=canvas.winfo_width())

    inner.bind('<Configure>', _resize)
    canvas.bind('<Configure>', _resize)
    canvas.bind_all('<MouseWheel>',
                    lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))
    return inner


# ---------------------------------------------------------------------------
# Grid helpers
# ---------------------------------------------------------------------------

def lbl(parent, row, text=None, var=None):
    kw = {'textvariable': var} if var is not None else {'text': text or ''}
    ttk.Label(parent, **kw).grid(row=row, column=0, sticky='w', padx=6, pady=3)


def ent(parent, row, sv, width=22):
    e = ttk.Entry(parent, textvariable=sv, width=width)
    e.grid(row=row, column=1, sticky='w', padx=6, pady=3)
    return e


def adj_row(parent, row, label, var, help_text):
    """Row with an entry and a '?' button that shows the help text.
    label may be a plain string or a tk.StringVar."""
    if isinstance(label, str):
        lbl(parent, row, label)
    else:
        lbl(parent, row, var=label)
    frame = ttk.Frame(parent)
    frame.grid(row=row, column=1, sticky='w', padx=6, pady=3)
    e = ttk.Entry(frame, textvariable=var, width=18)
    e.pack(side='left')
    ttk.Button(frame, text='?', width=2,
               command=lambda t=help_text: messagebox.showinfo('Help', t)
               ).pack(side='left', padx=(3, 0))
    return e


def section(parent, row, text):
    ttk.Separator(parent, orient='horizontal').grid(
        row=row, column=0, columnspan=3, sticky='ew', padx=4, pady=(8, 1))
    ttk.Label(parent, text=text, font=('', 9, 'italic')).grid(
        row=row+1, column=0, columnspan=3, sticky='w', padx=6)
    return row + 2


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class BoltNutGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('Bolt / Screw / Nut STL Generator')

        nb = ttk.Notebook(root)
        nb.pack(fill='both', expand=True, padx=8, pady=8)

        bolt_tab = ttk.Frame(nb)
        nut_tab  = ttk.Frame(nb)
        nb.add(bolt_tab, text='Bolt / Screw')
        nb.add(nut_tab,  text='Nut')

        bolt_inner = make_scrollable(bolt_tab)
        nut_inner  = make_scrollable(nut_tab)
        self._build_bolt_tab(bolt_inner)
        self._build_nut_tab(nut_inner)

        out_frame = ttk.LabelFrame(root, text='Output')
        out_frame.pack(fill='both', expand=False, padx=8, pady=(0, 8))
        self.output = scrolledtext.ScrolledText(
            out_frame, height=6, state='disabled',
            font=('Monospace', 9), wrap='word')
        self.output.pack(fill='both', expand=True, padx=4, pady=4)

        self._fit_window(bolt_inner, nut_inner)

    def _fit_window(self, *inner_frames):
        """Size the window to fit the tab content on any platform/font size."""
        self.root.update_idletasks()
        w = max(f.winfo_reqwidth() for f in inner_frames)
        w += 40          # scrollbar + borders
        w = max(w, 420)  # floor
        tab_h = max(f.winfo_reqheight() for f in inner_frames)
        tab_h += 40      # notebook tab strip + padding
        out_h  = 160     # output LabelFrame (6 text lines + padding)
        total  = tab_h + out_h + 20
        screen_h = self.root.winfo_screenheight()
        total = min(total, int(screen_h * 0.92))
        self.root.geometry(f'{w}x{total}')
        self.root.minsize(w, 400)

    # ------------------------------------------------------------------ bolt
    def _build_bolt_tab(self, f):
        r = 0

        # Units
        lbl(f, r, 'Units:')
        self.bolt_units = tk.StringVar(value='mm')
        uf = ttk.Frame(f)
        uf.grid(row=r, column=1, sticky='w')
        ttk.Radiobutton(uf, text='mm (metric)',   variable=self.bolt_units,
                         value='mm', command=self._bolt_units_changed).pack(side='left')
        ttk.Radiobutton(uf, text='in (imperial)', variable=self.bolt_units,
                         value='in', command=self._bolt_units_changed).pack(side='left', padx=6)
        r += 1

        # Type
        lbl(f, r, 'Type:')
        self.bolt_type = tk.StringVar(value='bolt')
        tf = ttk.Frame(f)
        tf.grid(row=r, column=1, sticky='w')
        ttk.Radiobutton(tf, text='Bolt',  variable=self.bolt_type, value='bolt',
                         command=self._bolt_type_changed).pack(side='left')
        ttk.Radiobutton(tf, text='Screw', variable=self.bolt_type, value='screw',
                         command=self._bolt_type_changed).pack(side='left', padx=6)
        r += 1

        # Diameter (editable combobox, desc for imperial / diam:g for metric)
        lbl(f, r, 'Diameter:')
        self.bolt_diam = tk.StringVar()
        self.bolt_diam_cb = ttk.Combobox(f, textvariable=self.bolt_diam, width=20)
        self.bolt_diam_cb.grid(row=r, column=1, sticky='w', padx=6, pady=3)
        self.bolt_diam_cb.bind('<<ComboboxSelected>>',
                                lambda e: self._bolt_diam_changed())
        self.bolt_diam_cb.bind('<FocusOut>', self._check_bolt_diam)
        self.bolt_diam_cb.bind('<Return>',   self._check_bolt_diam)
        self.bolt_diam.trace_add('write', self._bolt_diam_changed)
        r += 1

        # Length (starts blank; Generate disabled until filled)
        self._bolt_len_lbl = tk.StringVar(value='Length (mm):')
        lbl(f, r, var=self._bolt_len_lbl)
        self.bolt_length = tk.StringVar()
        _e = ent(f, r, self.bolt_length)
        _e.bind('<FocusOut>', self._check_bolt_length)
        _e.bind('<Return>',   self._check_bolt_length)
        self.bolt_length.trace_add('write', self._bolt_length_changed)
        r += 1

        # Head
        lbl(f, r, 'Head:')
        self.bolt_head = tk.StringVar(value='hex')
        self.bolt_head_cb = ttk.Combobox(
            f, textvariable=self.bolt_head,
            values=['hex', 'flat', 'pan', 'cap', 'none'],
            width=20, state='readonly')
        self.bolt_head_cb.grid(row=r, column=1, sticky='w', padx=6, pady=3)
        self.bolt_head_cb.bind('<<ComboboxSelected>>',
                                lambda e: self._bolt_head_changed())
        r += 1

        r = section(f, r, 'Advanced (pre-filled with defaults)')

        # Pitch / TPI  (editable combobox)
        self._bolt_pitch_lbl = tk.StringVar(value='Pitch (mm):')
        lbl(f, r, var=self._bolt_pitch_lbl)
        self.bolt_pitch = tk.StringVar()
        self.bolt_pitch_cb = ttk.Combobox(f, textvariable=self.bolt_pitch, width=20)
        self.bolt_pitch_cb.grid(row=r, column=1, sticky='w', padx=6, pady=3)
        self.bolt_pitch.trace_add('write', self._update_bolt_outfile)
        self.bolt_pitch_cb.bind('<FocusOut>', self._check_bolt_pitch)
        self.bolt_pitch_cb.bind('<Return>',   self._check_bolt_pitch)
        r += 1

        # Shank diameter (disabled for Screw)
        self._bolt_shankd_lbl = tk.StringVar(value='Shank diameter (mm):')
        lbl(f, r, var=self._bolt_shankd_lbl)
        self.bolt_shank_d = tk.StringVar()
        self.bolt_shank_d_entry = ent(f, r, self.bolt_shank_d)
        r += 1

        # Shank length (disabled for Screw)
        self._bolt_shankl_lbl = tk.StringVar(value='Shank length, blank=auto (mm):')
        lbl(f, r, var=self._bolt_shankl_lbl)
        self.bolt_shank_l = tk.StringVar()
        self.bolt_shank_l_entry = ent(f, r, self.bolt_shank_l)
        self.bolt_shank_l_entry.bind('<FocusOut>', self._check_bolt_shank_l)
        self.bolt_shank_l_entry.bind('<Return>',   self._check_bolt_shank_l)
        r += 1

        # Hex wrench / key size
        self._bolt_hex_lbl = tk.StringVar(value='Hex wrench/key size (mm):')
        lbl(f, r, var=self._bolt_hex_lbl)
        self.bolt_hex = tk.StringVar()
        _e = ent(f, r, self.bolt_hex)
        _e.bind('<FocusOut>', self._check_bolt_hex)
        _e.bind('<Return>',   self._check_bolt_hex)
        r += 1

        # hex_h (hex head height, in user units)
        self._bolt_hex_h_lbl = tk.StringVar(value='Hex head height (mm):')
        self.bolt_hex_h = tk.StringVar()
        adj_row(f, r, self._bolt_hex_h_lbl, self.bolt_hex_h,
                'Height of the hex head in user units.')
        r += 1

        # fn
        self.bolt_fn = tk.StringVar(value='50')
        adj_row(f, r, 'Segments (fn):', self.bolt_fn,
                'Number of segments for each cylinder.')
        r += 1

        # cross_adj
        self.bolt_cross_adj = tk.StringVar()
        adj_row(f, r, 'Cross recess adj (mm):', self.bolt_cross_adj,
                'Increase of cross-recess trench width in mm.')
        r += 1

        # diam_adj
        self.bolt_diam_adj = tk.StringVar()
        adj_row(f, r, 'Thread diam adj (mm):', self.bolt_diam_adj,
                'Increase/decrease the thread diameter in mm.')
        r += 1

        # hex_adj
        self.bolt_hex_adj = tk.StringVar()
        adj_row(f, r, 'Hex head adj (mm):', self.bolt_hex_adj,
                'Increase/decrease the diameter of the hex head in mm.')
        r += 1

        # h_adj (pan/flat/cap head height increase, always mm, non-negative)
        self.bolt_h_adj = tk.StringVar(value='0')
        _e = adj_row(f, r, 'Head height adj (mm):', self.bolt_h_adj,
                     'Increase the height of pan, flat, or cap head in mm.\nMust be >= 0.')
        _e.bind('<FocusOut>', self._check_bolt_h_adj)
        _e.bind('<Return>',   self._check_bolt_h_adj)
        r += 1

        # Output file (pre-filled, editable, browsable)
        lbl(f, r, 'Output file:')
        self.bolt_outfile = tk.StringVar()
        self._bolt_outfile_locked = False   # True when user has edited the field
        self._bolt_outfile_writing = False  # True while we are setting it programmatically
        self.bolt_outfile.trace_add('write', self._bolt_outfile_edited)
        ttk.Entry(f, textvariable=self.bolt_outfile, width=40).grid(
            row=r, column=1, sticky='w', padx=6, pady=3)
        r += 1
        ttk.Button(f, text='Browse…', command=self._bolt_browse).grid(
            row=r, column=1, sticky='w', padx=6, pady=(0, 3))
        r += 1

        # Verbose
        self.bolt_verbose = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text='Verbose output',
                         variable=self.bolt_verbose).grid(
            row=r, column=0, columnspan=2, sticky='w', padx=6, pady=3)
        r += 1

        # Generate (starts disabled until length is filled)
        self.bolt_btn = ttk.Button(f, text='Generate STL',
                                    command=self._generate_bolt,
                                    state='disabled')
        self.bolt_btn.grid(row=r, column=0, columnspan=2, pady=10)

        self._bolt_units_changed()   # populate all defaults

    # ------------------------------------------------------------------- nut
    def _build_nut_tab(self, f):
        r = 0

        # Units
        lbl(f, r, 'Units:')
        self.nut_units = tk.StringVar(value='mm')
        uf = ttk.Frame(f)
        uf.grid(row=r, column=1, sticky='w')
        ttk.Radiobutton(uf, text='mm (metric)',   variable=self.nut_units,
                         value='mm', command=self._nut_units_changed).pack(side='left')
        ttk.Radiobutton(uf, text='in (imperial)', variable=self.nut_units,
                         value='in', command=self._nut_units_changed).pack(side='left', padx=6)
        r += 1

        # Diameter
        lbl(f, r, 'Diameter:')
        self.nut_diam = tk.StringVar()
        self.nut_diam_cb = ttk.Combobox(f, textvariable=self.nut_diam, width=20)
        self.nut_diam_cb.grid(row=r, column=1, sticky='w', padx=6, pady=3)
        self.nut_diam_cb.bind('<<ComboboxSelected>>',
                               lambda e: self._nut_diam_changed())
        self.nut_diam_cb.bind('<FocusOut>', self._check_nut_diam)
        self.nut_diam_cb.bind('<Return>',   self._check_nut_diam)
        self.nut_diam.trace_add('write', self._nut_diam_changed)
        r += 1

        r = section(f, r, 'Advanced (pre-filled with defaults)')

        # Length
        self._nut_len_lbl = tk.StringVar(value='Length, blank=default (mm):')
        lbl(f, r, var=self._nut_len_lbl)
        self.nut_length = tk.StringVar()
        _e = ent(f, r, self.nut_length)
        _e.bind('<FocusOut>', self._check_nut_length)
        _e.bind('<Return>',   self._check_nut_length)
        self.nut_length.trace_add('write', self._update_nut_outfile)
        self.nut_length.trace_add('write', lambda *_: setattr(self, '_nut_length_validated', None))
        r += 1

        # Pitch / TPI
        self._nut_pitch_lbl = tk.StringVar(value='Pitch (mm):')
        lbl(f, r, var=self._nut_pitch_lbl)
        self.nut_pitch = tk.StringVar()
        self.nut_pitch_cb = ttk.Combobox(f, textvariable=self.nut_pitch, width=20)
        self.nut_pitch_cb.grid(row=r, column=1, sticky='w', padx=6, pady=3)
        self.nut_pitch.trace_add('write', self._update_nut_outfile)
        self.nut_pitch_cb.bind('<FocusOut>', self._check_nut_pitch)
        self.nut_pitch_cb.bind('<Return>',   self._check_nut_pitch)
        r += 1

        # Hex wrench size
        self._nut_hex_lbl = tk.StringVar(value='Hex wrench size (mm):')
        lbl(f, r, var=self._nut_hex_lbl)
        self.nut_hex = tk.StringVar()
        _e = ent(f, r, self.nut_hex)
        _e.bind('<FocusOut>', self._check_nut_hex)
        _e.bind('<Return>',   self._check_nut_hex)
        r += 1

        # fn
        self.nut_fn = tk.StringVar(value='50')
        adj_row(f, r, 'Segments (fn):', self.nut_fn,
                'Number of segments for each cylinder.')
        r += 1

        # diam_adj
        self.nut_diam_adj = tk.StringVar()
        adj_row(f, r, 'Thread diam adj (mm):', self.nut_diam_adj,
                'Increase/decrease the thread diameter in mm.')
        r += 1

        # hex_adj
        self.nut_hex_adj = tk.StringVar()
        adj_row(f, r, 'Hex nut adj (mm):', self.nut_hex_adj,
                'Increase/decrease the diameter of the hex nut in mm.')
        r += 1

        # Output file
        lbl(f, r, 'Output file:')
        self.nut_outfile = tk.StringVar()
        self._nut_outfile_locked = False
        self._nut_outfile_writing = False
        self.nut_outfile.trace_add('write', self._nut_outfile_edited)
        ttk.Entry(f, textvariable=self.nut_outfile, width=40).grid(
            row=r, column=1, sticky='w', padx=6, pady=3)
        r += 1
        ttk.Button(f, text='Browse…', command=self._nut_browse).grid(
            row=r, column=1, sticky='w', padx=6, pady=(0, 3))
        r += 1

        # Verbose
        self.nut_verbose = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text='Verbose output',
                         variable=self.nut_verbose).grid(
            row=r, column=0, columnspan=2, sticky='w', padx=6, pady=3)
        r += 1

        # Generate
        self.nut_btn = ttk.Button(f, text='Generate STL',
                                   command=self._generate_nut)
        self.nut_btn.grid(row=r, column=0, columnspan=2, pady=10)

        self._nut_units_changed()

        # last-validated sentinels — prevent repeated errors when nothing changed
        self._bolt_length_validated = None
        self._nut_length_validated  = None

    # ---------------------------------------------------------------- callbacks

    def _bolt_units_changed(self):
        am_metric = self.bolt_units.get() == 'mm'
        diams = diam_list(am_metric, is_nut=False)
        self.bolt_diam_cb['values'] = diams
        self.bolt_diam.set(diams[0])
        # update dynamic labels
        u = 'mm' if am_metric else 'in'
        self._bolt_pitch_lbl.set('Pitch (mm):' if am_metric else 'TPI:')
        self._bolt_len_lbl.set(f'Length ({u}):')
        self._bolt_shankd_lbl.set(f'Shank diameter ({u}):')
        self._bolt_shankl_lbl.set(f'Shank length, blank=auto ({u}):')
        self._bolt_hex_lbl.set(f'Hex wrench/key size ({u}):')
        self._bolt_hex_h_lbl.set(f'Hex head height ({u}):')
        # _bolt_diam_changed is triggered by the trace on bolt_diam

    def _bolt_type_changed(self):
        self._update_shank_state()
        self._update_bolt_outfile()

    def _update_shank_state(self):
        is_bolt = self.bolt_type.get() == 'bolt'
        state   = 'normal' if is_bolt else 'disabled'
        self.bolt_shank_d_entry.config(state=state)
        self.bolt_shank_l_entry.config(state=state)
        if not is_bolt:
            self.bolt_shank_d.set('')
            self.bolt_shank_l.set('')
        elif not self.bolt_shank_d.get():
            # restore shank_d default when switching back to bolt
            am_metric = self.bolt_units.get() == 'mm'
            try:
                _, bld = lookup_screw(am_metric, self.bolt_diam.get().strip())
                if bld:
                    self.bolt_shank_d.set(fmt_shank_d(bld, am_metric))
            except Exception:
                pass

    def _bolt_diam_changed(self, *_):
        am_metric = self.bolt_units.get() == 'mm'
        diam_str = self.bolt_diam.get().strip()
        if not diam_str:
            return
        try:
            orig, bld = lookup_screw(am_metric, diam_str)
        except Exception:
            return
        if orig is None or bld is None:
            return
        # clear length — new diameter, old length is no longer meaningful
        self.bolt_length.set('')
        # pitch list & default
        opts, defidx = pitch_options(orig, am_metric)
        self.bolt_pitch_cb['values'] = opts
        self.bolt_pitch.set(opts[defidx])
        # shank_d (only if bolt type)
        if self.bolt_type.get() == 'bolt':
            self.bolt_shank_d.set(fmt_shank_d(bld, am_metric))
        # adjustments
        self.bolt_diam_adj.set(f"{default_diam_adj(bld.diam):g}")
        self.bolt_cross_adj.set(f"{default_cross_adj(bld.diam):g}")
        # hex_h default in user units
        hex_h_disp = bld.hex_h if am_metric else bld.hex_h / 25.4
        self.bolt_hex_h.set(f"{hex_h_disp:g}")
        # hex & hex_adj depend on current head
        self._refresh_bolt_hex(bld)
        self._update_bolt_outfile()

    # ---- helpers: parse bolt/nut context without raising ----

    def _bolt_context(self):
        """Return dict of parsed bolt fields, or None if anything critical fails."""
        am_metric  = self.bolt_units.get() == 'mm'
        diam_str   = self.bolt_diam.get().strip()
        pitch_str  = self.bolt_pitch.get().strip()
        length_str = self.bolt_length.get().strip()
        if not (diam_str and pitch_str):
            return None
        try:
            orig, bld = lookup_screw(am_metric, diam_str)
            if bld is None:
                return None
            pitch_mm = display_to_mm_pitch(pitch_str, am_metric)
        except Exception:
            return None
        length_orig = None
        length_mm   = None
        if length_str:
            try:
                length_orig = parse_length(length_str, am_metric)
                length_mm   = length_orig if am_metric else length_orig * 25.4
            except Exception:
                pass
        try:
            fn = int(self.bolt_fn.get().strip())
        except Exception:
            fn = 50
        hex_str = self.bolt_hex.get().strip()
        try:
            hex_val = parse_length(hex_str, am_metric) if hex_str else None
            if hex_val is not None and not am_metric:
                hex_val *= 25.4
        except Exception:
            hex_val = None
        return dict(am_metric=am_metric, orig=orig, bld=bld,
                    pitch_mm=pitch_mm,
                    length_orig=length_orig, length_mm=length_mm,
                    fn=fn, hex_val=hex_val,
                    head=self.bolt_head.get().strip(),
                    btype=self.bolt_type.get())

    def _nut_context(self):
        """Return dict of parsed nut fields, or None if anything critical fails."""
        am_metric = self.nut_units.get() == 'mm'
        diam_str  = self.nut_diam.get().strip()
        pitch_str = self.nut_pitch.get().strip()
        len_s     = self.nut_length.get().strip()
        if not (diam_str and pitch_str):
            return None
        try:
            orig, bld = lookup_nut(am_metric, diam_str)
            if bld is None:
                return None
            pitch_mm = display_to_mm_pitch(pitch_str, am_metric)
        except Exception:
            return None
        length_mm = None
        if len_s:
            try:
                l = parse_length(len_s, am_metric)
                length_mm = l if am_metric else l * 25.4
            except Exception:
                pass
        try:
            fn = int(self.nut_fn.get().strip())
        except Exception:
            fn = 50
        try:
            hex_val = parse_length(self.nut_hex.get().strip(), am_metric)
            if not am_metric:
                hex_val *= 25.4
        except Exception:
            hex_val = None
        return dict(am_metric=am_metric, orig=orig, bld=bld,
                    pitch_mm=pitch_mm, length_mm=length_mm,
                    fn=fn, hex_val=hex_val)

    # ---- early validation callbacks ----

    def _check_bolt_diam(self, *_):
        am_metric = self.bolt_units.get() == 'mm'
        s = self.bolt_diam.get().strip()
        if not s:
            return
        if am_metric:
            if '#' in s:
                messagebox.showerror('Error',
                    f'"{s}" is an imperial size. Switch units to "in".')
                return
            if '/' in s:
                messagebox.showerror('Error',
                    f'Fractional sizes are imperial. Switch units to "in".')
                return
            try:
                if float(s) <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror('Error', f'Invalid diameter: "{s}"')
        else:
            if s.startswith('#'):
                if s not in diam_list(False, is_nut=False):
                    messagebox.showerror('Error',
                        f'Unknown {s}, can\'t interpolate.')
            else:
                try:
                    parts = s.strip().split()
                    if len(parts) == 1:
                        v = float(Fraction(parts[0]))
                    else:
                        v = int(parts[0]) + float(Fraction(parts[1]))
                    if v <= 0:
                        raise ValueError
                except Exception:
                    messagebox.showerror('Error', f'Invalid diameter: "{s}"')

    def _check_nut_diam(self, *_):
        am_metric = self.nut_units.get() == 'mm'
        s = self.nut_diam.get().strip()
        if not s:
            return
        if am_metric:
            if '#' in s:
                messagebox.showerror('Error',
                    f'"{s}" is an imperial size. Switch units to "in".')
                return
            if '/' in s:
                messagebox.showerror('Error',
                    f'Fractional sizes are imperial. Switch units to "in".')
                return
            try:
                if float(s) <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror('Error', f'Invalid diameter: "{s}"')
        else:
            if s.startswith('#'):
                if s not in diam_list(False, is_nut=True):
                    messagebox.showerror('Error',
                        f'Unknown {s}, can\'t interpolate.')
            else:
                try:
                    parts = s.strip().split()
                    if len(parts) == 1:
                        v = float(Fraction(parts[0]))
                    else:
                        v = int(parts[0]) + float(Fraction(parts[1]))
                    if v <= 0:
                        raise ValueError
                except Exception:
                    messagebox.showerror('Error', f'Invalid diameter: "{s}"')

    def _check_bolt_pitch(self, *_):
        ctx = self._bolt_context()
        if ctx is None:
            return
        bld, pitch_mm = ctx['bld'], ctx['pitch_mm']
        threshold = pitch_mm * math.sqrt(3) / 2 + 0.1
        if bld.diam / 2 < threshold:
            messagebox.showerror('Error',
                f'Pitch too coarse for diameter.\n'
                f'diam={bld.diam:.4f} mm, pitch={pitch_mm:.4f} mm\n'
                f'Need diam/2 ({bld.diam/2:.4f}) >= {threshold:.4f}')
            return
        # pitch change can also make the current length too short
        self._check_bolt_length()

    def _check_bolt_length(self, *_):
        cur = self.bolt_length.get().strip()
        if cur == self._bolt_length_validated:
            return                          # same value already checked
        self._bolt_length_validated = cur   # mark as checked (valid or error)
        ctx = self._bolt_context()
        if ctx is None:
            return
        bld, pitch_mm, length_mm, fn = (
            ctx['bld'], ctx['pitch_mm'], ctx['length_mm'], ctx['fn'])
        if length_mm is None:
            return
        w = 2.5 * pitch_mm + bld.diam / 16 + 2 * pitch_mm / fn + 0.1
        if length_mm < w:
            messagebox.showerror('Error',
                f'Length too short for this pitch.\nMinimum is {w:.2f} mm')
            return
        # when shank_l is auto-computed (blank), check it won't go negative
        if not self.bolt_shank_l.get().strip() and ctx['btype'] == 'bolt':
            orig, length_orig, head = ctx['orig'], ctx['length_orig'], ctx['head']
            if length_orig is not None:
                thread_l = 0.5 * bolt_thread_length(
                    length_orig, orig.diam, ctx['am_metric'])
                shank_l_auto = (length_mm - thread_l if ctx['am_metric']
                                else 25.4 * (length_orig - thread_l))
                if head == 'none':
                    shank_l_auto -= thread_l
                if shank_l_auto <= 0:
                    messagebox.showerror('Error',
                        'Length too short: computed shank length would be negative.')
                    return
        # also validate shank_l if it's filled in
        self._check_bolt_shank_l()

    def _check_bolt_shank_l(self, *_):
        ctx = self._bolt_context()
        if ctx is None:
            return
        length_mm = ctx['length_mm']
        shank_l_str = self.bolt_shank_l.get().strip()
        if not (length_mm and shank_l_str):
            return
        try:
            sl = parse_length(shank_l_str, ctx['am_metric'])
            if not ctx['am_metric']:
                sl *= 25.4
        except Exception:
            return
        if sl <= 0 or sl >= length_mm:
            messagebox.showerror('Error',
                'Shank length must be > 0 and < total length.')
            return
        # check remaining thread-segment length (mirrors fixed boltgen.py logic)
        bld, pitch_mm, fn = ctx['bld'], ctx['pitch_mm'], ctx['fn']
        w = 2.5 * pitch_mm + bld.diam / 16 + 2 * pitch_mm / fn + 0.1
        is_srod = ctx['head'] == 'none' and ctx['btype'] == 'bolt'
        ll = length_mm - sl
        if is_srod:
            if ll < 2 * w:
                messagebox.showerror('Error',
                    f'Length too short for this pitch with this shank.\n'
                    f'Minimum length is {2*w+sl:.2f} mm')
        else:
            if ll < w:
                messagebox.showerror('Error',
                    f'Length too short for this pitch with this shank.\n'
                    f'Minimum length is {w+sl:.2f} mm')

    def _check_nut_pitch(self, *_):
        ctx = self._nut_context()
        if ctx is None:
            return
        bld, pitch_mm = ctx['bld'], ctx['pitch_mm']
        threshold = pitch_mm * math.sqrt(3) / 2 + 0.1
        if bld.diam / 2 < threshold:
            messagebox.showerror('Error',
                f'Pitch too coarse for diameter.\n'
                f'diam={bld.diam:.4f} mm, pitch={pitch_mm:.4f} mm\n'
                f'Need diam/2 ({bld.diam/2:.4f}) >= {threshold:.4f}')
            return
        # pitch change can also make the current length too short
        self._check_nut_length()

    def _check_nut_length(self, *_):
        cur = self.nut_length.get().strip()
        if cur == self._nut_length_validated:
            return                         # same value already checked
        self._nut_length_validated = cur   # mark as checked
        ctx = self._nut_context()
        if ctx is None:
            return
        bld, pitch_mm, fn = ctx['bld'], ctx['pitch_mm'], ctx['fn']
        hex_val  = ctx['hex_val']
        length_mm = ctx['length_mm'] if ctx['length_mm'] is not None else bld.hex_h
        if hex_val is not None:
            w_hex = 0.2 * hex_val
            if length_mm < w_hex:
                messagebox.showerror('Error',
                    f'Length too short for this diameter.\nMinimum is {w_hex:.2f} mm')
                return
        min_thread = 2.5 * pitch_mm + 2 * pitch_mm / fn + 0.1
        if length_mm < min_thread:
            messagebox.showerror('Error',
                f'Length too short for this pitch.\nMinimum is {min_thread:.2f} mm')

    def _check_bolt_h_adj(self, *_):
        s = self.bolt_h_adj.get().strip()
        if not s:
            return
        try:
            v = float(s)
            assert v >= 0
        except Exception:
            messagebox.showerror('Error', 'Head height adj must be >= 0.')

    def _check_bolt_hex(self, *_):
        ctx = self._bolt_context()
        if ctx is None:
            return
        bld, head, hex_val = ctx['bld'], ctx['head'], ctx['hex_val']
        if hex_val is None:
            return
        if head == 'hex':
            if hex_val < bld.diam:
                messagebox.showerror('Error',
                    f'Hex wrench size too small (< diam {bld.diam:.2f} mm).')
        elif head == 'cap':
            hex_d = 2 * hex_val / math.sqrt(3)
            if hex_d > bld.cap_d - 1:
                messagebox.showerror('Error',
                    f'Hex key size too large for cap head (cap_d={bld.cap_d:.2f} mm).')

    def _check_nut_hex(self, *_):
        ctx = self._nut_context()
        if ctx is None:
            return
        bld, pitch_mm, hex_val = ctx['bld'], ctx['pitch_mm'], ctx['hex_val']
        if hex_val is None:
            return
        min_hex = bld.diam + 0.5 + pitch_mm
        if hex_val < min_hex:
            messagebox.showerror('Error',
                f'Hex wrench size too small.\nMinimum is {min_hex:.2f} mm.')

    def _bolt_head_changed(self):
        am_metric = self.bolt_units.get() == 'mm'
        try:
            _, bld = lookup_screw(am_metric, self.bolt_diam.get().strip())
        except Exception:
            return
        if bld is None:
            return
        self._refresh_bolt_hex(bld)
        self._update_bolt_outfile()

    def _refresh_bolt_hex(self, bld):
        am_metric = self.bolt_units.get() == 'mm'
        head = self.bolt_head.get()
        self.bolt_hex.set(fmt_hex(bld, head, am_metric))
        self.bolt_hex_adj.set(f"{default_hex_adj(bld.diam, head):g}")

    def _bolt_length_changed(self, *_):
        self._bolt_length_validated = None   # new value → allow re-check
        filled = bool(self.bolt_length.get().strip())
        self.bolt_btn.config(state='normal' if filled else 'disabled')
        self._update_bolt_outfile()

    def _bolt_outfile_edited(self, *_):
        if self._bolt_outfile_writing:
            return
        # User made this change: lock if non-empty, unlock if cleared
        self._bolt_outfile_locked = bool(self.bolt_outfile.get())

    def _update_bolt_outfile(self, *_):
        if self._bolt_outfile_locked:
            return
        am_metric  = self.bolt_units.get() == 'mm'
        units_str  = 'mm' if am_metric else 'in'
        diam_str   = self.bolt_diam.get().strip()
        length_str = self.bolt_length.get().strip()
        head       = self.bolt_head.get().strip()
        pitch_str  = self.bolt_pitch.get().strip()
        btype      = self.bolt_type.get()
        if not (diam_str and length_str and head and pitch_str):
            return
        try:
            _, bld     = lookup_screw(am_metric, diam_str)
            if bld is None:
                return
            pitch_mm   = display_to_mm_pitch(pitch_str, am_metric)
            gen_type   = ('srod' if btype == 'bolt' else 'rod') \
                          if head == 'none' else btype
            self._bolt_outfile_writing = True
            self.bolt_outfile.set(
                bolt_fname(am_metric, units_str, head, gen_type,
                           bld, pitch_mm, length_str))
            self._bolt_outfile_writing = False
        except Exception:
            self._bolt_outfile_writing = False

    def _nut_units_changed(self):
        am_metric = self.nut_units.get() == 'mm'
        diams = diam_list(am_metric, is_nut=True)
        self.nut_diam_cb['values'] = diams
        u = 'mm' if am_metric else 'in'
        self._nut_pitch_lbl.set('Pitch (mm):' if am_metric else 'TPI:')
        self._nut_len_lbl.set(f'Length, blank=default ({u}):')
        self._nut_hex_lbl.set(f'Hex wrench size ({u}):')
        # setting the diam triggers _nut_diam_changed which repopulates pitch
        self.nut_diam.set(diams[0])

    def _nut_diam_changed(self, *_):
        am_metric = self.nut_units.get() == 'mm'
        diam_str = self.nut_diam.get().strip()
        if not diam_str:
            return
        try:
            orig, bld = lookup_nut(am_metric, diam_str)
        except Exception:
            return
        if orig is None or bld is None:
            return
        # clear length — new diameter, old length is no longer meaningful
        self.nut_length.set('')
        opts, defidx = pitch_options(orig, am_metric)
        self.nut_pitch_cb['values'] = opts
        self.nut_pitch.set(opts[defidx])
        # hex wrench
        mm = bld.hex_a
        self.nut_hex.set(f"{mm:g}" if am_metric else fmt_frac(mm / 25.4))
        self.nut_diam_adj.set(f"{default_diam_adj(bld.diam, for_nut=True):g}")
        self.nut_hex_adj.set('-0.5')
        self._update_nut_outfile()

    def _nut_outfile_edited(self, *_):
        if self._nut_outfile_writing:
            return
        self._nut_outfile_locked = bool(self.nut_outfile.get())

    def _update_nut_outfile(self, *_):
        if self._nut_outfile_locked:
            return
        am_metric = self.nut_units.get() == 'mm'
        units_str = 'mm' if am_metric else 'in'
        diam_str  = self.nut_diam.get().strip()
        pitch_str = self.nut_pitch.get().strip()
        if not (diam_str and pitch_str):
            return
        try:
            _, bld = lookup_nut(am_metric, diam_str)
            if bld is None:
                return
            pitch_mm = display_to_mm_pitch(pitch_str, am_metric)
            len_s = self.nut_length.get().strip()
            length_orig = parse_length(len_s, am_metric) if len_s else None
            self._nut_outfile_writing = True
            self.nut_outfile.set(
                nut_fname(am_metric, units_str, bld, pitch_mm, length_orig))
            self._nut_outfile_writing = False
        except Exception:
            self._nut_outfile_writing = False

    # -------------------------------------------------------------- browse
    def _browse(self, outfile_var):
        current = outfile_var.get().strip()
        initialdir  = SCRIPT_DIR
        initialfile = ''
        if current:
            abs_path    = os.path.join(SCRIPT_DIR, current) \
                          if not os.path.isabs(current) else current
            initialdir  = os.path.dirname(abs_path) or SCRIPT_DIR
            initialfile = os.path.basename(abs_path)
        path = filedialog.asksaveasfilename(
            defaultextension='.stl',
            filetypes=[('STL files', '*.stl'), ('All files', '*.*')],
            initialdir=initialdir,
            initialfile=initialfile,
        )
        if path:
            outfile_var.set(path)

    def _bolt_browse(self):
        self._browse(self.bolt_outfile)

    def _nut_browse(self):
        self._browse(self.nut_outfile)

    # -------------------------------------------------------------- output log
    def _log(self, text):
        self.output.config(state='normal')
        self.output.insert('end', text + '\n')
        self.output.see('end')
        self.output.config(state='disabled')

    def _clear_log(self):
        self.output.config(state='normal')
        self.output.delete('1.0', 'end')
        self.output.config(state='disabled')

    def _log_print_vars(self, obj):
        buf = io.StringIO()
        old, sys.stdout = sys.stdout, buf
        try:
            obj.print_vars()
        finally:
            sys.stdout = old
        for line in buf.getvalue().splitlines():
            self._log(line)

    # ------------------------------------------------------------ generate bolt
    def _generate_bolt(self):
        am_metric  = self.bolt_units.get() == 'mm'
        units_str  = 'mm' if am_metric else 'in'
        btype      = self.bolt_type.get()
        diam_str   = self.bolt_diam.get().strip()
        length_str = self.bolt_length.get().strip()
        head       = self.bolt_head.get().strip()

        if not length_str:
            messagebox.showerror('Error', 'Length is required.')
            return
        if not head:
            messagebox.showerror('Error', 'Head is required.')
            return

        orig, bld = lookup_screw(am_metric, diam_str)
        if orig is None:
            messagebox.showerror('Error', f'Diameter "{diam_str}" not found.')
            return

        try:
            length_orig = parse_length(length_str, am_metric)
        except Exception:
            messagebox.showerror('Error', f'Invalid length: "{length_str}"')
            return
        if length_orig <= 0:
            messagebox.showerror('Error', 'Length must be > 0.')
            return
        length_mm = length_orig if am_metric else length_orig * 25.4

        try:
            pitch_mm = display_to_mm_pitch(self.bolt_pitch.get().strip(), am_metric)
        except Exception:
            messagebox.showerror('Error', f'Invalid pitch: "{self.bolt_pitch.get()}"')
            return

        try:
            fn = int(self.bolt_fn.get().strip())
            assert fn > 0
        except Exception:
            messagebox.showerror('Error', 'fn must be a positive integer.')
            return

        try:
            diam_adj  = float(self.bolt_diam_adj.get().strip())
            cross_adj = float(self.bolt_cross_adj.get().strip())
            hex_adj   = float(self.bolt_hex_adj.get().strip())
        except Exception:
            messagebox.showerror('Error', 'Invalid adjustment value.')
            return

        try:
            hex_h_raw = parse_length(self.bolt_hex_h.get().strip(), am_metric)
            assert hex_h_raw > 0
            hex_h = hex_h_raw if am_metric else hex_h_raw * 25.4
        except Exception:
            messagebox.showerror('Error', 'Hex head height must be > 0.')
            return

        try:
            h_adj = float(self.bolt_h_adj.get().strip())
            assert h_adj >= 0
        except Exception:
            messagebox.showerror('Error', 'Head height adj must be >= 0.')
            return

        threshold = pitch_mm * math.sqrt(3) / 2 + 0.1
        if bld.diam / 2 < threshold:
            messagebox.showerror('Error',
                f'Pitch too coarse for diameter.\n'
                f'diam={bld.diam:.4f} mm, pitch={pitch_mm:.4f} mm\n'
                f'Need diam/2={bld.diam/2:.4f} >= threshold={threshold:.4f}')
            return

        # hex: field holds mm for metric, inch fraction for imperial
        hex_str = self.bolt_hex.get().strip()
        try:
            hex_val = parse_length(hex_str, am_metric) if hex_str else None
            if hex_val is not None and not am_metric:
                hex_val *= 25.4   # → mm
        except Exception:
            messagebox.showerror('Error', f'Invalid hex size: "{hex_str}"')
            return
        if hex_val is not None:
            if head == 'hex' and hex_val < bld.diam:
                messagebox.showerror('Error', 'Error: hex < diam')
                return
            elif head == 'cap':
                hex_d = 2 * hex_val / math.sqrt(3)
                if hex_d > bld.cap_d - 1:
                    messagebox.showerror('Error', 'Error: hex too large')
                    return

        # shank_d: field holds mm for metric, decimal inches for imperial
        shank_d_str = self.bolt_shank_d.get().strip()
        if shank_d_str:
            try:
                shank_d = float(shank_d_str)
                if not am_metric:
                    shank_d *= 25.4
            except Exception:
                messagebox.showerror('Error', f'Invalid shank diameter: "{shank_d_str}"')
                return
        else:
            shank_d = bld.shank_d if btype == 'bolt' else None

        # shank_l: field in user units, auto-compute when blank
        shank_l_str = self.bolt_shank_l.get().strip()
        shank_l = None
        if shank_l_str:
            try:
                shank_l = parse_length(shank_l_str, am_metric)
                if not am_metric:
                    shank_l *= 25.4
            except Exception:
                messagebox.showerror('Error', f'Invalid shank length: "{shank_l_str}"')
                return
            if shank_l <= 0 or shank_l >= length_mm:
                messagebox.showerror('Error',
                    'Shank length must be > 0 and < total length.')
                return
        elif btype == 'bolt':
            thread_l = 0.5 * bolt_thread_length(length_orig, orig.diam, am_metric)
            shank_l  = length_mm - thread_l if am_metric \
                       else 25.4 * (length_orig - thread_l)
            if head == 'none':
                shank_l -= thread_l
            if shank_l <= 0:
                messagebox.showerror('Error',
                    'Error: length too short, shank length is negative')
                return

        # Minimum thread-segment length check (mirrors boltgen.py exactly).
        is_srod = (head == 'none' and btype == 'bolt')
        w = 2.5 * pitch_mm + bld.diam / 16 + 2 * pitch_mm / fn + 0.1
        if shank_l is None:
            if length_mm < w:
                messagebox.showerror('Error',
                    f'Error: length too short for this pitch.\nMinimum is {w:.2f}')
                return
        else:
            ll = length_mm - shank_l
            if is_srod:
                if ll < 2 * w:
                    messagebox.showerror('Error',
                        f'Error: length too short for this pitch.\nMinimum is {2*w+shank_l:.2f} mm')
                    return
            else:
                if ll < w:
                    messagebox.showerror('Error',
                        f'Error: length too short for this pitch.\nMinimum is {w+shank_l:.2f} mm')
                    return

        gen_type = ('srod' if btype == 'bolt' else 'rod') \
                    if head == 'none' else btype

        outfile = self.bolt_outfile.get().strip() or \
                  bolt_fname(am_metric, units_str, head, gen_type,
                              bld, pitch_mm, length_str)

        self._clear_log()
        if bld.am_interpolated:
            self._log(f'{btype} was interpolated')
        if self.bolt_verbose.get():
            self._log_print_vars(bld)
            self._log(f'  diam      : {orig.desc}  ({bld.diam:g} mm)')
            self._log(f'  type      : {gen_type}')
            self._log(f'  length    : {length_mm:g} mm')
            self._log(f'  head      : {head}')
            self._log(f'  pitch     : {pitch_mm:g} mm')
            self._log(f'  hex       : {hex_val}')
            self._log(f'  hex_h     : {hex_h}')
            self._log(f'  shank_l   : {shank_l}')
            self._log(f'  shank_d   : {shank_d}')
            self._log(f'  fn        : {fn}')
            self._log(f'  cross_adj : {cross_adj}')
            self._log(f'  diam_adj  : {diam_adj}')
            self._log(f'  hex_adj   : {hex_adj}')
            self._log(f'  h_adj     : {h_adj}')
        self._log(f'Generating {outfile} …')

        self.bolt_btn.config(state='disabled')
        btn = self.bolt_btn

        def run():
            try:
                facets = []
                generate_bolt(am_metric, gen_type, bld,
                               pitch_mm, length_mm, head, hex_val, hex_h, fn,
                               cross_adj, diam_adj, hex_adj, h_adj,
                               shank_l, shank_d, facets)
                comment = (outfile + ' boltgen_gui'
                           + f' cr={cross_adj:.2f}'
                           + f' dia={diam_adj:.2f}'
                           + f' hex={hex_adj:.2f}')[:80]
                write_binary_stl(outfile, comment, facets)
                n = len(facets)
                def ok():
                    self._log(f'Written: {outfile}  ({n} facets)')
                    btn.config(state='normal')
                self.root.after(0, ok)
            except Exception as exc:
                msg = str(exc)
                def err():
                    self._log(f'Error: {msg}')
                    btn.config(state='normal')
                self.root.after(0, err)

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------- generate nut
    def _generate_nut(self):
        am_metric = self.nut_units.get() == 'mm'
        units_str = 'mm' if am_metric else 'in'
        diam_str  = self.nut_diam.get().strip()

        orig, bld = lookup_nut(am_metric, diam_str)
        if bld is None:
            messagebox.showerror('Error', f'Diameter "{diam_str}" not found.')
            return

        len_s       = self.nut_length.get().strip()
        length_orig = None
        length_mm   = None
        if len_s:
            try:
                length_orig = parse_length(len_s, am_metric)
            except Exception:
                messagebox.showerror('Error', f'Invalid length: "{len_s}"')
                return
            if length_orig <= 0:
                messagebox.showerror('Error', 'Length must be > 0.')
                return
            length_mm = length_orig if am_metric else length_orig * 25.4

        gen_length = length_mm if length_mm is not None else bld.hex_h

        try:
            pitch_mm = display_to_mm_pitch(self.nut_pitch.get().strip(), am_metric)
        except Exception:
            messagebox.showerror('Error', f'Invalid pitch: "{self.nut_pitch.get()}"')
            return

        # hex: mm for metric, inch fraction for imperial
        hex_str = self.nut_hex.get().strip()
        try:
            hex_val = parse_length(hex_str, am_metric)
            if not am_metric:
                hex_val *= 25.4
        except Exception:
            messagebox.showerror('Error', f'Invalid hex wrench size: "{hex_str}"')
            return
        min_hex = bld.diam + 0.5 + pitch_mm
        if hex_val < min_hex:
            messagebox.showerror('Error',
                f'Error: hex too small\nMinimum is {min_hex:.2f} mm')
            return

        try:
            fn = int(self.nut_fn.get().strip())
            assert fn > 0
        except Exception:
            messagebox.showerror('Error', 'fn must be a positive integer.')
            return

        try:
            diam_adj = float(self.nut_diam_adj.get().strip())
            hex_adj  = float(self.nut_hex_adj.get().strip())
        except Exception:
            messagebox.showerror('Error', 'Invalid adjustment value.')
            return

        threshold = pitch_mm * math.sqrt(3) / 2 + 0.1
        if bld.diam / 2 < threshold:
            messagebox.showerror('Error',
                f'Pitch too coarse for diameter.\n'
                f'diam={bld.diam:.4f} mm, pitch={pitch_mm:.4f} mm\n'
                f'Need diam/2={bld.diam/2:.4f} >= threshold={threshold:.4f}')
            return

        # Minimum nut length check (mirrors nutgen.py).
        w_hex = 0.2 * hex_val
        if gen_length < w_hex:
            messagebox.showerror('Error',
                f'Error: length too short for this diameter.\n'
                f'Minimum is {w_hex:.2f}')
            return

        # Nut threads are not chamfered — check thread length directly.
        min_thread = 2.5 * pitch_mm + 2 * pitch_mm / fn + 0.1
        if gen_length < min_thread:
            messagebox.showerror('Error', 'Error: length too short for the pitch')
            return

        outfile = self.nut_outfile.get().strip() or \
                  nut_fname(am_metric, units_str, bld, pitch_mm, length_orig)

        self._clear_log()
        if bld.am_interpolated:
            self._log('nut was interpolated')
        if self.nut_verbose.get() and orig is not None:
            self._log_print_vars(bld)
            self._log(f'  diam      : {orig.desc}  ({bld.diam:g} mm)')
            self._log(f'  length    : {gen_length:g} mm')
            self._log(f'  pitch     : {pitch_mm:g} mm')
            self._log(f'  hex       : {hex_val}')
            self._log(f'  fn        : {fn}')
            self._log(f'  diam_adj  : {diam_adj}')
            self._log(f'  hex_adj   : {hex_adj}')
        self._log(f'Generating {outfile} …')

        self.nut_btn.config(state='disabled')
        btn = self.nut_btn

        def run():
            try:
                facets = []
                generate_nut(am_metric, bld, pitch_mm, gen_length, hex_val,
                              fn, diam_adj, hex_adj, facets)
                comment = (outfile + ' boltgen_gui'
                           + f' diam_adj={diam_adj:.2f}'
                           + f' hex_adj={hex_adj:.2f}')[:80]
                write_binary_stl(outfile, comment, facets)
                n = len(facets)
                def ok():
                    self._log(f'Written: {outfile}  ({n} facets)')
                    btn.config(state='normal')
                self.root.after(0, ok)
            except Exception as exc:
                msg = str(exc)
                def err():
                    self._log(f'Error: {msg}')
                    btn.config(state='normal')
                self.root.after(0, err)

        threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------------------

def main():
    root = tk.Tk()
    BoltNutGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
