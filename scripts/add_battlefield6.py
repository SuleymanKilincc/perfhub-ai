"""
Adds Battlefield 6 and the Ryzen 5 8400F, both needed before batch 7 can load.

**The game.** Its cost profile is deliberately left as a copy of Battlefield
2042's. The 33-CPU ladder that follows varies the processor, which is one of
the three things `is_identifiable` accepts, so calibrate_engine will fit both
costs from the measurements and overwrite whatever is seeded here. What it will
*not* fit is memory: there are no VRAM readings in this batch, so vram_base_gb
and ram_base_gb keep 2042's figures and remain a guess about a different game.

**The processor.** Scored from that ladder, and it is the weakest score in the
catalogue derived this way, because it rests on one game rather than the eight
behind the 5700X3D. The neighbours split cleanly into two answers:

    i5-12400F  122 fps, score 52  ->  48
    Ryzen 7500F 141 fps, score 60  ->  48
    Ryzen 5800X 111 fps, score 54  ->  55
    i9-11900K  110 fps, score 57  ->  59

48 is the one used. The 7500F is the right comparison — Zen 4, six cores, same
generation — and the gap between them is cache: 16 MB of L3 against 32 MB, in a
game where cache is worth a great deal. The two answers near 55 both come from
older eight-core parts, so what they really report is that this title rewards
cache and cores differently from the average of our set, not that the 8400F is
faster than it looks.

One game is thin evidence for a score. If this chip turns up in a second
ladder, check it.

    python scripts/add_battlefield6.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Battlefield 6"
CLONE_FROM = "Battlefield 2042"
GAME_OVERRIDES = {
    "genre": "FPS",
    "competitive": 1,
    "target_fps": 144,
    "tier_min": "Low",
    "tier_max": "Ultra",
    "flags_verified": 0,
    "steam_appid": None,
    "cover_url": None,
    "fps_low_measured": 0,
}

CPU = "AMD Ryzen 5 8400F"
CPU_SPEC = dict(cores=6, threads=12, base_clock=4.2, boost_clock=4.7,
                architecture="Zen 4", power_score=48)


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if cur.execute("SELECT 1 FROM games WHERE name=?", (GAME,)).fetchone():
        print(f"  {GAME} zaten katalogda")
    else:
        src = cur.execute("SELECT * FROM games WHERE name=?", (CLONE_FROM,)).fetchone()
        if not src:
            sys.exit(f"  {CLONE_FROM} bulunamadi")
        row = {k: src[k] for k in src.keys() if k != "id"}
        row["name"] = GAME
        row.update({k: v for k, v in GAME_OVERRIDES.items() if k in row})
        print(f"  {GAME}: {CLONE_FROM} profili kopyalaniyor "
              f"(gpu={row['gpu_cost']:.2f} cpu={row['cpu_cost']:.2f}, "
              f"olcumlerle degisecek)")
        print(f"    vram_base={row['vram_base_gb']:.1f} ram_base={row['ram_base_gb']:.1f}"
              f" — bunlar fit EDILMEYECEK, {CLONE_FROM}'nin degerleri kalacak")
        if apply_changes:
            cols = ", ".join(row)
            cur.execute(f"INSERT INTO games ({cols}) VALUES ({','.join('?' * len(row))})",
                        tuple(row.values()))

    if cur.execute("SELECT 1 FROM cpus WHERE name=?", (CPU,)).fetchone():
        print(f"  {CPU} zaten katalogda")
    else:
        print(f"  {CPU}: puan {CPU_SPEC['power_score']} (tek oyundan — dosya basina bakin)")
        if apply_changes:
            cur.execute(
                "INSERT INTO cpus (name, cores, threads, base_clock, boost_clock,"
                " architecture, power_score) VALUES (?,?,?,?,?,?,?)",
                (CPU, CPU_SPEC["cores"], CPU_SPEC["threads"], CPU_SPEC["base_clock"],
                 CPU_SPEC["boost_clock"], CPU_SPEC["architecture"],
                 CPU_SPEC["power_score"]))

    if apply_changes:
        conn.commit()
        print("  yazildi.")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
