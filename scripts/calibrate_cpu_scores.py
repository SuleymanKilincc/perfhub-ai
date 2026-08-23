"""
Rebuilds CPU `power_score` around gaming performance instead of throughput.

The GPU scores turned out to be compressed but correctly ordered, so widening
`GPU_PERF_EXPONENT` fixed most of it. The CPU scores are worse than that: they
are in the *wrong order*. Checked against a published 1080p gaming hierarchy,
the mean error is 13.3 points against the GPUs' 7.2, and the reason is visible
by eye — a Core Ultra 9 285K scored 96 and a Ryzen 7 9800X3D scored 95, when
in games the 285K is well behind it. The values rank all-core throughput, which
is not what this engine ever asks them for.

An exponent cannot repair an ordering, so the scores themselves are rebuilt.
`CPU_PERF_EXPONENT = 0.60` existed largely to flatten the damage — with scores
that mean what they say, it should sit far closer to 1.0.

Only 25 of the 220 CPUs appear in the reference, so the rest come from a model
fitted to those 25:

    index = K x IPC(architecture) x clock x X3D x (min(cores, 8) / 8)^0.25

Clock and the core term are pinned rather than fitted, deliberately. Every CPU
in the reference runs between 4.4 and 5.7 GHz, so a free fit cannot see what
clock does and lands on an exponent of 0.15 — which then scores a 3.5 GHz chip
from 2016 almost as if clock were free. Frame time is inversely proportional to
clock at fixed IPC, so 1.0 is the physically right answer and the safe one to
extrapolate with. The core term saturates at 8 because games do not use more.

That leaves architecture IPC and the X3D multiplier to fit. Six architectures
are covered by the reference; the rest carry published generational IPC and are
marked as such in ARCH_IPC, because a modelled score should not be mistaken for
a measured one.

    python scripts/calibrate_cpu_scores.py            # report
    python scripts/calibrate_cpu_scores.py --apply    # write scores
"""
import argparse
import math
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

# Tom's Hardware CPU hierarchy, 1080p gaming, normalised to the Ryzen 7 9850X3D
# at 100. That chip is not in the database, so nothing anchors to it directly.
REFERENCE_1080P = {
    "Ryzen 7 9800X3D": 97.0, "Ryzen 9 9950X3D": 95.7, "Ryzen 9 9900X3D": 86.9,
    "Ryzen 7 7800X3D": 85.6, "Ryzen 9 7950X3D": 83.9, "Ryzen 5 7600X3D": 80.6,
    "Core i9-14900K": 78.2, "Ryzen 9 7900X3D": 77.1, "Ryzen 9 9950X": 76.9,
    "Core i9-13900K": 76.8, "Core i7-14700K": 76.4, "Core i7-13700K": 75.8,
    "Ryzen 9 9900X": 73.9, "Core i5-14600K": 72.8, "Ryzen 5 9600X": 72.6,
    "Core Ultra 9 285K": 71.8, "Ryzen 9 7950X": 71.0, "Core i5-13600K": 70.9,
    "Ryzen 7 7700X": 70.6, "Core Ultra 7 265K": 70.3, "Ryzen 9 7900X": 69.2,
    "Ryzen 5 7600X": 67.3, "Core Ultra 5 245K": 67.1, "Core i7-12700K": 65.8,
    "Core i5-12600K": 60.8,
}

