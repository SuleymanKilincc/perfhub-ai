"""
Second measured benchmark batch, with VRAM figures.

Adds ~45 results covering resolution sweeps for the games that had no
calibrated profile, path tracing on two titles, extreme CPU-bound cases, an
8K run, and a full frame-generation ladder.

Two things about this batch shape the model rather than just tuning it:

  * Every row carries the VRAM figure the overlay reported. Those are
    *allocations*, not working sets, and they were captured on 16-32 GB cards
    where engines cache freely — Alan Wake 2 reported 28 GB at 8K. They are
    stored as an upper bound, and the working set is inferred separately.
  * Elden Ring was measured with its 60 fps cap lifted, which is what makes
    the numbers useful for hardware comparison. The cap is recorded on the
    game row so the engine can report both.

Run from the repo root:  python scripts/load_benchmarks_2.py
"""
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

CPU = {
    "9800X3D": "AMD Ryzen 7 9800X3D",
    "9950X3D": "AMD Ryzen 9 9950X3D",
    "7950X3D": "AMD Ryzen 9 7950X3D",
    "7800X3D": "AMD Ryzen 7 7800X3D",
}
GPU = {
    "5080": "NVIDIA GeForce RTX 5080",
    "5090": "NVIDIA GeForce RTX 5090",
    "4090": "NVIDIA GeForce RTX 4090",
    "5070Ti": "NVIDIA GeForce RTX 5070 Ti",
    "5060Ti16": "NVIDIA GeForce RTX 5060 Ti 16GB",
}

# Games the batch references that the catalog lacks.
NEW_GAMES = [
    # (name, clone_from, tier_max override or None)
    ("Grand Theft Auto V Enhanced", "Cyberpunk 2077", None),
    ("Resident Evil Requiem", "Resident Evil 4 Remake", None),
]

# Preset ladders wider than Low..Ultra, discovered while recording this batch.
TIER_OVERRIDES = {
    "Kingdom Come: Deliverance 2": ("Low", "Extreme"),   # "Experimental" preset
}

