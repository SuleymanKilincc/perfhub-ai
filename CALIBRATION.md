# Cadence — calibration log

Working notes on how accurate the FPS engine currently is, what has been
fitted against real measurements, and what to measure next. Update this as
new benchmark batches land so the work can be picked up without re-deriving
context.

## Current standing

| Metric | Value |
|---|---|
| Engine | Cadence 1.0 |
| Measurements in `benchmarks` table | 577 (491 fitted, 86 held out) |
| Mean absolute error | **6.9%** fitted, **32.0%** gameplay, **44.3%** texture-pack, **16.9%** ray-reconstruction |
| Systematic bias | +0.1% fitted, +13.3% gameplay |
| Derived profiles, leave-one-game-out | **51.5%** per game, against 6.5% for the same games fitted |
| Within 10% of measured | 80% |
| Within 20% of measured | 94% |
| Run-to-run noise | **1.1%** (one repeated configuration) |

The noise figure is new and it bounds everything above it. Cyberpunk 2077's
internal benchmark was run twice at one setting and returned 58.67 and 59.30.
No difference smaller than about a percent anywhere in this document is a
result.

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
| `RT_GPU_COST_MULT` | 1.80 | 1.70 | 7 RT on/off pairs, Extreme presets held out |
| `PT_GPU_COST_MULT` | 3.10 | 3.54 | 2 rows, both Cyberpunk 2077, PT on and off |
| `FG_GPU_OVERHEAD` | .22/.31/.38 | .40/.76/1.12 | GTA V Enhanced 2x/3x/4x ladder |
| `games.rt_gpu_mult` | — | 2.92 / 1.68 | per game, where RT was measured on and off |

`rt_gpu_mult` is NULL for 174 of the 176 games and they read `RT_GPU_COST_MULT`.
Only Hitman 3 and Forza Horizon 6 have enough of their own ray-tracing rows to
earn one; see gap 6b for why a single constant stopped working.

The last three rows were themselves wrong until batch 15 — they recorded 1.68,
3.30 and .35/.55/.75, values the code had moved past. Same failure as mistake
13 and found by the same fix; `python scripts/calibrate_engine.py` now prints
what the constants actually hold, so this table can be checked against it.

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

Twenty-nine of the catalog's 176 games have measurements behind them. The
remaining 147 carry values derived from the old model's hand-tuned scalings
and genre priors, and measured leave-one-game-out that derivation is 51.5%
out per game — the accuracy figure above applies to the measured set, not to
the whole catalog. Eight of the 29 are measured on one axis only: every row is
processor-limited, so their graphics cost is still a prior (gap 6e).

A Plague Tale: Requiem · Alan Wake 2 · Assetto Corsa Competizione ·
Baldur's Gate 3 · Battlefield 6 · Black Myth: Wukong · Cities: Skylines II ·
Counter-Strike 2 · Cyberpunk 2077 · Elden Ring · Far Cry 6 ·
Forza Horizon 5 · Forza Horizon 6 · Grand Theft Auto V Enhanced · Hitman 3 ·
Hogwarts Legacy · Kingdom Come: Deliverance 2 · Microsoft Flight Simulator ·
Red Dead Redemption 2 · Remnant II · Resident Evil Requiem · Starfield ·
Star Wars Jedi: Survivor · Star Wars Outlaws · The Last of Us Part I & II ·
Valorant · Warhammer 40K: Space Marine 2 · Watch Dogs Legion

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

**The first paired readings arrived in batch 17**, and they confirm the
warning the inversion has always carried. 63 of the 72 VRAM measurements are
allocations alone; nothing had ever reported both numbers at once. A Hitman
overlay on an RTX 5060 shows DEDICATED and ALLOCATED side by side across nine
configurations:

| dedicated | 4.72 | 4.68 | 5.00 | 4.92 | 5.02 | 5.51 | 6.00 | 6.52 | 6.46 |
|---|---|---|---|---|---|---|---|---|---|
| allocated | 5.02 | 5.01 | 5.32 | 5.24 | 5.34 | 5.83 | 6.32 | 6.84 | 6.77 |

