"""
Records whether a game's *graphics* cost was ever measured, not just its
processor cost.

The badge says "MEASURED · 28" and it is true and it is misleading. Assetto
Corsa Competizione has 28 benchmark rows and every one of them is 1080p on an
RTX 4090, where the processor is the limit in all 28. So the CPU side is
pinned well and the GPU side was never tested: its `gpu_cost` of 0.35 comes
from a genre prior whose only member is Assetto Corsa Competizione itself.

What that produces on screen is exactly what a user reported — upscaling
changes nothing (at 0.35 the card is never the limit, so there is nothing for
DLSS to relieve), and the frame rate barely moves between an RTX 4060 and an
RTX 4090, 126 against 140. A racing simulator cannot be lighter to draw than
Counter-Strike 2, and the model currently says it is.

This is gap 6e. Thirteen of the 28 fitted games are in some version of it and
seven have no GPU-bound row at all. Nothing here fixes the numbers — that
needs a measurement where the card binds, which means high resolution on a
mid-range GPU. What it fixes is the claim: a game measured on one axis should
not wear the same badge as a game measured on both.

    games.gpu_measured   1 = at least one benchmark row where the GPU is the
                             limit, 0 = the graphics cost rests on a prior

    python scripts/migrate_gpu_measured.py [--apply]
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager, scoring_engine as se


def main(apply_changes):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cols = {r[1] for r in cur.execute("PRAGMA table_info(games)")}
    if "gpu_measured" not in cols:
        print("  yeni sutun: games.gpu_measured INTEGER DEFAULT 0")
        if apply_changes:
            cur.execute("ALTER TABLE games ADD COLUMN gpu_measured INTEGER DEFAULT 0")
            cur.execute("UPDATE games SET gpu_measured = 0 WHERE gpu_measured IS NULL")
    else:
        print("  gpu_measured sutunu zaten var")

    games = {g["name"]: dict(g) for g in db_manager.get_all_games()}
    cpus = {c["name"]: c for c in db_manager.get_all_cpus()}
    gpus = {g["name"]: g for g in db_manager.get_all_gpus()}
    rows = [dict(r) for r in cur.execute(
        "SELECT * FROM benchmarks WHERE COALESCE(scene,'benchmark')='benchmark'"
        " AND COALESCE(texture_pack,0)=0 AND COALESCE(ray_reconstruction,0)=0"
        " AND COALESCE(vram_limited,0)=0")]

    per = {}
    for r in rows:
        g, c, p = games.get(r["game"]), cpus.get(r["cpu"]), gpus.get(r["gpu"])
        if not (g and c and p):
            continue
        d = se.estimate_fps_detailed(
            c, p, g, r["resolution"], r["settings"], r["upscaling"],
            r["frame_gen"], r["ram_gb"], ray_tracing=bool(r["ray_tracing"]),
            path_tracing=bool(r["path_tracing"]))
        per.setdefault(r["game"], []).append(d["bottleneck"])

    print(f"\n  {'oyun':34s} {'satir':>6s} {'GPU-bound':>10s}  durum")
    blind = 0
    for name, b in sorted(per.items()):
        ng = sum(1 for x in b if x == "GPU")
        ok = 1 if ng > 0 else 0
        blind += 1 - ok
        verdict = "GPU olculdu" if ok else "GPU OLCULMEDI — tur priori"
        print(f"  {name[:34]:34s} {len(b):6d} {ng:10d}  {verdict}")
        if apply_changes:
            cur.execute("UPDATE games SET gpu_measured=? WHERE name=?", (ok, name))

    print(f"\n  {blind} oyunun grafik maliyeti hicbir olcume dayanmiyor.")
    if apply_changes:
        conn.commit()
        print("  yazildi. simdi: scripts/export_engine_data.py")
    else:
        print("  (kuru calisma — yazmak icin --apply)")
    conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
