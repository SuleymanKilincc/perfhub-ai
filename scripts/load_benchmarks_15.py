"""
Batch 15 — Cyberpunk 2077 on an RTX 3080, from the game's own benchmark screen.

The first batch in this series that is not a video summary. Seven results
screens, photographed directly, which means every setting is legible rather
than reported: preset, upscaler, sharpness, ray-tracing sub-options, and both
frame-generation switches, all confirmed off. That removes the two failure
modes every previous batch had to guard against — frame generation slipping in
unlabelled, and anti-aliasing filed as an upscaler.

It also brings the first RTX 3080 measurement in the set. The card had none.

**What it is not.** The hunt was for one video containing both an internal
benchmark and free gameplay, so the +9.1% gap between them could finally be
corrected instead of only measured. This is seven benchmark runs and no
gameplay, so that gap is exactly where it was. Fifth attempt.

Two things had to be handled before any of it could be loaded.

**"Min FPS" is not a 1% low, and the table proves it.** The results screen
reports Average, Min and Max. Filing that Min as fps_1pct_low would have been
the obvious move and would have been wrong. Across the seven runs Min/Average
is 0.845, tightly held between 0.824 and 0.860. Cyberpunk's measured 1% low
ratio is 0.737. A true minimum frame is by definition at or below the 1st
percentile, so a statistic sitting *above* the 1% low cannot be a minimum
either — it is a third thing, most likely a windowed low. Loading it would
have pulled one of our fifteen measured ratios up by 15% using a quantity that
does not mean what its label says. Every row here carries fps_1pct_low = NULL.

**Ray Reconstruction is on in three of the seven**, and it is on in exactly the
path-traced one. See scripts/migrate_ray_reconstruction.py for why that stops
the batch rather than being noted and ignored: PT_GPU_COST_MULT rests on two
rows, and a third that differs by an unmodelled denoiser would not be measuring
path tracing. Those three load, and are held out of every fit.

What the remaining rows are worth:

  A repeat run. 2:18 and 24:29 are the same configuration measured twice —
  58.67 and 59.30, 1.1% apart. This is the first run-to-run figure this project
  has ever had, and it sets the floor under every error number quoted anywhere
  else: nothing below about 1% is a real difference. The two are loaded as a
  single row at their mean, because two readings of one configuration are one
  measurement, and the UNIQUE constraint says so too.

  A ray-tracing pair at matched render scale. FSR Quality with RT off reads
  92.19; DLSS Quality with RT on reads 58.99. Both upscale from 0.667, so the
  GPU is drawing the same number of pixels and only the ray tracing differs:
  1.563x. That is *below* the global RT_GPU_COST_MULT of 1.70 even though
  these rows use Psycho, the game's heaviest lighting tier — which is the
  signal that the RT-off row is partly held down by the processor rather than
  the card. It is a floor on Psycho's cost, not a measurement of it, and the
  rows are tagged rt_level='Extreme' so they cannot drag the global multiplier
  toward a preset most players never select.

**The preset is "Custom", and Ultra is the reading that fits.** Texture Quality
is High, which is that setting's maximum, and RT Lighting is Psycho, so this is
the ray-tracing preset with the upscaler changed. Scored as Ultra the batch
reads 18.2% mean error; as High, 42.8%. Ultra it is.

**The batch runs +15.5% against the engine, and that is not where it should
be.** Cyberpunk is our best-fitted title at +1.0% across 45 rows, and Ampere as
an architecture reads -4.1%, so neither the game nor the generation explains
it. The three cleanest rows — ray tracing on, Ray Reconstruction off, nowhere
near the processor ceiling — sit at +21%, +23% and +25%, which is a level
error, not a scaling one. Whatever it is, it is specific to this card at this
lighting tier, and the fit is where it gets resolved rather than here.

**The VRAM readings are deliberately not loaded.** The overlay records 8.15 to
9.39 GB against the card's 10.05, which is real data on a card we have none
for, and calibrate_vram.py would happily take it. But the overlay was
photographed on the results screen, after the run, so it can only be at or
below the peak. Feeding a lower bound into the memory fit teaches it that
cards are bigger than they need to be, and that error lands on 8 GB owners.
Kept here instead:

    DLAA 9593   DLSS Q 9613 / 9344   DLSS P 8784
    DLSS UP 8506   DLSS UP + PT 8848   FSR Q 8343     (MB, of 10053)

    python scripts/load_benchmarks_15.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Cyberpunk 2077"
CPU = "AMD Ryzen 9 5950X"
GPU = "NVIDIA GeForce RTX 3080"
RAM = 64
SOURCE = "b17-cp2077-3080"

# The two readings of the repeat configuration, kept for the noise figure.
REPEAT = (58.67, 59.30)

# upscaling, rt, pt, rt_level, ray_recon, avg, min, timestamp
#
# rt_level is 'Extreme' wherever RT Lighting read Psycho — the game's top tier.
# The path-traced row has none: with Path Tracing on, the results screen stops
# listing the RT sub-options entirely, so there is no preset to record.
ROWS = [
    ("DLAA",                   1, 0, "Extreme", 0, 32.88, 27.37, "0:00"),
    ("DLSS Quality",           1, 0, "Extreme", 0, 58.99, 50.37, "2:18 + 24:29"),
    ("DLSS Performance",       1, 0, "Extreme", 1, 75.26, 64.25, "15:49"),
    ("DLSS Ultra Performance", 1, 0, "Extreme", 1, 97.56, 80.42, "14:11"),
    ("DLSS Ultra Performance", 1, 1, None,      1, 81.71, 69.55, "18:59"),
    ("FSR Quality",            0, 0, None,      0, 92.19, 78.22, "22:32"),
]


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for table, name in (("games", GAME), ("cpus", CPU), ("gpus", GPU)):
        if not cur.execute(f"SELECT 1 FROM {table} WHERE name=?", (name,)).fetchone():
            sys.exit(f"  {name} katalogda yok")
    if "ray_reconstruction" not in {r[1] for r in cur.execute("PRAGMA table_info(benchmarks)")}:
        sys.exit("  once: python scripts/migrate_ray_reconstruction.py --apply")

    print(f"  {GPU} + {CPU}, 1440p, oyunun kendi benchmark'i")
    print(f"  {'ups':23s} {'RT':>2s} {'PT':>2s} {'RR':>2s} {'ort':>6s} {'min':>6s} "
          f"{'min/ort':>7s}  kaynak")
    added = skipped = 0
    ratios = []
    for ups, rt, pt, rt_level, rr, avg, mn, ts in ROWS:
        ratios.append(mn / avg)
        print(f"  {ups:23s} {rt:2d} {pt:2d} {rr:2d} {avg:6.2f} {mn:6.2f} "
              f"{mn / avg:7.3f}  {ts}")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=?"
            " AND resolution='1440p' AND settings='Ultra' AND upscaling=?"
            " AND ray_tracing=? AND path_tracing=?",
            (GAME, CPU, GPU, ups, rt, pt)).fetchone()
        if dup:
            skipped += 1
            continue
        added += 1
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, rt_level,"
                " ray_reconstruction, ram_gb, fps_avg, fps_1pct_low, scene,"
                " vram_measured_kind, source, verified)"
                " VALUES (?,?,?,'1440p','Ultra',?,'Kapalı',?,?,?,?,?,?,NULL,"
                "'benchmark','allocated',?,1)",
                (GAME, CPU, GPU, ups, rt, pt, rt_level, rr, RAM, avg,
                 SOURCE + ("-rayrecon" if rr else "")))

    mean = sum(ratios) / len(ratios)
    print()
    print("  min/ort ORANI 1% LOW DEGIL — yuklenmedi")
    print(f"    bu parti      {mean:.3f}  (yayilim {min(ratios):.3f}-{max(ratios):.3f})")
    print(f"    olculmus 1% low orani  0.737")
    print("    gercek minimum, 1. yuzdelige esit ya da ONDAN KUCUK olmak")
    print(f"    zorunda. {mean:.3f} > 0.737 oldugu icin bu sayi minimum da")
    print("    degil, 1% low da degil — ucuncu bir istatistik.")

    a, b = REPEAT
    print()
    print("  TEKRAR KOSUSU (ayni ayar, iki kez olculdu)")
    print(f"    {a} ve {b}  ->  %{abs(b - a) / a * 100:.1f} fark")
    print("    projenin ilk kosudan-kosuya gurultu olcumu. Bunun altindaki")
    print("    hicbir fark gercek degil.")

    rt_on = next(r[5] for r in ROWS if r[0] == "DLSS Quality")
    rt_off = next(r[5] for r in ROWS if r[0] == "FSR Quality")
    print()
    print("  RT PSYCHO MALIYETI (ayni 0.667 olcek, tek fark isin izleme)")
    print(f"    RT kapali {rt_off:6.2f}  /  RT acik {rt_on:6.2f}  =  "
          f"{rt_off / rt_on:.3f}x")
    print(f"    kuresel RT_GPU_COST_MULT 1.70. Psycho en agir kademe oldugu")
    print("    halde daha UCUZ cikiyor — cunku RT kapali satiri islemci")
    print("    tutuyor. Bu bir taban, olcum degil. rt_level='Extreme'.")

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}"
          f"  ({sum(1 for r in ROWS if r[4])} tanesi ray reconstruction — fit disi)")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  toplam {total} olcum")
        print("  simdi: calibrate_engine.py --apply, validate_engine.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
