"""
Derives per-game VRAM working sets from measured allocations.

The `vram_base_gb` values were originally derived from difficulty_multiplier,
which conflates "expensive to render" with "hungry for memory" — and got it
badly wrong. A Plague Tale: Requiem is one of the heaviest games to render and
uses about 5 GB; the derived value said 12.3.

Overlays report *allocation*, so the measured figures have to be inverted
through the allocation model to recover the working set:

    allocation = working * VRAM_ALLOC_APPETITE + VRAM_ALLOC_HEADROOM_GB
    working    = base * quality_vram * res_vram + rt/pt/fg additions

Rows where allocation was clamped by the card's capacity are discarded — on
those the number says more about the GPU than the game. Alan Wake 2 reporting
28 GB at 8K on a 32 GB card is exactly that case.

Run from the repo root:  python scripts/calibrate_vram.py [--apply]
"""
import argparse
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import balance_config as bc
from core import db_manager


def main(apply_changes):
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    games = {g["name"]: dict(g) for g in db_manager.get_all_games()}
    gpus = {g["name"]: dict(g) for g in db_manager.get_all_gpus()}
    rows = [dict(r) for r in cur.execute(
        "SELECT * FROM benchmarks WHERE vram_measured_gb IS NOT NULL")]

    estimates = defaultdict(list)
    discarded = 0

    for r in rows:
        capacity = gpus[r["gpu"]]["vram"] or 8
        measured = r["vram_measured_gb"]

        # Discard anything at or near the card's ceiling: the game would have
        # taken more if it could, so the figure is a property of the GPU.
        if measured >= capacity * bc.VRAM_ALLOC_CAPACITY_LIMIT * 0.97:
            discarded += 1
            continue

        working = (measured - bc.VRAM_ALLOC_HEADROOM_GB) / bc.VRAM_ALLOC_APPETITE

        # Strip the additions the engine layers on top of the base figure.
        if r["path_tracing"]:
            working -= bc.PT_VRAM_ADD_GB
        elif r["ray_tracing"]:
            working -= bc.RT_VRAM_ADD_GB
        working -= bc.FG_VRAM_ADD_GB.get(r["frame_gen"], 0.0)

        _, _, q_vram = bc.quality_multipliers(r["settings"])
        res_factor = bc.RES_VRAM_FACTOR.get(r["resolution"], 1.0)

        # Upscaling shrinks the framebuffers but not the textures, mirroring
        # the reduction applied in scoring_engine._vram_demand.
        up = (r["upscaling"] or "native").lower()
        scale = 1.0
        for keyword, value in bc.UPSCALING_RENDER_SCALE.items():
            if keyword in up:
                scale = value
                break
        if scale < 1.0:
            working /= (0.72 + 0.28 * scale ** 2)

        base = working / (q_vram * res_factor)
        if base > 0.3:
            estimates[r["game"]].append(base)

    print(f"  {len(rows)} VRAM olcumu, {discanded_note(discarded)}")
    print()
    print(f"  {'Oyun':32s} {'eski':>6s} {'yeni':>6s}  n")
    updates = {}
    for name, vals in sorted(estimates.items()):
        new = sum(vals) / len(vals)
        old = games[name].get("vram_base_gb") or 0
        updates[name] = new
        flag = "  <-- buyuk fark" if old and abs(new - old) / old > 0.35 else ""
        print(f"  {name[:32]:32s} {old:6.1f} {new:6.1f}  {len(vals)}{flag}")

    if apply_changes:
        for name, val in updates.items():
            cur.execute("UPDATE games SET vram_base_gb=? WHERE name=?",
                        (round(val, 2), name))
        conn.commit()
        print(f"\n  {len(updates)} oyunun vram_base_gb degeri guncellendi.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")

    conn.close()


def discanded_note(n):
    return f"{n} tanesi kart kapasitesine dayandigi icin atildi" if n else "hicbiri atilmadi"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