# Per-clock, per-core gaming performance relative to Zen 5 = 1.00. Six come
# out of the reference above (None = fitted at run time). The rest are chained
# off the two fitted anchors — Zen 4 at 0.943 and Alder Lake at 0.930 — using
# published generational IPC steps, rather than picked to taste:
#
#   Zen 4 -> Zen 3        +13%     Zen 3 -> Zen 2   +19%
#   Zen 2 -> Zen+         +15%     Zen+  -> Zen      +3%
#   Golden Cove -> Cypress Cove (Rocket Lake)   +19%
#   Cypress Cove -> Skylake                     +19%
#   Sunny Cove (Ice Lake) and Willow Cove (Tiger Lake) sit between the two.
#
# Clock is a separate term, so these are IPC alone: Zen 4's headline gain over
# Zen 3 was mostly clock, and taking the full headline figure here would double
# count it. A CPU scored through one of these has no measurement behind it.
ARCH_IPC = {
    # FITTED from the reference
    "Zen 5": None, "Raptor Lake Refresh": None, "Raptor Lake": None,
    "Arrow Lake": None, "Zen 4": None, "Alder Lake": None,
    # Derived, AMD
    "Zen 3+": 0.835, "Zen 3": 0.835, "Zen 2": 0.702, "Zen+": 0.610, "Zen": 0.592,
    # Derived, Intel
    "Meteor Lake": 0.911, "Sapphire Rapids": 0.893, "Tiger Lake": 0.820,
    "Rocket Lake": 0.781, "Ice Lake": 0.774, "Comet Lake": 0.656,
    "Coffee Lake Refresh": 0.656, "Coffee Lake": 0.656, "Skylake": 0.656,
    "Kaby Lake": 0.653, "Broadwell": 0.622,
    # Apple: high IPC at modest clocks. Included for completeness — these run
    # macOS, where the game catalogue this engine models barely applies, so
    # treat any number here as indicative only.
    "Apple Silicon": 1.020,
}

CLOCK_EXPONENT = 1.00       # pinned: frame time is inversely proportional
CORE_EXPONENT = 0.25        # pinned: saturating at 8 cores
CORE_SATURATION = 8

PREFIXES = ("AMD ", "Intel ", "Apple ")


def short(name):
    for p in PREFIXES:
        if name.startswith(p):
            return name if p == "Apple " else name[len(p):]
    return name


def solve(rows, archs):
    """
    Least squares on log(index) = log(K x IPC_arch) + x3d + core term, with the
    clock and core contributions moved to the left-hand side as fixed offsets.
    """
    cols = archs + ["x3d"]
    X, y = [], []
    for r in rows:
        row = [1.0 if r["arch"] == a else 0.0 for a in archs]
        row.append(1.0 if r["x3d"] else 0.0)
        X.append(row)
        offset = (CLOCK_EXPONENT * math.log(r["clock"])
                  + CORE_EXPONENT * math.log(min(r["cores"], CORE_SATURATION)
                                             / CORE_SATURATION))
        y.append(math.log(r["index"]) - offset)

    n = len(cols)
    A = [[sum(X[k][i] * X[k][j] for k in range(len(X))) for j in range(n)]
         for i in range(n)]
    b = [sum(X[k][i] * y[k] for k in range(len(X))) for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]
        b[i], b[p] = b[p], b[i]
        for r in range(n):
            if r == i:
                continue
            f = A[r][i] / A[i][i]
            for j in range(n):
                A[r][j] -= f * A[i][j]
            b[r] -= f * b[i]
    return dict(zip(cols, (b[i] / A[i][i] for i in range(n))))


