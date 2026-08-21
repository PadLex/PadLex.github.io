"""Compute figure-data.json, the static fallback SVGs (one per figure variant
embedded in post.md) and results.html (Table 1) from the W&B exports of the
sharpness benchmark. Without the CSV exports, refits the trend lines from the
points already checked into figure-data.json and rebuilds the SVGs.

Replicates post_process/print_table from ~/projects/DL-project/sharpness_plots.py:
epoch > 0, drop runs with any null sam_sharpness, rename optimizers, epoch-16 stats.

Python owns the numbers; figure.js only draws them.
"""
import csv
import json
import math
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
CSV_DIR = Path.home() / "projects/DL-project/sharpness_experiments"
SCHEDULES = {"fixed": "76a26f61.csv", "lds": "370aad54.csv"}

OPTIMIZERS = ["Normalized Muon", "Decoupled Muon", "Coupled SGD", "Coupled Adam"]
RENAME = {"NormalizedMuon": "Normalized Muon", "VanillaMuon": "Decoupled Muon",
          "SGD": "Coupled SGD", "Adam": "Coupled Adam"}
N_EPOCHS = 16

# hex twins of the rgb pastels in blog.css, for the static fallback SVG
FILL = {"Normalized Muon": "#AFD3F0", "Decoupled Muon": "#F2C6DF",
        "Coupled SGD": "#DACCEF", "Coupled Adam": "#C9E4DF"}
STRONG = {"Normalized Muon": "#4a7fb5", "Decoupled Muon": "#b55a92",
          "Coupled SGD": "#7c5fa8", "Coupled Adam": "#3f8a7a"}


def load(schedule):
    """-> {optimizer: [run, ...]}, run = {epoch: row-dict} with all 16 epochs."""
    runs = {}
    with open(CSV_DIR / SCHEDULES[schedule]) as f:
        for row in csv.DictReader(f):
            if not row["epoch"]:
                continue
            epoch = int(float(row["epoch"]))
            if epoch < 1:
                continue
            runs.setdefault(row["run_id"], {"optimizer": RENAME[row["optimizer"]], "epochs": {}})[
                "epochs"][epoch] = row

    by_opt = {o: [] for o in OPTIMIZERS}
    dropped = []
    for run_id, run in runs.items():
        rows = run["epochs"]
        if len(rows) != N_EPOCHS or any(not r["sam_sharpness"] for r in rows.values()):
            dropped.append(run_id)
            continue
        by_opt[run["optimizer"]].append(run)
    counts = {o: len(v) for o, v in by_opt.items()}
    print(f"{schedule}: kept {counts}, dropped {len(dropped)} run(s) {dropped}")
    return by_opt


def val(row, col):
    return float(row[col])


# ---- Pearson p-value (two-sided, t-distribution) via regularized incomplete beta ----

