"""
Matches games to their Steam AppID so the interface can show cover art.

There is no artwork in the database and none to license, which is most of why
a list of 176 titles reads as a spreadsheet. Steam publishes a header image
per app on a public CDN and a name-search endpoint that needs no API key, so
the whole problem reduces to storing one integer per game.

    https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{id}/header.jpg

Matching is by name and therefore fallible, so every result is graded and the
uncertain ones are printed for review rather than silently written:

    exact   normalised names are identical           -> trusted
    close   one contains the other                   -> printed, still written
    weak    only a partial match                     -> printed, NOT written
    none    nothing found                            -> no image, monogram

Coverage will never be complete: Valorant, League of Legends and the Forza
titles are not on Steam at all. Those keep the generated monogram tile, which
is why that fallback exists rather than being a placeholder to remove later.

    python scripts/link_steam_apps.py            # report matches
    python scripts/link_steam_apps.py --apply
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

SEARCH = "https://steamcommunity.com/actions/SearchApps/"
HEADERS = {"User-Agent": "Mozilla/5.0 (PerfHub catalogue linker)"}

# Not on Steam, so there is nothing to look for. Listed explicitly rather than
# left to fail, so a missing match always means something went wrong.
NOT_ON_STEAM = {
    "Valorant", "League of Legends", "Fortnite", "Apex Legends",
    "Overwatch 2", "Call of Duty: Warzone", "Minecraft RTX",
    "Forza Horizon 5", "Forza Horizon 6", "Forza Motorsport",
    "Microsoft Flight Simulator", "Microsoft Flight Simulator 2024",
    "Diablo IV", "World of Warcraft", "Destiny 2", "Rocket League",
    "Marvel Rivals", "Delta Force", "Lost Ark", "Warframe",
    "Genshin Impact", "EA FC 25", "EA Sports FC 26", "Battlefield 2042",
    "Call of Duty: Black Ops 6", "Call of Duty: Modern Warfare III",
    "Fall Guys",  # delisted from Steam when it moved to the Epic store
    "Escape from Tarkov",  # own launcher only
}

# Where the catalogue name and the Steam name genuinely differ.
OVERRIDE = {
    "GTA V": 271590,
    "Grand Theft Auto V Enhanced": 3240220,
    "Portal with RTX": 2012840,
    "Quake II RTX": 1089130,
    "The Witcher 3 Next-Gen": 292030,
    "The Witcher 3: Wild Hunt": 292030,
    "Counter-Strike 2": 730,
    "Dying Light": 239140,
    "Cities: Skylines II": 949230,
    # The search returns the first game's id for the sequel, and both are in
    # the catalogue, so they would have ended up sharing a cover.
    "Kingdom Come: Deliverance 2": 1771300,
    "Kingdom Come: Deliverance": 379430,
    # Renamed on Steam: Hitman 3 is now HITMAN World of Assassination.
    "Hitman 3": 1659040,
    "F1 2024": 2488620,
    "F1 25": 3059520,
    "Alan Wake 2": 2843840,
    "Dead Space Remake": 1693980,
    "Metro Exodus Enhanced": 1449560,
    "Warhammer 40K: Darktide": 1361210,
    "Warhammer 40K: Space Marine 2": 2183900,
}


def normalise(s):
    s = s.lower()
    s = re.sub(r"[™®©]", "", s)
    s = re.sub(r"\b(remastered|remake|enhanced|edition|next-gen|goty)\b", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def search(name, retries=2):
    url = SEARCH + urllib.parse.quote(name)
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if attempt == retries:
                return []
            time.sleep(1.5)
    return []


CDN = ("https://shared.cloudflare.steamstatic.com/store_item_assets/"
       "steam/apps/{}/header.jpg")


def has_cover(appid):
    """
    Confirm the image actually exists before storing the id.

    Name matching alone is not enough: the search happily returned appid
    3932890 for Escape from Tarkov, which is not on Steam at all, and that id
    has no header image. Trusting the match would have shipped a row with a
    broken image and no fallback, because the fallback only triggers when the
    id is absent. So every candidate is fetched once, here, where it is cheap
    to be wrong.
    """
    try:
        req = urllib.request.Request(CDN.format(appid), headers=HEADERS, method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200 and r.headers.get("Content-Type", "").startswith("image/")
    except Exception:
        return False


def grade(name, candidates):
    """Best candidate and how much to trust it."""
    want = normalise(name)
    best = None
    for c in candidates:
        got = normalise(c["name"])
        if got == want:
            return int(c["appid"]), "exact"
        if best is None and (want in got or got in want):
            best = int(c["appid"])
    if best:
        return best, "close"
    if candidates:
        return int(candidates[0]["appid"]), "weak"
    return None, "none"


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(games)")}
    if "steam_appid" not in cols:
        print("  yeni sutun: steam_appid" + ("" if apply_changes else "  (kuru calisma)"))
        if apply_changes:
            cur.execute("ALTER TABLE games ADD COLUMN steam_appid INTEGER")

    rows = [dict(r) for r in cur.execute("SELECT id, name FROM games ORDER BY name")]
    results = {"exact": [], "close": [], "weak": [], "none": [], "skip": [],
               "manual": [], "broken": []}

    for i, r in enumerate(rows, 1):
        name = r["name"]
        if name in OVERRIDE:
            appid = OVERRIDE[name]
            if not has_cover(appid):
                results["broken"].append((name, appid))
                continue
            results["manual"].append((name, appid))
            if apply_changes:
                cur.execute("UPDATE games SET steam_appid=? WHERE id=?", (appid, r["id"]))
            continue
        if name in NOT_ON_STEAM:
            results["skip"].append((name, None))
            continue

        appid, quality = grade(name, search(name))
        if appid and quality in ("exact", "close") and not has_cover(appid):
            quality = "broken"
            results.setdefault("broken", []).append((name, appid))
            appid = None
        else:
            results[quality].append((name, appid))
        # Only exact and close matches are trusted enough to store. A weak match
        # is usually a sequel or a soundtrack, and a wrong cover is worse than
        # no cover.
        if apply_changes and quality in ("exact", "close"):
            cur.execute("UPDATE games SET steam_appid=? WHERE id=?", (appid, r["id"]))
        time.sleep(0.25)
        if i % 25 == 0:
            print(f"  … {i}/{len(rows)}")

    print()
    print(f"  tam eslesme      : {len(results['exact'])}")
    print(f"  yakin eslesme    : {len(results['close'])}")
    print(f"  zayif (yazilmadi): {len(results['weak'])}")
    print(f"  bulunamadi       : {len(results['none'])}")
    print(f"  elle girilmis    : {len(results['manual'])}")
    print(f"  Steam'de degil   : {len(results['skip'])}")
    print(f"  gorsel 404 verdi : {len(results['broken'])}  (yazilmadi)")
    covered = len(results['exact']) + len(results['close']) + len(results['manual'])
    print(f"\n  gorsel gelecek   : {covered}/{len(rows)} oyun "
          f"({covered * 100 // len(rows)}%)")

    for key, title in (("broken", "GORSEL YOK — 404, yazilmadi"),
                       ("close", "YAKIN — gozden gecirin"),
                       ("weak", "ZAYIF — yazilmadi"),
                       ("none", "BULUNAMADI")):
        if results[key]:
            print(f"\n  {title}:")
            for name, appid in results[key]:
                print(f"    {name[:38]:38s} {appid or '-'}")

    if apply_changes:
        conn.commit()
        print("\n  yazildi. scripts/export_engine_data.py calistirin.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
