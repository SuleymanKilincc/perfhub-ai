"""
Balance / tuning constants for the FPS estimation engine (core/scoring_engine.py).

Changing a value here re-tunes FPS predictions without touching the
estimation logic itself. Names encode WHERE a constant applies
(resolution / quality tier / VRAM tier) so a change's blast radius is
obvious from the name alone.
"""

# ─── CPU-specific gaming buffs ─────────────────────────────────────────────
X3D_CACHE_FPS_BUFF = 1.18   # AMD X3D 3D V-Cache: ~18% more gaming FPS

# ─── Base FPS budget: GPU/CPU weight per resolution ────────────────────────
# Resolution shifts CPU/GPU relevance: 1080p leans CPU, 4K is GPU-bound.
GPU_WEIGHT_1080P, CPU_WEIGHT_1080P = 3.5, 1.5
GPU_WEIGHT_1440P, CPU_WEIGHT_1440P = 3.8, 1.2
GPU_WEIGHT_4K,    CPU_WEIGHT_4K    = 4.2, 0.9

# ─── VRAM demand proxy (derived from game difficulty_multiplier) ──────────
VRAM_DEMAND_DIFFICULTY_DIVISOR = 5.0   # difficulty_multiplier / this = raw demand (0-1)
VRAM_DEMAND_FLOOR = 0.10               # demand never scores below this
VRAM_PENALTY_DEMAND_THRESHOLD = 0.32   # below this demand, skip VRAM penalty entirely

# ─── VRAM penalty coefficients — 4K ────────────────────────────────────────
VRAM_PENALTY_4K_ULTRA_UNDER_8GB     = 0.42
VRAM_PENALTY_4K_ULTRA_UNDER_10GB    = 0.55
VRAM_PENALTY_4K_ULTRA_UNDER_12GB    = 0.78
VRAM_PENALTY_4K_ULTRA_UNDER_16GB    = 0.92
VRAM_PENALTY_4K_NON_ULTRA_UNDER_8GB = 0.88
VRAM_SUFFICIENT_4K_GB = 12   # below this, vram_sufficient=False (read later by Frame Gen)

# ─── VRAM penalty coefficients — 1440p ─────────────────────────────────────
VRAM_PENALTY_1440P_UNDER_6GB       = 0.72
VRAM_PENALTY_1440P_ULTRA_UNDER_8GB = 0.88
VRAM_SUFFICIENT_1440P_GB = 8

# ─── VRAM penalty coefficients — 1080p ─────────────────────────────────────
VRAM_PENALTY_1080P_UNDER_4GB = 0.80
VRAM_PENALTY_1080P_UNDER_6GB = 0.92
VRAM_SUFFICIENT_1080P_GB = 4

# ─── Upscaling: VRAM-penalty undo ──────────────────────────────────────────
# Upscaling renders at a lower internal resolution, relieving VRAM
# pressure, so part (or all) of the earlier VRAM penalty is restored.
UPSCALING_VRAM_UNDO_MIN_MULT = 1.05          # only undo penalty if boost exceeds this
UPSCALING_BALANCED_QUALITY_UNDO_RATIO = 0.65  # Balanced/Quality undo ~65% of the penalty

# ─── Upscaling: technology efficiency delta vs DLSS reference ─────────────
UPSCALING_TECH_SCALE_DLSS = 1.00
UPSCALING_TECH_SCALE_FSR  = 0.88   # FSR2/3: ~12% less efficient than DLSS per mode
UPSCALING_TECH_SCALE_XESS = 0.93   # Intel XeSS: ~7% less efficient than DLSS

# ─── Upscaling: render-resolution multiplier, per output resolution ───────
UPSCALING_MULT_DLAA = 0.96   # DLAA: renders at native res with AI AA
UPSCALING_MULT_ULTRA_PERFORMANCE = {"4k": 3.05, "1440p": 2.05, "1080p": 1.90}
UPSCALING_MULT_PERFORMANCE       = {"4k": 2.38, "1440p": 1.72, "1080p": 1.58}
UPSCALING_MULT_BALANCED          = {"4k": 1.92, "1440p": 1.50, "1080p": 1.43}
UPSCALING_MULT_QUALITY           = {"4k": 1.65, "1440p": 1.38, "1080p": 1.29}
UPSCALING_MULT_NATIVE = 1.0   # Native rendering -- no upscaling

# ─── Frame Generation ───────────────────────────────────────────────────────
# Real-world net FPS multipliers per mode (after latency/overhead cost).
# Frame Gen doubles the output frames, but ~15% overhead + input latency cost.
FG_NET_MULT = {
    "2x": 1.80,   # 2 frames out per render; ~10% overhead -> net 1.80x
    "3x": 2.55,   # 3:1 ratio, higher overhead
    "4x": 3.20,   # 4:1, significant overhead
}
# Minimum VRAM for Frame Gen's extra frame buffers to not backfire, per resolution.
FG_MIN_VRAM_GB = {"1080p": 6, "1440p": 10, "4k": 14}
FG_INSUFFICIENT_VRAM_PENALTY = 0.70   # 30% FPS loss when VRAM can't back FG's buffers

# ─── RAM impact ─────────────────────────────────────────────────────────────
RAM_PENALTY_UNDER_8GB = 0.65                    # severe bottleneck - constant paging
RAM_SENSITIVITY_EXPONENT_UNDER_8GB = 0.85       # more penalty for RAM-hungry games

RAM_PENALTY_UNDER_16GB_DEMANDING = 0.78         # 4K or Ultra settings
RAM_SENSITIVITY_EXPONENT_UNDER_16GB_DEMANDING = 0.90

RAM_PENALTY_UNDER_16GB_LIGHT = 0.88             # 1080p Medium/High
RAM_SENSITIVITY_EXPONENT_UNDER_16GB_LIGHT = 0.95

RAM_SENSITIVITY_HIGH_THRESHOLD = 1.5   # game_ram_sensitivity >= this = "RAM-hungry" game
RAM_BONUS_32GB_HUNGRY_GAME = 0.95      # RAM-hungry games still want more than 32GB
RAM_BONUS_32GB_NORMAL_GAME = 1.0       # sweet spot for normal games
RAM_BONUS_64GB_HUNGRY_GAME = 1.05      # RAM-hungry games finally shine
RAM_BONUS_64GB_NORMAL_GAME = 1.02      # slight benefit for 4K ultra with heavy mods
