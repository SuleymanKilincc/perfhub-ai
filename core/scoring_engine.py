"""
Cadence — PerfHub's FPS prediction engine.

Named for frame cadence, since that is what it actually computes: how long a
frame takes, rather than a frames-per-second figure arrived at by multiplying
correction factors together.

System scoring, bottleneck analysis, and FPS estimation.

The FPS model works in frame time rather than fps. Each frame costs the CPU
some milliseconds and the GPU some milliseconds, and those two costs are
affected by completely different things:

    resolution      -> GPU only
    quality preset  -> GPU heavily, CPU lightly
    ray tracing     -> GPU heavily, CPU slightly (BVH work)
    upscaling       -> GPU only (renders fewer pixels)
    frame gen       -> multiplies output frames, needs no CPU simulation

Combining them at the end (rather than multiplying one blended number by a
chain of fudge factors) is what makes the interesting behaviour appear on its
own: CPU-limited games stop scaling with a bigger GPU, 4K shifts the limit
back to the GPU, and frame generation helps most exactly when the CPU is the
wall — because that is what the arithmetic says, not because a special case
was written for it.

Memory is modelled as a separate stage. VRAM demand is compared against the
card's capacity; anything that does not fit spills across PCIe into system
RAM, which is slow, and if system RAM cannot absorb the spill either the game
is reported as unplayable rather than given an optimistic number.
"""
from core import balance_config as bc

ENGINE_NAME = "Cadence"
# Bumped when the model changes in a way that moves predictions. 1.0 is the
# frame-time rewrite, calibrated against 55 measured benchmarks.
ENGINE_VERSION = "1.0"

# ─── GPU tier lookup: rough "raw render budget" per power_score unit ──────────
# Kept for callers that still reference them; the FPS model no longer uses
# these weights, since CPU/GPU balance now comes out of the frame-time blend.
GPU_WEIGHT = 3.8
CPU_WEIGHT = 1.2


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
    "RX 9060": ["2x"],
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


def get_fg_options(gpu_name: str) -> list:
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


# ─────────────────────────────────────────────────────────────────────────────
#  FPS ESTIMATION
# ─────────────────────────────────────────────────────────────────────────────

def _perf(score, exponent):
    """Turn a 0-110 power_score into a throughput multiplier (1.0 at REF_SCORE)."""
    return max(0.05, (max(score, 1.0) / bc.REF_SCORE) ** exponent)


def _extract_hardware(cpu_data, gpu_data):
    """Accepts either a full DB row dict or a bare power_score number."""
    if isinstance(cpu_data, dict):
        cpu_score = cpu_data.get("power_score", 50.0)
        cpu_name = cpu_data.get("name", "") or ""
    else:
        cpu_score, cpu_name = float(cpu_data), ""

    if isinstance(gpu_data, dict):
        gpu_score = gpu_data.get("power_score", 50.0)
        gpu_name = gpu_data.get("name", "") or ""
        vram = gpu_data.get("vram", 8) or 8
        gpu_arch = gpu_data.get("architecture", "") or ""
    else:
        # A bare score carries no architecture, so no generation claim can be
        # made about it either way.
        gpu_score, gpu_name, vram, gpu_arch = float(gpu_data), "", 8, ""

    # Apple unified memory: the GPU can address system RAM, so VRAM pressure
    # is not a meaningful constraint here.
    if "apple" in gpu_name.lower():
        vram = 64

    # A 1.18x bonus for 3D V-Cache used to be applied here, because
    # power_score was a throughput rating and did not carry a gaming-only win.
    # It does now — the CPU scores are a 1080p gaming index, and the model that
    # fills in the unmeasured chips has its own fitted 1.23x X3D multiplier, so
    # applying it again here counted it twice.
    return cpu_score, cpu_name, gpu_score, gpu_name, vram, gpu_arch


def _game_profile(game):
    """
    Read the per-game cost profile, falling back to a derivation from the
    legacy columns when a row predates scripts/migrate_game_profiles.py (for
    example a database freshly seeded by _populate_initial_data).
    """
    gpu_cost = game.get("gpu_cost")
    cpu_cost = game.get("cpu_cost")
    vram_base = game.get("vram_base_gb")
    ram_base = game.get("ram_base_gb")

    if not gpu_cost or not cpu_cost:
        # Legacy fallback: split the old single difficulty number evenly-ish.
        total = (game.get("difficulty_multiplier") or 1.0) / (game.get("res_1080p_scaling") or 1.0)
        blend = (1.0 ** bc.BOTTLENECK_BLEND_K + 1.0) ** (1.0 / bc.BOTTLENECK_BLEND_K)
        gpu_cost = total / blend
        cpu_cost = gpu_cost
    if not vram_base:
        vram_base = max(1.5, min(11.0, 2.2 + 0.85 * (gpu_cost + cpu_cost)))
    if not ram_base:
        ram_base = max(4.0, min(20.0, 5.5 * (game.get("ram_sensitivity") or 1.0)))

    return float(gpu_cost), float(cpu_cost), float(vram_base), float(ram_base)


