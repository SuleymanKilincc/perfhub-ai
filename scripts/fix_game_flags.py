"""
Corrects feature flags that were wrong, and separates who says so.

The prompt for this was Resident Evil Requiem showing path tracing as
unavailable when the game offers it. Checking around that found more: The
Witcher 3 listed with no upscaler at all, though the Next-Gen update shipped
DLSS 3 and FSR 2; Quake II RTX marked as having path tracing but not DLSS,
which is contradictory for a title built as an NVIDIA showcase.

The wider picture is worse than any single row. 148 of the 176 games have
never had their flags checked — `flags_verified` is 0 — and the interface
offers their ray-tracing and upscaling toggles with exactly the confidence it
gives a checked one. That is the same failure that has come up all through this
project: an unverified value presented as fact.

So corrections here come in two kinds and are not conflated.

  OBSERVED   Someone ran the game and looked. Resident Evil Requiem is here
             because Süleyman saw the path-tracing option in its menu. These
             set flags_verified = 1.

  RECALLED   My own knowledge of what a game shipped. Better than the value it
             replaces, which came from a genre derivation, but nobody has
             checked it against the game. These leave flags_verified at 0, so
             they stay in the queue of things to confirm.

Fixing the remaining ~145 needs someone to open each game's settings. It is not
something to guess through in bulk, and pretending otherwise would put a
confident wrong flag where an admittedly unknown one is at least honest.

    python scripts/fix_game_flags.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

# game -> {column: value}
OBSERVED = {
    # Süleyman, in-game, 2026-08-30. The menu offers path tracing.
    "Resident Evil Requiem": {"supports_pt": 1},
}

# Flags our own measurements contradict. These need no judgement at all: if a
# game was benchmarked with ray tracing on, it has ray tracing. `--check` finds
# them, and finding one means either the flag or the measurement is wrong —
# both worth knowing.
CONTRADICTED = {
    # Two rows measured with ray_tracing=1 while the flag said the game has
    # none. It does: ray-traced shadows and global illumination arrived in a
    # 2023 patch.
    "A Plague Tale: Requiem": {"supports_rt": 1},
}

# Third-party research Süleyman relayed on 2026-08-30. Neither of us opened
# these games, and unlike the ray-tracing-level and VRAM claims earlier in this
# project there is nothing here I can test — we hold no XeSS measurements, so
# the contradiction scan cannot speak to it either. They go in at
# flags_verified = 0 and stay in the queue.
#
# Two claims in the same report asked for changes that were already the case
# (Assetto Corsa Competizione's XeSS was off already), and one described
# Hitman 3 as having XeSS *and* called our row correct while our row says it
# does not — so that one is left alone until someone looks at the menu.
RELAYED = {
    # Reported as launching without ray tracing, the engine built for frame
    # rate rather than reflections. Consistent with the flag having come from a
    # genre derivation that assumed every modern shooter has it.
    "Battlefield 6": {"supports_rt": 0},
    # An AMD partner title: FSR yes, DLSS never shipped. This one I would have
    # bet on independently.
    "Far Cry 6": {"supports_dlss": 0},
    # XeSS arriving in post-launch updates. Remnant II and Starfield match what
    # I remember; Baldur's Gate 3 and Space Marine 2 I could not confirm on my
    # own, and they are here on the strength of the report alone.
    "Remnant II": {"supports_xess": 1},
    "Starfield": {"supports_xess": 1},
    "Baldur's Gate 3": {"supports_xess": 1},
    "Warhammer 40K: Space Marine 2": {"supports_xess": 1},
}

RECALLED = {
    # The Next-Gen update (December 2022) added DLSS 3, FSR 2 and ray tracing.
    "The Witcher 3: Wild Hunt": {"supports_rt": 1, "supports_dlss": 1, "supports_fsr": 1},
    # DLSS and FSR both arrived in post-launch updates.
    "Destiny 2": {"supports_dlss": 1, "supports_fsr": 1},
    "Sea of Thieves": {"supports_dlss": 1, "supports_fsr": 1},
    "Warframe": {"supports_dlss": 1},
    # A path-traced NVIDIA showcase with DLSS switched off in the catalogue,
    # which cannot be right — DLSS is the reason it runs at all.
    "Quake II RTX": {"supports_dlss": 1},
    # Path tracing added after launch, in both cases as an NVIDIA
    # collaboration.
    "Star Wars Outlaws": {"supports_pt": 1},
    "DOOM: The Dark Ages": {"supports_pt": 1},
}


# Measurements the scan proved wrong, rather than flags. Fixing a flag can
# expose a bad row: setting Far Cry 6's supports_dlss to 0 made the scan report
# two of its rows as using DLAA, which the game does not have — it never
# shipped DLSS or anything built on it. The rows came from a source that
# recorded the game's own temporal AA, and DLAA was the wrong word for it. In
# this model that word is not cosmetic: DLAA costs an upscaling pass and Native
# does not.
MEASUREMENT_FIXES = [
    # (source, game, old upscaling, new upscaling)
    ("batch6-hdtex", "Far Cry 6", "DLAA", "Native"),
]


CHECKS = [
    ("RT", "supports_rt", "ray_tracing=1"),
    ("PT", "supports_pt", "path_tracing=1"),
    ("DLSS", "supports_dlss", "upscaling LIKE 'DLSS%' OR upscaling='DLAA'"),
    ("FSR", "supports_fsr", "upscaling LIKE 'FSR%'"),
    ("XeSS", "supports_xess", "upscaling LIKE 'XeSS%'"),
]


def check(cur):
    """Flags the benchmark table disagrees with. Needs no judgement to read."""
    found = 0
    for label, col, cond in CHECKS:
        for r in cur.execute(
                f"SELECT b.game, COUNT(*) n FROM benchmarks b"
                f" JOIN games g ON g.name = b.game"
                f" WHERE ({cond}) AND COALESCE(g.{col}, 0) = 0"
                f" GROUP BY b.game"):
            found += 1
            print(f"  {label:5s} {r['game'][:36]:36s} {r['n']:3d} olcum var, bayrak kapali")
    if not found:
        print("  celiski yok — her olcum kendi oyununun bayraklariyla tutarli")
    return found


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for label, table, verified in (("GOZLEMLENDI", OBSERVED, 1),
                                   ("OLCUMLE CELISEN", CONTRADICTED, 1),
                                   ("HATIRLANAN", RECALLED, 0),
                                   ("AKTARILAN", RELAYED, 0)):
        print(f"\n=== {label} ===")
        for game, changes in table.items():
            row = cur.execute("SELECT * FROM games WHERE name=?", (game,)).fetchone()
            if not row:
                print(f"  {game[:36]:36s} KATALOGDA YOK")
                continue
            diff = {k: v for k, v in changes.items() if row[k] != v}
            if not diff:
                print(f"  {game[:36]:36s} zaten dogru")
                continue
            shown = ", ".join(f"{k.replace('supports_', '')}: {row[k]} -> {v}"
                              for k, v in diff.items())
            print(f"  {game[:36]:36s} {shown}")
            if apply_changes:
                sets = ", ".join(f"{k}=?" for k in diff)
                cur.execute(f"UPDATE games SET {sets}, flags_verified=? WHERE name=?",
                            (*diff.values(), verified, game))

    print()
    print("=== OLCUM DUZELTMELERI ===")
    for source, game, old, new in MEASUREMENT_FIXES:
        rows = cur.execute(
            "SELECT id, gpu, resolution FROM benchmarks"
            " WHERE source=? AND game=? AND upscaling=?", (source, game, old)).fetchall()
        if not rows:
            print(f"  {game[:30]:30s} {old} -> {new}: eslesen satir yok (yapilmis)")
            continue
        for r in rows:
            print(f"  id={r['id']:3d} {game[:26]:26s} {r['resolution']:6s} "
                  f"{r['gpu'][14:32]:18s} {old} -> {new}")
        if apply_changes:
            cur.execute("UPDATE benchmarks SET upscaling=? WHERE source=? AND game=?"
                        " AND upscaling=?", (new, source, game, old))

    print()
    print("=== OLCUMLERLE CELISKI TARAMASI ===")
    check(cur)

    unchecked = cur.execute(
        "SELECT COUNT(*) FROM games WHERE COALESCE(flags_verified, 0)=0").fetchone()[0]
    total = cur.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    print(f"\n  {unchecked}/{total} oyunun bayraklari hala kontrol edilmemis.")
    print("  Bunlari toplu tahminle doldurmak, bilinmediginin kabul edildigi bir")
    print("  degeri kendinden emin yanlis bir degerle degistirmek olurdu.")

    if apply_changes:
        conn.commit()
        print("\n  yazildi.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
