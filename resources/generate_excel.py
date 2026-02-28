"""
AL KABIR TOWER — Professional Opening Schedule Excel
All quantities & elevations extracted directly from DXF block geometry.

Classification (verified from building illustrations + DXF analysis):
  - Width < 800mm  → Top Hung Window (small bathroom/kitchen ventilation)
  - Width 800-1800mm → Fixed Window (non-operable glass panels on facade)
  - Width >= 1800mm → Sliding Window (horizontal sliding, 3P or 4P)
  - Doors: fm-door1 → Single Leaf Hinged, fm-door4 → Double Leaf Hinged

Elevation detection: annotation position within floor-plan block →
  closest edge determines facade (E1=Front, E2=Back, E3=Right, E4=Left).
"""
import sys, os, re, math
sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

import ezdxf
import xlsxwriter
from collections import Counter
from datetime import date

doc = ezdxf.readfile('resources/AL KABIR TOWER.dxf')
_DIM = re.compile(r'^(\d{2,4})\s*/\s*(\d{2,4})$')
_TURKISH_DIM_LAYERS = re.compile(r'(?i)(penc.?yaz|kap.?yaz|door.?text|do[gğ]rama)')

LOGO_PATH = 'resources/CompanyLogo.jpeg'

ELEV_NAMES = {'E1': 'Front', 'E2': 'Back', 'E3': 'Right', 'E4': 'Left'}

# ═══════════════════════════════════════════════════════════════════════
# DATA EXTRACTION — exact counts + elevations from DXF
# ═══════════════════════════════════════════════════════════════════════

msp_inserts = Counter()
for e in doc.modelspace():
    try:
        if e.dxftype() == 'INSERT':
            msp_inserts[e.dxf.name] += 1
    except:
        pass

RST_INSERTS = msp_inserts.get('RST FLOOR', 0)  # 9
LAST_INSERTS = msp_inserts.get('LAST', 0)       # 1

DOOR_H_CM = 220
_DOOR_DIM_LAYER = re.compile(r'(?i)kap.*yaz')

def classify_door(w_cm):
    """Classify door type from width in cm (architect's annotation)."""
    if w_cm >= 180:
        return 'Double Leaf Hinged Entrance Door'
    return 'Single Leaf Hinged Door'


def classify_window(w_cm):
    """Classify window type from width in cm."""
    w_mm = w_cm * 10
    if w_mm < 800:
        return 'Top Hung Window', 1, 'Top Hung'
    elif w_mm < 1800:
        return 'Fixed Window', 1, 'Fixed'
    elif w_mm >= 2400:
        return '4-Panel Sliding Window', 4, 'Horizontal Sliding'
    else:
        return '3-Panel Sliding Window', 3, 'Horizontal Sliding'


def detect_elevation(x, y, x_min, x_max, y_min, y_max):
    """Determine facade from annotation position within floor plan."""
    db = abs(y - y_min)  # E1 Front (bottom)
    dt = abs(y - y_max)  # E2 Back (top)
    dl = abs(x - x_min)  # E4 Left
    dr = abs(x - x_max)  # E3 Right
    md = min(db, dt, dl, dr)
    if md == db: return 'E1'
    if md == dt: return 'E2'
    if md == dr: return 'E3'
    return 'E4'


# ── Extract windows with type + elevation ──
# Key: (w_cm, h_cm, win_type, panels, mechanism)
# Value per block: count
window_classified = {}
# Elevation distribution: {block_name: {(w_cm, h_cm): {elev: count}}}
window_elevations = {}

door_per_block = {}

for block_name in ['RST FLOOR', 'LAST']:
    block = doc.blocks.get(block_name)
    if not block:
        continue

    # Get annotation positions for elevation detection
    ann_positions = []
    for e in block:
        try:
            if e.dxftype() == 'TEXT':
                layer = e.dxf.layer if hasattr(e.dxf, 'layer') else ''
                if _TURKISH_DIM_LAYERS.search(layer):
                    text = e.dxf.text.strip()
                    m = _DIM.match(text)
                    if m:
                        w, h = int(m.group(1)), int(m.group(2))
                        x, y = e.dxf.insert.x, e.dxf.insert.y
                        ann_positions.append((w, h, x, y))
        except:
            continue

    if not ann_positions:
        continue

    xs = [a[2] for a in ann_positions]
    ys = [a[3] for a in ann_positions]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    classified = []
    elev_dist = {}
    for w, h, x, y in ann_positions:
        win_type, panels, mechanism = classify_window(w)
        classified.append((w, h, win_type, panels, mechanism))

        elev = detect_elevation(x, y, x_min, x_max, y_min, y_max)
        key = (w, h)
        if key not in elev_dist:
            elev_dist[key] = Counter()
        elev_dist[key][elev] += 1

    window_classified[block_name] = Counter(classified)
    window_elevations[block_name] = elev_dist

    # Extract doors from kapi-yazi annotations (architect's stated dimensions)
    doors = []
    for e in block:
        try:
            if e.dxftype() == 'TEXT':
                layer = e.dxf.layer if hasattr(e.dxf, 'layer') else ''
                if _DOOR_DIM_LAYER.search(layer):
                    text = e.dxf.text.strip()
                    m = _DIM.match(text)
                    if m:
                        dw, dh = int(m.group(1)), int(m.group(2))
                        dtype = classify_door(dw)
                        doors.append((dw, dtype))
        except:
            continue
    door_per_block[block_name] = dict(Counter(doors))


