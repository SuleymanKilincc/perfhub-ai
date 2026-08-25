/**
 * Node-side half of scripts/conformance_test.py.
 *
 * Reads a JSON array of cases, runs each through the TypeScript engine, and
 * writes the results back out. Deliberately dumb — all the case generation and
 * comparison lives on the Python side so there is exactly one definition of
 * what "the same answer" means.
 *
 *   node runner.mjs <cases.json> <results.json>
 */
import { readFileSync, writeFileSync } from "node:fs";
import { estimateFpsDetailed } from "../frontend/src/engine/cadence";

type Case = {
  cpu: { name: string; power_score: number };
  gpu: { name: string; power_score: number; vram: number | null };
  game: Record<string, unknown>;
  resolution: string;
  settings: string;
  upscaling: string;
  frame_gen: string;
  ram_gb: number;
  ray_tracing: boolean;
  path_tracing: boolean;
};

const cases: Case[] = JSON.parse(readFileSync(process.argv[2], "utf8"));

const results = cases.map((c) =>
  estimateFpsDetailed(
    c.cpu,
    c.gpu,
    c.game as never,
    c.resolution,
    c.settings,
    c.upscaling,
    c.frame_gen,
    c.ram_gb,
    c.ray_tracing,
    c.path_tracing,
  ),
);

writeFileSync(process.argv[3], JSON.stringify(results));
