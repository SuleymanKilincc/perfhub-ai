"""
Hardware database cleanup pass.

Fixes issues found while auditing the CPU/GPU catalog that the web System
Builder reads from:

  1. Duplicate rows for the same card ("RTX 4060" vs "RTX 4060 8GB", …)
  2. Rows whose `vram` column contradicts the name ("RTX 4060 Ti 16GB" with
     vram=8) — this one silently corrupts FPS estimates, because the VRAM
     penalty in scoring_engine reads the column, not the name.
  3. Score inversions (a card scoring above a strictly faster one, e.g.
     GTX 1650 below GTX 1050 Ti, or a laptop part above its desktop twin).
  4. Models that don't exist (RTX 4070 Ti Laptop GPU, Ryzen 7 9700X3D,
     Intel "i9-15900K", RX 7750 XT).
  5. Missing mainstream parts (the whole RDNA1 desktop line, RX 9070 GRE, …).
  6. Workstation/Apple chips carrying productivity-grade scores (up to 110)
     that feed straight into the gaming FPS formula and inflate results.

Idempotent: safe to re-run. Run from the repo root:

    python scripts/fix_hardware_db.py
"""
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager


# ─── GPUs that are duplicates of another row, or don't exist ────────────────
GPU_DELETIONS = [
    # Duplicate: same card already present under its plain name.
    "NVIDIA GeForce RTX 4060 8GB",       # dup of "RTX 4060"        (52 vs 60)
    "NVIDIA GeForce RTX 4070 12GB",      # dup of "RTX 4070"        (73 vs 77)
    # Superseded by explicit 8GB/16GB variants added below.
    "NVIDIA GeForce RTX 4060 Ti",
    "NVIDIA GeForce RTX 5060 Ti",
    "AMD Radeon RX 9060 XT",
    # Not real products.
    "NVIDIA GeForce RTX 4070 Ti Laptop GPU",  # Ada laptop line is 4050-4090
    "AMD Radeon RX 7750 XT",
]

CPU_DELETIONS = [
    "AMD Ryzen 7 9700X3D",   # Zen 5 X3D line is 9800X3D / 9900X3D / 9950X3D
    "Intel Core i5-15600K",  # Arrow Lake desktop is branded "Core Ultra 2xxK"
    "Intel Core i7-15700K",
    "Intel Core i9-15900K",
]

# ─── GPUs to insert or correct ─────────────────────────────────────────────
# (name, vram, core_clock, memory_clock, architecture, power_score)
GPU_UPSERTS = [
    # VRAM variants kept separate: identical silicon, but the capacity really
    # does change 4K/Ultra behaviour through the VRAM penalty.
    ("NVIDIA GeForce RTX 4060 Ti 8GB",  8,  2535, 2250, "Ada Lovelace", 60.0),
    ("NVIDIA GeForce RTX 4060 Ti 16GB", 16, 2535, 2250, "Ada Lovelace", 62.0),
    ("NVIDIA GeForce RTX 5060 Ti 8GB",  8,  2572, 3500, "Blackwell",    70.0),
    ("NVIDIA GeForce RTX 5060 Ti 16GB", 16, 2572, 3500, "Blackwell",    72.0),
    ("AMD Radeon RX 9060 XT 8GB",       8,  3130, 2518, "RDNA 4",       73.0),
    ("AMD Radeon RX 9060 XT 16GB",      16, 3130, 2518, "RDNA 4",       75.0),

    # vram column contradicted the real card.
    ("AMD Radeon RX 7600 XT",           16, 2755, 2250, "RDNA 3",       53.0),

    # Missing: the entire RDNA1 desktop line (only the mobile parts existed).
    ("AMD Radeon RX 5700 XT",           8,  1905, 1750, "RDNA",         47.0),
    ("AMD Radeon RX 5700",              8,  1725, 1750, "RDNA",         43.0),
    ("AMD Radeon RX 5600 XT",           6,  1560, 1500, "RDNA",         39.0),
    ("AMD Radeon RX 5500 XT",           8,  1845, 1750, "RDNA",         33.0),

    # Other missing mainstream parts.
    ("AMD Radeon RX 9070 GRE",          12, 2790, 2518, "RDNA 4",       80.0),
    ("NVIDIA GeForce RTX 3080 12GB",    12, 1710, 1188, "Ampere",       72.0),
    ("NVIDIA GeForce GTX 1630",         4,  1785, 1500, "Turing",       16.0),

    # Score corrections — GTX 1650 sat below the much slower 1050 Ti (26) and
    # below its own laptop variant (28).
    ("NVIDIA GeForce GTX 1650",         4,  1665, 2000, "Turing",       30.0),
    ("NVIDIA GeForce GTX 1650 Laptop GPU", 4, 1560, 2000, "Turing",     26.0),

    # Kepler parts were rated near Pascal/Turing midrange; a 780 Ti lands
    # around GTX 1060 6GB (36), not GTX 1070 (42).
    ("NVIDIA GeForce GTX 780 Ti",       3,  1020, 1750, "Kepler",       34.0),
    ("NVIDIA GeForce GTX 780",          3,  900,  1502, "Kepler",       31.0),
    ("NVIDIA GeForce GTX 770",          2,  1085, 1753, "Kepler",       27.0),
    ("NVIDIA GeForce GTX 760",          2,  1033, 1502, "Kepler",       24.0),

    # Mobile part outscored its desktop twin.
    ("Intel Arc A770M",                 16, 1650, 2187, "Alchemist",    49.0),

    # Duplicate removed above; keep the survivor on a sane rung between
    # RTX 3060 Ti (55) and RTX 4060 Ti 8GB (60).
    ("NVIDIA GeForce RTX 4060",         8,  2460, 2125, "Ada Lovelace", 54.0),
]

