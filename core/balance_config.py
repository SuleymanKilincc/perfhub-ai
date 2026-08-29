"""
Balance / tuning constants for Cadence, the FPS prediction engine
(core/scoring_engine.py).

The engine works in *frame time* (milliseconds), not in fps. A game costs the
CPU some milliseconds per frame and the GPU some milliseconds per frame; the
slower of the two is what you actually get. Working this way is what makes
bottlenecks fall out of the model instead of being faked with weights, and
it is why resolution, upscaling and frame generation can each be applied to
the term they really affect.

Everything in this file is a tuning knob. Changing a value here re-tunes
predictions without touching the estimation logic. The absolute constants
(GPU_MS_CONST / CPU_MS_CONST) and the exponents are the ones the benchmark
calibration pass is expected to move.
"""

# ─── Bottleneck blend ───────────────────────────────────────────────────────
# Frame times combine as ft = (ft_cpu^k + ft_gpu^k)^(1/k). A plain max() would
# put a hard corner at the crossover; real systems ease into a bottleneck
# because the two pipelines only partly overlap. k=4 gives that soft knee
# while still converging on the slower stage.
BOTTLENECK_BLEND_K = 4.0

# ─── Absolute calibration ───────────────────────────────────────────────────
# Convert relative per-game cost units into milliseconds. Anchored so that an
# RTX 4090 + 7800X3D lands near 160 fps in Cyberpunk 2077 at 1080p/High with
# no ray tracing and no upscaling.
GPU_MS_CONST = 2.65
CPU_MS_CONST = 2.25

# power_score is not linear in real throughput. An RTX 4090 (99) is roughly
# 3.2x an RTX 4060 (54) once the CPU is out of the way, which needs an
# exponent well above 1. Gaming CPU performance is far more compressed, so
# its curve stays near linear.
#
# Raised from 1.54 after checking the scores against a published 1440p
# hierarchy: all 48 cards covered were predicted too fast relative to the
# RTX 5090, so the ladder was compressed rather than individually noisy.
# See scripts/calibrate_gpu_scores.py.
GPU_PERF_EXPONENT = 1.85

# CPU power_score is now a 1080p gaming index rather than a throughput rating
# (see scripts/calibrate_cpu_scores.py), so it is already proportional to frame
# rate and needs no curve: 1.0 is the definition, not a fit.
#
# It was 0.60, which existed to flatten scores that ranked all-core throughput
# — they had a Core Ultra 9 285K above a Ryzen 7 9800X3D. For a long time the
# benchmark set could not argue either way, because 74 of 111 measurements used
# a 7800X3D or a 9800X3D and nothing below a 5700X existed. That has now been
# settled by a 27-processor ladder on one RTX 4090 at 1080p, running from a
# 9800X3D down to an i3-12100F.
#
# Fitting it needs the level of each game divided out first: a game whose cost
# is wrong shifts its whole ladder up or down, while the exponent sets the
# ladder's slope, and fitting both at once lets a level error masquerade as a
# curve. With levels normalised, shape error is 6.3% at 1.00 and 6.1% at 1.10,
# and the ratio between the fastest and slowest chip implies 1.06. So it stays
# at 1.00: a fifth of a point is not a reason to move a constant, and what was
# chosen on principle turns out to have been right.
CPU_PERF_EXPONENT = 1.00
REF_SCORE = 100.0          # score that maps to 1.0x performance

# ─── Resolution ─────────────────────────────────────────────────────────────
# Pixel counts relative to 1080p.
RESOLUTION_PIXELS = {
    "1080p": 1.00,
    "1440p": 1.78,
    "4k":    4.00,
    "8k":   16.00,
}
# GPU cost grows slower than raw pixel count — part of a frame (culling, some
# post, driver overhead) is resolution-independent. Without this, 4K comes out
# roughly 40% too slow.
RES_PIXEL_EXPONENT = 0.82

# VRAM does not follow pixel count either; textures dominate and they are
# resolution-independent. Only buffers scale.
# Confirmed by measurement: The Last of Us Part I moves from 9.4 GB at 1080p
# to 12.2 GB at 4K — about 30% for four times the pixels.
RES_VRAM_FACTOR = {
    "1080p": 1.00,
    "1440p": 1.14,
    "4k":    1.38,
    "8k":    1.85,
}

