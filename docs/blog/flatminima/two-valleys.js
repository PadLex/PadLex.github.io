/* Two-valleys landscape: the Flat Minima intuition as a picture.
   A synthetic 1-D loss landscape with a sharp valley and a flat one, and a handful
   of runs converged at the bottom of each. The validation landscape is the training
   landscape shifted right by a fixed ε. Toggling "validation loss" on fades in the
   shifted curve and slides every run from its training loss up to its validation
   loss, leaving a vertical trace back to where it came from — that trace is the
   run's generalization gap. Sharp-valley runs climb the wall, flat-valley runs
   barely move.

   Dual mode, so the curve and the runs live in exactly one place:
     browser  — interactive (toggle + animation, via the shared Fig helpers)
     node     — `node two-valleys.js > two-valleys.svg` writes the static fallback
                in the "shown" state (the build inlines it; JS then replaces it). */
(function () {
    "use strict";

    const W = 640, H = 340;
    const PAD = { left: 40, right: 14, top: 18, bottom: 38 };
    const iw = W - PAD.left - PAD.right;
    const ih = H - PAD.top - PAD.bottom;

    /* ---- the landscape ------------------------------------------------- */
    const CEIL = 0.86;                                   // loss far from any valley
    const SHARP = { m: 0.25, s: 0.036, depth: 0.7, p: 2 };
    const FLAT = { m: 0.68, s: 0.14, depth: 0.7, p: 2.6 };  // p > 2: flatter floor
    const EPS = 0.03;                                    // validation shift

    function well(w, v) {
        return v.depth * Math.exp(-Math.pow(Math.abs((w - v.m) / v.s), v.p) / 2);
    }
    const loss = (w) => CEIL - well(w, SHARP) - well(w, FLAT);
    const valLoss = (w) => loss(w - EPS);

    /* ---- the converged runs (deterministic, so node and browser agree) ---- */
    function rng(seed) {                                 // mulberry32
        return () => {
            seed = (seed + 0x6D2B79F5) | 0;
            let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
            t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
            return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
        };
    }
    const RUNS = (() => {
        const r = rng(1337);
        const gauss = () => Math.sqrt(-2 * Math.log(1 - r())) * Math.cos(2 * Math.PI * r());
        const out = [];
        // runs settle where the gradient dies: spread scales with the valley's width
        for (const [valley, v, n, k] of [["sharp", SHARP, 11, 0.3], ["flat", FLAT, 11, 0.4]]) {
            for (let i = 0; i < n; i++) {
                const w = v.m + k * v.s * gauss();
                out.push({ valley, w, train: loss(w), val: valLoss(w) });
            }
        }
        return out;
    })();
    const meanGap = (valley) => {
        const g = RUNS.filter((r) => r.valley === valley).map((r) => r.val - r.train);
        return g.reduce((a, b) => a + b, 0) / g.length;
    };

    const X = (w) => PAD.left + w * iw;
    const Y = (l) => PAD.top + (1 - l) * ih;
    const f1 = (x) => x.toFixed(1);

    function curvePath(fn) {
        const N = 220;
        let d = "";
        for (let i = 0; i <= N; i++) {
            const w = i / N;
            d += (i ? "L" : "M") + f1(X(w)) + " " + f1(Y(fn(w)));
        }
        return d;
    }

    /* ---- drawing -------------------------------------------------------- */
    const INK = "#565B60", MUTED = "#9a9ea3", HAIR = "#c9c9c9";
    const RUN = { fill: "#F2C6DF", strong: "#b55a92" };    // runs, as in the scatter figures
    const VAL = "#4a7fb5";                                  // validation landscape

    /* t = 0: training view; t = 1: validation view. Everything that belongs to the
       validation view carries class "val" and is drawn at opacity t; each run sits
       at the lerp of its two losses. */
    function draw(t, interactive) {
        const s = [];
        s.push(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${W} ${H}' font-family='Lato, sans-serif' font-size='11'>`);

        // axes: recessive hairlines, no ticks — the units are arbitrary
        s.push(`<line x1='${PAD.left}' y1='${PAD.top}' x2='${PAD.left}' y2='${PAD.top + ih}' stroke='${HAIR}'/>`);
        s.push(`<line x1='${PAD.left}' y1='${PAD.top + ih}' x2='${PAD.left + iw}' y2='${PAD.top + ih}' stroke='${HAIR}'/>`);
        s.push(`<text x='${PAD.left + iw / 2}' y='${H - 8}' text-anchor='middle' fill='${INK}' font-size='11.5'>Parameter <tspan font-style='italic'>w</tspan></text>`);
        s.push(`<text x='13' y='${PAD.top + ih / 2}' fill='${INK}' font-size='11.5' text-anchor='middle' transform='rotate(-90 13 ${PAD.top + ih / 2})'>Loss</text>`);

        // the two landscapes
        s.push(`<path d='${curvePath(loss)}' fill='none' stroke='${INK}' stroke-width='2' stroke-linejoin='round'/>`);
        s.push(`<path class='val' d='${curvePath(valLoss)}' fill='none' stroke='${VAL}' stroke-width='2' stroke-linejoin='round' stroke-dasharray='7 4' opacity='${t}'/>`);

        // legend, in-figure: two line keys, text in ink
        const lx = PAD.left + 14, ly = PAD.top + 12;
        s.push(`<line x1='${lx}' y1='${ly - 4}' x2='${lx + 20}' y2='${ly - 4}' stroke='${INK}' stroke-width='2'/>`);
        s.push(`<text x='${lx + 26}' y='${ly}' fill='${INK}'>training loss</text>`);
        s.push(`<g class='val' opacity='${t}'>`);
        s.push(`<line x1='${lx + 110}' y1='${ly - 4}' x2='${lx + 130}' y2='${ly - 4}' stroke='${VAL}' stroke-width='2' stroke-dasharray='7 4'/>`);
        s.push(`<text x='${lx + 136}' y='${ly}' fill='${INK}'>validation loss <tspan fill='${MUTED}'>(training loss shifted by ε = ${EPS})</tspan></text>`);
        s.push(`</g>`);

        // runs: the trace back to the training loss, then the run itself
        const dots = [];
        RUNS.forEach((run, i) => {
            const x = f1(X(run.w)), y0 = Y(run.train), y1 = Y(run.val);
            const y = y0 + (y1 - y0) * t;
            s.push(`<line class='trace' data-i='${i}' x1='${x}' y1='${f1(y0)}' x2='${x}' y2='${f1(y)}' stroke='${VAL}' stroke-width='1' opacity='0.55'/>`);
            const data = interactive ? ` data-i='${i}' data-run='${run.valley}|${run.train.toFixed(2)}|${run.val.toFixed(2)}|${(run.val - run.train).toFixed(2)}'` : "";
            dots.push(`<circle class='run' cx='${x}' cy='${f1(y)}' r='3.4' fill='${RUN.fill}' stroke='${RUN.strong}' stroke-width='0.8'${data}/>`);
        });
        s.push(...dots);

        // valley labels; the mean gap only means something in the validation view
        for (const [v, key] of [[SHARP, "sharp"], [FLAT, "flat"]]) {
            const x = f1(X(v.m)), y = Y(loss(v.m)) + 24;
            s.push(`<text x='${x}' y='${f1(y)}' text-anchor='middle' fill='${INK}' font-size='11.5'>${key} minimum</text>`);
            s.push(`<text class='val' x='${x}' y='${f1(y + 15)}' text-anchor='middle' fill='${MUTED}' opacity='${t}'>mean gap ${meanGap(key).toFixed(2)}</text>`);
        }

        s.push("</svg>");
        return s.join("");
    }

    /* ---- node: emit the static fallback --------------------------------- */
    if (typeof window === "undefined") {
        process.stdout.write(draw(1, false) + "\n");
        return;
    }

    /* ---- browser: interactive ------------------------------------------- */
    const figure = document.querySelector("figure[data-figure='two-valleys']");
    if (!figure || !window.Fig) return;
    const mount = figure.querySelector(".fig-mount");
    mount.innerHTML = "";
    const wrap = Fig.el(mount, "div", "fig-panels");
    wrap.style.cssText = "position:relative;display:flex;justify-content:center;";
    const host = Fig.el(wrap, "div");
    host.style.cssText = `width:100%;max-width:${W}px`;
    host.innerHTML = draw(0, true);
    const svg = host.firstChild;
    svg.style.cssText = "width:100%;height:auto;display:block";

    const valNodes = [...svg.querySelectorAll(".val")];
    const runNodes = [...svg.querySelectorAll("circle.run")];
    const traceNodes = [...svg.querySelectorAll("line.trace")];

    // set the view to t in [0, 1] without redrawing: opacity for the validation
    // layer, a lerp between the two losses for every run and its trace
    function setView(t) {
        valNodes.forEach((n) => n.setAttribute("opacity", t));
        RUNS.forEach((run, i) => {
            const y = f1(Y(run.train) + (Y(run.val) - Y(run.train)) * t);
            runNodes[i].setAttribute("cy", y);
            traceNodes[i].setAttribute("y2", y);
        });
    }

    let shown = false, current = 0, raf = null;
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    const ease = (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
    const DURATION = 650;

    function animateTo(target) {
        cancelAnimationFrame(raf);
        if (reduced) { current = target; setView(current); return; }
        const from = current, dist = Math.abs(target - from);
        const t0 = performance.now();
        const step = (now) => {
            const u = Math.min(1, (now - t0) / (DURATION * dist || 1));
            current = from + (target - from) * ease(u);
            setView(current);
            if (u < 1) raf = requestAnimationFrame(step);
        };
        raf = requestAnimationFrame(step);
    }

    const panel = Fig.panel(mount);
    Fig.toggleGroup(panel.row("Validation"), null,
        [{ value: "hide", label: "Hide" }, { value: "show", label: "Show" }],
        "hide", (v) => { shown = v === "show"; animateTo(shown ? 1 : 0); });

    Fig.tooltip(wrap, "circle[data-run]", (c) => {
        const [valley, tl, vl, gap] = c.dataset.run.split("|");
        return `<strong>run in the ${valley} valley</strong><br>` +
            `train loss ${tl} &middot; val loss ${vl}` +
            (shown ? `<br>gap ${gap}` : "");
    });
})();
