import { useMemo, useState } from "react";
import { cpus, gpus, games, predictAll } from "../engine/catalog";
import { estimateFpsDetailed, getFgOptions } from "../engine/cadence";
import { LEGACY_GPU_ARCHITECTURES } from "../engine/balance.generated";
import type { CPUData, GPUData } from "../types";
import { targetFps, verdict, searchGames, VERDICT_COLOR, VERDICT_KEY, type Verdict } from "./lib";
import Picker from "./Picker";
import useIsMobile from "./useIsMobile";
import { LangContext, strings, useT, renderNote, type Lang } from "./i18n";
import { readUrl, useUrlState } from "./urlState";

const RESOLUTIONS = ["1080p", "1440p", "4k"];
const PRESETS = ["Low", "Medium", "High", "Ultra"];
const RAM = [8, 16, 32, 64];

type Phase = "build" | "results";

/**
 * Sorting by raw frame rate is the obvious default and it is useless: the top
 * of the list is always Stardew Valley at 961 fps. "struggling" sorts by frame
 * rate relative to each game's own target, worst first, which puts the answer
 * to the question actually being asked on the first screen.
 */
type Sort = "struggling" | "fastest" | "name";

type Game = (typeof games)[number];

export default function Demo() {
  const mobile = useIsMobile();
  // Read once, at mount. A shared link should open on the result it points
  // at, and an unknown part name simply falls back rather than erroring.
  const [initial] = useState(readUrl);

  const [lang, setLang] = useState<Lang>(initial.lang ?? "tr");
  const t = strings[lang];
  const [section, setSection] = useState<"gaming" | "workstation">("gaming");

  const [cpu, setCpu] = useState<CPUData | null>(
    () => cpus.find((c) => c.name === initial.cpu) ?? null);
  const [gpu, setGpu] = useState<GPUData | null>(
    () => gpus.find((g) => g.name === initial.gpu) ?? null);
  const [ram, setRam] = useState(initial.ram ?? 16);
  // Desktop by default: every one of the 492 measurements is on desktop
  // hardware, so it is both the common case and the only validated one.
  const [form, setForm] = useState(
    () => gpus.find((g) => g.name === initial.gpu)?.form_factor === "laptop"
      ? "laptop" : "desktop");
  const [resolution, setResolution] = useState(initial.res ?? "1440p");
  const [preset, setPreset] = useState(initial.preset ?? "High");
  const [phase, setPhase] = useState<Phase>(cpu && gpu ? "results" : "build");

  const [query, setQuery] = useState("");
  const [onlyProblems, setOnlyProblems] = useState(false);
  // Measured games predict at 9.1% mean error; the derived costs the rest
  // carry were 49.2% out against the same benchmarks. Showing both by
  // default would present a coin flip with the same confidence as a
  // measurement, so the trustworthy set is what you see first.
  const [onlyMeasured, setOnlyMeasured] = useState(true);
  const [sort, setSort] = useState<Sort>("struggling");
  const [openId, setOpenId] = useState<number | null>(initial.game ?? null);

  useUrlState({
    cpu: cpu?.name, gpu: gpu?.name, ram, res: resolution, preset, lang,
    game: openId ?? undefined,
  });

  const scored = useMemo(() => {
    if (!cpu || !gpu) return [];
    const byId = new Map(games.map((g) => [g.id, g]));
    return predictAll({ cpu, gpu, ramGb: ram, resolution, preset }).map((r) => {
      const game = byId.get(r.id)!;
      const target = targetFps(game);
      return { ...r, game, target, v: verdict(r.fps, target, r.status ?? "ok") as Verdict };
    });
  }, [cpu, gpu, ram, resolution, preset]);

  const problemCount = scored.filter((r) => r.v === "poor" || r.v === "bad").length;
  const measuredCount = scored.filter((r) => (r.game.measurements ?? 0) > 0).length;

  const rows = useMemo(() => {
    const hits = query.trim() ? new Map(searchGames(query).map((h) => [h.id, h.score])) : null;
    let list = [...scored];
    if (onlyMeasured) list = list.filter((r) => (r.game.measurements ?? 0) > 0);
    if (onlyProblems) list = list.filter((r) => r.v === "poor" || r.v === "bad");
    if (hits) {
      list = list.filter((r) => hits.has(r.id))
        .sort((a, b) => (hits.get(b.id)! - hits.get(a.id)!) || b.fps - a.fps);
    } else if (sort === "struggling") {
      list.sort((a, b) => a.fps / a.target - b.fps / b.target);
    } else if (sort === "fastest") {
      list.sort((a, b) => b.fps - a.fps);
    } else {
      list.sort((a, b) => a.name.localeCompare(b.name, lang));
    }
    return list;
  }, [scored, query, onlyProblems, onlyMeasured, sort, lang]);

  const summary = useMemo(() => ({
    good: scored.filter((r) => r.v === "good").length,
    close: scored.filter((r) => r.v === "close").length,
    poor: scored.filter((r) => r.v === "poor").length,
    bad: scored.filter((r) => r.v === "bad").length,
  }), [scored]);

  const ready = !!cpu && !!gpu;
  const open = openId === null ? null : games.find((g) => g.id === openId) ?? null;

  return (
    <LangContext.Provider value={{ lang, t }}>
    <div style={{
      display: "flex", flexDirection: mobile ? "column" : "row",
      height: "100%", background: "var(--bg)",
    }}>
      <Sidebar mobile={mobile} section={section} onSection={setSection}
        lang={lang} onLang={setLang}
        onHome={() => setPhase("build")} />

      <main style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        {section === "workstation" ? (
          <Placeholder />
        ) : (
          <Stage phase={phase} mobile={mobile}>
            {phase === "build" ? (
              <Builder
                cpu={cpu} gpu={gpu} ram={ram} resolution={resolution} preset={preset}
                form={form} onForm={(v) => { setForm(v); setCpu(null); setGpu(null); }}
                onCpu={setCpu} onGpu={setGpu} onRam={setRam}
                onResolution={setResolution} onPreset={setPreset}
                ready={ready} total={games.length} mobile={mobile}
                onSubmit={() => setPhase("results")}
              />
            ) : (
              <Results
                cpu={cpu!} gpu={gpu!} ram={ram} resolution={resolution} preset={preset}
                rows={rows} summary={summary} total={scored.length}
                problemCount={problemCount}
                query={query} onQuery={setQuery}
                onlyProblems={onlyProblems} onToggleProblems={setOnlyProblems}
                onlyMeasured={onlyMeasured} onToggleMeasured={setOnlyMeasured}
                measuredCount={measuredCount}
                sort={sort} onSort={setSort} mobile={mobile}
                onBack={() => setPhase("build")}
                onOpen={setOpenId}
              />
            )}
          </Stage>
        )}
      </main>

      {open && cpu && gpu && (
        <Detail
          game={open} cpu={cpu} gpu={gpu} ram={ram}
          resolution={resolution} preset={preset} mobile={mobile}
          onClose={() => setOpenId(null)}
        />
      )}
    </div>
    </LangContext.Provider>
  );
}

