/* Shared figure helpers for blog posts — labeled toggle groups, a slider with an
   optional play button, legend chips, and a delegated tooltip. Vanilla JS, no deps.
   Per-post figure scripts own their state and drawing; these helpers only build the
   standard controls and report changes. Copied to docs/blog/fig.js by the build. */
window.Fig = (function () {
    "use strict";

    function el(parent, tag, className, html) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (html !== undefined) node.innerHTML = html;
        parent.appendChild(node);
        return node;
    }

    /* A contained control panel above a figure. Rows share an aligned small-caps
       label column: const p = Fig.panel(mount); Fig.toggleGroup(p.row("X Axis"), ...).
       Place a reset via Fig.button(p.root, "Reset", fn).className = "reset" —
       it docks to the panel's top-right corner. */
    function panel(parent) {
        const root = el(parent, "div", "fig-ctl-panel");
        return {
            root,
            row(label) {
                const r = el(root, "div", "ctl-row");
                if (label) el(r, "span", "ctl-label", label);
                return el(r, "span", "ctl-content");
            },
        };
    }

    /* Labeled group of mutually exclusive options.
       toggleGroup(row, "Learning Rate", [{value, label}, ...], initial, onChange)
       -> { value, set(v) }  (set() updates the UI without firing onChange) */
    function toggleGroup(parent, label, options, initial, onChange) {
        const wrap = el(parent, "span", "ctl-group");
        if (label) el(wrap, "span", "ctl-label", label);
        const seg = el(wrap, "span", "seg");
        seg.setAttribute("role", "group");
        if (label) seg.setAttribute("aria-label", label);
        const api = {
            value: initial,
            set(v) {
                api.value = v;
                seg.querySelectorAll("button").forEach((b) =>
                    b.classList.toggle("active", b.dataset.value === v));
            },
        };
        for (const opt of options) {
            const b = el(seg, "button", null, opt.label);
            b.type = "button";
            b.dataset.value = opt.value;
            b.addEventListener("click", () => { api.set(opt.value); onChange(opt.value); });
        }
        api.set(initial);
        return api;
    }

    /* Discrete slider with an optional play button (hidden under prefers-reduced-
       motion) and a tick mark per step. slider(row, {label, min, max, initial,
       playMs, loop, holdMs, format, printValue, onChange})
       -> {value, playing, set(v), play(), stop()}.
       play() drives the same run as the button, so a figure can start itself.
       A run stops on the last step unless loop is set, in which case it holds
       there for holdMs (three steps by default) and starts over. */
    function slider(parent, opts) {
        const wrap = el(parent, "span", "ctl-group ctl-slider");
        let timer = null;
        const play = opts.playMs ? el(wrap, "button", "play", "&#9654;") : null;
        const track = el(wrap, "span", "slider-track");
        const range = el(track, "input");
        range.type = "range";
        range.min = opts.min;
        range.max = opts.max;
        range.step = opts.step || 1;
        const ticks = el(track, "span", "slider-ticks");
        const n = Math.floor((opts.max - opts.min) / (opts.step || 1)) + 1;
        for (let i = 0; i < n; i++) el(ticks, "span", "tick");
        const labelEl = el(wrap, "span", "slider-value");
        const format = opts.format || ((v) => `${v}`);
        const holdMs = opts.holdMs || opts.playMs * 3;
        const api = {
            value: opts.initial,
            playing: false,
            set(v) {
                api.value = v;
                range.value = v;
                labelEl.textContent = format(v);
            },
            play() {
                if (timer) return;
                api.playing = true;
                if (play) play.innerHTML = "&#10074;&#10074;";
                timer = setTimeout(advance, opts.playMs);
            },
            stop() {
                clearTimeout(timer);
                timer = null;
                api.playing = false;
                if (play) play.innerHTML = "&#9654;";
            },
        };

        // one step per tick, wrapping past the end; stop() before onChange so the
        // caller's redraw already sees the run as finished on its last frame
        function advance() {
            api.set(api.value >= opts.max ? opts.min : api.value + 1);
            const end = api.value >= opts.max;
            if (end && !opts.loop) api.stop();
            else timer = setTimeout(advance, end ? holdMs : opts.playMs);
            opts.onChange(api.value);
        }
        range.setAttribute("aria-label", opts.label);
        range.addEventListener("input", () => { api.stop(); api.set(+range.value); opts.onChange(api.value); });
        if (play) {
            play.type = "button";
            play.setAttribute("aria-label", `play through ${opts.label}s`);
            if (matchMedia("(prefers-reduced-motion: reduce)").matches) play.style.display = "none";
            play.addEventListener("click", () => (timer ? api.stop() : api.play()));
        }
        /* Printing keeps whatever step the reader chose — except mid-run, which
           would land on an arbitrary frame of the sweep; that prints at
           printValue (the figure's resting step) and picks the run back up. */
        if (opts.printValue != null) {
            let resume = null;
            addEventListener("beforeprint", () => {
                if (!api.playing) return;
                resume = api.value;
                api.stop();
                api.set(opts.printValue);
                opts.onChange(api.value);
            });
            addEventListener("afterprint", () => {
                if (resume === null) return;
                api.set(resume);
                resume = null;
                opts.onChange(api.value);
                api.play();
            });
        }

        api.set(opts.initial);
        return api;
    }

    function button(parent, label, onClick) {
        const b = el(parent, "button", null, label);
        b.type = "button";
        b.addEventListener("click", onClick);
        return b;
    }

    /* Clickable legend chips. items: [{name, fill, strong}]; onToggle(name).
       -> { update(name, {off, extra}) } */
    function legend(parent, items, onToggle) {
        const box = el(parent, "div", "fig-legend");
        const chips = {};
        for (const item of items) {
            const chip = el(box, "button", "chip");
            chip.type = "button";
            chip.innerHTML =
                `<span class="dot" style="background:${item.fill};box-shadow:inset 0 0 0 1.5px ${item.strong}"></span>` +
                `<span>${item.name}</span> <span class="r-val"></span>`;
            chip.addEventListener("click", () => onToggle(item.name));
            chips[item.name] = chip;
        }
        return {
            update(name, state) {
                chips[name].classList.toggle("off", !!state.off);
                chips[name].querySelector(".r-val").textContent = state.extra || "";
            },
        };
    }

    /* Delegated tooltip over `selector` elements inside `wrap` (wrap must be
       position:relative). contentFn(element) returns html or null. */
    function tooltip(wrap, selector, contentFn) {
        const tip = el(wrap, "div", "fig-tooltip");
        tip.hidden = true;
        wrap.addEventListener("pointerover", (e) => {
            const target = e.target.closest(selector);
            if (!target) return;
            const html = contentFn(target);
            if (html === null) return;
            tip.innerHTML = html;
            tip.hidden = false;
        });
        wrap.addEventListener("pointermove", (e) => {
            if (tip.hidden) return;
            const box = wrap.getBoundingClientRect();
            tip.style.left = Math.min(e.clientX - box.left + 14, box.width - 180) + "px";
            tip.style.top = e.clientY - box.top + 14 + "px";
        });
        wrap.addEventListener("pointerout", (e) => {
            if (e.target.closest(selector)) tip.hidden = true;
        });
        return tip;
    }

    /* Tick-label number formatting: 3 significant digits, no trailing decimal zeros. */
    function fmt(v) {
        return (+v).toPrecision(3).replace(/(\.\d*?)0+(?=$|e)/, "$1").replace(/\.(?=$|e)/, "");
    }

    return { el, panel, toggleGroup, slider, button, legend, tooltip, fmt };
})();
