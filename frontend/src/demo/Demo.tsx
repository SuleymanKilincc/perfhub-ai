import { useMemo, useState } from "react";
import { cpus, gpus, games, predictAll } from "../engine/catalog";
import { estimateFpsDetailed, getFgOptions } from "../engine/cadence";
import type { CPUData, GPUData } from "../types";
import { targetFps, verdict, searchGames } from "./lib";

const RESOLUTIONS = ["1080p", "1440p", "4k"];
const PRESETS = ["Low", "Medium", "High", "Ultra"];
const RAM = [8, 16, 32, 64];
const UPSCALING = ["Native", "DLAA", "DLSS Quality", "DLSS Balanced", "DLSS Performance"];

type Phase = "build" | "results";

/**
 * Sorting by raw frame rate is the obvious default and it is useless: the top
 * of the list is always Stardew Valley at 961 fps, and every bar is pinned to
 * full because everything up there is miles past its target. Nobody opens this
 * to find out that Terraria runs.
 *
 * "struggling" sorts by frame rate *relative to the game's own target*, worst
 * first, which puts the answer to the actual question — what will this machine
 * have trouble with — on the first screen.
 */
type Sort = "struggling" | "fastest";

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

  const results = useMemo(() => {
    if (!cpu || !gpu) return [];
    return predictAll({ cpu, gpu, ramGb: ram, resolution, preset });
  }, [cpu, gpu, ram, resolution, preset]);

  const rows = useMemo(() => {
    const hits = query.trim() ? new Map(searchGames(query).map((h) => [h.id, h.score])) : null;
    let list = results.map((r) => {
      const target = targetFps(r.genre);
      return { ...r, target, v: verdict(r.fps, target, r.status ?? "ok") };
    });
    if (hits) {
      list = list.filter((r) => hits.has(r.id))
        .sort((a, b) => (hits.get(b.id)! - hits.get(a.id)!) || b.fps - a.fps);
    } else if (sort === "struggling") {
      list.sort((a, b) => a.fps / a.target - b.fps / b.target);
    } else {
      list.sort((a, b) => b.fps - a.fps);
    }
    if (onlyProblems) list = list.filter((r) => r.v === "bad" || r.v === "under");
    return list;
  }, [results, query, onlyProblems, sort]);

  const summary = useMemo(() => {
    const all = results.map((r) => verdict(r.fps, targetFps(r.genre), r.status ?? "ok"));
    return {
      total: all.length,
      good: all.filter((v) => v === "over" || v === "at").length,
      under: all.filter((v) => v === "under").length,
      bad: all.filter((v) => v === "bad").length,
    };
  }, [results]);

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
                ready={ready} onSubmit={() => setPhase("results")}
              />
            ) : (
              <Results
                cpu={cpu!} gpu={gpu!} ram={ram} resolution={resolution} preset={preset}
                rows={rows} summary={summary}
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
      width: 232, flexShrink: 0, borderRight: "1px solid var(--border)",
      background: "var(--surface)", display: "flex", flexDirection: "column",
      padding: "28px 0",
    }}>
      <button
        onClick={onHome}
        style={{
          background: "none", border: "none", padding: "0 24px 28px",
          textAlign: "left", display: "block",
        }}
      >
        <div style={{
          fontFamily: "var(--mono)", fontSize: 11, letterSpacing: "0.35em",
          color: "var(--text-3)",
        }}>PERFHUB</div>
        <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.02em", marginTop: 2 }}>
          Performans
        </div>
      </button>

      <nav style={{ padding: "0 12px", display: "grid", gap: 2 }}>
        <NavItem
          active={section === "gaming"} onClick={() => onSection("gaming")}
          label="Oyun" hint="FPS tahmini"
        />
        <NavItem
          active={section === "workstation"} onClick={() => onSection("workstation")}
          label="İş istasyonu" hint="Render, derleme" muted
        />
      </nav>

      <div style={{ marginTop: "auto", padding: "0 24px" }}>
        <div style={{
          fontFamily: "var(--mono)", fontSize: 11, color: "var(--text-3)",
          lineHeight: 1.7,
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
        padding: "11px 12px", borderRadius: 8, border: "none",
        background: active ? "var(--raised)" : "transparent",
        position: "relative",
      }}
    >
      {active && (
        <span style={{
          position: "absolute", left: 0, top: 12, bottom: 12, width: 2,
          background: "var(--amber)", borderRadius: 2,
        }} />
      )}
      <div style={{
        fontSize: 14, fontWeight: 500,
        color: active ? "var(--text)" : muted ? "var(--text-3)" : "var(--text-2)",
      }}>{label}</div>
      <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 1 }}>{hint}</div>
    </button>
  );
}

