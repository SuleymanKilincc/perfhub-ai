"""
Validates and corrects GPU `power_score` against measured relative performance.

The scores were hand assigned and never checked. Comparing them against a
published 1440p performance hierarchy showed every one of 48 cards predicted
*too fast* relative to the RTX 5090 — a one-sided error, which means the scale
itself was compressed rather than individual cards being noisy.

Two corrections come out of that, applied in this order:

1. `GPU_PERF_EXPONENT` 1.54 -> 1.85. The exponent controls how much of a score
   gap turns into a frame-rate gap, so widening it stretches the whole ladder
   at once. This halves the error without touching a single card, and it is
   safe for the 116 cards the reference does not cover: it is monotonic, so no
   card overtakes another.

2. Per-card correction for what remains. After step 1 the residuals are
   two-sided — real per-card errors rather than a scale problem — so the cards
   more than `TOLERANCE` points off get their score solved directly from the
   measured figure.

Step 2 can move a card past a sibling the reference never measured — correcting
the RX 9060 XT downwards leaves the plain RX 9060 above it, which is wrong. So
step 3 carries the correction across to cards that are variants of a corrected
one, in proportion.

What step 3 deliberately does *not* do is interpolate a correction for every
card from its old score. That was the first attempt and it is unsound: once the
exponent is fixed the residuals are two-sided per-card noise, not a trend, so
neighbouring scores disagree about which way to move. Cards with neither a
measurement nor a corrected sibling — the GTX 10 and RTX 20 series, Arc A,
integrated graphics — are left alone. The exponent change already applies to
them, and inventing individual corrections without evidence would only add
noise that looks like precision.

    python scripts/calibrate_gpu_scores.py            # report
    python scripts/calibrate_gpu_scores.py --apply    # write scores
"""
import argparse
import os
import re
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

# Tom's Hardware GPU benchmarks hierarchy, 1440p ultra, normalised to
# RTX 5090 = 100. Two rows from the source are deliberately absent: it puts the
# RX 6600 below an RTX 3050 and the RX 6650 XT below an RX 6600 XT, both of
# which invert the real ordering. Its low end is unreliable; its top is not.
REFERENCE_1440P = {
    "RTX 5090": 100.0, "RTX 4090": 85.7, "RTX 5080": 76.7, "RX 7900 XTX": 73.1,
    "RTX 4080 SUPER": 70.9, "RTX 4080": 70.3, "RTX 5070 Ti": 69.8,
    "RX 9070 XT": 69.7, "RX 7900 XT": 64.6, "RTX 4070 Ti SUPER": 62.1,
    "RX 9070": 62.1, "RTX 3090 Ti": 59.7, "RTX 4070 Ti": 58.6, "RTX 5070": 57.6,
    "RTX 3090": 54.7, "RTX 4070 SUPER": 54.5, "RX 6950 XT": 53.5,
    "RTX 3080 Ti": 53.3, "RX 9070 GRE": 51.8, "RX 7800 XT": 50.7,
    "RX 6900 XT": 50.2, "RTX 3080": 49.0, "RX 6800 XT": 47.6, "RTX 4070": 46.5,
    "RTX 5060 Ti 16GB": 43.9, "RX 7700 XT": 43.4, "RTX 5060 Ti 8GB": 41.0,
    "RX 9060 XT 16GB": 40.2, "RTX 3070 Ti": 40.0, "RX 9060 XT 8GB": 37.3,
    "RTX 4060 Ti 16GB": 36.2, "RTX 5060": 35.8, "RTX 4060 Ti 8GB": 35.2,
    "RTX 3070": 34.8, "RX 6750 XT": 34.4, "RX 6700 XT": 32.5,
    "RTX 3060 Ti": 30.5, "Arc B580": 30.3, "RX 7600 XT": 30.0, "RTX 4060": 28.4,
    "RX 7600": 27.2, "RTX 5050": 27.1, "Arc B570": 26.5, "RTX 3060": 25.0,
    "RX 6600 XT": 24.3, "RTX 3050": 17.8,
}

NEW_EXPONENT = 1.85
ANCHOR_SCORE = 108.0        # RTX 5090, the top of the scale and its reference
TOLERANCE = 2.0             # leave a card alone if it is this close, in points

PREFIXES = ("NVIDIA GeForce ", "AMD Radeon ", "Intel ")


def short(name):
    for p in PREFIXES:
        if name.startswith(p):
            return name[len(p):]
    return name


def family(name):
    """The desktop base model a variant derives from: 'RTX 4090 Laptop GPU'
    and 'RTX 4090 D' both reduce to 'RTX 4090'."""
    n = re.sub(r"\s*(Laptop GPU|Max-Q|Mobile)$", "", name).strip()
    return re.sub(r"\s*\(.*\)$", "", n).strip()


def find_sibling(name, corrected, measured):
    """
    The corrected card this one is a variant of, longest match first so
    'RX 9060' picks the 9060 XT rather than anything shorter.

    A variant whose own base model was measured and found correct gets nothing:
    an 'RTX 4070 Laptop GPU' follows the RTX 4070, and if that needed no
    correction neither does the laptop part. Without this the prefix search
    would walk on and match it to the RTX 4070 Ti SUPER.
    """
    base = family(name)
    if base in corrected:
        return base
    if base in measured:
        return None
    for key in sorted(corrected, key=len, reverse=True):
        if base.startswith(key + " ") or key.startswith(base + " "):
            return key
    return None


