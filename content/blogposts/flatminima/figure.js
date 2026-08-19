/* Interactive sharpness-vs-generalization figure.
   All numbers are precomputed in figure_data.py; this file only draws.
   State: schedule (fixed|lds), epoch (1..16), hidden optimizers. Reset restores
   the paper's configuration: fixed LR, epoch 16, all optimizers. */
(function () {
    "use strict";

    const figure = document.querySelector("figure[data-figure='sharpness']");
    if (!figure) return;
    const mount = figure.querySelector(".fig-mount");

    fetch("figure-data.json")
        .then((r) => r.json())
        .then(init)
        .catch((err) => console.error("figure: keeping static fallback —", err));

    const DEFAULTS = { schedule: "fixed", epoch: 16 };
    const METRICS = ["raw", "adaptive"];
    const PANEL = { w: 430, h: 330, left: 46, right: 12, top: 12, bottom: 40 };

    function init(data) {
        const css = getComputedStyle(document.documentElement);
        const color = data.optimizers.map((_, i) => ({
            fill: `rgba(${css.getPropertyValue(`--opt-${i}`).trim()}, 0.75)`,
            strong: css.getPropertyValue(`--opt-${i}-strong`).trim(),
        }));

        const state = { schedule: DEFAULTS.schedule, epoch: DEFAULTS.epoch, hidden: new Set() };
        let timer = null;

        /* ---- skeleton ---- */
        mount.innerHTML = `
            <div class="fig-controls">
                <span class="seg" role="group" aria-label="learning rate schedule">
                    <button data-sched="fixed">Fixed LR</button>
                    <button data-sched="lds">LDS</button>
                </span>
                <span class="epoch-wrap">
                    <button class="play" aria-label="play through epochs">&#9654;</button>
                    <input type="range" min="1" max="${data.epochs}" step="1" aria-label="epoch">
                    <span class="epoch-label"></span>
                </span>
                <button class="reset">Reset</button>
            </div>
            <div class="fig-panels" style="display:flex;flex-wrap:wrap;justify-content:center;gap:4px;position:relative;">
                <svg class="p0" viewBox="0 0 ${PANEL.w} ${PANEL.h}" style="flex:1 1 300px;max-width:${PANEL.w}px"></svg>
                <svg class="p1" viewBox="0 0 ${PANEL.w} ${PANEL.h}" style="flex:1 1 300px;max-width:${PANEL.w}px"></svg>
                <div class="fig-tooltip" hidden></div>
            </div>
            <div class="fig-legend"></div>`;

        const el = {
            segBtns: mount.querySelectorAll(".seg button"),
            play: mount.querySelector(".play"),
            slider: mount.querySelector("input[type=range]"),
            epochLabel: mount.querySelector(".epoch-label"),
            reset: mount.querySelector(".reset"),
            panels: [mount.querySelector(".p0"), mount.querySelector(".p1")],
            panelsWrap: mount.querySelector(".fig-panels"),
            legend: mount.querySelector(".fig-legend"),
            tooltip: mount.querySelector(".fig-tooltip"),
        };

        /* ---- controls ---- */
        el.segBtns.forEach((b) =>
            b.addEventListener("click", () => { state.schedule = b.dataset.sched; render(); }));
        el.slider.addEventListener("input", () => { state.epoch = +el.slider.value; render(); });
        el.reset.addEventListener("click", () => {
            stop();
            state.schedule = DEFAULTS.schedule;
            state.epoch = DEFAULTS.epoch;
            state.hidden.clear();
            render();
        });
        if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
            el.play.style.display = "none";
        }
        el.play.addEventListener("click", () => (timer ? stop() : play()));

        function play() {
            el.play.innerHTML = "&#10074;&#10074;";
            if (state.epoch >= data.epochs) state.epoch = 0;
            timer = setInterval(() => {
                state.epoch += 1;
                if (state.epoch >= data.epochs) stop();
                render();
            }, 400);
        }
        function stop() {
            clearInterval(timer);
            timer = null;
            el.play.innerHTML = "&#9654;";
        }

        /* ---- legend ---- */
        data.optimizers.forEach((opt, i) => {
            const chip = document.createElement("button");
            chip.className = "chip";
            chip.innerHTML =
                `<span class="dot" style="background:${color[i].fill};box-shadow:inset 0 0 0 1.5px ${color[i].strong}"></span>` +
                `<span>${opt}</span> <span class="r-val"></span>`;
            chip.addEventListener("click", () => {
                state.hidden.has(opt) ? state.hidden.delete(opt) : state.hidden.add(opt);
                render();
            });
            el.legend.appendChild(chip);
        });

        /* ---- tooltip (delegated) ---- */
        el.panelsWrap.addEventListener("pointerover", (e) => {
            const c = e.target.closest("circle[data-run]");
            if (!c) return;
            const [opt, raw, adaptive, gap, val] = c.dataset.run.split("|");
            el.tooltip.innerHTML =
                `<strong>${opt}</strong> — epoch ${state.epoch}<br>` +
                `gap ${gap} &middot; val acc ${val}<br>` +
                `raw ${raw} &middot; adaptive ${adaptive}`;
            el.tooltip.hidden = false;
        });
        el.panelsWrap.addEventListener("pointermove", (e) => {
            if (el.tooltip.hidden) return;
            const box = el.panelsWrap.getBoundingClientRect();
            el.tooltip.style.left = Math.min(e.clientX - box.left + 14, box.width - 170) + "px";
            el.tooltip.style.top = e.clientY - box.top + 14 + "px";
        });
        el.panelsWrap.addEventListener("pointerout", (e) => {
            if (!e.target.closest("circle[data-run]")) return;
            el.tooltip.hidden = true;
        });

        /* ---- drawing ---- */
        const fmt = (v) => (+v).toPrecision(3).replace(/\.?0+$/, "");

        function drawPanel(svg, metricIdx) {
            const metric = METRICS[metricIdx];
            const sched = data.schedules[state.schedule];
            const [xLo, xHi] = data.axes.x[metric][state.schedule];
            const [yLo, yHi] = data.axes.y[state.schedule];
            const iw = PANEL.w - PANEL.left - PANEL.right;
            const ih = PANEL.h - PANEL.top - PANEL.bottom;
            const X = (v) => PANEL.left + ((Math.min(v, xHi) - xLo) / (xHi - xLo)) * iw;
            const Y = (v) => PANEL.top + ih - ((Math.min(v, yHi) - yLo) / (yHi - yLo)) * ih;
            const clip = `clip-${metricIdx}`;

            let s = `<clipPath id="${clip}"><rect x="${PANEL.left}" y="${PANEL.top}" width="${iw}" height="${ih}"/></clipPath>`;

            // axes + ticks
            s += `<line x1="${PANEL.left}" y1="${PANEL.top + ih}" x2="${PANEL.left + iw}" y2="${PANEL.top + ih}" stroke="#c9c9c9"/>`;
            s += `<line x1="${PANEL.left}" y1="${PANEL.top}" x2="${PANEL.left}" y2="${PANEL.top + ih}" stroke="#c9c9c9"/>`;
            for (let t = 0; t <= 4; t++) {
                const xv = xLo + (t * (xHi - xLo)) / 4;
                const yv = yLo + (t * (yHi - yLo)) / 4;
                s += `<text x="${X(xv)}" y="${PANEL.top + ih + 16}" text-anchor="middle" fill="#9a9ea3" font-size="10">${fmt(xv)}</text>`;
                if (metricIdx === 0)
                    s += `<text x="${PANEL.left - 6}" y="${Y(yv) + 3.5}" text-anchor="end" fill="#9a9ea3" font-size="10">${fmt(yv)}</text>`;
                s += `<line x1="${X(xv)}" y1="${PANEL.top + ih}" x2="${X(xv)}" y2="${PANEL.top + ih + 4}" stroke="#c9c9c9"/>`;
            }
            s += `<text x="${PANEL.left + iw / 2}" y="${PANEL.h - 6}" text-anchor="middle" fill="#565B60" font-size="11.5">${data.metricLabels[metric]}</text>`;
            if (metricIdx === 0)
                s += `<text x="12" y="${PANEL.top + ih / 2}" fill="#565B60" font-size="11.5" text-anchor="middle" transform="rotate(-90 12 ${PANEL.top + ih / 2})">Generalization Gap</text>`;

            // data
            let statsY = PANEL.top + 14;
            s += `<g clip-path="url(#${clip})">`;
            data.optimizers.forEach((opt, i) => {
                if (state.hidden.has(opt)) return;
                const f = sched.fits[metric][state.epoch - 1][opt];
                if (f) {
                    const [slope, intercept] = f;
                    s += `<line x1="${X(xLo)}" y1="${Y(slope * xLo + intercept)}" x2="${X(xHi)}" y2="${Y(slope * xHi + intercept)}" stroke="${color[i].strong}" stroke-width="1.6" opacity="0.85"/>`;
                }
                for (const run of sched.points[opt]) {
                    const [raw, adaptive, gap, val] = run[state.epoch - 1];
                    const v = metric === "raw" ? raw : adaptive;
                    s += `<circle cx="${X(v).toFixed(1)}" cy="${Y(gap).toFixed(1)}" r="3.2" fill="${color[i].fill}" stroke="${color[i].strong}" stroke-width="0.8" data-run="${opt}|${raw}|${adaptive}|${gap}|${val}"/>`;
                }
            });
            s += "</g>";

            // per-optimizer R (outside clip so it never hides)
            data.optimizers.forEach((opt, i) => {
                if (state.hidden.has(opt)) return;
                const f = sched.fits[metric][state.epoch - 1][opt];
                if (!f) return;
                const p = f[3] < 1e-4 ? "p&lt;10&#8315;&#8308;" : `p=${fmt(f[3])}`;
                s += `<text x="${PANEL.left + 8}" y="${statsY}" fill="${color[i].strong}" font-size="10.5">R=${f[2].toFixed(2)} (${p})</text>`;
                statsY += 14;
            });

            svg.innerHTML = s;
        }

        function render() {
            el.segBtns.forEach((b) => b.classList.toggle("active", b.dataset.sched === state.schedule));
            el.slider.value = state.epoch;
            el.epochLabel.textContent = `epoch ${state.epoch}`;
            el.legend.querySelectorAll(".chip").forEach((chip, i) => {
                const opt = data.optimizers[i];
                chip.classList.toggle("off", state.hidden.has(opt));
                const f = data.schedules[state.schedule].fits.adaptive[state.epoch - 1][opt];
                chip.querySelector(".r-val").textContent =
                    !state.hidden.has(opt) && f ? `r=${f[2].toFixed(2)}` : "";
            });
            el.panels.forEach((svg, i) => drawPanel(svg, i));
        }

        render();
    }
})();
