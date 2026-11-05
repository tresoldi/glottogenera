"""
Browser check of the explorer: every page renders without errors, the
threshold recuts the genera, maps draw areas, and the
exports download. Usage (serve web/ first, e.g. python -m http.server -d web):

    uv run --no-project --with playwright python web/tests/browser.py http://127.0.0.1:8811/ [screenshots-dir]
"""

import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/") + "/"
SHOTS = Path(sys.argv[2]) if len(sys.argv) > 2 else None
PAGES = ["", "genera", "languages", "families", "map", "wals", "downloads", "about",
         "genus/germ1287", "genus/cent2060", "language/stan1293", "family/indo1319", "family/sino1245"]


def main() -> int:
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))

        # the development notice opens on the first visit of a session, and only then
        page.goto(BASE)
        page.wait_for_selector("dialog#notice[open]", timeout=20000)
        page.click("dialog#notice button")
        page.goto(BASE + "#/genera")
        page.wait_for_timeout(500)
        assert not page.is_visible("dialog#notice"), "notice shown twice"
        print("ok notice")

        for path in PAGES:
            page.goto(BASE + "#/" + path)
            page.wait_for_selector("main h1", timeout=20000)
            page.wait_for_timeout(1500 if path.startswith(("map", "genus", "family", "language")) else 300)
            h1 = page.inner_text("main h1")
            assert "went wrong" not in h1 and "Could not" not in h1, (path, h1)
            if SHOTS:
                SHOTS.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(SHOTS / f"{path.replace('/', '_') or 'home'}.png"))
            print("ok", path or "home", "|", h1)

        # the formal definition renders with MathML, and its citation links stay on the page
        page.goto(BASE + "#/about")
        page.wait_for_selector("#definition math", timeout=20000)
        assert page.locator("#definition math").count() > 50
        page.locator('#definition a[href^="#ref-"]').first.click()
        page.wait_for_timeout(300)
        assert page.url.endswith("#/about"), page.url
        print("ok definition")

        # the released threshold gives the released number of genera; another recuts
        page.goto(BASE + "#/")
        page.wait_for_selector(".stats")
        released = page.inner_text(".stats div b")
        page.goto(BASE + "#/?d=0.750")
        page.wait_for_timeout(500)
        other = page.inner_text(".stats div b")
        assert released == "1,190" and other != released, (released, other)
        print("ok threshold", released, "->", other)

        # the mean family ARI at the released threshold is the release's (params.json)
        page.goto(BASE + "#/wals")
        page.wait_for_selector(".stats")
        mean = page.inner_text(".stats div b")
        assert mean == "0.654", mean
        print("ok WALS mean ARI", mean)

        # the map draws with and without areas, and exports download
        for areas in ["", "?a=none", "?r=50", "?r=3000"]:
            page.goto(BASE + "#/map" + areas)
            page.wait_for_selector(".leaflet-container")
            page.wait_for_timeout(2500)
            print("ok map", areas or "areas")
        # a new threshold keeps the zoomed view; the World button resets it
        page.goto(BASE + "#/family/indo1319")
        page.wait_for_timeout(2500)
        page.evaluate("void window.glottogeneraMaps[0].setView([50, 10], 6)")
        page.fill("#delta-num", "0.7")
        page.press("#delta-num", "Enter")
        page.wait_for_timeout(2500)
        zoom = page.evaluate("window.glottogeneraMaps[0].getZoom()")
        assert zoom == 6 and "0.700" in page.inner_text("main"), zoom
        page.click("a.world")
        page.wait_for_timeout(500)
        assert page.evaluate("window.glottogeneraMaps[0].getZoom()") == 2
        print("ok view kept across thresholds, world button")

        page.goto(BASE + "#/map?f=indo1319&r=75")
        page.wait_for_timeout(2000)
        for kind in ["geojson", "csv", "langs"]:
            with page.expect_download() as d:
                page.click(f'button[data-x="{kind}"]')
            path = d.value.path()
            text = Path(path).read_text(encoding="utf-8")
            if kind == "geojson":
                fc = json.loads(text)
                assert fc["features"] and all(f["geometry"]["coordinates"] for f in fc["features"])
                assert {f["properties"]["radius_km"] for f in fc["features"]} == {75}
            else:
                assert text.count("\n") > 10
            print("ok export", kind, d.value.suggested_filename)

        page.goto(BASE + "#/genera")
        page.wait_for_selector("tbody tr")
        with page.expect_download() as d:
            page.click("button.csv")
        assert Path(d.value.path()).read_text().count("\n") == 1191
        print("ok genera CSV")

        # phone width: no horizontal page scroll
        mobile = browser.new_page(viewport={"width": 390, "height": 800})
        mobile.add_init_script("sessionStorage.setItem('glottogenera-notice', 'seen')")
        for path in ["", "genera", "genus/germ1287", "map", "about"]:
            mobile.goto(BASE + "#/" + path)
            mobile.wait_for_timeout(1200)
            sw = mobile.evaluate("document.documentElement.scrollWidth")
            assert sw <= 390, (path, sw)
        print("ok mobile")
        browser.close()
    for e in errors:
        print(e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
