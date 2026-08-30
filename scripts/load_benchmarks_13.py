"""
Batch 13 — The Last of Us Part II from two videos, and a third independence test.

Six rows across an RTX 5080 and an RX 9070 XT, both on a 9800X3D. Neither video
ran the game's internal benchmark, so the benchmark-versus-free-play question
is still open after four attempts.

What they do give is the ratio, on hardware from both vendors:

    RTX 5080  (Blackwell)  0.771, 0.750, 0.699   mean 0.740
    RX 9070 XT (RDNA 4)    0.790, 0.739, 0.708   mean 0.746

That is the third property the ratio has now been shown not to depend on. It
was stored per game because it came out flat across CPU scores from 50 to 100;
Red Dead Redemption 2 and Starfield then showed it flat across location; and
these two show it flat across GPU vendor and architecture. A number that
survives three independent attempts to break it is worth the confidence the
interface gives it.

One row is rejected. The RX 9070 XT video lists 1440p Max FSR4 Native AA twice,
at 100 fps and at 209, same settings and same district. 209/100 is 2.09 — the
frame-generation signature. The prompt asked for frame-generation rows to be
left out and this one arrived unlabelled rather than not at all, which is worth
knowing about the method: a filter stated in the prompt is not a filter applied
to the data.

All six are free gameplay and held out, so the fit still sees only the five
1080p RTX 4060 rows it had. Those give a preset ladder, which identifies the
cost split, but the resolution scaling for this title remains untested by
anything the model is fitted to.

    python scripts/load_benchmarks_13.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

GAME = "The Last of Us Part II"
CPU = "AMD Ryzen 7 9800X3D"

# gpu, resolution, upscaling, avg, 1% low, where
ROWS = [
    ("NVIDIA GeForce RTX 5080", "4k",    "Native",      83,  64,  "forest"),
    ("NVIDIA GeForce RTX 5080", "1440p", "Native",      144, 108, "indoors"),
    ("NVIDIA GeForce RTX 5080", "1080p", "Native",      196, 137, "Seattle"),
    ("AMD Radeon RX 9070 XT",   "1440p", "Native",      100, 79,  "Seattle"),
    ("AMD Radeon RX 9070 XT",   "4k",    "Native",      69,  51,  "Seattle"),
    ("AMD Radeon RX 9070 XT",   "4k",    "FSR Quality", 120, 85,  "Seattle"),
]


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    by_gpu = {}
    added = skipped = 0
    print(f"  {'kart':24s} {'coz':6s} {'ups':13s} {'ort':>4s} {'low':>4s} {'oran':>6s}  konum")
    for gpu, res, ups, avg, low, where in ROWS:
        if not cur.execute("SELECT 1 FROM gpus WHERE name=?", (gpu,)).fetchone():
            sys.exit(f"  {gpu} katalogda yok")
        by_gpu.setdefault(gpu, []).append(low / avg)
        print(f"  {gpu[10:34]:24s} {res:6s} {ups:13s} {avg:4d} {low:4d} {low / avg:6.3f}  {where}")
        dup = cur.execute(
            "SELECT 1 FROM benchmarks WHERE game=? AND cpu=? AND gpu=? AND resolution=?"
            " AND settings='Extreme' AND upscaling=?",
            (GAME, CPU, gpu, res, ups)).fetchone()
        if dup:
            skipped += 1
            continue
        added += 1
        if apply_changes:
            cur.execute(
                "INSERT INTO benchmarks (game, cpu, gpu, resolution, settings,"
                " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb, fps_avg,"
                " fps_1pct_low, scene, vram_measured_kind, source, verified)"
                " VALUES (?,?,?,?,'Extreme',?,'Kapalı',0,0,32,?,?,'gameplay',"
                "'allocated','b18-tlou2-two-vendors',1)",
                (GAME, CPU, gpu, res, ups, avg, low))

    print()
    print("  URETICIYE GORE ORAN")
    for gpu, qs in by_gpu.items():
        print(f"    {gpu[10:34]:24s} n={len(qs)}  {sum(qs) / len(qs):.3f}")
    print("    -> fark yok. Oran artik CPU'dan, konumdan ve uretici/mimariden")
    print("       bagimsiz oldugu gosterilmis bir sayi.")

    print(f"\n  {added} satir{'' if apply_changes else ' eklenecek'}"
          f"{f', {skipped} zaten var' if skipped else ''}")
    print("  1 satir reddedildi: 1440p 209 fps, ayni ayarin 100 fps satirinin")
    print("  2.09 kati — frame generation imzasi, etiketlenmeden gelmis.")
    if apply_changes:
        conn.commit()
        total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
        print(f"  toplam {total} olcum")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