# ── Build unified lists ──
all_window_keys = sorted(set(
    list(window_classified.get('RST FLOOR', {}).keys()) +
    list(window_classified.get('LAST', {}).keys())
), key=lambda x: (x[0], x[1], x[2]))

all_door_keys = sorted(set(
    list(door_per_block.get('RST FLOOR', {}).keys()) +
    list(door_per_block.get('LAST', {}).keys())
))

# ── Build elevation string for each window size ──
def elev_string(w, h):
    """Combine elevation info from both blocks."""
    parts = []
    for bn in ['RST FLOOR', 'LAST']:
        ed = window_elevations.get(bn, {}).get((w, h), {})
        for elev in sorted(ed.keys()):
            parts.append(f"{elev}\u00d7{ed[elev]}")
    return ', '.join(parts) if parts else ''


# ── Compute totals ──
total_win = sum(
    window_classified.get('RST FLOOR', {}).get(k, 0) * RST_INSERTS +
    window_classified.get('LAST', {}).get(k, 0) * LAST_INSERTS
    for k in all_window_keys
)
total_door = sum(
    door_per_block.get('RST FLOOR', {}).get(k, 0) * RST_INSERTS +
    door_per_block.get('LAST', {}).get(k, 0) * LAST_INSERTS
    for k in all_door_keys
)
total_all = total_win + total_door

win_area = sum(
    (k[0] * 10 * k[1] * 10 / 1e6) * (
        window_classified.get('RST FLOOR', {}).get(k, 0) * RST_INSERTS +
        window_classified.get('LAST', {}).get(k, 0) * LAST_INSERTS
    ) for k in all_window_keys
)
door_area = sum(
    (k[0] * 10 * DOOR_H_CM * 10 / 1e6) * (
        door_per_block.get('RST FLOOR', {}).get(k, 0) * RST_INSERTS +
        door_per_block.get('LAST', {}).get(k, 0) * LAST_INSERTS
    ) for k in all_door_keys
)


# ═══════════════════════════════════════════════════════════════════════
# EXCEL GENERATION
# ═══════════════════════════════════════════════════════════════════════
OUTPUT = 'resources/AL_KABIR_TOWER_Opening_Schedule.xlsx'
wb = xlsxwriter.Workbook(OUTPUT)

DARK_BLUE = '#1F4E79'; MED_BLUE = '#2E75B6'; LIGHT_BLUE = '#D6E4F0'
GREEN = '#548235'; ORANGE = '#C55A11'; PURPLE = '#7030A0'; TEAL = '#00B050'
LIGHT_GRAY = '#F2F2F2'; BORDER = '#B4C6E7'

def mkfmt(**kw):
    base = {'font_name': 'Calibri', 'font_size': 10, 'valign': 'vcenter'}
    base.update(kw)
    return wb.add_format(base)

fmt_title = mkfmt(bold=True, font_size=16, font_color=DARK_BLUE, bottom=2, bottom_color=DARK_BLUE)
fmt_subtitle = mkfmt(bold=True, font_size=11, font_color=MED_BLUE, italic=True)
fmt_hdr = mkfmt(bold=True, font_color='white', bg_color=DARK_BLUE, border=1,
                border_color=BORDER, text_wrap=True, align='center')
fmt_hdr_l = mkfmt(bold=True, font_color='white', bg_color=DARK_BLUE, border=1,
                  border_color=BORDER, text_wrap=True, align='left')
fmt_sec_g = mkfmt(bold=True, font_size=11, font_color='white', bg_color=GREEN, border=1, border_color=BORDER)
fmt_sec_o = mkfmt(bold=True, font_size=11, font_color='white', bg_color=ORANGE, border=1, border_color=BORDER)
fmt_sec_b = mkfmt(bold=True, font_size=11, font_color='white', bg_color=MED_BLUE, border=1, border_color=BORDER)
fmt_sec_t = mkfmt(bold=True, font_size=11, font_color='white', bg_color=TEAL, border=1, border_color=BORDER)
fmt_label = mkfmt(bold=True, font_color=DARK_BLUE, align='right')
fmt_val = mkfmt(bold=True)
fmt_note = mkfmt(italic=True, font_color='#666666', font_size=9, text_wrap=True)

def rf(bg=None, bold=False, nf=None, align='center'):
    p = {'border': 1, 'border_color': BORDER, 'align': align, 'font_name': 'Calibri', 'font_size': 10, 'valign': 'vcenter'}
    if bg: p['bg_color'] = bg
    if bold: p['bold'] = True
    if nf: p['num_format'] = nf
    return wb.add_format(p)