def _resolve_quality(settings, game):
    """Clamp the requested preset to the range the game actually offers."""
    tier = settings if settings in bc.QUALITY_TIERS else bc.DEFAULT_QUALITY_TIER
    tier_min = game.get("tier_min") or "Low"
    tier_max = game.get("tier_max") or "Ultra"
    order = bc.QUALITY_ORDER
    try:
        i, lo, hi = order.index(tier), order.index(tier_min), order.index(tier_max)
    except ValueError:
        return tier
    return order[max(lo, min(hi, i))]


def _upscaling_profile(upscaling, game):
    """
    Returns (render_scale, pass_cost_ms, active).

    `active` is False when the game doesn't support the requested technology,
    in which case it renders natively — the old engine's behaviour of bailing
    out of the whole calculation at that point (skipping frame generation and
    RAM effects entirely) was a bug, not a feature.
    """
    up = (upscaling or "native").lower()

    supports = {
        "dlss": game.get("supports_dlss", 1),
        "fsr": game.get("supports_fsr", 1),
        "xess": game.get("supports_xess", 0),
    }
    tech = next((t for t in ("dlss", "fsr", "xess") if t in up), None)
    if tech and not supports[tech]:
        return 1.0, 0.0, False

    scale = 1.0
    for keyword, value in bc.UPSCALING_RENDER_SCALE.items():
        if keyword in up:
            scale = value
            break

    if scale >= 1.0 and "dlaa" not in up:
        return 1.0, 0.0, True          # native, no upscaler running

    cost_key = "dlaa" if "dlaa" in up else (tech or "dlss")
    pass_cost = bc.UPSCALING_PASS_COST_MS.get(cost_key, bc.DEFAULT_UPSCALING_PASS_COST_MS)
    return scale, pass_cost, True


def _frame_times(gpu_cost, cpu_cost, gpu_score, cpu_score, resolution, quality,
                 ray_tracing, path_tracing, render_scale, upscale_pass_ms,
                 frame_gen_mode):
    """Per-frame GPU and CPU cost in milliseconds, before memory effects."""
    q_gpu, q_cpu, _ = bc.quality_multipliers(quality)

    # GPU: pixels × quality × ray tracing, divided by throughput.
    pixels = bc.RESOLUTION_PIXELS.get(resolution, 1.0) ** bc.RES_PIXEL_EXPONENT
    # Upscaling shrinks the rendered pixel count, but part of the frame is
    # always done at output resolution.
    if render_scale < 1.0:
        pixel_work = render_scale ** 2
        pixels *= (pixel_work * (1 - bc.UPSCALING_UNSCALED_FRACTION)
                   + bc.UPSCALING_UNSCALED_FRACTION)

    rt_gpu = bc.PT_GPU_COST_MULT if path_tracing else (bc.RT_GPU_COST_MULT if ray_tracing else 1.0)
    rt_cpu = bc.PT_CPU_COST_MULT if path_tracing else (bc.RT_CPU_COST_MULT if ray_tracing else 1.0)

    ft_gpu = bc.GPU_MS_CONST * gpu_cost * pixels * q_gpu * rt_gpu / _perf(gpu_score, bc.GPU_PERF_EXPONENT)
    ft_gpu += upscale_pass_ms

    # Generating extra frames is GPU work on top of the rendered frame.
    if frame_gen_mode in bc.FG_GPU_OVERHEAD:
        ft_gpu *= (1.0 + bc.FG_GPU_OVERHEAD[frame_gen_mode])

    # CPU: independent of resolution, lightly affected by quality.
    ft_cpu = bc.CPU_MS_CONST * cpu_cost * q_cpu * rt_cpu / _perf(cpu_score, bc.CPU_PERF_EXPONENT)

    return ft_gpu, ft_cpu


def _blend_frame_time(ft_gpu, ft_cpu):
    """Soft-max of the two limits — whichever is slower dominates."""
    k = bc.BOTTLENECK_BLEND_K
    return (ft_cpu ** k + ft_gpu ** k) ** (1.0 / k)


