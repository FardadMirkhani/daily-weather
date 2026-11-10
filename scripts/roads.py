"""Short list of severe conditions on major US interstates.

Sources (free, no key):
  - NWS active alerts (api.weather.gov): blizzard / winter storm / ice / high wind / dust
    warnings whose area touches a major interstate corridor.
  - Caltrans chain controls (cwwp2.dot.ca.gov): chains required on I-5 / I-80 / I-15 etc.
"""
import json, math, urllib.request

UA = {"User-Agent": "daily-weather-broadcast (truck safety text)", "Accept": "application/geo+json"}
MAX_LINES = 6

# Waypoints (lat, lon, place) along each major corridor; points are interpolated between them.
CORRIDORS = {
    "I-5":  [(32.72,-117.16,"San Diego"),(34.05,-118.24,"Los Angeles"),(34.80,-118.87,"Grapevine"),(36.0,-119.9,"Kettleman City"),
             (38.58,-121.49,"Sacramento"),(40.59,-122.39,"Redding"),(41.31,-122.31,"Mt Shasta"),(41.73,-122.63,"Yreka"),
             (42.33,-122.87,"Medford"),(42.95,-123.34,"Roseburg"),(44.05,-123.09,"Eugene"),(45.52,-122.68,"Portland"),(47.61,-122.33,"Seattle"),(48.95,-122.75,"Blaine")],
    "I-8":  [(32.72,-117.16,"San Diego"),(32.68,-116.30,"Pine Valley"),(32.79,-115.56,"El Centro"),(32.69,-114.62,"Yuma"),(32.88,-111.76,"Casa Grande")],
    "I-10": [(34.05,-118.24,"Los Angeles"),(33.93,-116.82,"Banning"),(33.61,-114.60,"Blythe"),(33.45,-112.07,"Phoenix"),(32.22,-110.97,"Tucson"),
             (32.29,-108.70,"Lordsburg"),(31.76,-106.49,"El Paso"),(30.89,-102.88,"Fort Stockton"),(29.42,-98.49,"San Antonio"),(29.76,-95.37,"Houston"),
             (30.45,-91.19,"Baton Rouge"),(30.69,-88.04,"Mobile"),(30.44,-84.28,"Tallahassee"),(30.33,-81.66,"Jacksonville")],
    "I-15": [(32.72,-117.16,"San Diego"),(34.30,-117.47,"Cajon Pass"),(34.90,-117.02,"Barstow"),(36.17,-115.14,"Las Vegas"),(37.68,-113.06,"Cedar City"),
             (39.37,-112.58,"Scipio"),(40.76,-111.89,"Salt Lake City"),(42.86,-112.45,"Pocatello"),(44.00,-112.23,"Dubois"),(45.00,-112.84,"Dillon"),
             (46.59,-112.04,"Helena"),(47.50,-111.30,"Great Falls"),(48.99,-111.96,"Sweetgrass")],
    "I-20": [(31.42,-103.49,"Pecos"),(32.00,-102.08,"Midland"),(32.45,-99.73,"Abilene"),(32.76,-97.33,"Fort Worth"),(32.78,-96.80,"Dallas"),
             (32.50,-93.75,"Shreveport"),(32.30,-90.18,"Jackson"),(33.52,-86.80,"Birmingham"),(33.75,-84.39,"Atlanta"),(34.00,-81.03,"Columbia"),(34.19,-79.76,"Florence")],
    "I-25": [(32.31,-106.78,"Las Cruces"),(35.08,-106.65,"Albuquerque"),(35.69,-105.94,"Santa Fe"),(36.90,-104.44,"Raton"),(37.17,-104.51,"Trinidad"),
             (38.25,-104.61,"Pueblo"),(38.83,-104.82,"Colorado Springs"),(39.74,-104.99,"Denver"),(41.14,-104.82,"Cheyenne"),(42.85,-106.31,"Casper"),(44.35,-106.70,"Buffalo")],
    "I-35": [(27.51,-99.51,"Laredo"),(29.42,-98.49,"San Antonio"),(30.27,-97.74,"Austin"),(32.76,-97.33,"Fort Worth"),(35.47,-97.52,"Oklahoma City"),
             (37.69,-97.34,"Wichita"),(39.10,-94.58,"Kansas City"),(41.59,-93.62,"Des Moines"),(44.98,-93.27,"Minneapolis"),(46.79,-92.10,"Duluth")],
    "I-40": [(34.90,-117.02,"Barstow"),(34.85,-114.61,"Needles"),(35.19,-114.05,"Kingman"),(35.20,-111.65,"Flagstaff"),(35.53,-108.74,"Gallup"),
             (35.08,-106.65,"Albuquerque"),(35.17,-103.72,"Tucumcari"),(35.22,-101.83,"Amarillo"),(35.47,-97.52,"Oklahoma City"),(35.39,-94.40,"Fort Smith"),
             (34.75,-92.29,"Little Rock"),(35.15,-90.05,"Memphis"),(36.16,-86.78,"Nashville"),(35.96,-83.92,"Knoxville"),(35.60,-82.55,"Asheville"),
             (36.07,-79.79,"Greensboro"),(35.78,-78.64,"Raleigh"),(34.23,-77.94,"Wilmington")],
    "I-70": [(38.57,-112.61,"Cove Fort"),(38.99,-110.16,"Green River"),(39.06,-108.55,"Grand Junction"),(39.55,-107.32,"Glenwood Springs"),(39.64,-106.37,"Vail"),
             (39.68,-105.92,"Eisenhower Tunnel"),(39.74,-104.99,"Denver"),(39.30,-102.27,"Burlington"),(38.88,-99.33,"Hays"),(39.05,-95.68,"Topeka"),
             (39.10,-94.58,"Kansas City"),(38.63,-90.20,"St. Louis"),(39.77,-86.16,"Indianapolis"),(39.96,-83.00,"Columbus"),(40.07,-80.72,"Wheeling"),(39.64,-77.72,"Hagerstown")],
    "I-75": [(25.94,-80.31,"Miami"),(26.64,-81.87,"Fort Myers"),(27.95,-82.46,"Tampa"),(29.65,-82.32,"Gainesville"),(30.83,-83.28,"Valdosta"),
             (33.75,-84.39,"Atlanta"),(35.05,-85.31,"Chattanooga"),(35.96,-83.92,"Knoxville"),(38.04,-84.50,"Lexington"),(39.10,-84.51,"Cincinnati"),
             (39.76,-84.19,"Dayton"),(41.65,-83.54,"Toledo"),(42.33,-83.05,"Detroit"),(43.42,-83.95,"Saginaw"),(45.78,-84.73,"Mackinaw City"),(46.50,-84.35,"Sault Ste Marie")],
    "I-80": [(37.80,-122.27,"Oakland"),(38.58,-121.49,"Sacramento"),(39.32,-120.33,"Donner Pass"),(39.53,-119.81,"Reno"),(40.97,-117.74,"Winnemucca"),
             (40.83,-115.76,"Elko"),(40.74,-114.04,"Wendover"),(40.76,-111.89,"Salt Lake City"),(41.27,-110.96,"Evanston"),(41.59,-109.20,"Rock Springs"),
             (41.79,-107.24,"Rawlins"),(41.31,-105.59,"Laramie"),(41.14,-104.82,"Cheyenne"),(41.13,-100.77,"North Platte"),(40.81,-96.68,"Lincoln"),
             (41.26,-95.94,"Omaha"),(41.59,-93.62,"Des Moines"),(41.52,-90.58,"Davenport"),(41.52,-87.88,"Chicago"),(41.68,-86.25,"South Bend"),
             (41.65,-83.54,"Toledo"),(41.50,-81.69,"Cleveland"),(41.10,-80.65,"Youngstown"),(41.24,-77.00,"Williamsport"),(40.86,-74.16,"Paterson")],
    "I-81": [(36.55,-82.56,"Kingsport"),(37.27,-79.94,"Roanoke"),(38.45,-78.87,"Harrisonburg"),(39.64,-77.72,"Hagerstown"),(40.27,-76.88,"Harrisburg"),
             (41.41,-75.66,"Scranton"),(42.10,-75.91,"Binghamton"),(43.05,-76.15,"Syracuse"),(44.34,-75.92,"Watertown")],
    "I-90": [(47.61,-122.33,"Seattle"),(47.42,-121.41,"Snoqualmie Pass"),(47.13,-119.28,"Moses Lake"),(47.66,-117.43,"Spokane"),(47.47,-115.80,"Lookout Pass"),
             (46.87,-113.99,"Missoula"),(46.00,-112.53,"Butte"),(45.68,-111.04,"Bozeman"),(45.78,-108.50,"Billings"),(44.80,-106.96,"Sheridan"),
             (44.29,-105.50,"Gillette"),(44.08,-103.23,"Rapid City"),(43.55,-96.73,"Sioux Falls"),(43.65,-94.46,"Fairmont"),(43.81,-91.24,"La Crosse"),
             (43.07,-89.40,"Madison"),(41.88,-87.63,"Chicago"),(41.50,-81.69,"Cleveland"),(42.89,-78.88,"Buffalo"),(43.05,-76.15,"Syracuse"),
             (42.65,-73.75,"Albany"),(42.36,-71.06,"Boston")],
    "I-94": [(46.87,-104.00,"Glendive MT"),(46.88,-102.79,"Dickinson"),(46.81,-100.78,"Bismarck"),(46.88,-96.79,"Fargo"),(44.98,-93.27,"Minneapolis"),
             (44.81,-91.50,"Eau Claire"),(43.04,-87.91,"Milwaukee"),(41.88,-87.63,"Chicago"),(42.29,-85.59,"Kalamazoo"),(42.33,-83.05,"Detroit")],
    "I-95": [(25.77,-80.19,"Miami"),(28.08,-80.61,"Melbourne"),(30.33,-81.66,"Jacksonville"),(32.08,-81.09,"Savannah"),(34.19,-79.76,"Florence"),
             (35.05,-78.88,"Fayetteville"),(37.54,-77.44,"Richmond"),(38.90,-77.04,"Washington"),(39.29,-76.61,"Baltimore"),(39.95,-75.17,"Philadelphia"),
             (40.71,-74.01,"New York"),(41.31,-72.92,"New Haven"),(41.82,-71.41,"Providence"),(42.36,-71.06,"Boston"),(43.66,-70.26,"Portland ME"),(44.80,-68.77,"Bangor")],
}

