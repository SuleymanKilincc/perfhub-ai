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
| Mean absolute error | **9.8%** (44.8% before any calibration) |
| Systematic bias | −1.3% |
| Within 10% of measured | 65% |
| Within 20% of measured | 85% |

The set now covers resolution sweeps, GPU and CPU ladders, preset ladders,
ray tracing and path tracing, a full frame-generation ladder, 8K, and
8GB-vs-16GB pairs of the same GPU.

Run `python scripts/validate_engine.py` to reproduce.

## Fitted constants

Fitted in `core/balance_config.py` from the batches noted below.

| Constant | Before | After | Fitted from |
|---|---|---|---|
| `RES_PIXEL_EXPONENT` | 0.78 | 0.82 | resolution sweeps |
| `GPU_PERF_EXPONENT` | 1.40 | 1.54 | GPU ladder |
| `CPU_PERF_EXPONENT` | 1.00 | 0.60 | CPU ladder |
| `CPU_MS_CONST` | 2.65 | 2.25 | CPU ladder |
| `VRAM_SPILL_SEVERITY` | 2.6 | 0.50 | 8GB vs 16GB pairs |
| `VRAM_SPILL_FLOOR` | 0.22 | 0.80 | 8GB vs 16GB pairs |
| `RT_GPU_COST_MULT` | 1.80 | 1.34 | games measured RT on and off |
| `PT_GPU_COST_MULT` | 3.10 | 2.62 | Alan Wake 2 with and without PT |
| `FG_GPU_OVERHEAD` | .22/.31/.38 | .60/.72/.84 | GTA V Enhanced 2x/3x/4x ladder |

Two findings worth remembering:

- **Gaming CPU performance is far more compressed than `power_score`
  suggests.** A 7800X3D and an i5-14600K are ~13% apart in CS2, not the gap
  their scores imply. Hence the sub-1.0 exponent.
- **VRAM overflow does not collapse modern games.** Measured 8GB-vs-16GB
  ratios on the same RTX 4060 Ti ranged 0.38–0.95; the first model predicted
  0.29 where reality was 0.95. Engines drop texture streaming quality instead
  of falling over.

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

## Known gaps

Visible in the validation output; none of these are hidden.

1. **Far Cry 6's optional HD texture pack is not modelled.** Published figures
   put it near 11-12 GB at 1440p where the base game sits far lower, and it is
   the single worst prediction in the set. Needs a per-game flag.
2. **Forza Horizon 6 has internally inconsistent measurements.** An RTX 2060
   at 1080p Ultra gives 40 fps and an RTX 5080 gives 175 — a 4.38x gap, where
   the score scale only permits 3.63x. Either the two runs differ in scene or
   version, or the GPU scores themselves are wrong at the low end.
3. **GPU `power_score` values have never been validated.** They are hand
   assigned, and `GPU_PERF_EXPONENT` is partly compensating for that. Gap 2 is
   the first concrete symptom.
4. **Alan Wake 2 at 8K runs out of VRAM on a 32 GB card** — measured, with
   ~4 GB spilling to system RAM. The engine predicts 18 fps against 10.
5. **Ray Reconstruction is not modelled**; the one measurement using it is
   recorded as RT + DLSS Quality.
6. **~157 games remain uncalibrated.** The plan is to derive genre-level
   corrections from the calibrated twenty rather than measure every title.

## Next measurements needed

The most valuable shape remains **one game, one system, three resolutions** —
it is the only thing that separates a game's CPU cost from its GPU cost.

- **Far Cry 6 without the HD texture pack**, to separate the pack's cost from
  the base game.
- **Forza Horizon 6 re-run** on a mid-range card to resolve gap 2.
- **A GPU ladder at a fixed setting** spanning weak to strong cards, to
  validate `power_score` directly rather than through an exponent.
- More games from the uncalibrated ~157, prioritising ones whose genre is not
  yet represented.

Record with every measurement: resolution, preset, ray tracing state,
upscaling mode, frame generation mode, RAM amount, VRAM reading if the overlay
shows one, and the source. GPU utilisation below ~85% indicates a CPU limit
and is worth noting.

## Tools

```bash
python scripts/validate_engine.py        # report accuracy against measurements
python scripts/validate_engine.py --add  # record one measurement interactively
python scripts/calibrate_engine.py       # fit costs and multipliers (dry run)
python scripts/calibrate_engine.py --apply
python scripts/calibrate_vram.py --apply # fit VRAM working sets
python scripts/load_benchmarks.py        # bulk-load batch 1
python scripts/load_benchmarks_2.py      # bulk-load batch 2
```

Order matters: VRAM working sets and cost profiles are coupled, because a
spurious VRAM penalty gets absorbed into a game's fitted cost. Run
`calibrate_vram.py --apply` first, then `calibrate_engine.py --apply`.