Two things follow. Inverting the 5.02 allocation as though it were one gives
(5.02 − 0.8) / 1.12 = 3.77 GB against the 4.72 actually resident — 20% low,
against the "about 25%" `calibrate_vram.py` has claimed from reasoning alone.
Loading the dedicated column as `used` instead lands Hitman's base at 4.3 GB
where the mistaken kind gave 3.4 and the old derivation guessed 4.5.

And the ratio is 1.049–1.069 across all nine, where the model says
`working × 1.12 + 0.8 GB` — 6.09 predicted against 5.02 measured, 21% high.
That does not make the constants wrong so much as the *shape*: this is an 8 GB
card with almost nothing spare, and Alan Wake 2 reported 28 GB at 8K on a
32 GB one. A flat appetite plus a flat reserve cannot describe both. The
measurement that settles it is a paired reading on a large card.

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
3. **`PT_GPU_COST_MULT` rests on two rows.** Alan Wake 2 is the game that
   should be constraining it and cannot: every one of its baseline rows is at
   4K, so its own cost is unidentifiable and letting it set the multiplier
   would be circular. One video at a second resolution with ray tracing off
   fixes that, its own profile, and its ratio at the same time. Path tracing now fits at 6.6%,
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
5. **Ray Reconstruction is not modelled**, and as of batch 15 it is at least
   recorded. `benchmarks.ray_reconstruction` marks the four rows that use it
   and they are excluded from every fit, the same treatment as texture packs.
   What forced it: three of the seven rows in the RTX 3080 batch use it, and
   one of those three is path traced — and `PT_GPU_COST_MULT` is fitted from
   two rows. A third row differing by an unmodelled denoiser would not have
   been measuring path tracing.
   The cost is still unknown. No source has run it on and off at otherwise
   identical settings. Looking for a signal in the batch finds none — the
   three rows using it read 0.79, 0.93 and 1.10 against prediction where the
   four without read 0.80 to 0.87 — but each of the three carries its own
   confound, so that test could not have detected a moderate effect. Held out
   they read 18.5%. One on/off pair settles it.
6. **Optional high-resolution texture packs are not modelled**, and the cost of
   that is now measured: rows using one read 44.3% error against 6.5% for the
   fitted set. Far Cry 6 is the case — an RTX 4060 Ti 8GB with its 38 GB pack
   reads 28 fps at 1440p Ultra with ray tracing where an RTX 3060 Ti without it
   reads 68. A 2.4x collapse from a texture download. `benchmarks.texture_pack`
   records it and those rows are excluded from fitting, because a profile built
   from them describes a configuration the engine cannot express — Far Cry 6's
   whole profile came from two such rows and read -31% against an ordinary
   install. Space Marine 2's 4K pack is in the same position but unmarked, since
   its rows are a CPU ladder where the pack was constant.
6b. **A game's ray-tracing implementation is not the global multiplier.** Far
   Cry 6 measured on and off at the same settings costs 1.10x at 4K, against
   `RT_GPU_COST_MULT` of 1.70. Its ray tracing is reflections and shadows;
   Cyberpunk's is a different order of work. This is the RT-preset problem one
   level up — one boolean averaging implementations that are not comparable —
   and the fix is the same shape: a per-game notion of how much ray tracing a
   title actually does.
   Batch 18 puts a number on the far end. Hitman World of Assassination on an
   RTX 5090 at 4K native, ray tracing on and off in the same place with both
   sides GPU-bound at 99% and 96%, costs **3.25x**. So the measured spread now
   runs 1.10x to 3.25x, a factor of three, between two games whose ray tracing
   is described the same way — reflections and shadows in both. One boolean
   cannot hold that, and this is no longer an argument from principle.
   **Fixed in batch 19.** Hitman's own benchmark confirmed it a third time —
   Dartmoor, both sides GPU-bound at 99%, 3.46x — and loading those rows made
   the consequence unavoidable: the single constant fitted to 2.72, the
   whole-model error went 6.5% to 7.4%, and the ray-tracing rows stayed at 26%
   because 2.72 fits neither end. `games.rt_gpu_mult` now holds a per-game
   value where one has been measured and NULL everywhere else, which is what
   the 174 unmeasured games need and what the global average is for.
   Fitted: Hitman 3 at **2.92** (its rows 71.1% → 11.9%) and Forza Horizon 6
   at **1.68**. `RT_GPU_COST_MULT` stays 1.70 — after the measured games take
   their own, two rows from one game remain, and `MIN_RT_ROWS_FOR_GLOBAL`
   refuses to move a number 174 games read on that. The held-out gameplay rows
   improved at the same time, 33.3% to 31.4% and +16.6% to +12.3% bias, which
   is the part that says this is a better model rather than a closer fit.
