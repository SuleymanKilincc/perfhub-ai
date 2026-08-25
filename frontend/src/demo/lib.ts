/**
 * Frame-rate targets and search.
 */
import { games } from "../engine/catalog";

/**
 * What "enough frames" means, per game.
 *
 * This used to be derived from genre here in the UI, which was wrong twice
 * over: 73 of the games had no genre at all and silently fell back to 60, and
 * genre is only a proxy for the thing that decides it — whether the game is
 * competitive. DOOM and Counter-Strike are both "FPS" and want completely
 * different frame rates.
 *
 * Both are now settled in the database by scripts/curate_games.py, which fills
 * every genre, flags the 21 games that are actually ranked or esports play, and
 * writes `target_fps`. So this just reads it.
 */
export const DEFAULT_TARGET = 60;

export function targetFps(game: { target_fps?: number | null }): number {
  return game.target_fps || DEFAULT_TARGET;
}

/**
 * Sixty frames a second: the line below which a result is a genuine problem
 * rather than merely short of an ambition.
 *
 * This is what red is reserved for, and the reason is about how the page reads
 * rather than about the model. Judging purely against each game's own target
 * turned most of a mid-range build's library red, because a competitive
 * shooter wants 144 and missing that by a third is arithmetically "poor" — but
 * 100 fps in Marvel Rivals is not a problem, and painting it the same colour
 * as 22 fps in Cities: Skylines II wastes the only signal the page has. A page
 * that is mostly red says nothing except that the reader should feel bad.
 *
 * So red means "below 60, this will not feel good", orange means "runs fine,
 * just short of what this genre wants", and green means it got there.
 */
export const RED_BELOW = 60;

/** Below this, nothing is enjoyable regardless of genre. */
export const PLAYABLE_FLOOR = 25;

export type Verdict = "good" | "close" | "poor" | "bad";

export function verdict(fps: number, target: number, status: string): Verdict {
  if (status === "unplayable" || fps < PLAYABLE_FLOOR) return "bad";
  if (fps >= target * 0.95) return "good";
  if (fps >= RED_BELOW) return "close";
  return "poor";
}

export const VERDICT_COLOR: Record<Verdict, string> = {
  good: "var(--green)",
  close: "var(--orange)",
  poor: "var(--red)",
  bad: "var(--red)",
};

export const VERDICT_LABEL: Record<Verdict, string> = {
  good: "hedefte",
  close: "hedefin altında",
  poor: "60 fps altı",
  bad: "oynanamaz",
};

// ─── Search ──────────────────────────────────────────────────────────────────

/** Turkish letters fold onto their ASCII neighbours so "ı" matches "i". */
export function normalise(s: string): string {
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