rw = rf(); rg = rf(bg=LIGHT_GRAY)
rw_l = rf(align='left'); rg_l = rf(bg=LIGHT_GRAY, align='left')
rw_n1 = rf(nf='0.0'); rg_n1 = rf(bg=LIGHT_GRAY, nf='0.0')
rw_n2 = rf(nf='0.00'); rg_n2 = rf(bg=LIGHT_GRAY, nf='0.00')
rw_i = rf(nf='#,##0'); rg_i = rf(bg=LIGHT_GRAY, nf='#,##0')
st = rf(bg=LIGHT_BLUE, bold=True); st_l = rf(bg=LIGHT_BLUE, bold=True, align='left')
st_i = rf(bg=LIGHT_BLUE, bold=True, nf='#,##0'); st_n1 = rf(bg=LIGHT_BLUE, bold=True, nf='0.0')
gt = rf(bg=DARK_BLUE, bold=True); gt_l = rf(bg=DARK_BLUE, bold=True, align='left')
gt_i = rf(bg=DARK_BLUE, bold=True, nf='#,##0'); gt_n1 = rf(bg=DARK_BLUE, bold=True, nf='0.0')
for f in [gt, gt_l, gt_i, gt_n1]:
    f.set_font_color('white')

def pick(i, a, b): return a if i % 2 == 0 else b

def add_logo(ws, row, col):
    if os.path.exists(LOGO_PATH):
        scale = 80 / 1024
        ws.insert_image(row, col, LOGO_PATH, {
            'x_scale': scale, 'y_scale': scale,
            'x_offset': 2, 'y_offset': 2, 'object_position': 1,
        })


# ═══════════════════════════════════════════════════════════════════════
# SHEET 1: PROJECT SUMMARY
# ═══════════════════════════════════════════════════════════════════════
ws = wb.add_worksheet('Project Summary')
ws.hide_gridlines(2); ws.set_tab_color(DARK_BLUE)
ws.set_column('A:A', 5); ws.set_column('B:B', 8); ws.set_column('C:C', 10)
ws.set_column('D:D', 10); ws.set_column('E:E', 10); ws.set_column('F:F', 30)
ws.set_column('G:G', 8); ws.set_column('H:H', 10); ws.set_column('I:I', 12)

r = 0; add_logo(ws, r, 1); r += 4
ws.merge_range(r, 1, r, 8, 'AL KABIR TOWER', fmt_title); r += 1
ws.merge_range(r, 1, r, 8, 'Facade Opening Schedule', fmt_subtitle); r += 2

for label, val in [
    ('Project:', 'AL KABIR TOWER'), ('Date:', str(date.today())),
    ('Drawing File:', 'AL KABIR TOWER.dxf'),
    ('Building Structure:', f'{RST_INSERTS} Typical Floors + {LAST_INSERTS} Last Floor'),
    ('Typical Floor Block:', f'RST FLOOR (\u00d7{RST_INSERTS} inserts)'),
    ('Last Floor Block:', f'LAST (\u00d7{LAST_INSERTS} insert)'),
]:
    ws.write(r, 1, label, fmt_label); ws.write(r, 2, val, fmt_val); r += 1

r += 1; ws.merge_range(r, 1, r, 4, 'SCHEDULE STATISTICS', fmt_sec_b); r += 1
for label, val in [
    ('Window Types:', len(all_window_keys)), ('Door Types:', len(all_door_keys)),
    ('Total Windows:', total_win), ('Total Doors:', total_door),
    ('Total Openings:', total_all),
    ('Window Area:', f'{win_area:.1f} m\u00b2'), ('Door Area:', f'{door_area:.1f} m\u00b2'),
    ('Total Facade Area:', f'{win_area + door_area:.1f} m\u00b2'),
]:
    ws.write(r, 1, label, fmt_label); ws.write(r, 2, str(val), fmt_val); r += 1

r += 1; ws.merge_range(r, 1, r, 9, 'ALL OPENINGS OVERVIEW', fmt_sec_b); r += 1
for c, h in enumerate(['#', 'Mark', 'Type', 'W (mm)', 'H (mm)', 'Configuration', 'Qty', 'Unit m\u00b2', 'Total m\u00b2']):
    ws.write(r, c, h, fmt_hdr if c >= 3 else fmt_hdr_l)
r += 1