// ─── Shell ───────────────────────────────────────────────────────────────────

function LangToggle({ lang, onLang }: { lang: Lang; onLang: (l: Lang) => void }) {
  return (
    <div style={{ display: "flex", gap: 2, background: "var(--bg)", borderRadius: 8, padding: 2 }}>
      {(["tr", "en"] as const).map((l) => (
        <button key={l} onClick={() => onLang(l)} style={{
          padding: "5px 9px", borderRadius: 6, border: "none", fontSize: 12,
          fontFamily: "var(--mono)", fontWeight: lang === l ? 600 : 400,
          background: lang === l ? "var(--raised)" : "transparent",
          color: lang === l ? "var(--amber)" : "var(--text-3)",
        }}>{l.toUpperCase()}</button>
      ))}
    </div>
  );
}

function Sidebar({ mobile, section, onSection, lang, onLang, onHome }: {
  mobile: boolean;
  section: "gaming" | "workstation";
  onSection: (s: "gaming" | "workstation") => void;
  lang: Lang; onLang: (l: Lang) => void;
  onHome: () => void;
}) {
  const { t } = useT();
  if (mobile) {
    return (
      <header style={{
        flexShrink: 0, borderBottom: "1px solid var(--border)",
        background: "var(--surface)", display: "flex", alignItems: "center",
        gap: 10, padding: "12px 16px",
      }}>
        <button onClick={onHome} style={{ background: "none", border: "none", textAlign: "left", padding: 0 }}>
          <span style={{
            fontFamily: "var(--mono)", fontSize: 11, letterSpacing: "0.3em",
            color: "var(--amber)",
          }}>PERFHUB</span>
        </button>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6, alignItems: "center" }}>
          <LangToggle lang={lang} onLang={onLang} />
          {(["gaming", "workstation"] as const).map((k) => (
            <button
              key={k}
              onClick={() => onSection(k)}
              style={{
                padding: "7px 12px", borderRadius: 8, fontSize: 13,
                border: `1px solid ${section === k ? "var(--amber)" : "var(--border)"}`,
                background: section === k ? "var(--amber-glow)" : "transparent",
                color: section === k ? "var(--amber)" : "var(--text-3)",
              }}
            >{k === "gaming" ? t.navGaming : t.navWorkstation}</button>
          ))}
        </div>
      </header>
    );
  }
  return (
    <aside style={{
      width: 264, flexShrink: 0, borderRight: "1px solid var(--border)",
      background: "var(--surface)", display: "flex", flexDirection: "column",
      padding: "32px 0",
    }}>
      <button
        onClick={onHome}
        style={{ background: "none", border: "none", padding: "0 26px 32px", textAlign: "left" }}
      >
        <div style={{
          fontFamily: "var(--mono)", fontSize: 12, letterSpacing: "0.34em",
          color: "var(--amber)",
        }}>PERFHUB</div>
        <div style={{ fontSize: 27, fontWeight: 600, letterSpacing: "-0.02em", marginTop: 4 }}>
          {t.brand}
        </div>
      </button>

      <div style={{ padding: "0 24px 22px" }}>
        <LangToggle lang={lang} onLang={onLang} />
      </div>

      <nav style={{ padding: "0 14px", display: "grid", gap: 4 }}>
        <NavItem active={section === "gaming"} onClick={() => onSection("gaming")}
          label={t.navGaming} hint={t.navGamingHint} />
        <NavItem active={section === "workstation"} onClick={() => onSection("workstation")}
          label={t.navWorkstation} hint={t.navWorkstationHint} muted />
      </nav>

      <div style={{ marginTop: "auto", padding: "0 26px" }}>
        <div style={{
          fontFamily: "var(--mono)", fontSize: 12, color: "var(--text-3)", lineHeight: 1.8,
        }}>
          {t.engineFoot(106, "9.0").split("\n").map((line, i) => (
            <span key={i}>{line}<br /></span>
          ))}
        </div>
      </div>
    </aside>
  );
}

function NavItem({ active, onClick, label, hint, muted }: {
  active: boolean; onClick: () => void; label: string; hint: string; muted?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "block", width: "100%", textAlign: "left",
        padding: "13px 14px", borderRadius: 10, border: "none",
        background: active ? "var(--raised)" : "transparent", position: "relative",
      }}
    >
      {active && (
        <span style={{
          position: "absolute", left: 0, top: 13, bottom: 13, width: 3,
          background: "var(--amber)", borderRadius: 3,
        }} />
      )}
      <div style={{
        fontSize: 16, fontWeight: 500,
        color: active ? "var(--text)" : muted ? "var(--text-3)" : "var(--text-2)",
      }}>{label}</div>
      <div style={{ fontSize: 13, color: "var(--text-3)", marginTop: 2 }}>{hint}</div>
    </button>
  );
}

/**
 * The monitor, and the transition through it. The bezel is the entry state;
 * submitting pushes the camera through the screen into a full-width list,
 * which is both the "entering an object" effect and the fix for the frame's
 * real problem — a fixed bezel around a 176-row list leaves no room to read it.
 */
function Stage({ phase, mobile, children }: {
  phase: Phase; mobile: boolean; children: React.ReactNode;
}) {
  // The bezel is the right frame for this on a desktop and completely wrong on
  // a phone, where it would spend most of a 375px screen on a picture of a
  // monitor. Below the breakpoint the content just fills the viewport.
  if (mobile) {
    return <div style={{ position: "absolute", inset: 0, overflow: "hidden" }}>{children}</div>;
  }
  const building = phase === "build";
  return (
    <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
      <Blueprint dim={!building} />
      <div style={{
        position: "relative",
        width: building ? "min(1340px, 95%)" : "100%",
        // The stand hangs below the bezel, so its height has to come out of
        // the budget too — otherwise the monitor fits and the stand pushes
        // the whole page into a scrollbar, which is what happened at 720p.
        height: building ? "min(820px, calc(100% - 76px))" : "100%",
        transition: "width 620ms var(--ease), height 620ms var(--ease)",
      }}>
        <div style={{
          position: "absolute", inset: 0,
          borderRadius: building ? 22 : 0,
          border: building ? "1px solid var(--border-strong)" : "1px solid transparent",
          background: building ? "var(--raised)" : "var(--bg)",
          padding: building ? 18 : 0,
          transition: "border-radius 620ms var(--ease), padding 620ms var(--ease), background 620ms var(--ease)",
          boxShadow: building ? "0 50px 100px -20px rgba(0,0,0,0.85)" : "none",
        }}>
          <div style={{
            width: "100%", height: "100%", overflow: "hidden",
            borderRadius: building ? 10 : 0, background: "var(--bg)",
            transition: "border-radius 620ms var(--ease)",
          }}>
            {children}
          </div>
        </div>

        <div style={{
          position: "absolute", top: "100%", left: "50%", transform: "translateX(-50%)",
          width: 150, height: building ? 40 : 0,
          background: "linear-gradient(var(--raised), var(--surface))",
          borderRadius: "0 0 12px 12px",
          opacity: building ? 1 : 0,
          transition: "height 420ms var(--ease), opacity 300ms var(--ease)",
        }} />
      </div>
    </div>
  );
}

