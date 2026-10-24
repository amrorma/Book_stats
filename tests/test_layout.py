"""
test_layout.py

Automated layout checks of the built app in headless Chromium, at a desktop
and two phone viewport sizes. For a set of roots, in both the folded view
(one plum "others" petal) and the unfolded view (all forms in outer rings):

    * no overlap between labels, between labels and petals, or with the ring
    * centre word and count stay inside the centre disc
    * one petal per distinct word form when unfolded
    * every frequency number lies inside its petal
    * every small-petal label lies inside its petal
    * no horizontal page scroll
    * no JavaScript errors

Screenshots are written to build/screenshots/. The exit code is 1 when any
check fails, so the script can be used in CI.

Usage (from the repository root)
    pip install playwright && python3 -m playwright install chromium
    python3 tests/test_layout.py ["متصفح القرآن.html"]
"""

# ---------------------------------------------------------------------------
# Required libraries
# ---------------------------------------------------------------------------
import asyncio    # Playwright async API
import json       # quoting Arabic strings for page.evaluate
import sys        # arguments and exit code
from pathlib import Path  # path handling

from playwright.async_api import async_playwright  # headless browser

# ---------------------------------------------------------------------------
# Input / output paths and parameters
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
APP_HTML = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO_ROOT / "متصفح القرآن.html"
SCREENSHOT_DIR = REPO_ROOT / "build" / "screenshots"
ROOTS = ["ءتي", "علم", "ءخذ", "قول", "رحم", "صبر", "نور", "قلب", "كفر", "زلزل"]  # large to tiny
VIEWPORTS = (("pc", 1366, 900), ("phone", 390, 844), ("small-phone", 360, 740))

# JavaScript: frequency numbers that are not inside their petal
NUMBERS_OUTSIDE_JS = """(() => {
  const nums = [...document.querySelectorAll('#gNums text')], pet = [...document.querySelectorAll('#gPetals .petal')];
  return nums.filter((t, i) => {
    const bb = t.getBBox();
    const inside = (x, y) => { const q = new DOMPoint(x, y).matrixTransform(pet[i].getCTM().inverse().multiply(t.getCTM()));
                               return pet[i].isPointInFill(new DOMPoint(q.x, q.y)); };
    return !(inside(bb.x + 2, bb.y + bb.height / 2) && inside(bb.x + bb.width - 2, bb.y + bb.height / 2));
  }).length; })()"""


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def has_problem(check):
    """True when any counter of a __labelCheck() result (except the label count) is non-zero."""
    return any(v for k, v in check.items() if k != "labels")


async def check_viewport(browser, name, width, height, errors):
    """Run all checks at one viewport size; return a list of problems."""
    page = await browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=2)
    page.on("pageerror", lambda e: errors.append(str(e)))
    await page.emulate_media(reduced_motion="reduce")           # no animation: measure final geometry
    await page.goto(APP_HTML.resolve().as_uri())
    await page.wait_for_timeout(1500)
    problems, summary = [], []

    for root in ROOTS:
        # --- folded view --------------------------------------------------------
        await page.evaluate(f"window.__bloom({json.dumps(root)})")
        await page.wait_for_timeout(60)
        folded = await page.evaluate("window.__labelCheck()")
        if has_problem(folded):
            problems.append(("folded", root, folded))

        # --- unfolded view ------------------------------------------------------
        await page.evaluate("window.__setExpanded(true)")
        await page.wait_for_timeout(120)
        unfolded = await page.evaluate("window.__labelCheck()")
        info = await page.evaluate("window.__demoInfo()")
        numbers_outside = await page.evaluate(NUMBERS_OUTSIDE_JS)
        outer = await page.evaluate("window.__outerCheck()")
        summary.append(f"{root}: {info['petals']}/{info['items']} petals, small labels {outer['fontPx']}px")
        if (info["petals"] != info["items"] or numbers_outside or outer["outside"] or has_problem(unfolded)):
            problems.append(("unfolded", root, unfolded, numbers_outside, info, outer))

    # --- page width and screenshots ---------------------------------------------
    scroll_width = await page.evaluate("document.documentElement.scrollWidth")
    if scroll_width > width:
        problems.append(("horizontal scroll", scroll_width, width))
    await page.evaluate("window.__bloom('ءتي')")
    await page.screenshot(path=str(SCREENSHOT_DIR / f"folded_{name}.png"))
    await page.evaluate("window.__setExpanded(true)")
    await page.screenshot(path=str(SCREENSHOT_DIR / f"unfolded_{name}.png"))
    await page.close()

    print(f"{name:12s} | " + " | ".join(summary))
    print(f"{'':12s}   problems: {problems or 'none'}")
    return problems


async def main():
    """Run every viewport and return the process exit code."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    errors, all_problems = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for name, width, height in VIEWPORTS:
            all_problems += await check_viewport(browser, name, width, height, errors)
        await browser.close()
    print("JavaScript errors:", errors or "none")
    return 1 if all_problems or errors else 0


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
