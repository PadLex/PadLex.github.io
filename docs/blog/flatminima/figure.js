/* Interactive sharpness-vs-generalization figure (single panel).
   All numbers are precomputed in figure_data.py; this file only draws.
   Controls live in a Fig.panel between the plot and the caption:
     Optimizers    | clickable legend chips (include/exclude)
     Epoch         | play + ticked slider + readout
     Learning Rate | Fixed · Linear Decay
     X Axis        | Raw Sharpness · Adaptive Sharpness    [Reset top-right]
   Axes are fixed (per metric on x, global on y) so no toggle ever rescales them.
   Reset restores the paper's configuration: fixed LR, raw sharpness, epoch 16. */
(function () {
    "use strict";

    const figure = document.querySelector("figure[data-figure='sharpness']");
    if (!figure || !window.Fig) return;
    const mount = figure.querySelector(".fig-mount");

    fetch("figure-data.json")
        .then((r) => r.json())
        .then(init)
        .catch((err) => console.error("figure: keeping static fallback —", err));

    const DEFAULTS = { schedule: "fixed", metric: "raw", epoch: 16 };
    const PANEL = { w: 640, h: 380, left: 48, right: 14, top: 14, bottom: 42 };

    function init(data) {
        const css = getComputedStyle(document.documentElement);
        const color = {};
        data.optimizers.forEach((opt, i) => {
            color[opt] = {
                fill: `rgba(${css.getPropertyValue(`--opt-${i}`).trim()}, 0.75)`,
                strong: css.getPropertyValue(`--opt-${i}-strong`).trim(),
            };
        });

        const state = { ...DEFAULTS, hidden: new Set() };

        // plot first, control panel below it (the figcaption follows outside the mount)
        mount.innerHTML = "";
        const panelWrap = Fig.el(mount, "div", "fig-panels");
        panelWrap.style.cssText = "position:relative;display:flex;justify-content:center;";
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("viewBox", `0 0 ${PANEL.w} ${PANEL.h}`);
        svg.style.cssText = `width:100%;max-width:${PANEL.w}px;height:auto`;
        panelWrap.appendChild(svg);

        const panel = Fig.panel(mount);

        const legend = Fig.legend(panel.row("Optimizers"), data.optimizers.map((opt) => ({
            name: opt, fill: color[opt].fill, strong: color[opt].strong,
        })), (opt) => {
            state.hidden.has(opt) ? state.hidden.delete(opt) : state.hidden.add(opt);
            render();
        });

        const epoch = Fig.slider(panel.row("Epoch"), {
            label: "epoch", min: 1, max: data.epochs, initial: state.epoch, playMs: 400,
            format: (v) => `${v} / ${data.epochs}`,
            onChange: (v) => { state.epoch = v; render(); },
        });

        const schedule = Fig.toggleGroup(panel.row("Learning Rate"), null,
            [{ value: "fixed", label: "Fixed" }, { value: "lds", label: "Linear Decay" }],
            state.schedule, (v) => { state.schedule = v; render(); });

        const metric = Fig.toggleGroup(panel.row("X Axis"), null,
            [{ value: "raw", label: "Raw Sharpness" }, { value: "adaptive", label: "Adaptive Sharpness" }],
            state.metric, (v) => { state.metric = v; render(); });

        Fig.button(panel.root, "Reset", () => {
            epoch.stop();
            Object.assign(state, DEFAULTS);
            state.hidden.clear();
            schedule.set(state.schedule);
            metric.set(state.metric);
            epoch.set(state.epoch);
            render();
        }).className = "reset";

        Fig.tooltip(panelWrap, "circle[data-run]", (c) => {
            const [opt, raw, adaptive, gap, val] = c.dataset.run.split("|");
            return `<strong>${opt}</strong> — epoch ${state.epoch}<br>` +
                `gap ${gap} &middot; val acc ${val}<br>` +
                `raw ${raw} &middot; adaptive ${adaptive}`;
        });

        function render() {
            const sched = data.schedules[state.schedule];
            const [xLo, xHi] = data.axes.x[state.metric];
            const [yLo, yHi] = data.axes.y;
            const iw = PANEL.w - PANEL.left - PANEL.right;
            const ih = PANEL.h - PANEL.top - PANEL.bottom;
            const X = (v) => PANEL.left + ((Math.min(v, xHi) - xLo) / (xHi - xLo)) * iw;
            const Y = (v) => PANEL.top + ih - ((Math.min(v, yHi) - yLo) / (yHi - yLo)) * ih;
            const mi = state.metric === "raw" ? 0 : 1;

            let s = `<clipPath id="fig-clip"><rect x="${PANEL.left}" y="${PANEL.top}" width="${iw}" height="${ih}"/></clipPath>`;

            s += `<line x1="${PANEL.left}" y1="${PANEL.top + ih}" x2="${PANEL.left + iw}" y2="${PANEL.top + ih}" stroke="#c9c9c9"/>`;
            s += `<line x1="${PANEL.left}" y1="${PANEL.top}" x2="${PANEL.left}" y2="${PANEL.top + ih}" stroke="#c9c9c9"/>`;
            for (let t = 0; t <= 4; t++) {
                const xv = xLo + (t * (xHi - xLo)) / 4;
                const yv = yLo + (t * (yHi - yLo)) / 4;
                s += `<text x="${X(xv)}" y="${PANEL.top + ih + 16}" text-anchor="middle" fill="#9a9ea3" font-size="10">${Fig.fmt(xv)}</text>`;
                s += `<text x="${PANEL.left - 6}" y="${Y(yv) + 3.5}" text-anchor="end" fill="#9a9ea3" font-size="10">${Fig.fmt(yv)}</text>`;
                s += `<line x1="${X(xv)}" y1="${PANEL.top + ih}" x2="${X(xv)}" y2="${PANEL.top + ih + 4}" stroke="#c9c9c9"/>`;
            }
            s += `<text x="${PANEL.left + iw / 2}" y="${PANEL.h - 6}" text-anchor="middle" fill="#565B60" font-size="11.5">${data.metricLabels[state.metric]}</text>`;
            s += `<text x="12" y="${PANEL.top + ih / 2}" fill="#565B60" font-size="11.5" text-anchor="middle" transform="rotate(-90 12 ${PANEL.top + ih / 2})">Generalization Gap</text>`;

            s += `<g clip-path="url(#fig-clip)">`;
            for (const opt of data.optimizers) {
                if (state.hidden.has(opt)) continue;
                const f = sched.fits[state.metric][state.epoch - 1][opt];
                if (f) {
                    const [slope, intercept] = f;
                    s += `<line x1="${X(xLo)}" y1="${Y(slope * xLo + intercept)}" x2="${X(xHi)}" y2="${Y(slope * xHi + intercept)}" stroke="${color[opt].strong}" stroke-width="1.6" opacity="0.85"/>`;
                }
                for (const run of sched.points[opt]) {
                    const [raw, adaptive, gap, val] = run[state.epoch - 1];
                    s += `<circle cx="${X(run[state.epoch - 1][mi]).toFixed(1)}" cy="${Y(gap).toFixed(1)}" r="3.4" fill="${color[opt].fill}" stroke="${color[opt].strong}" stroke-width="0.8" data-run="${opt}|${raw}|${adaptive}|${gap}|${val}"/>`;
                }
            }
            s += "</g>";

            let statsY = PANEL.top + 14;
            for (const opt of data.optimizers) {
                if (state.hidden.has(opt)) continue;
                const f = sched.fits[state.metric][state.epoch - 1][opt];
                if (!f) continue;
                const p = f[3] < 1e-4 ? "p&lt;10&#8315;&#8308;" : `p=${Fig.fmt(f[3])}`;
                s += `<text x="${PANEL.left + 8}" y="${statsY}" fill="${color[opt].strong}" font-size="10.5">R=${f[2].toFixed(2)} (${p})</text>`;
                statsY += 14;
            }

            svg.innerHTML = s;

            for (const opt of data.optimizers) {
                legend.update(opt, { off: state.hidden.has(opt) });
            }
        }

        render();
    }
})();
