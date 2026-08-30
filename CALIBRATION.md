# Cadence — calibration log

Working notes on how accurate the FPS engine currently is, what has been
fitted against real measurements, and what to measure next. Update this as
new benchmark batches land so the work can be picked up without re-deriving
context.

## Current standing

| Metric | Value |
|---|---|
| Engine | Cadence 1.0 |
| Measurements in `benchmarks` table | 508 (480 fitted, 28 held out) |
| Mean absolute error | **6.6%** fitted, **22.5%** on the held-out set |
| Systematic bias | −0.8% fitted, **+17.4%** held out |
| Within 10% of measured | 79% |
| Within 20% of measured | 93% |

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

Open items. All are visible in the validation output; none are hidden.

**Model**

1. **One ray-tracing flag, several presets per game.** Forza Horizon 6 on an
   RTX 3080 Ti at 1440p reads 85 fps at High RT and 40 at Extreme; the engine
   answers 56 to both, 34% low on one and 40% high on the other.
   `benchmarks.rt_level` records the preset and the calibration holds Extreme
   rows out, so `RT_GPU_COST_MULT` means a *typical* preset. Real RT levels
   need an RT sweep on a second game.
2. **Frame generation is the weakest part, 18.5% against 6.2% on the base
   set.** The 3x and 4x steps come from one ladder, in one game, on one card.
   A second ladder is the whole fix.
3. **`PT_GPU_COST_MULT` rests on two rows.** Path tracing now fits at 6.6%,
   but only because everything that could not constrain it was excluded — what
   is left is Cyberpunk 2077's two rows. A second game measured both with and
   without path tracing would make it real.
4. **A processor's score does not capture how many threads a game wants.** The
   set holds one four-core chip, an i3-12100F, and the engine reads +11.9% high
   on it across thirteen games. The average hides the shape: against the
   i5-12400F one step up, whose score is only 1.13x higher, the measured gap is
   1.15x in Assetto Corsa Competizione and 1.17x in Remnant II, and 1.44x in
   Battlefield 6, 1.48x in Cyberpunk 2077, 1.82x in Star Wars Outlaws. Lowering
   the chip would break the first group, so this is a per-game property, not a
   scoring error. Not fitted, because one processor cannot fit a per-game
   property; 35 of the 222 CPUs are affected and the estimate carries a note.
   A second four-core chip makes it modellable.
5. **Ray Reconstruction is not modelled.** The one measurement using it is
   recorded as RT + DLSS Quality.
6. **Far Cry 6's optional HD texture pack is not modelled**, and neither is
   Space Marine 2's. Needs a per-game flag rather than being folded into the
   base cost.
7. **Alan Wake 2 at 8K exhausts VRAM on a 32 GB card** — measured, ~4 GB
   spilling to system RAM. The engine predicts 14 fps against 10.

**Coverage**

8. **We do not know how the engine behaves on pre-2019 GPUs.** 79 of the 164
   catalogue cards are on architectures with no measurement at all. Five
   outside systems put the engine +110% high, which looked like a clean
   architectural cliff; a sixth broke it — the GTX 1080 Ti is the same Pascal
   generation as the GTX 1070 that read +153%, and across ten current games it
   comes to +8%. VRAM was the next hypothesis and chasing it found a real bug
   (see Closed 6) but moved the low-end rates by 1.7 points out of 110. The
   engine applies no correction and says the card is outside what has been
   measured — no direction, no magnitude, because the evidence supports
   neither.
9. **Every one of the 492 measurements is on desktop hardware.** Laptop
   predictions are entirely unvalidated. Related: the catalogue holds no Apple
   GPU, so every pairing offered for an M-series chip is wrong.
