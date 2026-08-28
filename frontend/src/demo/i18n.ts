import type { Note } from "../engine/cadence";

/**
 * Interface text, in both languages.
 *
 * The engine reports what happened as a code and the numbers behind it (see
 * `Note` in cadence.ts); the sentence is written here. That split is why this
 * file can exist at all — the prose used to live inside the model, so the
 * language was a property of the engine and the conformance test compared
 * Turkish word for word.
 */
export type Lang = "tr" | "en";

const N = (n: number, d: number) => n.toFixed(d);

export const strings = {
  tr: {
    brand: "Performans",
    navGaming: "Oyun", navGamingHint: "FPS tahmini",
    navWorkstation: "İş istasyonu", navWorkstationHint: "Render, derleme",
    engineFoot: (m: number, e: string) => `Cadence 1.0\n${m} ölçüm · %${e} hata`,

    buildTitleA: "Donanımını seç,",
    buildTitleB: (n: number) => `${n} oyunun kaç kare vereceğini gör.`,
    buildLead:
      "Çözünürlük ve preset tüm listeyi belirler. Ray tracing, upscaling ve " +
      "frame generation oyun başına.",
    cpu: "İşlemci", gpu: "Ekran kartı", ram: "RAM",
    resolution: "Çözünürlük", preset: "Preset",
    pickCpu: "İşlemci seçin", pickGpu: "Ekran kartı seçin",
    searchCpu: "Ara — 5600, 14700, x3d…", searchGpu: "Ara — 4070, 9070 xt, arc…",
    noMatch: "Eşleşme yok",
    calculate: (n: number) => `${n} oyunu hesapla`,
    needParts: "İşlemci ve ekran kartı seçin",

    back: "← Sistemi değiştir",
    libraryStatus: "KÜTÜPHANE DURUMU",
    headline: (total: number, good: number) => ({
      a: `${total} oyunun `, b: `${good}`,
      c: "'i bu sistemde hedefinde çalışıyor.",
    }),
    onTarget: "hedefe ulaşıyor", nearTarget: "hedefe yakın",
    belowTarget: "hedefin altında", inTarget: "HEDEFTE",
    searchGame: "Oyun ara —  cs2, gta, cyberpunk…",
    sortStruggling: "Zorlananlar", sortFastest: "En hızlı", sortName: "A-Z",
    measuredFilter: (n: number) => `Ölçülmüş · ${n}`,
    problemFilter: (n: number) => `Sorunlular · ${n}`,
    showing: (total: number, shown: number) =>
      `${total} oyundan ${shown} tanesi gösteriliyor`,
    onlyProblemsNote: " · sadece sorunlular",
    noGames: "Eşleşen oyun yok.",

    measured: (n: number) => `ÖLÇÜLDÜ · ${n}`,
    measuredTitle: (n: number) => `${n} gerçek benchmark ölçümüne dayanıyor`,
    estimated: "TAHMİN",
    estimatedTitle: "Bu satır ölçüme dayanmıyor; sapma büyük olabilir",
    competitive: "REKABETÇİ",
    target: (n: number) => `hedef ${n}`,
    badgeUnplayable: "⚠ OYNANAMAZ",
    badgeSpill: (gb: number) => `⚠ VRAM TAŞIYOR · ${gb} GB`,
    badgeTight: (gb: number) => `⚠ VRAM SINIRDA · ${gb} GB`,

    verdictGood: "hedefte", verdictClose: "hedefin altında",
    verdictPoor: "60 fps altı", verdictBad: "oynanamaz",

    detailTargetLine: (genre: string, comp: boolean, t: number) =>
      `${genre}${comp ? " · rekabetçi" : ""} · hedef ${t} fps`,
    measuredBadge: (n: number) => `✓ ${n} gerçek ölçüme dayanıyor`,
    estimatedBadge: "Tahmin — bu oyun ölçülmedi",
    estimatedExplain:
      "Bu oyunun maliyet profili ölçülmedi, benzer oyunlardan türetildi. " +
      "Ölçülen oyunlarda motor %9 hatayla çalışıyor; türetilmiş profillerde " +
      "aynı test %49 sapma gösterdi.",
    bottleneckLine: (b: string, vram: number, q: string) =>
      `${b} sınırlı · ${vram} GB VRAM · ${q}`,
    upscaling: "Upscaling", frameGen: "Frame generation",
    rayTracing: "Ray tracing", pathTracing: "Path tracing",
    noUpscaling: "Bu oyunda upscaling yok",
    noFgGame: "Bu oyunda frame generation yok",
    noFgGpu: "Bu ekran kartı desteklemiyor",
    unsupported: "Bu oyun desteklemiyor",
    fgOff: "Kapalı",

    workstationTitle: "İş istasyonu modu",
    workstationBody:
      "Bu bölüm ayrı veri istiyor: tek çekirdek ve çok çekirdek skorları, " +
      "Blender gibi uygulamalarda ölçülmüş süreler. Oyun puanları buraya " +
      "taşınamaz — bilerek oyun endeksine çevrildiler.",
  },

  en: {
    brand: "Performance",
    navGaming: "Gaming", navGamingHint: "Frame rate estimates",
    navWorkstation: "Workstation", navWorkstationHint: "Render, compile",
    engineFoot: (m: number, e: string) => `Cadence 1.0\n${m} measurements · ${e}% error`,

    buildTitleA: "Pick your hardware,",
    buildTitleB: (n: number) => `see what ${n} games will run at.`,
    buildLead:
      "Resolution and preset apply to the whole list. Ray tracing, upscaling " +
      "and frame generation are per game.",
    cpu: "Processor", gpu: "Graphics card", ram: "RAM",
    resolution: "Resolution", preset: "Preset",
    pickCpu: "Choose a processor", pickGpu: "Choose a graphics card",
    searchCpu: "Search — 5600, 14700, x3d…", searchGpu: "Search — 4070, 9070 xt, arc…",
    noMatch: "No match",
    calculate: (n: number) => `Estimate ${n} games`,
    needParts: "Choose a processor and a graphics card",

    back: "← Change system",
    libraryStatus: "LIBRARY STATUS",
    headline: (total: number, good: number) => ({
      a: "", b: `${good}`, c: ` of ${total} games hit their target on this system.`,
    }),
    onTarget: "at target", nearTarget: "close to target",
    belowTarget: "below target", inTarget: "AT TARGET",
    searchGame: "Search games —  cs2, gta, cyberpunk…",
    sortStruggling: "Struggling", sortFastest: "Fastest", sortName: "A-Z",
    measuredFilter: (n: number) => `Measured · ${n}`,
    problemFilter: (n: number) => `Problems · ${n}`,
    showing: (total: number, shown: number) => `Showing ${shown} of ${total} games`,
    onlyProblemsNote: " · problems only",
    noGames: "No games match.",

    measured: (n: number) => `MEASURED · ${n}`,
    measuredTitle: (n: number) => `Backed by ${n} real benchmark measurements`,
    estimated: "ESTIMATE",
    estimatedTitle: "This row is not backed by measurement; it may be well off",
    competitive: "COMPETITIVE",
    target: (n: number) => `target ${n}`,
    badgeUnplayable: "⚠ UNPLAYABLE",
    badgeSpill: (gb: number) => `⚠ VRAM OVERFLOW · ${gb} GB`,
    badgeTight: (gb: number) => `⚠ VRAM TIGHT · ${gb} GB`,

    verdictGood: "at target", verdictClose: "below target",
    verdictPoor: "under 60 fps", verdictBad: "unplayable",

    detailTargetLine: (genre: string, comp: boolean, t: number) =>
      `${genre}${comp ? " · competitive" : ""} · target ${t} fps`,
    measuredBadge: (n: number) => `✓ Backed by ${n} real measurements`,
    estimatedBadge: "Estimate — this game has not been measured",
    estimatedExplain:
      "This game's cost profile was derived from similar titles rather than " +
      "measured. On measured games the engine runs at 9% mean error; on " +
      "derived profiles the same test showed 49%.",
    bottleneckLine: (b: string, vram: number, q: string) =>
      `${b}-limited · ${vram} GB VRAM · ${q}`,
    upscaling: "Upscaling", frameGen: "Frame generation",
    rayTracing: "Ray tracing", pathTracing: "Path tracing",
    noUpscaling: "This game has no upscaling",
    noFgGame: "This game has no frame generation",
    noFgGpu: "This card does not support it",
    unsupported: "Not supported by this game",
    fgOff: "Off",

    workstationTitle: "Workstation mode",
    workstationBody:
      "This section needs its own data: single- and multi-core scores, and " +
      "measured times in applications like Blender. The gaming scores cannot " +
      "be reused here — they were deliberately turned into a gaming index.",
  },
};
// No `as const`: it would make every value a literal type, and "Performance"
// is then not assignable to "Performans", so the two languages stop being the
// same shape. Widened strings are what a translation table wants anyway.

