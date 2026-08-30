"""
Proves the Python and TypeScript engines give identical answers.

The website runs its own copy of Cadence so a prediction needs no server (see
frontend/src/engine/cadence.ts). Two implementations can drift, and a drift
here is invisible: the site would simply be confidently wrong while every test
that only exercises Python stays green.

So this runs both over a grid of cases and compares every field, not just the
frame rate — status, bottleneck, VRAM figures and the warning strings too,
since those are what the UI shows. Any difference fails.

Constants and the catalogue are generated rather than compared, by
scripts/export_engine_data.py. This covers the part that is hand-written.

    python scripts/conformance_test.py            # ~4000 cases
    python scripts/conformance_test.py --cases N
"""
import argparse
import io
import json
import os
import random
import subprocess
import sys
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager
from core import scoring_engine as se

RESOLUTIONS = ["1080p", "1440p", "4k", "8k"]
SETTINGS = ["Very Low", "Low", "Medium", "High", "Ultra", "Extreme", "Nonsense"]
UPSCALING = ["Native", "DLAA", "DLSS Quality", "DLSS Balanced", "DLSS Performance",
             "DLSS Ultra Performance", "FSR Quality", "FSR Performance",
             "XeSS Quality", "XeSS Balanced"]
FRAME_GEN = ["Kapalı", "2x", "3x", "4x"]
# Deliberately includes cramped configurations: the interesting behaviour is
# VRAM spilling into system RAM, and that only shows up when RAM is short.
RAM_SIZES = [8, 16, 24, 32, 64]

# `notes` is the structured version and the one that matters: it compares what
# the model observed rather than how it was worded, so rephrasing a warning no
# longer fails the run. `warnings` stays in the list because the desktop app
# reads it and the two renderers have to agree character for character.
FIELDS = ["fps", "fps_low", "fps_low_measured", "capped_fps", "rendered_fps",
          "status", "bottleneck",
          "vram_needed_gb", "vram_alloc_gb", "vram_available_gb", "quality",
          "notes", "warnings"]

GAME_KEYS = ["name", "gpu_cost", "cpu_cost", "vram_base_gb", "ram_base_gb",
             "fps_low_ratio", "fps_low_measured",
             "tier_min", "tier_max", "fps_cap", "supports_rt", "supports_pt",
             "supports_dlss", "supports_fsr", "supports_xess"]


def build_cases(n, seed=20260824):
    rng = random.Random(seed)
    cpus = [dict(c) for c in db_manager.get_all_cpus()]
    gpus = [dict(g) for g in db_manager.get_all_gpus()]
    games = [dict(g) for g in db_manager.get_all_games()]

    # Trim to the fields the engines actually read, but trim honestly: a field
    # left out here is a field the test cannot compare, and it will still pass.
    # `architecture` was missing when the legacy-GPU note was added, so 4768
    # cases agreed perfectly while never once running the new branch.
    def hw(row, *keys):
        return {k: row.get(k) for k in keys}

    cases = []
    for _ in range(n):
        cpu = rng.choice(cpus)
        gpu = rng.choice(gpus)
        game = rng.choice(games)
        cases.append({
            "cpu": hw(cpu, "name", "power_score", "form_factor", "cores"),
            "gpu": hw(gpu, "name", "power_score", "vram", "architecture", "form_factor"),
            "game": {k: game.get(k) for k in GAME_KEYS},
            "resolution": rng.choice(RESOLUTIONS),
            "settings": rng.choice(SETTINGS),
            "upscaling": rng.choice(UPSCALING),
            "frame_gen": rng.choice(FRAME_GEN),
            "ram_gb": rng.choice(RAM_SIZES),
            "ray_tracing": rng.random() < 0.35,
            "path_tracing": rng.random() < 0.15,
        })

    # Pin the corners as well as the random middle: the weakest and strongest
    # parts, and an 8 GB card on 8 GB of RAM at 8K, which is the case the
    # memory model is most likely to disagree about.
    weakest_gpu = min(gpus, key=lambda g: g["power_score"])
    strongest_gpu = max(gpus, key=lambda g: g["power_score"])
    weakest_cpu = min(cpus, key=lambda c: c["power_score"])
    strongest_cpu = max(cpus, key=lambda c: c["power_score"])
    for cpu, gpu in ((weakest_cpu, weakest_gpu), (strongest_cpu, strongest_gpu),
                     (weakest_cpu, strongest_gpu), (strongest_cpu, weakest_gpu)):
        for game in games[:12]:
            for res in RESOLUTIONS:
                for ram in (8, 32):
                    cases.append({
                        "cpu": hw(cpu, "name", "power_score", "form_factor", "cores"),
                        "gpu": hw(gpu, "name", "power_score", "vram", "architecture", "form_factor"),
                        "game": {k: game.get(k) for k in GAME_KEYS},
                        "resolution": res, "settings": "Ultra",
                        "upscaling": "Native", "frame_gen": "Kapalı",
                        "ram_gb": ram, "ray_tracing": True, "path_tracing": True,
                    })
    return cases