/**
 * The monitor frame, and the transition through it.
 *
 * In the build phase it is a real bezel with blueprint line art behind it —
 * a performance tool shown inside a monitor, which is form matching subject
 * rather than decoration. On submit the camera pushes into the screen and the
 * bezel scales past the viewport, which is both the "entering an object"
 * effect and the fix for the frame's real problem: a fixed bezel around a
 * 180-row list leaves far too little room to read it.
 */
function Stage({ phase, children }: { phase: Phase; children: React.ReactNode }) {
  const building = phase === "build";
  return (
    <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
      <Blueprint dim={!building} />
      <div
        style={{
          position: "relative",
          width: building ? "min(880px, 88%)" : "100%",
          height: building ? "min(560px, 82%)" : "100%",
          transform: building ? "scale(1)" : "scale(1)",
          transition: "width 620ms var(--ease), height 620ms var(--ease)",
        }}
      >
        {/* Bezel */}
        <div style={{
          position: "absolute", inset: 0,
          borderRadius: building ? 18 : 0,
          border: `1px solid ${building ? "var(--border)" : "transparent"}`,
          background: "var(--surface)",
          padding: building ? 14 : 0,
          transition: "border-radius 620ms var(--ease), padding 620ms var(--ease), border-color 620ms var(--ease)",
          boxShadow: building ? "0 40px 80px -20px rgba(0,0,0,0.7)" : "none",
        }}>
          <div style={{
            width: "100%", height: "100%", overflow: "hidden",
            borderRadius: building ? 8 : 0,
            background: "var(--bg)",
            transition: "border-radius 620ms var(--ease)",
          }}>
            {children}
          </div>
        </div>

        {/* Stand, only while the monitor is a monitor. */}
        <div style={{
          position: "absolute", top: "100%", left: "50%",
          transform: "translateX(-50%)",
          width: 120, height: building ? 46 : 0,
          background: "linear-gradient(var(--raised), var(--surface))",
          borderRadius: "0 0 10px 10px",
          opacity: building ? 1 : 0,
          transition: "height 420ms var(--ease), opacity 300ms var(--ease)",
        }} />
      </div>
    </div>
  );
}

/** Technical line art. Low contrast on purpose — texture, not content. */
function Blueprint({ dim }: { dim: boolean }) {
  return (
    <svg
      aria-hidden
      style={{
        position: "absolute", inset: 0, width: "100%", height: "100%",
        opacity: dim ? 0.25 : 1,
        transition: "opacity 620ms var(--ease)",
        pointerEvents: "none",
      }}
    >
      <defs>
        <pattern id="bp" width="44" height="44" patternUnits="userSpaceOnUse">
          <path d="M44 0 L0 0 0 44" fill="none" stroke="var(--line)" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#bp)" />
      <g stroke="var(--line)" fill="none" strokeWidth="1.5">
        <circle cx="14%" cy="34%" r="120" />
        <circle cx="14%" cy="34%" r="86" />
        <rect x="72%" y="16%" width="220" height="90" rx="4" />
        <rect x="76%" y="20%" width="140" height="34" rx="2" />
        {/* Percentages are legal on rect/circle but not inside a path's `d`,
            which is why these are rects rather than the paths they started as. */}
        <rect x="6%" y="74%" width="190" height="70" />
        <rect x="80%" y="70%" width="150" height="110" />
      </g>
      {/* The red corner marks from the reference — now with a job: they are the
          same red the app uses for a real problem, so the language is consistent. */}
      <g fill="var(--red)" opacity="0.5">
        <rect x="5%" y="12%" width="7" height="7" />
        <rect x="93%" y="12%" width="7" height="7" />
        <rect x="5%" y="86%" width="7" height="7" />
        <rect x="93%" y="86%" width="7" height="7" />
      </g>
    </svg>
  );
}

