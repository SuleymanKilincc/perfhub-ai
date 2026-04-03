"""
Scoring Engine - v3.0
Handles system scoring, bottleneck analysis, and accurate FPS estimation.
"""

# ─── GPU tier lookup: rough "raw render budget" per power_score unit ──────────
# In practice: (gpu_score * GPU_WEIGHT + cpu_score * CPU_WEIGHT) → raw frames
#
# Gaming is ~70-75 % GPU-bound at medium-high resolution.
# CPU matters more for 1080p / CPU-heavy games; GPU dominates 1440p/4K.
GPU_WEIGHT  = 2.2   # scales the GPU power_score to "raw frame equivalents"
CPU_WEIGHT  = 0.55  # CPU contributes significantly at low res, but less at 4K


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
    if resolution == "1080p":
        g_w, c_w = 1.90, 0.75
    elif resolution == "1440p":
        g_w, c_w = 2.20, 0.55
    else:  # 4k
        g_w, c_w = 2.50, 0.35

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

    # ── 6. VRAM penalty ─────────────────────────────────────────────────
    # Only penalize when VRAM is genuinely insufficient for the task
    vram_ok = True
    if resolution == "1440p":
        if settings == "Ultra" and vram < 10: fps *= 0.82; vram_ok = False
        elif vram < 8:                         fps *= 0.68; vram_ok = False
    elif resolution == "4k":
        if settings == "Ultra" and vram < 16: fps *= 0.72; vram_ok = False
        if vram < 12:                          fps *= 0.55; vram_ok = False
        if vram < 8:                           fps *= 0.30; vram_ok = False  # Unplayable

    # ── 7. AI Upscaling multiplier ───────────────────────────────────────
    up = upscaling.lower()
    if "dlaa" in up or ("native" in up and "aa" in up):
        up_mult = 0.94   # slight AA cost
    elif "quality" in up:
        up_mult = 1.23
    elif "balanced" in up:
        up_mult = 1.40
    elif "ultra performance" in up:
        up_mult = 1.82
    elif "performance" in up:
        up_mult = 1.58
    else:
        up_mult = 1.0    # Native

    fps *= up_mult

    # ── 8. Frame Generation ─────────────────────────────────────────────
    if frame_gen_mode and frame_gen_mode != "Kapalı":
        net_mult = FG_NET_MULT.get(frame_gen_mode, 1.0)

        # VRAM safeguard: FG needs extra frame buffer VRAM
        vram_min_fg = {"1080p": 4, "1440p": 8, "4k": 12}.get(resolution, 4)
        if not vram_ok or vram < vram_min_fg:
            # Already VRAM-starved — FG makes it worse
            fps *= 0.82
        else:
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
