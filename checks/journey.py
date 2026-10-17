#!/usr/bin/env python3
"""Walk through osgovt.com the way a visitor does. Exit 1 if any step fails.

  home          the page loads with its title and heading, and links to the demo and source
  pages         For officials, For IT and Open data each load with their heading and a link back to the docs
  machine       robots.txt, sitemap.xml and llms.txt answer and agree with each other
  accessibility no axe-core WCAG 2.1 A/AA violations on every page, at desktop and 320px phone width,
                and no sideways scrolling on a phone
  not-found     a missing page answers 404 with a way home
  addresses     (live site only) http:// and www. go to https://osgovt.com
  demo          (live site only) the demo county the pages link to is answering

Usage:
  python3 checks/journey.py --url https://osgovt.com --summary journey.md
  python3 checks/journey.py --url http://127.0.0.1:8080        # a local copy
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import httpx

UA = "OSGovt-LiveCheck/1.0 (+https://github.com/OSGovt/osgovt.com)"
AXE = Path(__file__).resolve().parent / "node_modules" / "axe-core" / "axe.min.js"
results: list[tuple[str, bool, str]] = []


def add(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}", flush=True)


def wake(base: str, wait_s: int) -> bool:
    start, last = time.time(), ""
    while time.time() - start < wait_s:
        try:
            r = httpx.get(base + "/", headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 200:
                add("wake", True, f"answered in {time.time() - start:.0f} s")
                return True
            last = f"HTTP {r.status_code}"
        except httpx.HTTPError as exc:
            last = type(exc).__name__
        time.sleep(5)
    add("wake", False, f"no answer within {wait_s} s (last: {last})")
    return False


def run(base: str, live: bool) -> None:
    from playwright.sync_api import Error as PWError
    from playwright.sync_api import sync_playwright

    host = urlparse(base).netloc
    axe_source = AXE.read_text(encoding="utf-8") if AXE.exists() else None
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        ctx = browser.new_context(user_agent=UA, bypass_csp=True)
        ctx.set_default_timeout(30_000)
        page = ctx.new_page()

        def step(name, fn):
            try:
                ok, detail = fn()
                if ok and urlparse(page.url).netloc not in ("", host):
                    ok, detail = False, f"ended up off the site at {page.url}"
                add(name, ok, detail)
            except (PWError, AssertionError, ValueError, httpx.HTTPError) as exc:
                msg = str(exc).strip().splitlines()[0][:200] if str(exc).strip() else type(exc).__name__
                add(name, False, f"{msg} (at {page.url})")

        def home():
            page.goto(base + "/")
            h1 = page.get_by_role("heading", level=1).inner_text()
            demo = page.get_by_role("link", name="Try the demo county").first.get_attribute("href")
            src = page.get_by_role("navigation", name="Main").get_by_role("link", name="Source").get_attribute("href")
            ok = (page.title().startswith("OSGovt") and "open-source" in h1.lower()
                  and demo == "https://utopia.osgovt.com" and src == "https://github.com/OSGovt/open-county-portal")
            return ok, f"title {page.title()!r}; heading {h1!r}; demo {demo}; source {src}"

        PAGES = {"/for-officials/": ("For elected officials", "docs/officials/README.md"),
                 "/for-it/": ("For IT staff", "docs/admin/README.md"),
                 "/open-data/": ("Open data and API", "docs/data/README.md")}

        def pages():
            bad = []
            for path, (heading, doc) in PAGES.items():
                r = page.goto(base + path)
                h1 = page.get_by_role("heading", level=1).inner_text()
                hrefs = " ".join(a.get_attribute("href") or "" for a in page.locator("main a").all())
                if r is None or r.status != 200: bad.append(f"{path}: HTTP {r.status if r else '?'}")
                elif not h1.startswith(heading): bad.append(f"{path}: heading {h1!r}")
                elif doc not in hrefs: bad.append(f"{path}: no link to {doc}")
            return not bad, "all three pages load and link to their docs" if not bad else "; ".join(bad)

        def machine():
            robots = httpx.get(base + "/robots.txt", headers={"User-Agent": UA}, timeout=30)
            sitemap = httpx.get(base + "/sitemap.xml", headers={"User-Agent": UA}, timeout=30)
            llms = httpx.get(base + "/llms.txt", headers={"User-Agent": UA}, timeout=30)
            locs = re.findall(r"<loc>https://osgovt\.com(/[^<]*)</loc>", sitemap.text)
            bad = []
            if robots.status_code != 200 or "Sitemap: https://osgovt.com/sitemap.xml" not in robots.text: bad.append("robots.txt")
            if sitemap.status_code != 200 or set(locs) != {"/", *PAGES}: bad.append(f"sitemap lists {locs}")
            if llms.status_code != 200 or not llms.text.startswith("# OSGovt") or any(p not in llms.text for p in PAGES):
                bad.append("llms.txt")
            return not bad, "robots, sitemap and llms.txt agree" if not bad else "; ".join(bad)

        def accessibility():
            if axe_source is None:
                return False, "axe-core isn't installed (run: cd checks && npm ci)"
            problems = []
            for label, width in (("desktop", 1280), ("phone", 320)):
                page.set_viewport_size({"width": width, "height": 800})
                for path in ("/", *PAGES, "/no-such-page"):
                    page.goto(base + path)
                    page.evaluate(axe_source)
                    found = page.evaluate("""async () => (await axe.run(document, {runOnly: {type: 'tag',
                        values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}})).violations
                        .map(v => v.id + ' (' + v.nodes.length + ')')""")
                    problems += [f"{path} {label}: {v}" for v in found]
                    if width == 320:
                        sw = page.evaluate("document.documentElement.scrollWidth")
                        if sw > 320:
                            problems.append(f"{path} phone: page is {sw}px wide")
            page.set_viewport_size({"width": 1280, "height": 800})
            return not problems, "no WCAG 2.1 AA violations on any page; fits a 320px phone" if not problems else "; ".join(problems)

        def not_found():
            r = page.goto(base + "/no-such-page")
            ok = r is not None and r.status == 404 and page.get_by_role("link", name="Go to the OSGovt home page").count() == 1
            return ok, f"HTTP {r.status if r else '?'}"

        steps = [("home", home), ("pages", pages), ("machine", machine),
                 ("accessibility", accessibility), ("not-found", not_found)]
        for name, fn in steps:
            step(name, fn)
        browser.close()

    if live:
        with httpx.Client(headers={"User-Agent": UA}, timeout=30, follow_redirects=False) as client:
            try:
                bad = []
                for start in (f"http://{host}/", f"https://www.{host}/", f"http://www.{host}/"):
                    r = client.get(start)
                    if r.status_code not in (301, 308) or r.headers.get("location") != f"https://{host}/":
                        bad.append(f"{start} -> {r.status_code} {r.headers.get('location')}")
                add("addresses", not bad, "http:// and www. redirect to https://" + host if not bad else "; ".join(bad))
            except httpx.HTTPError as exc:
                add("addresses", False, type(exc).__name__)
            for name, health in (("demo", "https://utopia.osgovt.com/healthz"),):
                try:
                    r = client.get(health)
                    add(name, r.status_code == 200, f"{urlparse(health).netloc}/healthz answered {r.status_code}")
                except httpx.HTTPError as exc:
                    add(name, False, type(exc).__name__)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Walk through osgovt.com the way a visitor does.")
    ap.add_argument("--url", required=True)
    ap.add_argument("--wait", type=int, default=120)
    ap.add_argument("--summary", help="Also write the results as a Markdown table to this file")
    args = ap.parse_args(argv)
    base = args.url.rstrip("/")
    live = urlparse(base).scheme == "https"
    if wake(base, args.wait):
        run(base, live)
    failed = [r for r in results if not r[1]]
    if args.summary:
        with open(args.summary, "w", encoding="utf-8") as fh:
            fh.write(f"Walk-through of {base}\n\n| Step | Result | Detail |\n|---|---|---|\n")
            fh.writelines(f"| {n} | {'PASS' if ok else '**FAIL**'} | {d.replace('|', '/')} |\n" for n, ok, d in results)
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
