/**
 * Cadence — the FPS model, ported from core/scoring_engine.py.
 *
 * Why a second implementation exists at all: the prediction is a pure function
 * over a 84 KB catalogue and needs no secrets, so running it here removes the
 * server from the critical path entirely. The backend is on a free tier that
 * sleeps after 15 minutes and takes ~50 seconds to wake, which is the single
 * worst thing about the site. Only the AI chat genuinely needs a server, and
 * nobody minds waiting for a chat reply.
 *
 * The obvious risk is drift between the two copies. Three things hold it down:
 *
 *   1. Every constant and the whole catalogue are GENERATED from the Python
 *      source by scripts/export_engine_data.py. They cannot drift, only go
 *      stale — and a stale export is visible as a failing conformance run.
 *   2. scripts/conformance_test.py runs both implementations over a grid of
 *      inputs and fails on any disagreement.
 *   3. This file mirrors the Python function-for-function, in the same order,
 *      so the two can be read side by side.
 *
 * Keep that structure when changing it. A clever refactor here buys nothing
 * and costs the ability to diff the two.
 */
import * as bc from "./balance.generated";

export type Cpu = {
  name?: string;
  power_score: number;
  form_factor?: string | null;
  cores?: number | null;
};
export type Gpu = {
  name?: string;
  power_score: number;
  vram?: number | null;
  architecture?: string | null;
  form_factor?: string | null;
};

export type Game = {
  name: string;
  gpu_cost?: number | null;
  cpu_cost?: number | null;
  vram_base_gb?: number | null;
  ram_base_gb?: number | null;
  tier_min?: string | null;
  tier_max?: string | null;
  fps_cap?: number | null;
  fps_low_ratio?: number | null;
  fps_low_measured?: number | null;
  supports_rt?: number | null;
  supports_pt?: number | null;
  supports_dlss?: number | null;
  supports_fsr?: number | null;
  supports_xess?: number | null;
  difficulty_multiplier?: number | null;
  res_1080p_scaling?: number | null;
  ram_sensitivity?: number | null;
  // Carried on the catalogue row but not used by the model: these describe
  // what frame rate is *enough*, which is a presentation question, not a
  // prediction one. See scripts/curate_games.py.
  competitive?: number | null;
  target_fps?: number | null;
  cover_url?: string | null;
  flags_verified?: number | null;
  measurements?: number | null;
};

/**
 * What the model observed, as a code and the numbers behind it.
 *
 * The prose used to live inside the model, in Turkish, and the conformance
 * test compared it word for word — so rephrasing a warning broke the test, and
 * showing the site in another language was impossible without touching the
 * engine. The model reports structure now and the interface writes the
 * sentence. `warnings` is still produced, from these, because the desktop
 * application reads it.
 */
export type Note =
  | { code: "ram_short"; game_ram_gb: number; ram_gb: number }
  | { code: "vram_tight"; needed_gb: number; wanted_gb: number; capacity_gb: number }
  | { code: "vram_spill"; needed_gb: number; capacity_gb: number; overflow_gb: number }
  | { code: "unplayable"; overflow_gb: number; ram_gb: number; suggested_ram_gb: number }
  | { code: "ram_cramped"; ram_gb: number; suggested_ram_gb: number }
  | { code: "upscaling_unsupported" }
  | { code: "legacy_gpu"; architecture: string }
  | { code: "form_factor_mismatch"; cpu_form: string; gpu_form: string }
  | { code: "few_cores"; cores: number }
  | { code: "fps_cap"; cap: number; uncapped: number };

export type Estimate = {
  fps: number;
  fps_low: number;
  fps_low_measured: boolean;
  capped_fps: number | null;
  rendered_fps: number;
  status: "ok" | "ram_short" | "vram_tight" | "vram_spill" | "unplayable";
  bottleneck: "CPU" | "GPU";
  vram_needed_gb: number;
  vram_alloc_gb: number;
  vram_available_gb: number;
  quality: string;
  notes: Note[];
  warnings: string[];
};

