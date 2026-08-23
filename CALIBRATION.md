# Cadence — calibration log

Working notes on how accurate the FPS engine currently is, what has been
fitted against real measurements, and what to measure next. Update this as
new benchmark batches land so the work can be picked up without re-deriving
context.

## Current standing

| Metric | Value |
|---|---|
| Engine | Cadence 1.0 |
| Measurements in `benchmarks` table | 104 |
| Mean absolute error | **9.0%** (44.8% before any calibration) |
| Systematic bias | −1.2% |
| Within 10% of measured | 70% |
| Within 20% of measured | 84% |

The set now covers resolution sweeps, GPU and CPU ladders, preset ladders,
ray tracing and path tracing, a full frame-generation ladder, 8K, and
8GB-vs-16GB pairs of the same GPU.

Run `python scripts/validate_engine.py` to reproduce.

## Fitted constants

Fitted in `core/balance_config.py` from the batches noted below.

| Constant | Before | After | Fitted from |
|---|---|---|---|
| `RES_PIXEL_EXPONENT` | 0.78 | 0.82 | resolution sweeps |
| `GPU_PERF_EXPONENT` | 1.40 | 1.85 | published 1440p hierarchy, 46 cards |
| `CPU_PERF_EXPONENT` | 1.00 | 0.60 | CPU ladder |
| `CPU_MS_CONST` | 2.65 | 2.25 | CPU ladder |
| `VRAM_SPILL_SEVERITY` | 2.6 | 0.50 | 8GB vs 16GB pairs |
| `VRAM_SPILL_FLOOR` | 0.22 | 0.80 | 8GB vs 16GB pairs |
| `RT_GPU_COST_MULT` | 1.80 | 1.62 | games measured RT on and off |
| `PT_GPU_COST_MULT` | 3.10 | 2.74 | Alan Wake 2 with and without PT |
| `FG_GPU_OVERHEAD` | .22/.31/.38 | .35/.53/.71 | GTA V Enhanced 2x/3x/4x ladder |

Three findings worth remembering:

- **Gaming CPU performance is far more compressed than `power_score`
  suggests.** A 7800X3D and an i5-14600K are ~13% apart in CS2, not the gap
  their scores imply. Hence the sub-1.0 exponent.
- **VRAM overflow does not collapse modern games.** Measured 8GB-vs-16GB
  ratios on the same RTX 4060 Ti ranged 0.38–0.95; the first model predicted
  0.29 where reality was 0.95. Engines drop texture streaming quality instead
  of falling over.
- **The GPU ladder was compressed, not noisy.** Checked against a published
  1440p hierarchy, all 48 covered cards were predicted *too fast* relative to
  the RTX 5090 — a one-sided error, which is a scale problem rather than a
  per-card one. See the section below.

## Games with calibrated cost profiles

Twenty of the catalog's 177 games now have `gpu_cost`, `cpu_cost` and
`vram_base_gb` fitted to measurements. The remaining ~157 still carry values
derived from the old model's hand-tuned scalings and should be treated as
rough — the accuracy figure above applies to the measured set, not to the
whole catalog.

A Plague Tale: Requiem · Alan Wake 2 · Baldur's Gate 3 · Black Myth: Wukong ·
Cities: Skylines II · Counter-Strike 2 · Cyberpunk 2077 · Elden Ring ·
Far Cry 6 · Forza Horizon 5 · Forza Horizon 6 · Grand Theft Auto V Enhanced ·
Hogwarts Legacy · Kingdom Come: Deliverance 2 · Microsoft Flight Simulator ·
Red Dead Redemption 2 · Resident Evil Requiem · Starfield ·
The Last of Us Part I & II · Valorant

## VRAM: working set vs allocation

Overlays report *allocated* memory, which is not what determines frame rate.
Engines cache into whatever VRAM is spare, so the reported figure partly
describes the card rather than the game — Alan Wake 2 reported 28 GB at 8K on
a 32 GB card.

The engine therefore tracks two numbers:

| | Answers | Drives |
|---|---|---|
| working set | "will the frame rate drop?" | the spill penalty |
| allocation | "will it stutter?" | the tight-VRAM warning |

`scripts/calibrate_vram.py` inverts measured allocations back into working
sets, discarding rows where the figure was clamped by the card's capacity.
That pass corrected the derived values substantially in both directions:
Starfield 11.3 → 4.3 GB, Alan Wake 2 13.4 → 6.8, The Last of Us Part I
10.3 → 6.3, while Forza Horizon 6 went the other way, 4.1 → 7.0.

Cross-check: the fitted 6.3 GB base for The Last of Us Part I predicts a
10.5 GB allocation at 1440p Ultra, against 10.2 GB measured.

## GPU power_score

The scores were hand assigned and had never been checked. Against a published
1440p hierarchy covering 48 of the 164 cards, every single one was predicted
too fast relative to the RTX 5090 — mean 7.2 points out, worst 17. A one-sided
error across every card is a compressed scale, not per-card noise.

The correction, in `scripts/calibrate_gpu_scores.py`, is in three parts:

| | What | Effect |
|---|---|---|
| 1 | `GPU_PERF_EXPONENT` 1.54 → 1.85 | 7.2 → 3.6 points, no card touched |
| 2 | solve the score for cards still >2 points out | 30 cards |
| 3 | carry the correction to variants of those cards | 14 cards, +2 laptop caps |

