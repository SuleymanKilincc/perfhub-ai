"""
Scoring Engine - v4.0
Handles system scoring, bottleneck analysis, and accurate FPS estimation.
"""

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


def calculate_system_score(cpu_score, gpu_score, ram_gb):
    """
    Returns a 0-100 composite score.
    GPU weighted at 60 %, CPU at 30 %, RAM 10 %. Scores can exceed 100 for
    extreme rigs — we cap the returned value at 100 for the progress bar.
    """
    gpu_w, cpu_w, ram_w = 0.60, 0.30, 0.10

    if ram_gb >= 32:   ram_score = 100
    elif ram_gb >= 16: ram_score = 80
    elif ram_gb >= 8:  ram_score = 50
    else:              ram_score = 25

    raw = (gpu_score * gpu_w) + (cpu_score * cpu_w) + (ram_score * ram_w)
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

# Real-world net FPS multipliers per mode (after latency/overhead cost)
# Frame Gen doubles the output frames, but ~15 % overhead + input latency cost.
FG_NET_MULT = {
    "2x": 1.80,   # 2 frames out per render; ~10 % overhead → net 1.80x
    "3x": 2.55,   # 3:1 ratio, higher overhead
    "4x": 3.20,   # 4:1, significant overhead
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
    # ── 0. Extract scores ───────────────────────────────────────────────
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

    # ── 1. AMD X3D gaming buff (~18 % more due to 3D V-Cache) ──────────
    if "X3D" in cpu_name.upper():
        cpu_score *= 1.18

    # ── 2. Base raw frame budget ─────────────────────────────────────────
    # Resolution shifts CPU/GPU relevance:
    #   1080p → CPU matters more  (bottleneck often CPU)
    #   4K    → ~90 % GPU-limited
    # UPDATED: Increased weights for more realistic FPS
    if resolution == "1080p":
        g_w, c_w = 3.5, 1.5
    elif resolution == "1440p":
        g_w, c_w = 3.8, 1.2
    else:  # 4k
        g_w, c_w = 4.2, 0.9

    base_raw = (gpu_score * g_w) + (cpu_score * c_w)

    # ── 3. Game difficulty ───────────────────────────────────────────────
    diff_mult = game.get("difficulty_multiplier", 1.0)
    fps_base  = base_raw / diff_mult

    # ── 4. Resolution scaling (each game has individual values) ─────────
    res_key    = f"res_{resolution}_scaling"
    res_scale  = game.get(res_key, 1.0)

    # ── 5. Quality settings scaling ──────────────────────────────────────
    setting_key_map = {
        "Low":    "low_scaling",
        "Medium": "med_scaling",
        "High":   "high_scaling",
        "Ultra":  "ultra_scaling",
    }
    qual_key  = setting_key_map.get(settings, "high_scaling")
    qual_scale = game.get(qual_key, 1.0)

    # Apply scalings multiplicatively (they're already tuned per-game in DB)
    fps = fps_base * res_scale * qual_scale

    # ── 6. VRAM penalty ──────────────────────────────────────────────────────
    # KEY INSIGHT: VRAM penalty depends heavily on the GAME.
    # Heavy games (Cyberpunk, Alan Wake 2) use 12-18 GB at 4K Ultra → full penalty.
    # Light games (CS2, Valorant, LoL, Fortnite) use < 6 GB at 4K → NO penalty on 8GB.
    # Medium games (GTA V, CoD, RDR2) use 7-10 GB at 4K Ultra → scaled penalty.
    #
    # We use difficulty_multiplier as a VRAM demand proxy:
    #   diff < 1.6  = very light (Valorant, CS2, LoL, OW2)     → NO VRAM PENALTY at 8GB
    #   diff 1.6-3.0 = moderate (GTA V, CoD, Apex, Fortnite)   → vram_demand ≈ 0.40-0.65
    #   diff 3.0-5.0 = demanding (Elden Ring, RDR2, Hogwarts)   → vram_demand ≈ 0.70-0.90
    #   diff > 5.0   = extreme VRAM (Cyberpunk, Alan Wake)       → vram_demand = 1.00
    diff_mult = game.get("difficulty_multiplier", 2.5)
    raw_demand = min(diff_mult / 5.0, 1.0)   # 0.0 – 1.0
    vram_demand = max(0.10, raw_demand)      # floor keeps math clean

    # THRESHOLD: If vram_demand < 0.32 (diff < ~1.6), the game doesn't
    # load VRAM heavily enough to cause overflow — skip penalty entirely.
    VRAM_PENALTY_THRESHOLD = 0.32
    apply_vram_penalty = (vram_demand >= VRAM_PENALTY_THRESHOLD)

    vram_ok = True
    vram_sufficient = True
    vram_penalty_applied = 1.0  # track exact penalty for the undo step

    if resolution == "4k":
        if settings in ("Ultra", "High") and apply_vram_penalty:
            if vram < 8:
                base_pen = 0.42 + (1.0 - 0.42) * (1.0 - vram_demand)  # heavy=0.42, light→1.0
                fps *= base_pen
                vram_penalty_applied = base_pen
                vram_ok = False
            elif vram < 10:
                base_pen = 0.55 + (1.0 - 0.55) * (1.0 - vram_demand)
                fps *= base_pen
                vram_penalty_applied = base_pen
                vram_ok = False
            elif vram < 12:
                base_pen = 0.78 + (1.0 - 0.78) * (1.0 - vram_demand)
                fps *= base_pen
                vram_penalty_applied = base_pen
                vram_ok = False
            elif vram < 16:
                base_pen = 0.92 + (1.0 - 0.92) * (1.0 - vram_demand)
                fps *= base_pen
                vram_penalty_applied = base_pen
                vram_ok = False
        elif vram < 8 and apply_vram_penalty:  # non-Ultra at 4K
            fps *= 0.88
            vram_penalty_applied = 0.88
            vram_ok = False
        if vram < 12:
            vram_sufficient = False

    elif resolution == "1440p":
        if vram < 6:
            base_pen = 0.72 + (1.0 - 0.72) * (1.0 - vram_demand)
            fps *= base_pen
            vram_penalty_applied = base_pen
            vram_ok = False
        elif settings == "Ultra" and vram < 8:
            base_pen = 0.88 + (1.0 - 0.88) * (1.0 - vram_demand)
            fps *= base_pen
            vram_penalty_applied = base_pen
            vram_ok = False
        if vram < 8:
            vram_sufficient = False

    else:  # 1080p — VRAM rarely matters
        if vram < 4:
            fps *= 0.80
            vram_penalty_applied = 0.80
            vram_ok = False
        elif vram < 6:
            fps *= 0.92
            vram_penalty_applied = 0.92
            vram_ok = False
        if vram < 4:
            vram_sufficient = False

    # -- 7. AI Upscaling multiplier -------------------------------------------
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
        # Fall back to native — no upscaling boost at all
        fps *= 1.0
        return max(1, round(fps))

    # Technology efficiency delta vs DLSS reference
    if "fsr" in up:
        tech_scale = 0.88    # FSR2/3: ~12% less efficient than DLSS per mode
    elif "xess" in up:
        tech_scale = 0.93    # Intel XeSS: ~7% less efficient than DLSS
    else:
        tech_scale = 1.00    # DLSS or generic


    if "dlaa" in up or ("native" in up and "aa" in up):
        up_mult = 0.96       # DLAA: renders at native res with AI AA

    elif "ultra performance" in up:
        # 4K->1080p / 1440p->720p render -- extreme load reduction
        up_mult = {"4k": 3.05, "1440p": 2.05, "1080p": 1.90}.get(resolution, 2.05)

    elif "performance" in up:
        # 4K->~1080p / 1440p->~960p render
        up_mult = {"4k": 2.38, "1440p": 1.72, "1080p": 1.58}.get(resolution, 1.72)

    elif "balanced" in up:
        # 4K->~1200p / 1440p->~1080p render
        up_mult = {"4k": 1.92, "1440p": 1.50, "1080p": 1.43}.get(resolution, 1.50)

    elif "quality" in up:
        # 4K->~1440p / 1440p->~1080p render
        up_mult = {"4k": 1.65, "1440p": 1.38, "1080p": 1.29}.get(resolution, 1.38)

    else:
        up_mult = 1.0        # Native rendering -- no upscaling

    # Apply technology efficiency delta (only for non-native modes)
    if up_mult > 1.0:
        up_mult = (up_mult - 1.0) * tech_scale + 1.0

    # VRAM UNDO: GPU renders at lower res -> VRAM pressure drops.
    # Performance / Ultra Perf  -> full VRAM relief (renders at 720-1080p)
    # Balanced / Quality        -> ~65% relief (renders at 60-70% output res)
    if not vram_ok and up_mult > 1.05:
        if "ultra performance" in up or "performance" in up:
            fps /= vram_penalty_applied          # fully restore pre-penalty FPS
        elif "balanced" in up or "quality" in up:
            partial_undo = 1.0 + (1.0 / vram_penalty_applied - 1.0) * 0.65
            fps *= partial_undo                  # undo ~65% of the VRAM penalty

    fps *= up_mult


    # ── 8. Frame Generation ──────────────────────────────────────────────────
    # Frame Gen creates AI-generated frames BETWEEN rendered frames.
    # Important: FG multiplies the BASE rendered FPS, not the DLSS-output FPS.
    # e.g. if native renders at 60 FPS → DLSS displays 80 FPS → FG creates
    # 1 more per pair → 160 FPS output (≈ 2x the DLSS output).
    # So the net effect: FG multiplies the final (post-DLSS) FPS by net_mult.
    if frame_gen_mode and frame_gen_mode != "Kapalı":
        net_mult = FG_NET_MULT.get(frame_gen_mode, 1.0)

        # CRITICAL: Frame Gen requires extra VRAM for frame buffers
        # If VRAM is insufficient, Frame Gen causes STUTTERING and LOWER FPS
        vram_min_fg = {"1080p": 6, "1440p": 10, "4k": 14}.get(resolution, 6)
        
        if vram < vram_min_fg or not vram_sufficient:
            # VRAM insufficient - Frame Gen HURTS performance
            # The GPU has to swap frame buffers to system RAM = massive slowdown
            fps *= 0.70  # Frame Gen with insufficient VRAM = 30% FPS LOSS (reduced from 35%)
        else:
            # VRAM sufficient - Frame Gen works as intended
            fps *= net_mult

    # ── 9. RAM Impact (Game-Specific) ──────────────────────────────────────
    # RAM affects FPS especially in modern games with large textures/assets
    # Insufficient RAM causes stuttering and lower average FPS
    # Game-specific sensitivity: some games (Cities Skylines 2, MSFS) need much more RAM
    
    game_ram_sensitivity = game.get("ram_sensitivity", 1.0)  # 1.0=normal, 1.5=high, 0.7=low
    
    ram_mult = 1.0
    if ram_gb < 8:
        # Severe bottleneck - constant paging
        base_penalty = 0.65
        ram_mult = base_penalty * (0.85 ** (game_ram_sensitivity - 1.0))  # More penalty for RAM-hungry games
    elif ram_gb < 16:
        if resolution == "4k" or settings == "Ultra":
            # Modern games need 16GB+ for high settings
            base_penalty = 0.78
            ram_mult = base_penalty * (0.90 ** (game_ram_sensitivity - 1.0))
        else:
            # Acceptable for 1080p medium/high
            base_penalty = 0.88
            ram_mult = base_penalty * (0.95 ** (game_ram_sensitivity - 1.0))
    elif ram_gb < 32:
        # Sweet spot for most games, but RAM-hungry games still benefit from 32GB
        if game_ram_sensitivity >= 1.5:
            ram_mult = 0.95  # RAM-hungry games still want more
        else:
            ram_mult = 1.0  # Perfect for normal games
    else:
        # 32GB+ - excellent for all games
        if game_ram_sensitivity >= 1.5:
            ram_mult = 1.05  # RAM-hungry games finally shine
        else:
            ram_mult = 1.02  # Slight benefit for 4K ultra with heavy mods
    
    fps *= ram_mult

    return max(int(fps), 0)