function Placeholder() {
  return (
    <div style={{ display: "grid", placeItems: "center", height: "100%", textAlign: "center" }}>
      <div>
        <div style={{ fontSize: 20, fontWeight: 500 }}>İş istasyonu modu</div>
        <p style={{ color: "var(--text-2)", maxWidth: 380, margin: "10px auto 0", lineHeight: 1.6 }}>
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
  resolution: string; preset: string; ready: boolean;
  onCpu: (c: CPUData | null) => void; onGpu: (g: GPUData | null) => void;
  onRam: (n: number) => void; onResolution: (s: string) => void;
  onPreset: (s: string) => void; onSubmit: () => void;
}) {
  return (
    <div style={{ padding: "38px 44px", height: "100%", overflowY: "auto" }}>
      <Label>Sistemini kur</Label>
      <p style={{ color: "var(--text-2)", margin: "8px 0 26px", fontSize: 14 }}>
        Çözünürlük ve preset tüm listeyi belirler. Ray tracing, upscaling ve
        frame generation oyun başına, detay panelinden.
      </p>

      <div style={{ display: "grid", gap: 16 }}>
        <Field label="İşlemci">
          <Select
            value={p.cpu?.name ?? ""}
            onChange={(v) => p.onCpu(cpus.find((c) => c.name === v) ?? null)}
            placeholder="Seçin"
            options={cpus.map((c) => ({ value: c.name, label: `${c.name}  ·  ${c.power_score}` }))}
          />
        </Field>
        <Field label="Ekran kartı">
          <Select
            value={p.gpu?.name ?? ""}
            onChange={(v) => p.onGpu(gpus.find((g) => g.name === v) ?? null)}
            placeholder="Seçin"
            options={gpus.map((g) => ({
              value: g.name,
              label: `${g.name}  ·  ${g.power_score}${g.vram ? `  ·  ${g.vram} GB` : ""}`,
            }))}
          />
        </Field>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
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
          marginTop: 30, width: "100%", padding: "14px 0", borderRadius: 10,
          border: "1px solid " + (p.ready ? "var(--amber)" : "var(--border)"),
          background: p.ready ? "var(--amber)" : "transparent",
          color: p.ready ? "#1A1204" : "var(--text-3)",
          fontWeight: 600, fontSize: 15,
          cursor: p.ready ? "pointer" : "not-allowed",
          transition: "background 200ms, color 200ms, border-color 200ms",
        }}
      >
        {p.ready ? "180 oyunu hesapla" : "İşlemci ve ekran kartı seçin"}
      </button>
    </div>
  );
}

// ─── Results ─────────────────────────────────────────────────────────────────

type Row = ReturnType<typeof Object> & {
  id: number; name: string; genre: string; fps: number;
  target: number; v: string; status?: string; vram_needed_gb?: number;
  warnings?: string[];
};

