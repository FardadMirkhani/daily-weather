"""Send today's weather image + safety message via EZ Texting.

Env: EZ_USER, EZ_PASS (GitHub secrets), IMAGE_URL, and either TO_NUMBER (test) or GROUP_NAME.
"""
import base64, json, os, sys, urllib.request
from roads import road_section
from datetime import datetime
from zoneinfo import ZoneInfo

API = "https://a.eztexting.com/v1"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def read(name):
    path = os.path.join(ROOT, name)
    return open(path, encoding="utf-8").read().strip() if os.path.exists(path) else ""

SAFETY = read("safety-message.txt")
SUBJECT = read("subject-line.txt")  # shown in parentheses at the top; leave the file empty for none

def call(method, path, body=None):
    auth = base64.b64encode(f"{os.environ['EZ_USER']}:{os.environ['EZ_PASS']}".encode()).decode()
    req = urllib.request.Request(API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Basic " + auth, "Accept": "application/json",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")

def main():
    if not os.environ.get("EZ_USER") or not os.environ.get("EZ_PASS"):
        sys.exit("EZ_USER / EZ_PASS repository secrets are missing (Settings > Secrets and variables > Actions).")
    today = datetime.now(ZoneInfo("America/New_York"))
    roads = road_section()
    text = f"{today:%a %b %-d, %Y}\n" + (roads + "\n\n" if roads else "") + SAFETY
    text = text[:1500]
    media = call("POST", "/media-files", {"mediaUrl": os.environ["IMAGE_URL"]})
    msg = {"message": text, "mediaFileId": media["id"], "messageType": "MMS"}
    if SUBJECT:
        msg["companyName"] = SUBJECT
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
