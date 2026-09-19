# Building the blog

From the repository root, with Python 3 and Node.js installed:

```sh
npm ci
npm run build:blog
```

This builds only `docs/blog/`; it does not rebuild or change the résumé.
GitHub Pages publishes the committed `docs/` directory from `main`.
The KaTeX stylesheet and fonts live in `docs/assets/katex/`.

Post content lives in `content/blogposts/<id>/post.md`, with metadata in
`post.json`. The metadata's `slug` controls the public URL, independently of
the source directory name. An optional `author` overrides the résumé name.

The Flat Minima post is an unlisted draft at
`/blog/flatminima-draft-e41a424c4caf8705/`. Its `draft: true` metadata emits
`<meta name="robots" content="noindex">`. Keep it out of homepage links and
sitemaps while it is a draft. Do not block it in `robots.txt`: crawlers need
to read the `noindex` tag. The draft is public to anyone with its URL, and
its source and location are visible in this public repository.

When publishing the finished article, set `draft` to `false`, choose its
final slug, rebuild, and add the résumé link separately. The build does not
delete old output directories; explicitly remove the old draft directory
from the deployed files if its URL should stop working.
