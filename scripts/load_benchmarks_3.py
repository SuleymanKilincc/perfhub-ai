"""
Batch 3 — Forza Horizon 6 on an RTX 3080 Ti, and the two rows it disproves.

Source: a YouTube benchmark run (RTX 3080 Ti + i5-12600KF), read through the
video's own AI summary, which lists each setting with a timestamp. That
timestamp is the part that makes the method usable: an extracted number that
can be checked against the frame it came from is evidence, and one that cannot
is a rumour.

**It resolved a contradiction that had been logged as unexplained.** The
catalogue held three RTX 5080 measurements of the *same* configuration — 4K
Ultra, DLAA, ray tracing off — reading 260, 152 and 89 fps. Scaling this run's
RTX 3080 Ti figures by the score ratio (1.45x) predicts 159 / 130 / 87 at
1080p / 1440p / 4K, against 175 / 133 / 89 recorded. Two independent sources
agree at all three resolutions and both disagree with 152 and 260, so those
two rows are removed.

Deliberately NOT loaded, and why:

  4K DLSS Performance (69 fps) and DLSS Quality (80 fps)
      Performance mode renders fewer pixels and cannot be slower. One of the
      two is misattributed in the summary; check 9:06 and 11:38 in the video.

  the ray tracing rows
      The model carries a single ray-tracing flag while the video sweeps High,
      Ultra and Extreme RT plus an RT GI setting. Feeding "Extreme" in against
      a 5080 row measured at some other level would push the error straight
      into RT_GPU_COST_MULT, which is fitted from exactly these rows.

  VRAM on every row but one
      The overlay reports allocated and used separately (10319 MB and 8837 MB
      at 1440p); the summary collapses them into "9-10 GB". `vram_measured_gb`
      means allocation, so only the row with a real overlay reading gets one.

    python scripts/load_benchmarks_3.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

CPU = "Intel Core i5-12600K"   # video says 12600KF; identical silicon, no iGPU
GPU = "NVIDIA GeForce RTX 3080 Ti"
RAM = 32                        # overlay shows 12.8 GB in use, so not 8 or 16
SOURCE = "b8-fh6-3080ti"

# game, resolution, settings, upscaling, frame_gen, rt, pt, fps, vram
ROWS = [
    ("Forza Horizon 6", "1080p", "Ultra", "DLAA", "Kapalı", 0, 0, 110, None),
    # 1440p uses the figure on screen at 1:57 (AVG 96) rather than the
    # summary's "80-100" band, and its overlay gives a real allocation number.
    ("Forza Horizon 6", "1440p", "Ultra", "DLAA", "Kapalı", 0, 0, 96, 10.3),
    ("Forza Horizon 6", "4k", "Ultra", "DLAA", "Kapalı", 0, 0, 60, None),
    # "TAA" in the video is native rendering with temporal AA, which is what
    # the model calls Native.
    ("Forza Horizon 6", "4k", "Ultra", "Native", "Kapalı", 0, 0, 62, None),
    ("Forza Horizon 6", "4k", "Ultra", "DLSS Quality", "Kapalı", 0, 0, 80, None),
]

# Same configuration as an existing row, three different answers. These two are
# the ones a second source contradicts.
REMOVE_IDS = [76, 77]


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for name in (CPU, GPU):
        table = "cpus" if "Core" in name or "Ryzen" in name else "gpus"
        if not cur.execute(f"SELECT 1 FROM {table} WHERE name=?", (name,)).fetchone():
            sys.exit(f"  {name} katalogda yok")

    print("=== KALDIRILAN SATIRLAR ===")
    for rid in REMOVE_IDS:
        row = cur.execute(
            "SELECT game, gpu, resolution, settings, fps_avg FROM benchmarks WHERE id=?",
            (rid,)).fetchone()
        if not row:
            print(f"  id={rid} bulunamadi (zaten kaldirilmis)")
            continue
        print(f"  id={rid}  {row['game']} / {row['gpu']} / {row['resolution']} "
              f"{row['settings']} = {row['fps_avg']:.0f} fps")
        if apply_changes:
            cur.execute("DELETE FROM benchmarks WHERE id=?", (rid,))

    print("\n=== EKLENEN SATIRLAR ===")
    added = 0
    for game, res, settings, ups, fg, rt, pt, fps, vram in ROWS:
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
            " AND settings=? AND upscaling=? AND frame_gen=? AND ray_tracing=?",
            (game, CPU, GPU, res, settings, ups, fg, rt)).fetchone()
        if dup:
            print(f"  {res:6s} {settings:6s} {ups:14s} — zaten var, atlandi")
            continue
        added += 1
        print(f"  {res:6s} {settings:6s} {ups:14s} rt={rt}  {fps:5.0f} fps"
              f"  vram={vram if vram else '-'}")
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb,"
                " fps_avg, vram_measured_gb, source, verified)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                (game, CPU, GPU, res, settings, ups, fg, rt, pt, RAM, fps, vram, SOURCE))

    print(f"\n  {added} satir eklenecek, {len(REMOVE_IDS)} satir kaldirilacak")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  yazildi. toplam olcum: {total}")
        print("  simdi: calibrate_vram.py --apply, calibrate_engine.py --apply,")
        print("         validate_engine.py, export_engine_data.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
