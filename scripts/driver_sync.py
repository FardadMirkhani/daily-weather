"""Keep the EZ Texting "Drivers" group in step with the active drivers in Motive, through the website login.

- New active drivers (phone not in Drivers yet) are uploaded as a .csv into the Drivers group.
- Drivers in the group who are no longer active in Motive are listed, and taken out of the group
  and deleted (Reza's choice) only when REMOVE_INACTIVE=yes. Contacts also in another group are only taken out of Drivers.
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
# Never removed: office staff who are in Drivers but not in Motive (Reza, Darcy, Chris Corona, Armando Lomeli),
# by their EZ Texting contact id.
# Contacts whose EZ Texting number bounced on the Nov 26, 2026 broadcast while Motive has a different number
# (Juan Banuelos, Tomas Enriquez). The Motive number is uploaded and the old contact deleted.
REPLACE_IDS = {"5841723780003", "6939350365003"}
KEEP_IDS = {"3922673811003", "3987734538003", "6528316206003", "6701581272003"}

def digits(p):
    d = re.sub(r"\D", "", p or "")
    return d[-10:] if len(d) >= 10 else ""

def namekey(first, last):
    """Same person even with small spelling differences: first 4 letters of first name + first word of last name."""
    f = re.sub(r"[^a-z]", "", (first or "").lower())[:4]
    l = ((last or "").lower().split() or [""])[0]
    return f + "|" + re.sub(r"[^a-z]", "", l)

def motive_drivers():
    """Active Motive drivers as a list of (phone or '', first, last)."""
    key = os.environ["MOTIVE_API_KEY"]
    out, page = [], 1
    while True:
        req = urllib.request.Request(f"https://api.gomotive.com/v1/users?role=driver&status=active&per_page=100&page_no={page}",
                                     headers={"X-Api-Key": key, "Accept": "application/json"})
        d = json.load(urllib.request.urlopen(req, timeout=60))
        users = [u.get("user", u) for u in d.get("users", [])]
        for u in users:
            if u.get("role", "driver") != "driver" or u.get("status", "active") != "active":
                continue
            first, last = (u.get("first_name") or "").strip(), (u.get("last_name") or "").strip()
            if first.upper().startswith(("MECHANIC", "TEST")):
                continue
            out.append((digits(u.get("phone")), first, last))
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
    items = d.get("_embedded", {}).get("entities", [])
    total = d.get("total") or 0
    if total and total > len(items):
        raise RuntimeError(f"Group has {total} contacts but only {len(items)} were read; paging needed")
    members = {}
    for c in items:
        ph = digits(str(c.get("phoneNumber") or c.get("phone") or ""))
        if ph:
            members[ph] = {"id": str(c.get("id")), "groups": len(c.get("groups") or []),
                           "name": f"{c.get('firstName') or ''} {c.get('lastName') or ''}".strip(),
                           "key": namekey(c.get("firstName"), c.get("lastName"))}
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

def remove(pg, ids, button="#removeFromThisGroupBtn"):
    pg.goto(f"https://spa.eztexting.com/groups/{GROUP_ID}", wait_until="domcontentloaded", timeout=60000)
    pg.locator("#pagination-page-size-select").wait_for(timeout=60000)
    pg.wait_for_timeout(2000)
    with pg.expect_response(lambda r: "/contact/view-list" in r.url and "pageSize=200" in r.url, timeout=60000):
        pg.locator("#pagination-page-size-select").select_option("200")
    pg.wait_for_timeout(4000)
    if button == "#deleteBtn":  # one at a time through each row's own menu (some rows have no tick box)
        for cid in ids:
            pg.locator(f"#contacts-actions-{cid}").first.click()
            pg.locator(f"#contacts-delete-{cid}").first.click(timeout=15000)
            pg.wait_for_timeout(1500)
            confirm(pg, 1)
            pg.wait_for_timeout(3000)
        note(pg, 87, "remove-done")
        return
    for cid in ids:
        pg.locator(f"#table-checkbox-{cid}-input").first.check(force=True)
    note(pg, 85, "remove-selected")
    pg.locator(button).click()
    pg.wait_for_timeout(2000)
    note(pg, 86, "remove-confirm")
    confirm(pg, len(ids))
    pg.wait_for_timeout(5000)
    note(pg, 87, "remove-done")

def confirm(pg, n):
    dlg = pg.locator("[role=dialog], mat-dialog-container, .modal").last
    shown = len(re.findall(r"\(\d{3}\) \d{3}-\s?\d{4}", dlg.inner_text(timeout=10000)))
    if shown != n:  # the dialog lists the numbers it will act on; stop if it isn't exactly ours
        note(pg, 88, "confirm-mismatch")
        pg.get_by_role("button", name="Cancel").last.click()
        raise RuntimeError(f"Confirm dialog lists {shown} numbers, expected {n}; cancelled")
    dlg.get_by_role("button", name=re.compile("^(Submit|Remove|Delete|Confirm|Yes)", re.I)).last.click(timeout=15000)

def main():
    active = motive_drivers() if os.environ.get("MOTIVE_API_KEY") else None
    keep = {digits(x) for x in os.environ.get("KEEP_NUMBERS", "").splitlines() if digits(x)}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1400, "height": 1000})
        try:
            login(pg)
            members = group_members(pg)
            if active is None:
                print(f"Drivers group read OK: {len(members)} contacts. MOTIVE_API_KEY secret is not set yet, stopping.")
                return
            if len(active) < 20:
                raise RuntimeError("Fewer than 20 active drivers came back from Motive; not changing anything")
            member_keys = {m["key"]: ph for ph, m in members.items()}
            replace_old = []
            motive_phones = {ph for ph, _, _ in active if ph}
            motive_keys = {namekey(f, l) for _, f, l in active}
            add, mismatch, nophone = [], [], []
            for ph, f, l in active:
                k = namekey(f, l)
                if ph and ph in members:
                    continue
                if k in member_keys:  # same driver, but the phone differs (or Motive has none): keep EZ's, tell Reza
                    old = member_keys[k]
                    if ph and members[old]["id"] in REPLACE_IDS:
                        add.append([ph, f, l]); replace_old.append(old)
                        continue
                    if ph:
                        mismatch.append(f"{f} {l}: Motive {ph}, EZ Texting {member_keys[k]}")
                    continue
                if ph:
                    add.append([ph, f, l])
                else:
                    nophone.append(f"{f} {l}")
            gone = sorted(ph for ph, m in members.items()
                          if ph not in motive_phones and m["key"] not in motive_keys
                          and ph not in keep and m["id"] not in KEEP_IDS)
            print(f"Motive active drivers: {len(active)} | Drivers group now: {len(members)}")
            # an outdated contact whose new number was already uploaded on an earlier run
            replace_old += [ph for ph, m in members.items() if m["id"] in REPLACE_IDS and ph not in replace_old]
            print(f"Numbers to replace with Motive's: {len(replace_old)}")
            print(f"To add: {len(add)} | no longer active: {len(gone)} | phone differs between Motive and EZ: {len(mismatch)} | new driver with no phone in Motive: {len(nophone)}")
            with open(f"{OUT}/sync-report.txt", "w") as f:
                f.write("ADD (active in Motive, not in Drivers):\n" + "".join(f"  {r[0]} {r[1]} {r[2]}\n" for r in add))
                f.write("NOT ACTIVE (in Drivers, not active in Motive):\n" + "".join(f"  {ph} {members[ph]['name']}\n" for ph in gone))
                f.write("REPLACE (old EZ number deleted):\n" + "".join(f"  {ph} {members[ph]['name']}\n" for ph in replace_old))
                f.write("PHONE DIFFERS (left as is in EZ Texting):\n" + "".join(f"  {x}\n" for x in mismatch))
                f.write("NEW IN MOTIVE BUT NO PHONE THERE:\n" + "".join(f"  {x}\n" for x in nophone))
            if MODE != "apply":
                print("Report only, nothing changed.")
                return
            if add:
                upload(pg, add)
                print(f"Uploaded {len(add)} new drivers into Drivers.")
            if replace_old and REMOVE:
                remove(pg, [members[ph]["id"] for ph in replace_old], "#deleteBtn")
                print(f"Deleted {len(replace_old)} contacts with outdated numbers (new numbers uploaded above).")
            if gone and REMOVE:
                if len(gone) > max(10, len(members) // 4):
                    raise RuntimeError(f"{len(gone)} removals is more than expected; not removing, please check")
                # Reza's choice: delete the contact. A contact that is also in another group is only taken out of Drivers.
                only = [members[ph]["id"] for ph in gone if members[ph]["groups"] <= 1]
                multi = [members[ph]["id"] for ph in gone if members[ph]["groups"] > 1]
                if only:
                    remove(pg, only, "#deleteBtn")
                    print(f"Deleted {len(only)} inactive drivers.")
                if multi:
                    remove(pg, multi)
                    print(f"Took {len(multi)} inactive drivers out of Drivers (they are in other groups too, so kept).")
            after = group_members(pg)
            print(f"Drivers group after sync: {len(after)}")
        except Exception:
            note(pg, 99, "error")
            raise
        finally:
            b.close()

if __name__ == "__main__":
    main()
