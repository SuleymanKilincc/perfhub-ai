"""
Extends the games table with the per-game data the rebuilt FPS engine needs,
deriving initial values from what the old model already stored.

Why this is needed
------------------
The old engine described a game with a single `difficulty_multiplier` plus
hand-tuned resolution/quality scalings. That shape cannot express:

  * whether a game is CPU-bound or GPU-bound (one global CPU/GPU weight was
    applied to every game, so Valorant and Cyberpunk went through identical
    math),
  * how much VRAM a game actually wants (the old code used
    `difficulty_multiplier / 5.0` as a stand-in, which conflates "heavy to
    render" with "hungry for memory" — MSFS scored 0.40 "VRAM demand" while
    The Last of Us scored 1.00, the opposite of reality),
  * how much system RAM it needs, independently of that.

New columns
-----------
    gpu_cost      GPU frame-time cost at 1080p/High (relative units)
    cpu_cost      CPU frame-time cost at High (resolution-independent)
    vram_base_gb  VRAM working set at 1080p/High
    ram_base_gb   System RAM working set at High
    tier_min      Lowest preset the game actually offers
    tier_max      Highest preset the game actually offers

Derivation
----------
1. Resolution anchors are normalised first. The existing rows are anchored
   inconsistently — Cyberpunk stores 1080p=1.25/1440p=1.00 (anchored at
   1440p) while MSFS stores 1080p=1.00/1440p=0.55 (anchored at 1080p), which
   means their `difficulty_multiplier` values were never on the same scale.
   Everything is rebased so 1080p = 1.00.

2. The CPU/GPU split is solved from the observed 4K falloff. A purely
   GPU-bound game loses ~4x going 1080p -> 4K (pixel count); a purely
   CPU-bound game loses almost nothing. Inverting the frame-time blend
   recovers the ratio of CPU to GPU cost per game.

3. That result is blended with a genre prior, because some stored scalings
   are demonstrably wrong (MSFS's curve claims perfect GPU scaling, yet it
   is one of the most CPU-limited games there is). Games where the two
   disagree sharply are printed for manual review.

Every derived number here is a *starting point* meant to be corrected by the
benchmark calibration pass — not a claim of measured truth.

Idempotent. Run from the repo root:  python scripts/migrate_game_profiles.py
"""
import os
import sqlite3
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import db_manager

# Exponent of the frame-time blend used by the engine (see scoring_engine).
# Must match balance_config.BOTTLENECK_BLEND_K.
BLEND_K = 4.0

# How CPU-limited a genre tends to be, expressed as the expected ratio of CPU
# frame time to GPU frame time at 1080p/High. >1 means CPU-limited first.
GENRE_CPU_RATIO = {
    "Strategy": 1.9,
    "Simulation": 1.8,
    "Sandbox": 1.6,
    "MMO": 1.7,
    "FPS": 1.4,          # competitive shooters run at high fps, CPU walls early
    "Shooter": 1.2,
    "Racing": 0.85,
    "Fighting": 0.85,
    "Roguelike": 1.0,
    "Metroidvania": 0.95,
    "Survival": 1.2,
    # Heavy single-player AAA is GPU-limited at 1080p on any realistic
    # system, so these sit below 1.0.
    "RPG": 0.75,
    "Action": 0.70,
    "Action Adventure": 0.70,
    "Horror": 0.65,
    "Puzzle": 0.75,
}
DEFAULT_CPU_RATIO = 1.0

# Genres whose VRAM footprint runs above/below what raw render cost implies.
GENRE_VRAM_BIAS = {
    "Simulation": 1.35,
    "Sandbox": 1.15,
    "Action Adventure": 1.15,
    "Horror": 1.10,
    "RPG": 1.05,
    "FPS": 0.80,
    "Fighting": 0.75,
    "Puzzle": 0.70,
    "Metroidvania": 0.60,
    "Roguelike": 0.65,
}

