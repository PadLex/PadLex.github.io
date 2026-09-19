// Renders a batch of TeX strings to HTML. stdin: [{"tex": "...", "display": bool}, ...]
// stdout: {"version": "...", "html": ["...", ...]}
import katex from "katex";
import { createRequire } from "module";

const version = createRequire(import.meta.url)("katex/package.json").version;

let input = "";
process.stdin.on("data", (d) => (input += d));
process.stdin.on("end", () => {
    const items = JSON.parse(input);
    const html = items.map(({ tex, display }) =>
        katex.renderToString(tex, { displayMode: display, trust: true, throwOnError: true })
    );
    process.stdout.write(JSON.stringify({ version, html }));
});
