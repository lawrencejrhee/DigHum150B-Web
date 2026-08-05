#!/usr/bin/env python3
"""Final project: regenerate every number and figure from the source data.

Reads the FAO-derived datasets committed in assets/data/ and rebuilds:
  assets/data/final/convergence.csv       dispersion by two methods, yearly
  assets/data/final/anchor-distances.csv  distance to four 1961 anchor plates
  assets/data/final/plates.csv            twelve countries, five food groups
  assets/data/final/calorie-gap.csv       best and worst fed country, yearly
  assets/images/final-plates.svg          the plates figure
  assets/images/final-calorie-gap.svg     the unequal portion figure
  assets/images/final-anchors.svg         the directional test figure

Run from anywhere: python scripts/final-project-analysis.py
"""
import csv, math, os, statistics as st
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "assets", "data")
OUT = os.path.join(DATA, "final")
IMG = os.path.join(ROOT, "assets", "images")
os.makedirs(OUT, exist_ok=True)

CATS = ['other','alcoholic_beverages','sugar','oils_and_fats','meat','dairy_and_eggs',
        'fruits_and_vegetables','starchy_roots','pulses','cereals_and_grains']

def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None

rows = list(csv.DictReader(open(os.path.join(DATA, "dietary-composition.csv"),
                                encoding="utf-8", errors="replace")))
D = defaultdict(dict)      # country -> year -> (composition shares, total kcal)
for r in rows:
    c = (r["code"] or "").strip()
    if len(c) != 3 or c.startswith("OWID"): continue
    v = [num(r[k]) for k in CATS]
    if any(x is None for x in v): continue
    t = sum(v)
    if t > 0:
        D[r["entity"]][int(r["year"])] = ([x/t for x in v], t)

YEARS = list(range(1961, 2024))
BAL = [e for e in D if all(y in D[e] for y in YEARS)]
print(f"balanced panel: {len(BAL)} countries")

# ---------------- convergence, two methods --------------------------------
def euclid_disp(year, countries):
    V = [D[e][year][0] for e in countries]
    n = len(V); m = [sum(v[i] for v in V)/n for i in range(len(CATS))]
    return st.mean(math.dist(v, m) for v in V)

def cosine_pairwise(year, countries):
    V = [D[e][year][0] for e in countries]
    tot = 0.0; cnt = 0
    for i in range(len(V)):
        vi = V[i]; ni = math.sqrt(sum(x*x for x in vi))
        for j in range(i+1, len(V)):
            vj = V[j]; nj = math.sqrt(sum(x*x for x in vj))
            tot += 1 - sum(a*b for a, b in zip(vi, vj))/(ni*nj); cnt += 1
    return tot/cnt

conv = []
for y in YEARS:
    allc = [e for e in D if y in D[e]]
    conv.append((y, euclid_disp(y, allc), euclid_disp(y, BAL), cosine_pairwise(y, BAL)))
print(f"euclid all:  {conv[0][1]:.4f} -> {conv[-1][1]:.4f} ({(conv[-1][1]/conv[0][1]-1)*100:+.1f}%)")
print(f"euclid bal:  {conv[0][2]:.4f} -> {conv[-1][2]:.4f} ({(conv[-1][2]/conv[0][2]-1)*100:+.1f}%)")
print(f"cosine bal:  {conv[0][3]:.4f} -> {conv[-1][3]:.4f} ({(conv[-1][3]/conv[0][3]-1)*100:+.1f}%)")