# Games whose preset ladder is wider than the default Low..Ultra. The engine
# clamps a requested preset to what the game actually offers, so a game only
# responds to "Extreme" or "Very Low" once it is listed here.
#
# This list is deliberately short and only covers titles whose preset names
# are well known. It is the hook for the per-game research pass — extend it
# rather than widening the default for everything.
CUSTOM_TIERS = {
    # Forza Horizon exposes an Extreme preset above Ultra.
    "Forza Horizon 5": ("Low", "Extreme"),
    "Forza Horizon 6": ("Low", "Extreme"),
    # Competitive shooters ship aggressive bottom-end presets so the game runs
    # on anything, and players actually use them for frame rate.
    "Valorant": ("Very Low", "High"),
    "CS:GO 2": ("Very Low", "Ultra"),
    "Overwatch 2": ("Very Low", "Ultra"),
    "Fortnite": ("Very Low", "Extreme"),
    "Apex Legends": ("Very Low", "Ultra"),
    "Rainbow Six Siege": ("Very Low", "Ultra"),
    "PUBG": ("Very Low", "Ultra"),
    "Call of Duty: Warzone": ("Very Low", "Extreme"),
    # Simulators with very wide scalability.
    "Microsoft Flight Simulator": ("Very Low", "Ultra"),
    "Cities: Skylines II": ("Very Low", "Ultra"),
}

NEW_COLUMNS = [
    ("gpu_cost", "REAL"),
    ("cpu_cost", "REAL"),
    ("vram_base_gb", "REAL"),
    ("ram_base_gb", "REAL"),
    ("tier_min", "TEXT"),
    ("tier_max", "TEXT"),
]


def _add_columns(cursor):
    """Add the new columns if they aren't there yet."""
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(games)")}
    for name, coltype in NEW_COLUMNS:
        if name not in existing:
            cursor.execute(f"ALTER TABLE games ADD COLUMN {name} {coltype}")
            print(f"  + kolon eklendi: {name}")


def _solve_cpu_gpu_ratio(fps_ratio_4k):
    """
    Recover (cpu frame time / gpu frame time) at 1080p from how much fps the
    game loses going 1080p -> 4K.

    The engine blends the two limits as ft = (ft_cpu^k + ft_gpu^k)^(1/k), and
    4K multiplies only the GPU term (4x the pixels). Writing t = ft_cpu/ft_gpu
    and solving that blend for the observed ratio gives t directly.

    fps_ratio_4k near 0.25 -> purely GPU-bound (t -> 0)
    fps_ratio_4k near 1.00 -> purely CPU-bound (t -> large)
    """
    r = max(0.26, min(0.97, fps_ratio_4k))
    pixel_scale = 4.0 ** BLEND_K          # GPU term grows 4x in frame time
    rk = r ** BLEND_K
    # (t^k + 1) / (t^k + pixel_scale) = r^k   ->  solve for t^k
    denom = 1.0 - rk
    if denom <= 1e-9:
        return 4.0
    t_k = (rk * pixel_scale - 1.0) / denom
    if t_k <= 0:
        return 0.05
    return t_k ** (1.0 / BLEND_K)


