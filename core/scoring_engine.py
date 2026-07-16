"""
Scoring Engine - v4.0
Handles system scoring, bottleneck analysis, and accurate FPS estimation.
"""
from core import balance_config as bc

# ─── GPU tier lookup: rough "raw render budget" per power_score unit ──────────
# In practice: (gpu_score * GPU_WEIGHT + cpu_score * CPU_WEIGHT) → raw frames
#
# Gaming is ~70-75 % GPU-bound at medium-high resolution.
# CPU matters more for 1080p / CPU-heavy games; GPU dominates 1440p/4K.
# 
# UPDATED: Increased weights for more realistic FPS values
# RTX 5070 Ti (88 score) should get ~60-80 FPS in 4K Ultra demanding games
GPU_WEIGHT  = 3.8   # scales the GPU power_score to "raw frame equivalents"
CPU_WEIGHT  = 1.2   # CPU contributes significantly at low res, but less at 4K


def calculate_system_score(cpu_score, gpu_score, ram_gb, ram_details=None, storage=None):
    """
    Returns a 0-100 composite score.
    GPU weighted at 50 %, CPU at 25 %, RAM 15 %, Storage 10 %.
    Scores can exceed 100 for extreme rigs — we cap at 100.
    """
    gpu_w, cpu_w, ram_w, storage_w = 0.50, 0.25, 0.15, 0.10

    # RAM scoring: capacity + speed + type
    if ram_details and len(ram_details) > 0:
        s0 = ram_details[0]
        mem_type = s0.get('mem_type', 'DDR4')
        configured = s0.get('configured_mhz', 0) or s0.get('speed_mhz', 0)
        total_cap = sum(s.get('capacity_gb', 0) for s in ram_details)
        
        # Base score from capacity
        if total_cap >= 64:   cap_score = 100
        elif total_cap >= 32: cap_score = 90
        elif total_cap >= 16: cap_score = 75
        elif total_cap >= 8:  cap_score = 50
        else:                 cap_score = 25
        
        # Speed bonus (DDR5 gets higher base)
        is_ddr5 = "DDR5" in mem_type.upper() or "LPDDR5" in mem_type.upper()
        speed_score = min(10, (configured / 600.0) * 10) if configured > 0 else 5
        
        # Type bonus
        type_bonus = 15 if is_ddr5 else 0
        
        ram_score = min(100, cap_score + speed_score + type_bonus)
    else:
        # Fallback to simple capacity-based scoring
        if ram_gb >= 32:   ram_score = 80
        elif ram_gb >= 16: ram_score = 65
        elif ram_gb >= 8:  ram_score = 45
        else:              ram_score = 20

    # Storage scoring: NVMe > SATA SSD > HDD
    if storage and len(storage) > 0:
        storage_score = 0
        for d in storage:
            drv_bus = d.get('bus_type', '')
            drv_type = d.get('media_type', '')
            
            is_nvme = "NVME" in drv_bus.upper() or drv_bus in ("NVMe", "17", "9")
            is_ssd = drv_type == "SSD" or is_nvme
            
            if is_nvme:
                storage_score = max(storage_score, 100)  # NVMe is best
            elif is_ssd:
                storage_score = max(storage_score, 70)   # SATA SSD is good
            else:
                storage_score = max(storage_score, 30)   # HDD is poor
    else:
        storage_score = 50  # Default if unknown

    raw = (gpu_score * gpu_w) + (cpu_score * cpu_w) + (ram_score * ram_w) + (storage_score * storage_w)
    return round(min(max(raw, 0), 100), 1)