function Blueprint({ dim }: { dim: boolean }) {
  return (
    <svg aria-hidden style={{
      position: "absolute", inset: 0, width: "100%", height: "100%",
      opacity: dim ? 0.2 : 1, transition: "opacity 620ms var(--ease)",
      pointerEvents: "none",
    }}>
      <defs>
        <pattern id="bp" width="48" height="48" patternUnits="userSpaceOnUse">
          <path d="M48 0 L0 0 0 48" fill="none" stroke="var(--line)" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#bp)" />
      <g stroke="var(--line)" fill="none" strokeWidth="2">
        <circle cx="11%" cy="32%" r="150" />
        <circle cx="11%" cy="32%" r="104" />
        <circle cx="11%" cy="32%" r="58" />
        <rect x="74%" y="13%" width="250" height="104" rx="5" />
        <rect x="78%" y="18%" width="160" height="40" rx="3" />
        <rect x="5%" y="76%" width="215" height="82" />
        <rect x="82%" y="72%" width="170" height="124" />
      </g>
      {/* Red corner marks from the reference, now with a job: the same red the
          app uses for a real problem, so the language stays consistent. */}
      <g fill="var(--red)" opacity="0.55">
        <rect x="4%" y="10%" width="9" height="9" />
        <rect x="94%" y="10%" width="9" height="9" />
        <rect x="4%" y="88%" width="9" height="9" />
        <rect x="94%" y="88%" width="9" height="9" />
      </g>
    </svg>
  );
}

function Placeholder() {
  const { t } = useT();
  return (
    <div style={{ display: "grid", placeItems: "center", height: "100%", textAlign: "center" }}>
      <div>
        <div style={{ fontSize: 24, fontWeight: 600 }}>{t.workstationTitle}</div>
        <p style={{ color: "var(--text-2)", maxWidth: 440, margin: "12px auto 0", lineHeight: 1.7, fontSize: 16 }}>
          {t.workstationBody}
        </p>
      </div>
    </div>
  );
}

// ─── Build ───────────────────────────────────────────────────────────────────