# (game, cpu, gpu, res, preset, upscaling, framegen, rt, pt, ram, fps, vram, source)
M = [
    # ── The Last of Us Part I — 9800X3D + 5080, max settings ───────────────
    ("The Last of Us Part I", "9800X3D", "5080", "4k", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 65, 12.2, "b7-tlou"),
    ("The Last of Us Part I", "9800X3D", "5080", "4k", "Ultra", "DLSS Quality", "Kapalı", 0, 0, 32, 90, 10.6, "b7-tlou"),
    ("The Last of Us Part I", "9800X3D", "5080", "4k", "Ultra", "DLSS Performance", "Kapalı", 0, 0, 32, 102, 10.1, "b7-tlou"),
    ("The Last of Us Part I", "9800X3D", "5080", "1440p", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 89, 10.2, "b7-tlou"),
    ("The Last of Us Part I", "9800X3D", "5080", "1080p", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 123, 9.4, "b7-tlou"),

    # ── Forza Horizon 5 — RT here is only car reflections, so recorded off ──
    ("Forza Horizon 5", "9800X3D", "5080", "4k", "Ultra", "Native", "Kapalı", 0, 0, 32, 123, 10.3, "b7-fh5"),
    ("Forza Horizon 5", "9800X3D", "5080", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 170, 9.8, "b7-fh5"),
    ("Forza Horizon 5", "9800X3D", "5080", "1080p", "Ultra", "Native", "Kapalı", 0, 0, 32, 185, 9.2, "b7-fh5"),

    # ── Forza Horizon 6 — real ray tracing, measured both ways ─────────────
    ("Forza Horizon 6", "9800X3D", "5080", "4k", "Ultra", "DLAA", "Kapalı", 1, 0, 32, 57, 13.5, "b7-fh6rt"),
    ("Forza Horizon 6", "9800X3D", "5080", "4k", "Ultra", "DLSS Quality", "Kapalı", 1, 0, 32, 83, 13.1, "b7-fh6rt"),
    ("Forza Horizon 6", "9800X3D", "5080", "4k", "Ultra", "DLSS Quality", "2x", 1, 0, 32, 125, 14.0, "b7-fh6rt"),
    ("Forza Horizon 6", "9800X3D", "5080", "1440p", "Ultra", "DLAA", "Kapalı", 1, 0, 32, 85, 13.7, "b7-fh6rt"),
    ("Forza Horizon 6", "9800X3D", "5080", "1080p", "Ultra", "DLAA", "Kapalı", 1, 0, 32, 127, 12.8, "b7-fh6rt"),
    ("Forza Horizon 6", "9800X3D", "5080", "4k", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 89, 12.8, "b7-fh6"),
    ("Forza Horizon 6", "9800X3D", "5080", "4k", "Ultra", "DLAA", "2x", 0, 0, 32, 152, 13.2, "b7-fh6"),
    ("Forza Horizon 6", "9800X3D", "5080", "4k", "Ultra", "DLAA", "4x", 0, 0, 32, 260, 13.3, "b7-fh6"),
    ("Forza Horizon 6", "9800X3D", "5080", "1440p", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 133, 12.2, "b7-fh6"),
    ("Forza Horizon 6", "9800X3D", "5080", "1080p", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 175, 11.9, "b7-fh6"),

    # ── Kingdom Come: Deliverance 2 — "Experimental" is above Ultra ────────
    ("Kingdom Come: Deliverance 2", "9800X3D", "5080", "4k", "Extreme", "DLAA", "Kapalı", 0, 0, 32, 61, 12.7, "b7-kcd2"),
    ("Kingdom Come: Deliverance 2", "9800X3D", "5080", "1440p", "Extreme", "DLAA", "Kapalı", 0, 0, 32, 104, 11.9, "b7-kcd2"),
    ("Kingdom Come: Deliverance 2", "9800X3D", "5080", "1080p", "Extreme", "DLAA", "Kapalı", 0, 0, 32, 123, 11.2, "b7-kcd2"),

    # ── Alan Wake 2 — the path tracing reference, plus an 8K run ───────────
    ("Alan Wake 2", "9800X3D", "5090", "4k", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 70, 12.0, "b7-aw2"),
    ("Alan Wake 2", "9800X3D", "5090", "4k", "Ultra", "DLAA", "Kapalı", 1, 1, 32, 28, 14.0, "b7-aw2"),
    ("Alan Wake 2", "9800X3D", "5090", "4k", "Ultra", "DLAA", "2x", 1, 1, 32, 48, 15.0, "b7-aw2"),
    ("Alan Wake 2", "9800X3D", "5090", "1440p", "Ultra", "DLAA", "Kapalı", 1, 1, 32, 57, 12.0, "b7-aw2"),
    ("Alan Wake 2", "9800X3D", "5090", "8k", "Ultra", "DLAA", "Kapalı", 1, 1, 32, 8, 28.0, "b7-aw2"),
    # Frame gen at 8K gained almost nothing: VRAM ran out and ~4 GB spilled to
    # system RAM. A direct observation of the behaviour the memory model exists
    # to predict.
    ("Alan Wake 2", "9800X3D", "5090", "8k", "Ultra", "DLAA", "4x", 1, 1, 32, 10, 32.0, "b7-aw2-vramout"),

    # ── Black Myth: Wukong ─────────────────────────────────────────────────
    ("Black Myth: Wukong", "7950X3D", "4090", "4k", "Ultra", "DLAA", "Kapalı", 1, 0, 32, 28, 12.7, "b7-wukong"),
    ("Black Myth: Wukong", "7950X3D", "4090", "1440p", "Ultra", "DLAA", "Kapalı", 1, 0, 32, 49, 10.0, "b7-wukong"),

    # ── Starfield ──────────────────────────────────────────────────────────
    ("Starfield", "7800X3D", "5090", "4k", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 103, 8.9, "b7-starfield"),
    ("Starfield", "7800X3D", "5090", "1440p", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 125, 7.0, "b7-starfield"),
    ("Starfield", "7800X3D", "5090", "1080p", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 145, 6.7, "b7-starfield"),

    # ── Cities: Skylines II — CPU-bound extreme. GPU sat at 70-80% even on a
    #    5090; the second row is a 1.2M-population save using 35 GB of RAM.
    ("Cities: Skylines II", "9950X3D", "5090", "4k", "Ultra", "Native", "Kapalı", 0, 0, 96, 45, 12.5, "b7-cs2-500k"),
    ("Cities: Skylines II", "9950X3D", "5090", "4k", "Ultra", "DLAA", "Kapalı", 0, 0, 96, 32, 12.8, "b7-cs2-1.2m"),

    # ── Microsoft Flight Simulator — heavy on both, 25 GB of system RAM ─────
    ("Microsoft Flight Simulator", "9800X3D", "4090", "4k", "Ultra", "Native", "Kapalı", 0, 0, 32, 55, 16.0, "b7-msfs"),
    ("Microsoft Flight Simulator", "9800X3D", "4090", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 65, 14.2, "b7-msfs"),
    ("Microsoft Flight Simulator", "9800X3D", "4090", "1080p", "Ultra", "Native", "Kapalı", 0, 0, 32, 70, 13.2, "b7-msfs"),

    # ── Valorant — the CPU wall in its purest form. Ultra vs Low differs by
    #    4%, and 1080p vs 1440p by 5%.
    ("Valorant", "9950X3D", "5080", "1440p", "Low", "Native", "Kapalı", 0, 0, 32, 750, 3.5, "b7-valorant"),
    ("Valorant", "9950X3D", "5080", "1440p", "High", "Native", "Kapalı", 0, 0, 32, 720, 4.1, "b7-valorant"),
    ("Valorant", "9950X3D", "5080", "1080p", "Low", "Native", "Kapalı", 0, 0, 32, 790, 3.2, "b7-valorant"),
    ("Valorant", "9950X3D", "5080", "1080p", "High", "Native", "Kapalı", 0, 0, 32, 760, 3.6, "b7-valorant"),

    # ── Elden Ring — measured with the 60 fps cap lifted ───────────────────
    ("Elden Ring", "7800X3D", "5070Ti", "4k", "Ultra", "Native", "Kapalı", 0, 0, 32, 105, 7.8, "b7-eldenring-uncapped"),
    ("Elden Ring", "7800X3D", "5070Ti", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 150, 6.6, "b7-eldenring-uncapped"),

    # ── Resident Evil Requiem ──────────────────────────────────────────────
    ("Resident Evil Requiem", "9800X3D", "5090", "4k", "Ultra", "DLAA", "Kapalı", 1, 1, 32, 40, 16.2, "b7-rerequiem"),
    ("Resident Evil Requiem", "9800X3D", "5090", "4k", "Ultra", "DLSS Quality", "Kapalı", 1, 1, 32, 83, 14.5, "b7-rerequiem"),

    # ── Frame generation ladder — GTA V Enhanced, RT on, 1440p DLAA ────────
    ("Grand Theft Auto V Enhanced", "9800X3D", "5060Ti16", "1440p", "Ultra", "DLAA", "Kapalı", 1, 0, 32, 59, 8.1, "b7-fg"),
    ("Grand Theft Auto V Enhanced", "9800X3D", "5060Ti16", "1440p", "Ultra", "DLAA", "2x", 1, 0, 32, 90, 8.8, "b7-fg"),
    ("Grand Theft Auto V Enhanced", "9800X3D", "5060Ti16", "1440p", "Ultra", "DLAA", "3x", 1, 0, 32, 130, 8.9, "b7-fg"),
    ("Grand Theft Auto V Enhanced", "9800X3D", "5060Ti16", "1440p", "Ultra", "DLAA", "4x", 1, 0, 32, 170, 9.0, "b7-fg"),
]


