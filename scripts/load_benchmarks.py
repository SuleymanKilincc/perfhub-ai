"""
Loads the measured benchmark set into the `benchmarks` table.

These are real figures collected from published benchmark videos, not
estimates. Each row records the exact configuration it was measured at, so
scripts/validate_engine.py can compare the engine against it.

Also performs two prerequisites:

  * Removes the duplicate "CS:GO 2" row. Counter-Strike 2 exists under both
    names with different derived profiles (2.2 GB vs 3.0 GB of VRAM), which
    would let the same game validate against two different predictions.
  * Adds The Last of Us Part II and Forza Horizon 6, which the preset-ladder
    measurements use. Their cost profiles are cloned from their predecessors
    (Part I and Horizon 5) — same studio, same engine generation — and are
    starting points to be corrected by calibration like every other profile.

Run from the repo root:  python scripts/load_benchmarks.py
"""
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

# Names as written in the source notes -> names in the database.
GPU_ALIASES = {
    "RTX 4090": "NVIDIA GeForce RTX 4090",
    "RTX 4070": "NVIDIA GeForce RTX 4070",
    "RTX 3060 Ti": "NVIDIA GeForce RTX 3060 Ti",
    "RX 7800 XT": "AMD Radeon RX 7800 XT",
    "RX 9060 XT 16GB": "AMD Radeon RX 9060 XT 16GB",
    "RTX 5070 Ti": "NVIDIA GeForce RTX 5070 Ti",
    "RTX 4060": "NVIDIA GeForce RTX 4060",
    "RTX 2060": "NVIDIA GeForce RTX 2060",
    "RTX 4060 Ti 8GB": "NVIDIA GeForce RTX 4060 Ti 8GB",
    "RTX 4060 Ti 16GB": "NVIDIA GeForce RTX 4060 Ti 16GB",
}
CPU_ALIASES = {
    "7800X3D": "AMD Ryzen 7 7800X3D",
    "7950X3D": "AMD Ryzen 9 7950X3D",
    "7700": "AMD Ryzen 7 7700",
    "i5-14600K": "Intel Core i5-14600K",
    # 14700KF is the 14700K without the integrated GPU — identical for gaming.
    "i7-14700KF": "Intel Core i7-14700K",
    "5700X": "AMD Ryzen 7 5700X",
    "i7-13700": "Intel Core i7-13700",
}

