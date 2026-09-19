/* Interactive sharpness-vs-generalization figure (single panel).
   All numbers are precomputed in figure_data.py; this file only draws.
   The post embeds the same interactive plot several times; each embed is a named
   variant whose default view (and Reset target) tells that section's story, and
   which declares the controls it exposes — later embeds progressively reveal more:
     optimizers | clickable legend chips (include/exclude)
     epoch      | play + ticked slider + readout
     schedule   | Fixed · Linear Decay
     metric     | Raw Sharpness · Adaptive Sharpness
   Every embed rests on the final epoch; a variant may also set autoplay, which
   cycles epoch 1 → 16 (holding on 16 between passes) from the moment it first
   scrolls into view, until the reader pauses it (skipped under reduced motion).
   Declared controls live in a Fig.panel between plot and caption; a Reset button
   docks to the panel's corner only while the view differs from the preset. An
   undeclared control's state stays pinned to the variant's preset. Axes are
   fixed (per metric on x, global on y) so no toggle ever rescales them.
   In print only the legend row survives (blog.css), so the paper copy shows the
   view the reader left behind — a sweep in progress prints at the preset epoch. */
(function () {
    "use strict";

    /* Variant name = the %%figure:name%% directive in post.md; static fallbacks
       come from figure_data.py's VARIANTS, which must stay in sync with this. */
    const VARIANTS = {
        "sharpness-lds": {
            preset: { schedule: "lds", metric: "raw", epoch: 16 },
            controls: ["optimizers", "epoch"],
            autoplay: true,
        },
        "sharpness-fixed": {
            preset: { schedule: "fixed", metric: "raw", epoch: 16 },
            controls: ["optimizers", "epoch", "schedule"],
        },
        "sharpness-adaptive": {
            preset: { schedule: "fixed", metric: "adaptive", epoch: 16 },
            controls: ["optimizers", "epoch", "schedule", "metric"],
        },
    };

    /* Decoupled Muon matches the canonical Muon (Newton-Schulz + decoupled weight
       decay); Normalized Muon is airbench's speedrun-specific variant, so every
       embed hides it by default — its legend chip brings it back, Reset re-hides. */
    const DEFAULT_HIDDEN = ["Normalized Muon"];

    const figures = [...document.querySelectorAll("figure[data-figure]")]
        .filter((f) => VARIANTS[f.dataset.figure]);
    if (!figures.length || !window.Fig) return;

    fetch("figure-data.json")
        .then((r) => r.json())
        .then((data) => figures.forEach((f) => init(f, data)))
        .catch((err) => console.error("figure: keeping static fallbacks —", err));

    const PANEL = { w: 640, h: 380, left: 48, right: 14, top: 14, bottom: 42 };

    function init(figure, data) {
        const name = figure.dataset.figure;
        const { preset, controls, autoplay } = VARIANTS[name];
        const has = (c) => controls.includes(c);
        const mount = figure.querySelector(".fig-mount");
        const css = getComputedStyle(document.documentElement);
        const color = {};
        data.optimizers.forEach((opt, i) => {
            color[opt] = {
                fill: `rgba(${css.getPropertyValue(`--opt-${i}`).trim()}, 0.75)`,
                strong: css.getPropertyValue(`--opt-${i}-strong`).trim(),
            };
        });

        const state = { ...preset, hidden: new Set(DEFAULT_HIDDEN) };

        // plot first, control panel below it (the figcaption follows outside the mount)
        mount.innerHTML = "";
        const panelWrap = Fig.el(mount, "div", "fig-panels");
        panelWrap.style.cssText = "position:relative;display:flex;justify-content:center;";
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.setAttribute("viewBox", `0 0 ${PANEL.w} ${PANEL.h}`);
        svg.style.cssText = `width:100%;max-width:${PANEL.w}px;height:auto`;
        panelWrap.appendChild(svg);

        const panel = Fig.panel(mount);

        const legend = !has("optimizers") ? null :
            Fig.legend(panel.row("Optimizers"), data.optimizers.map((opt) => ({
                name: opt, fill: color[opt].fill, strong: color[opt].strong,
            })), (opt) => {
                state.hidden.has(opt) ? state.hidden.delete(opt) : state.hidden.add(opt);
                render();
            });

        const epoch = !has("epoch") ? null : Fig.slider(panel.row("Epoch"), {
            label: "epoch", min: 1, max: data.epochs, initial: state.epoch, playMs: 400,
            loop: !!autoplay,   // only the self-playing embed cycles; the rest stop at 16
            printValue: preset.epoch,   // a sweep in progress prints at the resting epoch
            format: (v) => `${v} / ${data.epochs}`,
            onChange: (v) => { state.epoch = v; render(); },
        });

        const schedule = !has("schedule") ? null : Fig.toggleGroup(panel.row("Learning Rate"), null,
            [{ value: "fixed", label: "Fixed" }, { value: "lds", label: "Linear Decay" }],
            state.schedule, (v) => { state.schedule = v; render(); });

        const metric = !has("metric") ? null : Fig.toggleGroup(panel.row("X Axis"), null,
            [{ value: "raw", label: "Raw Sharpness" }, { value: "adaptive", label: "Adaptive Sharpness" }],
            state.metric, (v) => { state.metric = v; render(); });

        const reset = Fig.button(panel.root, "Reset", () => {
            if (epoch) epoch.stop();
            Object.assign(state, preset);
            state.hidden = new Set(DEFAULT_HIDDEN);
            if (schedule) schedule.set(state.schedule);
            if (metric) metric.set(state.metric);
            if (epoch) epoch.set(state.epoch);
            render();
        });
        reset.className = "reset";

        // Reset only appears once something differs from this variant's default view
        function isDirty() {
            return state.schedule !== preset.schedule
                || state.metric !== preset.metric
                || (state.epoch !== preset.epoch && !(epoch && epoch.playing))
                || state.hidden.size !== DEFAULT_HIDDEN.length
                || DEFAULT_HIDDEN.some((opt) => !state.hidden.has(opt));
        }

        Fig.tooltip(panelWrap, "circle[data-run]", (c) => {
            const [opt, raw, adaptive, gap, val, outlier] = c.dataset.run.split("|");
            return `<strong>${opt}</strong> — epoch ${state.epoch}<br>` +
                `gap ${gap} &middot; val acc ${val}<br>` +
                `raw ${raw} &middot; adaptive ${adaptive}` +
                (outlier === "1" ? "<br><em>outlier — excluded from the fit</em>" : "");
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

            let s = `<clipPath id="clip-${name}"><rect x="${PANEL.left}" y="${PANEL.top}" width="${iw}" height="${ih}"/></clipPath>`;

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

            s += `<g clip-path="url(#clip-${name})">`;
            for (const opt of data.optimizers) {
                if (state.hidden.has(opt)) continue;
                const f = sched.fits[state.metric][state.epoch - 1][opt];
                if (f) {
                    const [slope, intercept] = f;
                    s += `<line x1="${X(xLo)}" y1="${Y(slope * xLo + intercept)}" x2="${X(xHi)}" y2="${Y(slope * xHi + intercept)}" stroke="${color[opt].strong}" stroke-width="1.6" opacity="0.85" stroke-dasharray="6 4"/>`;
                }
                const cut = f && f[4] != null ? f[4] : null;
                for (const run of sched.points[opt]) {
                    const [raw, adaptive, gap, val] = run[state.epoch - 1];
                    const x = run[state.epoch - 1][mi];
                    // runs the fit trimmed as outliers are drawn without an outline
                    const outlier = cut !== null && Math.abs(gap - (f[0] * x + f[1])) > cut * 1.001;
                    const stroke = outlier ? "" : ` stroke="${color[opt].strong}" stroke-width="0.8"`;
                    s += `<circle cx="${X(x).toFixed(1)}" cy="${Y(gap).toFixed(1)}" r="3.4" fill="${color[opt].fill}"${stroke} data-run="${opt}|${raw}|${adaptive}|${gap}|${val}|${outlier ? 1 : 0}"/>`;
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
            reset.hidden = !isDirty();

            if (legend) for (const opt of data.optimizers) {
                legend.update(opt, { off: state.hidden.has(opt) });
            }
        }

        render();

        /* An autoplay variant rests on the preset epoch, but sweeps the whole run
           once, the first time the reader reaches it, so the story plays itself. */
        if (epoch && autoplay && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
            const observer = new IntersectionObserver((entries) => {
                if (!entries.some((e) => e.isIntersecting)) return;
                observer.disconnect();
                state.epoch = 1;
                epoch.set(1);
                epoch.play();   // before the draw, so Reset stays hidden for the sweep
                render();
            }, { threshold: 0.4 });
            observer.observe(figure);
        }
    }
})();