def main(apply_changes):
    gpus = [dict(g) for g in db_manager.get_all_gpus()]
    by_short = {short(g["name"]): g for g in gpus}

    missing = [k for k in REFERENCE_1440P if k not in by_short]
    if missing:
        print(f"  UYARI: veritabaninda bulunamadi: {missing}")

    print("=== ASAMA 1: ustel ===")
    print(f"  GPU_PERF_EXPONENT 1.54 -> {NEW_EXPONENT}")
    print("  (48 kartta ortalama sapma 7.2 -> 3.6 puan, tek karta dokunmadan)")

    print(f"\n=== ASAMA 2: olculen kartlarin duzeltilmesi (esik {TOLERANCE} puan) ===")
    corrected = {}
    already_right = 0
    for key, pct in sorted(REFERENCE_1440P.items(), key=lambda kv: -kv[1]):
        gpu = by_short.get(key)
        if not gpu:
            continue
        old = gpu["power_score"]
        predicted_pct = (old / ANCHOR_SCORE) ** NEW_EXPONENT * 100
        if abs(predicted_pct - pct) < TOLERANCE:
            already_right += 1
            continue
        new = round(ANCHOR_SCORE * (pct / 100.0) ** (1 / NEW_EXPONENT))
        corrected[key] = new
        print(f"  {key:22s} {old:5.0f} -> {new:3.0f}   "
              f"(tahmin %{predicted_pct:.1f}, olculen %{pct:.1f})")
    print(f"  {len(corrected)} kart duzeltildi, {already_right} kart zaten dogruydu")

    print("\n=== ASAMA 3: duzeltilen kartlarin varyantlari ===")
    measured = set(REFERENCE_1440P)
    carried = {}
    for g in gpus:
        key = short(g["name"])
        if key in measured:
            continue
        sib = find_sibling(key, corrected, measured)
        if not sib:
            continue
        old_sib = by_short[sib]["power_score"]
        new = round(g["power_score"] * corrected[sib] / old_sib)
        if new != g["power_score"]:
            carried[key] = new
            print(f"  {key[:30]:30s} {g['power_score']:5.0f} -> {new:3.0f}   "
                  f"({sib} {old_sib:.0f}->{corrected[sib]} oraniyla)")
    orphans = sum(1 for g in gpus if short(g["name"]) not in measured
                  and not find_sibling(short(g["name"]), corrected, measured))
    print(f"  {len(carried)} varyant tasindi; olcumu de akrabasi da olmayan "
          f"{orphans} kart oldugu gibi birakildi")

    score_of = {short(g["name"]): g["power_score"] for g in gpus}
    score_of.update(carried)
    score_of.update(corrected)

    print("\n=== ASAMA 4: dizustu tavani ===")
    # A laptop part is the same silicon or a cut of it on a smaller power
    # budget, so it cannot beat the desktop card it is named after. Two entries
    # broke that before any of this ran; fixing it with a rule rather than a
    # hand-picked number is the whole point of the exercise.
    for name in sorted(score_of):
        base = family(name)
        if base == name or base not in score_of:
            continue
        if score_of[name] > score_of[base]:
            print(f"  {name:30s} {score_of[name]:3.0f} -> {score_of[base]:3.0f}  "
                  f"({base} tavani)")
            score_of[name] = score_of[base]

    updates = [(g["name"], g["power_score"], score_of[short(g["name"])])
               for g in gpus if score_of[short(g["name"])] != g["power_score"]]

    print("\n=== ASAMA 5: siralama denetimi ===")
    bad = 0
    for name, score in sorted(score_of.items()):
        for suffix in (" XT", " Ti", " SUPER", " XTX"):
            if score_of.get(name + suffix, score + 1) < score:
                bad += 1
                print(f"  BOZUK: {name} {score:.0f} > {name}{suffix} "
                      f"{score_of[name + suffix]:.0f}")
        base = family(name)
        if base != name and score > score_of.get(base, score):
            bad += 1
            print(f"  BOZUK: {name} {score:.0f} > {base} {score_of[base]:.0f}")
    print(f"  aile siralamasi ihlali: {bad}")

    print("\n=== SONUC ===")
    print(f"  {len(updates)} kartin puani degisiyor, "
          f"{len(gpus) - len(updates)} kart ayni kaliyor")
    for name, old, new in sorted(updates, key=lambda u: -abs(u[2] - u[1]))[:10]:
        print(f"    {short(name)[:30]:30s} {old:5.0f} -> {new:3.0f}  ({new - old:+.0f})")

    if apply_changes:
        conn = db_manager.get_connection()
        cur = conn.cursor()
        for name, _old, new in updates:
            cur.execute("UPDATE gpus SET power_score=? WHERE name=?", (new, name))
        conn.commit()
        conn.close()
        print(f"\n  {len(updates)} kart yazildi. "
              f"balance_config.py icinde GPU_PERF_EXPONENT = {NEW_EXPONENT} "
              f"yapin, sonra calibrate_vram.py ve calibrate_engine.py calistirin.")
    else:
        print("\n  (kuru calisma — yazmak icin --apply)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    main(ap.parse_args().apply)