# (game, cpu, gpu, res, preset, upscaling, framegen, rt, pt, ram, fps, source)
MEASUREMENTS = [
    # ── Batch 1: resolution sweep, 7800X3D + RTX 4090, Ultra, native, no RT ──
    ("Cyberpunk 2077", "7800X3D", "RTX 4090", "1080p", "Ultra", "Native", "Kapalı", 0, 0, 32, 140, "batch1"),
    ("Cyberpunk 2077", "7800X3D", "RTX 4090", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 125, "batch1"),
    ("Cyberpunk 2077", "7800X3D", "RTX 4090", "4k", "Ultra", "Native", "Kapalı", 0, 0, 32, 60, "batch1"),
    ("Counter-Strike 2", "7800X3D", "RTX 4090", "1080p", "Ultra", "Native", "Kapalı", 0, 0, 32, 515, "batch1"),
    ("Counter-Strike 2", "7800X3D", "RTX 4090", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 390, "batch1"),
    ("Counter-Strike 2", "7800X3D", "RTX 4090", "4k", "Ultra", "Native", "Kapalı", 0, 0, 32, 205, "batch1"),
    # CS2 also measured at Low — a CPU-bound game's preset ladder is the
    # clearest test of whether the quality tiers flatten correctly.
    ("Counter-Strike 2", "7800X3D", "RTX 4090", "1080p", "Low", "Native", "Kapalı", 0, 0, 32, 780, "batch1"),
    ("Counter-Strike 2", "7800X3D", "RTX 4090", "1440p", "Low", "Native", "Kapalı", 0, 0, 32, 770, "batch1"),
    ("Counter-Strike 2", "7800X3D", "RTX 4090", "4k", "Low", "Native", "Kapalı", 0, 0, 32, 590, "batch1"),
    ("Red Dead Redemption 2", "7800X3D", "RTX 4090", "1080p", "Ultra", "Native", "Kapalı", 0, 0, 32, 190, "batch1"),
    ("Red Dead Redemption 2", "7800X3D", "RTX 4090", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 160, "batch1"),
    ("Red Dead Redemption 2", "7800X3D", "RTX 4090", "4k", "Ultra", "Native", "Kapalı", 0, 0, 32, 120, "batch1"),
    # Note from the source: CPU-limited at 1080p and 1440p (GPU at 70% / 80%).
    ("Hogwarts Legacy", "7800X3D", "RTX 4090", "1080p", "Ultra", "Native", "Kapalı", 0, 0, 32, 150, "batch1"),
    ("Hogwarts Legacy", "7800X3D", "RTX 4090", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 140, "batch1"),
    ("Hogwarts Legacy", "7800X3D", "RTX 4090", "4k", "Ultra", "Native", "Kapalı", 0, 0, 32, 85, "batch1"),
    ("Baldur's Gate 3", "7800X3D", "RTX 4090", "1080p", "Ultra", "Native", "Kapalı", 0, 0, 32, 260, "batch1"),
    ("Baldur's Gate 3", "7800X3D", "RTX 4090", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 200, "batch1"),
    ("Baldur's Gate 3", "7800X3D", "RTX 4090", "4k", "Ultra", "Native", "Kapalı", 0, 0, 32, 140, "batch1"),

    # ── Batch 2: GPU ladder, 7800X3D, Cyberpunk 1440p Ultra native ──────────
    ("Cyberpunk 2077", "7800X3D", "RTX 4070", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 52, "batch2"),
    ("Cyberpunk 2077", "7800X3D", "RTX 3060 Ti", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 45, "batch2"),
    ("Cyberpunk 2077", "7800X3D", "RX 7800 XT", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 80, "batch2"),
    ("Cyberpunk 2077", "7800X3D", "RX 9060 XT 16GB", "1440p", "Ultra", "Native", "Kapalı", 0, 0, 32, 67, "batch2"),

    # ── Batch 3: CPU ladder, RTX 5070 Ti, CS2 1080p High native ─────────────
    ("Counter-Strike 2", "7800X3D", "RTX 5070 Ti", "1080p", "High", "Native", "Kapalı", 0, 0, 32, 604, "batch3"),
    ("Counter-Strike 2", "7700", "RTX 5070 Ti", "1080p", "High", "Native", "Kapalı", 0, 0, 32, 551, "batch3"),
    ("Counter-Strike 2", "i5-14600K", "RTX 5070 Ti", "1080p", "High", "Native", "Kapalı", 0, 0, 32, 532, "batch3"),
    ("Counter-Strike 2", "i7-14700KF", "RTX 5070 Ti", "1080p", "High", "Native", "Kapalı", 0, 0, 32, 577, "batch3"),

    # ── Batch 4: preset ladders (DLAA = native resolution + AI AA) ──────────
    ("The Last of Us Part II", "5700X", "RTX 4060", "1080p", "Very Low", "DLAA", "Kapalı", 0, 0, 16, 106, "batch4"),
    ("The Last of Us Part II", "5700X", "RTX 4060", "1080p", "Low", "DLAA", "Kapalı", 0, 0, 16, 100, "batch4"),
    ("The Last of Us Part II", "5700X", "RTX 4060", "1080p", "Medium", "DLAA", "Kapalı", 0, 0, 16, 96, "batch4"),
    ("The Last of Us Part II", "5700X", "RTX 4060", "1080p", "High", "DLAA", "Kapalı", 0, 0, 16, 92, "batch4"),
    ("The Last of Us Part II", "5700X", "RTX 4060", "1080p", "Ultra", "DLAA", "Kapalı", 0, 0, 16, 65, "batch4"),
    ("Forza Horizon 6", "i7-13700", "RTX 2060", "1080p", "Very Low", "DLAA", "Kapalı", 0, 0, 16, 94, "batch4"),
    ("Forza Horizon 6", "i7-13700", "RTX 2060", "1080p", "Low", "DLAA", "Kapalı", 0, 0, 16, 80, "batch4"),
    ("Forza Horizon 6", "i7-13700", "RTX 2060", "1080p", "Medium", "DLAA", "Kapalı", 0, 0, 16, 71, "batch4"),
    ("Forza Horizon 6", "i7-13700", "RTX 2060", "1080p", "High", "DLAA", "Kapalı", 0, 0, 16, 62, "batch4"),
    ("Forza Horizon 6", "i7-13700", "RTX 2060", "1080p", "Ultra", "DLAA", "Kapalı", 0, 0, 16, 40, "batch4"),
    ("Forza Horizon 6", "i7-13700", "RTX 2060", "1080p", "Extreme", "DLAA", "Kapalı", 0, 0, 16, 33, "batch4"),

    # ── Batch 5: RT / PT / upscaling / frame gen, 4090 + 7950X3D, CP2077 4K ─
    ("Cyberpunk 2077", "7950X3D", "RTX 4090", "4k", "Ultra", "Native", "Kapalı", 0, 0, 32, 65, "batch5"),
    ("Cyberpunk 2077", "7950X3D", "RTX 4090", "4k", "Ultra", "Native", "Kapalı", 1, 0, 32, 40, "batch5"),
    ("Cyberpunk 2077", "7950X3D", "RTX 4090", "4k", "Ultra", "Native", "Kapalı", 1, 1, 32, 20, "batch5"),
    ("Cyberpunk 2077", "7950X3D", "RTX 4090", "4k", "Ultra", "DLSS Quality", "Kapalı", 0, 0, 32, 90, "batch5"),
    ("Cyberpunk 2077", "7950X3D", "RTX 4090", "4k", "Ultra", "DLSS Performance", "Kapalı", 0, 0, 32, 125, "batch5"),
    ("Cyberpunk 2077", "7950X3D", "RTX 4090", "4k", "Ultra", "Native", "2x", 0, 0, 32, 97, "batch5"),
    ("Cyberpunk 2077", "7950X3D", "RTX 4090", "4k", "Ultra", "DLSS Quality", "2x", 0, 0, 32, 123, "batch5"),
    # Ray Reconstruction is not modelled separately; recorded as RT + DLSS Q.
    ("Cyberpunk 2077", "7950X3D", "RTX 4090", "4k", "Ultra", "DLSS Quality", "Kapalı", 1, 0, 32, 103, "batch5-rayrecon"),

    # ── Batch 6: VRAM capacity, same chip 8GB vs 16GB, 1440p Ultra DLAA ─────
    # Far Cry 6's HD texture pack is not a separate flag in the model.
    ("Far Cry 6", "7800X3D", "RTX 4060 Ti 8GB", "1440p", "Ultra", "DLAA", "Kapalı", 1, 0, 32, 28, "batch6-hdtex"),
    ("Far Cry 6", "7800X3D", "RTX 4060 Ti 16GB", "1440p", "Ultra", "DLAA", "Kapalı", 1, 0, 32, 73, "batch6-hdtex"),
    ("The Last of Us Part I", "7800X3D", "RTX 4060 Ti 8GB", "1440p", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 40, "batch6"),
    ("The Last of Us Part I", "7800X3D", "RTX 4060 Ti 16GB", "1440p", "Ultra", "DLAA", "Kapalı", 0, 0, 32, 53, "batch6"),
    ("Hogwarts Legacy", "7800X3D", "RTX 4060 Ti 8GB", "1440p", "Ultra", "DLAA", "2x", 1, 0, 32, 53, "batch6"),
    ("Hogwarts Legacy", "7800X3D", "RTX 4060 Ti 16GB", "1440p", "Ultra", "DLAA", "2x", 1, 0, 32, 56, "batch6"),
    ("Forza Horizon 5", "7800X3D", "RTX 4060 Ti 8GB", "1440p", "Ultra", "DLAA", "2x", 1, 0, 32, 73, "batch6"),
    ("Forza Horizon 5", "7800X3D", "RTX 4060 Ti 16GB", "1440p", "Ultra", "DLAA", "2x", 1, 0, 32, 100, "batch6"),
    ("A Plague Tale: Requiem", "7800X3D", "RTX 4060 Ti 8GB", "1440p", "Ultra", "DLAA", "2x", 1, 0, 32, 34, "batch6"),
    ("A Plague Tale: Requiem", "7800X3D", "RTX 4060 Ti 16GB", "1440p", "Ultra", "DLAA", "2x", 1, 0, 32, 68, "batch6"),
]

