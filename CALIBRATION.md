# Cadence — calibration log

Working notes on how accurate the FPS engine currently is, what has been
fitted against real measurements, and what to measure next. Update this as
new benchmark batches land so the work can be picked up without re-deriving
context.

## Current standing

| Metric | Value |
|---|---|
| Engine | Cadence 1.0 |
| Measurements in `benchmarks` table | 111 |
| Mean absolute error | **9.1%** (44.8% before any calibration) |
| Systematic bias | −1.3% |
| Within 10% of measured | 69% |
| Within 20% of measured | 86% |

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
| `CPU_PERF_EXPONENT` | 0.60 | 1.00 | definition, once the scores meant gaming |
| `CPU_MS_CONST` | 2.65 | 2.25 | CPU ladder |
| `VRAM_SPILL_SEVERITY` | 2.6 | 0.50 | 8GB vs 16GB pairs |
| `VRAM_SPILL_FLOOR` | 0.22 | 0.80 | 8GB vs 16GB pairs |
| `RT_GPU_COST_MULT` | 1.80 | 1.68 | RT on/off pairs, Extreme presets held out |
| `PT_GPU_COST_MULT` | 3.10 | 3.30 | Alan Wake 2 and Cyberpunk, PT on and off |
| `FG_GPU_OVERHEAD` | .22/.31/.38 | .35/.55/.75 | GTA V Enhanced 2x/3x/4x ladder |

Three findings worth remembering:

- **The CPU scores were measuring the wrong thing.** They ranked all-core
  throughput, and the sub-1.0 exponent existed to flatten the damage. Both are
  fixed; see the CPU section below.
- **VRAM overflow does not collapse modern games.** Measured 8GB-vs-16GB
  ratios on the same RTX 4060 Ti ranged 0.38–0.95; the first model predicted
  0.29 where reality was 0.95. Engines drop texture streaming quality instead
  of falling over.
- **The GPU ladder was compressed, not noisy.** Checked against a published
  1440p hierarchy, all 48 covered cards were predicted *too fast* relative to
  the RTX 5090 — a one-sided error, which is a scale problem rather than a
  per-card one. See the section below.

## Games with calibrated cost profiles

Twenty-one of the catalog's 175 games now have `gpu_cost`, `cpu_cost` and
`vram_base_gb` fitted to measurements. The remaining ~154 still carry values
derived from the old model's hand-tuned scalings, or in one case an openly
stated guess, and should be treated as rough — the accuracy figure above applies to the measured set, not to the
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

## CPU power_score

The same check applied to the CPUs found a worse problem. Against a published
1080p gaming hierarchy the mean error was 13.3 points, against the GPUs' 7.2 —
and unlike the GPUs the errors were not just large but *out of order*. A Core
Ultra 9 285K scored 96 and a Ryzen 7 9800X3D scored 95, when in games the 285K
is well behind it. The values ranked all-core throughput, which is not what
this engine ever asks them for.

Two causes, both measurable in the residuals: score rose with core count
(+0.68 points per core, 6-core chips +6.2 out, 24-core +20.3) and 3D V-Cache
was not credited (X3D parts +6.7, everything else +16.9).

An exponent cannot repair an ordering, so `scripts/calibrate_cpu_scores.py`
rebuilds the scores. Twenty-five come straight from the reference; the other
195 come from a model fitted to those 25:

```
index = K x IPC(architecture) x clock x X3D x (min(cores, 8) / 8)^0.25
```

Clock and the core term are pinned rather than fitted. Every CPU in the
reference runs between 4.4 and 5.7 GHz, so a free fit cannot see what clock
does — it lands on an exponent of 0.15, which would then score a 3.5 GHz chip
from 2016 as if clock were nearly free. Frame time is inversely proportional to
clock at fixed IPC, so 1.0 is both the physically right answer and the safe one
to extrapolate with. It costs accuracy in-sample (2.1 → 3.4 points) and buys
correctness out of it.

That leaves architecture IPC and the X3D multiplier to fit. The fit is
recognisable rather than arbitrary, which is the reassuring part: the X3D
multiplier came out at 1.23x against the 15-25% gaming uplift 3D V-Cache is
known for, and Arrow Lake landed below Raptor Lake on IPC, which is exactly its
reputation. Six architectures are covered by the reference; the rest are
chained off the two fitted anchors using published generational IPC steps and
are marked as estimates in `ARCH_IPC`.