# ─── CPU score corrections ─────────────────────────────────────────────────
# These chips stay in the catalog, but their scores now reflect *gaming*
# throughput rather than all-core productivity. A 96-core Threadripper is
# slower than a 9800X3D in games; at 110 it produced nonsense FPS numbers,
# since power_score feeds estimate_fps() directly.
CPU_SCORE_FIXES = {
    # Threadripper: fewer cores / higher clocks game better, hence inverted.
    "AMD Ryzen Threadripper PRO 7995WX": 80.0,   # was 110
    "AMD Ryzen Threadripper PRO 7985WX": 81.0,   # was 108
    "AMD Ryzen Threadripper 7980X":      82.0,   # was 106
    "AMD Ryzen Threadripper PRO 7975WX": 83.0,   # was 105
    "AMD Ryzen Threadripper 7970X":      84.0,   # was 103
    "AMD Ryzen Threadripper 7960X":      85.0,   # was 100
    # Xeon W: workstation clocks, weak gaming.
    "Intel Xeon W9-3495X":               76.0,   # was 102
    "Intel Xeon W9-3475X":               77.0,   # was 98
    "Intel Xeon W7-3465X":               79.0,   # was 94
    # Apple Silicon: excellent chips, but Windows titles only run translated,
    # so productivity-grade scores badly overstate game performance.
    "Apple M5 Max":  82.0,   # was 105
    "Apple M5 Pro":  78.0,   # was 95
    "Apple M5":      74.0,   # was 85
    "Apple M4 Max":  80.0,   # was 100
    "Apple M4 Pro":  76.0,   # was 90
    "Apple M4":      72.0,   # was 80
    "Apple M3 Max":  76.0,   # was 92
    "Apple M3 Pro":  71.0,   # was 82
    "Apple M3":      68.0,   # was 72
    "Apple M2 Ultra": 78.0,  # was 98
    "Apple M2 Max":  72.0,   # was 85
    "Apple M2 Pro":  68.0,   # was 75
    "Apple M2":      63.0,   # was 65
    "Apple M1 Ultra": 72.0,  # was 88
    "Apple M1 Max":  68.0,   # was 78
    "Apple M1 Pro":  64.0,   # was 68
}


def _upsert_gpu(cursor, name, vram, core_clock, memory_clock, arch, score):
    """Insert the GPU, or overwrite its specs if the row already exists."""
    cursor.execute("SELECT id FROM gpus WHERE name = ?", (name,))
    if cursor.fetchone():
        cursor.execute(
            "UPDATE gpus SET vram=?, core_clock=?, memory_clock=?, "
            "architecture=?, power_score=? WHERE name=?",
            (vram, core_clock, memory_clock, arch, score, name),
        )
        return "updated"
    cursor.execute(
        "INSERT INTO gpus (name, vram, core_clock, memory_clock, architecture, "
        "power_score) VALUES (?, ?, ?, ?, ?, ?)",
        (name, vram, core_clock, memory_clock, arch, score),
    )
    return "inserted"


def main():
    conn = db_manager.get_connection()
    cursor = conn.cursor()

    deleted = updated = inserted = 0

    for name in GPU_DELETIONS:
        cursor.execute("DELETE FROM gpus WHERE name = ?", (name,))
        if cursor.rowcount:
            deleted += cursor.rowcount
            print(f"  - GPU silindi : {name}")

    for name in CPU_DELETIONS:
        cursor.execute("DELETE FROM cpus WHERE name = ?", (name,))
        if cursor.rowcount:
            deleted += cursor.rowcount
            print(f"  - CPU silindi : {name}")

    for row in GPU_UPSERTS:
        action = _upsert_gpu(cursor, *row)
        if action == "inserted":
            inserted += 1
            print(f"  + GPU eklendi : {row[0]}  ({row[1]}GB, {row[5]})")
        else:
            updated += 1
            print(f"  ~ GPU guncel. : {row[0]}  ({row[1]}GB, {row[5]})")

    for name, score in CPU_SCORE_FIXES.items():
        cursor.execute(
            "UPDATE cpus SET power_score = ? WHERE name = ? AND power_score != ?",
            (score, name, score),
        )
        if cursor.rowcount:
            updated += cursor.rowcount
            print(f"  ~ CPU puani   : {name} -> {score}")

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM cpus")
    cpu_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM gpus")
    gpu_count = cursor.fetchone()[0]
    conn.close()

    print(
        f"\nOzet: {deleted} silindi, {inserted} eklendi, {updated} guncellendi."
        f"\nToplam: {cpu_count} CPU, {gpu_count} GPU."
    )


if __name__ == "__main__":
    main()
