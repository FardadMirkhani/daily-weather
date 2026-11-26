"""Drive the EZ Texting website with a headless browser (used while the API login is locked).

explore mode (STEPS env = JSON list of actions): runs the actions and saves screenshots/page notes into out/,
which the workflow encrypts before saving so nothing private lands in the public repo or logs.
"""
import json, os, sys
from playwright.sync_api import sync_playwright

OUT = "out"
os.makedirs(OUT, exist_ok=True)

def login(pg):
    pg.goto("https://app.eztexting.com/", wait_until="networkidle", timeout=90000)
    pg.locator("input[type=email], input[name=username], input[name=email], input[type=text]").first.fill(os.environ["EZ_USER"])
    pg.locator("input[type=password]").first.fill(os.environ["EZ_PASS"])
    pg.get_by_role("button", name="Log In").click()
    pg.wait_for_url("**spa.eztexting.com/**", timeout=60000)
    pg.wait_for_load_state("networkidle")

def note(pg, i, label):
    pg.screenshot(path=f"{OUT}/{i:02d}-{label}.png", full_page=True)
    info = pg.evaluate("""() => {
      const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
      const pick = sel => [...document.querySelectorAll(sel)].filter(vis).map(e => {
        const t = (e.innerText || e.value || e.getAttribute('aria-label') || e.placeholder || '').trim().slice(0, 60);
        return `${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}${e.name ? '[name=' + e.name + ']' : ''}${e.type ? '[type=' + e.type + ']' : ''} ${e.getAttribute('data-testid') || ''} :: ${t}`;
      });
      return {url: location.href, controls: pick('button, a, input, textarea, select, [role=button], [contenteditable=true], [role=option], [role=checkbox]')};
    }""")
    with open(f"{OUT}/{i:02d}-{label}.txt", "w") as f:
        f.write(info["url"] + "\n" + "\n".join(info["controls"]))

def run_steps(pg, steps):
    for i, st in enumerate(steps, 1):
        k, v = next(iter(st.items()))
        try:
            if k == "goto": pg.goto(v, wait_until="networkidle", timeout=60000)
            elif k == "click": pg.get_by_text(v, exact=True).first.click(timeout=15000)
            elif k == "clickrole": pg.get_by_role(v[0], name=v[1]).first.click(timeout=15000)
            elif k == "css": pg.locator(v).first.click(timeout=15000)
            elif k == "fill": pg.locator(v[0]).first.fill(v[1], timeout=15000)
            elif k == "type": pg.keyboard.type(v)
            elif k == "press": pg.keyboard.press(v)
            elif k == "upload": pg.locator(v[0]).first.set_input_files(v[1])
            elif k == "wait": pg.wait_for_timeout(v)
            pg.wait_for_timeout(2500)
            print(f"step {i} {k}: ok")
        except Exception as e:
            print(f"step {i} {k}: FAILED {type(e).__name__}")
        note(pg, i, k)

if __name__ == "__main__":
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1400, "height": 1000})
        login(pg)
        print("logged in")
        note(pg, 0, "dashboard")
        run_steps(pg, json.loads(os.environ.get("STEPS", "[]")))
        b.close()
