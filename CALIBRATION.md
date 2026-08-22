# Cadence — calibration log

Working notes on how accurate the FPS engine currently is, what has been
fitted against real measurements, and what to measure next. Update this as
new benchmark batches land so the work can be picked up without re-deriving
context.

## Current standing

| Metric | Value |
|---|---|
| Engine | Cadence 1.0 |
| Measurements in `benchmarks` table | 55 |
| Mean absolute error | **13.9%** (was 44.8% before calibration) |
| Systematic bias | +1.9% (was −19.2%, uniformly pessimistic) |
| Within 20% of measured | 76% (was 24%) |

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

Two findings worth remembering:

- **Gaming CPU performance is far more compressed than `power_score`
  suggests.** A 7800X3D and an i5-14600K are ~13% apart in CS2, not the gap
  their scores imply. Hence the sub-1.0 exponent.
- **VRAM overflow does not collapse modern games.** Measured 8GB-vs-16GB
  ratios on the same RTX 4060 Ti ranged 0.38–0.95; the first model predicted
  0.29 where reality was 0.95. Engines drop texture streaming quality instead
  of falling over.

## Games with calibrated cost profiles

Only these have `gpu_cost` / `cpu_cost` fitted to measurements. The other ~170
still use values derived from the old model's hand-tuned scalings and should
be treated as rough.

| Game | Fitted from |
|---|---|
| Cyberpunk 2077 | resolution sweep |
| Counter-Strike 2 | resolution sweep |
| Red Dead Redemption 2 | resolution sweep |
| Hogwarts Legacy | resolution sweep |
| Baldur's Gate 3 | resolution sweep |
| Forza Horizon 6 | preset ladder |
| The Last of Us Part II | preset ladder |

## Known gaps

Each of these is visible in the validation output — they are not hidden.

1. **VRAM base estimates are systematically too high.** They were derived from
   `difficulty_multiplier`, which conflates "expensive to render" with
   "hungry for memory". Research contradicts three of four games checked:

   | Game | Model says | Sources say |
   |---|---|---|
   | The Last of Us Part I | 14.1 GB @1440p Ultra | ~10–12 GB |
   | A Plague Tale: Requiem | 12.3 GB @1440p | ~5 GB |
   | Far Cry 6 (HD textures) | 6.0 GB @1440p | ~11–12 GB |

   The derivation formula needs rewriting once enough measured VRAM figures
   exist to fit it. Note the A Plague Tale case still validates the *shape* of
   the model: its measured 8GB-vs-16GB gap comes from RT and frame generation
   pushing a ~5 GB base over the 8 GB line, which is exactly what the model
   claims happens.

2. **Far Cry 6's optional HD texture pack is not modelled.** It roughly
   doubles VRAM demand. Needs either a per-game flag or a separate entry.

3. **Frame generation is over-predicted at 4K** (+45% on the one measurement
   available). Needs a 2x/3x/4x ladder on one system to fit.

4. **No frame rate cap support.** Elden Ring is locked to 60 fps; the engine
   happily predicts 200. A per-game `fps_cap` column is needed.

5. **Ray Reconstruction is not modelled** — the one measurement using it is
   recorded as RT + DLSS Quality and tagged `batch5-rayrecon`.

## Next measurements needed

Priority order. The single most valuable shape is **one game, one system,
three resolutions**, because that is the only thing that separates a game's
CPU cost from its GPU cost.

**Priority 1** — games already in the benchmark set but with uncalibrated
profiles: The Last of Us Part I, A Plague Tale: Requiem, Forza Horizon 5.
Ultra, no RT, no upscaling, at 1080p / 1440p / 4K.

**Priority 2** — spread across behaviour types: Alan Wake 2 and Black Myth
Wukong (path tracing), Starfield and Cities: Skylines II and MSFS
(CPU-bound), Valorant (extreme high frame rate), Resident Evil 4 (aggressive
VRAM settings), Elden Ring (frame cap confirmation only).

**Priority 3** — frame generation ladder: one system, one game, off / 2x / 3x
/ 4x. Needs an RTX 50 series card for 3x and 4x.

Record with every measurement: resolution, preset, ray tracing state,
upscaling mode, RAM amount, and the source. GPU utilisation percentage is
valuable when the overlay shows it — below ~85% indicates a CPU limit.

## Tools

```bash
python scripts/validate_engine.py        # report accuracy against measurements
python scripts/validate_engine.py --add  # record one measurement interactively
python scripts/calibrate_engine.py       # fit constants (dry run)
python scripts/calibrate_engine.py --apply
python scripts/load_benchmarks.py        # bulk-load a recorded batch
```