6d. **What ray tracing costs depends on the scene; what rasterising costs does
   not.** The same batch, same machine and settings, three locations:
   with ray tracing on it reads 43 in Sapienza, 70 in Miami and 72 in
   Chongqing — a 1.67x spread. With it off, the two locations measured both
   ways agree to within 6%, 249 against 234.
   This reframes every earlier location finding. Saint Denis against the
   countryside, New Atlantis against a planet surface, Act 1 against Act 3 —
   each asked whether a game's cost is one number and got a different answer.
   It looks like the question was aimed slightly wrong: base rendering is
   steady across a game's areas, and it is the ray tracing that is not,
   because its cost depends on what is in front of the player. That is a
   mechanism rather than an observation, and `benchmarks.location` now exists
   so the next batch can test it instead of arguing it from a docstring.
   Sapienza also shows the cost is not only on the card. With ray tracing on
   its GPU utilisation is 61% against 96% with it off — the card idles a third
   of the time, so something else sets the pace. `RT_CPU_COST_MULT` is a flat
   1.08 and is plainly too small for this engine. That is why Sapienza reads
   5.79x where Chongqing reads 3.25x: the second is the card, the first is the
   card plus a wall.
6c. **One system reads +20.6% and the fit will not absorb it.** Batch 15 is an
   RTX 3080 with a Ryzen 9 5950X, and both had *zero* measurements before it —
   every component in that machine was untested. Its three fitted Cyberpunk
   rows read +20.6% where the game's other 44 read +1.9%, and recalibration
   left the profile exactly where it was: 45 rows outvote 3.
   What has been ruled out. Not the game — Cyberpunk is the best-fitted title
   in the set. Not the architecture — the RTX 3080 Ti reads −4.4% across 7
   rows, and lowering the 3080 below a validated sibling would break the one
   Ampere card that works. Not the preset — scored as High the batch reads
   +39.4%, and Extreme is not available to it (`tier_max` is Ultra, which is
   correct: Cyberpunk ships no Extreme).
   What it narrows to. The DLAA row runs at 32.88 fps, far below any processor
   ceiling, and still reads +24.7%, so the CPU cannot be the cause of that one.
   The error is also consistently larger with ray tracing on (+22 to +26%)
   than off (+15%), which points at RT Lighting: Psycho costing more than the
   global 1.70. That is gap 6b again, from the other direction.
   Not acted on. One system cannot say which of its two untested parts is
   wrong — the identifiability trap, and this project already published a
   hardware law from one generation once and had to retract it. Any RTX 3080
   measurement in a second game separates the card from the game; an RT preset
   ladder on one card separates Psycho from the card.
6e. **Thirteen of the 28 fitted games have a `gpu_cost` no measurement
   constrains, and the calibration reported them as fitted.** `is_identifiable`
   asks whether a game's rows vary in resolution, preset or processor, and
   answers whether *something* can be separated. It never asked whether *both*
   halves can. A 28-processor ladder at 1080p on an RTX 4090 varies 28 ways in
   the CPU and pins the CPU cost well, while every row sits against the
   processor — so the GPU cost is never tested and arrives from the genre prior
   wearing a "n=28" label.
   Seven games have no GPU-bound row at all: Assetto Corsa Competizione,
   Battlefield 6, Remnant II, Star Wars Jedi: Survivor, The Last of Us Part II,
   Valorant, Watch Dogs Legion. Six more rest on three rows or fewer —
   A Plague Tale: Requiem 2/30, Counter-Strike 2 3/38, Hitman 3 3/28, Hogwarts
   Legacy 3/33, Star Wars Outlaws 1/28, Space Marine 2 1/28.
   Hitman is the case that exposed it, and it is not a small error: two
   independent cards measured in free play read roughly twice the frame rate
   the fitted cost predicts — the engine says 118 at 4K where an RTX 5090
   returns 249 and 234. The inference is unusually safe, because those are
   gameplay rows and gameplay runs *below* a benchmark loop, so the true figure
   is higher still and the error can only be larger than it looks.
   `calibrate_engine.py` now names these games at the end of every run instead
   of letting a genre prior pass for a fit. The measurement that fixes them is
   the same in every case: high resolution on a mid-range card, where the GPU
   is what binds. A processor ladder cannot open this side no matter how long
   it gets.
   Batch 19 supplied exactly that for Hitman — its own benchmark at 1440p on an
   RTX 3070 — and the game left the thin list. Its `gpu_cost` still did not
   move, which is the next finding rather than a failure: see 10c.