/**
 * Python's round(), which breaks ties to even: round(2.5) is 2, not 3, where
 * Math.round says 3.
 *
 * The tie-breaking is the easy half. The subtle half is that a "tie" has to be
 * judged against the double's real value, not its decimal appearance: 4.65 is
 * actually 4.65000000000000035, so Python rounds it up to 4.7 while scaling by
 * ten first — 4.65 * 10 lands on exactly 46.5 — sees a tie and rounds down to
 * 4.6. The conformance test caught precisely that on two cases out of twelve
 * hundred, which is exactly how often a bug like this would have been noticed
 * in production: never.
 *
 * So the digits are taken from a wide fixed-point expansion and the rounding is
 * done in integer arithmetic, where there is nothing left to lose.
 */
function pyRound(x: number, digits = 0): number {
  if (!Number.isFinite(x)) return x;
  const negative = x < 0;
  const text = Math.abs(x).toFixed(30);
  const dot = text.indexOf(".");
  const whole = text.slice(0, dot);
  const fraction = text.slice(dot + 1);

  const kept = fraction.slice(0, digits);
  const dropped = fraction.slice(digits);

  let scaled = BigInt(whole + kept);
  const first = dropped.charCodeAt(0) - 48;
  let roundUp: boolean;
  if (first > 5) roundUp = true;
  else if (first < 5) roundUp = false;
  else if (/[1-9]/.test(dropped.slice(1))) roundUp = true;
  else roundUp = scaled % 2n === 1n; // a real tie: to even
  if (roundUp) scaled += 1n;

  const digitsOut = scaled.toString().padStart(digits + 1, "0");
  const cut = digitsOut.length - digits;
  const value = Number(
    digits > 0 ? `${digitsOut.slice(0, cut)}.${digitsOut.slice(cut)}` : digitsOut,
  );
  return negative ? -value : value;
}

/** Python's f"{x:.Nf}". */
function fmt(x: number, digits: number): string {
  return pyRound(x, digits).toFixed(digits);
}

const asRecord = <T,>(o: unknown) => o as Record<string, T>;

// ─── Frame generation support ────────────────────────────────────────────────

export function getFgOptions(gpuName: string): string[] {
  const upper = (gpuName || "").toUpperCase();
  const options = ["Kapalı"];
  // Insertion order matters: "RTX 5070 Ti" has to be tested before "RTX 5070".
  for (const [keyword, mults] of Object.entries(asRecord<string[]>(bc.FG_SUPPORT))) {
    if (upper.includes(keyword.toUpperCase())) {
      options.push(...mults);
      break;
    }
  }
  return options;
}

// ─── FPS estimation ──────────────────────────────────────────────────────────

function perf(score: number, exponent: number): number {
  return Math.max(0.05, (Math.max(score, 1.0) / bc.REF_SCORE) ** exponent);
}

function extractHardware(cpu: Cpu | number, gpu: Gpu | number) {
  let cpuScore: number, cpuName: string, cpuForm: string, cpuCores: number;
  if (typeof cpu === "object") {
    cpuScore = cpu.power_score ?? 50.0;
    cpuName = cpu.name || "";
    cpuForm = cpu.form_factor || "";
    cpuCores = cpu.cores || 0;
  } else {
    cpuScore = cpu;
    cpuName = "";
    cpuForm = "";
    cpuCores = 0;
  }

  let gpuScore: number, gpuName: string, vram: number, gpuArch: string, gpuForm: string;
  if (typeof gpu === "object") {
    gpuScore = gpu.power_score ?? 50.0;
    gpuName = gpu.name || "";
    vram = gpu.vram || 8;
    gpuArch = gpu.architecture || "";
    gpuForm = gpu.form_factor || "";
  } else {
    // A bare score carries no architecture, so no generation claim can be
    // made about it either way.
    gpuScore = gpu;
    gpuName = "";
    vram = 8;
    gpuArch = "";
    gpuForm = "";
  }

  // Apple unified memory: the GPU can address system RAM, so VRAM pressure is
  // not a meaningful constraint here.
  if (gpuName.toLowerCase().includes("apple")) vram = 64;

  return { cpuScore, cpuName, cpuForm, cpuCores, gpuScore, gpuName, vram, gpuArch, gpuForm };
}