# ─── Quality presets ────────────────────────────────────────────────────────
# (gpu_cost_mult, cpu_cost_mult, vram_mult), all relative to High = 1.0.
# Quality settings hit the GPU hard and the CPU only lightly — draw distance
# and crowd density move the CPU, shadows/textures/effects move the GPU.
QUALITY_TIERS = {
    "Very Low": (0.42, 0.80, 0.55),
    "Low":      (0.58, 0.86, 0.68),
    "Medium":   (0.77, 0.93, 0.83),
    "High":     (1.00, 1.00, 1.00),
    "Ultra":    (1.34, 1.07, 1.20),
    "Extreme":  (1.70, 1.14, 1.38),
}
DEFAULT_QUALITY_TIER = "High"
# Order matters for clamping a request to what a game actually offers.
QUALITY_ORDER = ["Very Low", "Low", "Medium", "High", "Ultra", "Extreme"]

# ─── Ray tracing / path tracing ─────────────────────────────────────────────
# Multipliers on GPU frame-time cost, plus the extra VRAM the BVH and
# denoisers need. Path tracing is a different order of magnitude, not a
# heavier RT preset.
#
# RT_GPU_COST_MULT is an average over *typical* ray-tracing presets, not the
# maximum. The model has one boolean where games ship several levels, and the
# spread is large: Forza Horizon 6 on one card at 1440p reads 85 fps at High RT
# and 40 at Extreme. Measurements now record which preset they used
# (benchmarks.rt_level) and the calibration holds Extreme rows out, so a single
# maxed-out run cannot drag this toward a setting most players never pick.
RT_GPU_COST_MULT = 1.70
PT_GPU_COST_MULT = 3.40
RT_VRAM_ADD_GB = 1.10
PT_VRAM_ADD_GB = 1.90
# RT also adds BVH build/update work on the CPU.
RT_CPU_COST_MULT = 1.08
PT_CPU_COST_MULT = 1.12

# ─── Hardware outside the measured range ────────────────────────────────────
# Architectures with no measurement behind them at all: 79 of the 164 catalogue
# GPUs sit on one, and every benchmark we hold is Turing or newer.
#
# What outside runs on these cards say is genuinely unsettled. Five systems put
# the engine +110% high on average, which looked at first like a clean
# architectural cliff — these chips lack mesh shaders and much of the DX12
# Ultimate set that newer engines assume. A sixth then contradicted it: the GTX
# 1080 Ti is the same Pascal generation as the GTX 1070 that read +153%, and
# across ten current games it comes to +8%, landing within 2% on the very title
# the 1070 missed by 308%.
#
# VRAM looked like the explanation — 11 GB against 8 — and it was worth chasing,
# because the working sets really were 18% low and fixing them moved the memory
# model from seeing 4 of 12 games spill on an 8 GB card to seeing 8, against 7
# that really do. But it moved the low-end frame rates by 1.7 points. So that is
# not the cause either.
#
# Which leaves the honest answer: we do not know. The runs that disagree most
# pair a flagship CPU with a 2016 budget card, a combination assembled for
# content rather than for use, and their numbers are not internally consistent
# with each other. Claiming a correction from them would be inventing a law out
# of two videos.
#
# The estimate is still produced, and it carries a note saying the card is
# outside what has been measured. Not a direction, not a magnitude — those are
# what the evidence does not support.
LEGACY_GPU_ARCHITECTURES = frozenset({
    "Kepler", "Maxwell", "Pascal", "Polaris", "Vega", "Gen 9.5", "Gen 11",
})

# ─── Upscaling ──────────────────────────────────────────────────────────────
# Linear render scale per mode: the GPU renders at this fraction of the output
# resolution on each axis, so pixel work scales with the square.
UPSCALING_RENDER_SCALE = {
    "ultra performance": 0.333,
    "performance":       0.500,
    "balanced":          0.580,
    "quality":           0.667,
    "dlaa":              1.000,   # native resolution, AI anti-aliasing
    "native":            1.000,
}
# Part of the GPU frame does not shrink with render resolution (post
# processing at output res, UI, driver overhead), so the saving is damped.
UPSCALING_UNSCALED_FRACTION = 0.16
# The upscaling pass itself costs GPU time (roughly constant per frame).
UPSCALING_PASS_COST_MS = {
    "dlss": 0.35,
    "fsr":  0.30,
    "xess": 0.55,   # XeSS DP4a path is the most expensive on non-Arc cards
    "dlaa": 0.45,
}
DEFAULT_UPSCALING_PASS_COST_MS = 0.35