Splitting it this way matters. Rebuilding all 164 scores from the reference
would have meant extrapolating to the 57 cards weaker than an RTX 3050, which
the reference does not reach. The exponent is monotonic and applies to every
card safely; step 2 only touches cards with evidence. Cards with neither a
measurement nor a corrected sibling — GTX 10, RTX 20, Arc A, integrated — keep
their scores, because after step 1 the residuals are two-sided noise and noise
does not interpolate.

Two source rows were discarded: the reference puts the RX 6600 below an
RTX 3050 and the RX 6650 XT below an RX 6600 XT, both inverted. Its low end is
unreliable, its top is not.

Worth recording:

- **The RTX 4080 SUPER and RTX 5080 had the same score (97).** They are 6
  points apart in the reference.
- **RDNA 4 was scored far too high.** RX 9060 XT 16GB 75 → 66, 8GB 73 → 63.
- **Step 3 was the whole reason for step 2's caution.** Correcting the
  RX 9060 XT downwards left the plain RX 9060 above it.
- **Two laptop parts outranked their desktop namesake** (RTX 3060 and RTX 4060
  Laptop). A laptop part is the same silicon or a cut of it on a smaller power
  budget, so it is now capped at the desktop score by rule.

Independent confirmation: the Forza Horizon 6 contradiction logged as gap 2
below resolved itself. A measured RTX 2060 → RTX 5080 gap of 4.38x needed a
scale that only permitted 3.63x; the new one permits 4.44x. That anomaly was
recorded before this work started and the fix came from an unrelated source.

Overall effect on the benchmark set: 9.8% → 9.0% mean error, and predictions
within 10% of measured rose from 65% to 70%.

## Known gaps

Visible in the validation output; none of these are hidden.

1. **Far Cry 6's optional HD texture pack is not modelled.** Published figures
   put it near 11-12 GB at 1440p where the base game sits far lower, and it is
   the single worst prediction in the set. Needs a per-game flag.
2. ~~Forza Horizon 6 has internally inconsistent measurements.~~ **Resolved**
   by the GPU score correction above — the 4.38x gap the old scale could not
   reach now falls inside it.
3. ~~GPU `power_score` values have never been validated.~~ **Resolved**; see
   the section above. 118 of the 164 cards still carry unvalidated scores, but
   they are no longer subject to the systematic error.
4. **Alan Wake 2 at 8K runs out of VRAM on a 32 GB card** — measured, with
   ~4 GB spilling to system RAM. The engine predicts 19 fps against 10.
5. **Ray Reconstruction is not modelled**; the one measurement using it is
   recorded as RT + DLSS Quality.
6. **~157 games remain uncalibrated.** The plan is to derive genre-level
   corrections from the calibrated twenty rather than measure every title.
7. **Frame generation is the weakest part of the model**, at 21.7% error over
   16 measurements against 9.0% overall. The Cyberpunk 4K DLSS Quality + 2x
   row predicts 174 against 123 measured.
8. **CPU `power_score` has not been validated.** Same problem the GPU scores
   had, and `CPU_PERF_EXPONENT` at 0.60 is suspiciously far from linear —
   part of that is real (gaming CPU performance is compressed) and part may be
   the exponent absorbing bad scores, exactly as 1.54 was doing for the GPUs.
9. **One benchmark row looks wrong.** Cyberpunk 2077, 1440p Ultra native on an
   RTX 4070 is recorded at 52 fps, which puts it below an RX 9060 XT 16GB (67)
   and only 16% above an RTX 3060 Ti (45); the reference hierarchy puts the
   4070 above both, at 1.52x the 3060 Ti. It is now the third-worst prediction
   in the set. Worth re-checking the source before trusting it.

## Next measurements needed

The most valuable shape remains **one game, one system, three resolutions** —
it is the only thing that separates a game's CPU cost from its GPU cost.

- **Far Cry 6 without the HD texture pack**, to separate the pack's cost from
  the base game.
- **Cyberpunk 2077, 1440p Ultra native on an RTX 4070**, to settle gap 9.
- **A frame generation ladder on a second game**, for gap 7 — the overhead is
  currently fitted from GTA V Enhanced alone.
- **A CPU ladder at 1080p on a CPU-bound game**, to validate CPU scores the
  way the hierarchy validated the GPU ones.
- **Older cards at a fixed setting** — a GTX 1660 Super, RTX 2060 or RX 580
  against a card in the reference set. The score correction above stops at the
  RTX 3050 because no data reaches below it.
- More games from the uncalibrated ~157, prioritising ones whose genre is not
  yet represented.

Record with every measurement: resolution, preset, ray tracing state,
upscaling mode, frame generation mode, RAM amount, VRAM reading if the overlay
shows one, and the source. GPU utilisation below ~85% indicates a CPU limit
and is worth noting.

## Tools

```bash
python scripts/validate_engine.py          # report accuracy against measurements
python scripts/validate_engine.py --add    # record one measurement interactively
python scripts/calibrate_gpu_scores.py     # check GPU scores against reference
python scripts/calibrate_gpu_scores.py --apply
python scripts/calibrate_vram.py --apply   # fit VRAM working sets
python scripts/calibrate_engine.py         # fit costs and multipliers (dry run)
python scripts/calibrate_engine.py --apply
python scripts/load_benchmarks.py          # bulk-load batch 1
python scripts/load_benchmarks_2.py        # bulk-load batch 2
```

Order matters, and it is the order above. Hardware scores come first because
everything else is fitted relative to them. VRAM working sets come before cost
profiles, because a spurious VRAM penalty gets absorbed into a game's fitted
cost — running them the other way round cost 1.8 points of accuracy once.
`calibrate_engine.py` prints three constants that have to be copied into
`balance_config.py` by hand; it only writes the per-game profiles.