EVENTS = {  # NWS event -> short label, in priority order
    "Blizzard Warning": "BLIZZARD",
    "Ice Storm Warning": "ICE STORM",
    "Winter Storm Warning": "WINTER STORM",
    "Dust Storm Warning": "DUST STORM",
    "Extreme Wind Warning": "EXTREME WIND",
    "High Wind Warning": "HIGH WIND",
    "Snow Squall Warning": "SNOW SQUALL",
    "Blizzard Watch": "blizzard watch (storm coming)",
    "Winter Storm Watch": "winter storm watch (storm coming)",
}

CHAIN_DISTRICTS = [1, 2, 3, 6, 7, 8, 9, 10, 11]
CHAIN_LABEL = {"R-1": "chains/snow tires req", "R-2": "CHAINS REQUIRED", "R-3": "CHAINS ALL VEHICLES", "R-4": "CLOSED"}


def get(url, headers=UA):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read())


def corridor_points(wps, step_km=12):
    pts = []
    for (a, b) in zip(wps, wps[1:]):
        d = math.hypot((b[0] - a[0]) * 111, (b[1] - a[1]) * 85)
        n = max(1, int(d / step_km))
        for i in range(n):
            t = i / n
            lat, lon = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            pts.append((lat, lon, a[2] if t < 0.5 else b[2]))
    pts.append(wps[-1])
    return pts