10. **The engine predicts a benchmark-loop average and free play runs well
   below it — far enough that the displayed range does not cover it.** This is
   the largest open problem in the model and the only one a reader would notice
   unprompted.
   The held-out set now holds 25 rows, and splits by whether the engine flags
   the hardware. Twelve on a GTX 1080 Ti read 22.4% error at +10.7% bias.
   Thirteen on RTX 5080 and 5090 systems — modern, nothing flagged — read 18.2%
   at **+18.2%**: mean absolute error and bias are the same number, so every
   single row is over-predicted. Not scatter. A definition.
   It is worse at low resolution, where the CPU binds: Red Dead Redemption 2 on
   an RTX 5090 reads +7.1% at 8K, +23.6% at 4K, +33.3% at 1440p and +42.0% at
   1080p. And the range does not rescue it — only 5 of those 13 free-play
   averages fall between the predicted 1% low and the predicted average, so a
   reader is shown a band their machine sits underneath.
   No correction is applied. 25 rows across three games and two systems is not
   enough to move every prediction, and applying a blanket shift would break
   the relationship with the 480 benchmark rows the model is fitted to. What
   settles it is more held-out gameplay: different games, different hardware,
   ideally one game measured both ways on the same machine.
10b. **One cost per game cannot describe a game whose areas differ this much.**
   Baldur's Gate 3 on one machine, at one preset: the engine reads -11.5% and
   -12.6% in Act 1 and +22.6%, +43.6% and +57.1% in Act 3's Lower City. The
   sign of the error flips with where the player is standing, because Act 1
   runs at 200 fps at 1080p where Act 3 runs at 55 at 4K. The four rows the
   profile was fitted from came from somewhere lighter, so it describes that.
   No amount of further measurement fixes this without a per-area notion the
   model does not have, and adding one would need per-area measurements for
   every affected title. Worth separating from gap 10: this is a *level* that
   moves with location, where Red Dead Redemption 2 showed the *ratio* does
   not.
11. **147 of the 176 games carry derived cost profiles**, and 148 have never
   had their feature flags checked in-game. The interface marks both.
12. **162 games use the global 0.762 for the 1% low ratio** rather than their
   own; fourteen are measured. Kingdom Come: Deliverance 2 was the case that
   prompted this, on a relayed claim of a 30-40% drop in Kuttenberg. Measured,
   it is 0.874 — a 13% drop, putting it among the steadiest games in the set
   next to Hitman 3. The claim is not refuted though: the video holds no city
   measurements, only rural and indoor, so what is recorded is the ratio
   *outside* Kuttenberg. If the city really does drop 30-40%, that is a
   per-location effect one ratio per game cannot express.
   Red Dead Redemption 2 then tested the location idea directly, on the
   best-known CPU-heavy city in any open world we hold: Saint Denis reads 0.792
   across three rows against 0.798 for its rural and forest scenes. No
   difference. Not proof for every game, but the first real evidence, from the
   title where the effect should have been easiest to see.
   Baldur's Gate 3 lands at 0.707 — beside The Last of Us Part I rather than at
   the bottom of the range, which is where a game with Act 3's reputation was
   expected. Its Act 1 rows were both discarded (one at 0.980, one at 0.409),
   so what is recorded is Lower City's ratio and the act comparison could not
   be made.
   KCD2, RDR2 and BG3 are the only games whose ratios come from free gameplay
   rather than a benchmark loop. Nothing here can test whether the two differ, so
   calibrate_fps_low.py prints the source per game instead of blending it out
   of sight.
13. **The X3D gap may be understated.** Scoring the Ryzen 7 5700X3D off the
   28-CPU ladder gives 60 against its 5800X3D sibling (a stable 0.93-0.96 ratio
   across eight games) but 65 against the non-X3D 5700X, because the ladder
   puts the 5800X3D 1.28x above the 5700X where their scores say 1.19x. The
   sibling answer is used and the disagreement recorded, because it is a
   question about the CPU scores rather than about that chip.

## Mistakes in method

Not gaps in the model — errors in how the work was done, found and corrected.
Kept because the same shapes keep recurring, and because a log of what went
wrong is worth more than a list of what works.

1. **Counting rows instead of configurations.** `fit_game_costs` required two
   *rows* before fitting a game's CPU/GPU split, and its own docstring
   explained why one cannot separate them — but two rows of the same
   configuration cannot either. Grand Theft Auto V's four rows are a
   frame-generation ladder at one resolution on one machine, and the solver
   parked the cost in the CPU term: it implied a Ryzen 5 5600 could not exceed
   38 fps in a game that really runs past a hundred. `is_identifiable` now asks
   for variation in resolution, preset or CPU. Ceiling moved to 213 fps against
   125 measured on hardware the fit never saw.
