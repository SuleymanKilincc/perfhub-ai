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


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for label, table, verified in (("GOZLEMLENDI", OBSERVED, 1),
                                   ("HATIRLANAN", RECALLED, 0)):
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