# Games the measurements reference that the catalog lacks, cloned from the
# closest sibling title (same studio and engine generation).
CLONE_GAMES = [
    ("The Last of Us Part II", "The Last of Us Part I"),
    ("Forza Horizon 6", "Forza Horizon 5"),
]


def _dedupe_counter_strike(cursor):
    """Counter-Strike 2 exists twice, under two names, with different profiles."""
    rows = {r[0] for r in cursor.execute(
        "SELECT name FROM games WHERE name IN ('CS:GO 2','Counter-Strike 2')")}
    if {"CS:GO 2", "Counter-Strike 2"} <= rows:
        # Keep the correct product name; carry over the wider preset range the
        # duplicate had recorded.
        cursor.execute(
            "UPDATE games SET tier_min = (SELECT tier_min FROM games WHERE name='CS:GO 2') "
            "WHERE name='Counter-Strike 2'")
        cursor.execute("DELETE FROM games WHERE name='CS:GO 2'")
        print("  - 'CS:GO 2' kopyasi silindi (Counter-Strike 2 korundu)")


def _clone_games(cursor):
    for new_name, source_name in CLONE_GAMES:
        if cursor.execute("SELECT 1 FROM games WHERE name=?", (new_name,)).fetchone():
            continue
        src = cursor.execute("SELECT * FROM games WHERE name=?", (source_name,)).fetchone()
        if not src:
            print(f"  ! {source_name} bulunamadi, {new_name} eklenemedi")
            continue
        cols = [d[0] for d in cursor.description]
        data = dict(zip(cols, src))
        data.pop("id")
        data["name"] = new_name
        placeholders = ",".join("?" * len(data))
        cursor.execute(
            f"INSERT INTO games ({','.join(data)}) VALUES ({placeholders})",
            list(data.values()))
        print(f"  + '{new_name}' eklendi ('{source_name}' profilinden turetildi)")