with open(os.path.join(OUT, "convergence.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["year","dispersion_all_countries","dispersion_balanced_panel","cosine_distance_balanced"])
    for y, a, b, c in conv: w.writerow([y, round(a,4), round(b,4), round(c,4)])

# ---------------- four 1961 anchors, yearly -------------------------------
ANCH = {"Western": ["United States","United Kingdom","France","Germany","Australia","Canada"],
        "South Asian": ["India","Pakistan","Bangladesh","Sri Lanka","Nepal"],
        "West African": ["Nigeria","Ghana","Senegal","Mali","Burkina Faso"],
        "East Asian": ["Japan","South Korea","China","Thailand","Philippines"]}
profiles = {}
for name, mem in ANCH.items():
    ref = [D[c][1961][0] for c in mem if c in D and 1961 in D[c]]
    profiles[name] = [sum(r[i] for r in ref)/len(ref) for i in range(len(CATS))]
anch_rows = []
for y in YEARS:
    anch_rows.append([y] + [round(st.mean(math.dist(D[e][y][0], profiles[n]) for e in BAL), 4)
                            for n in ANCH])
with open(os.path.join(OUT, "anchor-distances.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["year"] + [f"distance_to_{n.lower().replace(' ','_')}_1961_plate" for n in ANCH])
    for r in anch_rows: w.writerow(r)
for i, name in enumerate(ANCH):
    a, b = anch_rows[0][i+1], anch_rows[-1][i+1]
    print(f"anchor {name:<13} {a:.4f} -> {b:.4f} ({(b/a-1)*100:+.1f}%)")

# ---------------- twelve plates -------------------------------------------
GROUPS = {"Staple plants": ["cereals_and_grains","starchy_roots","pulses"],
          "Oils and sugar": ["oils_and_fats","sugar"],
          "Meat, dairy, eggs": ["meat","dairy_and_eggs"],
          "Fruits and vegetables": ["fruits_and_vegetables"],
          "Alcohol and other": ["alcoholic_beverages","other"]}
PLATES = ["United States","United Kingdom","France","Japan","South Korea","China",
          "Brazil","Mexico","Egypt","India","Nigeria","Senegal"]
def grouped(e, y):
    sh = D[e][y][0]
    return [sum(sh[CATS.index(c)] for c in members) for members in GROUPS.values()]
def last_year(e):
    return max(y for y in D[e] if y <= 2023)
with open(os.path.join(OUT, "plates.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["country","year"] + list(GROUPS))
    for e in PLATES:
        for y in (1961, last_year(e)):
            w.writerow([e, y] + [round(x*100,1) for x in grouped(e, y)])

# ---------------- calorie gap ---------------------------------------------
crows = list(csv.DictReader(open(os.path.join(DATA, "daily-calorie-supply.csv"),
                                 encoding="utf-8", errors="replace")))
K = defaultdict(dict)
for r in crows:
    c = (r["code"] or "").strip()
    if len(c) != 3 or c.startswith("OWID"): continue
    v = num(r["daily_calories"])
    if v and r["year"].isdigit(): K[r["entity"]][int(r["year"])] = v
KB = [e for e in K if all(y in K[e] for y in YEARS)]
gap = []
for y in YEARS:
    vals = sorted((K[e][y], e) for e in KB)
    lo, hi = vals[0], vals[-1]
    gap.append((y, round(hi[0]), hi[1], round(lo[0]), lo[1], round(hi[0]/lo[0],2)))
with open(os.path.join(OUT, "calorie-gap.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["year","highest_kcal","highest_country","lowest_kcal","lowest_country","ratio"])
    for r in gap: w.writerow(r)
print(f"calorie gap ratio: {gap[0][5]} (1961) -> {gap[-1][5]} (2023)")


# ---------------- figure: toward whose plate ------------------------------
a2 = [(int(r["year"]), float(r["distance_to_western_1961_plate"]),
       float(r["distance_to_south_asian_1961_plate"]),
       float(r["distance_to_west_african_1961_plate"]),
       float(r["distance_to_east_asian_1961_plate"]))
      for r in csv.DictReader(open(os.path.join(OUT, "anchor-distances.csv"), encoding="utf-8"))]
W, H = 1128, 640; padL, padR, padT, padB = 96, 300, 120, 70
pw, ph = W-padL-padR, H-padT-padB
Y0, Y1 = 1961, 2023; V0, V1 = 0.20, 0.37
X = lambda y: padL + (y-Y0)/(Y1-Y0)*pw
Y = lambda v: padT + (V1-v)/(V1-V0)*ph
SER = [("Western 1961 plate", 1, "#2b50e0", 3.4, "", "down 30 percent"),
       ("South Asian 1961 plate", 2, "#d1477a", 2.2, "6 4", "up 15 percent"),
       ("East Asian 1961 plate", 4, "#e0862b", 2.2, "6 4", "up 14 percent"),
       ("West African 1961 plate", 3, "#12a594", 2.2, "6 4", "flat")]
s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
     f'aria-label="Line chart from 1961 to 2023 of the average distance between the diets of 133 countries and four reference plates fixed at their 1961 composition. Distance to the Western plate falls 30 percent, the only line that falls substantially. Distance to the South Asian and East Asian plates rises about 15 percent and distance to the West African plate stays flat. The world moved toward one plate and away from the others.">']
s.append("""<style>
 .bg{fill:#ffffff}
 .t{fill:#0f141c;font:700 26px system-ui,-apple-system,Segoe UI,sans-serif}
 .sub{fill:#586170;font:15px system-ui,-apple-system,Segoe UI,sans-serif}
 .grid{stroke:#e6ebf3;stroke-width:1}.axis{stroke:#c7d0dc;stroke-width:1.2}
 .tick{fill:#5b6470;font:13px system-ui,-apple-system,Segoe UI,sans-serif}
 .end{font:600 14.5px system-ui,-apple-system,Segoe UI,sans-serif}
 .endv{fill:#586170;font:13px system-ui,-apple-system,Segoe UI,sans-serif}
 .src{fill:#8b94a3;font:12px system-ui,-apple-system,Segoe UI,sans-serif}
 @media (prefers-color-scheme:dark){.bg{fill:#0f141c}.t{fill:#e7eef7}.sub{fill:#94a1b2}
 .grid{stroke:#223047}.axis{stroke:#33415a}.tick{fill:#94a1b2}.endv{fill:#94a1b2}.src{fill:#6b7688}}
</style>""")
s.append(f'<rect class="bg" width="{W}" height="{H}" rx="12"/>')
s.append(f'<text class="t" x="{padL}" y="44">Toward whose plate?</text>')
s.append(f'<text class="sub" x="{padL}" y="72">Average distance of the diets of 133 countries from four plates frozen at their 1961 composition</text>')
for v in (0.20, 0.25, 0.30, 0.35):
    s.append(f'<line class="grid" x1="{padL}" y1="{Y(v):.1f}" x2="{W-padR}" y2="{Y(v):.1f}"/>')
    s.append(f'<text class="tick" x="{padL-10}" y="{Y(v)+4:.1f}" text-anchor="end">{v:.2f}</text>')
for name, idx, col, wdt, dash, verdict in SER:
    pts = " ".join(f"{X(r[0]):.1f},{Y(r[idx]):.1f}" for r in a2)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    s.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="{wdt}"{d} stroke-linejoin="round"/>')
    last = a2[-1]
    s.append(f'<circle cx="{X(last[0]):.1f}" cy="{Y(last[idx]):.1f}" r="5" fill="{col}"/>')
    s.append(f'<text class="end" x="{W-padR+12}" y="{Y(last[idx])+1:.1f}" fill="{col}">{name}</text>')
    s.append(f'<text class="endv" x="{W-padR+12}" y="{Y(last[idx])+19:.1f}">{verdict}</text>')
for y in (1961, 1980, 2000, 2023):
    s.append(f'<text class="tick" x="{X(y):.1f}" y="{H-padB+22}" text-anchor="middle">{y}</text>')
s.append(f'<line class="axis" x1="{padL}" y1="{H-padB}" x2="{W-padR}" y2="{H-padB}"/>')
s.append(f'<text class="src" x="{padL}" y="{H-20}">Balanced panel of 133 countries. Distance is euclidean distance between ten part compositions of daily calorie supply.</text>')
s.append('</svg>')
open(os.path.join(IMG, "final-anchors.svg"), "w", encoding="utf-8").write("\n".join(s))
print("final-anchors.svg written")

# ---------------- figure: twelve plates -----------------------------------
GCOL = ["#8a7a4e","#e0862b","#d1477a","#12a594","#8b94a3"]
GNAMES = list(GROUPS)
pl = list(csv.DictReader(open(os.path.join(OUT, "plates.csv"), encoding="utf-8")))
PD = defaultdict(dict); order = []
for r in pl:
    c = r["country"]
    if c not in order: order.append(c)
    PD[c][r["year"]] = [float(r[g]) for g in GNAMES]
COLS = 3
tw, th = 340, 255; gx, gy = 26, 30; padL = 28; padT = 128; padB = 64
NROWS = 4
W = padL*2 + COLS*tw + (COLS-1)*gx
H = padT + NROWS*th + (NROWS-1)*gy + padB
s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
     f'aria-label="Twelve countries shown as pairs of stacked bars, their diets in 1961 and in the most recent year, as shares of daily calories. Beside each bar is the share coming from oils, sugar, meat and dairy, the Western pattern. In 1961 that number is 64 for the United States but only 7 for South Korea and 10 for China. By 2023 South Korea reaches 54, China 33, and Brazil 57, while Nigeria and Senegal barely move. The plates converge toward the Western pattern.">']
s.append('''<style>
 .bg{fill:#ffffff}
 .t{fill:#0f141c;font:700 26px system-ui,-apple-system,Segoe UI,sans-serif}
 .sub{fill:#586170;font:15px system-ui,-apple-system,Segoe UI,sans-serif}
 .cty{fill:#0f141c;font:600 18px system-ui,-apple-system,Segoe UI,sans-serif}
 .yr{fill:#8b94a3;font:12.5px system-ui,-apple-system,Segoe UI,sans-serif}
 .num{fill:#0f141c;font:700 15px system-ui,-apple-system,Segoe UI,sans-serif}
 .lg{fill:#586170;font:13.5px system-ui,-apple-system,Segoe UI,sans-serif}
 .src{fill:#8b94a3;font:12px system-ui,-apple-system,Segoe UI,sans-serif}
 @media (prefers-color-scheme:dark){.bg{fill:#0f141c}.t{fill:#e7eef7}.sub{fill:#94a1b2}
 .cty{fill:#e7eef7}.yr{fill:#6b7688}.num{fill:#e7eef7}.lg{fill:#94a1b2}.src{fill:#6b7688}}
</style>''')
s.append(f'<rect class="bg" width="{W}" height="{H}" rx="12"/>')
s.append(f'<text class="t" x="{padL}" y="42">Twelve plates, then and now</text>')
s.append(f'<text class="sub" x="{padL}" y="68">Share of daily calories by food group, 1961 (top bar) and the latest year (bottom bar).</text>')
s.append(f'<text class="sub" x="{padL}" y="88">The number beside each bar is the Western pattern share: calories from oils, sugar, meat and dairy.</text>')
lx = padL
for name, col in zip(GNAMES, GCOL):
    s.append(f'<rect x="{lx}" y="{100}" width="13" height="13" rx="3" fill="{col}"/>')
    s.append(f'<text class="lg" x="{lx+18}" y="{111}">{name}</text>')
    lx += 18 + 7.6*len(name) + 22
for i, c in enumerate(order):
    cx = padL + (i % COLS)*(tw+gx); cy = padT + (i // COLS)*(th+gy)
    s.append(f'<text class="cty" x="{cx}" y="{cy+20}">{c}</text>')
    for bi, yr in enumerate(sorted(PD[c])):
        vals = PD[c][yr]
        by = cy + 44 + bi*92; bh = 48; bx = cx + 44; bw = tw - 44 - 46
        s.append(f'<text class="yr" x="{cx}" y="{by+bh/2+4}">{yr}</text>')
        acc = 0.0
        for vi, v in enumerate(vals):
            wpx = v/100*bw
            s.append(f'<rect x="{bx+acc:.1f}" y="{by}" width="{max(wpx,0.8):.1f}" height="{bh}" fill="{GCOL[vi]}"/>')
            acc += wpx
        west = round(vals[1] + vals[2])
        s.append(f'<text class="num" x="{bx+bw+10:.1f}" y="{by+bh/2+5}">{west}</text>')
s.append(f'<text class="src" x="{padL}" y="{H-22}">Data: FAO food balance sheets via Our World in Data. Latest year is 2023, or 2022 for Japan.</text>')
s.append('</svg>')
open(os.path.join(IMG, "final-plates.svg"), "w", encoding="utf-8").write("\n".join(s))
print("final-plates.svg written")

# ---------------- figure: the unequal portion ------------------------------
g2 = [(int(r["year"]), float(r["highest_kcal"]), r["highest_country"],
       float(r["lowest_kcal"]), r["lowest_country"], float(r["ratio"]))
      for r in csv.DictReader(open(os.path.join(OUT, "calorie-gap.csv"), encoding="utf-8"))]
W, H = 1128, 640; padL, padR, padT, padB = 86, 220, 120, 70
pw, ph = W-padL-padR, H-padT-padB
Y0, Y1 = 1961, 2023; K0, K1 = 0, 4400
X = lambda y: padL + (y-Y0)/(Y1-Y0)*pw
Y = lambda v: padT + (K1-v)/(K1-K0)*ph
s = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
     f'aria-label="Chart of daily calorie supply from 1961 to 2023 showing the best fed and worst fed country in each year. In 1961 the extremes were Jordan at 4,064 calories and Burkina Faso at 1,339, a ratio of 3.0 to 1. In 2023 they were the United States at 3,947 and Yemen at 1,811, a ratio of 2.2 to 1. The band between the two lines narrows slowly but never closes.">']
s.append('''<style>
 .bg{fill:#ffffff}
 .t{fill:#0f141c;font:700 26px system-ui,-apple-system,Segoe UI,sans-serif}
 .sub{fill:#586170;font:15px system-ui,-apple-system,Segoe UI,sans-serif}
 .grid{stroke:#e6ebf3;stroke-width:1}.axis{stroke:#c7d0dc;stroke-width:1.2}
 .tick{fill:#5b6470;font:13px system-ui,-apple-system,Segoe UI,sans-serif}
 .lg{font:600 14px system-ui,-apple-system,Segoe UI,sans-serif}
 .end{fill:#0f141c;font:600 14.5px system-ui,-apple-system,Segoe UI,sans-serif}
 .endv{fill:#586170;font:13px system-ui,-apple-system,Segoe UI,sans-serif}
 .chip{fill:#0f141c;font:700 15px system-ui,-apple-system,Segoe UI,sans-serif}
 .src{fill:#8b94a3;font:12px system-ui,-apple-system,Segoe UI,sans-serif}
 @media (prefers-color-scheme:dark){.bg{fill:#0f141c}.t{fill:#e7eef7}.sub{fill:#94a1b2}
 .grid{stroke:#223047}.axis{stroke:#33415a}.tick{fill:#94a1b2}
 .end{fill:#e7eef7}.endv{fill:#94a1b2}.chip{fill:#e7eef7}.src{fill:#6b7688}}
</style>''')
s.append(f'<rect class="bg" width="{W}" height="{H}" rx="12"/>')
s.append(f'<text class="t" x="{padL}" y="44">The unequal portion</text>')
s.append(f'<text class="sub" x="{padL}" y="72">Daily calorie supply of the best fed and worst fed country in each year, 1961 to 2023</text>')
for v in (1000, 2000, 3000, 4000):
    s.append(f'<line class="grid" x1="{padL}" y1="{Y(v):.1f}" x2="{W-padR}" y2="{Y(v):.1f}"/>')
    s.append(f'<text class="tick" x="{padL-10}" y="{Y(v)+4:.1f}" text-anchor="end">{v:,}</text>')
top = " ".join(f"{X(y):.1f},{Y(h):.1f}" for y, h, _, l, _, _ in g2)
botr = " ".join(f"{X(y):.1f},{Y(l):.1f}" for y, h, _, l, _, _ in reversed(g2))
s.append(f'<polygon points="{top} {botr}" fill="#d1477a" fill-opacity="0.10"/>')
s.append(f'<polyline points="{top}" fill="none" stroke="#d1477a" stroke-width="3.2" stroke-linejoin="round"/>')
s.append(f'<polyline points="{" ".join(f"{X(y):.1f},{Y(l):.1f}" for y, h, _, l, _, _ in g2)}" fill="none" stroke="#d1477a" stroke-width="3.2" stroke-dasharray="7 5" stroke-linejoin="round"/>')
f0, fN = g2[0], g2[-1]
ex = W - padR + 12
s.append(f'<circle cx="{X(fN[0]):.1f}" cy="{Y(fN[1]):.1f}" r="5" fill="#d1477a"/>')
s.append(f'<text class="end" x="{ex}" y="{Y(fN[1])-8:.1f}">{fN[2]}</text>')
s.append(f'<text class="endv" x="{ex}" y="{Y(fN[1])+10:.1f}">{int(fN[1]):,} kcal</text>')
s.append(f'<text class="lg" x="{ex}" y="{Y(fN[1])+28:.1f}" fill="#d1477a">best fed country</text>')
s.append(f'<circle cx="{X(fN[0]):.1f}" cy="{Y(fN[3]):.1f}" r="5" fill="#d1477a"/>')
s.append(f'<text class="end" x="{ex}" y="{Y(fN[3])-8:.1f}">{fN[4]}</text>')
s.append(f'<text class="endv" x="{ex}" y="{Y(fN[3])+10:.1f}">{int(fN[3]):,} kcal</text>')
s.append(f'<text class="lg" x="{ex}" y="{Y(fN[3])+28:.1f}" fill="#d1477a">worst fed country</text>')
s.append(f'<circle cx="{X(f0[0]):.1f}" cy="{Y(f0[1]):.1f}" r="5" fill="#d1477a"/>')
s.append(f'<text class="end" x="{padL}" y="{Y(f0[1])-34:.1f}">{f0[2]}</text>')
s.append(f'<text class="endv" x="{padL}" y="{Y(f0[1])-16:.1f}">{int(f0[1]):,} kcal</text>')
s.append(f'<circle cx="{X(f0[0]):.1f}" cy="{Y(f0[3]):.1f}" r="5" fill="#d1477a"/>')
s.append(f'<text class="end" x="{padL}" y="{Y(f0[3])+34:.1f}">{f0[4]}</text>')
s.append(f'<text class="endv" x="{padL}" y="{Y(f0[3])+52:.1f}">{int(f0[3]):,} kcal</text>')
s.append(f'<text class="chip" x="{X(1964):.1f}" y="{Y((f0[1]+f0[3])/2):.1f}">3.0 to 1</text>')
s.append(f'<text class="chip" x="{X(2015):.1f}" y="{Y((fN[1]+fN[3])/2):.1f}">2.2 to 1</text>')
for y in (1961, 1980, 2000, 2023):
    s.append(f'<text class="tick" x="{X(y):.1f}" y="{H-padB+22}" text-anchor="middle">{y}</text>')
s.append(f'<line class="axis" x1="{padL}" y1="{H-padB}" x2="{W-padR}" y2="{H-padB}"/>')
s.append(f'<text class="src" x="{padL}" y="{H-20}">Data: FAO via Our World in Data. Calories are supply, not intake; waste rises with income, so the true gap is smaller than shown.</text>')
s.append('</svg>')
open(os.path.join(IMG, "final-calorie-gap.svg"), "w", encoding="utf-8").write("\n".join(s))
print("final-calorie-gap.svg written")
print("done")