function gameProfile(game: Game) {
  let gpuCost = game.gpu_cost;
  let cpuCost = game.cpu_cost;
  let vramBase = game.vram_base_gb;
  let ramBase = game.ram_base_gb;

  if (!gpuCost || !cpuCost) {
    // Legacy fallback for rows predating scripts/migrate_game_profiles.py.
    const total = (game.difficulty_multiplier || 1.0) / (game.res_1080p_scaling || 1.0);
    const blend = (1.0 ** bc.BOTTLENECK_BLEND_K + 1.0) ** (1.0 / bc.BOTTLENECK_BLEND_K);
    gpuCost = total / blend;
    cpuCost = gpuCost;
  }
  if (!vramBase) vramBase = Math.max(1.5, Math.min(11.0, 2.2 + 0.85 * (gpuCost + cpuCost)));
  if (!ramBase) ramBase = Math.max(4.0, Math.min(20.0, 5.5 * (game.ram_sensitivity || 1.0)));

  return { gpuCost, cpuCost, vramBase, ramBase };
}

function resolveQuality(settings: string, game: Game): string {
  const tiers = asRecord<readonly number[]>(bc.QUALITY_TIERS);
  const tier = settings in tiers ? settings : bc.DEFAULT_QUALITY_TIER;
  const order = bc.QUALITY_ORDER as readonly string[];
  const i = order.indexOf(tier);
  const lo = order.indexOf(game.tier_min || "Low");
  const hi = order.indexOf(game.tier_max || "Ultra");
  if (i < 0 || lo < 0 || hi < 0) return tier;
  return order[Math.max(lo, Math.min(hi, i))];
}

function upscalingProfile(upscaling: string, game: Game) {
  const up = (upscaling || "native").toLowerCase();

  // Matches Python's dict.get(key, 1): a column that is present but NULL means
  // "not supported", only a missing column falls back to 1.
  const supports: Record<string, unknown> = {
    dlss: game.supports_dlss === undefined ? 1 : game.supports_dlss,
    fsr: game.supports_fsr === undefined ? 1 : game.supports_fsr,
    xess: game.supports_xess === undefined ? 0 : game.supports_xess,
  };
  const tech = ["dlss", "fsr", "xess"].find((t) => up.includes(t)) ?? null;
  if (tech && !supports[tech]) return { scale: 1.0, passCost: 0.0, active: false };

  let scale = 1.0;
  for (const [keyword, value] of Object.entries(asRecord<number>(bc.UPSCALING_RENDER_SCALE))) {
    if (up.includes(keyword)) {
      scale = value;
      break;
    }
  }

  if (scale >= 1.0 && !up.includes("dlaa")) {
    return { scale: 1.0, passCost: 0.0, active: true }; // native, no upscaler
  }

  const costKey = up.includes("dlaa") ? "dlaa" : tech ?? "dlss";
  const passCost =
    asRecord<number>(bc.UPSCALING_PASS_COST_MS)[costKey] ?? bc.DEFAULT_UPSCALING_PASS_COST_MS;
  return { scale, passCost, active: true };
}

function frameTimes(
  gpuCost: number, cpuCost: number, gpuScore: number, cpuScore: number,
  resolution: string, quality: string, rayTracing: boolean, pathTracing: boolean,
  renderScale: number, upscalePassMs: number, frameGenMode: string | null,
) {
  const [qGpu, qCpu] = bc.qualityMultipliers(quality);

  let pixels =
    (asRecord<number>(bc.RESOLUTION_PIXELS)[resolution] ?? 1.0) ** bc.RES_PIXEL_EXPONENT;
  if (renderScale < 1.0) {
    const pixelWork = renderScale ** 2;
    pixels *= pixelWork * (1 - bc.UPSCALING_UNSCALED_FRACTION) + bc.UPSCALING_UNSCALED_FRACTION;
  }

  const rtGpu = pathTracing ? bc.PT_GPU_COST_MULT : rayTracing ? bc.RT_GPU_COST_MULT : 1.0;
  const rtCpu = pathTracing ? bc.PT_CPU_COST_MULT : rayTracing ? bc.RT_CPU_COST_MULT : 1.0;

  let ftGpu =
    (bc.GPU_MS_CONST * gpuCost * pixels * qGpu * rtGpu) / perf(gpuScore, bc.GPU_PERF_EXPONENT);
  ftGpu += upscalePassMs;

  const fgOverhead = asRecord<number>(bc.FG_GPU_OVERHEAD);
  if (frameGenMode !== null && frameGenMode in fgOverhead) {
    ftGpu *= 1.0 + fgOverhead[frameGenMode];
  }

  const ftCpu = (bc.CPU_MS_CONST * cpuCost * qCpu * rtCpu) / perf(cpuScore, bc.CPU_PERF_EXPONENT);

  return { ftGpu, ftCpu };
}