idx = 1
for i, wk in enumerate(all_window_keys):
    w_cm, h_cm, win_type, panels, mechanism = wk
    qty = (window_classified.get('RST FLOOR', {}).get(wk, 0) * RST_INSERTS +
           window_classified.get('LAST', {}).get(wk, 0) * LAST_INSERTS)
    ua = w_cm * 10 * h_cm * 10 / 1e6; ta = ua * qty
    fl = pick(idx, rg, rw); fl_l = pick(idx, rg_l, rw_l)
    fl_i = pick(idx, rg_i, rw_i); fl_n1 = pick(idx, rg_n1, rw_n1); fl_n2 = pick(idx, rg_n2, rw_n2)
    ws.write(r, 0, idx, fl); ws.write(r, 1, f'W{idx:02d}', fl)
    ws.write(r, 2, 'Window', fl_l)
    ws.write(r, 3, w_cm*10, fl_i); ws.write(r, 4, h_cm*10, fl_i)
    ws.write(r, 5, f'{win_type} ({panels}P)', fl_l)
    ws.write(r, 6, qty, fl_i); ws.write(r, 7, round(ua, 2), fl_n2); ws.write(r, 8, round(ta, 1), fl_n1)
    r += 1; idx += 1

for i, (w_cm, dtype) in enumerate(all_door_keys):
    qty = (door_per_block.get('RST FLOOR', {}).get((w_cm, dtype), 0) * RST_INSERTS +
           door_per_block.get('LAST', {}).get((w_cm, dtype), 0) * LAST_INSERTS)

    ua = w_cm * 10 * DOOR_H_CM * 10 / 1e6; ta = ua * qty
    fl = pick(idx, rg, rw); fl_l = pick(idx, rg_l, rw_l)
    fl_i = pick(idx, rg_i, rw_i); fl_n1 = pick(idx, rg_n1, rw_n1); fl_n2 = pick(idx, rg_n2, rw_n2)
    ws.write(r, 0, idx, fl); ws.write(r, 1, f'D{i+1:02d}', fl)
    ws.write(r, 2, 'Door', fl_l)
    ws.write(r, 3, w_cm*10, fl_i); ws.write(r, 4, DOOR_H_CM*10, fl_i)
    ws.write(r, 5, dtype, fl_l)
    ws.write(r, 6, qty, fl_i); ws.write(r, 7, round(ua, 2), fl_n2); ws.write(r, 8, round(ta, 1), fl_n1)
    r += 1; idx += 1

for c in range(9): ws.write(r, c, '', gt)
ws.write(r, 2, 'GRAND TOTAL', gt_l); ws.write(r, 6, total_all, gt_i)
ws.write(r, 8, round(win_area + door_area, 1), gt_n1)


# ═══════════════════════════════════════════════════════════════════════
# SHEET 2: WINDOW SCHEDULE (with elevation)
# ═══════════════════════════════════════════════════════════════════════
ws2 = wb.add_worksheet('Window Schedule')
ws2.set_tab_color(MED_BLUE); ws2.freeze_panes(5, 0)
ws2.set_column('A:A', 5); ws2.set_column('B:B', 8); ws2.set_column('C:C', 10)
ws2.set_column('D:D', 10); ws2.set_column('E:E', 28); ws2.set_column('F:F', 8)
ws2.set_column('G:G', 18); ws2.set_column('H:H', 22)
ws2.set_column('I:I', 14); ws2.set_column('J:J', 14)
ws2.set_column('K:K', 10); ws2.set_column('L:L', 10); ws2.set_column('M:M', 12)

r = 0; add_logo(ws2, r, 0); r += 3
ws2.merge_range(r, 0, r, 12, 'AL KABIR TOWER \u2014 Window Schedule', fmt_title); r += 1
ws2.merge_range(r, 0, r, 12,
    'Elevations: E1=Front, E2=Back, E3=Right Side, E4=Left Side',
    fmt_note); r += 1

hdrs = ['#', 'Mark', 'W (mm)', 'H (mm)', 'Configuration', 'Panels', 'Mechanism',
        'Elevation\n(per block)',
        f'Per Floor\n(Typical \u00d7{RST_INSERTS})',
        f'Per Floor\n(Last \u00d7{LAST_INSERTS})', 'Total\nQty',
        'Unit m\u00b2', 'Total m\u00b2']
for c, h in enumerate(hdrs):
    ws2.write(r, c, h, fmt_hdr if c >= 2 else fmt_hdr_l)
ws2.set_row(r, 36); r += 1

rst_win_total = sum(window_classified.get('RST FLOOR', {}).values())
last_win_total = sum(window_classified.get('LAST', {}).values())

for i, wk in enumerate(all_window_keys):
    w_cm, h_cm, win_type, panels, mechanism = wk
    rst_pf = window_classified.get('RST FLOOR', {}).get(wk, 0)
    last_pf = window_classified.get('LAST', {}).get(wk, 0)
    total = rst_pf * RST_INSERTS + last_pf * LAST_INSERTS
    ua = w_cm * 10 * h_cm * 10 / 1e6; ta = ua * total
    ev = elev_string(w_cm, h_cm)

    fl = pick(i, rg, rw); fl_l = pick(i, rg_l, rw_l); fl_i = pick(i, rg_i, rw_i)
    fl_n2 = pick(i, rg_n2, rw_n2); fl_n1 = pick(i, rg_n1, rw_n1)

    ws2.write(r, 0, i+1, fl); ws2.write(r, 1, f'W{i+1:02d}', fl)
    ws2.write(r, 2, w_cm*10, fl_i); ws2.write(r, 3, h_cm*10, fl_i)
    ws2.write(r, 4, win_type, fl_l); ws2.write(r, 5, panels, fl)
    ws2.write(r, 6, mechanism, fl_l); ws2.write(r, 7, ev, fl_l)
    ws2.write(r, 8, rst_pf if rst_pf > 0 else '', fl)
    ws2.write(r, 9, last_pf if last_pf > 0 else '', fl)
    ws2.write(r, 10, total, fl_i)
    ws2.write(r, 11, round(ua, 2), fl_n2); ws2.write(r, 12, round(ta, 1), fl_n1)
    r += 1