10c. **Hitman's two benchmark scenes are 1.33x apart and it has one profile.**
   Dubai reads 103.80 fps native where Dartmoor reads 78.00, on the same
   machine at the same settings, and the processor ceilings differ far more —
   roughly 165 in Dubai against 92 in Dartmoor, from the size of the DLSS step
   each one allows. That is why the fit did not move when the GPU-bound rows
   arrived: no single (`gpu_cost`, `cpu_cost`) pair describes both, and the
   28 existing rows anchor it to Dubai. Which scene those 28 measured was never
   recorded and had to be inferred — Hardware Unboxed's 5800X3D at 213 fps is
   consistent with Dubai's ceiling and not with Dartmoor's.
   This is gap 10b — Baldur's Gate 3's acts — in a game where the *benchmark
   tool itself* offers two scenes. It is also the first such case where the
   evidence is in the table rather than a docstring, because `location` now
   records it.
7. **Alan Wake 2 at 8K exhausts VRAM on a 32 GB card** — measured, ~4 GB
   spilling to system RAM. The engine predicts 14 fps against 10.

6f. **The measured set does not span the catalogue, and that invalidates the
   obvious fix for the 147 derived games.** Measuring how badly a derived
   profile does is easy — hold each measured game out in turn, derive it as if
   unmeasured, score it against its own rows. It reads 6.4% fitted against
   51.6% derived. Whole-catalogue that is roughly 44%.
   The obvious response is a better derivation, and one looked available.
   `difficulty_multiplier`, which the current formula rests on, correlates with
   fitted `gpu_cost` at r=0.097 — nothing. `ram_sensitivity` reaches 0.740
   (Spearman 0.673). Refitting the transfer onto it takes the held-out figure
   from 51.6% to 28.9%, which by the same arithmetic is worth measuring about
   74 more games. It was recommended on that basis and the recommendation was
   wrong.
   Two things were missed. First, 70% of that gain is not the new signal at
   all: assigning *every* game the median measured profile, using no signal
   whatsoever, already reads 35.8%. Most of the improvement is from ceasing to
   use a bad predictor, not from having found a good one.
   Second, and fatally, all 29 measured games sit between 1.05 and 6.82 on
   `difficulty_multiplier` while the catalogue reaches down to 0.20 — **28 of
   the 147 are lighter than anything ever measured**. Stardew Valley, Hollow
   Knight, Terraria, Dota 2, League of Legends. A correlation measured inside a
   narrow band says little about the range outside it, so r=0.097 is much
   weaker evidence than it looked. And the transfer's output on those games is
   visibly wrong: it moves Stardew Valley from 1028 fps to 395 on an RTX 4060,
   because `ram_sensitivity` takes only about six distinct values and every
   game sharing one collapses onto the same number.
   Not applied. What unblocks it is small: **two or three videos on light
   games** — an esports title, a 2D indie, a fighting game. That extends the
   measured range downward, tests whether the ordering holds across the whole
   catalogue rather than inside the AAA band, and anchors the end where every
   candidate transfer currently breaks. Two videos, not seventy-four.

