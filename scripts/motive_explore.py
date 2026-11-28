"""Look at Motive groups (structure only; names of people go to out/, which is encrypted)."""
import json, os, urllib.request
KEY = os.environ["MOTIVE_API_KEY"]
os.makedirs("out", exist_ok=True)
def get(path):
    req = urllib.request.Request("https://api.gomotive.com" + path, headers={"X-Api-Key": KEY, "Accept": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode()[:500]}
groups = get("/v1/groups?per_page=100")
json.dump(groups, open("out/groups.json", "w"))
for g in groups.get("groups", []):
    g = g.get("group", g)
    print("group:", g.get("id"), g.get("name"), {k: (len(v) if isinstance(v, list) else None) for k, v in g.items() if isinstance(v, list)})
    if "driver" in (g.get("name") or "").lower():
        d = get(f"/v1/groups/{g['id']}")
        json.dump(d, open(f"out/group-{g['id']}.json", "w"))
        print("  detail keys:", list((d.get("group", d) if isinstance(d, dict) else {}).keys()))
users = get("/v1/users?role=driver&per_page=100&page_no=1")
nunez = [u.get("user", u) for u in users.get("users", []) if "nunez" in ((u.get("user", u).get("last_name")) or "").lower()]
json.dump(nunez, open("out/nunez.json", "w"))
print("nunez entries:", len(nunez))