def run_python(cases):
    out = []
    for c in cases:
        out.append(se.estimate_fps_detailed(
            c["cpu"], c["gpu"], c["game"], c["resolution"], c["settings"],
            c["upscaling"], c["frame_gen"], c["ram_gb"],
            ray_tracing=c["ray_tracing"], path_tracing=c["path_tracing"]))
    return out


def run_node(cases, tmpdir):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    esbuild = os.path.join(root, "frontend", "node_modules", ".bin",
                           "esbuild.cmd" if os.name == "nt" else "esbuild")
    if not os.path.exists(esbuild):
        sys.exit("  esbuild yok — once 'cd frontend && npm install' calistirin.")

    bundle = os.path.join(tmpdir, "runner.mjs")
    subprocess.run(
        [esbuild, os.path.join(root, "scripts", "conformance_runner.ts"),
         "--bundle", "--platform=node", "--format=esm", "--log-level=warning",
         f"--outfile={bundle}"],
        check=True)

    cases_path = os.path.join(tmpdir, "cases.json")
    out_path = os.path.join(tmpdir, "results.json")
    with open(cases_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False)

    subprocess.run(["node", bundle, cases_path, out_path], check=True)
    with open(out_path, encoding="utf-8") as f:
        return json.load(f)


def describe(case):
    return (f"{case['game']['name']} / {case['gpu']['name']} / {case['cpu']['name']} / "
            f"{case['resolution']} {case['settings']} {case['upscaling']} "
            f"fg={case['frame_gen']} ram={case['ram_gb']} "
            f"rt={int(case['ray_tracing'])} pt={int(case['path_tracing'])}")


def main(n):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cases = build_cases(n)
    print(f"  {len(cases)} vaka uretildi")

    py = run_python(cases)
    print("  Python motoru calisti")

    with tempfile.TemporaryDirectory() as tmp:
        ts = run_node(cases, tmp)
    print("  TypeScript motoru calisti")
    print()

    mismatches = []
    per_field = {f: 0 for f in FIELDS}
    for case, a, b in zip(cases, py, ts):
        diff = [f for f in FIELDS if a.get(f) != b.get(f)]
        if diff:
            for f in diff:
                per_field[f] += 1
            mismatches.append((case, a, b, diff))

    if not mismatches:
        print(f"  TAMAM: {len(cases)} vakanin tamami, {len(FIELDS)} alanda birebir ayni.")
        return 0

    print(f"  AYRISMA: {len(mismatches)}/{len(cases)} vaka ayrisiyor")
    print()
    print("  alan bazinda:")
    for f, k in sorted(per_field.items(), key=lambda kv: -kv[1]):
        if k:
            print(f"    {f:18s} {k}")
    print()
    print("  ilk 5 ayrisma:")
    for case, a, b, diff in mismatches[:5]:
        print(f"    {describe(case)}")
        for f in diff:
            print(f"      {f}:  python={a.get(f)!r}  ts={b.get(f)!r}")
    return 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=4000)
    sys.exit(main(ap.parse_args().cases))
