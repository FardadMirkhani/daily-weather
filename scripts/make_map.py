"""Build the daily truck-driver weather image from public NWS/NOAA maps."""
import io, sys, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

RADAR = "https://radar.weather.gov/ridge/standard/CONUS_0.gif"          # live radar + interstates
TEMPS = "https://graphical.weather.gov/images/conus/MaxT1_conus.png"    # today's forecast highs

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "daily-weather-broadcast"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")

def font(size, bold=True):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        try: return ImageFont.truetype(p, size)
        except OSError: pass
    return ImageFont.load_default()

def build(out_path):
    radar = fetch(RADAR)                 # 600x400
    temps = fetch(TEMPS)                 # 515x390
    temps = temps.crop((0, 0, temps.width, 330))   # trim the NOAA footer text
    temps = temps.resize((600, round(330 * 600 / temps.width)))
    W = 600
    now = datetime.now(ZoneInfo("America/New_York"))
    head_h, gap, label_h = 44, 6, 26
    H = head_h + label_h + radar.height + gap + label_h + temps.height
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, head_h), fill=(20, 40, 80))
    d.text((12, 10), f"Daily Weather  -  {now:%a %b %-d, %Y}", font=font(20), fill="white")
    y = head_h
    d.text((10, y + 4), "Radar (precipitation) with interstates", font=font(15), fill=(20, 40, 80)); y += label_h
    img.paste(radar, (0, y)); y += radar.height + gap
    d.text((10, y + 4), "Today's forecast high temperatures (F)", font=font(15), fill=(20, 40, 80)); y += label_h
    img.paste(temps, (0, y))
    img.save(out_path, "JPEG", quality=85, optimize=True)
    return out_path

if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else "weather.jpg"))