def main():
    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    _add_columns(cursor)
    conn.commit()

    games = [dict(r) for r in cursor.execute("SELECT * FROM games")]
    disagreements = []

    for g in games:
        res_1080 = g["res_1080p_scaling"] or 1.0
        res_4k = g["res_4k_scaling"] or 0.25

        # 1. Rebase every game so 1080p == 1.00.
        norm_4k = res_4k / res_1080
        # Total render cost at 1080p/High, on a single consistent scale.
        total_cost = (g["difficulty_multiplier"] or 1.0) / res_1080

        # 2. Split that cost into CPU and GPU frame time.
        ratio_from_data = _solve_cpu_gpu_ratio(norm_4k)

        # 3. Blend with the genre prior. The prior carries most of the weight
        #    on purpose: the stored resolution curves were hand-tuned rather
        #    than measured, and taking them at face value made *every* game
        #    come out CPU-bound — including Cyberpunk and The Last of Us,
        #    which are GPU-limited at 1080p on any realistic system. The
        #    stored curve is kept only as a nudge, and the whole split is
        #    meant to be replaced by benchmark calibration later.
        prior = GENRE_CPU_RATIO.get(g["genre"], DEFAULT_CPU_RATIO)
        looks_synthetic = norm_4k <= 0.27
        weight_prior = 0.85 if looks_synthetic else 0.70
        ratio = ratio_from_data * (1 - weight_prior) + prior * weight_prior

        if abs(ratio_from_data - prior) > 0.9:
            disagreements.append((g["name"], g["genre"], round(ratio_from_data, 2),
                                  prior, round(ratio, 2)))

        # ft_total = (ft_cpu^k + ft_gpu^k)^(1/k), with ft_cpu = ratio * ft_gpu.
        # Keep the blended total equal to total_cost so existing balance holds.
        blend = (ratio ** BLEND_K + 1.0) ** (1.0 / BLEND_K)
        gpu_cost = total_cost / blend
        cpu_cost = gpu_cost * ratio

        # VRAM: driven by render cost, then corrected by genre. An esports
        # title and an open-world RPG with the same frame cost do not use
        # remotely the same amount of memory.
        # Calibrated against real 1080p/High working sets: Cyberpunk sits near
        # 7 GB, Hogwarts Legacy near 8, CS2 near 2.5. The first attempt used a
        # much flatter slope and landed ~40% low on every heavy title, which
        # made VRAM overflow almost impossible to trigger.
        vram_bias = GENRE_VRAM_BIAS.get(g["genre"], 1.0)
        vram_base = (1.8 + 1.90 * total_cost) * vram_bias
        vram_base = max(1.5, min(16.0, vram_base))

        # System RAM: the old ram_sensitivity was a pure output multiplier;
        # reuse it as the signal it really was — how memory-hungry the game is.
        ram_sens = g["ram_sensitivity"] or 1.0
        ram_base = max(4.0, min(20.0, 5.5 * ram_sens + 0.35 * total_cost))

        tier_min, tier_max = CUSTOM_TIERS.get(g["name"], ("Low", "Ultra"))

        cursor.execute(
            "UPDATE games SET gpu_cost=?, cpu_cost=?, vram_base_gb=?, "
            "ram_base_gb=?, tier_min=?, tier_max=? WHERE id=?",
            (round(gpu_cost, 4), round(cpu_cost, 4), round(vram_base, 2),
             round(ram_base, 2), tier_min, tier_max, g["id"]),
        )

    conn.commit()

    print(f"\n  {len(games)} oyun profillendirildi.")

    # "Bound" here means: which limit binds first at 1080p on the reference
    # system (a score-100 CPU and a score-100 GPU). The same game flips to
    # GPU-bound on weaker graphics hardware — that is the whole point of
    # tracking the two costs separately.
    rows = list(cursor.execute("SELECT cpu_cost, gpu_cost FROM games"))
    cpu_bound = sum(1 for r in rows if r["cpu_cost"] > r["gpu_cost"])
    print(f"  Referans sistemde: {cpu_bound} CPU-bound, "
          f"{len(rows) - cpu_bound} GPU-bound")

    print("\n  Ornek profiller (referans sistemde hangi limit once dolar):")
    for name in ["Cyberpunk 2077", "Valorant", "Microsoft Flight Simulator",
                 "Hogwarts Legacy", "The Last of Us Part I", "CS:GO 2"]:
        r = cursor.execute(
            "SELECT name, genre, gpu_cost, cpu_cost, vram_base_gb, ram_base_gb "
            "FROM games WHERE name=?", (name,)).fetchone()
        if r:
            bound = "CPU-bound" if r["cpu_cost"] > r["gpu_cost"] else "GPU-bound"
            print(f"    {r['name']:32s} gpu={r['gpu_cost']:5.2f} cpu={r['cpu_cost']:5.2f} "
                  f"vram={r['vram_base_gb']:4.1f}GB ram={r['ram_base_gb']:4.1f}GB  {bound}")

    if disagreements:
        print(f"\n  Elle gozden gecirilmesi onerilen {len(disagreements)} oyun "
              f"(kayitli egri ile tur beklentisi celisiyor):")
        for name, genre, from_data, prior, final in disagreements[:12]:
            print(f"    {name:32s} [{genre}] veri={from_data} tur={prior} -> {final}")
        if len(disagreements) > 12:
            print(f"    ... ve {len(disagreements) - 12} tane daha")

    conn.close()


if __name__ == "__main__":
    main()