def _vram_demand(vram_base, quality, resolution, render_scale,
                 ray_tracing, path_tracing, frame_gen_mode):
    """How much VRAM the game wants, in GB."""
    _, _, q_vram = bc.quality_multipliers(quality)
    demand = vram_base * q_vram * bc.RES_VRAM_FACTOR.get(resolution, 1.0)

    # Rendering at a lower internal resolution shrinks the framebuffers, but
    # not the textures, so only part of the demand comes down.
    if render_scale < 1.0:
        demand *= (0.72 + 0.28 * render_scale ** 2)

    if path_tracing:
        demand += bc.PT_VRAM_ADD_GB
    elif ray_tracing:
        demand += bc.RT_VRAM_ADD_GB

    demand += bc.FG_VRAM_ADD_GB.get(frame_gen_mode, 0.0)
    return demand


def _vram_allocation(working_gb, vram_available):
    """
    What the game will actually reserve, as opposed to what a frame needs.

    Engines cache into spare VRAM, so allocation tracks the card as much as the
    game. This is what an overlay reports, and it is only useful for telling
    the user whether the card will fill up — not for predicting frame rate.
    """
    wanted = working_gb * bc.VRAM_ALLOC_APPETITE + bc.VRAM_ALLOC_HEADROOM_GB
    return min(wanted, vram_available * bc.VRAM_ALLOC_CAPACITY_LIMIT)


def _memory_pressure(vram_needed, vram_available, ram_gb, ram_base_gb):
    """
    Model what happens when the working set does not fit in VRAM.

    `vram_needed` is the *working set* — what a frame genuinely requires.
    Allocation is handled separately, because a game reserving more than the
    card holds is normal and mostly harmless: the driver evicts the surplus
    cache. It costs smoothness, not average frame rate.

    Returns (multiplier, status, warnings).

    Status is one of:
        ok           — everything fits, cache included
        vram_tight   — the frame fits but the cache does not; expect stutter
        vram_spill   — the frame itself does not fit; slow but playable
        unplayable   — overflowing with nowhere to spill to
    """
    notes = []
    ram_free = ram_gb - ram_base_gb - bc.OS_RAM_RESERVE_GB
    overflow = vram_needed - vram_available

    # System RAM alone can be the problem even when VRAM is fine.
    ram_mult = 1.0
    if ram_free < 0:
        ram_mult = bc.RAM_SHORTFALL_PENALTY
        notes.append({"code": "ram_short",
                      "game_ram_gb": ram_base_gb, "ram_gb": ram_gb})
    elif ram_free > 8:
        ram_mult = bc.RAM_ABUNDANCE_BONUS

    if overflow <= 0:
        # The frame fits. Whether the game's texture cache also fits decides
        # between "smooth" and "fine on average but stutters when the camera
        # moves somewhere new".
        wanted = vram_needed * bc.VRAM_ALLOC_APPETITE + bc.VRAM_ALLOC_HEADROOM_GB
        if wanted > vram_available:
            return (bc.VRAM_TIGHT_PENALTY * ram_mult, "vram_tight", notes + [
                {"code": "vram_tight", "needed_gb": vram_needed,
                 "wanted_gb": wanted, "capacity_gb": vram_available}
            ])
        return ram_mult, ("ok" if not notes else "ram_short"), notes

    # Overflowing. The spilled data has to live in system RAM.
    notes.append({"code": "vram_spill", "needed_gb": vram_needed,
                  "capacity_gb": vram_available, "overflow_gb": overflow})

    if ram_free < overflow * bc.RAM_UNPLAYABLE_SHORTFALL_RATIO:
        # Nothing meaningful left to spill into. Merely having less free RAM
        # than the overflow is not enough — Windows pages the rest to disk and
        # the game stays playable, just slower.
        notes.append({"code": "unplayable", "overflow_gb": overflow,
                      "ram_gb": ram_gb, "suggested_ram_gb": int(ram_gb * 2)})
        return (bc.VRAM_SPILL_FLOOR * 0.35, "unplayable", notes)

    # Spilling, but system RAM can absorb it. Streaming over PCIe is slow and
    # gets worse the further over the limit you are.
    severity = overflow / max(vram_available, 1.0)
    mult = 1.0 / (1.0 + bc.VRAM_SPILL_SEVERITY * severity)

    # How comfortably RAM can host the spill matters too. Barely fitting means
    # the OS is constantly evicting and re-fetching; lots of headroom lets it
    # keep a stable cache. This is what separates "16 GB, technically survives"
    # from "32 GB, actually playable" in the same overflow scenario.
    comfort = min(1.0, ram_free / max(overflow * bc.RAM_SPILL_COMFORT_RATIO, 0.1))
    mult *= bc.RAM_SPILL_CRAMPED_PENALTY + (1.0 - bc.RAM_SPILL_CRAMPED_PENALTY) * comfort
    if comfort < 0.6:
        notes.append({"code": "ram_cramped", "ram_gb": ram_gb,
                      "suggested_ram_gb": int(ram_gb * 2)})

    mult = max(bc.VRAM_SPILL_FLOOR, mult)
    return (mult * ram_mult, "vram_spill", notes)