def analyze_bottleneck(cpu_score, gpu_score):
    """
    Returns a dict with status / msg / color / percentage.
    Threshold tightened to 12 for 'perfect' (real-world rigs rarely match exactly).
    """
    diff = abs(cpu_score - gpu_score)
    pct  = round(diff, 1)

    if diff < 12:
        return {
            "status":     "✅ MÜKEMMEL DENGE",
            "msg":        "CPU ve GPU mükemmel eşleşiyor. Darboğaz minimumdur.",
            "color":      "#10B981",
            "percentage": pct,
        }
    elif cpu_score < gpu_score:
        sev = "⚠️" if diff < 30 else "🔴"
        return {
            "status":     f"{sev} CPU DARBOĞAZİ  ({pct:.0f} puan fark)",
            "msg":        "İşlemciniz ekran kartınızın gerisinde kalıyor. CPU yükseltmeyi düşünün.",
            "color":      "#F59E0B",
            "percentage": pct,
        }
    else:
        sev = "⚠️" if diff < 30 else "🔴"
        return {
            "status":     f"{sev} GPU DARBOĞAZİ  ({pct:.0f} puan fark)",
            "msg":        "Ekran kartınız üst düzey işlemcinizin önünü kesiyor. GPU yükseltmeyi düşünün.",
            "color":      "#F59E0B",
            "percentage": pct,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  FRAME GENERATION SUPPORT TABLE
#  Maps GPU model keywords → list of supported multipliers (excluding "Kapalı")
# ─────────────────────────────────────────────────────────────────────────────
FG_SUPPORT = {
    # NVIDIA Blackwell – DLSS 4 Multi Frame Gen (up to 4 generated frames = 4x)
    "RTX 5090": ["2x", "3x", "4x"],
    "RTX 5080": ["2x", "3x", "4x"],
    "RTX 5070 Ti": ["2x", "3x", "4x"],
    "RTX 5070":    ["2x", "3x", "4x"],
    "RTX 5060 Ti": ["2x", "3x"],
    "RTX 5060":    ["2x", "3x"],
    "RTX 5050":    ["2x"],

    # NVIDIA Ada – DLSS 3 Frame Gen (1 generated frame = 2x visual output)
    "RTX 4090":    ["2x"],
    "RTX 4080":    ["2x"],
    "RTX 4070 Ti": ["2x"],
    "RTX 4070":    ["2x"],
    "RTX 4060 Ti": ["2x"],
    "RTX 4060":    ["2x"],
    "RTX 4050":    ["2x"],

    # AMD RX 7000/8000/9000 – FSR 3 Frame Gen
    "RX 9070": ["2x"],
    "RX 8900": ["2x"],
    "RX 8800": ["2x"],
    "RX 8700": ["2x"],
    "RX 7900": ["2x"],
    "RX 7800": ["2x"],
    "RX 7700": ["2x"],
    "RX 7600": ["2x"],

    # Intel Arc Battlemage – XeSS Frame Gen
    "Arc B580": ["2x"],
    "Arc B570": ["2x"],
}

def get_fg_options(gpu_name: str) -> list[str]:
    """
    Returns a list of Frame Generation dropdown options for the given GPU.
    Always starts with 'Kapalı'. If the GPU has no FG support, returns only ['Kapalı'].
    """
    gpu_upper = gpu_name.upper()
    options = ["Kapalı"]
    for keyword, mults in FG_SUPPORT.items():
        if keyword.upper() in gpu_upper:
            options.extend(mults)
            break
    return options


def _calculate_base_fps(cpu_data, gpu_data, game, resolution, settings):
    """
    Extracts hardware scores and computes the raw FPS budget from
    CPU/GPU power scores, the game's difficulty_multiplier, and its
    resolution/quality scaling factors — before any VRAM, upscaling,
    frame-gen, or RAM modifiers are applied.

    Returns (fps, vram): vram is returned alongside fps because it's
    extracted here (including the Apple unified-memory override) but is
    needed by the VRAM-penalty and frame-generation steps that follow.
    """
    if isinstance(cpu_data, dict):
        cpu_score = cpu_data.get("power_score", 50.0)
        cpu_name  = cpu_data.get("name", "")
    else:
        cpu_score = float(cpu_data)
        cpu_name  = ""

    if isinstance(gpu_data, dict):
        gpu_score = gpu_data.get("power_score", 50.0)
        gpu_name  = gpu_data.get("name", "")
        vram      = gpu_data.get("vram", 8) or 8
    else:
        gpu_score = float(gpu_data)
        gpu_name  = ""
        vram      = 8

    # Apple unified memory = unlimited VRAM for our purposes
    if "apple" in gpu_name.lower():
        vram = 64

    diff_mult = game.get("difficulty_multiplier", 1.0)

    # AMD X3D gaming buff (~18 % more due to 3D V-Cache)
    if "X3D" in cpu_name.upper():
        cpu_score *= bc.X3D_CACHE_FPS_BUFF

    # Resolution shifts CPU/GPU relevance:
    #   1080p → CPU matters more  (bottleneck often CPU)
    #   4K    → ~90 % GPU-limited
    if resolution == "1080p":
        g_w, c_w = bc.GPU_WEIGHT_1080P, bc.CPU_WEIGHT_1080P
    elif resolution == "1440p":
        g_w, c_w = bc.GPU_WEIGHT_1440P, bc.CPU_WEIGHT_1440P
    else:  # 4k
        g_w, c_w = bc.GPU_WEIGHT_4K, bc.CPU_WEIGHT_4K

    base_raw = (gpu_score * g_w) + (cpu_score * c_w)
    fps_base = base_raw / diff_mult

    # Resolution scaling (each game has individual values)
    res_key   = f"res_{resolution}_scaling"
    res_scale = game.get(res_key, 1.0)

    # Quality settings scaling
    setting_key_map = {
        "Low":    "low_scaling",
        "Medium": "med_scaling",
        "High":   "high_scaling",
        "Ultra":  "ultra_scaling",
    }
    qual_key   = setting_key_map.get(settings, "high_scaling")
    qual_scale = game.get(qual_key, 1.0)

    # Apply scalings multiplicatively (they're already tuned per-game in DB)
    fps = fps_base * res_scale * qual_scale
    return fps, vram


def _apply_vram_penalty(fps, vram, resolution, settings, game):
    """
    Applies the VRAM-shortage penalty.

    KEY INSIGHT: VRAM penalty depends heavily on the GAME.
    Heavy games (Cyberpunk, Alan Wake 2) use 12-18 GB at 4K Ultra → full penalty.
    Light games (CS2, Valorant, LoL, Fortnite) use < 6 GB at 4K → NO penalty on 8GB.
    Medium games (GTA V, CoD, RDR2) use 7-10 GB at 4K Ultra → scaled penalty.

    We use difficulty_multiplier as a VRAM demand proxy:
      diff < 1.6   = very light (Valorant, CS2, LoL, OW2)     → NO VRAM PENALTY at 8GB
      diff 1.6-3.0 = moderate (GTA V, CoD, Apex, Fortnite)    → vram_demand ≈ 0.40-0.65
      diff 3.0-5.0 = demanding (Elden Ring, RDR2, Hogwarts)   → vram_demand ≈ 0.70-0.90
      diff > 5.0   = extreme VRAM (Cyberpunk, Alan Wake)      → vram_demand = 1.00

    Returns (fps, vram_ok, vram_sufficient, vram_penalty_applied):
      vram_ok               - False if a penalty was applied this call
      vram_sufficient       - False if VRAM is below the "recommended"
                               tier for this resolution (read later by
                               the frame-generation step)
      vram_penalty_applied  - the multiplier that was applied, so the
                               upscaling step can undo it when the GPU
                               ends up rendering at a lower internal res
    """
    diff_mult = game.get("difficulty_multiplier", 1.0)
    raw_demand = min(diff_mult / bc.VRAM_DEMAND_DIFFICULTY_DIVISOR, 1.0)   # 0.0 – 1.0
    vram_demand = max(bc.VRAM_DEMAND_FLOOR, raw_demand)                   # floor keeps math clean

    # THRESHOLD: If vram_demand is below this (diff < ~1.6), the game
    # doesn't load VRAM heavily enough to cause overflow — skip penalty entirely.
    apply_vram_penalty = (vram_demand >= bc.VRAM_PENALTY_DEMAND_THRESHOLD)

    vram_ok = True
    vram_sufficient = True
    vram_penalty_applied = 1.0  # track exact penalty for the undo step

    if resolution == "4k":
        if settings in ("Ultra", "High") and apply_vram_penalty:
            if vram < 8:
                pen = bc.VRAM_PENALTY_4K_ULTRA_UNDER_8GB
                base_pen = pen + (1.0 - pen) * (1.0 - vram_demand)  # heavy=pen, light→1.0
                fps *= base_pen
                vram_penalty_applied = base_pen
                vram_ok = False
            elif vram < 10:
                pen = bc.VRAM_PENALTY_4K_ULTRA_UNDER_10GB
                base_pen = pen + (1.0 - pen) * (1.0 - vram_demand)
                fps *= base_pen
                vram_penalty_applied = base_pen
                vram_ok = False
            elif vram < 12:
                pen = bc.VRAM_PENALTY_4K_ULTRA_UNDER_12GB
                base_pen = pen + (1.0 - pen) * (1.0 - vram_demand)
                fps *= base_pen
                vram_penalty_applied = base_pen
                vram_ok = False
            elif vram < 16:
                pen = bc.VRAM_PENALTY_4K_ULTRA_UNDER_16GB
                base_pen = pen + (1.0 - pen) * (1.0 - vram_demand)
                fps *= base_pen
                vram_penalty_applied = base_pen
                vram_ok = False
        elif vram < 8 and apply_vram_penalty:  # non-Ultra at 4K
            fps *= bc.VRAM_PENALTY_4K_NON_ULTRA_UNDER_8GB
            vram_penalty_applied = bc.VRAM_PENALTY_4K_NON_ULTRA_UNDER_8GB
            vram_ok = False
        if vram < bc.VRAM_SUFFICIENT_4K_GB:
            vram_sufficient = False

    elif resolution == "1440p":
        if vram < 6:
            pen = bc.VRAM_PENALTY_1440P_UNDER_6GB
            base_pen = pen + (1.0 - pen) * (1.0 - vram_demand)
            fps *= base_pen
            vram_penalty_applied = base_pen
            vram_ok = False
        elif settings == "Ultra" and vram < 8:
            pen = bc.VRAM_PENALTY_1440P_ULTRA_UNDER_8GB
            base_pen = pen + (1.0 - pen) * (1.0 - vram_demand)
            fps *= base_pen
            vram_penalty_applied = base_pen
            vram_ok = False
        if vram < bc.VRAM_SUFFICIENT_1440P_GB:
            vram_sufficient = False

    else:  # 1080p — VRAM rarely matters
        if vram < 4:
            fps *= bc.VRAM_PENALTY_1080P_UNDER_4GB
            vram_penalty_applied = bc.VRAM_PENALTY_1080P_UNDER_4GB
            vram_ok = False
        elif vram < 6:
            fps *= bc.VRAM_PENALTY_1080P_UNDER_6GB
            vram_penalty_applied = bc.VRAM_PENALTY_1080P_UNDER_6GB
            vram_ok = False
        if vram < bc.VRAM_SUFFICIENT_1080P_GB:
            vram_sufficient = False

    return fps, vram_ok, vram_sufficient, vram_penalty_applied


def _apply_upscaling(fps, upscaling, resolution, vram_ok, vram_penalty_applied, game):
    """
    Applies the DLSS/FSR/XeSS upscaling multiplier and undoes (fully or
    partially) the VRAM penalty, since upscaling renders at a lower
    internal resolution and relieves VRAM pressure.

    Returns (fps, upscaling_supported). If the game doesn't support the
    requested tech, upscaling_supported is False and fps is returned
    unmodified (native). The caller must stop and return immediately in
    that case — matching the original function's behavior of skipping
    frame generation and RAM impact entirely when upscaling falls back
    to native.
    """
    up = upscaling.lower()

    # Gate: check if the game actually supports the selected upscaling tech.
    # If not, treat as Native (no boost). Defaults to 1 (supported) for
    # backwards compatibility if the column doesn't exist.
    game_dlss = game.get("supports_dlss", 1)
    game_fsr  = game.get("supports_fsr",  1)
    game_xess = game.get("supports_xess", 0)

    upscaling_supported = True
    if "dlss" in up and not game_dlss:
        upscaling_supported = False      # e.g. Elden Ring + DLSS -> Native
    elif "fsr" in up and not game_fsr:
        upscaling_supported = False      # e.g. Quake II RTX + FSR -> Native
    elif "xess" in up and not game_xess:
        upscaling_supported = False      # XeSS not supported

    if not upscaling_supported:
        return fps, False

    # Technology efficiency delta vs DLSS reference
    if "fsr" in up:
        tech_scale = bc.UPSCALING_TECH_SCALE_FSR
    elif "xess" in up:
        tech_scale = bc.UPSCALING_TECH_SCALE_XESS
    else:
        tech_scale = bc.UPSCALING_TECH_SCALE_DLSS

    if "dlaa" in up or ("native" in up and "aa" in up):
        up_mult = bc.UPSCALING_MULT_DLAA

    elif "ultra performance" in up:
        # 4K->1080p / 1440p->720p render -- extreme load reduction
        up_mult = bc.UPSCALING_MULT_ULTRA_PERFORMANCE.get(resolution, 2.05)

    elif "performance" in up:
        # 4K->~1080p / 1440p->~960p render
        up_mult = bc.UPSCALING_MULT_PERFORMANCE.get(resolution, 1.72)

    elif "balanced" in up:
        # 4K->~1200p / 1440p->~1080p render
        up_mult = bc.UPSCALING_MULT_BALANCED.get(resolution, 1.50)

    elif "quality" in up:
        # 4K->~1440p / 1440p->~1080p render
        up_mult = bc.UPSCALING_MULT_QUALITY.get(resolution, 1.38)

    else:
        up_mult = bc.UPSCALING_MULT_NATIVE

    # Apply technology efficiency delta (only for non-native modes)
    if up_mult > 1.0:
        up_mult = (up_mult - 1.0) * tech_scale + 1.0

    # VRAM UNDO: GPU renders at lower res -> VRAM pressure drops.
    # Performance / Ultra Perf  -> full VRAM relief (renders at 720-1080p)
    # Balanced / Quality        -> partial relief (renders at 60-70% output res)
    if not vram_ok and up_mult > bc.UPSCALING_VRAM_UNDO_MIN_MULT:
        if "ultra performance" in up or "performance" in up:
            fps /= vram_penalty_applied          # fully restore pre-penalty FPS
        elif "balanced" in up or "quality" in up:
            undo_ratio = bc.UPSCALING_BALANCED_QUALITY_UNDO_RATIO
            partial_undo = 1.0 + (1.0 / vram_penalty_applied - 1.0) * undo_ratio
            fps *= partial_undo                  # undo part of the VRAM penalty

    fps *= up_mult
    return fps, True


def _apply_frame_generation(fps, frame_gen_mode, vram, resolution, vram_sufficient):
    """
    Applies Frame Generation. FG creates AI-generated frames BETWEEN
    rendered frames — the net effect multiplies the final (post-upscaling)
    FPS by net_mult. It requires extra VRAM for frame buffers: if VRAM is
    insufficient, FG causes stuttering and LOWERS fps instead.
    """
    if frame_gen_mode and frame_gen_mode != "Kapalı":
        net_mult = bc.FG_NET_MULT.get(frame_gen_mode, 1.0)

        vram_min_fg = bc.FG_MIN_VRAM_GB.get(resolution, 6)

        if vram < vram_min_fg or not vram_sufficient:
            # VRAM insufficient - Frame Gen HURTS performance
            # The GPU has to swap frame buffers to system RAM = massive slowdown
            fps *= bc.FG_INSUFFICIENT_VRAM_PENALTY
        else:
            # VRAM sufficient - Frame Gen works as intended
            fps *= net_mult

    return fps


def _apply_ram_impact(fps, ram_gb, game, resolution, settings):
    """
    Applies the RAM-capacity impact multiplier. RAM sensitivity is
    game-specific — some games (Cities Skylines 2, MSFS) need much more
    RAM than others before stuttering/paging sets in.
    """
    game_ram_sensitivity = game.get("ram_sensitivity", 1.0)  # 1.0=normal, 1.5=high, 0.7=low

    ram_mult = 1.0
    if ram_gb < 8:
        # Severe bottleneck - constant paging
        ram_mult = bc.RAM_PENALTY_UNDER_8GB * (
            bc.RAM_SENSITIVITY_EXPONENT_UNDER_8GB ** (game_ram_sensitivity - 1.0)
        )  # More penalty for RAM-hungry games
    elif ram_gb < 16:
        if resolution == "4k" or settings == "Ultra":
            # Modern games need 16GB+ for high settings
            ram_mult = bc.RAM_PENALTY_UNDER_16GB_DEMANDING * (
                bc.RAM_SENSITIVITY_EXPONENT_UNDER_16GB_DEMANDING ** (game_ram_sensitivity - 1.0)
            )
        else:
            # Acceptable for 1080p medium/high
            ram_mult = bc.RAM_PENALTY_UNDER_16GB_LIGHT * (
                bc.RAM_SENSITIVITY_EXPONENT_UNDER_16GB_LIGHT ** (game_ram_sensitivity - 1.0)
            )
    elif ram_gb < 32:
        # Sweet spot for most games, but RAM-hungry games still benefit from 32GB
        if game_ram_sensitivity >= bc.RAM_SENSITIVITY_HIGH_THRESHOLD:
            ram_mult = bc.RAM_BONUS_32GB_HUNGRY_GAME
        else:
            ram_mult = bc.RAM_BONUS_32GB_NORMAL_GAME
    else:
        # 32GB+ - excellent for all games
        if game_ram_sensitivity >= bc.RAM_SENSITIVITY_HIGH_THRESHOLD:
            ram_mult = bc.RAM_BONUS_64GB_HUNGRY_GAME
        else:
            ram_mult = bc.RAM_BONUS_64GB_NORMAL_GAME

    return fps * ram_mult


def estimate_fps(cpu_data, gpu_data, game, resolution="1080p",
                 settings="High", upscaling="Native", frame_gen_mode="Kapalı", ram_gb=16):
    """
    Estimates FPS for a game on specified hardware.

    Parameters
    ----------
    cpu_data      : dict or float (power_score)
    gpu_data      : dict or float (power_score)
    game          : dict with difficulty_multiplier and *_scaling fields
    resolution    : "1080p" | "1440p" | "4k"
    settings      : "Low" | "Medium" | "High" | "Ultra"
    upscaling     : upscaling mode label string
    frame_gen_mode: "Kapalı" | "2x" | "3x" | "4x" | "8x"
    ram_gb        : RAM amount in GB (default: 16)
    """
    fps, vram = _calculate_base_fps(cpu_data, gpu_data, game, resolution, settings)

    fps, vram_ok, vram_sufficient, vram_penalty_applied = _apply_vram_penalty(
        fps, vram, resolution, settings, game
    )

    fps, upscaling_supported = _apply_upscaling(
        fps, upscaling, resolution, vram_ok, vram_penalty_applied, game
    )
    if not upscaling_supported:
        # Fall back to native — no upscaling boost, and (matching the
        # original behavior) frame generation / RAM impact are skipped.
        return max(1, round(fps))

    fps = _apply_frame_generation(fps, frame_gen_mode, vram, resolution, vram_sufficient)
    fps = _apply_ram_impact(fps, ram_gb, game, resolution, settings)

    return max(int(fps), 0)