for c in range(13): ws2.write(r, c, '', st)
ws2.write(r, 4, 'WINDOW SUBTOTAL', st_l)
ws2.write(r, 8, rst_win_total, st_i); ws2.write(r, 9, last_win_total, st_i)
ws2.write(r, 10, total_win, st_i); ws2.write(r, 12, round(win_area, 1), st_n1)


# ═══════════════════════════════════════════════════════════════════════
# SHEET 3: DOOR SCHEDULE
# ═══════════════════════════════════════════════════════════════════════
ws3 = wb.add_worksheet('Door Schedule')
ws3.set_tab_color(ORANGE); ws3.freeze_panes(4, 0)
ws3.set_column('A:A', 5); ws3.set_column('B:B', 8); ws3.set_column('C:C', 10)
ws3.set_column('D:D', 10); ws3.set_column('E:E', 36)
ws3.set_column('F:F', 14); ws3.set_column('G:G', 14)
ws3.set_column('H:H', 10); ws3.set_column('I:I', 10); ws3.set_column('J:J', 12)

r = 0; add_logo(ws3, r, 0); r += 3
ws3.merge_range(r, 0, r, 9, 'AL KABIR TOWER \u2014 Door Schedule', fmt_title); r += 1

for c, h in enumerate(['#', 'Mark', 'W (mm)', 'H (mm)', 'Door Type',
        f'Per Floor\n(Typical \u00d7{RST_INSERTS})',
        f'Per Floor\n(Last \u00d7{LAST_INSERTS})', 'Total\nQty', 'Unit m\u00b2', 'Total m\u00b2']):
    ws3.write(r, c, h, fmt_hdr if c >= 2 else fmt_hdr_l)
ws3.set_row(r, 32); r += 1

rst_door_total = sum(door_per_block.get('RST FLOOR', {}).values())
last_door_total = sum(door_per_block.get('LAST', {}).values())

for i, (w_cm, dtype) in enumerate(all_door_keys):
    rst_pf = door_per_block.get('RST FLOOR', {}).get((w_cm, dtype), 0)
    last_pf = door_per_block.get('LAST', {}).get((w_cm, dtype), 0)
    total = rst_pf * RST_INSERTS + last_pf * LAST_INSERTS

    ua = w_cm * 10 * DOOR_H_CM * 10 / 1e6; ta = ua * total

    fl = pick(i, rg, rw); fl_l = pick(i, rg_l, rw_l); fl_i = pick(i, rg_i, rw_i)
    fl_n2 = pick(i, rg_n2, rw_n2); fl_n1 = pick(i, rg_n1, rw_n1)
    ws3.write(r, 0, i+1, fl); ws3.write(r, 1, f'D{i+1:02d}', fl)
    ws3.write(r, 2, w_cm*10, fl_i); ws3.write(r, 3, DOOR_H_CM*10, fl_i)
    ws3.write(r, 4, dtype, fl_l)
    ws3.write(r, 5, rst_pf if rst_pf > 0 else '', fl)
    ws3.write(r, 6, last_pf if last_pf > 0 else '', fl)
    ws3.write(r, 7, total, fl_i); ws3.write(r, 8, round(ua, 2), fl_n2)
    ws3.write(r, 9, round(ta, 1), fl_n1)
    r += 1

for c in range(10): ws3.write(r, c, '', st)
ws3.write(r, 4, 'DOOR SUBTOTAL', st_l)
ws3.write(r, 5, rst_door_total, st_i); ws3.write(r, 6, last_door_total, st_i)
ws3.write(r, 7, total_door, st_i); ws3.write(r, 9, round(door_area, 1), st_n1)


# ═══════════════════════════════════════════════════════════════════════
# SHEET 4: PER-FLOOR BREAKDOWN
# ═══════════════════════════════════════════════════════════════════════
ws4 = wb.add_worksheet('Per-Floor Breakdown')
ws4.set_tab_color(GREEN); ws4.freeze_panes(5, 5)
floor_names = [f'Floor {i}' for i in range(1, RST_INSERTS + 1)] + ['Last Floor']
nf = len(floor_names)
ws4.set_column('A:A', 5); ws4.set_column('B:B', 8)
ws4.set_column('C:C', 28); ws4.set_column('D:D', 10); ws4.set_column('E:E', 10)
for c in range(nf): ws4.set_column(5+c, 5+c, 9)
ws4.set_column(5+nf, 5+nf, 10)
DC = 5

