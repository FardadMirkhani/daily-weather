"""Find a driver in Motive and take them out of the Active Drivers group (Reza's request). Output encrypted."""
import json, os, urllib.request
KEY = os.environ["MOTIVE_API_KEY"]
GROUP = 259925  # Active Drivers
os.makedirs("out", exist_ok=True)
def call(path, method="GET", body=None):
    req = urllib.request.Request("https://api.gomotive.com" + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"X-Api-Key": KEY, "Accept": "application/json", "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode()[:500]}
users, page = [], 1
while True:
    d = call(f"/v1/users?role=driver&per_page=100&page_no={page}")
    batch = [u.get("user", u) for u in d.get("users", [])]
    users += batch
    if len(batch) < 100: break
    page += 1
in_group = [u for u in users if GROUP in (u.get("group_ids") or [])]
print("drivers total:", len(users), "| in Active Drivers group:", len(in_group),
      "| in group and active:", sum(u.get("status") == "active" for u in in_group),
      "| active but not in group:", sum(u.get("status") == "active" and GROUP not in (u.get("group_ids") or []) for u in users))
with open("out/group-vs-status.txt", "w") as f:
    for u in users:
        g = GROUP in (u.get("group_ids") or [])
        if g != (u.get("status") == "active"):
            f.write(f"{u['first_name']} {u['last_name']} status={u.get('status')} in_group={g}\n")
target = [u for u in users if (u.get("first_name") or "").lower().startswith("benj") and (u.get("last_name") or "").lower().startswith("nu")]
print("matches:", len(target))
if len(target) == 1 and os.environ.get("APPLY") == "yes":
    u = target[0]
    new = [g for g in (u.get("group_ids") or []) if g != GROUP]
    r = call(f"/v1/users/{u['id']}", "PUT", {"group_ids": new})
    print("update result:", "error " + str(r.get("_error")) if "_error" in r else "ok")
    json.dump(r, open("out/update.json", "w"))
    after = call(f"/v1/users/{u['id']}")
    a = after.get("user", after)
    print("still in group after update:", GROUP in (a.get("group_ids") or []), "| status:", a.get("status"))
