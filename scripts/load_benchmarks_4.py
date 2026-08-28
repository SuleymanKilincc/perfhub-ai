"""
Batch 4 — three outside systems, kept as a held-out set rather than fitted.

All three are free gameplay, not benchmark loops, so they go in with
scene='gameplay' and never touch the cost fit. What makes them worth keeping is
exactly that: a set the fit has never seen is the only way to find out whether
the engine generalises, and the first thing it did was correct a conclusion
drawn from earlier data.

That conclusion was that pre-2019 architectures are over-predicted by ~110%
because they lack mesh shaders and the rest of the DX12 Ultimate set. The GTX
1080 Ti disproves it as a general claim. It is Pascal, same generation as the
GTX 1070 that read +131%, and across ten modern games it comes to +8%. On Alan
Wake 2 — the case that read +308% on the 1070 — it lands within 2%.

The difference between those two cards is not the architecture, it is 11 GB
against 8. And the VRAM readings here say why: modern games at 1080p are
touching 8.8 to 9.8 GB, while the model puts them 18% lower. On an 8 GB card
the model sees four of these games spilling where seven really do, so the
collapse that spilling causes is invisible to it and the estimate stays
confident.

Only the VRAM figures are loaded, and only from the 1080 Ti: at 11 GB nothing
is clamped by capacity, so its overlay numbers are the games' own appetite.
They are marked vram_measured_kind='used' — the overlay reports usage, and
inverting usage through the allocation model would land ~25% low.

The frame rates come along because the schema requires one, and they are the
weakest part of the row: the source notes 10-15 fps swings between scenes in
open-world games. scene='gameplay' is what keeps them out of the fit.

    python scripts/load_benchmarks_4.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

CPU = "AMD Ryzen 5 3600"
GPU = "NVIDIA GeForce GTX 1080 Ti"
RAM = 32
SOURCE = "b9-1080ti-3600"

# game, settings, upscaling, fps, vram used (GB)
ROWS = [
    ("A Plague Tale: Requiem", "High", "Native", 58, 8.8),
    ("Alan Wake 2", "Medium", "FSR Quality", 45, 9.2),
    ("Baldur's Gate 3", "Ultra", "Native", 75, 6.5),
    ("Counter-Strike 2", "Ultra", "Native", 180, 5.2),
    ("Cyberpunk 2077", "High", "Native", 50, 9.5),
    ("Elden Ring", "Ultra", "Native", 60, 5.8),
    ("Far Cry 6", "Ultra", "Native", 85, 7.4),
    ("Forza Horizon 5", "Extreme", "Native", 90, 7.8),
    ("Hogwarts Legacy", "High", "Native", 55, 9.8),
    ("Kingdom Come: Deliverance 2", "Ultra", "Native", 45, 9.4),
    ("Red Dead Redemption 2", "Ultra", "Native", 65, 8.4),
    ("The Last of Us Part II", "High", "Native", 55, 9.7),
]

# Deliberately not loaded:
#   the RTX 2060 and GTX 1050 Ti systems
#       Their overlays report usage against 6 GB and 4 GB, and the games that
#       matter here are the ones pressing on that ceiling — so the figures say
#       what the card allowed, not what the game wanted.
#   every "Very High", "Ultra High", "Balanced", "Epic", "Low/Med" preset
#       These do not map onto a tier the model has. Guessing which one would
#       put the guess inside a column that reads as measured.
#   900p rows, and anything reported as a range ("40-60", "70+")


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}
    for needed in ("scene", "vram_measured_kind"):
        if needed not in cols:
            sys.exit(f"  {needed} sutunu yok — once migrate_measurement_kind.py")

    capacity = cur.execute("SELECT vram FROM gpus WHERE name=?", (GPU,)).fetchone()[0]
    print(f"  {GPU} — {capacity} GB\n")
    print(f"  {'oyun':30s} {'preset':8s} {'fps':>4s} {'vram':>6s}")

    added = clamped = 0
    for game, settings, ups, fps, vram in ROWS:
        if not cur.execute("SELECT 1 FROM games WHERE name=?", (game,)).fetchone():
            sys.exit(f"  {game} katalogda yok")
        # Same guard calibrate_vram applies, checked here so a clamped reading
        # is never written in the first place.
        if vram >= capacity * 0.94:
            clamped += 1
            print(f"  {game[:30]:30s} {settings:8s} {fps:4.0f} {vram:5.1f}GB  tavana yakin, VRAM atlandi")
            vram = None
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution='1080p'"
            " AND settings=? AND upscaling=?", (game, CPU, GPU, settings, ups)).fetchone()
        if dup:
            print(f"  {game[:30]:30s} {settings:8s} — zaten var, atlandi")
            continue
        added += 1
        print(f"  {game[:30]:30s} {settings:8s} {fps:4.0f} "
              f"{(f'{vram:5.1f}GB' if vram else '     -')}")
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb,"
                " fps_avg, vram_measured_gb, vram_measured_kind, scene, source,"
                " verified) VALUES (?,?,?,'1080p',?,?,'Kapalı',0,0,?,?,?,'used',"
                "'gameplay',?,1)",
                (game, CPU, GPU, settings, ups, RAM, fps, vram, SOURCE))

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{', ' + str(clamped) + ' VRAM degeri tavana yakin oldugu icin atlandi' if clamped else ''}")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        gp = cur.execute("SELECT COUNT(*) FROM benchmarks WHERE scene='gameplay'").fetchone()[0]
        print(f"  toplam {total} olcum, {gp} tanesi fit disi (gameplay)")
        print("  simdi: calibrate_vram.py --apply, validate_engine.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