r = 0; add_logo(ws4, r, 0); r += 3
ws4.merge_range(r, 0, r, DC+nf, 'AL KABIR TOWER \u2014 Per-Floor Opening Breakdown', fmt_title); r += 1
for c, h in enumerate(['#', 'Mark', 'Type / Configuration', 'W (mm)', 'H (mm)'] + floor_names + ['TOTAL']):
    ws4.write(r, c, h, fmt_hdr)
ws4.set_row(r, 24); r += 1

ws4.merge_range(r, 0, r, DC+nf, 'WINDOWS', fmt_sec_g); r += 1
win_pf = [0] * nf; idx = 1
for i, wk in enumerate(all_window_keys):
    w_cm, h_cm, win_type, panels, mechanism = wk
    rst_pf = window_classified.get('RST FLOOR', {}).get(wk, 0)
    last_pf = window_classified.get('LAST', {}).get(wk, 0)
    fl = pick(i, rg, rw); fl_l = pick(i, rg_l, rw_l); fl_i = pick(i, rg_i, rw_i)
    ws4.write(r, 0, idx, fl); ws4.write(r, 1, f'W{idx:02d}', fl)
    ws4.write(r, 2, win_type, fl_l)
    ws4.write(r, 3, w_cm*10, fl_i); ws4.write(r, 4, h_cm*10, fl_i)
    rt = 0
    for fc in range(RST_INSERTS):
        ws4.write(r, DC+fc, rst_pf if rst_pf > 0 else '', fl); rt += rst_pf; win_pf[fc] += rst_pf
    ws4.write(r, DC+RST_INSERTS, last_pf if last_pf > 0 else '', fl)
    rt += last_pf; win_pf[RST_INSERTS] += last_pf
    ws4.write(r, DC+nf, rt, fl_i); r += 1; idx += 1

for c in range(DC+nf+1): ws4.write(r, c, '', st)
ws4.write(r, 2, 'Window Subtotal', st_l)
for fc in range(nf): ws4.write(r, DC+fc, win_pf[fc] if win_pf[fc] else '', st_i)
ws4.write(r, DC+nf, total_win, st_i); r += 1

ws4.merge_range(r, 0, r, DC+nf, 'DOORS', fmt_sec_o); r += 1
door_pf = [0] * nf
for i, (w_cm, dtype) in enumerate(all_door_keys):
    rst_pf = door_per_block.get('RST FLOOR', {}).get((w_cm, dtype), 0)
    last_pf = door_per_block.get('LAST', {}).get((w_cm, dtype), 0)

    fl = pick(i, rg, rw); fl_l = pick(i, rg_l, rw_l); fl_i = pick(i, rg_i, rw_i)
    ws4.write(r, 0, idx, fl); ws4.write(r, 1, f'D{i+1:02d}', fl)
    ws4.write(r, 2, dtype, fl_l)
    ws4.write(r, 3, w_cm*10, fl_i); ws4.write(r, 4, DOOR_H_CM*10, fl_i)
    rt = 0
    for fc in range(RST_INSERTS):
        ws4.write(r, DC+fc, rst_pf if rst_pf else '', fl); rt += rst_pf; door_pf[fc] += rst_pf
    ws4.write(r, DC+RST_INSERTS, last_pf if last_pf else '', fl)
    rt += last_pf; door_pf[RST_INSERTS] += last_pf
    ws4.write(r, DC+nf, rt, fl_i); r += 1; idx += 1

for c in range(DC+nf+1): ws4.write(r, c, '', st)
ws4.write(r, 2, 'Door Subtotal', st_l)
for fc in range(nf): ws4.write(r, DC+fc, door_pf[fc] if door_pf[fc] else '', st_i)
ws4.write(r, DC+nf, total_door, st_i); r += 1

for c in range(DC+nf+1): ws4.write(r, c, '', gt)
ws4.write(r, 2, 'GRAND TOTAL', gt_l)
for fc in range(nf): ws4.write(r, DC+fc, win_pf[fc]+door_pf[fc], gt_i)
ws4.write(r, DC+nf, total_all, gt_i)


# ═══════════════════════════════════════════════════════════════════════
# SHEET 5: AREA SUMMARY
# ═══════════════════════════════════════════════════════════════════════
ws5 = wb.add_worksheet('Area Summary')
ws5.set_tab_color(PURPLE); ws5.hide_gridlines(2)
ws5.set_column('A:A', 5); ws5.set_column('B:B', 8); ws5.set_column('C:C', 30)
ws5.set_column('D:D', 10); ws5.set_column('E:E', 10); ws5.set_column('F:F', 12)
ws5.set_column('G:G', 8); ws5.set_column('H:H', 12)