def main():
    conn = db_manager.get_connection()
    cursor = conn.cursor()

    _dedupe_counter_strike(cursor)
    _clone_games(cursor)
    conn.commit()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS benchmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game TEXT NOT NULL, cpu TEXT NOT NULL, gpu TEXT NOT NULL,
            resolution TEXT NOT NULL, settings TEXT NOT NULL,
            upscaling TEXT DEFAULT 'Native', frame_gen TEXT DEFAULT 'Kapalı',
            ray_tracing INTEGER DEFAULT 0, path_tracing INTEGER DEFAULT 0,
            ram_gb INTEGER DEFAULT 32, fps_avg REAL NOT NULL,
            source TEXT, verified INTEGER DEFAULT 0,
            UNIQUE(game, cpu, gpu, resolution, settings, upscaling, frame_gen,
                   ray_tracing, path_tracing))
    """)
    # Drop the earlier placeholder rows — they were guesses, and mixing them
    # with real measurements would corrupt the error figure.
    cursor.execute("DELETE FROM benchmarks WHERE source = 'placeholder'")

    added = skipped = 0
    for (game, cpu, gpu, res, preset, up, fg, rt, pt, ram, fps, src) in MEASUREMENTS:
        cpu_full = CPU_ALIASES.get(cpu, cpu)
        gpu_full = GPU_ALIASES.get(gpu, gpu)
        missing = [
            label for label, table, value in
            (("oyun", "games", game), ("cpu", "cpus", cpu_full), ("gpu", "gpus", gpu_full))
            if not cursor.execute(f"SELECT 1 FROM {table} WHERE name=?", (value,)).fetchone()
        ]
        if missing:
            print(f"  ! atlandi ({', '.join(missing)} yok): {game} / {cpu} / {gpu}")
            skipped += 1
            continue
        cursor.execute(
            "INSERT OR REPLACE INTO benchmarks (game, cpu, gpu, resolution, settings,"
            " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb, fps_avg,"
            " source, verified) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)",
            (game, cpu_full, gpu_full, res, preset, up, fg, rt, pt, ram, fps, src))
        added += 1

    conn.commit()
    total = cursor.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
    conn.close()
    print(f"\n  {added} olcum yuklendi, {skipped} atlandi. Tabloda toplam {total}.")


if __name__ == "__main__":
    main()
