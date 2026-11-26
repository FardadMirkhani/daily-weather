"""Send a broadcast through Twilio and text a delivery summary to the office.

Secrets/env: TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET, TWILIO_FROM (+1XXXXXXXXXX),
DRIVER_NUMBERS (one driver per line: "Name,8581234567"; kept as a secret so numbers stay private),
REPORT_NUMBER (optional, gets the summary text).
"""
import base64, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

def _auth():
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    if os.environ.get("TWILIO_AUTH_TOKEN"):  # simplest and always allowed: Account SID + Auth Token
        user, pw = sid, os.environ["TWILIO_AUTH_TOKEN"]
    else:
        user, pw = os.environ.get("TWILIO_API_KEY", ""), os.environ.get("TWILIO_API_SECRET", "")
    return sid, "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()

def _call(method, url, form=None):
    sid, auth = _auth()
    data = urllib.parse.urlencode(form, doseq=True).encode() if form else None
    req = urllib.request.Request(url if url.startswith("http") else
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}{url}", data=data, method=method,
        headers={"Authorization": auth})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            return {"error": json.loads(e.read())}
        except Exception:
            return {"error": {"code": e.code, "message": str(e)}}

def e164(num):
    d = re.sub(r"\D", "", num)
    if len(d) == 10:
        d = "1" + d
    return "+" + d

def drivers():
    out = []
    for line in os.environ.get("DRIVER_NUMBERS", "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        name, _, num = line.rpartition(",")
        out.append((name.strip() or num.strip(), e164(num)))
    return out

def send(text, media_url=None, recipients=None, label="BROADCAST"):
    """recipients: list of (name, +1number). Returns summary string."""
    recipients = recipients or drivers()
    if not recipients:
        sys.exit("No recipients: DRIVER_NUMBERS secret is empty.")
    sent, failed, opted = [], [], []
    for name, num in recipients:
        form = {"To": num, "From": os.environ["TWILIO_FROM"], "Body": text[:1600]}
        if media_url:
            form["MediaUrl"] = media_url
        r = _call("POST", "/Messages.json", form)
        if "error" in r:
            (opted if r["error"].get("code") == 21610 else failed).append(name)
            print(f"{name}: {r['error']}")
        else:
            sent.append((name, r["sid"]))
    # Give carriers a couple of minutes, then check what was actually delivered.
    time.sleep(120 if len(sent) > 1 else 30)
    delivered = 0
    for name, msid in sent:
        st = _call("GET", f"/Messages/{msid}.json").get("status", "unknown")
        if st in ("delivered", "sent", "queued", "sending", "accepted"):
            delivered += 1
        else:
            failed.append(name)
    summary = f"{label}: {delivered} delivered"
    if failed:
        summary += f", {len(failed)} failed ({', '.join(failed[:8])}{'...' if len(failed) > 8 else ''})"
    if opted:
        summary += f", {len(opted)} opted out ({', '.join(opted[:8])}{'...' if len(opted) > 8 else ''})"
    print(summary)
    rep = os.environ.get("REPORT_NUMBER")
    if rep and len(recipients) > 1:
        _call("POST", "/Messages.json", {"To": e164(rep), "From": os.environ["TWILIO_FROM"], "Body": summary})
    if not delivered:
        sys.exit("Nothing was delivered.")
    return summary