function Builder(p: {
  cpu: CPUData | null; gpu: GPUData | null; ram: number;
  form: string; onForm: (v: string) => void;
  resolution: string; preset: string; ready: boolean; total: number;
  onCpu: (c: CPUData | null) => void; onGpu: (g: GPUData | null) => void;
  onRam: (n: number) => void; onResolution: (s: string) => void;
  onPreset: (s: string) => void; onSubmit: () => void; mobile: boolean;
}) {
  const { t } = useT();
  return (
    <div style={{ padding: p.mobile ? "22px 18px" : "26px 48px", height: "100%", overflowY: "auto" }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <div style={{
          fontSize: 12.5, letterSpacing: "0.24em", color: "var(--amber)",
          fontFamily: "var(--mono)", marginBottom: 10,
        }}>CADENCE 1.0</div>
        {/* Big. This screen has no data on it to protect, so the restraint that
            keeps the results list readable buys nothing here — it only made the
            product look like a form. */}
        {/* Two lines, not three: at 1280x720 the taller version pushed the
            button past the bottom of the monitor and the whole screen had to
            be scrolled, which is not what a five-field form should ask for. */}
        <h1 style={{
          fontSize: p.mobile ? 26 : 34, fontWeight: 600, letterSpacing: "-0.03em",
          margin: 0, lineHeight: 1.1,
        }}>
          {t.buildTitleA}{" "}
          <span style={{ color: "var(--text-2)" }}>{t.buildTitleB(p.total)}</span>
        </h1>
        <p style={{ color: "var(--text-2)", margin: "12px 0 22px", fontSize: 15, lineHeight: 1.55, maxWidth: 580 }}>
          {t.buildLead}
        </p>

        <div style={{ display: "grid", gap: 13 }}>
          {/* Nothing used to stop a desktop Ryzen 9 being paired with an RTX
              4070 Laptop, and the engine would answer for a machine that
              cannot exist — both kinds of part are soldered to their boards.
              Asking once, up front, prevents the mistake instead of explaining
              it afterwards, and it says why the list is the length it is.
              Apple chips appear in both, since the M-series ships in laptops
              and desktops alike. */}
          <Field label={t.machineType}>
            <Segmented
              value={p.form} onChange={p.onForm}
              options={[
                { value: "desktop", label: t.desktop },
                { value: "laptop", label: t.laptop },
              ]}
            />
          </Field>
          <Field label={t.cpu}>
            <Picker
              items={cpus
                .filter((c) => c.form_factor === p.form || c.form_factor === "apple")
                .map((c) => ({ value: c.name, label: c.name, meta: String(c.power_score) }))}
              value={p.cpu?.name ?? ""}
              onChange={(v) => p.onCpu(cpus.find((c) => c.name === v) ?? null)}
              placeholder={t.searchCpu}
              emptyLabel={t.pickCpu}
            />
          </Field>
          <Field label={t.gpu}>
            <Picker
              items={gpus
                .filter((g) => g.form_factor === p.form || g.form_factor === "integrated")
                .map((g) => ({
                  value: g.name, label: g.name,
                  meta: `${g.power_score}${g.vram ? ` · ${g.vram}GB` : ""}`,
                }))}
              value={p.gpu?.name ?? ""}
              onChange={(v) => p.onGpu(gpus.find((g) => g.name === v) ?? null)}
              placeholder={t.searchGpu}
              emptyLabel={t.pickGpu}
            />
          </Field>

          <div style={{
            display: "grid",
            gridTemplateColumns: p.mobile ? "1fr" : "1fr 1fr 1.2fr", gap: 14,
          }}>
            <Field label={t.ram}>
              <Segmented value={String(p.ram)} onChange={(v) => p.onRam(Number(v))}
                options={RAM.map((r) => ({ value: String(r), label: `${r}` }))} />
            </Field>
            <Field label={t.resolution}>
              <Segmented value={p.resolution} onChange={p.onResolution}
                options={RESOLUTIONS.map((r) => ({ value: r, label: r }))} />
            </Field>
            <Field label={t.preset}>
              <Segmented value={p.preset} onChange={p.onPreset}
                options={PRESETS.map((r) => ({ value: r, label: r }))} />
            </Field>
          </div>
        </div>

        <button
          onClick={p.onSubmit}
          disabled={!p.ready}
          style={{
            marginTop: 22, width: "100%", padding: "15px 0", borderRadius: 12,
            border: "1px solid " + (p.ready ? "var(--amber)" : "var(--border)"),
            background: p.ready ? "var(--amber)" : "transparent",
            color: p.ready ? "#170F02" : "var(--text-3)",
            fontWeight: 600, fontSize: 17,
            cursor: p.ready ? "pointer" : "not-allowed",
          }}
        >
          {p.ready ? t.calculate(p.total) : t.needParts}
        </button>
      </div>
    </div>
  );
}

// ─── Results ─────────────────────────────────────────────────────────────────

type Row = {
  id: number; name: string; genre: string; fps: number; fps_low: number;
  fps_low_measured: boolean; target: number;
  v: Verdict; game: Game; status?: string; vram_needed_gb?: number; warnings?: string[];
};

const WIDTH = 1180;

function Results(p: {
  cpu: CPUData; gpu: GPUData; ram: number; resolution: string; preset: string;
  rows: Row[]; total: number; problemCount: number;
  summary: { good: number; close: number; poor: number; bad: number };
  query: string; onQuery: (s: string) => void;
  onlyProblems: boolean; onToggleProblems: (b: boolean) => void;
  onlyMeasured: boolean; onToggleMeasured: (b: boolean) => void;
  measuredCount: number;
  sort: Sort; onSort: (s: Sort) => void; mobile: boolean;
  onBack: () => void; onOpen: (id: number) => void;
}) {
  // The hero is 322px, which is a third of the viewport. That is the right
  // size to arrive on and the wrong size to read a list through, so it packs
  // itself away once you start scrolling and comes back when you return.
  const [compact, setCompact] = useState(false);
  const { t } = useT();

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      {/* Generous on purpose. "Spacious" does not come from even padding
          everywhere — it comes from a lot of room in one place and very little
          in the rest, which is the thing the first pass got wrong. */}
      <header style={{
        padding: compact
          ? (p.mobile ? "12px 16px" : "16px 36px")
          : (p.mobile ? "18px 16px 20px" : "30px 36px 28px"),
        borderBottom: "1px solid var(--border)",
        background: "var(--lift)", flexShrink: 0, overflow: "hidden",
        transition: "padding 380ms var(--ease)",
      }}>
        <div style={{ maxWidth: WIDTH, margin: "0 auto" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 18,
            marginBottom: compact ? 0 : 20,
            transition: "margin-bottom 380ms var(--ease)",
          }}>
            <button onClick={p.onBack} style={{
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 10, padding: "10px 15px", fontSize: 14, color: "var(--text-2)",
            }}>{t.back}</button>
            <div style={{ fontFamily: "var(--mono)", fontSize: 13.5, color: "var(--text-2)" }}>
              {p.cpu.name} · {p.gpu.name} · {p.ram} GB ·{" "}
              <span style={{ color: "var(--amber)" }}>{p.resolution} {p.preset}</span>
            </div>
            {/* Collapsed, the counts move up here so the summary never leaves. */}
            <div style={{
              marginLeft: "auto", display: "flex", gap: 16, fontFamily: "var(--mono)",
              fontSize: 17, fontWeight: 600,
              opacity: compact ? 1 : 0,
              transition: "opacity 240ms var(--ease)",
              pointerEvents: compact ? "auto" : "none",
            }}>
              <span style={{ color: "var(--green)" }}>{p.summary.good}</span>
              <span style={{ color: "var(--orange)" }}>{p.summary.close}</span>
              <span style={{ color: "var(--red)" }}>{p.summary.poor + p.summary.bad}</span>
            </div>
          </div>

          {/* Grid, not a wrapping flex row: at 1280 wide the two blocks were
              837px against 855px of space and the arc dropped below the
              headline, making the hero *taller* on the screens that could
              least afford it. Here the headline gives way instead. */}
          <div style={{
            display: "grid",
            gridTemplateColumns: p.mobile ? "1fr" : "minmax(0, 1fr) auto",
            alignItems: "center", gap: p.mobile ? 18 : 32,
            maxHeight: compact ? 0 : 300,
            opacity: compact ? 0 : 1,
            transition: "max-height 380ms var(--ease), opacity 240ms var(--ease)",
          }}>
            <div>
              <div style={{
                fontSize: 13, letterSpacing: "0.24em", color: "var(--text-3)",
                fontFamily: "var(--mono)",
              }}>{t.libraryStatus}</div>
              <h1 style={{
                fontSize: p.mobile ? 25 : 36, fontWeight: 600, letterSpacing: "-0.03em",
                margin: "8px 0 0", lineHeight: 1.08,
              }}>
                {t.headline(p.total, p.summary.good).a}
                <span style={{ color: "var(--green)" }}>
                  {t.headline(p.total, p.summary.good).b}
                </span>
                <span style={{ color: "var(--text-2)" }}>
                  {t.headline(p.total, p.summary.good).c}
                </span>
              </h1>
            </div>
            <SummaryArc summary={p.summary} total={p.total} mobile={p.mobile} />
          </div>
        </div>
      </header>

      {/* A caveat belongs where the confidence is loudest. The headline reads
          "78% of your library on target" whether or not a single measurement
          exists for the card it was computed on, and 79 of the 164 GPUs have
          none. Filed behind a click, the confident half stays on screen and the
          qualification does not. */}
      {(LEGACY_GPU_ARCHITECTURES as readonly string[]).includes(p.gpu.architecture ?? "") && (
        <div style={{
          padding: p.mobile ? "12px 16px" : "14px 36px",
          background: "color-mix(in oklab, var(--orange) 12%, var(--bg))",
          borderBottom: "1px solid color-mix(in oklab, var(--orange) 34%, var(--border))",
        }}>
          <div style={{
            maxWidth: WIDTH, margin: "0 auto", display: "flex", gap: 12,
            alignItems: "flex-start", fontSize: p.mobile ? 13 : 14, lineHeight: 1.5,
          }}>
            <span style={{ color: "var(--orange)", flexShrink: 0 }}>▲</span>
            <span style={{ color: "var(--text-2)" }}>{t.legacyGpuBanner(p.gpu.architecture ?? "")}</span>
          </div>
        </div>
      )}

      <div style={{ padding: p.mobile ? "12px 16px" : "16px 36px", borderBottom: "1px solid var(--border)" }}>
        <div style={{
          maxWidth: WIDTH, margin: "0 auto", display: "flex",
          gap: p.mobile ? 8 : 14, alignItems: "center",
          flexWrap: p.mobile ? "wrap" : "nowrap",
        }}>
          <input
            value={p.query}
            onChange={(e) => p.onQuery(e.target.value)}
            placeholder={t.searchGame}
            style={{
              flex: 1, background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 10, padding: "13px 16px", fontSize: 15.5, outline: "none",
            }}
          />
          <Segmented
            value={p.sort} onChange={(v) => p.onSort(v as Sort)}
            options={[
              { value: "struggling", label: t.sortStruggling },
              { value: "fastest", label: t.sortFastest },
              { value: "name", label: t.sortName },
            ]}
          />
          {/* The count lives in the label because with "struggling" sorting the
              top of the list is already the problems — toggling the filter used
              to change nothing visible and read as a broken button. */}
          <button
            onClick={() => p.onToggleMeasured(!p.onlyMeasured)}
            title={p.onlyMeasured ? t.estimatedTitle : t.measuredTitle(0)}
            style={{
              border: `1px solid ${p.onlyMeasured ? "var(--green)" : "var(--border)"}`,
              background: p.onlyMeasured ? "var(--green-dim)" : "var(--surface)",
              borderRadius: 10, padding: "12px 16px", fontSize: 14.5, whiteSpace: "nowrap",
              color: p.onlyMeasured ? "var(--green)" : "var(--text-2)",
              fontWeight: p.onlyMeasured ? 600 : 400,
            }}
          >
            {p.onlyMeasured ? "✓ " : ""}{t.measuredFilter(p.measuredCount)}
          </button>
          <button
            onClick={() => p.onToggleProblems(!p.onlyProblems)}
            style={{
              border: `1px solid ${p.onlyProblems ? "var(--red)" : "var(--border)"}`,
              background: p.onlyProblems ? "var(--red-dim)" : "var(--surface)",
              borderRadius: 10, padding: "12px 16px", fontSize: 14.5, whiteSpace: "nowrap",
              color: p.onlyProblems ? "var(--red)" : "var(--text-2)",
              fontWeight: p.onlyProblems ? 600 : 400,
            }}
          >
            {t.problemFilter(p.problemCount)}
          </button>
        </div>
      </div>

      <div
        style={{ flex: 1, overflowY: "auto" }}
        onScroll={(e) => {
          const y = (e.target as HTMLDivElement).scrollTop;
          setCompact((c) => (c ? y > 30 : y > 90));  // hysteresis, so it does
        }}                                            // not flicker at the edge
      >
        <div style={{ maxWidth: WIDTH, margin: "0 auto", padding: p.mobile ? "0 12px" : "0 36px" }}>
          {(p.query || p.onlyProblems) && (
            <div style={{
              padding: "12px 0", fontSize: 13.5, color: "var(--text-2)",
              fontFamily: "var(--mono)",
            }}>
              {t.showing(p.total, p.rows.length)}
              {p.onlyProblems && t.onlyProblemsNote}
            </div>
          )}
          {p.rows.length === 0 ? (
            <div style={{ padding: 70, textAlign: "center", color: "var(--text-3)", fontSize: 16 }}>
              {t.noGames}
            </div>
          ) : (
            p.rows.map((r, i) => (
              <GameRow key={r.id} row={r} index={i} mobile={p.mobile}
                onOpen={() => p.onOpen(r.id)} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * The hero.
 *
 * The first version put this information in three small chips in a corner,
 * which was accurate and completely forgettable. It is the answer to the
 * question the user actually asked — can this machine play my games — so it
 * gets the size that deserves. The arc reuses the loader's instrument
 * language, which is what makes the two screens feel like one product.
 */
function SummaryArc({ summary, total, mobile }: {
  summary: { good: number; close: number; poor: number; bad: number };
  total: number; mobile: boolean;
}) {
  const { t } = useT();
  const pct = total ? Math.round((summary.good / total) * 100) : 0;
  const sweep = 220;
  const start = 180 + (360 - sweep) / 2;
  const R = 64;
  const polar = (deg: number, r: number) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return [110 + r * Math.cos(rad), 110 + r * Math.sin(rad)] as const;
  };
  const arc = (a: number, b: number, r: number) => {
    if (b - a < 0.01) return "";
    const [sx, sy] = polar(a, r);
    const [ex, ey] = polar(b, r);
    return `M ${sx} ${sy} A ${r} ${r} 0 ${b - a > 180 ? 1 : 0} 1 ${ex} ${ey}`;
  };

  // Each verdict takes the share of the arc it actually holds, so the ring is
  // the distribution rather than a decoration wrapped around a number.
  const segs = [
    { n: summary.good, c: "var(--green)" },
    { n: summary.close, c: "var(--orange)" },
    { n: summary.poor + summary.bad, c: "var(--red)" },
  ];
  let cursor = start;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
      <div style={{
        position: "relative", width: mobile ? 150 : 190, height: mobile ? 98 : 124,
        flexShrink: 0,
      }}>
        <svg width={mobile ? 150 : 190} height={mobile ? 98 : 124}
          viewBox="20 26 180 118" aria-hidden>
          <path d={arc(start, start + sweep, R)} fill="none"
            stroke="var(--raised)" strokeWidth="13" strokeLinecap="round" />
          {segs.map((s, i) => {
            const span = total ? (s.n / total) * sweep : 0;
            const a = cursor;
            cursor += span;
            return span > 0.5 ? (
              <path key={i} d={arc(a + 1, cursor - 1, R)} fill="none"
                stroke={s.c} strokeWidth="13" strokeLinecap="round" />
            ) : null;
          })}
          <text x="110" y="112" textAnchor="middle" style={{
            fill: "var(--text)", fontFamily: "var(--mono)",
            fontSize: 40, fontWeight: 600, letterSpacing: "-0.03em",
          }}>{pct}<tspan style={{ fontSize: 18, fill: "var(--text-3)" }}>%</tspan></text>
          <text x="110" y="134" textAnchor="middle" style={{
            fill: "var(--text-3)", fontSize: 11.5, letterSpacing: "0.22em",
          }}>{t.inTarget}</text>
        </svg>
      </div>

      <div style={{ display: "grid", gap: mobile ? 7 : 11, minWidth: 0 }}>
        <Legend n={summary.good} label={t.onTarget} color="var(--green)" />
        <Legend n={summary.close} label={t.nearTarget} color="var(--orange)" />
        <Legend n={summary.poor + summary.bad} label={t.belowTarget} color="var(--red)" />
      </div>
    </div>
  );
}

function Legend({ n, label, color }: { n: number; label: string; color: string }) {
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: 9, minWidth: 0 }}>
      <span style={{ width: 9, height: 9, borderRadius: 3, background: color, flexShrink: 0 }} />
      <span style={{
        fontFamily: "var(--mono)", fontSize: 24, fontWeight: 600, color,
        minWidth: 40, flexShrink: 0,
      }}>{n}</span>
      <span style={{
        fontSize: 14, color: "var(--text-2)", minWidth: 0,
        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
      }}>{label}</span>
    </div>
  );
}

/**
 * A tile per game, built from its initials.
 *
 * There is no cover art in the database and none to license, but a list of 176
 * lines of text with nothing to look at is most of why this read as a
 * spreadsheet. Deliberately monochrome: colour on this page already means a
 * verdict, and a wall of tinted squares would compete with the thing that
 * matters. Rhythm without noise.
 */
function Cover({ game, size = 108, eager }: { game: Game; size?: number; eager?: boolean }) {
  const [failed, setFailed] = useState(false);
  const h = size * 0.47;  // Steam header images are 460x215

  if (game.cover_url && !failed) {
    return (
      <div style={{
        width: size, height: h, borderRadius: 9, flexShrink: 0, overflow: "hidden",
        border: "1px solid var(--border)", background: "var(--raised)",
        boxShadow: "var(--shadow-sm)",
      }}>
        <img
          // The full URL is stored rather than built from the app id: newer
          // Steam entries live under a hashed path that cannot be constructed,
          // which is why Death Stranding 2 and F1 25 had valid ids and no
          // image. See scripts/link_steam_apps.py.
          src={game.cover_url}
          alt=""
          loading={eager ? "eager" : "lazy"}
          onError={() => setFailed(true)}
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
        />
      </div>
    );
  }
  return <Monogram name={game.name} width={size} height={h} />;
}

function Monogram({ name, width = 52, height = 52 }: {
  name: string; width?: number; height?: number;
}) {
  const initials = name
    .replace(/^(The|A) /, "")
    .split(/[\s:]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toLocaleUpperCase("tr");

  // Deterministic tilt of the gradient so neighbouring tiles differ.
  let h = 0;
  for (const ch of name) h = (h * 31 + ch.charCodeAt(0)) % 360;

  return (
    <div style={{
      width, height, borderRadius: 9, flexShrink: 0,
      background: `linear-gradient(${h}deg, var(--raised), var(--surface))`,
      border: "1px solid var(--border)",
      display: "grid", placeItems: "center",
      fontFamily: "var(--mono)", fontSize: 17, fontWeight: 600,
      color: "var(--text-3)", letterSpacing: "-0.02em",
      boxShadow: "var(--shadow-sm)",
    }}>{initials}</div>
  );
}

/**
 * One game.
 *
 * The frame rate is colour coded, which is only honest because it is judged
 * against this game's own target rather than a fixed number — 60 fps is green
 * in an RPG and red in Counter-Strike, and both are correct.
 */
function GameRow({ row, index, mobile, onOpen }: {
  row: Row; index: number; mobile: boolean; onOpen: () => void;
}) {
  const { t } = useT();
  const color = VERDICT_COLOR[row.v];
  const ratio = Math.min(1, row.fps / row.target);
  const warning = row.status && row.status !== "ok" && row.status !== "ram_short";

  return (
    <button
      onClick={onOpen}
      className="rise"
      style={{
        ["--i" as string]: Math.min(index, 18),
        display: "grid",
        gridTemplateColumns: mobile ? "1fr auto" : "1fr 190px 150px",
        alignItems: "center",
        gap: mobile ? 12 : 22, width: "100%", textAlign: "left",
        padding: mobile ? "12px 10px" : "13px 18px",
        background: "none", border: "1px solid transparent",
        borderBottom: "1px solid var(--border)", borderRadius: 12,
        transition: "background 160ms, transform 160ms var(--ease), border-color 160ms",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "var(--surface)";
        e.currentTarget.style.borderColor = "var(--border)";
        e.currentTarget.style.transform = "translateX(4px)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "none";
        e.currentTarget.style.borderColor = "transparent";
        e.currentTarget.style.borderBottomColor = "var(--border)";
        e.currentTarget.style.transform = "none";
      }}
    >
      <div style={{ minWidth: 0, display: "flex", alignItems: "center", gap: 18 }}>
        <Cover game={row.game} size={mobile ? 76 : 108} eager={index < 12} />
        <div style={{ minWidth: 0 }}>
        <div style={{
          fontSize: 18, fontWeight: 500,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>{row.name}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 9, marginTop: 5 }}>
          <span style={{ fontSize: 13, color: "var(--text-3)" }}>{row.genre}</span>
          {(row.game.measurements ?? 0) > 0 ? (
            <span title={t.measuredTitle(row.game.measurements ?? 0)}
              style={{
                fontSize: 11, fontFamily: "var(--mono)", color: "var(--green)",
                border: "1px solid var(--green)", borderRadius: 5, padding: "1px 6px",
                background: "var(--green-dim)", fontWeight: 600,
              }}>{t.measured(row.game.measurements ?? 0)}</span>
          ) : (
            <span title={t.estimatedTitle}
              style={{
                fontSize: 11, fontFamily: "var(--mono)", color: "var(--text-3)",
                border: "1px dashed var(--border)", borderRadius: 5, padding: "1px 6px",
              }}>{t.estimated}</span>
          )}
          {row.game.competitive ? (
            <span style={{
              fontSize: 11, fontFamily: "var(--mono)", color: "var(--amber)",
              border: "1px solid var(--amber-dim)", borderRadius: 5, padding: "1px 6px",
            }}>{t.competitive}</span>
          ) : null}
          {warning && (
            <span style={{
              fontSize: 12, fontWeight: 600, color: "var(--red)",
              background: "var(--red-dim)", border: "1px solid var(--red-deep)",
              borderRadius: 6, padding: "2px 8px",
            }}>
              {row.status === "unplayable" ? t.badgeUnplayable
                : row.status === "vram_spill" ? t.badgeSpill(row.vram_needed_gb ?? 0)
                : t.badgeTight(row.vram_needed_gb ?? 0)}
            </span>
          )}
        </div>
        </div>
      </div>

      <div style={{ gridColumn: mobile ? "1 / -1" : undefined, order: mobile ? 3 : undefined }}>
        <div style={{
          height: 8, background: "var(--raised)", borderRadius: 4, overflow: "hidden",
          boxShadow: "inset 0 1px 2px rgba(0,0,0,0.5)",
        }}>
          <div style={{
            width: `${ratio * 100}%`, height: "100%", background: color,
            boxShadow: `0 0 12px ${color}`,
          }} />
        </div>
        <div style={{
          fontSize: 12, color: "var(--text-3)", marginTop: 8, fontFamily: "var(--mono)",
          display: "flex", justifyContent: "space-between",
        }}>
          <span style={{ color }}>{t[VERDICT_KEY[row.v]]}</span>
          <span>{t.target(row.target)}</span>
        </div>
      </div>

      {/* The number is the answer. It gets to be the biggest thing on the row.
          The low sits under it in small type rather than beside it: a reader
          scanning the list wants one number per game, and a reader deciding on
          one game wants to know how far it drops when the scene fills up. */}
      <div style={{ textAlign: "right" }}>
        <div>
          <span style={{
            fontFamily: "var(--mono)", fontSize: mobile ? 30 : 38, fontWeight: 600, color,
            letterSpacing: "-0.035em", lineHeight: 1,
          }}>{row.fps}</span>
          <span style={{ fontSize: 13, color: "var(--text-3)", marginLeft: 6 }}>fps</span>
        </div>
        <div style={{
          fontFamily: "var(--mono)", fontSize: 12, color: "var(--text-3)", marginTop: 5,
        }}>{t.busyScenes(row.fps_low)}</div>
      </div>
    </button>
  );
}

// ─── Per-game detail ─────────────────────────────────────────────────────────

function Detail({ game, cpu, gpu, ram, resolution, preset, mobile, onClose }: {
  game: Game; cpu: CPUData; gpu: GPUData; ram: number;
  resolution: string; preset: string; mobile: boolean; onClose: () => void;
}) {
  const { t, lang } = useT();
  const [res, setRes] = useState(resolution);
  const [set, setSet] = useState(preset);
  // Technology and quality tier are separate choices, because flattening them
  // produced a row of up to nine buttons that had to be abbreviated to fit —
  // "DLSS Q", "FSR P", "XeSS B" — and three of the four DLSS tiers and half of
  // FSR's were simply left out to keep it short. Two rows fit every mode at
  // full width and read as words.
  const [upsTech, setUpsTech] = useState("Native");
  const [upsLevel, setUpsLevel] = useState("Quality");
  const [fg, setFg] = useState("Kapalı");
  const [rt, setRt] = useState(false);
  const [pt, setPt] = useState(false);

  // Only offer what this game actually has. The first version listed every
  // DLSS mode on every game, so Valorant — which has no upscaler at all —
  // appeared to support DLSS Performance. The engine handled it correctly and
  // computed at native, but the interface was lying about the game.
  const techs: string[] = ["Native"];
  if (game.supports_dlss) techs.push("DLAA", "DLSS");
  if (game.supports_fsr) techs.push("FSR");
  if (game.supports_xess) techs.push("XeSS");
  // DLSS, FSR and XeSS all ship the same four tiers. Native and DLAA render at
  // full resolution, so a tier means nothing for them.
  const LEVELS = ["Quality", "Balanced", "Performance", "Ultra Performance"];
  const scaled = upsTech !== "Native" && upsTech !== "DLAA";
  const ups = scaled ? `${upsTech} ${upsLevel}` : upsTech;

  // Frame generation needs both a card that can do it and a game that ships
  // it. DLSS 3 and FSR 3 frame generation come with their respective
  // upscalers, so the game side is keyed off those.
  const gameHasFg = !!(game.supports_dlss || game.supports_fsr);
  const fgOptions = gameHasFg ? getFgOptions(gpu.name) : ["Kapalı"];
  // "Kapalı" stays the value the engine sees; only the label is translated.
  const fgLabel = (x: string) => (x === "Kapalı" ? t.fgOff : x);

  const r = estimateFpsDetailed(
    cpu as never, { ...gpu, vram: gpu.vram ?? 8 } as never,
    game, res, set, ups, fg, ram, rt, pt,
  );
  const target = targetFps(game);
  const v = verdict(r.fps, target, r.status);
  const color = VERDICT_COLOR[v];
  const measured = (game.measurements ?? 0) > 0;

  return (
    <>
      <div onClick={onClose} style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 20,
      }} />
      {/* A 470px drawer is wider than a phone, so on mobile it becomes a
          bottom sheet instead — the same content, reachable with a thumb. */}
      <aside style={mobile ? {
        position: "fixed", left: 0, right: 0, bottom: 0, maxHeight: "88%", zIndex: 21,
        background: "var(--surface)", borderTop: "1px solid var(--border-strong)",
        borderRadius: "16px 16px 0 0", padding: "20px 18px 28px", overflowY: "auto",
      } : {
        position: "fixed", top: 0, right: 0, bottom: 0, width: 470, zIndex: 21,
        background: "var(--surface)", borderLeft: "1px solid var(--border-strong)",
        padding: "30px 32px", overflowY: "auto",
      }}>
        <div style={{ display: "flex", alignItems: "start", gap: 14 }}>
          <div style={{ flex: 1 }}>
            <h2 style={{ fontSize: 22, fontWeight: 600, margin: 0, letterSpacing: "-0.01em" }}>
              {game.name}
            </h2>
            <div style={{ fontSize: 13.5, color: "var(--text-3)", marginTop: 5 }}>
              {t.detailTargetLine(game.genre, !!game.competitive, target)}
            </div>
            {/* The single most important thing on this panel: whether the big
                number below is worth trusting. Measured rows sit at 8.9% mean
                error, derived ones were 49.2% out against the same set. */}
            <div style={{
              marginTop: 10, display: "inline-flex", alignItems: "center", gap: 7,
              fontSize: 12.5, borderRadius: 8, padding: "6px 10px",
              border: `1px solid ${measured ? "var(--green)" : "var(--border)"}`,
              background: measured ? "var(--green-dim)" : "transparent",
              color: measured ? "var(--green)" : "var(--text-3)",
            }}>
              {measured ? t.measuredBadge(game.measurements ?? 0) : t.estimatedBadge}
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "var(--raised)", border: "1px solid var(--border)", borderRadius: 9,
            width: 34, height: 34, color: "var(--text-2)", fontSize: 15,
          }}>✕</button>
        </div>

        <div style={{
          margin: "26px 0", padding: "26px 0", borderTop: "1px solid var(--border)",
          borderBottom: "1px solid var(--border)", textAlign: "center",
        }}>
          <div style={{
            fontFamily: "var(--mono)", fontSize: 66, fontWeight: 600, lineHeight: 1, color,
          }}>{r.fps}</div>
          <div style={{ fontSize: 14, color, marginTop: 9, fontWeight: 500 }}>
            {t[VERDICT_KEY[v]]}
          </div>
          {/* Measured as a ratio of 1% low to average across 336 rows. It came
              out a property of the game rather than of the hardware, which is
              why it can be stated per title. */}
          <div style={{
            fontSize: 13, color: "var(--text-2)", marginTop: 11,
            fontFamily: "var(--mono)",
          }}>{t.fpsRange(r.fps_low, r.fps)}</div>
          <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 4 }}>
            {r.fps_low_measured ? t.lowMeasured : t.lowAssumed}
          </div>
          <div style={{ fontSize: 13, color: "var(--text-3)", marginTop: 7 }}>
            {t.bottleneckLine(r.bottleneck, r.vram_needed_gb, r.quality)}
          </div>
          {!measured && (
            <div style={{
              fontSize: 12.5, color: "var(--text-3)", marginTop: 12,
              maxWidth: 330, marginLeft: "auto", marginRight: "auto", lineHeight: 1.55,
            }}>
              {t.estimatedExplain}
            </div>
          )}
        </div>

        <div style={{ display: "grid", gap: 17 }}>
          <Field label={t.resolution}>
            <Segmented value={res} onChange={setRes}
              options={RESOLUTIONS.map((x) => ({ value: x, label: x }))} />
          </Field>
          <Field label={t.preset}>
            <Segmented value={set} onChange={setSet}
              options={PRESETS.map((x) => ({ value: x, label: x }))} />
          </Field>
          {techs.length > 1 ? (
            <>
              <Field label={t.upscaling}>
                <Segmented value={upsTech} onChange={setUpsTech}
                  options={techs.map((x) => ({
                    value: x, label: x === "Native" ? t.nativeRes : x,
                  }))} />
              </Field>
              {scaled && (
                <Field label={t.upscalingLevel}>
                  <Segmented value={upsLevel} onChange={setUpsLevel}
                    options={LEVELS.map((x) => ({ value: x, label: t.upsLevel[x] }))} />
                </Field>
              )}
            </>
          ) : (
            <Unsupported label={t.upscaling} note={t.noUpscaling} />
          )}
          {fgOptions.length > 1 ? (
            <Field label={t.frameGen}>
              <Segmented value={fg} onChange={setFg}
                options={fgOptions.map((x) => ({ value: x, label: fgLabel(x) }))} />
            </Field>
          ) : (
            <Unsupported
              label={t.frameGen}
              note={gameHasFg ? t.noFgGpu : t.noFgGame}
            />
          )}
          <div style={{ display: "flex", gap: 12 }}>
            <Toggle on={rt} disabled={!game.supports_rt} onClick={() => setRt(!rt)} label={t.rayTracing} />
            <Toggle on={pt} disabled={!game.supports_pt} onClick={() => setPt(!pt)} label={t.pathTracing} />
          </div>
          {/* Which features a game ships is checked for 27 of the 176. For the
              rest these switches are showing a derivation, and a greyed-out
              toggle looks exactly as certain as a verified one — which is how
              Resident Evil Requiem came to hide a path-tracing mode it has. */}
          {!game.flags_verified && (
            <div style={{ fontSize: 12, color: "var(--text-3)", lineHeight: 1.5 }}>
              {t.flagsUnverified}
            </div>
          )}
        </div>

        {r.notes.length > 0 && (
          <div style={{ marginTop: 26, display: "grid", gap: 12 }}>
            {r.notes.map((n, i) => (
              <div key={i} style={{
                fontSize: 13.5, lineHeight: 1.65, color: "var(--text)",
                background: "var(--red-dim)",
                border: "1px solid var(--red-deep)",
                borderRadius: 10, padding: "13px 15px",
                display: "flex", gap: 11,
              }}>
                <span style={{ color: "var(--red)", fontSize: 16, lineHeight: 1.3 }}>⚠</span>
                <span>{renderNote(n, lang)}</span>
              </div>
            ))}
          </div>
        )}
      </aside>
    </>
  );
}

