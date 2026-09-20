Hey! This is my personal website. Check it out at [https://padula.dev](https://padula.dev). I hand-made the design in pure HTML, JS, and CSS. I've also built a rickety template engine in Python to automatically convert a JSON description of my resume (`content/resume.json`) to a static website. I'm especially proud of the highlight markers - feel free to steal the CSS from `src/marker_src.txt` if you need something similar. Please don't use any other part of this repo, though. I usually keep my work open-source, but in this case I would like my personal website's style to remain mine.

## Development

Install [`uv`](https://docs.astral.sh/uv/) and [Node.js](https://nodejs.org/), then install the locked Python and JavaScript environments:

```sh
uv sync
npm ci
```

Build the site into `docs/`:

```sh
npm run build
```

Start the live-reloading development server:

```sh
npm run dev
```