6g. **Twelve VRAM readings were taken for working sets and were caches.**
   Batch 4 loaded overlay figures from a GTX 1080 Ti and argued them through
   as usage: "at 11 GB nothing is clamped by capacity, so its overlay numbers
   are the games' own appetite". The property is backwards — not being clamped
   means the number is not a ceiling, not that it is a floor, and 11 GB is
   precisely the spare room a game caches into. The VRAM section above says so
   in its first line.
   The table contradicted the label and nobody looked: Alan Wake 2 at 1080p
   *Medium* read 9.2 GB, and Cyberpunk read 9.5 GB "used" at 1080p High
   against 7.3 GB "allocated" at 1440p Ultra — a usage figure above an
   allocation, at a lower resolution and a lower preset, both orderings
   violated at once.
   It reached the site. Red Dead Redemption 2's base came from one of those
   rows and put 11.6 GB on screen for 4K Ultra where the game wants about 6.7;
   the user who reported it also identified the likely cause, that 10 GB is
   what RDR2 takes with 8x MSAA, which the model has no term for.
   Relabelling them `allocated` and inverting was tried and left RDR2 at 9.4.
   The inversion assumes a fixed 1.12x plus 0.8 GB, and the only paired
   reading we hold — batch 17, an 8 GB card — measures 1.05; an 11 GB card
   caches more and nothing here knows how much. So they are marked `cached`
   and excluded, the same treatment texture packs and ray reconstruction get.
   Seven games lose their only VRAM evidence and fall back to derivation,
   which puts RDR2 at 7.4 GB against ~6.7 measured. Still high, no longer 73%
   out. A paired reading on a large card is what would fix it properly.

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
   **Batch 16 measures it properly for the first time, and it is much larger
   than +18%.** Batches 15 and 16 are the same card — an RTX 3080 10GB — one
   running Cyberpunk's internal benchmark, the other free in Night City. Two
   different videos and two different processors, which turns out not to
   matter, because the quantity wanted is a ratio of two measurements and the
   card's own error divides out of a ratio. At 1440p the benchmark reads
   measured/predicted 0.895 against the city's 0.527: **the benchmark is 1.70x
   free play**. The cleanest single pair needs no model at all — 1440p Ultra,
   RT Psycho, full render resolution: 32.88 with DLAA in the benchmark against
   20 in the city, and DLAA is the more expensive of the two.
   The three explanations that would have made it an artefact are all ruled
   out. The gameplay machine has the *faster* processor (5800X3D at 63 against
   the 5950X at 56). Video memory is the wrong way round — the row the engine
   flags nothing on reads 0.495 while the benchmark's full-resolution DLAA row,
   which needs far more memory, reads 0.802. And the benchmark video's "Custom"
   preset held textures and RT lighting at maximum, so if it differs from Ultra
   it differs upward, making 1.70x a floor.
   It is not only the card. At 1080p with Psycho lighting the city goes 50
   native to 60 with DLSS Quality — a 1.20x gain where 0.667 render scale
   should give about 1.9x. That flattening is a processor wall at roughly 60-65
   fps, on a chip Hardware Unboxed measured at 164 fps in the benchmark scene.
   Both halves of the machine meet a different game.
   No correction is applied. One title cannot license a global factor when the
   same document records Baldur's Gate 3 at -12% in one act and +57% in
   another, and a blanket shift would break the relationship with the 480
   benchmark rows the model is fitted to. What this changes is that the size of
   the problem is now known rather than estimated, and the earlier +18.1% is
   explained: it averaged Night City against Bohemian countryside and lunar
   surfaces. A second game measured both ways on one card says whether 1.70x is
   Cyberpunk's number or something wider.
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
   The ratio has now survived three independent attempts to break it. Across
   CPU scores from 50 to 100 it is flat between 0.744 and 0.772, which is why
   it is stored per game at all. Across location it does not move (below).
   And across GPU vendor it does not either: The Last of Us Part II reads 0.740
   on an RTX 5080 and 0.746 on an RX 9070 XT, Blackwell against RDNA 4.
   That idea has now been tested twice and failed twice. Red Dead Redemption 2:
   Saint Denis 0.792, countryside 0.798. Starfield: New Atlantis 0.753, planet
   surface 0.753, identical to three places across nine rows none of which had
   to be discarded. Two of the best-known CPU walls in any open world, two
   studios, two engines, and neither moves the ratio. One ratio per game is the
   right shape — a conclusion reached first from the ratio being flat across
   CPU scores, and now confirmed on location as well.
   It does not follow that location is unimportant: gap 10b shows the frame
   rate *level* moving enormously with it. What holds is that the distance
   between the average and the 1% low does not.
   Baldur's Gate 3 lands at 0.707 — beside The Last of Us Part I rather than at
   the bottom of the range, which is where a game with Act 3's reputation was
   expected. Its Act 1 rows were both discarded (one at 0.980, one at 0.409),
   so what is recorded is Lower City's ratio and the act comparison could not
   be made.
   KCD2, RDR2 and BG3 are the only games whose ratios come from free gameplay
   rather than a benchmark loop. calibrate_fps_low.py prints the source per game
   instead of blending it out of sight.
   Batch 16 gives the first within-game comparison of the two, and they are not
   the same: Cyberpunk's 28 benchmark rows give 0.737, its 8 gameplay rows give
   0.813. The fitted ratio moves to 0.754. Two reasons not to conclude much yet.
   The gameplay numbers are read off a live overlay and are round — 10 and 9,
   20 and 15 — so single rows carry several points of quantisation error. And
   the benchmark rows are a 1080p CPU ladder while these are GPU-bound, which
   was worth ruling out and now is: across all 423 rows carrying a 1% low the
   ratio is 0.764 where the engine calls the row CPU-bound and 0.750 where it
   calls it GPU-bound, and inside the three games holding both it reads
   0.878/0.881 (Hitman 3), 0.876/0.872 (KCD2) and 0.756/0.749 (Starfield).
   Bottleneck does not move the ratio. That is the fourth thing it has now
   survived, after CPU score, location and GPU vendor.
   Batch 17 forced a fifth test and a sharper one. Hitman's two sources
   disagree by 0.199 — 0.878 from 28 Dartmoor benchmark rows, the steadiest
   figure in the set, against 0.679 from nine crowded-hotel gameplay rows —
   and Cyberpunk's equivalent gap ran the *other* way. A ratio that moves in
   both directions with the source looks like measurement tooling rather than
   games. It is not: inside the single b10-hub source, eight games measured by
   one reviewer with one tool spread from 0.533 in Counter-Strike 2 to 0.847
   in Star Wars Jedi: Survivor, a range of 0.314, while the means of all ten
   sources span 0.167. Games separate further than sources do.
   What the disagreement does mean is that one ratio per game has the same
   limit one cost per game has. Hitman lands at 0.827 from 42 rows, and no
   single number describes both a quiet English manor and a crowded hotel.
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
3b. **A fix that passed every test and never shipped.** `rt_gpu_mult` was
   added to both engines, agreed on across 4384 conformance cases, and
   confirmed by a positive control — and the site kept using the global 1.70,
   because `export_engine_data.py` has its own list of game columns and
   nothing added the new one to it. The conformance test cannot catch this: it
   builds its cases straight from the database, so both engines agree
   perfectly on data the browser never receives. Two separate lists have to
   agree for a game field to reach a user, and only one of them is tested.