r = 0; add_logo(ws5, r, 0); r += 4
ws5.merge_range(r, 0, r, 7, 'AL KABIR TOWER \u2014 Facade Area Summary', fmt_title); r += 2
for c, h in enumerate(['#', 'Mark', 'Opening', 'W (mm)', 'H (mm)', 'Unit m\u00b2', 'Qty', 'Total m\u00b2']):
    ws5.write(r, c, h, fmt_hdr if c >= 3 else fmt_hdr_l)
r += 1

ws5.merge_range(r, 0, r, 7, f'WINDOWS ({len(all_window_keys)} types, {total_win} units)', fmt_sec_g); r += 1
wc = 0
for i, wk in enumerate(all_window_keys):
    w_cm, h_cm, win_type, panels, mechanism = wk
    qty = (window_classified.get('RST FLOOR', {}).get(wk, 0) * RST_INSERTS +
           window_classified.get('LAST', {}).get(wk, 0) * LAST_INSERTS)
    ua = w_cm*10*h_cm*10/1e6; ta = round(ua*qty, 1); wc += ta
    fl = pick(i, rg, rw); fl_l = pick(i, rg_l, rw_l)
    fl_n2 = pick(i, rg_n2, rw_n2); fl_n1 = pick(i, rg_n1, rw_n1); fl_i = pick(i, rg_i, rw_i)
    ws5.write(r, 0, i+1, fl); ws5.write(r, 1, f'W{i+1:02d}', fl)
    ws5.write(r, 2, win_type, fl_l)
    ws5.write(r, 3, w_cm*10, fl_i); ws5.write(r, 4, h_cm*10, fl_i)
    ws5.write(r, 5, round(ua, 2), fl_n2); ws5.write(r, 6, qty, fl_i)
    ws5.write(r, 7, ta, fl_n1); r += 1

for c in range(8): ws5.write(r, c, '', st)
ws5.write(r, 2, 'WINDOW SUBTOTAL', st_l)
ws5.write(r, 6, total_win, st_i); ws5.write(r, 7, round(wc, 1), st_n1); r += 1

ws5.merge_range(r, 0, r, 7, f'DOORS ({len(all_door_keys)} types, {total_door} units)', fmt_sec_o); r += 1
dc = 0
for i, (w_cm, dtype) in enumerate(all_door_keys):
    qty = (door_per_block.get('RST FLOOR', {}).get((w_cm, dtype), 0) * RST_INSERTS +
           door_per_block.get('LAST', {}).get((w_cm, dtype), 0) * LAST_INSERTS)
    ua = w_cm*10*DOOR_H_CM*10/1e6; ta = round(ua*qty, 1); dc += ta

    fl = pick(i, rg, rw); fl_l = pick(i, rg_l, rw_l)
    fl_n2 = pick(i, rg_n2, rw_n2); fl_n1 = pick(i, rg_n1, rw_n1); fl_i = pick(i, rg_i, rw_i)
    ws5.write(r, 0, len(all_window_keys)+i+1, fl); ws5.write(r, 1, f'D{i+1:02d}', fl)
    ws5.write(r, 2, dtype, fl_l)
    ws5.write(r, 3, w_cm*10, fl_i); ws5.write(r, 4, DOOR_H_CM*10, fl_i)
    ws5.write(r, 5, round(ua, 2), fl_n2); ws5.write(r, 6, qty, fl_i)
    ws5.write(r, 7, ta, fl_n1); r += 1

for c in range(8): ws5.write(r, c, '', st)
ws5.write(r, 2, 'DOOR SUBTOTAL', st_l)
ws5.write(r, 6, total_door, st_i); ws5.write(r, 7, round(dc, 1), st_n1); r += 1
for c in range(8): ws5.write(r, c, '', gt)
ws5.write(r, 2, 'GRAND TOTAL FACADE AREA', gt_l)
ws5.write(r, 6, total_all, gt_i); ws5.write(r, 7, round(wc+dc, 1), gt_n1)


# ═══════════════════════════════════════════════════════════════════════
# SHEET 6: QUANTITY VERIFICATION
# ═══════════════════════════════════════════════════════════════════════
ws6 = wb.add_worksheet('Quantity Verification')
ws6.set_tab_color(TEAL); ws6.hide_gridlines(2)
ws6.set_column('A:A', 3); ws6.set_column('B:B', 30); ws6.set_column('C:C', 16)
ws6.set_column('D:D', 12); ws6.set_column('E:E', 12); ws6.set_column('F:F', 12)
ws6.set_column('G:G', 12); ws6.set_column('H:H', 12); ws6.set_column('I:I', 12)

r = 0; add_logo(ws6, r, 1); r += 4
ws6.merge_range(r, 1, r, 8, 'AL KABIR TOWER \u2014 Quantity Verification (Audit Trail)', fmt_title); r += 1
ws6.merge_range(r, 1, r, 8, 'Every quantity = (per-block count) \u00d7 (block inserts in modelspace)', fmt_subtitle); r += 2

