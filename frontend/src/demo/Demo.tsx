import { useMemo, useState } from "react";
import { cpus, gpus, games, predictAll } from "../engine/catalog";
import { estimateFpsDetailed, getFgOptions } from "../engine/cadence";
import type { CPUData, GPUData } from "../types";
import { targetFps, verdict, searchGames, VERDICT_COLOR, VERDICT_LABEL, type Verdict } from "./lib";
import Picker from "./Picker";

const RESOLUTIONS = ["1080p", "1440p", "4k"];
const PRESETS = ["Low", "Medium", "High", "Ultra"];
const RAM = [8, 16, 32, 64];
const UPSCALING = ["Native", "DLAA", "DLSS Quality", "DLSS Balanced", "DLSS Performance"];

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
  const [section, setSection] = useState<"gaming" | "workstation">("gaming");
  const [phase, setPhase] = useState<Phase>("build");

  const [cpu, setCpu] = useState<CPUData | null>(null);
  const [gpu, setGpu] = useState<GPUData | null>(null);
  const [ram, setRam] = useState(16);
  const [resolution, setResolution] = useState("1440p");
  const [preset, setPreset] = useState("High");

  const [query, setQuery] = useState("");
  const [onlyProblems, setOnlyProblems] = useState(false);
  const [sort, setSort] = useState<Sort>("struggling");
  const [openId, setOpenId] = useState<number | null>(null);

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

  const rows = useMemo(() => {
    const hits = query.trim() ? new Map(searchGames(query).map((h) => [h.id, h.score])) : null;
    let list = [...scored];
    if (onlyProblems) list = list.filter((r) => r.v === "poor" || r.v === "bad");
    if (hits) {
      list = list.filter((r) => hits.has(r.id))
        .sort((a, b) => (hits.get(b.id)! - hits.get(a.id)!) || b.fps - a.fps);
    } else if (sort === "struggling") {
      list.sort((a, b) => a.fps / a.target - b.fps / b.target);
    } else if (sort === "fastest") {
      list.sort((a, b) => b.fps - a.fps);
    } else {
      list.sort((a, b) => a.name.localeCompare(b.name, "tr"));
    }
    return list;
  }, [scored, query, onlyProblems, sort]);

  const summary = useMemo(() => ({
    good: scored.filter((r) => r.v === "good").length,
    close: scored.filter((r) => r.v === "close").length,
    poor: scored.filter((r) => r.v === "poor").length,
    bad: scored.filter((r) => r.v === "bad").length,
  }), [scored]);

  const ready = !!cpu && !!gpu;
  const open = openId === null ? null : games.find((g) => g.id === openId) ?? null;

  return (
    <div style={{ display: "flex", height: "100%", background: "var(--bg)" }}>
      <Sidebar section={section} onSection={setSection} onHome={() => setPhase("build")} />

      <main style={{ flex: 1, position: "relative", overflow: "hidden" }}>
        {section === "workstation" ? (
          <Placeholder />
        ) : (
          <Stage phase={phase}>
            {phase === "build" ? (
              <Builder
                cpu={cpu} gpu={gpu} ram={ram} resolution={resolution} preset={preset}
                onCpu={setCpu} onGpu={setGpu} onRam={setRam}
                onResolution={setResolution} onPreset={setPreset}
                ready={ready} total={games.length}
                onSubmit={() => setPhase("results")}
              />
            ) : (
              <Results
                cpu={cpu!} gpu={gpu!} ram={ram} resolution={resolution} preset={preset}
                rows={rows} summary={summary} total={scored.length}
                problemCount={problemCount}
                query={query} onQuery={setQuery}
                onlyProblems={onlyProblems} onToggleProblems={setOnlyProblems}
                sort={sort} onSort={setSort}
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
          resolution={resolution} preset={preset}
          onClose={() => setOpenId(null)}
        />
      )}
    </div>
  );
}

// ─── Shell ───────────────────────────────────────────────────────────────────

function Sidebar({ section, onSection, onHome }: {
  section: "gaming" | "workstation";
  onSection: (s: "gaming" | "workstation") => void;
  onHome: () => void;
}) {
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
          Performans
        </div>
      </button>

      <nav style={{ padding: "0 14px", display: "grid", gap: 4 }}>
        <NavItem active={section === "gaming"} onClick={() => onSection("gaming")}
          label="Oyun" hint="FPS tahmini" />
        <NavItem active={section === "workstation"} onClick={() => onSection("workstation")}
          label="İş istasyonu" hint="Render, derleme" muted />
      </nav>

      <div style={{ marginTop: "auto", padding: "0 26px" }}>
        <div style={{
          fontFamily: "var(--mono)", fontSize: 12, color: "var(--text-3)", lineHeight: 1.8,
        }}>
          Cadence 1.0<br />
          106 ölçüm · %9.0 hata
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
function Stage({ phase, children }: { phase: Phase; children: React.ReactNode }) {
  const building = phase === "build";
  return (
    <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
      <Blueprint dim={!building} />
      <div style={{
        position: "relative",
        width: building ? "min(1180px, 92%)" : "100%",
        height: building ? "min(700px, 84%)" : "100%",
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
          width: 150, height: building ? 54 : 0,
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
  return (
    <div style={{ display: "grid", placeItems: "center", height: "100%", textAlign: "center" }}>
      <div>
        <div style={{ fontSize: 24, fontWeight: 600 }}>İş istasyonu modu</div>
        <p style={{ color: "var(--text-2)", maxWidth: 440, margin: "12px auto 0", lineHeight: 1.7, fontSize: 16 }}>
          Bu bölüm ayrı veri istiyor: tek çekirdek ve çok çekirdek skorları,
          Blender gibi uygulamalarda ölçülmüş süreler. Oyun puanları buraya
          taşınamaz — bilerek oyun endeksine çevrildiler.
        </p>
      </div>
    </div>
  );
}

// ─── Build ───────────────────────────────────────────────────────────────────

function Builder(p: {
  cpu: CPUData | null; gpu: GPUData | null; ram: number;
  resolution: string; preset: string; ready: boolean; total: number;
  onCpu: (c: CPUData | null) => void; onGpu: (g: GPUData | null) => void;
  onRam: (n: number) => void; onResolution: (s: string) => void;
  onPreset: (s: string) => void; onSubmit: () => void;
}) {
  return (
    <div style={{ padding: "44px 56px", height: "100%", overflowY: "auto" }}>
      <div style={{ maxWidth: 720, margin: "0 auto" }}>
        <h1 style={{ fontSize: 30, fontWeight: 600, letterSpacing: "-0.02em", margin: 0 }}>
          Sistemini kur
        </h1>
        <p style={{ color: "var(--text-2)", margin: "10px 0 32px", fontSize: 16, lineHeight: 1.6 }}>
          Çözünürlük ve preset tüm listeyi belirler. Ray tracing, upscaling ve
          frame generation oyun başına, detay panelinden.
        </p>

        <div style={{ display: "grid", gap: 20 }}>
          <Field label="İşlemci">
            <Picker
              items={cpus.map((c) => ({ value: c.name, label: c.name, meta: String(c.power_score) }))}
              value={p.cpu?.name ?? ""}
              onChange={(v) => p.onCpu(cpus.find((c) => c.name === v) ?? null)}
              placeholder="Ara — 5600, 14700, x3d…"
              emptyLabel="İşlemci seçin"
            />
          </Field>
          <Field label="Ekran kartı">
            <Picker
              items={gpus.map((g) => ({
                value: g.name, label: g.name,
                meta: `${g.power_score}${g.vram ? ` · ${g.vram}GB` : ""}`,
              }))}
              value={p.gpu?.name ?? ""}
              onChange={(v) => p.onGpu(gpus.find((g) => g.name === v) ?? null)}
              placeholder="Ara — 4070, 9070 xt, arc…"
              emptyLabel="Ekran kartı seçin"
            />
          </Field>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1.2fr", gap: 16 }}>
            <Field label="RAM">
              <Segmented value={String(p.ram)} onChange={(v) => p.onRam(Number(v))}
                options={RAM.map((r) => ({ value: String(r), label: `${r}` }))} />
            </Field>
            <Field label="Çözünürlük">
              <Segmented value={p.resolution} onChange={p.onResolution}
                options={RESOLUTIONS.map((r) => ({ value: r, label: r }))} />
            </Field>
            <Field label="Preset">
              <Segmented value={p.preset} onChange={p.onPreset}
                options={PRESETS.map((r) => ({ value: r, label: r }))} />
            </Field>
          </div>
        </div>

        <button
          onClick={p.onSubmit}
          disabled={!p.ready}
          style={{
            marginTop: 34, width: "100%", padding: "17px 0", borderRadius: 12,
            border: "1px solid " + (p.ready ? "var(--amber)" : "var(--border)"),
            background: p.ready ? "var(--amber)" : "transparent",
            color: p.ready ? "#170F02" : "var(--text-3)",
            fontWeight: 600, fontSize: 17,
            cursor: p.ready ? "pointer" : "not-allowed",
          }}
        >
          {p.ready ? `${p.total} oyunu hesapla` : "İşlemci ve ekran kartı seçin"}
        </button>
      </div>
    </div>
  );
}

// ─── Results ─────────────────────────────────────────────────────────────────

type Row = {
  id: number; name: string; genre: string; fps: number; target: number;
  v: Verdict; game: Game; status?: string; vram_needed_gb?: number; warnings?: string[];
};

const WIDTH = 1180;

function Results(p: {
  cpu: CPUData; gpu: GPUData; ram: number; resolution: string; preset: string;
  rows: Row[]; total: number; problemCount: number;
  summary: { good: number; close: number; poor: number; bad: number };
  query: string; onQuery: (s: string) => void;
  onlyProblems: boolean; onToggleProblems: (b: boolean) => void;
  sort: Sort; onSort: (s: Sort) => void;
  onBack: () => void; onOpen: (id: number) => void;
}) {
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <header style={{ padding: "24px 36px 20px", borderBottom: "1px solid var(--border)" }}>
        <div style={{
          maxWidth: WIDTH, margin: "0 auto", display: "flex",
          alignItems: "center", gap: 26, flexWrap: "wrap",
        }}>
          <button onClick={p.onBack} style={{
            background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 10, padding: "10px 15px", fontSize: 14, color: "var(--text-2)",
          }}>← Sistemi değiştir</button>

          <div style={{ fontFamily: "var(--mono)", fontSize: 13.5, color: "var(--text-2)" }}>
            {p.cpu.name} · {p.gpu.name} · {p.ram} GB ·{" "}
            <span style={{ color: "var(--amber)" }}>{p.resolution} {p.preset}</span>
          </div>

          <div style={{ marginLeft: "auto", display: "flex", gap: 10 }}>
            <Chip n={p.summary.good} label="hedefte" color="var(--green)" />
            <Chip n={p.summary.close} label="yakın" color="var(--orange)" />
            <Chip n={p.summary.poor + p.summary.bad} label="sorunlu" color="var(--red)" />
          </div>
        </div>
      </header>

      <div style={{ padding: "16px 36px", borderBottom: "1px solid var(--border)" }}>
        <div style={{ maxWidth: WIDTH, margin: "0 auto", display: "flex", gap: 14, alignItems: "center" }}>
          <input
            value={p.query}
            onChange={(e) => p.onQuery(e.target.value)}
            placeholder="Oyun ara —  cs2, gta, cyberpunk…"
            style={{
              flex: 1, background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 10, padding: "13px 16px", fontSize: 15.5, outline: "none",
            }}
          />
          <Segmented
            value={p.sort} onChange={(v) => p.onSort(v as Sort)}
            options={[
              { value: "struggling", label: "Zorlananlar" },
              { value: "fastest", label: "En hızlı" },
              { value: "name", label: "A-Z" },
            ]}
          />
          {/* The count lives in the label because with "struggling" sorting the
              top of the list is already the problems — toggling the filter used
              to change nothing visible and read as a broken button. */}
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
            Sorunlular · {p.problemCount}
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: "auto" }}>
        <div style={{ maxWidth: WIDTH, margin: "0 auto", padding: "0 36px" }}>
          {(p.query || p.onlyProblems) && (
            <div style={{
              padding: "12px 0", fontSize: 13.5, color: "var(--text-2)",
              fontFamily: "var(--mono)",
            }}>
              {p.total} oyundan {p.rows.length} tanesi gösteriliyor
              {p.onlyProblems && " · sadece sorunlular"}
            </div>
          )}
          {p.rows.length === 0 ? (
            <div style={{ padding: 70, textAlign: "center", color: "var(--text-3)", fontSize: 16 }}>
              Eşleşen oyun yok.
            </div>
          ) : (
            p.rows.map((r) => <GameRow key={r.id} row={r} onOpen={() => p.onOpen(r.id)} />)
          )}
        </div>
      </div>
    </div>
  );
}

function Chip({ n, label, color }: { n: number; label: string; color: string }) {
  return (
    <div style={{
      display: "flex", alignItems: "baseline", gap: 7,
      background: "var(--surface)", border: "1px solid var(--border)",
      borderRadius: 10, padding: "8px 13px",
    }}>
      <span style={{ fontFamily: "var(--mono)", fontSize: 19, fontWeight: 600, color }}>{n}</span>
      <span style={{ fontSize: 12.5, color: "var(--text-3)" }}>{label}</span>
    </div>
  );
}

/**
 * One game.
 *
 * The frame rate is colour coded, which is only honest because it is judged
 * against this game's own target rather than a fixed number — 60 fps is green
 * in an RPG and red in Counter-Strike, and both are correct.
 */
function GameRow({ row, onOpen }: { row: Row; onOpen: () => void }) {
  const color = VERDICT_COLOR[row.v];
  const ratio = Math.min(1, row.fps / row.target);
  const warning = row.status && row.status !== "ok" && row.status !== "ram_short";

  return (
    <button
      onClick={onOpen}
      style={{
        display: "grid", gridTemplateColumns: "1fr 190px 130px", alignItems: "center",
        gap: 22, width: "100%", textAlign: "left", padding: "17px 14px",
        background: "none", border: "none", borderBottom: "1px solid var(--border)",
        borderRadius: 8,
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{
          fontSize: 17, fontWeight: 500,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>{row.name}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 9, marginTop: 4 }}>
          <span style={{ fontSize: 13, color: "var(--text-3)" }}>{row.genre}</span>
          {row.game.competitive ? (
            <span style={{
              fontSize: 11, fontFamily: "var(--mono)", color: "var(--amber)",
              border: "1px solid var(--amber-dim)", borderRadius: 5, padding: "1px 6px",
            }}>REKABETÇİ</span>
          ) : null}
          {warning && (
            <span style={{
              fontSize: 12, fontWeight: 600, color: "var(--red)",
              background: "var(--red-dim)", border: "1px solid var(--red-deep)",
              borderRadius: 6, padding: "2px 8px",
            }}>
              {row.status === "unplayable" ? "⚠ OYNANAMAZ"
                : row.status === "vram_spill" ? `⚠ VRAM TAŞIYOR · ${row.vram_needed_gb} GB`
                : `⚠ VRAM SINIRDA · ${row.vram_needed_gb} GB`}
            </span>
          )}
        </div>
      </div>

      <div>
        <div style={{ height: 7, background: "var(--raised)", borderRadius: 4, overflow: "hidden" }}>
          <div style={{ width: `${ratio * 100}%`, height: "100%", background: color }} />
        </div>
        <div style={{
          fontSize: 12, color: "var(--text-3)", marginTop: 7, fontFamily: "var(--mono)",
          display: "flex", justifyContent: "space-between",
        }}>
          <span>{VERDICT_LABEL[row.v]}</span>
          <span>hedef {row.target}</span>
        </div>
      </div>

      <div style={{ textAlign: "right" }}>
        <span style={{ fontFamily: "var(--mono)", fontSize: 27, fontWeight: 600, color }}>
          {row.fps}
        </span>
        <span style={{ fontSize: 12.5, color: "var(--text-3)", marginLeft: 5 }}>fps</span>
      </div>
    </button>
  );
}

// ─── Per-game detail ─────────────────────────────────────────────────────────

function Detail({ game, cpu, gpu, ram, resolution, preset, onClose }: {
  game: Game; cpu: CPUData; gpu: GPUData; ram: number;
  resolution: string; preset: string; onClose: () => void;
}) {
  const [res, setRes] = useState(resolution);
  const [set, setSet] = useState(preset);
  const [ups, setUps] = useState("Native");
  const [fg, setFg] = useState("Kapalı");
  const [rt, setRt] = useState(false);
  const [pt, setPt] = useState(false);

  const fgOptions = getFgOptions(gpu.name);

  const r = estimateFpsDetailed(
    { name: cpu.name, power_score: cpu.power_score },
    { name: gpu.name, power_score: gpu.power_score, vram: gpu.vram ?? 8 },
    game, res, set, ups, fg, ram, rt, pt,
  );
  const target = targetFps(game);
  const v = verdict(r.fps, target, r.status);
  const color = VERDICT_COLOR[v];

  return (
    <>
      <div onClick={onClose} style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 20,
      }} />
      <aside style={{
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
              {game.genre}
              {game.competitive ? " · rekabetçi" : ""} · hedef {target} fps
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
            {VERDICT_LABEL[v]}
          </div>
          <div style={{ fontSize: 13, color: "var(--text-3)", marginTop: 7 }}>
            {r.bottleneck} sınırlı · {r.vram_needed_gb} GB VRAM · {r.quality}
          </div>
        </div>

        <div style={{ display: "grid", gap: 17 }}>
          <Field label="Çözünürlük">
            <Segmented value={res} onChange={setRes}
              options={RESOLUTIONS.map((x) => ({ value: x, label: x }))} />
          </Field>
          <Field label="Preset">
            <Segmented value={set} onChange={setSet}
              options={PRESETS.map((x) => ({ value: x, label: x }))} />
          </Field>
          <Field label="Upscaling">
            <Segmented value={ups} onChange={setUps}
              options={UPSCALING.map((x) => ({ value: x, label: x.replace("DLSS ", "") }))} />
          </Field>
          {fgOptions.length > 1 && (
            <Field label="Frame generation">
              <Segmented value={fg} onChange={setFg}
                options={fgOptions.map((x) => ({ value: x, label: x }))} />
            </Field>
          )}
          <div style={{ display: "flex", gap: 12 }}>
            <Toggle on={rt} disabled={!game.supports_rt} onClick={() => setRt(!rt)} label="Ray tracing" />
            <Toggle on={pt} disabled={!game.supports_pt} onClick={() => setPt(!pt)} label="Path tracing" />
          </div>
        </div>

        {r.warnings.length > 0 && (
          <div style={{ marginTop: 26, display: "grid", gap: 12 }}>
            {r.warnings.map((w, i) => (
              <div key={i} style={{
                fontSize: 13.5, lineHeight: 1.65, color: "var(--text)",
                background: "var(--red-dim)",
                border: "1px solid var(--red-deep)",
                borderRadius: 10, padding: "13px 15px",
                display: "flex", gap: 11,
              }}>
                <span style={{ color: "var(--red)", fontSize: 16, lineHeight: 1.3 }}>⚠</span>
                <span>{w}</span>
              </div>
            ))}
          </div>
        )}
      </aside>
    </>
  );
}

// ─── Primitives ──────────────────────────────────────────────────────────────

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{
        fontSize: 12, color: "var(--text-3)", marginBottom: 8,
        textTransform: "uppercase", letterSpacing: "0.11em", fontWeight: 500,
      }}>{label}</div>
      {children}
    </div>
  );
}

function Segmented({ value, onChange, options }: {
  value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div style={{
      display: "flex", background: "var(--surface)", borderRadius: 10,
      border: "1px solid var(--border)", padding: 3, gap: 3,
    }}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            style={{
              flex: 1, padding: "9px 8px", borderRadius: 7, border: "none",
              background: on ? "var(--amber)" : "transparent",
              color: on ? "#170F02" : "var(--text-2)",
              fontSize: 14, fontWeight: on ? 600 : 400,
              fontFamily: "var(--mono)", whiteSpace: "nowrap",
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
  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      title={disabled ? "Bu oyun desteklemiyor" : undefined}
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