`CPU_PERF_EXPONENT` goes 0.60 → 1.00. The score is now a gaming index, so it is
already proportional to frame rate and needs no curve — 1.0 is the definition
rather than a fit. The benchmark set cannot argue either way here: a nested
refit across exponents from 0.45 to 1.20 moves the total error by half a point,
because 74 of the 104 measurements use a 7800X3D or a 9800X3D and nothing below
a 5700X was ever measured.

Two consequences elsewhere, both of which were live bugs the moment the scores
changed meaning:

- `scoring_engine` multiplied X3D chips by 1.18 "because power_score doesn't
  carry it". It does now, so that was counting it twice. Removed.
- `db_manager.fix_power_scores()` overwrote scores with hand-written values
  keyed to Cinebench R23 multi-core — the very metric that caused this. It ran
  from the module's `__main__` block, so anyone initialising the database would
  have silently undone the calibration. Removed.

**This did not improve the benchmark error, and could not have.** It stayed at
9.0%, because the measurement set has almost no CPU diversity to exercise. The
change shows up in the catalogue instead. Counter-Strike 2, 1080p Low, RTX 4090:

| CPU | score | before | after |
|---|---|---|---|
| Ryzen 7 9800X3D | 95 → 97 | 909 | 954 |
| Core Ultra 9 285K | 96 → 72 | 837 | 627 |
| Ryzen 7 5800X3D | 74 → 63 | 794 | 647 |
| Ryzen 9 5950X | 82 → 56 | 767 | 490 |

The 285K sat 8% behind the 9800X3D and is now 34% behind, which is roughly
where it actually sits. The 5950X, a 16-core productivity part, is no longer
presented as near-flagship for gaming.

## Known gaps

Visible in the validation output; none of these are hidden.

1. **Far Cry 6's optional HD texture pack is not modelled.** Published figures
   put it near 11-12 GB at 1440p where the base game sits far lower, and it is
   the single worst prediction in the set. Needs a per-game flag.
2. ~~Forza Horizon 6 has internally inconsistent measurements.~~ **Resolved
   twice.** The GPU score correction fixed the 4.38x gap the old scale could
   not reach. The rest was worse than inconsistent: three RTX 5080 rows
   described the *same* configuration — 4K Ultra, DLAA, no ray tracing — as
   260, 152 and 89 fps. A second source settled it. An RTX 3080 Ti run scaled
   by the score ratio (1.45x) predicts 159 / 130 / 87 at 1080p / 1440p / 4K
   against 175 / 133 / 89 recorded, so the 89 stands and the other two were
   removed. See scripts/load_benchmarks_3.py.
3. ~~GPU `power_score` values have never been validated.~~ **Resolved**; see
   the section above. 118 of the 164 cards still carry unvalidated scores, but
   they are no longer subject to the systematic error.
4. **Alan Wake 2 at 8K runs out of VRAM on a 32 GB card** — measured, with
   ~4 GB spilling to system RAM. The engine predicts 19 fps against 10.
5. **Ray Reconstruction is not modelled**; the one measurement using it is
   recorded as RT + DLSS Quality.
5a. **Measuring only on fast CPUs hid a whole class of error.** 74 of the 111
   rows use an X3D chip, where the CPU term almost never binds, so a wrong CPU
   cost changes no prediction and no fit notices. A single outside run on a
   Ryzen 5 5600 exposed three games whose fitted CPU cost was nonsense — Grand
   Theft Auto V Enhanced implied that chip could not pass 38 fps, against 125
   observed. The cause was that `fit_game_costs` required two *rows* rather
   than two *distinct configurations*: GTA V's four rows are a frame-generation
   ladder at one resolution on one machine, and the solver was free to park the
   cost anywhere. `is_identifiable` now requires variation in resolution,
   preset or CPU before the split is fitted at all, and holds the ratio at the
   genre prior otherwise. GTA V's ceiling moved to 213 fps and the independent
   run agrees to within 1%. Cost: 0.2 points of fitted error, for three numbers
   the data never supported. The gap that remains is the measurement set, not
   the fit — weak CPUs are what it lacks.