# ─────────────────────────────────────────────────────────────────────────────
#  Note rendering
#
#  The model reports what happened as a code and the numbers behind it; this
#  turns that into a sentence. Keeping the prose out of the model is what lets
#  the website show these in another language without the engine knowing one
#  exists — and it makes the conformance test compare structure rather than
#  wording, so rephrasing a warning no longer breaks it.
#
#  `warnings` is still returned, and still in Turkish, because the desktop
#  application reads it.
# ─────────────────────────────────────────────────────────────────────────────

def _render_note(note):
    c = note["code"]
    if c == "ram_short":
        return (f"Sistem RAM'i yetersiz: oyun ~{note['game_ram_gb']:.0f} GB istiyor, "
                f"{note['ram_gb']} GB RAM ile takas (paging) başlıyor.")
    if c == "vram_tight":
        return (f"VRAM sınırda: kare için ~{note['needed_gb']:.1f} GB yetiyor ama oyun "
                f"~{note['wanted_gb']:.1f} GB önbellek ayırmak istiyor "
                f"({note['capacity_gb']} GB kart). Ortalama FPS iyi kalır, ancak "
                f"yeni sahnelere geçerken takılma olabilir.")
    if c == "vram_spill":
        return (f"VRAM yetersiz: ~{note['needed_gb']:.1f} GB ihtiyaç, "
                f"{note['capacity_gb']} GB kart "
                f"(~{note['overflow_gb']:.1f} GB taşıyor).")
    if c == "unplayable":
        return (f"Taşan {note['overflow_gb']:.1f} GB'ı karşılayacak sistem RAM'i de yok "
                f"({note['ram_gb']} GB). Oyun çökebilir veya oynanamaz hale gelir — "
                f"{note['suggested_ram_gb']} GB RAM bu senaryoyu kurtarır.")
    if c == "ram_cramped":
        return (f"Sistem RAM'i taşmayı ancak zar zor karşılıyor; daha fazla RAM "
                f"({note['suggested_ram_gb']} GB) bu senaryoda gözle görülür fark yaratır.")
    if c == "upscaling_unsupported":
        return ("Bu oyun seçilen upscaling teknolojisini desteklemiyor; "
                "native çözünürlükte hesaplandı.")
    if c == "legacy_gpu":
        return (f"Bu kart {note['architecture']} nesli ve elimizdeki ölçümlerin "
                f"tamamı 2019 sonrası mimarilerde. Bu nesilde tahmin "
                f"doğrulanmadı — dışarıdan gelen sonuçlar hem çok yüksek hem "
                f"tutarlı çıktığı için hangi yönde saptığını da söyleyemiyoruz.")
    if c == "fps_cap":
        return (f"Bu oyun varsayılan halinde {note['cap']} FPS ile sınırlı. "
                f"Donanımın {note['uncapped']} FPS'e yetiyor, ancak sınır "
                f"kaldırılmadan {note['cap']} FPS görürsün.")
    return ""


