# OSGovt.com

The project home page for **OSGovt (Open County Portal)**: what the software
does, pages for officials, IT staff and open-data users, and links to the
demo and the repository. Static files in `public/`, served by Cloudflare
Workers. The software itself lives at
[OSGovt/open-county-portal](https://github.com/OSGovt/open-county-portal).

Every factual claim on these pages comes from a file in that repository
(the README, `docs/officials/README.md`, `docs/admin/*.md`,
`docs/data/README.md`, `ACCESSIBILITY.md`). When those change, these pages
change; nothing is promised here that isn't written there.

## How it's checked

- **CI** (`.github/workflows/ci.yml`): on every push, serves the site
  locally with Cloudflare's dev server and runs `checks/journey.py`: the
  pages load, link to their docs, robots/sitemap/llms.txt agree, axe-core
  finds no WCAG 2.1 A/AA violations at desktop and 320px phone widths, and
  the 404 page offers a way home.
- **Deploy** (`deploy.yml`): after CI passes on `main`, `wrangler deploy`,
  then waits for the site to answer.
- **Live check** (`live-check.yml`): after each deploy and nightly, the same
  walk-through against https://osgovt.com, plus redirects and the demo's
  health. A failure opens an issue labeled `live-check`; the next pass
  closes it.

## Run it locally

```
cd deploy/cloudflare && npm ci && npx wrangler dev --port 8787
```

Then `python checks/journey.py --url http://127.0.0.1:8787` (needs
`pip install -r checks/requirements.txt`, `cd checks && npm ci`, and
`python -m playwright install chromium`).

## Contact

hello@osgovt.com · security reports to security@osgovt.com (privately)