5b. **The model has one ray-tracing flag where games ship several presets**,
   and the cost of that is now measured rather than suspected. Forza Horizon 6
   on an RTX 3080 Ti at 1440p reads 85 fps at High RT and 40 at Extreme; the
   engine answers 56 to both, so it is 34% low on one and 40% high on the
   other. `benchmarks.rt_level` records the preset from now on and the
   calibration holds Extreme rows out, so the multiplier means a *typical*
   preset. Building real RT levels needs more than the two rows that exist —
   an RT sweep on a second game would be the thing that makes it possible.
6. **~155 games remain uncalibrated.** The plan is to derive genre-level
   corrections from the calibrated twenty rather than measure every title.
7. **Frame generation is the weakest part of the model**, at 21.7% error over
   16 measurements against 9.0% overall. The Cyberpunk 4K DLSS Quality + 2x
   row predicts 174 against 123 measured.
8. ~~CPU `power_score` has not been validated.~~ **Resolved**; see the section
   above. 195 of the 220 are modelled rather than measured, and the model's own
   error against the reference is 3.4 points, so treat individual CPUs outside
   the reference 25 as estimates.
9. ~~One benchmark row looks wrong.~~ **Resolved.** The Cyberpunk RTX 4070 row
   was re-measured: 65 fps, not 52. The re-run also produced an RT Ultra and a
   path-traced figure with VRAM readings for all three, which is where
   `PT_GPU_COST_MULT` moved from 2.74 to 2.98 and Cyberpunk's VRAM working set
   from 6.8 to 4.8 GB. The engine still predicts all three of those rows 12-25%
   high, so the 4070 is not fully settled — but it is no longer inverted
   against the cards around it.

## Next measurements needed

The most valuable shape remains **one game, one system, three resolutions** —
it is the only thing that separates a game's CPU cost from its GPU cost.

- **Far Cry 6 without the HD texture pack**, to separate the pack's cost from
  the base game.
- **Microsoft Flight Simulator 2024**, which is in the catalogue with costs
  that are openly a guess. They were derived from the calibrated 2020 profile
  plus an uplift, because 2024 is a separate and much heavier game that was
  missing entirely — the catalogue instead had the 2020 release listed twice,
  once under each of its names. One run at three resolutions settles it.
- **A frame generation ladder on a second game**, for gap 7 — the overhead is
  currently fitted from GTA V Enhanced alone.
- **A CPU ladder at 1080p on a CPU-bound game, reaching the low end** — a
  Ryzen 5 5600 or an i5-12400F alongside one of the X3D chips already measured.
  This is the single most valuable CPU measurement: 74 of the 104 rows use a
  7800X3D or a 9800X3D, which is why `CPU_PERF_EXPONENT` had to be chosen on
  principle rather than fitted.
- **Older cards at a fixed setting** — a GTX 1660 Super, RTX 2060 or RX 580
  against a card in the reference set. The score correction above stops at the
  RTX 3050 because no data reaches below it.
- More games from the uncalibrated ~155, prioritising ones whose genre is not
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
python scripts/calibrate_cpu_scores.py     # rebuild CPU scores as a gaming index
python scripts/calibrate_cpu_scores.py --apply
python scripts/calibrate_vram.py --apply   # fit VRAM working sets
python scripts/calibrate_engine.py         # fit costs and multipliers (dry run)
python scripts/calibrate_engine.py --apply
python scripts/load_benchmarks.py          # bulk-load batch 1
python scripts/load_benchmarks_2.py        # bulk-load batch 2
python scripts/load_benchmarks_3.py        # bulk-load batch 3

python scripts/curate_games.py --apply     # catalogue hygiene: junk, genres, targets
python scripts/export_engine_data.py       # push constants + catalogue to the web build
python scripts/conformance_test.py         # prove Python and TypeScript agree
```

**Any calibration change has to end with the last two.** The website runs its
own copy of the engine in TypeScript so a prediction needs no server; the
exporter regenerates the constants and catalogue it uses, and the conformance
test runs both implementations over ~25,000 cases and fails on any
disagreement. Skip the exporter and the site keeps predicting with the numbers
it was built with, silently.

Order matters, and it is the order above. Hardware scores come first because
everything else is fitted relative to them. VRAM working sets come before cost
profiles, because a spurious VRAM penalty gets absorbed into a game's fitted
cost — running them the other way round cost 1.8 points of accuracy once.
`calibrate_engine.py` prints three constants that have to be copied into
`balance_config.py` by hand; it only writes the per-game profiles.