function Results(p: {
  cpu: CPUData; gpu: GPUData; ram: number; resolution: string; preset: string;
  rows: Row[]; summary: { total: number; good: number; under: number; bad: number };
  query: string; onQuery: (s: string) => void;
  onlyProblems: boolean; onToggleProblems: (b: boolean) => void;
  sort: Sort; onSort: (s: Sort) => void;
  onBack: () => void; onOpen: (id: number) => void;
}) {
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <header style={{
        padding: "22px 32px 18px", borderBottom: "1px solid var(--border)",
      }}>
       <div style={{
        maxWidth: 1040, margin: "0 auto",
        display: "flex", alignItems: "center", gap: 24, flexWrap: "wrap",
       }}>
        <button onClick={p.onBack} style={{
          background: "none", border: "1px solid var(--border)", borderRadius: 8,
          padding: "7px 12px", fontSize: 13, color: "var(--text-2)",
        }}>← Sistemi değiştir</button>

        <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--text-2)" }}>
          {p.cpu.name} · {p.gpu.name} · {p.ram} GB ·{" "}
          <span style={{ color: "var(--amber)" }}>{p.resolution} {p.preset}</span>
        </div>

        <div style={{ marginLeft: "auto", display: "flex", gap: 22, fontSize: 13 }}>
          <Stat n={p.summary.good} label="hedefte" />
          <Stat n={p.summary.under} label="hedefin altında" />
          <Stat n={p.summary.bad} label="sorunlu" tone="bad" />
        </div>
       </div>
      </header>

      <div style={{ padding: "14px 32px", borderBottom: "1px solid var(--border)" }}>
       <div style={{
        maxWidth: 1040, margin: "0 auto",
        display: "flex", gap: 12, alignItems: "center",
       }}>
        <input
          value={p.query}
          onChange={(e) => p.onQuery(e.target.value)}
          placeholder="Oyun ara —  cs2, gta, cyberpunk…"
          style={{
            flex: 1, background: "var(--surface)", border: "1px solid var(--border)",
            borderRadius: 8, padding: "10px 13px", fontSize: 14, outline: "none",
          }}
        />
        <Segmented
          value={p.sort}
          onChange={(v) => p.onSort(v as Sort)}
          options={[
            { value: "struggling", label: "Zorlananlar" },
            { value: "fastest", label: "En hızlı" },
          ]}
        />
        <button
          onClick={() => p.onToggleProblems(!p.onlyProblems)}
          style={{
            border: "1px solid " + (p.onlyProblems ? "var(--red)" : "var(--border)"),
            background: "transparent", borderRadius: 8, padding: "9px 13px",
            fontSize: 13, color: p.onlyProblems ? "var(--red)" : "var(--text-2)",
          }}
        >
          Sadece sorunlular
        </button>
       </div>
      </div>

      {/* A row is a name on the left and a number on the right, so letting it
          stretch to a 2500px monitor puts them a foot apart and the eye has to
          travel the whole way. Capped and centred instead. */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        <div style={{ maxWidth: 1040, margin: "0 auto" }}>
          {p.rows.length === 0 ? (
            <div style={{ padding: 60, textAlign: "center", color: "var(--text-3)" }}>
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

function Stat({ n, label, tone }: { n: number; label: string; tone?: "bad" }) {
  return (
    <div style={{ textAlign: "right" }}>
      <div style={{
        fontFamily: "var(--mono)", fontSize: 17, fontWeight: 600,
        color: tone === "bad" && n > 0 ? "var(--red)" : "var(--text)",
      }}>{n}</div>
      <div style={{ fontSize: 11, color: "var(--text-3)" }}>{label}</div>
    </div>
  );
}

/**
 * One game.
 *
 * The frame rate is not colour coded. 60 fps is a good result in a narrative
 * RPG and a poor one in a competitive shooter, so a traffic light bakes in a
 * judgement that is wrong about half the time. Instead the number stays
 * neutral, the target is printed next to it, and the amber bar shows where the
 * result lands against *that* target. Red appears only when something is
 * genuinely broken.
 */
function GameRow({ row, onOpen }: { row: Row; onOpen: () => void }) {
  const bad = row.v === "bad";
  const under = row.v === "under";
  const ratio = Math.min(1, row.fps / row.target);

  return (
    <button
      onClick={onOpen}
      style={{
        display: "grid", gridTemplateColumns: "1fr 150px 92px", alignItems: "center",
        gap: 18, width: "100%", textAlign: "left",
        padding: "13px 32px", background: "none",
        border: "none", borderBottom: "1px solid var(--border)",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = "var(--surface)")}
      onMouseLeave={(e) => (e.currentTarget.style.background = "none")}
    >
      <div style={{ minWidth: 0 }}>
        <div style={{
          fontSize: 15, fontWeight: 500,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>{row.name}</div>
        <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 2 }}>
          {row.genre || "—"}
          {bad && <span style={{ color: "var(--red)", marginLeft: 10 }}>
            {row.status === "unplayable" ? "oynanamaz" : "çok düşük"}
          </span>}
          {!bad && row.status && row.status !== "ok" && (
            <span style={{ color: "var(--red-dim)", marginLeft: 10 }}>
              {row.status === "vram_spill" ? "VRAM taşıyor" : "VRAM sınırda"}
            </span>
          )}
        </div>
      </div>

      {/* Relative to this game's own target, not to the fastest game in the
          list. A game comfortably past its target gets no bar at all — a row
          of identical full bars is noise, and "it's fine" needs no emphasis. */}
      <div>
        {row.v === "over" ? (
          <div style={{ height: 4, display: "flex", alignItems: "center" }}>
            <span style={{ fontSize: 11, color: "var(--text-3)" }}>hedefin üstünde</span>
          </div>
        ) : (
          <div style={{ height: 4, background: "var(--border)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{
              width: `${ratio * 100}%`, height: "100%",
              background: bad ? "var(--red)" : "var(--amber)",
              opacity: under ? 0.6 : 1,
            }} />
          </div>
        )}
        <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 5, fontFamily: "var(--mono)" }}>
          hedef {row.target}
        </div>
      </div>

      <div style={{ textAlign: "right" }}>
        <span style={{
          fontFamily: "var(--mono)", fontSize: 21, fontWeight: 600,
          color: bad ? "var(--red)" : "var(--text)",
        }}>{row.fps}</span>
        <span style={{ fontSize: 11, color: "var(--text-3)", marginLeft: 4 }}>fps</span>
      </div>
    </button>
  );
}

// ─── Per-game detail ─────────────────────────────────────────────────────────

function Detail({ game, cpu, gpu, ram, resolution, preset, onClose }: {
  game: (typeof games)[number]; cpu: CPUData; gpu: GPUData; ram: number;
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
  const target = targetFps(game.genre);
  const v = verdict(r.fps, target, r.status);

  return (
    <>
      <div onClick={onClose} style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 20,
      }} />
      <aside style={{
        position: "fixed", top: 0, right: 0, bottom: 0, width: 420, zIndex: 21,
        background: "var(--surface)", borderLeft: "1px solid var(--border)",
        padding: "26px 28px", overflowY: "auto",
      }}>
        <div style={{ display: "flex", alignItems: "start", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <Label>{game.name}</Label>
            <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 3 }}>
              {game.genre || "tür bilinmiyor"} · hedef {target} fps
            </div>
          </div>
          <button onClick={onClose} style={{
            background: "none", border: "1px solid var(--border)", borderRadius: 8,
            width: 30, height: 30, color: "var(--text-2)",
          }}>✕</button>
        </div>

        <div style={{
          margin: "22px 0", padding: "20px 0", borderTop: "1px solid var(--border)",
          borderBottom: "1px solid var(--border)", textAlign: "center",
        }}>
          <div style={{
            fontFamily: "var(--mono)", fontSize: 52, fontWeight: 600, lineHeight: 1,
            color: v === "bad" ? "var(--red)" : "var(--text)",
          }}>{r.fps}</div>
          <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 6 }}>
            {r.bottleneck} sınırlı · {r.vram_needed_gb} GB VRAM · {r.quality}
          </div>
        </div>

        <div style={{ display: "grid", gap: 14 }}>
          <Field label="Çözünürlük">
            <Segmented value={res} onChange={setRes}
              options={RESOLUTIONS.map((x) => ({ value: x, label: x }))} />
          </Field>
          <Field label="Preset">
            <Segmented value={set} onChange={setSet}
              options={PRESETS.map((x) => ({ value: x, label: x }))} />
          </Field>
          <Field label="Upscaling">
            <Select value={ups} onChange={setUps}
              options={UPSCALING.map((x) => ({ value: x, label: x }))} />
          </Field>

          {fgOptions.length > 1 && (
            <Field label="Frame generation">
              <Segmented value={fg} onChange={setFg}
                options={fgOptions.map((x) => ({ value: x, label: x }))} />
            </Field>
          )}

          <div style={{ display: "flex", gap: 10 }}>
            <Toggle
              on={rt} disabled={!game.supports_rt}
              onClick={() => setRt(!rt)} label="Ray tracing"
            />
            <Toggle
              on={pt} disabled={!game.supports_pt}
              onClick={() => setPt(!pt)} label="Path tracing"
            />
          </div>
        </div>

        {r.warnings.length > 0 && (
          <div style={{ marginTop: 22, display: "grid", gap: 8 }}>
            {r.warnings.map((w, i) => (
              <div key={i} style={{
                fontSize: 12, lineHeight: 1.55, color: "var(--text-2)",
                borderLeft: `2px solid ${r.status === "unplayable" ? "var(--red)" : "var(--red-dim)"}`,
                paddingLeft: 11,
              }}>{w}</div>
            ))}
          </div>
        )}
      </aside>
    </>
  );
}