export type Strings = (typeof strings)["tr"];

/** The engine's structured note, written out as a sentence. */
export function renderNote(note: Note, lang: Lang): string {
  if (lang === "en") {
    switch (note.code) {
      case "ram_short":
        return `Not enough system RAM: the game wants about ${N(note.game_ram_gb, 0)} GB, ` +
          `and with ${note.ram_gb} GB the system starts paging.`;
      case "vram_tight":
        return `VRAM is tight: a frame needs about ${N(note.needed_gb, 1)} GB, but the ` +
          `game wants to reserve about ${N(note.wanted_gb, 1)} GB of cache on a ` +
          `${note.capacity_gb} GB card. Average frame rate holds up, but expect ` +
          `hitching when the camera moves somewhere new.`;
      case "vram_spill":
        return `Not enough VRAM: about ${N(note.needed_gb, 1)} GB needed on a ` +
          `${note.capacity_gb} GB card (about ${N(note.overflow_gb, 1)} GB over).`;
      case "unplayable":
        return `There is no system RAM to absorb the ${N(note.overflow_gb, 1)} GB overflow ` +
          `either (${note.ram_gb} GB). The game may crash or become unplayable — ` +
          `${note.suggested_ram_gb} GB of RAM would rescue this case.`;
      case "ram_cramped":
        return `System RAM only just covers the overflow; more of it ` +
          `(${note.suggested_ram_gb} GB) would make a visible difference here.`;
      case "upscaling_unsupported":
        return "This game does not support the selected upscaling technology; " +
          "it was calculated at native resolution.";
      case "fps_cap":
        return `This game is capped at ${note.cap} fps by default. Your hardware ` +
          `is good for ${note.uncapped} fps, but without lifting the cap you will ` +
          `see ${note.cap}.`;
    }
  }
  switch (note.code) {
    case "ram_short":
      return `Sistem RAM'i yetersiz: oyun ~${N(note.game_ram_gb, 0)} GB istiyor, ` +
        `${note.ram_gb} GB RAM ile takas (paging) başlıyor.`;
    case "vram_tight":
      return `VRAM sınırda: kare için ~${N(note.needed_gb, 1)} GB yetiyor ama oyun ` +
        `~${N(note.wanted_gb, 1)} GB önbellek ayırmak istiyor ` +
        `(${note.capacity_gb} GB kart). Ortalama FPS iyi kalır, ancak yeni ` +
        `sahnelere geçerken takılma olabilir.`;
    case "vram_spill":
      return `VRAM yetersiz: ~${N(note.needed_gb, 1)} GB ihtiyaç, ` +
        `${note.capacity_gb} GB kart (~${N(note.overflow_gb, 1)} GB taşıyor).`;
    case "unplayable":
      return `Taşan ${N(note.overflow_gb, 1)} GB'ı karşılayacak sistem RAM'i de yok ` +
        `(${note.ram_gb} GB). Oyun çökebilir veya oynanamaz hale gelir — ` +
        `${note.suggested_ram_gb} GB RAM bu senaryoyu kurtarır.`;
    case "ram_cramped":
      return `Sistem RAM'i taşmayı ancak zar zor karşılıyor; daha fazla RAM ` +
        `(${note.suggested_ram_gb} GB) bu senaryoda gözle görülür fark yaratır.`;
    case "upscaling_unsupported":
      return "Bu oyun seçilen upscaling teknolojisini desteklemiyor; " +
        "native çözünürlükte hesaplandı.";
    case "fps_cap":
      return `Bu oyun varsayılan halinde ${note.cap} FPS ile sınırlı. Donanımın ` +
        `${note.uncapped} FPS'e yetiyor, ancak sınır kaldırılmadan ` +
        `${note.cap} FPS görürsün.`;
  }
}

// ─── Context ─────────────────────────────────────────────────────────────────
// Threading `t` through every component as a prop would have meant touching
// each signature twice; a context keeps the change to the components that
// actually print text.

import { createContext, useContext } from "react";

export const LangContext = createContext<{ lang: Lang; t: Strings }>({
  lang: "tr",
  t: strings.tr,
});

export const useT = () => useContext(LangContext);