// ─── Primitives ──────────────────────────────────────────────────────────────

/** States plainly that a feature is absent, instead of offering it greyed out
 *  or — worse — offering it as if it worked. */
function Unsupported({ label, note }: { label: string; note: string }) {
  return (
    <Field label={label}>
      <div style={{
        padding: "12px 14px", borderRadius: 10, fontSize: 14,
        border: "1px dashed var(--border)", color: "var(--text-3)",
      }}>{note}</div>
    </Field>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{
        fontSize: 11.5, color: "var(--text-3)", marginBottom: 6,
        textTransform: "uppercase", letterSpacing: "0.11em", fontWeight: 500,
      }}>{label}</div>
      {children}
    </div>
  );
}

/**
 * A row of choices — or a block of them.
 *
 * Once upscaling started being built from what each game actually supports,
 * a title with DLSS, FSR and XeSS produces nine options. Nine `nowrap` buttons
 * in a 470px drawer came to 755px and pushed the panel's contents off the
 * side. Past four options it wraps instead of insisting on one line.
 */
function Segmented({ value, onChange, options }: {
  value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  const wrap = options.length > 4;
  return (
    <div style={{
      display: "flex", flexWrap: wrap ? "wrap" : "nowrap",
      background: "var(--surface)", borderRadius: 10,
      border: "1px solid var(--border)", padding: 3, gap: 3,
    }}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            style={{
              flex: wrap ? "1 1 30%" : "1 1 0", minWidth: 0,
              padding: "9px 8px", borderRadius: 7, border: "none",
              background: on ? "var(--amber)" : "transparent",
              color: on ? "#170F02" : "var(--text-2)",
              fontSize: 14, fontWeight: on ? 600 : 400,
              fontFamily: "var(--mono)",
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}
          >{o.label}</button>
        );
      })}
    </div>
  );
}

function Toggle({ on, disabled, onClick, label }: {
  on: boolean; disabled?: boolean; onClick: () => void; label: string;
}) {
  const { t } = useT();
  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      title={disabled ? t.unsupported : undefined}
      style={{
        flex: 1, padding: "13px 10px", borderRadius: 10, fontSize: 14.5,
        border: `1px solid ${on ? "var(--amber)" : "var(--border)"}`,
        background: on ? "var(--amber-glow)" : "var(--surface)",
        color: disabled ? "var(--text-3)" : on ? "var(--amber)" : "var(--text-2)",
        opacity: disabled ? 0.35 : 1,
        cursor: disabled ? "not-allowed" : "pointer",
        fontWeight: on ? 600 : 400,
      }}
    >{label}</button>
  );
}
