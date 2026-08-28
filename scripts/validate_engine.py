"""
Benchmark harness: measures how far the FPS engine is from reality.

Without this there is no way to tell whether a change to the engine or to the
balance constants made predictions better or worse — every "improvement" is
just an opinion. This script turns that into a number.

Usage
-----
    python scripts/validate_engine.py              # report current accuracy
    python scripts/validate_engine.py --seed       # create the table + sample rows
    python scripts/validate_engine.py --add        # interactively add one anchor

How to use it properly
----------------------
Fill the `benchmarks` table with *real measured* numbers: a known CPU + GPU
combination running a specific game at a specific resolution and preset, with
the average fps a review or your own machine actually produced. Thirty or
forty well-spread anchors are enough to calibrate the whole model.

Then change one constant in core/balance_config.py, re-run this, and see
whether the mean error went down. That is the entire loop.

Every seeded row carries a `source` and a `verified` flag. Rows with
verified=0 are placeholders that have NOT been checked against a real review
and should be replaced before they are trusted for calibration.
"""
import argparse
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager, scoring_engine

SCHEMA = """
CREATE TABLE IF NOT EXISTS benchmarks (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    game         TEXT    NOT NULL,
    cpu          TEXT    NOT NULL,
    gpu          TEXT    NOT NULL,
    resolution   TEXT    NOT NULL,
    settings     TEXT    NOT NULL,
    upscaling    TEXT    DEFAULT 'Native',
    frame_gen    TEXT    DEFAULT 'Kapalı',
    ray_tracing  INTEGER DEFAULT 0,
    path_tracing INTEGER DEFAULT 0,
    ram_gb       INTEGER DEFAULT 32,
    fps_avg      REAL    NOT NULL,
    source       TEXT,
    verified     INTEGER DEFAULT 0,
    UNIQUE(game, cpu, gpu, resolution, settings, upscaling, frame_gen,
           ray_tracing, path_tracing)
)
"""

# Starting anchors. These are rough reference points used to sanity-check the
# harness itself, NOT verified measurements — every one is verified=0 on
# purpose. Replace them with numbers taken from a specific review or your own
# runs (and set verified=1) before using them to tune anything.
SEED_ROWS = [
    # (game, cpu, gpu, res, settings, upscaling, fg, rt, pt, ram, fps, source)
    ("Cyberpunk 2077", "AMD Ryzen 7 7800X3D", "NVIDIA GeForce RTX 4090",
     "1080p", "High", "Native", "Kapalı", 0, 0, 32, 170, "placeholder"),
    ("Cyberpunk 2077", "AMD Ryzen 7 7800X3D", "NVIDIA GeForce RTX 4090",
     "1440p", "High", "Native", "Kapalı", 0, 0, 32, 115, "placeholder"),
    ("Cyberpunk 2077", "AMD Ryzen 7 7800X3D", "NVIDIA GeForce RTX 4090",
     "4k", "High", "Native", "Kapalı", 0, 0, 32, 67, "placeholder"),
    ("Cyberpunk 2077", "Intel Core i5-13400F", "NVIDIA GeForce RTX 4060",
     "1080p", "High", "Native", "Kapalı", 0, 0, 16, 65, "placeholder"),
    ("Valorant", "AMD Ryzen 7 7800X3D", "NVIDIA GeForce RTX 4090",
     "1080p", "High", "Native", "Kapalı", 0, 0, 32, 700, "placeholder"),
    ("CS:GO 2", "AMD Ryzen 7 7800X3D", "NVIDIA GeForce RTX 4090",
     "1080p", "High", "Native", "Kapalı", 0, 0, 32, 600, "placeholder"),
]


def _connect():
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    return conn


def seed():
    conn = _connect()
    cur = conn.cursor()
    cur.execute(SCHEMA)
    added = 0
    for row in SEED_ROWS:
        cur.execute(
            "INSERT OR IGNORE INTO benchmarks (game, cpu, gpu, resolution, "
            "settings, upscaling, frame_gen, ray_tracing, path_tracing, "
            "ram_gb, fps_avg, source, verified) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)", row)
        added += cur.rowcount
    conn.commit()
    total = cur.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0]
    conn.close()
    print(f"  benchmarks tablosu hazir. {added} yeni satir, toplam {total}.")
    print("  NOT: seed satirlari 'placeholder' — gercek olcumlerle "
          "degistirilmeli (verified=1 yapin).")


