"""
Batch 16 — Night City on the same RTX 3080, and the comparison this project
has been trying to make for five batches.

Batch 15 was Cyberpunk 2077's internal benchmark on an RTX 3080 10GB. This is
free gameplay in Night City on an RTX 3080 10GB. Different video, different
processor, same card and same game — which turns out to be enough, because the
thing we need is a ratio of two measurements, and the card's own error divides
out of a ratio. That is what took the requirement down from "one video with
both" to "any two videos on the same card", and it is why this landed on the
sixth try instead of never.

**The internal benchmark reads 1.70x free play at 1440p.**

    benchmark  (5950X)  measured / predicted   0.895   n=5, all 1440p
    gameplay   (5800X3D)                       0.527   n=4, all 1440p

Every previous estimate of this gap was assembled from different games on
different hardware and came to +18.1%. On one card it is +70%. The earlier
number was not wrong so much as diluted: it averaged Night City against
Bohemian countryside and lunar surfaces.

The single cleanest pair, needing no model at all: 1440p Ultra, RT Lighting
Psycho, rendering at full resolution. The benchmark reads 32.88 with DLAA; the
city reads 20 with no upscaling. 1.64x, and DLAA is the *more* expensive of
the two — it pays for an upscaling pass that Native does not.

Three things that could have explained it away, and did not:

  The processor. The gameplay machine has the *faster* chip — a 5800X3D at
  score 63 against the 5950X at 56. Whatever the gap is, the slower CPU is on
  the side reading higher.

  Video memory. A 10 GB card in Night City with path tracing is exactly where
  one expects a memory wall, and the engine does flag vram_spill on the
  heaviest row. But the row it flags *nothing* on — 1440p DLSS Balanced,
  rendering at 0.58 scale — reads 0.495 against prediction, while the
  benchmark's DLAA row draws every pixel at full resolution, needs far more
  memory, and reads 0.802. The gap is largest where memory pressure is
  lowest, which is the wrong way round for a VRAM explanation.

  The preset. Batch 15's screens said "Custom"; this video says Ultra. If the
  custom settings were lighter than Ultra the benchmark would read high for
  that reason — but that Custom had Texture Quality at its maximum and RT
  Lighting at Psycho, so if it differs from Ultra it differs upward, which
  makes 1.70x an underestimate rather than an artefact.

**The scene changes the processor's ceiling too, not just the card's load.**
At 1080p with Psycho lighting, native reads 50 and DLSS Quality reads 60 — a
1.20x gain where dropping to 0.667 render scale should give roughly 1.9x. That
flattening is a CPU wall, and it puts the 5800X3D at about 60-65 fps in Night
City. Hardware Unboxed measured the same chip at 164 fps in Cyberpunk's
benchmark scene. Some of that is RT and Ultra against RT-off and High, but not
a factor of two and a half. So the benchmark-versus-gameplay gap is not the
card working harder in a busier scene; it is both halves of the machine
meeting a different game.

None of this is corrected in the engine, and one game cannot license a global
factor — Baldur's Gate 3 already showed a title running -12% in one act and
+57% in another. What it does establish is what the predictions *are*: they
answer a benchmark loop, and for Cyberpunk that is nearly twice what someone
driving through Night City will see. Recording it is the first step to saying
so in the interface.

**The 1% low ratios go in, and they raise a question the fitter says it cannot
ask.** calibrate_fps_low.py notes that benchmark and gameplay ratios "are not
interchangeable and nothing here can test whether they differ". For Cyberpunk
it now can: 28 benchmark rows give 0.737, these 8 gameplay rows give 0.813.
Two caveats before anyone believes it. The gameplay figures are read off a
live overlay and are round — 10 and 9, 20 and 15 — so a single row carries
several points of quantisation error. And the benchmark rows are a CPU ladder
at 1080p while these are GPU-bound, which was worth checking: across all 415
rows carrying a 1% low the ratio is 0.764 where the engine says CPU-bound and
0.750 where it says GPU-bound, and inside the three games holding both it is
0.878/0.881, 0.876/0.872 and 0.756/0.749. Bottleneck does not move it. So the
0.076 is not that, and it is either the scene or the rounding.

    python scripts/load_benchmarks_16.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "Cyberpunk 2077"
CPU = "AMD Ryzen 7 5800X3D"
GPU = "NVIDIA GeForce RTX 3080"          # 10 GB, stated at 1:49 in the video
RAM = 64
SOURCE = "b18-cp2077-3080-play"

# The batch 15 benchmark rows, for the comparison printed below. Same card.
BENCH = [("DLAA", 0, 32.88), ("DLSS Quality", 0, 58.99),
         ("DLSS Performance", 0, 75.26), ("DLSS Ultra Performance", 0, 97.56),
         ("DLSS Ultra Performance", 1, 81.71)]

# resolution, upscaling, path_tracing, rt_level, avg, 1% low
# Every row is Ultra, ray tracing on, inside the city.
ROWS = [
    ("1080p", "Native",             1, None,      21, 15),
    ("1080p", "DLSS Balanced",      1, None,      50, 40),
    ("1080p", "Native",             0, "Extreme", 50, 38),
    ("1080p", "DLSS Quality",       0, "Extreme", 60, 50),
    ("1440p", "Native",             1, None,      10,  9),
    ("1440p", "DLSS Performance",   1, None,      35, 30),
    ("1440p", "Native",             0, "Extreme", 20, 15),
    ("1440p", "DLSS Balanced",      0, "Extreme", 45, 40),
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
    bench_cpu = {c["name"]: c for c in db_manager.get_all_cpus()}["AMD Ryzen 9 5950X"]
    gpu = {g["name"]: g for g in db_manager.get_all_gpus()}[GPU]

    def predict(c, res, ups, pt):
        return se.estimate_fps(c, gpu, game, res, "Ultra", ups, "Kapalı", RAM,
                               ray_tracing=True, path_tracing=bool(pt))

    print(f"  {GPU} 10GB + {CPU}, sehir ici serbest oyun")
    print(f"  {'coz':6s} {'ups':22s} {'PT':>2s} {'ort':>4s} {'low':>4s} "
          f"{'oran':>6s} {'tahmin':>6s} {'olc/tah':>7s}")
    added = skipped = 0
    ratios, residual = [], {}
    for res, ups, pt, rt_level, avg, low in ROWS:
        p = predict(cpu, res, ups, pt)
        ratios.append(low / avg)
        residual.setdefault(res, []).append(avg / p)
        print(f"  {res:6s} {ups:22s} {pt:2d} {avg:4d} {low:4d} {low / avg:6.3f} "
              f"{p:6d} {avg / p:7.3f}")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
            " AND settings='Ultra' AND upscaling=? AND path_tracing=?",
            (GAME, CPU, GPU, res, ups, pt)).fetchone()
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
                " VALUES (?,?,?,?,'Ultra',?,'Kapalı',1,?,?,0,?,?,?,'gameplay',"
                "'allocated',?,1)",
                (GAME, CPU, GPU, res, ups, pt, rt_level, RAM, avg, low, SOURCE))

    bench_res = [avg / predict(bench_cpu, "1440p", ups, pt) for ups, pt, avg in BENCH]
    b = sum(bench_res) / len(bench_res)
    g14 = sum(residual["1440p"]) / len(residual["1440p"])
    g10 = sum(residual["1080p"]) / len(residual["1080p"])

    print()
    print("  DAHILI BENCHMARK vs SEHIR (ayni kart — kartin hatasi sadelesiyor)")
    print(f"    benchmark 1440p  olculen/tahmin  {b:.3f}   n={len(bench_res)}")
    print(f"    sehir     1440p                  {g14:.3f}   n={len(residual['1440p'])}")
    print(f"    sehir     1080p                  {g10:.3f}   n={len(residual['1080p'])}")
    print(f"    -> benchmark, sehrin {b / g14:.2f} KATI (1440p)")
    print(f"       1080p'de {b / g10:.2f}x, cunku orada CPU tavani devreye giriyor")
    print("    en temiz cift, modele hic ihtiyac duymayan:")
    print("      1440p Psycho tam cozunurluk — benchmark DLAA 32.88 / sehir 20")
    print(f"      = {32.88 / 20:.2f}x, ustelik DLAA daha PAHALI olan taraf")

    print()
    print("  SEHRIN KENDI CPU TAVANI")
    print("    1080p Psycho: yerli 50 -> DLSS Quality 60 = 1.20x")
    print("    0.667 olcege inerken beklenen kazanc ~1.9x. Fark CPU duvari:")
    print("    5800X3D sehirde ~60-65 fps. HUB ayni islemciyi benchmark")
    print("    sahnesinde 164 fps olcmustu.")

    print()
    mean = sum(ratios) / len(ratios)
    print(f"  %1 LOW ORANI  bu parti {mean:.3f}  (yayilim {min(ratios):.3f}-{max(ratios):.3f})")
    print(f"    Cyberpunk'in kayitli orani 0.737, 28 benchmark satirindan.")
    print("    Sayilar overlay'den okunmus ve yuvarlak (10/9, 20/15) —")
    print("    tek satir birkac puan kuantalama hatasi tasiyor.")

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}, hepsi fit disi (gameplay)")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  toplam {total} olcum")
        print("  simdi: calibrate_fps_low.py --apply, validate_engine.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
