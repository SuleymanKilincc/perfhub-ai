/**
 * Target frame rates and search for the prototype.
 */
import { games } from "../engine/catalog";

/**
 * What counts as "enough" frames, per genre.
 *
 * A single global threshold is the thing that makes frame-rate colour coding
 * lie: 60 fps is a good result in a narrative RPG and a bad one in Counter-
 * Strike. The judgement belongs to the game, so the UI shows the number
 * against this rather than against a constant.
 *
 * Two caveats, both real:
 *
 * 1. 73 of the 180 games have no genre at all, and the taxonomy that does
 *    exist overlaps ("FPS", "Shooter" and "Action" are not distinct). Those
 *    fall back to 60. It shows in the UI — League of Legends currently gets 60
 *    when it plainly wants 144.
 * 2. Genre is a proxy for the thing that actually matters, which is whether
 *    the game is competitive multiplayer. Single-player shooters are filed
 *    under "FPS" and get 144 here, which is too strict; Doom at 90 fps is
 *    fine. A `competitive` flag would beat genre outright.
 *
 * Both are data jobs rather than model ones, and unlike power_score these are
 * documented facts rather than measurements, so they are low risk to fill in.
 */
const TARGET_BY_GENRE: Record<string, number> = {
  FPS: 144,
  Shooter: 144,
  Fighting: 120,
  Racing: 120,
  Metroidvania: 90,
  Roguelike: 90,
  Sports: 90,
  Action: 72,
  "Action Adventure": 72,
  Horror: 72,
  Stealth: 72,
  Survival: 72,
  Sandbox: 72,
  RPG: 60,
  Simulation: 60,
  Strategy: 60,
  Puzzle: 60,
};

export const DEFAULT_TARGET = 60;

export function targetFps(genre: string | null | undefined): number {
  return (genre && TARGET_BY_GENRE[genre]) || DEFAULT_TARGET;
}

/** Below this, nothing is enjoyable regardless of genre. */
export const PLAYABLE_FLOOR = 25;

export type Verdict = "over" | "at" | "under" | "bad";

export function verdict(fps: number, target: number, status: string): Verdict {
  if (status === "unplayable" || fps < PLAYABLE_FLOOR) return "bad";
  if (fps >= target * 1.5) return "over";
  if (fps >= target * 0.92) return "at";
  return "under";
}

// ─── Search ──────────────────────────────────────────────────────────────────

/** Turkish letters fold onto their ASCII neighbours so "ı" matches "i". */
function normalise(s: string): string {
  return s
    .toLocaleLowerCase("tr")
    .replace(/ı/g, "i").replace(/ş/g, "s").replace(/ğ/g, "g")
    .replace(/ü/g, "u").replace(/ö/g, "o").replace(/ç/g, "c")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

/**
 * How people actually type these. Without it "cs2" finds nothing, which is
 * the single most likely first search anyone will make.
 */
const ALIASES: Record<string, string[]> = {
  "Counter-Strike 2": ["cs2", "cs", "csgo", "counter strike"],
  "Grand Theft Auto V Enhanced": ["gta", "gta5", "gtav", "gta 5"],
  "Cyberpunk 2077": ["cp2077", "cp77", "cyber"],
  "Red Dead Redemption 2": ["rdr2", "rdr", "red dead"],
  "Microsoft Flight Simulator": ["msfs", "flight sim"],
  "The Last of Us Part I": ["tlou", "tlou1", "last of us"],
  "The Last of Us Part II": ["tlou2", "last of us 2"],
  "Baldur's Gate 3": ["bg3", "baldurs gate"],
  "Call of Duty: Warzone": ["cod", "warzone", "cod warzone"],
  "Black Myth: Wukong": ["wukong", "black myth"],
  "A Plague Tale: Requiem": ["plague tale", "requiem"],
  "Cities: Skylines II": ["cities skylines", "skylines", "cs2 cities"],
  "Kingdom Come: Deliverance 2": ["kcd2", "kingdom come"],
  "Forza Horizon 5": ["fh5", "forza"],
  "Forza Horizon 6": ["fh6", "forza"],
  "Alan Wake 2": ["aw2", "alan wake"],
  "Hogwarts Legacy": ["hogwarts", "harry potter"],
  "Resident Evil Requiem": ["re requiem", "resident evil"],
};

const INDEX = games.map((g) => {
  const extra = (ALIASES[g.name] ?? []).map(normalise);
  return { game: g, haystack: normalise(g.name), aliases: extra };
});

export type SearchHit = { id: number; score: number };

/**
 * Ranked substring search. Not fuzzy — 180 titles is small enough that exact
 * prefix and word-start matching finds everything, and fuzzy matching at this
 * size mostly produces confident nonsense.
 */
export function searchGames(query: string): SearchHit[] {
  const q = normalise(query);
  if (!q) return [];

  const hits: SearchHit[] = [];
  for (const { game, haystack, aliases } of INDEX) {
    let score = 0;
    if (haystack === q) score = 100;
    else if (aliases.includes(q)) score = 95;
    else if (haystack.startsWith(q)) score = 80;
    else if (aliases.some((a) => a.startsWith(q))) score = 70;
    else if (haystack.split(" ").some((w) => w.startsWith(q))) score = 60;
    else if (haystack.includes(q)) score = 40;
    else if (aliases.some((a) => a.includes(q))) score = 30;

    if (score) hits.push({ id: game.id, score });
  }
  return hits.sort((a, b) => b.score - a.score);
}
