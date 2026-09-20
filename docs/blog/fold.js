/* Paper-fold sections. Styling and every tunable live in fold.css; this file only
 * measures, mirrors, and animates.
 *
 * Markup (from parser.py):
 *   section.fold > div.fold-body > div.fold-panel.fold-panel-lead > div.fold-content
 *                                > span.fold-crease (top, mid, bottom)
 *               > button.fold-toggle
 *
 * The content sits in the lead panel, flat and unclipped when open. Closed, it is cut at
 * two places. --fold-lead is the first: everything above it stays flat on the page. With
 * a mid-paragraph %%startfold%% that cut falls part-way down the letters of the line the
 * marker landed on, so the fold runs straight through the text — glyph tops flat, glyph
 * bottoms tilting away on the flap below, meeting on the hinge. Which line that is
 * depends on how the text wrapped, so it is measured here and re-measured on reflow.
 *
 * The strip below the lead is split at its midpoint into two flaps that hinge
 * backwards, meeting at the middle crease (a Z-fold); each is a clone of the content
 * shifted up to its own slice and clipped to it. A single value t in [0, 1] (0 flat
 * shut, 1 open) goes out as --fold-t plus --fold-deg / --fold-cos / --fold-sin, which
 * fold.css turns into geometry and shading.
 *
 * A closed fold rests at --fold-rest, shut flat by default. That resting geometry is
 * fixed: nothing here runs while you scroll. The only things that move it are a click
 * (which opens it fully, or folds it back to rest) and, with a mouse, hovering it, which
 * eases --fold-hover-bonus in on a sine so the seam swells into a peek of the paper.
 */
