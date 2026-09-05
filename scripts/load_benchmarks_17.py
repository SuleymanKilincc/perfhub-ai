"""
Batch 17 — Hitman World of Assassination, and the first paired VRAM readings.

Nine configurations from one video: 1080p, 1440p and 4K, native and DLSS,
frame generation on and off, ray tracing on and off. Read from an overlay,
which is why every setting had to be recovered from the video's chapter marks
rather than from a results screen — the labels are 1080p ULTRA, 1080p ULTRA /
DLSS Q, 1080p ULTRA / DLSS Q / F.G ON, 1440p ULTRA, 1440p ULTRA / DLSS Q,
1440p ULTRA / DLSS Q / F.G ON, 4K ULTRA, 4K ULTRA / DLSS P, 1080p ULTRA /
RTX ON, 1080p ULTRA / RTX ON / DLSS Q. Eight of the ten were captured; 4K
native was not.

**It is gameplay, not the internal benchmark.** The channel is called Panda
Benchmarks and the title says Benchmark, but the footage has a minimap,
mission objectives and SUBDUE prompts — someone walking a route through
Bangkok. Hitman's built-in tool is a cameras-only flythrough of Dubai or
Dartmoor. So every row is scene='gameplay' and none of it reaches the cost
fit, which costs us the thing this game most needs: all 28 existing Hitman
rows are the *same* configuration — RTX 4090, 1080p, Ultra, native, RT off,
28 processors — so the game's `gpu_cost` of 0.90 has never been measured and
still has not been. What the resolution sweep does say is that the direction
is wrong: at native the engine reads -20% at 1080p and -33% at 1440p.

**Ray tracing in this game costs at least 3x.** Same resolution, same preset,
same upscaler, ray tracing the only difference:

    1080p native        162 -> 42     3.86x
    1080p DLSS Quality  168 -> 54     3.11x

Both are floors rather than measurements, because the ray-tracing-off rows are
against the processor (see below) and so understate what the card was capable
of. Against a global RT_GPU_COST_MULT of 1.70 and Far Cry 6's measured 1.10x,
that is the third point on a spread that a single boolean cannot hold — Far
Cry 6 does reflections and shadows, Hitman does reflections and shadows and
apparently pays several times more for them.

**The processor wall shows up here as it did in Cyberpunk.** At 1080p, native
reads 162 and DLSS Quality reads 168 — a 1.04x gain where dropping to 0.667
render scale should give about 1.9x. The card is not the limit; the chip is,
at roughly 165-170 in this scene. Hardware Unboxed measured Hitman's internal
benchmark on an i5-12400F — score 52 against this i5-14400F's 63, a slower
chip — at 206 fps. The faster processor in gameplay reads 1.23x *below* the
slower one in the benchmark loop. That is batch 16's Cyberpunk finding on a
second game, from the processor side, and it is the same direction.

**The first paired working-set and allocation readings this project has had.**
All 63 existing VRAM measurements are allocations alone; the formula that
turns them into working sets — `allocation = working x 1.12 + 0.8 GB` — has
never been checked against a direct measurement of both. This overlay reports
DEDICATED and ALLOCATED side by side:

    ded  4.72 alloc 5.02      ded 4.68 alloc 5.01      ded 5.00 alloc 5.32
    ded  4.92 alloc 5.24      ded 5.02 alloc 5.34      ded 5.51 alloc 5.83
    ded  6.00 alloc 6.32      ded 6.52 alloc 6.84      ded 6.46 alloc 6.77

The measured ratio is 1.049 to 1.069 across all nine — remarkably steady. The
formula predicts 6.09 GB where 5.02 was measured, 21% high.

This also decides which of the two numbers to load. calibrate_vram.py warns
that inverting a usage figure as though it were an allocation "lands about 25%
low", and that warning has until now rested on reasoning rather than a
measurement. Invert this row's allocation — (5.02 - 0.8) / 1.12 — and it gives
3.77 GB against the 4.72 the overlay reports as resident. 20% low, confirming
the warning with the first paired reading the project has had. So the
DEDICATED column goes in with `vram_measured_kind='used'`, and the allocations
stay here as the record.
Before calling the formula wrong, note what the VRAM section of CALIBRATION.md
already says: a game caches into whatever is spare, so the number partly
describes the card. This is an 8 GB card with very little spare, and Alan Wake
2 reported 28 GB at 8K on a 32 GB one. So the honest reading is not "1.12 and
0.8 are wrong" but "a flat appetite plus a flat reserve cannot be right for
both cards", and the measurement that settles it is a paired reading on a
large card. Also worth saying: DEDICATED is a process's resident memory, which
includes cache, so it sits a little above a true working set rather than
exactly on it.

**The 1% low ratio disagrees with the existing rows by 0.199**, the widest gap
between two sources for one game we have. Hitman's 0.878 comes from 28
Dartmoor benchmark rows — a quiet English manor, and the steadiest ratio in
the set. These nine crowded-hotel rows give 0.679. The fitted value lands at
0.830.
That is worth one check, because Cyberpunk's equivalent gap ran the *other*
way (benchmark 0.737, gameplay 0.813) and a ratio that moves in both
directions with the source looks like tooling rather than games. It is not.
Inside the single b10-hub source, eight games measured by one reviewer with
one tool spread from 0.533 in Counter-Strike 2 to 0.847 in Star Wars Jedi:
Survivor — a range of 0.314 — while the means of all ten sources span 0.167.
Games separate further than sources do. The per-game ratio survives a fifth
test, after processor score, location, GPU vendor and bottleneck.
What it does mean is that one ratio per game has the same limit one cost per
game has: Baldur's Gate 3 for the cost, Hitman for the ratio.

**One row is not trusted.** Frame generation reads 168 -> 256 at 1080p, a
1.52x gain, and 152 -> 178 at 1440p, a 1.17x gain. Those cannot both be right.
The overlay's AVG resets per segment and each screenshot was taken at an
unknown point inside its segment, so a mid-run average over a light stretch of
the route is the likely cause. Both rows are loaded because both are held out
of every fit anyway, and the inconsistency is recorded here rather than
averaged into something that looks like a measurement.

    python scripts/load_benchmarks_17.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Hitman 3"
CPU = "Intel Core i5-14400"      # video says 14400F; the F is only the missing iGPU
GPU = "NVIDIA GeForce RTX 5060"  # 8 GB
RAM = 32
SOURCE = "b20-hitman-5060-play"

# chapter, resolution, upscaling, ray_tracing, frame_gen, avg, 1% low,
# dedicated MB, allocated MB
ROWS = [
    ("0:00  1080p ULTRA",             "1080p", "Native",           0, "Kapalı", 162, 106, 4834, 5143),
    ("1:35  1080p DLSS Q",            "1080p", "DLSS Quality",     0, "Kapalı", 168, 112, 4797, 5126),
    ("3:13  1080p DLSS Q FG",         "1080p", "DLSS Quality",     0, "2x",     256, 175, 5120, 5448),
    ("5:01  1440p ULTRA",             "1440p", "Native",           0, "Kapalı", 123,  86, 5034, 5362),
    ("6:39  1440p DLSS Q",            "1440p", "DLSS Quality",     0, "Kapalı", 152, 101, 5144, 5472),
    ("8:21  1440p DLSS Q FG",         "1440p", "DLSS Quality",     0, "2x",     178, 135, 5645, 5973),
    ("11:29 4K DLSS P",               "4k",    "DLSS Performance", 0, "Kapalı", 117,  84, 6141, 6469),
    ("13:05 1080p RTX ON",            "1080p", "Native",           1, "Kapalı",  42,  26, 6680, 7007),
    ("14:37 1080p RTX ON DLSS Q",     "1080p", "DLSS Quality",     1, "Kapalı",  54,  35, 6610, 6937),
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

    game = {g["name"]: g for g in db_manager.get_all_games()}[GAME]
    cpu = {c["name"]: c for c in db_manager.get_all_cpus()}[CPU]
    gpu = {g["name"]: g for g in db_manager.get_all_gpus()}[GPU]

    print(f"  {GPU} 8GB + {CPU} (14400F), Bangkok, serbest oyun")
    print(f"  {'bolum':28s} {'ort':>4s} {'low':>4s} {'oran':>6s} {'tahmin':>6s} {'hata':>7s}")
    added = skipped = 0
    ratios, alloc_ratio = [], []
    for lbl, res, ups, rt, fg, avg, low, ded, alloc in ROWS:
        p = se.estimate_fps(cpu, gpu, game, res, "Ultra", ups, fg, RAM,
                            ray_tracing=bool(rt))
        ratios.append(low / avg)
        alloc_ratio.append(alloc / ded)
        print(f"  {lbl:28s} {avg:4d} {low:4d} {low / avg:6.3f} {p:6d} "
              f"{(p - avg) / avg * 100:+6.1f}%")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
            " AND settings='Ultra' AND upscaling=? AND frame_gen=? AND ray_tracing=?",
            (GAME, CPU, GPU, res, ups, fg, rt)).fetchone()
        if dup:
            skipped += 1
            continue
        added += 1
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ray_reconstruction,"
                " ram_gb, fps_avg, fps_1pct_low, vram_measured_gb, scene,"
                " vram_measured_kind, source, verified)"
                " VALUES (?,?,?,?,'Ultra',?,?,?,0,0,?,?,?,?,'gameplay',"
                "'used',?,1)",
                (GAME, CPU, GPU, res, ups, fg, rt, RAM, avg, low,
                 round(ded / 1024, 1), SOURCE))

    print()
    print("  ISIN IZLEME MALIYETI (tek fark RT)")
    print(f"    1080p yerli    162 -> 42  = {162 / 42:.2f}x")
    print(f"    1080p DLSS Q   168 -> 54  = {168 / 54:.2f}x")
    print("    ikisi de TABAN: RT-kapali satirlar islemci duvarinda.")
    print("    kuresel 1.70, Far Cry 6 1.10x — tek boolean bu yayilimi tutamiyor.")

    print()
    print("  ISLEMCI DUVARI")
    print(f"    1080p yerli 162 -> DLSS Q 168 = {168 / 162:.2f}x  (beklenen ~1.9x)")
    print("    kart limit degil, cip limit: bu sahnede ~165-170 fps.")
    print("    HUB, DAHILI BENCHMARK, i5-12400F (skor 52, bu ciptan yavas): 206 fps")
    print(f"    -> hizli cip serbest oyunda {206 / 168:.2f}x DAHA DUSUK okuyor.")
    print("       Batch 16'nin Cyberpunk bulgusu, ikinci oyunda, islemci tarafindan.")

    print()
    print("  VRAM: ilk esli okuma (dedicated + allocated ayni anda)")
    print(f"    olculen alloc/ded orani {min(alloc_ratio):.3f}-{max(alloc_ratio):.3f}"
          f"  ort {sum(alloc_ratio) / len(alloc_ratio):.3f}")
    print("    model: alloc = working * 1.12 + 0.8 GB")
    print(f"    ornek: ded 4.72 -> model {4.72 * 1.12 + 0.8:.2f} GB, olculen 5.02 GB")
    print("    8 GB kart, bos yeri az. Buyuk kartta esli okuma gerekiyor.")

    mean = sum(ratios) / len(ratios)
    print()
    print(f"  %1 LOW ORANI  bu parti {mean:.3f}   kayitli Hitman orani 0.878")
    print("    0.878, 28 Dartmoor benchmark satirindan (sakin bir malikane).")
    print("    Bu satirlar kalabalik bir otel. Fark 0.199 — tek oyun icin")
    print("    gordugumuz en genis kaynak ayrismasi.")

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