function blendFrameTime(ftGpu: number, ftCpu: number): number {
  const k = bc.BOTTLENECK_BLEND_K;
  return (ftCpu ** k + ftGpu ** k) ** (1.0 / k);
}

function vramDemand(
  vramBase: number, quality: string, resolution: string, renderScale: number,
  rayTracing: boolean, pathTracing: boolean, frameGenMode: string | null,
): number {
  const qVram = bc.qualityMultipliers(quality)[2];
  let demand = vramBase * qVram * (asRecord<number>(bc.RES_VRAM_FACTOR)[resolution] ?? 1.0);

  if (renderScale < 1.0) demand *= 0.72 + 0.28 * renderScale ** 2;

  if (pathTracing) demand += bc.PT_VRAM_ADD_GB;
  else if (rayTracing) demand += bc.RT_VRAM_ADD_GB;

  demand += (frameGenMode && asRecord<number>(bc.FG_VRAM_ADD_GB)[frameGenMode]) || 0.0;
  return demand;
}

function vramAllocation(workingGb: number, vramAvailable: number): number {
  const wanted = workingGb * bc.VRAM_ALLOC_APPETITE + bc.VRAM_ALLOC_HEADROOM_GB;
  return Math.min(wanted, vramAvailable * bc.VRAM_ALLOC_CAPACITY_LIMIT);
}

function memoryPressure(
  vramNeeded: number, vramAvailable: number, ramGb: number, ramBaseGb: number,
): { mult: number; status: Estimate["status"]; notes: Note[] } {
  const notes: Note[] = [];
  const ramFree = ramGb - ramBaseGb - bc.OS_RAM_RESERVE_GB;
  const overflow = vramNeeded - vramAvailable;

  let ramMult = 1.0;
  if (ramFree < 0) {
    ramMult = bc.RAM_SHORTFALL_PENALTY;
    notes.push({ code: "ram_short", game_ram_gb: ramBaseGb, ram_gb: ramGb });
  } else if (ramFree > 8) {
    ramMult = bc.RAM_ABUNDANCE_BONUS;
  }

  if (overflow <= 0) {
    const wanted = vramNeeded * bc.VRAM_ALLOC_APPETITE + bc.VRAM_ALLOC_HEADROOM_GB;
    if (wanted > vramAvailable) {
      return {
        mult: bc.VRAM_TIGHT_PENALTY * ramMult,
        status: "vram_tight",
        notes: [
          ...notes,
          { code: "vram_tight", needed_gb: vramNeeded, wanted_gb: wanted,
            capacity_gb: vramAvailable },
        ],
      };
    }
    return { mult: ramMult, status: notes.length ? "ram_short" : "ok", notes };
  }

  notes.push({ code: "vram_spill", needed_gb: vramNeeded,
    capacity_gb: vramAvailable, overflow_gb: overflow });

  if (ramFree < overflow * bc.RAM_UNPLAYABLE_SHORTFALL_RATIO) {
    notes.push({ code: "unplayable", overflow_gb: overflow, ram_gb: ramGb,
      suggested_ram_gb: Math.trunc(ramGb * 2) });
    return { mult: bc.VRAM_SPILL_FLOOR * 0.35, status: "unplayable", notes };
  }

  const severity = overflow / Math.max(vramAvailable, 1.0);
  let mult = 1.0 / (1.0 + bc.VRAM_SPILL_SEVERITY * severity);

  const comfort = Math.min(1.0, ramFree / Math.max(overflow * bc.RAM_SPILL_COMFORT_RATIO, 0.1));
  mult *= bc.RAM_SPILL_CRAMPED_PENALTY + (1.0 - bc.RAM_SPILL_CRAMPED_PENALTY) * comfort;
  if (comfort < 0.6) {
    notes.push({ code: "ram_cramped", ram_gb: ramGb,
      suggested_ram_gb: Math.trunc(ramGb * 2) });
  }

  mult = Math.max(bc.VRAM_SPILL_FLOOR, mult);
  return { mult: mult * ramMult, status: "vram_spill", notes };
}