4. **A test that stopped covering what it was pointed at, four times.** The
   conformance runner trims hardware and game rows to the fields the engines
   read. `architecture` was missing when the legacy-GPU note landed, so 4768
   cases agreed perfectly while never entering the new branch; `form_factor`
   and `cores` repeated it; `rt_gpu_mult` made it four, passing 4384 cases in
   13 fields while both engines quietly took the same fallback.
   Counting the cases that reach a branch was the fix after the third, and it
   is necessary but not sufficient — it says the branch runs, not that running
   it differently would be caught. So the fourth was closed with a positive
   control instead: the TypeScript side was broken on purpose to ignore
   `rt_gpu_mult`, the run was confirmed to fail, and only then restored. Ten of
   the 4384 cases reach that branch and ten is enough, because the test failed.
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
13. **Three rounds of calibration output never reached the code.** The
   calibrator writes game profiles to the database but prints the global
   constants for a human to copy, and two of those print statements announced
   the *previous* value as a literal: `PT_GPU_COST_MULT: 3.10 -> 3.54` every
   run, when the constant had actually been sitting at 3.40 since the last
   time anyone updated it. It looked like a fit moving and it was a fit
   standing still, so `balance_config.py` went untouched from commit `c83f2bc`
   while three batches landed. `PT_GPU_COST_MULT` and `FG_GPU_OVERHEAD` were
   both stale. Both stages now capture the real value before the search
   mutates it — which is what stage 4 had been doing all along, with a comment
   explaining the trap the other two were falling into.
   Worth naming the general shape: a message that never changes is not
   verification, and this one was reassuring for months.

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