2. **Measuring only on fast CPUs hid the class of error above.** 74 of the
   then-111 rows sat on an X3D chip, where the CPU term barely binds, so a
   wrong CPU cost changed no prediction and no check noticed. It took a single
   outside run on a Ryzen 5 5600 to expose it.
3. **Making the genre labels finer without updating the priors.** 19 of the 34
   labels then matched nothing and fell to the 1.0 default in silence — a value
   that reads as a judgement about sixty-odd games and was really an absent key.
   `check_genre_coverage()` now reports a gap instead of swallowing it.
4. **A test that stopped covering what it was pointed at, three times.** The
   conformance runner trims hardware rows to the fields the engines read.
   `architecture` was missing when the legacy-GPU note landed, so 4768 cases
   agreed perfectly while never entering the new branch; `form_factor` and
   `cores` repeated it. Each is now passed through, and each addition is
   checked by counting how many cases actually reach the branch.
5. **Callers trimming the same rows.** `predictAll` and the detail panel both
   cut hardware down to name/score/vram before calling the engine, so the
   legacy-GPU and laptop-mismatch notes could never have fired in the interface
   at all.
6. **Claiming a law from two videos.** "Pre-2019 architectures run +110% high"
   was asserted, committed, and then withdrawn when a GTX 1080 Ti came in at
   +8%. The retraction is in the history on purpose.
7. **Letting a large batch settle a question by headcount.** A 27-CPU ladder is
   27 observations of the CPU axis and one of everything else; counted flat it
   outvoted five rows from another source 27 to 5 on The Last of Us Part I,
   where the two read 208 and 123 fps on the same processor and preset.
   `config_weights` groups by everything except the CPU and weights 1/sqrt(n).
8. **Printing a boundary value as if it were a fit.** The frame-generation
   search kept landing on the edge of its own range. Widening it once was real
   — the error fell 26.0% to 21.9% — but widening again bought two tenths,
   which is a flat objective wandering. The script now says when a constant
   lands on a boundary.
9. **A circular multiplier fit.** Resident Evil Requiem has two rows, both
   path-traced and no others, so its unfitted cost leaked straight into
   `PT_GPU_COST_MULT`. Stage 3 had guarded against exactly this for ray tracing
   since early on; stage 2 never had the same rule. Worse, the guard was
   written into `fit_toggle`, a function nothing calls — dead code that looked
   like a fix for three iterations before anyone checked.
10. **A guard too strict in the other direction.** With the CPU:GPU ratio
   pinned to the genre prior there is one parameter to find and one row can
   find it, but the blanket "needs two rows" turned such games away. Resident
   Evil Requiem was shown as MEASURED · 2 while never being fitted at all, and
   the engine answered 16 fps against 40 recorded. Relaxing it then created a
   third bug — a one-row stage-1 fit kept Alan Wake 2 out of a later pass that
   had six rows for it, sending its held-out row to +253% — so weakly fitted
   games are now reconsidered in that pass.
11. **A mislabelled measurement, found by a flag fix.** Setting Far Cry 6's
   `supports_dlss` to 0 made the contradiction scan report two of its own rows
   as using DLAA, which only exists where DLSS does. The rows were wrong: a
   source's temporal AA had been recorded as DLAA, and in this model that costs
   an upscaling pass where Native does not.
12. **An API key committed and then deleted.** Deleting a file does not remove
   it from git history, and the repository is public. Revoking the key is the
   only fix; the file removal was not one.

## Closed

1. ~~Forza Horizon 6 has internally inconsistent measurements.~~ Three RTX 5080
   rows described the *same* configuration as 260, 152 and 89 fps. A second
   source settled it: an RTX 3080 Ti run scaled by the score ratio predicts
   159 / 130 / 87 against 175 / 133 / 89 recorded, so 89 stands and the other
   two were removed.
2. ~~GPU `power_score` was never validated.~~ The ladder was systematically
   compressed — all 48 cards checked came out too fast relative to an RTX 5090.
   118 of the 164 still carry unvalidated scores but no longer share that
   error.