def main(apply_changes):
    cpus = [dict(c) for c in db_manager.get_all_cpus()]
    by_short = {short(c["name"]): c for c in cpus}

    rows = []
    for key, index in REFERENCE_1080P.items():
        c = by_short.get(key)
        if not c:
            print(f"  UYARI: veritabaninda yok: {key}")
            continue
        rows.append({"key": key, "arch": c["architecture"], "index": index,
                     "clock": c["boost_clock"], "cores": c["cores"],
                     "x3d": "X3D" in key, "old": c["power_score"]})

    fitted_archs = sorted({r["arch"] for r in rows})
    coef = solve(rows, fitted_archs)
    x3d_mult = math.exp(coef["x3d"])
    scale = {a: math.exp(coef[a]) for a in fitted_archs}
    zen5 = scale.get("Zen 5", max(scale.values()))

    print("=== ASAMA 1: model ===")
    print(f"  index = K x IPC x frekans^{CLOCK_EXPONENT} x X3D "
          f"x (cekirdek<={CORE_SATURATION}/{CORE_SATURATION})^{CORE_EXPONENT}")
    print(f"  X3D carpani: {x3d_mult:.3f}x")
    print(f"\n  mimari IPC (Zen 5 = 1.000):")
    for a in sorted(scale, key=lambda a: -scale[a]):
        print(f"    {a:24s} {scale[a] / zen5:.3f}   fit edildi")
    for a, v in sorted(ARCH_IPC.items(), key=lambda kv: -(kv[1] or 9)):
        if v is not None:
            print(f"    {a:24s} {v:.3f}   yayimlanmis IPC (tahmin)")

    def model_index(c):
        arch = c["architecture"]
        ipc = scale.get(arch)
        if ipc is None:
            published = ARCH_IPC.get(arch)
            if published is None:
                return None
            ipc = published * zen5
        return (ipc * c["boost_clock"] ** CLOCK_EXPONENT
                * (x3d_mult if "X3D" in c["name"] else 1.0)
                * (min(c["cores"], CORE_SATURATION) / CORE_SATURATION)
                ** CORE_EXPONENT)

    err = [abs(model_index(by_short[r["key"]]) - r["index"]) for r in rows]
    print(f"\n  referans uzerinde model hatasi: ortalama "
          f"{sum(err) / len(err):.1f} puan, en kotu {max(err):.1f}")

    print("\n=== ASAMA 2: yeni puanlar ===")
    new_scores, unknown = {}, []
    for c in cpus:
        key = short(c["name"])
        if key in REFERENCE_1080P:
            new_scores[key] = round(REFERENCE_1080P[key])
            continue
        idx = model_index(c)
        if idx is None:
            unknown.append(key)
            continue
        new_scores[key] = round(idx)

    if unknown:
        print(f"  mimarisi taninmayan {len(unknown)} CPU degismiyor: "
              f"{unknown[:6]}{' ...' if len(unknown) > 6 else ''}")

    print("\n=== ASAMA 3: aile denetimi ===")
    # The model derives each SKU from its own clock, so it already puts a
    # 12600K above a 12600 without being told. What it cannot see is a
    # database clock that is wrong, which shows up as a locked part beating
    # the unlocked one built from the same die. Cap the base part in that case
    # — never the other way round, which would flatten every K and X SKU onto
    # its slower sibling.
    fixed = 0
    for key in sorted(new_scores):
        faster = [key + s for s in ("K", "X", "KS")]
        faster.append(re.sub(r"K$", "KS", key) if key.endswith("K") else key)
        for sib in faster:
            if sib != key and sib in new_scores and new_scores[key] > new_scores[sib]:
                print(f"  {key:26s} {new_scores[key]:3d} -> {new_scores[sib]:3d}  "
                      f"({sib} bundan hizli olmali)")
                new_scores[key] = new_scores[sib]
                fixed += 1
                break
    # A laptop part is the same silicon on a smaller power budget.
    for key in sorted(new_scores):
        base = re.sub(r"(HX|HS|H|U)$", "", key).strip()
        if base != key and base in new_scores and new_scores[key] > new_scores[base]:
            print(f"  {key:26s} {new_scores[key]:3d} -> {new_scores[base]:3d}  "
                  f"({base} tavani)")
            new_scores[key] = new_scores[base]
            fixed += 1
    print(f"  {fixed} duzeltme")

    updates = [(c["name"], c["power_score"], new_scores[short(c["name"])])
               for c in cpus if short(c["name"]) in new_scores
               and new_scores[short(c["name"])] != c["power_score"]]

    print("\n=== SONUC ===")
    ranked = sorted(((v, k) for k, v in new_scores.items()), reverse=True)
    print("  yeni siralamanin tepesi:")
    for v, k in ranked[:10]:
        old = by_short[k]["power_score"]
        print(f"    {k:28s} {old:4.0f} -> {v:3d}  ({v - old:+.0f})")
    print("  ve dibi:")
    for v, k in ranked[-6:]:
        old = by_short[k]["power_score"]
        print(f"    {k:28s} {old:4.0f} -> {v:3d}  ({v - old:+.0f})")
    print(f"\n  {len(updates)} CPUnun puani degisiyor, "
          f"{len(cpus) - len(updates)} CPU ayni kaliyor")

    if apply_changes:
        conn = db_manager.get_connection()
        cur = conn.cursor()
        for name, _old, new in updates:
            cur.execute("UPDATE cpus SET power_score=? WHERE name=?", (new, name))
        conn.commit()
        conn.close()
        print(f"\n  {len(updates)} CPU yazildi. CPU_PERF_EXPONENT'i yeniden fit "
              f"edin, sonra calibrate_vram.py ve calibrate_engine.py calistirin.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
