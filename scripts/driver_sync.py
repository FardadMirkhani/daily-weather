"""Keep the EZ Texting "Drivers" group in step with the active drivers in Motive, through the website login.

- New active drivers (phone not in Drivers yet) are uploaded as a .csv into the Drivers group.
- Drivers in the group who are no longer active in Motive are listed, and taken out of the group
  ("Remove From Group", the contact itself is kept) only when REMOVE_INACTIVE=yes.
- KEEP_NUMBERS (secret, optional): phones that must never be removed (office staff, test phones), one per line.
- MODE=report changes nothing, MODE=apply makes the changes.

Names and phone numbers only go into out/ (encrypted by the workflow), never into the public log.
"""
import csv, json, os, re, sys, urllib.request
from playwright.sync_api import sync_playwright
import ez_web
from ez_web import login, note, OUT

GROUP_ID = os.environ.get("EZ_GROUP_ID", "34351329003")  # Drivers
MODE = os.environ.get("MODE", "report")
REMOVE = os.environ.get("REMOVE_INACTIVE", "no") == "yes"

def digits(p):
    d = re.sub(r"\D", "", p or "")
    return d[-10:] if len(d) >= 10 else ""

def motive_drivers():
    key = os.environ["MOTIVE_API_KEY"]
    out, page = {}, 1
    while True:
        req = urllib.request.Request(f"https://api.gomotive.com/v1/users?role=driver&status=active&per_page=100&page_no={page}",
                                     headers={"X-Api-Key": key, "Accept": "application/json"})
        d = json.load(urllib.request.urlopen(req, timeout=60))
        users = [u.get("user", u) for u in d.get("users", [])]
        for u in users:
            if u.get("role", "driver") != "driver" or u.get("status", "active") != "active":
                continue
            ph = digits(u.get("phone"))
            if ph:
                out[ph] = (u.get("first_name") or "").strip(), (u.get("last_name") or "").strip()
            else:
                out.setdefault("nophone", []).append(f"{u.get('first_name','')} {u.get('last_name','')}".strip())
        pg = d.get("pagination", {})
        if not users or page * pg.get("per_page", 100) >= pg.get("total", 0):
            break
        page += 1
    return out

def group_members(pg):
    """All contacts in the Drivers group, read from the data the group page itself loads."""
    with pg.expect_response(lambda r: "/contact/view-list" in r.url and "pageSize=200" in r.url, timeout=60000) as resp:
        pg.goto(f"https://spa.eztexting.com/groups/{GROUP_ID}", wait_until="domcontentloaded", timeout=60000)
        pg.locator("#pagination-page-size-select").wait_for(timeout=60000)
        pg.locator("#pagination-page-size-select").select_option("200")
    d = resp.value.json()
    with open(f"{OUT}/group-raw.json", "w") as f:
        json.dump(d, f)
    items = d.get("items") or d.get("data") or d.get("content") or (d if isinstance(d, list) else [])
    total = d.get("totalCount") or d.get("total") or len(items)
    if total and total > len(items):
        raise RuntimeError(f"Group has {total} contacts but only {len(items)} were read; paging needed")
    members = {}
    for c in items:
        ph = digits(str(c.get("phoneNumber") or c.get("phone") or ""))
        if ph:
            members[ph] = {"id": c.get("id"), "name": f"{c.get('firstName') or ''} {c.get('lastName') or ''}".strip()}
    return members

def upload(pg, rows):
    path = os.path.abspath(f"{OUT}/new-drivers.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Phone Number", "First Name", "Last Name"])
        w.writerows(rows)
    pg.goto(f"https://spa.eztexting.com/import-contacts/file?groups={GROUP_ID}", wait_until="domcontentloaded", timeout=60000)
    pg.locator("input#upload-drop-file").set_input_files(path)
    pg.wait_for_timeout(3000)
    pg.keyboard.press("Escape")  # tips popup
    pg.locator("#continueBtb").click()
    pg.locator("#agreeImport-input").wait_for(state="attached", timeout=30000)
    note(pg, 80, "assign-group")
    if "Drivers" not in pg.locator("body").inner_text():
        raise RuntimeError("Drivers group is not selected on the upload page")
    pg.locator("#agreeImport-input").check(force=True)
    pg.locator("#import-contacts-group-select-continue-btn").click()
    pg.wait_for_timeout(15000)
    note(pg, 81, "upload-done")

def remove(pg, ids):
    pg.goto(f"https://spa.eztexting.com/groups/{GROUP_ID}", wait_until="domcontentloaded", timeout=60000)
    pg.locator("#pagination-page-size-select").wait_for(timeout=60000)
    pg.locator("#pagination-page-size-select").select_option("200")
    pg.wait_for_timeout(4000)
    for cid in ids:
        pg.locator(f"#table-checkbox-{cid}-input").check(force=True)
    note(pg, 85, "remove-selected")
    pg.locator("#removeFromThisGroupBtn").click()
    pg.wait_for_timeout(2000)
    note(pg, 86, "remove-confirm")
    pg.get_by_role("button", name=re.compile("^(Remove|Confirm|Yes)", re.I)).last.click(timeout=15000)
    pg.wait_for_timeout(5000)
    note(pg, 87, "remove-done")

def main():
    active = motive_drivers()
    nophone = active.pop("nophone", [])
    keep = {digits(x) for x in os.environ.get("KEEP_NUMBERS", "").splitlines() if digits(x)}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1400, "height": 1000})
        try:
            login(pg)
            members = group_members(pg)
            add = sorted(ph for ph in active if ph not in members)
            gone = sorted(ph for ph in members if ph not in active and ph not in keep)
            print(f"Motive active drivers with a phone: {len(active)} (without a phone: {len(nophone)})")
            print(f"Drivers group now: {len(members)} | to add: {len(add)} | no longer active: {len(gone)}")
            if len(active) < 20:
                raise RuntimeError("Fewer than 20 active drivers came back from Motive; not changing anything")
            with open(f"{OUT}/sync-report.txt", "w") as f:
                f.write("ADD (active in Motive, not in Drivers):\n" + "".join(f"  {ph} {' '.join(active[ph])}\n" for ph in add))
                f.write("NOT ACTIVE (in Drivers, not active in Motive):\n" + "".join(f"  {ph} {members[ph]['name']}\n" for ph in gone))
                f.write("ACTIVE IN MOTIVE BUT NO PHONE:\n" + "".join(f"  {n}\n" for n in nophone))
            if MODE != "apply":
                print("Report only, nothing changed.")
                return
            if add:
                upload(pg, [[ph, *active[ph]] for ph in add])
                print(f"Uploaded {len(add)} new drivers into Drivers.")
            if gone and REMOVE:
                if len(gone) > max(10, len(members) // 4):
                    raise RuntimeError(f"{len(gone)} removals is more than expected; not removing, please check")
                remove(pg, [members[ph]["id"] for ph in gone])
                print(f"Removed {len(gone)} inactive drivers from Drivers (contacts kept).")
            after = group_members(pg)
            print(f"Drivers group after sync: {len(after)}")
        except Exception:
            note(pg, 99, "error")
            raise
        finally:
            b.close()

if __name__ == "__main__":
    main()