3. ~~CPU `power_score` was never validated.~~ Rebuilt as a 1080p gaming index.
   195 of the 222 are modelled rather than measured, and the model's own error
   against the reference is 3.4 points.
4. ~~`CPU_PERF_EXPONENT` was set on principle, not measurement.~~ Two ladders
   settle it at exactly 1.00. Fitting needs each game's level divided out
   first, or a wrong game cost masquerades as a wrong curve — raw, the scan
   runs to 1.60. The first ladder, reaching score 46, put the optimum at 1.10;
   a second reaching 30 moved it to 1.00 at 5.32% shape error across 369 rows.
   More measurement converged the answer rather than moving it.
5. ~~The estimate was a single number.~~ It is a range now, and the range is
   measured: across 336 rows the ratio of 1% low to average is a property of
   the *game*, flat between 0.744 and 0.772 across CPU scores from 50 to 100
   but running 0.533 in Counter-Strike 2 to 0.878 in Hitman 3.
6. ~~VRAM working sets were about 18% low.~~ Found by comparing against a GTX
   1080 Ti, whose 11 GB means nothing it reports is clamped. On an 8 GB card
   the model saw 4 of 12 current games spilling where 7 really do. Now −8.4%
   and 8 of 12.
7. ~~Desktop and laptop parts could be mixed.~~ Nothing recorded which was
   which. `form_factor` does now and the interface asks the machine type before
   the pickers, so the pairing cannot be made.
8. ~~One benchmark row looked wrong.~~ The Cyberpunk RTX 4070 row was
   re-measured at 65 fps, not 52.

## Next measurements needed

In order of what each would actually settle. The first three are the ones
holding the model back; the rest widen coverage.

1. **A frame-generation ladder on a second game** — off, 2x, 3x and 4x, same
   game, same card, same settings. Four numbers. The 3x and 4x steps currently
   come from Grand Theft Auto V Enhanced alone, which is why those rows sit at
   18.5% while the base set is at 6.2% (gap 2).
2. **1% low figures for the sixteen measured games that lack them** — Forza
   Horizon 5 and 6, Alan Wake 2, The Last of Us Part II, Red Dead Redemption 2,
   Valorant, Baldur's Gate 3, Kingdom Come: Deliverance 2, Grand Theft Auto V
   Enhanced, Starfield, Microsoft Flight Simulator, Elden Ring, Far Cry 6,
   Cities: Skylines II, Black Myth: Wukong, Resident Evil Requiem. The ratio is
   a property of the game and flat across processors, so **one reliable 1080p
   chart per game is enough** — matching hardware is not needed (gap 12).
3. **A second four-core processor in any CPU ladder** — an i3-13100F,
   i3-14100F or Ryzen 3 4100. One more chip turns the thread-demand effect from
   something we can only warn about into something we can fit (gap 4).

Then:

4. **A path-traced game other than Cyberpunk 2077, measured both with and
   without** — `PT_GPU_COST_MULT` is fitted from two rows (gap 3).
5. **A ray-tracing sweep on a second game**, ideally Cyberpunk's
   Low/Medium/High/Ultra/Overdrive, to make RT levels modellable (gap 1).
6. **Anything at all on modern hardware that we hold out of the fit.** The
   entire held-out set is one GTX 1080 Ti, which the engine already flags as
   outside its validated range, so it cannot separate "does the model
   generalise" from "does it handle Pascal" (gap 10).
7. **Far Cry 6 without the HD texture pack**, to separate the pack from the
   base game (gap 6).
8. **Microsoft Flight Simulator 2024 at three resolutions.** Its costs are
   openly a guess — derived from the 2020 profile plus an uplift.
9. **More of the 147 uncalibrated games**, prioritising genres not yet
   represented.

Record with every measurement: resolution, preset, ray-tracing state *and
preset name*, upscaling mode, frame-generation mode, RAM amount, VRAM reading
with whether it is allocated or used, whether the run is a benchmark loop or
free gameplay, and the source with a timestamp. GPU utilisation below ~85%
indicates a CPU limit and is worth noting.

The prompt that produces this from a video's AI summary is worth reusing; each
of its requirements exists because something was lost without it.

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
