"""Send today's weather image + safety message via EZ Texting.

Env: EZ_USER, EZ_PASS (GitHub secrets), IMAGE_URL, and either TO_NUMBER (test) or GROUP_NAME.
"""
import base64, json, os, sys, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

API = "https://a.eztexting.com/v1"
SAFETY = "SAFETY: Avoid I-80 between Salt Lake City and Iowa, and I-70 west of Denver. Drive safe."

def call(method, path, body=None):
    auth = base64.b64encode(f"{os.environ['EZ_USER']}:{os.environ['EZ_PASS']}".encode()).decode()
    req = urllib.request.Request(API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Basic " + auth, "Accept": "application/json",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")

def main():
    today = datetime.now(ZoneInfo("America/New_York"))
    text = f"Daily Weather {today:%a %b %-d}. {SAFETY}"
    media = call("POST", "/media-files", {"mediaUrl": os.environ["IMAGE_URL"]})
    msg = {"message": text, "mediaFileId": media["id"]}
    if os.environ.get("TO_NUMBER"):
        msg["toNumbers"] = [os.environ["TO_NUMBER"]]
        msg["message"] = "TEST - " + text
    else:
        name = os.environ.get("GROUP_NAME", "Drivers")
        groups = call("GET", "/contact-groups?page=0&size=100")["content"]
        ids = [g["id"] for g in groups if g["name"] == name]
        if not ids:
            sys.exit(f"Group {name!r} not found")
        msg["groupIds"] = ids
    print(call("POST", "/messages", msg))

if __name__ == "__main__":
    main()
