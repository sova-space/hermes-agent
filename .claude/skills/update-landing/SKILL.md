---
name: update-landing
description: Update the Sova landing page. Edit content in docs/index.md then run docs/build.py to rebuild docs/index.html. Use when features change, copy needs updating, or the page needs a refresh. Content lives in index.md — never edit index.html or template.html directly.
disable-model-invocation: false
---

The Sova landing page uses a content/template split:

| File | Role |
|------|------|
| `docs/index.md` | All copy, data, and text — edit this |
| `docs/template.html` | CSS, layout, animations, JS — do not edit |
| `docs/build.py` | Renders md + template → index.html |
| `docs/index.html` | Generated output — do not edit directly |

## To update content

1. Edit `docs/index.md` — change copy, update features, fix data values
2. Run `python docs/build.py` from the repo root
3. Open `docs/index.html` in browser to verify
4. Commit both `index.md` and `index.html`

## To redesign

Edit `docs/template.html` — CSS variables, layout, animations.
Then run `python docs/build.py` to regenerate.

## Sync rule

When features change in `agents/finance/README.md`, update `docs/index.md` in the same PR.
The README is the source of truth; the landing page is derived from it.

## Dependencies

```
pip install python-frontmatter markdown
```