POINTS = {r: corridor_points(w) for r, w in CORRIDORS.items()}


def in_ring(lon, lat, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def polygons(geom):
    if not geom:
        return []
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    if geom["type"] == "GeometryCollection":
        return [p for g in geom["geometries"] for p in polygons(g)]
    return []


def hit(lon, lat, polys):
    for poly in polys:
        if in_ring(lon, lat, poly[0]) and not any(in_ring(lon, lat, h) for h in poly[1:]):
            return True
    return False


def weather_lines():
    data = get("https://api.weather.gov/alerts/active?status=actual&message_type=alert,update&event="
               + ",".join(e.replace(" ", "%20") for e in EVENTS))
    zone_cache, found = {}, {}
    for f in data["features"]:
        p = f["properties"]
        label = EVENTS.get(p["event"])
        if not label:
            continue
        polys = polygons(f.get("geometry"))
        if not polys:
            for z in p.get("affectedZones", []):
                if z not in zone_cache:
                    try:
                        zone_cache[z] = polygons(get(z).get("geometry"))
                    except Exception:
                        zone_cache[z] = []
                polys += zone_cache[z]
        bbox = [(min(c[0] for c in poly[0]), max(c[0] for c in poly[0]), min(c[1] for c in poly[0]), max(c[1] for c in poly[0])) for poly in polys]
        for route, pts in POINTS.items():
            places = []
            for lat, lon, place in pts:
                if any(b[0] <= lon <= b[1] and b[2] <= lat <= b[3] for b in bbox) and hit(lon, lat, polys):
                    if place not in places:
                        places.append(place)
            if places:
                key = (route, label)
                found.setdefault(key, [])
                for pl in places:
                    if pl not in found[key]:
                        found[key].append(pl)
    order = list(EVENTS.values())
    lines = []
    for (route, label), places in sorted(found.items(), key=lambda kv: (order.index(kv[0][1]), int(kv[0][0][2:]))):
        span = places[0] if len(places) == 1 else f"{places[0]}-{places[-1]}"
        lines.append(f"{route} {span}: {label}")
    return lines


def chain_lines():
    worst = {}
    for d in CHAIN_DISTRICTS:
        try:
            data = get(f"https://cwwp2.dot.ca.gov/data/d{d}/cc/ccStatusD{d:02d}.json", {"User-Agent": UA["User-Agent"]})
        except Exception:
            continue
        for x in data.get("data", []):
            cc = x["cc"]; loc = cc["location"]; st = cc["statusData"]["status"]
            route = loc["route"]
            if route == "I-40" and loc.get("nearbyPlace") == "Truckee":   # Caltrans data quirk: Donner is I-80
                route = "I-80"
            if route not in CORRIDORS or st not in CHAIN_LABEL:
                continue
            place = loc["nearbyPlace"].title()
            k = route
            if k not in worst or st > worst[k][0]:
                worst[k] = (st, place)
    return [f"CA {r} near {p}: {CHAIN_LABEL[s]}" for r, (s, p) in sorted(worst.items())]


def road_section():
    lines = []
    for fn in (chain_lines, weather_lines):
        try:
            lines += fn()
        except Exception as e:  # never block the daily send
            print("road source failed:", fn.__name__, e)
    if not lines:
        return ""
    extra = len(lines) - MAX_LINES
    lines = lines[:MAX_LINES] + ([f"+{extra} more, check 511 before you roll"] if extra > 0 else [])
    return "ROAD ALERTS:\n" + "\n".join("- " + l for l in lines)


if __name__ == "__main__":
    print(road_section() or "(no severe interstate alerts)")
