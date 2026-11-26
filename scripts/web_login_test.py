"""One-time check: can a headless browser log in to the EZ Texting website? Saves screenshots (uploaded as a private run artifact)."""
import os, sys
from playwright.sync_api import sync_playwright
os.makedirs("shots", exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1280, "height": 900})
    resp = []
    pg.on("response", lambda r: resp.append(f"{r.status} {r.request.method} {r.url[:120]}") if ("login" in r.url or "token" in r.url or "auth" in r.url) else None)
    pg.goto("https://app.eztexting.com/", wait_until="networkidle", timeout=60000)
    pg.screenshot(path="shots/1-start.png")
    print("URL:", pg.url)
    user = pg.locator("input[type=email], input[name=username], input[name=email], input[type=text]").first
    user.fill(os.environ["EZ_USER"])
    pw = pg.locator("input[type=password]").first
    if not pw.is_visible():
        pg.keyboard.press("Enter"); pg.wait_for_timeout(3000)
    pw.fill(os.environ["EZ_PASS"])
    pg.screenshot(path="shots/2-filled.png")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(12000)
    pg.screenshot(path="shots/3-after.png", full_page=True)
    print("URL after:", pg.url)
    print("\n".join(resp))
    print(pg.inner_text("body")[:600].replace(os.environ["EZ_USER"], "<user>"))
    b.close()
