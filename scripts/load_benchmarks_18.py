"""
Batch 18 — Hitman's ray tracing on an RTX 5090, measured on and off in the
same place, and what that says about a model with one boolean for it.

Five rows from a ray-tracing comparison video: 4K native, max settings,
RTX 5090 with a 9800X3D. Three locations with ray tracing on, two of them
also with it off at otherwise identical settings. Gameplay, so nothing here
reaches the cost fit.

**Ray tracing costs 3.25x in this game.** Chongqing has both sides and both
are GPU-bound — 99% with it on, 96% with it off — so the pair measures the
card and nothing else:

    Chongqing   72 -> 234     3.25x

Against a global RT_GPU_COST_MULT of 1.70, and against Far Cry 6's measured
1.10x. The spread across games is now a factor of three, from titles whose
ray tracing is reflections and shadows to a title whose ray tracing is also
reflections and shadows. One boolean cannot hold that, which is gap 6b, and
this is the measurement that makes it hard to keep deferring.

**Sapienza reads 5.79x, and the difference from Chongqing is the processor.**
Same settings, same machine. The distinguishing number is not the frame rate
but GPU utilisation: 61% with ray tracing on, against 96% with it off. The
card is idle a third of the time, so something else is setting the pace — ray
tracing in this engine has a CPU cost that the model expresses as a flat
RT_CPU_COST_MULT of 1.08 and that is plainly larger here. Chongqing is
therefore the honest GPU figure and Sapienza is the GPU figure plus a wall.

**The scene sensitivity belongs to the ray tracing, not to the game.** This is
the part worth keeping. With ray tracing on, the three locations spread 1.67x:

    Sapienza 43     Miami 70     Chongqing 72

With it off, the two measured locations agree to within 6%:

    Sapienza 249    Chongqing 234

Every previous location finding in this project — Saint Denis against the
countryside, New Atlantis against a planet, Act 1 against Act 3 — asked
whether a game's cost is one number, and got mixed answers. This says the
question was aimed slightly wrong. Base rendering is steady across a game's
areas; it is the ray tracing that is not, because what it costs depends on
what is in front of the player. That is a mechanism rather than an
observation, and it predicts where to look next.

**Hitman's GPU cost is roughly twice what it should be, and this is the second
card to say so.** The engine reads -52.6% and -49.6% on the two ray-tracing-off
rows: 118 predicted against 249 and 234 measured. The RTX 5060 batch said the
same at lower resolutions. The inference is safe in a way it usually is not,
because these are gameplay rows and batch 16 measured gameplay as running
*below* a benchmark loop — so the true benchmark figure is higher still, and
the error can only be larger than it looks.
It is not corrected here. Fitting a cost to held-out gameplay is the discipline
this project has kept from the start, and one video does not buy an exception.
What it does buy is a precise ask: Hitman's *internal* benchmark, Dubai or
Dartmoor, at 1440p or 4K, on any card. That single video fixes it properly.

VRAM is recorded in the overlay as one unlabelled number — 9701, 7508, 9899,
9068 and 8390 MB — and is deliberately not loaded. The batch 17 rows for this
same game carry a labelled DEDICATED reading loaded as `used`, and mixing an
unlabelled figure into a fit whose whole job is to know which kind it is
would undo that. calibrate_vram.py's own docstring says the confusion lands
about 25% out.

    python scripts/load_benchmarks_18.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Hitman 3"
CPU = "AMD Ryzen 7 9800X3D"
GPU = "NVIDIA GeForce RTX 5090"
RAM = 64
SOURCE = "b21-hitman-5090-rt"

# location, ray_tracing, avg, 1% low, GPU utilisation, unloaded VRAM reading MB
ROWS = [
    ("Sapienza",  1,  43,  30, 61, 9701),
    ("Sapienza",  0, 249, 206, 96, 7508),
    ("Miami",     1,  70,  61, 99, 9899),
    ("Chongqing", 1,  72,  60, 99, 9068),
    ("Chongqing", 0, 234, 186, 96, 8390),
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

    print(f"  {GPU} + {CPU}, 4K yerli, max ayar, serbest oyun")
    print(f"  {'yer':10s} {'RT':>2s} {'ort':>4s} {'low':>4s} {'oran':>6s} "
          f"{'GPU%':>5s} {'tahmin':>6s} {'hata':>7s}")
    added = skipped = 0
    for loc, rt, avg, low, util, _vram in ROWS:
        p = se.estimate_fps(cpu, gpu, game, "4k", "Ultra", "Native", "Kapalı", RAM,
                            ray_tracing=bool(rt))
        print(f"  {loc:10s} {rt:2d} {avg:4d} {low:4d} {low / avg:6.3f} {util:4d}% "
              f"{p:6d} {(p - avg) / avg * 100:+6.1f}%")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND"
            " resolution='4k' AND settings='Ultra' AND upscaling='Native'"
            " AND ray_tracing=? AND location=?",
            (GAME, CPU, GPU, rt, loc)).fetchone()
        if dup:
            skipped += 1
            continue
        added += 1
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ray_reconstruction,"
                " ram_gb, fps_avg, fps_1pct_low, scene, location, source, verified)"
                " VALUES (?,?,?,'4k','Ultra','Native','Kapalı',?,0,0,?,?,?,"
                "'gameplay',?,?,1)",
                (GAME, CPU, GPU, rt, RAM, avg, low, loc, SOURCE))

    on = {loc: avg for loc, rt, avg, *_ in ROWS if rt}
    off = {loc: avg for loc, rt, avg, *_ in ROWS if not rt}
    print()
    print("  AYNI YERDE RT ACIK / KAPALI")
    for loc in off:
        print(f"    {loc:10s} {on[loc]:3d} -> {off[loc]:3d} = {off[loc] / on[loc]:.2f}x")
    print("    Chongqing iki tarafta da GPU-bound (%99 / %96) -> temiz olcum.")
    print("    Sapienza'da RT acikken GPU sadece %61 -> orada islemci tutuyor,")
    print("    5.79x'in farki kartin degil cipin.")
    print(f"    kuresel RT_GPU_COST_MULT = 1.70,  Far Cry 6 olculen 1.10x")

    print()
    print("  KONUMA DUYARLILIK ISIN IZLEMEYE AIT, OYUNA DEGIL")
    print(f"    RT acik : {' / '.join(f'{k} {v}' for k, v in on.items())}"
          f"   -> {max(on.values()) / min(on.values()):.2f}x yayilim")
    print(f"    RT kapali: {' / '.join(f'{k} {v}' for k, v in off.items())}"
          f"   -> {max(off.values()) / min(off.values()):.2f}x yayilim")
    print("    Temel render oyunun bolgeleri arasinda sabit; degisken olan")
    print("    isin izleme, cunku maliyeti oyuncunun onunde ne oldugna bagli.")

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}, hepsi fit disi (gameplay)")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  toplam {total} olcum")
        print("  simdi: calibrate_fps_low.py --apply, calibrate_vram.py, validate_engine.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