// ─── Primitives ──────────────────────────────────────────────────────────────

function Label({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 19, fontWeight: 600, letterSpacing: "-0.01em" }}>{children}</div>;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{
        fontSize: 11, color: "var(--text-3)", marginBottom: 6,
        textTransform: "uppercase", letterSpacing: "0.1em",
      }}>{label}</div>
      {children}
    </div>
  );
}

function Select({ value, onChange, options, placeholder }: {
  value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[]; placeholder?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      style={{
        width: "100%", background: "var(--surface)", border: "1px solid var(--border)",
        borderRadius: 8, padding: "10px 12px", fontSize: 14, outline: "none",
      }}
    >
      {placeholder && <option value="">{placeholder}</option>}
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

function Segmented({ value, onChange, options }: {
  value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <div style={{
      display: "flex", background: "var(--surface)", borderRadius: 8,
      border: "1px solid var(--border)", padding: 2, gap: 2,
    }}>
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            style={{
              flex: 1, padding: "7px 4px", borderRadius: 6, border: "none",
              background: on ? "var(--raised)" : "transparent",
              color: on ? "var(--amber)" : "var(--text-3)",
              fontSize: 13, fontWeight: on ? 600 : 400,
              fontFamily: "var(--mono)",
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
        flex: 1, padding: "10px 8px", borderRadius: 8, fontSize: 13,
        border: `1px solid ${on ? "var(--amber)" : "var(--border)"}`,
        background: on ? "var(--amber-glow)" : "transparent",
        color: disabled ? "var(--text-3)" : on ? "var(--amber)" : "var(--text-2)",
        opacity: disabled ? 0.4 : 1,
        cursor: disabled ? "not-allowed" : "pointer",
      }}
    >{label}</button>
  );
}