/** Mirrors _render_note in core/scoring_engine.py, character for character. */
export function renderNote(note: Note): string {
  switch (note.code) {
    case "ram_short":
      return `Sistem RAM'i yetersiz: oyun ~${fmt(note.game_ram_gb, 0)} GB istiyor, ` +
        `${note.ram_gb} GB RAM ile takas (paging) başlıyor.`;
    case "vram_tight":
      return `VRAM sınırda: kare için ~${fmt(note.needed_gb, 1)} GB yetiyor ama oyun ` +
        `~${fmt(note.wanted_gb, 1)} GB önbellek ayırmak istiyor ` +
        `(${note.capacity_gb} GB kart). Ortalama FPS iyi kalır, ancak ` +
        `yeni sahnelere geçerken takılma olabilir.`;
    case "vram_spill":
      return `VRAM yetersiz: ~${fmt(note.needed_gb, 1)} GB ihtiyaç, ` +
        `${note.capacity_gb} GB kart ` +
        `(~${fmt(note.overflow_gb, 1)} GB taşıyor).`;
    case "unplayable":
      return `Taşan ${fmt(note.overflow_gb, 1)} GB'ı karşılayacak sistem RAM'i de yok ` +
        `(${note.ram_gb} GB). Oyun çökebilir veya oynanamaz hale gelir — ` +
        `${note.suggested_ram_gb} GB RAM bu senaryoyu kurtarır.`;
    case "ram_cramped":
      return `Sistem RAM'i taşmayı ancak zar zor karşılıyor; daha fazla RAM ` +
        `(${note.suggested_ram_gb} GB) bu senaryoda gözle görülür fark yaratır.`;
    case "upscaling_unsupported":
      return "Bu oyun seçilen upscaling teknolojisini desteklemiyor; " +
        "native çözünürlükte hesaplandı.";
    case "few_cores":
      return `Bu işlemcinin ${note.cores} çekirdeği var. Bazı yeni oyun ` +
        `motorları dörtten fazla iş parçacığı istiyor ve orada puanın ima ` +
        `ettiğinden daha yavaş kalıyor — ölçtüğümüz tek dört çekirdekli çipte ` +
        `tahmin ortalama %12, en ağır oyunda %55 yüksek çıktı. Az iş parçacığı ` +
        `kullanan oyunlar etkilenmiyor.`;
    case "form_factor_mismatch": {
      const [a, b] = note.cpu_form === "laptop"
        ? ["İşlemci", "ekran kartı"] : ["Ekran kartı", "işlemci"];
      return `${a} bir laptop parçası, ${b} ise masaüstü. Bu ikisi aynı ` +
        `bilgisayarda bulunamaz — laptop parçaları anakarta lehimlidir. ` +
        `Sayı hesaplandı ama var olmayan bir sistemi tarif ediyor.`;
    }
    case "legacy_gpu":
      return `Bu kart ${note.architecture} nesli ve elimizdeki ölçümlerin ` +
        `tamamı 2019 sonrası mimarilerde. Bu nesilde tahmin doğrulanmadı — ` +
        `dışarıdan gelen sonuçlar hem çok yüksek hem tutarlı çıktığı için ` +
        `hangi yönde saptığını da söyleyemiyoruz.`;
    case "fps_cap":
      return `Bu oyun varsayılan halinde ${note.cap} FPS ile sınırlı. ` +
        `Donanımın ${note.uncapped} FPS'e yetiyor, ancak sınır ` +
        `kaldırılmadan ${note.cap} FPS görürsün.`;
  }
}