(function () {
    "use strict";

    const canHover = window.matchMedia("(hover: hover)").matches;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const easeInOut = p => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);

    // The hover peek rides this instead: a half cosine, so it pulls away from rest and
    // settles into the peek with zero speed at both ends and its quickest move in the
    // middle. Reversed part-way — cursor out before it has arrived — it keeps whatever
    // speed it had, because the same curve is read backwards from wherever it got to.
    const easeSine = p => 0.5 - 0.5 * Math.cos(Math.PI * p);

    const folds = Array.from(document.querySelectorAll(".fold"));

    // Lay the folds out flat until DOMContentLoaded so the template's marker-breaking pass
    // (which needs untransformed line boxes) sees normal geometry.
    folds.forEach(fold => fold.classList.add("is-measuring"));

    document.addEventListener("DOMContentLoaded", () => folds.forEach(init));

    function readKnobs(fold) {
        const cs = getComputedStyle(fold);
        const num = (name, fallback) => {
            const v = parseFloat(cs.getPropertyValue(name));
            return Number.isFinite(v) ? v : fallback;
        };
        return {
            rest: Math.min(1, Math.max(0, num("--fold-rest", 0.1))),
            liftAt: num("--fold-lift-at", 0.5),
            hoverBonus: num("--fold-hover-bonus", 0.5),
            hoverMs: num("--fold-hover-ms", 520),
            unhoverMs: num("--fold-unhover-ms", 420),
            openMs: num("--fold-open-ms", 720),
            closeMs: num("--fold-close-ms", 560),
        };
    }

    function init(fold) {
        const button = fold.querySelector(".fold-toggle");
        const body = fold.querySelector(".fold-body");
        const leadPanel = fold.querySelector(".fold-panel-lead");
        const content = leadPanel && leadPanel.querySelector(".fold-content");
        if (!button || !body || !content) return;

        let knobs = readKnobs(fold);   // re-read on every measure; see measure()

        // The two flaps are clones of the content, each shifted up to its own slice and
        // clipped to it (CSS). Inserted before the creases so those keep painting on top.
        const flaps = ["fold-panel-top", "fold-panel-bottom"].map(role => {
            const flap = document.createElement("div");
            flap.className = "fold-panel " + role;
            flap.setAttribute("aria-hidden", "true");
            flap.inert = true;
            const copy = content.cloneNode(true);
            copy.querySelectorAll("[id]").forEach(el => el.removeAttribute("id"));
            copy.querySelectorAll("mark").forEach(m => m.classList.add("animate-highlight"));
            flap.appendChild(copy);
            body.insertBefore(flap, body.querySelector(".fold-crease"));
            return flap;
        });

        // A mid-paragraph %%startfold%%; absent for a fold that starts at a block edge.
        const lift = content.querySelector(".fold-lift");
        fold.classList.toggle("has-lead", !!lift);

        const state = {
            t: knobs.rest,   // current fold amount, 0 flat shut .. 1 open
            open: false,     // the clicked state
            hoverP: 0,       // raw hover progress, 0 off .. 1 fully peeked
            hoverTo: 0,      // where it is headed: 1 while the cursor is on it
            tween: null,     // {from, to, start, dur} while a click animation runs
            raf: 0,
            last: 0,
        };

        // Where a closed fold sits: its resting amount, plus whatever the cursor has
        // added. The raw progress is what gets animated; the sine shapes it on the way out.
        const resting = () =>
            Math.min(1, knobs.rest + knobs.hoverBonus * easeSine(state.hoverP));

        // Where the paper bends, as an offset down the content. The marker picks a line;
        // the crease then runs straight across it, part-way down the letters. The lead
        // panel is clipped there and the flap below shows the very same content shifted
        // up by the same amount, so each glyph's top half stays flat on the page while
        // its bottom half tilts away, the two meeting exactly on the hinge.
        //
        // The marker is an empty inline, so its own box is the font's content area at
        // that spot: top at the ascenders, bottom under the descenders. Cutting a
        // fraction of the way down that box is what --fold-lift-at picks.
        function measureLead() {
            if (!lift) return 0;
            let line = lift.getBoundingClientRect();
            if (!line.height) {
                // no box of its own (rare); fall back to the text following it
                const range = document.createRange();
                range.setStartAfter(lift);
                range.setEnd(content, content.childNodes.length);
                line = Array.from(range.getClientRects()).find(r => r.height > 0);
                if (!line) return 0;
            }
            const y = line.top + line.height * knobs.liftAt;
            return Math.max(0, y - content.getBoundingClientRect().top);
        }

        function measure() {
            // The knobs come back here rather than being read once, so the geometry ones
            // (--fold-rest, --fold-lift-at) can be tuned by eye against a live page.
            knobs = readKnobs(fold);
            fold.style.setProperty("--fold-h", content.offsetHeight + "px");
            fold.style.setProperty("--fold-lead", measureLead().toFixed(2) + "px");
            if (!state.open && !state.tween) set(resting());
        }

        function set(t) {
            state.t = t;
            const deg = (1 - t) * 90;
            const rad = deg * Math.PI / 180;
            fold.style.setProperty("--fold-t", t.toFixed(5));
            fold.style.setProperty("--fold-deg", deg.toFixed(3) + "deg");
            fold.style.setProperty("--fold-cos", Math.cos(rad).toFixed(5));
            fold.style.setProperty("--fold-sin", Math.sin(rad).toFixed(5));
            fold.classList.toggle("is-open", t >= 1);
            body.inert = t < 1;
        }

        // Runs only for a click animation and to ease the hover bonus in and out;
        // at rest, and while scrolling, nothing here is scheduled at all.
        function frame(now) {
            state.raf = 0;
            const dt = state.last ? Math.min(100, now - state.last) : 16;
            state.last = now;

            if (state.tween) {
                const tw = state.tween;
                const p = Math.max(0, Math.min(1, (now - tw.start) / tw.dur));
                set(tw.from + (tw.to - tw.from) * easeInOut(p));
                if (p >= 1) state.tween = null;
            } else if (state.hoverP !== state.hoverTo) {
                // The progress moves at a constant rate, so a peek from shut takes the
                // whole --fold-hover-ms and one the cursor turns around on takes only
                // the share of it that is left to travel.
                const dur = Math.max(1, state.hoverTo ? knobs.hoverMs : knobs.unhoverMs);
                const step = dt / dur;
                state.hoverP = state.hoverTo > state.hoverP
                    ? Math.min(state.hoverTo, state.hoverP + step)
                    : Math.max(state.hoverTo, state.hoverP - step);
                if (!state.open) set(resting());
            }

            if (state.tween || state.hoverP !== state.hoverTo) wake();
            else state.last = 0;
        }

        function wake() {
            if (!state.raf) state.raf = requestAnimationFrame(frame);
        }

        function toggle() {
            state.open = !state.open;
            button.setAttribute("aria-expanded", String(state.open));
            button.setAttribute("aria-label", state.open ? "Fold section" : "Unfold section");
            // Shutting goes the whole way back to --fold-rest, not to resting(): the
            // cursor is on the label at the moment of the click, so resting() is the
            // hovered peek, and stopping there shut the paper in two goes — one tween
            // down to the peek, then a wait for the pointer to fall off the shrinking
            // section, then the peek easing out on its own. Dropping the preview here
            // makes it one move. It stays off until the cursor leaves and comes back:
            // nothing re-aims it, and aim() turns down anything that arrives while the
            // paper is still shutting, so it cannot swell straight back up under a
            // pointer that has not moved.
            const to = state.open ? 1 : knobs.rest;
            if (!state.open) { state.hoverP = 0; state.hoverTo = 0; }
            if (reduceMotion) { state.tween = null; set(to); return; }
            state.tween = {
                from: state.t, to,
                start: performance.now(),
                dur: state.open ? knobs.openMs : knobs.closeMs,
            };
            wake();
        }

        // Mouse only: resting on the seam swells it open by --fold-hover-bonus.
        // Always wired, and the bonus is applied in resting() from whatever measure()
        // last read, not captured here, so setting it to 0 (or back) in fold.css takes
        // effect without a reload like every other knob. A bonus of 0 leaves resting()
        // at --fold-rest whatever the progress does, so the fold simply never moves.
        if (canHover && !reduceMotion) {
            const shutting = () => state.tween && !state.open;
            const aim = to => {
                if (to && shutting()) return;
                if (state.hoverTo === to) return;
                state.hoverTo = to;
                wake();
            };
            // Only the folded paper and its label invite a preview. The flat lead
            // paragraph above the crease is outside the hover target. Keep a small
            // band around the seam so a fully shut fold is still easy to point at.
            const previewAt = e => {
                const rect = body.getBoundingClientRect();
                const lead = parseFloat(fold.style.getPropertyValue("--fold-lead")) || 0;
                const onPaper = e.clientX >= rect.left && e.clientX <= rect.right
                    && e.clientY >= rect.top + lead - 4 && e.clientY <= rect.bottom + 4;
                aim(!state.open && (onPaper || button.contains(e.target)) ? 1 : 0);
            };
            fold.addEventListener("mouseenter", previewAt);
            fold.addEventListener("mousemove", previewAt);
            fold.addEventListener("mouseleave", () => aim(0));
        }

        // Is the pointer over one of the three creases? The bands are pointer-events:
        // none and stay that way, so the text under them keeps its selection and its
        // links; their boxes are hit-tested here instead. That is what lets a crease
        // fold the paper shut without the band swallowing everything else the reader
        // might want to do with the line it happens to cross.
        const creases = Array.from(body.querySelectorAll(".fold-crease"));
        const onCrease = e => creases.some(c => {
            const r = c.getBoundingClientRect();
            return e.clientY >= r.top && e.clientY <= r.bottom
                && e.clientX >= r.left && e.clientX <= r.right;
        });

        // Closed: the whole section (the seam and its label) opens it.
        // Open: the label folds it back, and so does any of the three creases — but
        // only on a plain click on the paper, so a link still follows and the click
        // that ends a drag across the text does not fold the page away mid-sentence.
        fold.addEventListener("click", e => {
            if (!state.open || button.contains(e.target)) return toggle();
            if (!onCrease(e) || e.target.closest("a, button, input, textarea, select, label")) return;
            const sel = window.getSelection();
            if (sel && !sel.isCollapsed) return;
            toggle();
        });

        // ...and the cursor for it, which has to go on the section because the band
        // taking no pointer events cannot carry one of its own.
        if (canHover) {
            fold.addEventListener("mousemove", e => {
                fold.classList.toggle("is-on-crease", state.open && onCrease(e));
            });
            fold.addEventListener("mouseleave", () => fold.classList.remove("is-on-crease"));
        }

        // Keep the measurements in sync with reflow. A narrower viewport rewraps the
        // paragraph, which moves the marker onto a different line, so the lead has to be
        // taken again — and a rewrap can leave the height unchanged, which the observer
        // would not report, hence the resize listener too.
        if (window.ResizeObserver) new ResizeObserver(measure).observe(content);
        window.addEventListener("resize", measure);

        measure();
        fold.classList.remove("is-measuring");
        set(resting());
    }
})();