def estimate_fps_detailed(cpu_data, gpu_data, game, resolution="1080p",
                          settings="High", upscaling="Native",
                          frame_gen_mode="Kapalı", ram_gb=16,
                          ray_tracing=False, path_tracing=False):
    """
    Full estimate with diagnostics.

    Returns a dict:
        fps              final estimated frames per second
        rendered_fps     before frame generation
        status           ok | ram_short | vram_tight | vram_spill | unplayable
        bottleneck       'CPU' or 'GPU'
        vram_needed_gb   estimated VRAM working set
        warnings         human-readable notes for the UI
    """
    cpu_score, _, gpu_score, _, vram, gpu_arch = _extract_hardware(cpu_data, gpu_data)
    gpu_cost, cpu_cost, vram_base, ram_base = _game_profile(game)

    quality = _resolve_quality(settings, game)

    # Ray tracing only applies where the game supports it.
    path_tracing = bool(path_tracing) and bool(game.get("supports_pt", 0))
    ray_tracing = bool(ray_tracing) and bool(game.get("supports_rt", 0))

    render_scale, upscale_pass_ms, upscale_active = _upscaling_profile(upscaling, game)
    fg_mode = frame_gen_mode if frame_gen_mode in bc.FG_OUTPUT_MULTIPLIER else None

    ft_gpu, ft_cpu = _frame_times(
        gpu_cost, cpu_cost, gpu_score, cpu_score, resolution, quality,
        ray_tracing, path_tracing, render_scale, upscale_pass_ms, fg_mode,
    )
    rendered_fps = 1000.0 / _blend_frame_time(ft_gpu, ft_cpu)

    vram_needed = _vram_demand(vram_base, quality, resolution, render_scale,
                               ray_tracing, path_tracing, fg_mode)
    mem_mult, status, notes = _memory_pressure(vram_needed, vram, ram_gb, ram_base)
    rendered_fps *= mem_mult

    # Generated frames need no CPU simulation, which is why frame generation
    # is most effective exactly when the CPU is the limit.
    fps = rendered_fps * bc.FG_OUTPUT_MULTIPLIER.get(fg_mode, 1.0) if fg_mode else rendered_fps

    if not upscale_active:
        notes.append({"code": "upscaling_unsupported"})

    # No measurement exists on this architecture. See
    # LEGACY_GPU_ARCHITECTURES for why no correction is applied.
    if gpu_arch in bc.LEGACY_GPU_ARCHITECTURES:
        notes.append({"code": "legacy_gpu", "architecture": gpu_arch})

    # Some games ship with a hard frame rate limit. Reporting only the capped
    # figure would make every capable GPU look identical, so the uncapped
    # estimate is kept and the cap is surfaced as a note instead.
    uncapped_fps = max(int(round(fps)), 0)
    fps_cap = game.get("fps_cap") or 0
    if fps_cap and uncapped_fps > fps_cap:
        notes.append({"code": "fps_cap", "cap": int(fps_cap),
                      "uncapped": uncapped_fps})

    # What the reader will see when the scene gets busy. Measured as a ratio
    # of 1% low to average across 336 rows, where it came out a property of the
    # game (0.53 in Counter-Strike 2, 0.88 in Hitman 3) and flat across CPU
    # scores from 50 to 100. Games with no measurement carry the global mean
    # and say so through fps_low_measured, so an assumed range is never shown
    # with the confidence of a measured one.
    low_ratio = game.get("fps_low_ratio") or bc.FPS_LOW_RATIO_DEFAULT
    shown_fps = int(fps_cap) if fps_cap and uncapped_fps > fps_cap else uncapped_fps
    fps_low = max(int(round(shown_fps * low_ratio)), 0)

    return {
        "fps": uncapped_fps,
        "fps_low": fps_low,
        "fps_low_measured": bool(game.get("fps_low_measured")),
        "capped_fps": int(fps_cap) if fps_cap and uncapped_fps > fps_cap else None,
        "rendered_fps": max(int(round(rendered_fps)), 0),
        "status": status,
        "bottleneck": "CPU" if ft_cpu > ft_gpu else "GPU",
        # What a frame needs, versus what the game will reserve on this card.
        "vram_needed_gb": round(vram_needed, 1),
        "vram_alloc_gb": round(_vram_allocation(vram_needed, vram), 1),
        "vram_available_gb": vram,
        "quality": quality,
        # Structured first, prose derived from it. See _render_note.
        "notes": notes,
        "warnings": [_render_note(n) for n in notes],
    }


def estimate_fps(cpu_data, gpu_data, game, resolution="1080p",
                 settings="High", upscaling="Native", frame_gen_mode="Kapalı",
                 ram_gb=16, ray_tracing=False, path_tracing=False):
    """
    Estimates FPS for a game on specified hardware.

    Parameters
    ----------
    cpu_data      : dict or float (power_score)
    gpu_data      : dict or float (power_score)
    game          : dict describing the game (see migrate_game_profiles.py)
    resolution    : "1080p" | "1440p" | "4k"
    settings      : "Very Low" | "Low" | "Medium" | "High" | "Ultra" | "Extreme"
    upscaling     : upscaling mode label string
    frame_gen_mode: "Kapalı" | "2x" | "3x" | "4x"
    ram_gb        : RAM amount in GB (default: 16)
    ray_tracing   : enable ray tracing where the game supports it
    path_tracing  : enable path tracing where the game supports it

    Use estimate_fps_detailed() when the caller can surface VRAM/RAM warnings.
    """
    return estimate_fps_detailed(
        cpu_data, gpu_data, game, resolution, settings, upscaling,
        frame_gen_mode, ram_gb, ray_tracing, path_tracing,
    )["fps"]