export function estimateFpsDetailed(
  cpuData: Cpu | number,
  gpuData: Gpu | number,
  game: Game,
  resolution = "1080p",
  settings = "High",
  upscaling = "Native",
  frameGenMode = "Kapalı",
  ramGb = 16,
  rayTracing = false,
  pathTracing = false,
): Estimate {
  const { cpuScore, cpuForm, cpuCores, gpuScore, vram, gpuArch, gpuForm } =
    extractHardware(cpuData, gpuData);
  const { gpuCost, cpuCost, vramBase, ramBase } = gameProfile(game);

  const quality = resolveQuality(settings, game);

  const pt = Boolean(pathTracing) && Boolean(game.supports_pt);
  const rt = Boolean(rayTracing) && Boolean(game.supports_rt);

  const { scale: renderScale, passCost, active: upscaleActive } = upscalingProfile(upscaling, game);
  const fgMode = frameGenMode in asRecord<number>(bc.FG_OUTPUT_MULTIPLIER) ? frameGenMode : null;

  const { ftGpu, ftCpu } = frameTimes(
    gpuCost, cpuCost, gpuScore, cpuScore, resolution, quality, rt, pt,
    renderScale, passCost, fgMode,
  );
  let renderedFps = 1000.0 / blendFrameTime(ftGpu, ftCpu);

  const vramNeeded = vramDemand(vramBase, quality, resolution, renderScale, rt, pt, fgMode);
  const { mult, status, notes } = memoryPressure(vramNeeded, vram, ramGb, ramBase);
  renderedFps *= mult;

  const fps = fgMode
    ? renderedFps * (asRecord<number>(bc.FG_OUTPUT_MULTIPLIER)[fgMode] ?? 1.0)
    : renderedFps;

  if (!upscaleActive) notes.push({ code: "upscaling_unsupported" });

  // No measurement exists on this architecture. See
  // LEGACY_GPU_ARCHITECTURES for why no correction is applied.
  if ((bc.LEGACY_GPU_ARCHITECTURES as readonly string[]).includes(gpuArch)) {
    notes.push({ code: "legacy_gpu", architecture: gpuArch });
  }

  // See FEW_CORES_THRESHOLD: a real effect, measured on one chip, and left
  // unmodelled rather than fitted from a single processor.
  if (cpuCores > 0 && cpuCores <= bc.FEW_CORES_THRESHOLD) {
    notes.push({ code: "few_cores", cores: cpuCores });
  }

  // A laptop CPU is soldered to its board and so is a laptop GPU, so these two
  // never sit in the same machine. Integrated graphics constrain nothing and
  // pair with either.
  if ((cpuForm === "desktop" && gpuForm === "laptop") ||
      (cpuForm === "laptop" && gpuForm === "desktop")) {
    notes.push({ code: "form_factor_mismatch", cpu_form: cpuForm, gpu_form: gpuForm });
  }

  const uncappedFps = Math.max(pyRound(fps), 0);
  const fpsCap = game.fps_cap || 0;
  if (fpsCap && uncappedFps > fpsCap) {
    notes.push({ code: "fps_cap", cap: Math.trunc(fpsCap), uncapped: uncappedFps });
  }

  // What the reader will see when the scene gets busy. Measured as a ratio of
  // 1% low to average across 336 rows, where it came out a property of the game
  // (0.53 in Counter-Strike 2, 0.88 in Hitman 3) and flat across CPU scores
  // from 50 to 100. Games with no measurement carry the global mean and say so
  // through fps_low_measured, so an assumed range is never shown with the
  // confidence of a measured one.
  const lowRatio = game.fps_low_ratio || bc.FPS_LOW_RATIO_DEFAULT;
  const shownFps = fpsCap && uncappedFps > fpsCap ? Math.trunc(fpsCap) : uncappedFps;
  const fpsLow = Math.max(pyRound(shownFps * lowRatio), 0);

  return {
    fps: uncappedFps,
    fps_low: fpsLow,
    fps_low_measured: Boolean(game.fps_low_measured),
    capped_fps: fpsCap && uncappedFps > fpsCap ? Math.trunc(fpsCap) : null,
    rendered_fps: Math.max(pyRound(renderedFps), 0),
    status,
    bottleneck: ftCpu > ftGpu ? "CPU" : "GPU",
    vram_needed_gb: pyRound(vramNeeded, 1),
    vram_alloc_gb: pyRound(vramAllocation(vramNeeded, vram), 1),
    vram_available_gb: vram,
    quality,
    notes,
    warnings: notes.map(renderNote),
  };
}

export function estimateFps(
  cpuData: Cpu | number,
  gpuData: Gpu | number,
  game: Game,
  resolution = "1080p",
  settings = "High",
  upscaling = "Native",
  frameGenMode = "Kapalı",
  ramGb = 16,
  rayTracing = false,
  pathTracing = false,
): number {
  return estimateFpsDetailed(
    cpuData, gpuData, game, resolution, settings, upscaling, frameGenMode,
    ramGb, rayTracing, pathTracing,
  ).fps;
}