def validate(only_verified=False):
    conn = _connect()
    cur = conn.cursor()
    cur.execute(SCHEMA)

    games = {g["name"]: g for g in db_manager.get_all_games()}
    cpus = {c["name"]: c for c in db_manager.get_all_cpus()}
    gpus = {g["name"]: g for g in db_manager.get_all_gpus()}

    query = "SELECT * FROM benchmarks"
    if only_verified:
        query += " WHERE verified = 1"
    rows = list(cur.execute(query))
    conn.close()

    if not rows:
        print("  Hic olcum kaydi yok. Once: python scripts/validate_engine.py --seed")
        return

    results, missing = [], []
    for b in rows:
        game, cpu, gpu = games.get(b["game"]), cpus.get(b["cpu"]), gpus.get(b["gpu"])
        if not (game and cpu and gpu):
            missing.append((b["game"], b["cpu"], b["gpu"]))
            continue
        predicted = scoring_engine.estimate_fps(
            cpu, gpu, game, b["resolution"], b["settings"], b["upscaling"],
            b["frame_gen"], b["ram_gb"],
            ray_tracing=bool(b["ray_tracing"]), path_tracing=bool(b["path_tracing"]),
        )
        actual = b["fps_avg"]
        err = (predicted - actual) / actual * 100.0
        results.append((abs(err), err, predicted, actual, b))

    if missing:
        print(f"  {len(missing)} kayit atlandi (donanim/oyun veritabaninda yok):")
        for m in missing[:5]:
            print(f"    - {m}")
        print()

    if not results:
        print("  Degerlendirilebilir kayit yok.")
        return

    # Sort on the error alone. Sorting whole tuples breaks as soon as two rows
    # tie, because the comparison then falls through to the sqlite3.Row
    # objects, which are not orderable.
    results.sort(key=lambda r: r[0], reverse=True)
    mean_abs = sum(r[0] for r in results) / len(results)
    bias = sum(r[1] for r in results) / len(results)
    within10 = sum(1 for r in results if r[0] <= 10) / len(results) * 100
    within20 = sum(1 for r in results if r[0] <= 20) / len(results) * 100

    print(f"  Olcum sayisi          : {len(results)}")
    print(f"  Ortalama mutlak hata  : {mean_abs:5.1f} %")
    print(f"  Sistematik sapma      : {bias:+5.1f} %  "
          f"({'motor fazla iyimser' if bias > 0 else 'motor fazla kotumser'})")
    print(f"  %10 icinde            : {within10:5.1f} %")
    print(f"  %20 icinde            : {within20:5.1f} %")

    # The fit never sees gameplay rows, so their error is the only number here
    # that says anything about generalisation. Averaging the two together would
    # bury exactly that.
    by_scene = {}
    for r in results:
        by_scene.setdefault(r[4]["scene"] if "scene" in r[4].keys() else "benchmark",
                            []).append(r)
    if len(by_scene) > 1:
        print()
        for scene, rs in sorted(by_scene.items()):
            label = "fit edilmis" if scene == "benchmark" else "HARIC TUTULAN"
            print(f"  {scene:10s} ({label:13s}) : n={len(rs):3d}  "
                  f"hata {sum(x[0] for x in rs)/len(rs):5.1f} %  "
                  f"sapma {sum(x[1] for x in rs)/len(rs):+5.1f} %")

    print("\n  En kotu tahminler:")
    for _, err, pred, actual, b in results[:8]:
        flag = "" if b["verified"] else "  [dogrulanmamis]"
        print(f"    {b['game'][:26]:26s} {b['gpu'][14:32]:18s} {b['resolution']:6s} "
              f"{b['settings']:8s} tahmin={pred:4d} gercek={actual:5.0f} "
              f"hata={err:+6.1f}%{flag}")


def add_interactive():
    """Add one anchor from the command line."""
    fields = [
        ("game", "Oyun adi", None), ("cpu", "CPU adi", None),
        ("gpu", "GPU adi", None), ("resolution", "Cozunurluk (1080p/1440p/4k)", "1080p"),
        ("settings", "Ayar (Low/Medium/High/Ultra)", "High"),
        ("upscaling", "Upscaling", "Native"), ("frame_gen", "Frame Gen", "Kapalı"),
        ("ray_tracing", "Ray tracing (0/1)", "0"), ("path_tracing", "Path tracing (0/1)", "0"),
        ("ram_gb", "RAM (GB)", "32"), ("fps_avg", "Olculen ortalama FPS", None),
        ("source", "Kaynak (kanal/site/kendi olcumum)", "manual"),
    ]
    values = {}
    for key, prompt, default in fields:
        suffix = f" [{default}]" if default else ""
        raw = input(f"  {prompt}{suffix}: ").strip()
        values[key] = raw or default
        if values[key] is None:
            print("  Bu alan zorunlu.")
            return

    conn = _connect()
    cur = conn.cursor()
    cur.execute(SCHEMA)
    cur.execute(
        "INSERT OR REPLACE INTO benchmarks (game, cpu, gpu, resolution, settings,"
        " upscaling, frame_gen, ray_tracing, path_tracing, ram_gb, fps_avg,"
        " source, verified) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,1)",
        (values["game"], values["cpu"], values["gpu"], values["resolution"],
         values["settings"], values["upscaling"], values["frame_gen"],
         int(values["ray_tracing"]), int(values["path_tracing"]),
         int(values["ram_gb"]), float(values["fps_avg"]), values["source"]))
    conn.commit()
    conn.close()
    print("  Kaydedildi (verified=1).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FPS motoru dogrulama araci")
    parser.add_argument("--seed", action="store_true", help="tabloyu olustur + ornek satirlar")
    parser.add_argument("--add", action="store_true", help="elle olcum ekle")
    parser.add_argument("--verified-only", action="store_true",
                        help="sadece dogrulanmis olcumleri kullan")
    args = parser.parse_args()

    if args.seed:
        seed()
    elif args.add:
        add_interactive()
    else:
        validate(only_verified=args.verified_only)