In order of what each would actually settle. The first four are the ones
holding the model back; the rest widen coverage.

0. **A second game measured both ways on one graphics card** — its internal
   benchmark and free gameplay, any two videos, as long as the card matches.
   Cyberpunk 2077 now has this (batches 15 and 16, both RTX 3080 10GB) and it
   says the benchmark reads 1.70x free play at 1440p, against the +18.1% that
   mismatched sources had suggested. That is the largest correction waiting in
   the model and it currently rests on one title.
   Note what the requirement turned out to be. Five batches were spent hunting
   one video containing both, on the grounds that the machine had to be held
   constant. It does not: the answer is a ratio of two measurements, so the
   card's own error divides out, and even the processor may differ as long as
   neither side is CPU-bound. Any second game with a built-in benchmark whose
   card we can also find gameplay for will do — Shadow of the Tomb Raider,
   Assassin's Creed, Metro Exodus, Horizon Zero Dawn, Hitman 3. That is a far
   easier search than the one that failed five times.
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
3b. **Any of the thirteen GPU-blind games measured where the card binds** —
   1440p or 4K on a mid-range GPU, internal benchmark, one resolution sweep
   each. Seven of them have no GPU-bound row at all and their `gpu_cost` is a
   genre prior with 28 measurements standing behind the wrong half of the
   model (gap 6e). Hitman 3 is the one we know is wrong and by how much, so it
   is the place to start: its own Dubai or Dartmoor benchmark at 1440p or 4K,
   on any card, in one video.

Then:

4. **A path-traced game other than Cyberpunk 2077, measured both with and
   without** — `PT_GPU_COST_MULT` is fitted from two rows (gap 3).
5. **A ray-tracing sweep on a second game**, ideally Cyberpunk's
   Low/Medium/High/Ultra/Overdrive, to make RT levels modellable (gap 1).
6. **DLSS Ray Reconstruction on and off at otherwise identical settings** —
   two runs. Four rows now sit outside every fit because nobody has measured
   what it costs (gap 5).
7. **Any RTX 3080 measurement in a second game**, to say whether that card's
   +20.6% is the card or the Cyberpunk RT preset it was measured at. A Ryzen 9
   5950X anywhere does the same job from the other side — both parts of that
   machine are untested (gap 6c).
8. **Far Cry 6 without the HD texture pack**, to separate the pack from the
   base game (gap 6).
9. **Microsoft Flight Simulator 2024 at three resolutions.** Its costs are
   openly a guess — derived from the 2020 profile plus an uplift.
10. **More of the 147 uncalibrated games**, prioritising genres not yet
   represented.

Record with every measurement: resolution, preset, ray-tracing state *and
preset name*, upscaling mode, frame-generation mode, RAM amount, VRAM reading
with whether it is allocated or used, whether the run is a benchmark loop or
free gameplay, and the source with a timestamp. GPU utilisation below ~85%
indicates a CPU limit and is worth noting.

The prompt that produces this from a video's AI summary is worth reusing; each
of its requirements exists because something was lost without it.

Batch 15 suggests a better source where one exists. Photographs of a game's own
benchmark result screen carry the settings the summaries keep losing — both
frame-generation switches, the upscaler *and* its sharpness, every ray-tracing
sub-option, the preset name — and they cannot round a number or invent a range.
The two guards that batch still needed were of a different kind: a "Min FPS"
that is neither a minimum nor a 1% low, and a denoiser the model has no term
for. Where a game has an internal benchmark, ask for the result screens.

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