for c, h in enumerate(['Opening', 'Source Block', 'Per Block', '\u00d7', 'Inserts', '=', 'Subtotal', 'Total']):
    ws6.write(r, c+1, h, fmt_hdr)
r += 1; ws6.merge_range(r, 1, r, 8, 'WINDOWS', fmt_sec_g); r += 1

for i, wk in enumerate(all_window_keys):
    w_cm, h_cm, win_type, panels, mechanism = wk
    rst_pf = window_classified.get('RST FLOOR', {}).get(wk, 0)
    last_pf = window_classified.get('LAST', {}).get(wk, 0)
    fl = pick(i, rg, rw); fl_l = pick(i, rg_l, rw_l); fl_i = pick(i, rg_i, rw_i)
    label = f'{win_type} {w_cm*10}\u00d7{h_cm*10}mm'
    ws6.write(r, 1, label, fl_l); ws6.write(r, 2, 'RST FLOOR', fl_l)
    ws6.write(r, 3, rst_pf, fl); ws6.write(r, 4, '\u00d7', fl)
    ws6.write(r, 5, RST_INSERTS, fl); ws6.write(r, 6, '=', fl)
    ws6.write(r, 7, rst_pf * RST_INSERTS, fl_i); ws6.write(r, 8, '', fl); r += 1
    ws6.write(r, 1, '', fl_l); ws6.write(r, 2, 'LAST', fl_l)
    ws6.write(r, 3, last_pf, fl); ws6.write(r, 4, '\u00d7', fl)
    ws6.write(r, 5, LAST_INSERTS, fl); ws6.write(r, 6, '=', fl)
    ws6.write(r, 7, last_pf * LAST_INSERTS, fl_i)
    ws6.write(r, 8, rst_pf * RST_INSERTS + last_pf * LAST_INSERTS, st_i); r += 1

for c in range(1, 9): ws6.write(r, c, '', st)
ws6.write(r, 1, 'WINDOW TOTAL', st_l); ws6.write(r, 8, total_win, st_i); r += 1

ws6.merge_range(r, 1, r, 8, 'DOORS', fmt_sec_o); r += 1
for i, (w_cm, dtype) in enumerate(all_door_keys):
    rst_pf = door_per_block.get('RST FLOOR', {}).get((w_cm, dtype), 0)
    last_pf = door_per_block.get('LAST', {}).get((w_cm, dtype), 0)
    fl = pick(i, rg, rw); fl_l = pick(i, rg_l, rw_l); fl_i = pick(i, rg_i, rw_i)
    ws6.write(r, 1, f'{dtype} {w_cm*10}mm', fl_l); ws6.write(r, 2, 'RST FLOOR', fl_l)
    ws6.write(r, 3, rst_pf, fl); ws6.write(r, 4, '\u00d7', fl)
    ws6.write(r, 5, RST_INSERTS, fl); ws6.write(r, 6, '=', fl)
    ws6.write(r, 7, rst_pf * RST_INSERTS, fl_i); ws6.write(r, 8, '', fl); r += 1
    ws6.write(r, 1, '', fl_l); ws6.write(r, 2, 'LAST', fl_l)
    ws6.write(r, 3, last_pf, fl); ws6.write(r, 4, '\u00d7', fl)
    ws6.write(r, 5, LAST_INSERTS, fl); ws6.write(r, 6, '=', fl)
    ws6.write(r, 7, last_pf * LAST_INSERTS, fl_i)
    ws6.write(r, 8, rst_pf * RST_INSERTS + last_pf * LAST_INSERTS, st_i); r += 1

for c in range(1, 9): ws6.write(r, c, '', st)
ws6.write(r, 1, 'DOOR TOTAL', st_l); ws6.write(r, 8, total_door, st_i); r += 1
for c in range(1, 9): ws6.write(r, c, '', gt)
ws6.write(r, 1, 'GRAND TOTAL ALL OPENINGS', gt_l); ws6.write(r, 8, total_all, gt_i)


wb.close()
print(f'Generated: {OUTPUT}')
print(f'  6 sheets with company logo + elevation data')
print(f'  Windows: {len(all_window_keys)} types, {total_win} units, {win_area:.1f} m\u00b2')
print(f'  Doors: {len(all_door_keys)} types, {total_door} units, {door_area:.1f} m\u00b2')
print(f'  Grand total: {total_all} openings, {win_area + door_area:.1f} m\u00b2')
print()
print('Window type breakdown:')
for wk in all_window_keys:
    w_cm, h_cm, win_type, panels, mechanism = wk
    rst = window_classified.get('RST FLOOR', {}).get(wk, 0)
    last = window_classified.get('LAST', {}).get(wk, 0)
    total = rst * RST_INSERTS + last * LAST_INSERTS
    ev = elev_string(w_cm, h_cm)
    print(f'  {w_cm*10:>5}x{h_cm*10:<5} {win_type:<30s} RST:{rst}/blk LAST:{last}/blk = {total:>3}  [{ev}]')