def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 200, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1 / (d if abs(d) > FPMIN else FPMIN)
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        for aa in (m * (b - m) * x / ((qam + m2) * (a + m2)),
                   -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1 + aa * d
            d = 1 / (d if abs(d) > FPMIN else FPMIN)
            c = 1 + aa / c
            c = c if abs(c) > FPMIN else FPMIN
            h *= d * c
        if abs(d * c - 1) < EPS:
            break
    return h


def _betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return bt * _betacf(a, b, x) / a
    return 1 - bt * _betacf(b, a, 1 - x) / b


def pearson_p(r, n):
    if n < 3 or abs(r) >= 1:
        return 0.0
    df = n - 2
    t2 = r * r * df / (1 - r * r)
    return _betai(df / 2, 0.5, df / (df + t2))


# Residual-trim threshold for outlier exclusion in fit(), in robust standard
# deviations (1.4826 x MAD) of the vertical distance from the trend line.
TRIM = 3.3


def _ols(pts):
    """(slope, intercept) of the least-squares line through pts."""
    mx = statistics.fmean(p[0] for p in pts)
    my = statistics.fmean(p[1] for p in pts)
    slope = (sum((x - mx) * (y - my) for x, y in pts)
             / sum((x - mx) ** 2 for x, _ in pts))
    return slope, my - slope * mx


def fit(xs, ys):
    """OLS + Pearson on inliers: [slope, intercept, r, p, cutoff] (None when
    degenerate). Outliers are defined relative to the trend, not the axes (fencing
    either axis keeps on-trend extreme runs out and off-trend freaks in): starting
    from an OLS fit on all points, points whose |residual| exceeds TRIM x the
    robust residual scale (1.4826 x MAD) are dropped and the line refit, iterating
    to a fixed point. The reported r/p describe the same inlier set the line is
    fit to. cutoff is the final residual threshold (None if nothing was trimmed),
    so renderers can re-derive the inlier mask against the reported line."""
    if len(xs) < 3 or len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    pts = list(zip(xs, ys))
    mask = [True] * len(pts)
    cutoff = None
    if len(pts) >= 8:  # residual scale is meaningless on tiny samples
        for _ in range(20):
            slope, intercept = _ols([p for p, m in zip(pts, mask) if m])
            res = [abs(y - (slope * x + intercept)) for x, y in pts]
            scale = 1.4826 * statistics.median(r for r, m in zip(res, mask) if m)
            if scale == 0:
                break
            new = [r <= TRIM * scale for r in res]
            if sum(new) < 3:
                break
            cutoff = TRIM * scale  # matches the accepted mask below
            if new == mask:
                break
            mask = new
    if all(mask):
        cutoff = None  # nothing trimmed; don't let renderers reclassify
    xs, ys = zip(*(p for p, m in zip(pts, mask) if m))
    n = len(xs)
    if len(set(xs)) < 2 or len(set(ys)) < 2:
        return None
    r = statistics.correlation(xs, ys)
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    return [float(f"{slope:.5g}"), float(f"{my - slope * mx:.5g}"),
            round(r, 3), float(f"{pearson_p(r, n):.3g}"),
            float(f"{cutoff:.4g}") if cutoff is not None else None]


METRIC_COL = {"raw": "hessian", "adaptive": "adaptive_sharpness"}

# Fixed axis limits, ≈1.5× the paper's ranges, shared across schedules AND metrics'
# respective toggles so that no toggle ever rescales the axes. Chosen to divide into
# four clean ticks. p99 of the data is asserted to fit (see build_json).
AXES = {"x": {"raw": [0, 320], "adaptive": [0, 0.12]}, "y": [0, 0.32]}


def build_json(data):
    out = {
        "optimizers": OPTIMIZERS,
        "metricLabels": {"raw": "Raw Sharpness", "adaptive": "Adaptive Sharpness"},
        "epochs": N_EPOCHS,
        "axes": AXES,
        "schedules": {},
    }
    for sched, by_opt in data.items():
        points = {}
        for opt in OPTIMIZERS:
            points[opt] = [
                [[float(f"{val(r['epochs'][e], 'hessian'):.4g}"),
                  float(f"{val(r['epochs'][e], 'adaptive_sharpness'):.4g}"),
                  round(val(r["epochs"][e], "gap"), 4),
                  round(val(r["epochs"][e], "val_acc"), 4)]
                 for e in range(1, N_EPOCHS + 1)]
                for r in by_opt[opt]
            ]
        fits = {m: [] for m in METRIC_COL}
        for metric, col in METRIC_COL.items():
            for e in range(1, N_EPOCHS + 1):
                per_opt = {}
                for opt in OPTIMIZERS:
                    xs = [val(r["epochs"][e], col) for r in by_opt[opt]]
                    ys = [val(r["epochs"][e], "gap") for r in by_opt[opt]]
                    per_opt[opt] = fit(xs, ys)
                fits[metric].append(per_opt)
        out["schedules"][sched] = {"points": points, "fits": fits}

        # guard: the fixed limits must still cover the bulk of the data (p99 per axis)
        for metric, col in METRIC_COL.items():
            vals = sorted(
                val(r["epochs"][e], col)
                for opt in OPTIMIZERS for r in by_opt[opt] for e in range(1, N_EPOCHS + 1)
            )
            p99 = vals[min(len(vals) - 1, int(len(vals) * 0.99))]
            assert p99 <= AXES["x"][metric][1], f"{sched}/{metric}: p99={p99} exceeds axis"
        gaps = sorted(val(r["epochs"][e], "gap")
                      for opt in OPTIMIZERS for r in by_opt[opt] for e in range(1, N_EPOCHS + 1))
        p99g = gaps[min(len(gaps) - 1, int(len(gaps) * 0.99))]
        assert p99g <= AXES["y"][1], f"{sched}: gap p99={p99g} exceeds y axis"
    return out


def build_table(data):
    metrics = [("train_acc", "Train Acc", 1), ("val_acc", "Val Acc", 1),
               ("gap", "Acc Gap", 1), ("hessian", "Raw (&times;10<sup>2</sup>)", 0.01),
               ("adaptive_sharpness", "ASAM (&times;10<sup>-2</sup>)", 100)]
    rows = []
    for sched_label, sched in (("Fixed", "fixed"), ("LDS", "lds")):
        for i, opt in enumerate(OPTIMIZERS):
            cells = [sched_label if i == 0 else "", opt]
            for col, _, scale in metrics:
                values = [val(r["epochs"][N_EPOCHS], col) * scale for r in data[sched][opt]]
                cells.append(f"{statistics.fmean(values):.2f} &plusmn; {statistics.stdev(values):.3f}")
            cls = " class='block-start'" if i == 0 and sched == "lds" else ""
            rows.append(f"<tr{cls}>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    header = "".join(f"<th>{h}</th>" for h in ["LR", "Optimizer"] + [m[1] for m in metrics])
    return (
        "<figcaption><span class='fig-label'>Table 1.</span> For each Learning Rate scheduler (LR) "
        "and Optimizer pairing, we report Validation Accuracy (Val Acc), Generalization Gap (Gap), "
        "Raw Sharpness (Raw), and Adaptive Sharpness (ASAM) scores. Each entry aggregates the mean "
        "and standard deviation across 64 runs.</figcaption>\n"
        f"<div class='table-scroll'><table class='results'>\n<tr>{header}</tr>\n"
        + "\n".join(rows) + "\n</table></div>"
    )


# ---- static fallback SVGs: each embed's default view at epoch 16 ----
# One file per %%figure:name%% directive in post.md; must stay in sync with the
# VARIANTS map in figure.js, which mounts the interactive plot over these.
VARIANTS = {"sharpness-lds": ("lds", "raw"),
            "sharpness-fixed": ("fixed", "raw"),
            "sharpness-adaptive": ("fixed", "adaptive")}

# hidden in every embed's default view (see DEFAULT_HIDDEN in figure.js):
# Decoupled Muon matches canonical Muon; Normalized Muon is airbench-specific
DEFAULT_HIDDEN = {"Normalized Muon"}


def build_svg(fig, schedule, metric):
    W, H, PAD_L, PAD_R, PAD_T, PAD_B = 640, 400, 48, 14, 34, 42
    panel_w = W - PAD_L - PAD_R
    panel_h = H - PAD_T - PAD_B
    y_lo, y_hi = fig["axes"]["y"]
    x_lo, x_hi = fig["axes"]["x"][metric]
    sched = fig["schedules"][schedule]
    mi = 0 if metric == "raw" else 1
    sched_label = "fixed LR" if schedule == "fixed" else "linear-decay LR"

    def X(v):
        return PAD_L + (min(v, x_hi) - x_lo) / (x_hi - x_lo) * panel_w

    def Y(v):
        return PAD_T + panel_h - (min(v, y_hi) - y_lo) / (y_hi - y_lo) * panel_h

    parts = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {W} {H}' "
             f"font-family='Lato, sans-serif' font-size='11'>"]
    parts.append(f"<line x1='{PAD_L}' y1='{PAD_T + panel_h}' x2='{PAD_L + panel_w}' "
                 f"y2='{PAD_T + panel_h}' stroke='#c9c9c9'/>")
    parts.append(f"<line x1='{PAD_L}' y1='{PAD_T}' x2='{PAD_L}' y2='{PAD_T + panel_h}' stroke='#c9c9c9'/>")
    for t in range(5):
        xv = x_lo + t * (x_hi - x_lo) / 4
        yv = y_lo + t * (y_hi - y_lo) / 4
        parts.append(f"<text x='{X(xv):.1f}' y='{PAD_T + panel_h + 16}' text-anchor='middle' "
                     f"fill='#9a9ea3'>{xv:g}</text>")
        parts.append(f"<text x='{PAD_L - 8}' y='{Y(yv) + 4:.1f}' text-anchor='end' "
                     f"fill='#9a9ea3'>{yv:g}</text>")
    parts.append(f"<text x='{PAD_L + panel_w / 2:.1f}' y='{H - 8}' text-anchor='middle' "
                 f"fill='#565B60'>{fig['metricLabels'][metric]} ({sched_label}, epoch 16)</text>")
    parts.append(f"<text x='14' y='{PAD_T + panel_h / 2:.1f}' fill='#565B60' "
                 f"transform='rotate(-90 14 {PAD_T + panel_h / 2:.1f})' "
                 f"text-anchor='middle'>Generalization Gap</text>")

    stats_y = PAD_T + 12
    for opt in fig["optimizers"]:
        if opt in DEFAULT_HIDDEN:
            continue
        f16 = sched["fits"][metric][15][opt]
        cut = f16[4] if f16 else None
        for run in sched["points"][opt]:
            x, gap = run[15][mi], run[15][2]
            # trimmed outliers are drawn without an outline, matching figure.js
            outlier = cut is not None and abs(gap - (f16[0] * x + f16[1])) > cut * 1.001
            stroke = "" if outlier else f" stroke='{STRONG[opt]}' stroke-width='0.8'"
            parts.append(f"<circle cx='{X(x):.1f}' cy='{Y(gap):.1f}' r='3.4' "
                         f"fill='{FILL[opt]}' fill-opacity='0.75'{stroke}/>")
        if f16:
            slope, intercept, r = f16[0], f16[1], f16[2]
            parts.append(f"<line x1='{X(x_lo):.1f}' y1='{Y(slope * x_lo + intercept):.1f}' "
                         f"x2='{X(x_hi):.1f}' y2='{Y(slope * x_hi + intercept):.1f}' "
                         f"stroke='{STRONG[opt]}' stroke-width='1.6' opacity='0.85' "
                         f"stroke-dasharray='6 4'/>")
            parts.append(f"<text x='{PAD_L + 8}' y='{stats_y}' fill='{STRONG[opt]}'>"
                         f"{opt}: R={r:.2f}</text>")
            stats_y += 15

    # legend row across the top
    shown = [opt for opt in fig["optimizers"] if opt not in DEFAULT_HIDDEN]
    lx = W / 2 - 60 * len(shown)
    for opt in shown:
        parts.append(f"<circle cx='{lx}' cy='16' r='5' fill='{FILL[opt]}' stroke='{STRONG[opt]}'/>")
        parts.append(f"<text x='{lx + 10}' y='20' fill='#565B60'>{opt}</text>")
        lx += 120
    parts.append("</svg>")
    return "".join(parts)


def refit(fig):
    """Recompute all fits from the (rounded) points already in figure-data.json,
    for machines without the CSV exports. A full CSV rebuild is exact; this one
    inherits the 4-significant-digit rounding of the stored points."""
    for sched in fig["schedules"].values():
        fits = {}
        for metric, mi in (("raw", 0), ("adaptive", 1)):
            fits[metric] = [
                {opt: fit([run[e][mi] for run in sched["points"][opt]],
                          [run[e][2] for run in sched["points"][opt]])
                 for opt in fig["optimizers"]}
                for e in range(fig["epochs"])
            ]
        sched["fits"] = fits


def write_svgs(fig):
    for name, (schedule, metric) in VARIANTS.items():
        (HERE / f"{name}.svg").write_text(build_svg(fig, schedule, metric))
    print(f"wrote {', '.join(f'{name}.svg' for name in VARIANTS)}")


def main():
    if not CSV_DIR.exists():
        print(f"{CSV_DIR} not found; refitting from figure-data.json's points")
        fig = json.loads((HERE / "figure-data.json").read_text())
        refit(fig)
        (HERE / "figure-data.json").write_text(json.dumps(fig, separators=(",", ":")))
        write_svgs(fig)
        return
    data = {sched: load(sched) for sched in SCHEDULES}
    fig = build_json(data)
    (HERE / "figure-data.json").write_text(json.dumps(fig, separators=(",", ":")))
    print(f"figure-data.json: {(HERE / 'figure-data.json').stat().st_size / 1024:.0f} KB")
    (HERE / "results.html").write_text(build_table(data))
    write_svgs(fig)
    print("wrote results.html")
    # sanity: epoch-16 fixed-LR pearson r per paper: raw 0.27–0.49, adaptive 0.45–0.69
    for metric in ("raw", "adaptive"):
        rs = {o: (f[2] if (f := fig["schedules"]["fixed"]["fits"][metric][15][o]) else None)
              for o in OPTIMIZERS}
        print(f"fixed epoch16 {metric} r: {rs}")


if __name__ == "__main__":
    main()
