"""
Batch 19 — Hitman's own benchmark, both scenes, at last.

Eleven runs of the game's internal tool on an RTX 3070 with a Ryzen 7 5800X at
1440p: Dubai and Dartmoor, ray tracing on and off, and a full DLSS ladder with
ray tracing on. `scene='benchmark'`, so unlike batches 17 and 18 this reaches
the cost fit — which is the point, because Hitman's 28 existing rows are one
configuration measured 28 times and its `gpu_cost` has never been constrained
by anything (gap 6e).

**What is loaded is the Overall Score, and nothing else from the screen.** The
NVIDIA overlay in the corner also reports FPS and "99% FPS", and it is
tempting to take the second as a 1% low. It is not one. On the Dartmoor runs
the overlay tracks the score closely — 22 against 22.53, 75 against 78.00, 94
against 91.70 — but on the Dubai runs it does not: 123 against 160.30, 41
against 28.32, 87 against 59.24. The explanation is visible in the
screenshots. The overlay is reading whatever is on screen at that moment,
which is the results screen, and Dubai's is a bright sky that renders far
faster than the benchmark it is reporting. Dartmoor's is a dark moor that
happens to render at about the same rate. So every row here carries
fps_1pct_low = NULL, for the same reason batch 15's "Min FPS" did.

**Ray tracing costs 3.46x, and that is now the third independent measurement.**

    Dartmoor  native  78.00 -> 22.53    3.46x   both sides GPU-bound at 99%
    Dubai     native 103.80 -> 28.32    3.67x
    batch 18, RTX 5090, Chongqing, free play      3.25x

A different card, a different scene, and an internal benchmark against free
gameplay, all landing between 3.25x and 3.67x. `RT_GPU_COST_MULT` is 1.70 and
Far Cry 6 measures 1.10x. Whatever else is uncertain, one boolean is not
holding a factor of three any more.

**The upscaling model is right, and the rows that looked like it was wrong
were against the processor.** With ray tracing on, dropping to DLSS Balanced
gives 2.36x in Dubai and 2.31x in Dartmoor, where 0.58 render scale predicts
about 2.2-2.3x. With ray tracing off the same step gives 1.54x and 1.18x. The
difference is not the upscaler; it is that the ray-tracing-off runs have
already hit the chip. That is worth stating plainly because the same shape in
batch 17 — 1080p native 162 against DLSS Quality 168 — was read as a
processor wall on weaker evidence, and this confirms it.

**The two benchmark scenes are not interchangeable: 1.33x apart.** Dubai reads
103.80 native where Dartmoor reads 78.00. Any batch that mixes them without
saying which is fitting one game to two scenes, which is why the prompt asked
and why `benchmarks.location` now records the answer.
That also identifies what the 28 existing rows measured. This video puts the
5800X's Dubai ceiling at roughly 160-170 and its Dartmoor ceiling at 92-95;
Hardware Unboxed measured a 5800X3D at 213. Only Dubai is consistent with
that, so the CPU ladder is Dubai and these Dubai rows sit directly alongside
it.

    python scripts/load_benchmarks_19.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Hitman 3"
CPU = "AMD Ryzen 7 5800X"
GPU = "NVIDIA GeForce RTX 3070"
RAM = 32
SOURCE = "b22-hitman-3070-bench"

# location, upscaling, ray_tracing, Overall Score, GPU utilisation on screen
ROWS = [
    ("Dubai",    "Native",                 0, 103.80, 83),
    ("Dubai",    "DLSS Balanced",          0, 160.30, 62),
    ("Dubai",    "Native",                 1,  28.32, None),
    ("Dubai",    "DLSS Quality",           1,  59.24, 98),
    ("Dubai",    "DLSS Balanced",          1,  66.73, 91),
    ("Dubai",    "DLSS Performance",       1,  74.64, 91),
    ("Dubai",    "DLSS Ultra Performance", 1,  87.13, 65),
    ("Dartmoor", "Native",                 0,  78.00, 99),
    ("Dartmoor", "DLSS Balanced",          0,  91.70, 96),
    ("Dartmoor", "Native",                 1,  22.53, 99),
    ("Dartmoor", "DLSS Balanced",          1,  52.02, 99),
]


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from core import scoring_engine as se

    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for table, name in (("games", GAME), ("cpus", CPU), ("gpus", GPU)):
        if not cur.execute(f"SELECT 1 FROM {table} WHERE name=?", (name,)).fetchone():
            sys.exit(f"  {name} katalogda yok")
    if "location" not in {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}:
        sys.exit("  once: python scripts/migrate_location.py --apply")

    game = {g["name"]: g for g in db_manager.get_all_games()}[GAME]
    cpu = {c["name"]: c for c in db_manager.get_all_cpus()}[CPU]
    gpu = {g["name"]: g for g in db_manager.get_all_gpus()}[GPU]

    print(f"  {GPU} + {CPU}, 1440p, oyunun DAHILI benchmark'i")
    print(f"  {'yer':9s} {'ups':23s} {'RT':>2s} {'skor':>7s} {'GPU%':>5s} "
          f"{'tahmin':>6s} {'hata':>7s}  notlar")
    added = skipped = 0
    for loc, ups, rt, score, util in ROWS:
        d = se.estimate_fps_detailed(cpu, gpu, game, "1440p", "Ultra", ups,
                                     "Kapalı", RAM, ray_tracing=bool(rt))
        codes = [n.get("code") if isinstance(n, dict) else n
                 for n in (d.get("notes") or [])]
        u = f"{util}%" if util else "  ?"
        print(f"  {loc:9s} {ups:23s} {rt:2d} {score:7.2f} {u:>5s} {d['fps']:6d} "
              f"{(d['fps'] - score) / score * 100:+6.1f}%  {codes}")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND"
            " resolution='1440p' AND settings='Ultra' AND upscaling=?"
            " AND ray_tracing=? AND location=?",
            (GAME, CPU, GPU, ups, rt, loc)).fetchone()
        if dup:
            skipped += 1
            continue
        added += 1
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ray_reconstruction,"
                " ram_gb, fps_avg, fps_1pct_low, scene, location, source, verified)"
                " VALUES (?,?,?,'1440p','Ultra',?,'Kapalı',?,0,0,?,?,NULL,"
                "'benchmark',?,?,1)",
                (GAME, CPU, GPU, ups, rt, RAM, score, loc, SOURCE))

    def get(loc, ups, rt):
        return next(s for l, u, r, s, _ in ROWS if l == loc and u == ups and r == rt)

    print()
    print("  ISIN IZLEME MALIYETI")
    for loc in ("Dubai", "Dartmoor"):
        print(f"    {loc:9s} yerli {get(loc, 'Native', 0):6.2f} -> "
              f"{get(loc, 'Native', 1):5.2f} = "
              f"{get(loc, 'Native', 0) / get(loc, 'Native', 1):.2f}x")
    print("    Dartmoor'da iki taraf da GPU %99 -> en temiz olcum 3.46x")
    print("    batch 18 (RTX 5090, Chongqing, serbest oyun): 3.25x")
    print("    kuresel RT_GPU_COST_MULT = 1.70, Far Cry 6 = 1.10x")

    print()
    print("  UPSCALING MODELI DOGRU — yanlis gorunen satirlar CPU'daydi")
    for loc in ("Dubai", "Dartmoor"):
        for rt in (0, 1):
            g = get(loc, "DLSS Balanced", rt) / get(loc, "Native", rt)
            tag = "RT acik  " if rt else "RT kapali"
            print(f"    {loc:9s} {tag} yerli->Balanced = {g:.2f}x")
    print("    0.58 olcek icin beklenen ~2.2-2.3x. RT acikken tam o cikiyor.")

    print()
    print(f"  IKI SAHNE AYNI DEGIL: yerli RT kapali Dubai {get('Dubai','Native',0):.2f}"
          f" / Dartmoor {get('Dartmoor','Native',0):.2f}"
          f" = {get('Dubai','Native',0) / get('Dartmoor','Native',0):.2f}x")
    print("    HUB'in 28 satiri Dubai (CPU tavani oyle diyor).")

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''} — FIT EDILECEK (benchmark)")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  toplam {total} olcum")
        print("  simdi: calibrate_engine.py, validate_engine.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
