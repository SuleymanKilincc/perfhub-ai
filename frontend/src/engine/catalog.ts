/**
 * The hardware and game catalogue, bundled into the app.
 *
 * 84 KB of JSON, roughly 10 KB over the wire once compressed — small enough
 * that shipping it beats asking a server for it, and it means the builder is
 * usable the moment the page paints instead of after a cold start.
 */
import type { CPUData, GPUData, GameData } from "../types";
import { estimateFpsDetailed, type Game } from "./cadence";
import raw from "./catalog.generated.json";

type CatalogGame = Game & { id: number; genre: string };

export const cpus: CPUData[] = (raw.cpus as CPUData[])
  .slice()
  .sort((a, b) => b.power_score - a.power_score);

export const gpus: GPUData[] = (raw.gpus as GPUData[])
  .slice()
  .sort((a, b) => b.power_score - a.power_score);

export const games = raw.games as CatalogGame[];

/**
 * Accuracy figures measured by scripts/export_engine_data.py at export time.
 * The interface quotes these instead of typing numbers in by hand — every
 * hand-typed figure it used to show had gone stale.
 */
export const stats = raw.stats as {
  measurements: number;
  fitted_rows: number;
  fitted_error_pct: number;
  measured_games: number;
  measured_error_pct: number;
  derived_error_pct: number;
};

export type PredictionOptions = {
  cpu: CPUData;
  gpu: GPUData;
  ramGb: number;
  resolution: string;
  preset: string;
  upscaling?: string;
  frameGen?: string;
  rayTracing?: boolean;
  pathTracing?: boolean;
};

/**
 * Every game in the catalogue, scored for one build, sorted fastest first.
 * Runs in single-digit milliseconds for all 180 titles, which is why the UI can
 * recalculate on every control change rather than behind a "Calculate" button.
 */
export function predictAll(options: PredictionOptions): GameData[] {
  const {
    cpu, gpu, ramGb, resolution, preset,
    upscaling = "Native", frameGen = "Kapalı",
    rayTracing = false, pathTracing = false,
  } = options;

  return games
    .map((game) => {
      // Pass the rows whole. Trimming them to name/score/vram is how the
      // legacy-GPU and laptop-mismatch notes came to never fire here: a field
      // the engine reads but the caller drops is a branch that silently never
      // runs.
      const r = estimateFpsDetailed(
        cpu as never,
        { ...gpu, vram: gpu.vram ?? 8 } as never,
        game, resolution, preset, upscaling, frameGen, ramGb, rayTracing, pathTracing,
      );
      return {
        id: game.id,
        name: game.name,
        genre: game.genre,
        fps: r.fps,
        fps_low: r.fps_low,
        fps_low_measured: r.fps_low_measured,
        status: r.status,
        bottleneck: r.bottleneck,
        // How hard each part works in a frame. Carried per game so the shell
        // can say something about the machine as a whole rather than only
        // about one title.
        gpu_load: r.gpu_load,
        cpu_load: r.cpu_load,
        mem_load: r.mem_load,
        vram_needed_gb: r.vram_needed_gb,
        warnings: r.warnings,
      };
    })
    .sort((a, b) => b.fps - a.fps);
}