# ─── Frame generation ───────────────────────────────────────────────────────
# Generated frames cost GPU time to produce but need no CPU simulation, which
# is exactly why frame gen helps most when the CPU is the limit.
FG_OUTPUT_MULTIPLIER = {
    "2x": 2.00,
    "3x": 3.00,
    "4x": 4.00,
}
# Fraction of the rendered frame's GPU time spent generating the extra frames.
# Fitted from a single 3x/4x ladder — one game, one card — which is why the
# error on frame-generation rows stays near 22% while everything else sits
# under 8%.
#
# Getting even this far took widening the search: at the old ceiling the step
# pinned at 0.20, and a value resting on the edge of its own range is the
# search running out of room, not a fit. Widened once, the step moved off the
# edge and the error fell 26.0% to 21.9% — worth having. Widened again, it ran
# straight to the new edge for two tenths of a point, which is a flat objective
# wandering rather than evidence. calibrate_engine.py now refuses a boundary
# value that buys less than a point, so the warning is acted on instead of
# printed and ignored.
#
# What that means: one ladder cannot pin the 3x/4x step down. A second one, on
# a different game and card, is the measurement that would.
FG_GPU_OVERHEAD = {
    "2x": 0.50,
    "3x": 0.92,
    "4x": 1.34,
}
FG_VRAM_ADD_GB = {
    "2x": 1.0,
    "3x": 1.4,
    "4x": 1.8,
}

# ─── VRAM: working set vs allocation ────────────────────────────────────────
# Overlays report *allocated* memory, not what a frame actually needs. Engines
# pre-cache assets into any VRAM that happens to be free — a game that needs
# 5-6 GB will happily reserve 8, and on a 24 GB card it will reserve far more
# still. Alan Wake 2 reported 28 GB at 8K on a 32 GB card.
#
# The distinction matters because the two numbers answer different questions:
#
#   working set  ->  "will the frame rate drop?"   (this drives the penalty)
#   allocation   ->  "will it stutter?"            (this drives the warning)
#
# On a smaller card the driver simply evicts the surplus cache and the game
# keeps running, which is why Hogwarts Legacy loses almost nothing going from
# 16 GB to 8 GB despite reporting far more than 8 GB in use.
#
# Measured allocations sit roughly 1.2-2 GB above the working set on
# mid-sized cards, which this pair reproduces.
VRAM_ALLOC_APPETITE = 1.12     # how much more than the working set a game wants
VRAM_ALLOC_HEADROOM_GB = 0.8   # plus a flat cache reserve
# A game never reserves the entire card; the driver and desktop need room.
VRAM_ALLOC_CAPACITY_LIMIT = 0.92

# ─── VRAM pressure ──────────────────────────────────────────────────────────
# Once the working set no longer fits, textures stream across PCIe from system
# RAM. That is dramatically slower than local VRAM, so the loss is steep and
# non-linear in how far over the limit you are.
# Fitted against measured 8GB-vs-16GB pairs of the same GPU (RTX 4060 Ti),
# where the only variable is capacity. Measured ratios ranged from 0.38 to
# 0.95, nothing like the collapse the first guess (severity 2.6, floor 0.22)
# produced — it predicted Hogwarts Legacy at 0.29 where reality was 0.95.
# Modern engines drop texture streaming quality instead of falling over.
VRAM_SPILL_SEVERITY = 0.50     # higher = harsher penalty per unit of overflow
VRAM_SPILL_FLOOR = 0.80        # worst-case multiplier before it counts as unplayable
# Below this much free VRAM the allocator is already thrashing even though it
# technically fits.
VRAM_TIGHT_HEADROOM_GB = 0.4
VRAM_TIGHT_PENALTY = 0.94

# ─── System RAM ─────────────────────────────────────────────────────────────
# Reserved for Windows, background apps and the shader cache.
OS_RAM_RESERVE_GB = 3.5
# When VRAM overflows, the spilled data has to live in system RAM. If there is
# not enough room for it, the game runs out of address space and crashes or
# becomes a slideshow — this is the "8GB card + 16GB RAM" failure case.
RAM_SHORTFALL_PENALTY = 0.55   # applied when RAM is short but the game survives
RAM_ABUNDANCE_BONUS = 1.02     # plenty of headroom smooths frame delivery
# When VRAM spills, how much free system RAM counts as "comfortable" — the
# spill needs roughly this many times its own size to cache cleanly instead of
# thrashing. This is what makes 32 GB behave better than 16 GB in the same
# overflow scenario, rather than the two producing identical numbers.
RAM_SPILL_COMFORT_RATIO = 4.0
RAM_SPILL_CRAMPED_PENALTY = 0.62   # multiplier when the spill barely fits
# How far short of the spill system RAM has to fall before the game is called
# unplayable rather than merely slow. Requiring merely "less free RAM than the
# overflow" was far too eager: it reported 3 fps for The Last of Us Part II on
# an 8GB card with 16GB of RAM, which really runs at 65. Windows pages the
# excess to disk and the engine keeps streaming, so a true failure needs the
# shortfall to be severe.
RAM_UNPLAYABLE_SHORTFALL_RATIO = 0.25


def quality_multipliers(tier):
    """(gpu, cpu, vram) cost multipliers for a quality preset."""
    return QUALITY_TIERS.get(tier, QUALITY_TIERS[DEFAULT_QUALITY_TIER])
