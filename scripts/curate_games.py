"""
Cleans the game catalogue: removes junk, fills genres, flags competitive play.

Three separate jobs, all data rather than model:

1. **Remove entries that should not be there.** Duplicates under two spellings,
   and one game that never shipped on PC at all.

2. **Fill in the genre.** 73 of 180 rows had none, and the taxonomy that did
   exist overlapped — "FPS", "Shooter" and "Action" were not distinct. The UI
   needs it to decide what frame rate is *enough*, and a missing genre silently
   became 60, which is why League of Legends was being judged against 60 fps.

3. **Flag competitive play.** This is the honest version of what the target is
   actually asking. Genre is only a proxy: DOOM and Counter-Strike are both
   "FPS" and want completely different frame rates, because one is a
   single-player campaign and the other is ranked. What matters is whether
   input latency decides the outcome.

None of this touches cost profiles. Those are measurements, or estimates
standing in for measurements, and inventing them by hand is exactly the mistake
that put a Core Ultra 9 285K above a Ryzen 7 9800X3D in the CPU scores. A
genre is a documented fact; a frame time is not.

    python scripts/curate_games.py            # report
    python scripts/curate_games.py --apply
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

# Entries that should not be in a PC game catalogue.
REMOVE = {
    "Forza Motorsport 2":
        "Xbox 360 exclusive from 2007, never released on PC — and it was scored "
        "heavier than the 2023 Forza Motorsport, which is nonsense twice over",
    "Callisto Protocol":
        "duplicate of The Callisto Protocol, identical cost profile",
    "Prince of Persia: Lost Crown":
        "duplicate of Prince of Persia: The Lost Crown",
    "Portal RTX":
        "duplicate of Portal with RTX, which is the shipped name",
}

RENAME = {
    "Dying Light 1": "Dying Light",
}

# Ranked or esports play, where input latency decides the outcome. This drives
# the frame-rate target far better than genre does.
COMPETITIVE = {
    "Counter-Strike 2", "Valorant", "Apex Legends", "Overwatch 2",
    "Rainbow Six Siege", "PUBG", "Fortnite", "Call of Duty: Warzone",
    "Call of Duty: Black Ops 6", "Call of Duty: Modern Warfare III",
    "Battlefield 2042", "Marvel Rivals", "Delta Force", "Dota 2",
    "League of Legends", "Rocket League", "Street Fighter 6", "Tekken 8",
    "Escape from Tarkov", "Hunt: Showdown 1896", "The First Descendant",
}

# A finer taxonomy than the original, and complete. Only rows whose genre is
# missing or wrong are listed; everything else keeps what it has.
GENRE = {
    "A Plague Tale: Requiem": "Adventure",
    "ARK: Survival Ascended": "Survival",
    "Against the Storm": "City Builder",
    "Among Us": "Party",
    "Armored Core VI": "Action",
    "Callisto Protocol": "Horror",
    "Content Warning": "Party",
    "Dave the Diver": "Adventure",
    "DayZ": "Survival",
    "Dead Space Remake": "Horror",
    "Death Stranding 2": "Adventure",
    "Deep Rock Galactic": "Co-op Shooter",
    "Destiny 2": "Looter Shooter",
    "Dota 2": "MOBA",
    "Dredge": "Adventure",
    "Dying Light 1": "Survival",
    "Dying Light: The Beast": "Survival",
    "EA Sports FC 26": "Sports",
    "Escape from Tarkov": "Extraction Shooter",
    "F1 25": "Racing Sim",
    "Fall Guys": "Party",
    "Final Fantasy XVI": "JRPG",
    "Forspoken": "Action RPG",
    "Ghost of Tsushima": "Open World",
    "Ghostrunner": "Platformer",
    "Ghostrunner 2": "Platformer",
    "Gotham Knights": "Action RPG",
    "Grounded": "Survival",
    "Hades II": "Roguelike",
    "High on Life": "Shooter",
    "Hunt: Showdown 1896": "Extraction Shooter",
    "Kena: Bridge of Spirits": "Adventure",
    "Kingdom Come: Deliverance": "RPG",
    "League of Legends": "MOBA",
    "Lethal Company": "Co-op Horror",
    "Like a Dragon: Ishin": "Action RPG",
    "Little Nightmares III": "Puzzle Platformer",
    "Lost Ark": "MMO",
    "Manor Lords": "City Builder",
    "Metaphor: ReFantazio": "JRPG",
    "Monster Hunter Rise": "Action RPG",
    "NBA 2K25": "Sports",
    "Need for Speed Unbound": "Arcade Racing",
    "New World: Aeternum": "MMO",
    "Nier: Automata": "Action RPG",
    "No Rest for the Wicked": "Action RPG",
    "Phasmophobia": "Co-op Horror",
    "Planet Coaster 2": "Simulation",
    "Pragmata": "Action",
    "Prince of Persia: Lost Crown": "Metroidvania",
    "Risk of Rain 2": "Roguelike",
    "Rocket League": "Sports",
    "Rust": "Survival",
    "Sea of Thieves": "Adventure",
    "Silent Hill 2 Remake": "Horror",
    "Sons of the Forest": "Survival",
    "Star Wars Jedi: Survivor": "Action Adventure",
    "Stellar Blade": "Action",
    "Subnautica": "Survival",
    "The Callisto Protocol": "Horror",
    "The Medium": "Horror",
    "Uncharted: Legacy of Thieves Collection": "Action Adventure",
    "V Rising": "Survival",
    "Valheim": "Survival",
    "Vampire Survivors": "Roguelike",
    "WWE 2K24": "Sports",
    "Warframe": "Looter Shooter",
    "Warhammer 40K: Darktide": "Co-op Shooter",
    "Witchfire": "Shooter",
    "Wo Long: Fallen Dynasty": "Souls-like",
    "World of Warcraft": "MMO",
    "Frostpunk 2": "City Builder",
    "Forza Motorsport 2": "Racing Sim",

    # Corrections to genres that were already there but wrong.
    "Grand Theft Auto V Enhanced": "Open World",   # was RPG
    "GTA V": "Open World",                          # was Action
    "Elden Ring": "Souls-like",                     # was RPG
    "Dark Souls III": "Souls-like",                 # was Action
    "Sekiro: Shadows Die Twice": "Souls-like",      # was Action
    "Lies of P": "Souls-like",                      # was Action
    "Lords of the Fallen": "Souls-like",            # was Action
    "Helldivers 2": "Co-op Shooter",                # was Shooter
    "Forza Motorsport": "Racing Sim",
    "Assetto Corsa Competizione": "Racing Sim",
    "Gran Turismo 7": "Racing Sim",
    "F1 2024": "Racing Sim",
    "Forza Horizon 5": "Arcade Racing",
    "Forza Horizon 6": "Arcade Racing",
    "Cities: Skylines II": "City Builder",
    "Minecraft RTX": "Sandbox",
    "Path of Exile 2": "Action RPG",
    "Diablo IV": "Action RPG",
    "Baldur's Gate 3": "CRPG",
    "Starfield": "RPG",
}

# What "enough frames" means, by genre, for games that are not competitive.
# Competitive play overrides all of this at 144.
TARGET_BY_GENRE = {
    "Racing Sim": 90, "Arcade Racing": 90, "Fighting": 90,
    "Shooter": 72, "Co-op Shooter": 72, "Looter Shooter": 72,
    "Extraction Shooter": 90, "FPS": 72, "Action": 72,
    "Action Adventure": 72, "Souls-like": 72, "Platformer": 72,
    "Metroidvania": 72, "Roguelike": 72, "Sports": 72, "Horror": 72,
    "Co-op Horror": 72, "Stealth": 72, "Survival": 72, "Open World": 72,
    "Action RPG": 72, "Sandbox": 60, "Adventure": 60, "RPG": 60,
    "CRPG": 60, "JRPG": 60, "MMO": 60, "Simulation": 60, "City Builder": 60,
    "Strategy": 60, "Puzzle": 60, "Puzzle Platformer": 60, "Party": 60,
    "MOBA": 144,
}
COMPETITIVE_TARGET = 144
DEFAULT_TARGET = 60


def target_for(genre, competitive):
    if competitive:
        return COMPETITIVE_TARGET
    return TARGET_BY_GENRE.get(genre, DEFAULT_TARGET)


def main(apply_changes):
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(games)")}
    additions = []
    for col, decl in (("competitive", "INTEGER DEFAULT 0"),
                      ("target_fps", "INTEGER")):
        if col not in cols:
            additions.append(col)
            if apply_changes:
                cur.execute(f"ALTER TABLE games ADD COLUMN {col} {decl}")
    if additions:
        print(f"  yeni sutun: {', '.join(additions)}"
              + ("" if apply_changes else "  (kuru calisma, eklenmedi)"))

    rows = [dict(r) for r in cur.execute("SELECT id, name, genre FROM games")]
    by_name = {r["name"]: r for r in rows}

    print("\n=== 1. KALDIRILAN KAYITLAR ===")
    removed = 0
    for name, why in REMOVE.items():
        if name in by_name:
            removed += 1
            print(f"  {name}\n      {why}")
            if apply_changes:
                cur.execute("DELETE FROM games WHERE id=?", (by_name[name]["id"],))
    if not removed:
        print("  (yok — zaten temizlenmis)")

    print("\n=== 2. YENIDEN ADLANDIRMA ===")
    for old, new in RENAME.items():
        if old in by_name:
            print(f"  {old}  ->  {new}")
            if apply_changes:
                cur.execute("UPDATE games SET name=? WHERE id=?", (new, by_name[old]["id"]))

    print("\n=== 3. TUR VE REKABET BAYRAGI ===")
    filled = fixed = comp = 0
    for r in rows:
        if r["name"] in REMOVE:
            continue
        name = RENAME.get(r["name"], r["name"])
        genre = GENRE.get(r["name"]) or GENRE.get(name) or r["genre"]
        if not genre:
            continue
        if not r["genre"]:
            filled += 1
        elif genre != r["genre"]:
            fixed += 1
        is_comp = 1 if name in COMPETITIVE else 0
        comp += is_comp
        if apply_changes:
            cur.execute(
                "UPDATE games SET genre=?, competitive=?, target_fps=? WHERE id=?",
                (genre, is_comp, target_for(genre, is_comp), r["id"]))

    print(f"  {filled} oyunun turu dolduruldu, {fixed} tanesi duzeltildi")
    print(f"  {comp} oyun rekabetci olarak isaretlendi ({COMPETITIVE_TARGET} fps hedefi)")

    still = [r["name"] for r in rows
             if r["name"] not in REMOVE
             and not (GENRE.get(r["name"]) or r["genre"])]
    if still:
        print(f"  UYARI: hala turu olmayan {len(still)}: {still[:8]}")

    if apply_changes:
        conn.commit()
        print("\n  yazildi. scripts/export_engine_data.py calistirmayi unutmayin.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