def main():
    conn = db_manager.get_connection()
    cur = conn.cursor()

    # Record the measured allocation alongside each result.
    if "vram_measured_gb" not in {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}:
        cur.execute("ALTER TABLE benchmarks ADD COLUMN vram_measured_gb REAL")
        print("  + benchmarks.vram_measured_gb kolonu eklendi")

    for name, source, _ in NEW_GAMES:
        if cur.execute("SELECT 1 FROM games WHERE name=?", (name,)).fetchone():
            continue
        src = cur.execute("SELECT * FROM games WHERE name=?", (source,)).fetchone()
        if not src:
            print(f"  ! {source} yok, {name} eklenemedi")
            continue
        cols = [d[0] for d in cur.description]
        data = dict(zip(cols, src))
        data.pop("id")
        data["name"] = name
        cur.execute(f"INSERT INTO games ({','.join(data)}) "
                    f"VALUES ({','.join('?' * len(data))})", list(data.values()))
        print(f"  + '{name}' eklendi ('{source}' profilinden turetildi)")

    for game, (lo, hi) in TIER_OVERRIDES.items():
        cur.execute("UPDATE games SET tier_min=?, tier_max=? WHERE name=?", (lo, hi, game))

    added = skipped = 0
    for (game, cpu, gpu, res, preset, up, fg, rt, pt, ram, fps, vram, src) in M:
        cpu_f, gpu_f = CPU[cpu], GPU[gpu]
        missing = [lbl for lbl, tbl, val in
                   (("oyun", "games", game), ("cpu", "cpus", cpu_f), ("gpu", "gpus", gpu_f))
                   if not cur.execute(f"SELECT 1 FROM {tbl} WHERE name=?", (val,)).fetchone()]
        if missing:
            print(f"  ! atlandi ({', '.join(missing)} yok): {game} / {cpu} / {gpu}")
            skipped += 1
            continue
        cur.execute(
            "INSERT OR REPLACE INTO benchmarks (game, cpu, gpu, resolution, settings,"
            " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb, fps_avg,"
            " vram_measured_gb, source, verified) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
            (game, cpu_f, gpu_f, res, preset, up, fg, rt, pt, ram, fps, vram, src))
        added += 1

    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
    conn.close()
    print(f"\n  {added} olcum yuklendi, {skipped} atlandi. Tabloda toplam {total}.")


if __name__ == "__main__":
    main()
