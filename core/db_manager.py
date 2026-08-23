import sqlite3
import os
import json
import logging

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "hardware_db.sqlite")

def get_connection():
    """Returns a connection to the SQLite database."""
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def initialize_db():
    """Creates the necessary tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create CPUs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            cores INTEGER,
            threads INTEGER,
            base_clock REAL,
            boost_clock REAL,
            architecture TEXT,
            power_score REAL NOT NULL
        )
    ''')

    # Create GPUs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gpus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            vram INTEGER,
            core_clock INTEGER,
            memory_clock INTEGER,
            architecture TEXT,
            power_score REAL NOT NULL
        )
    ''')

    # Create Games table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            genre TEXT,
            difficulty_multiplier REAL NOT NULL,
            low_scaling REAL DEFAULT 1.5,
            med_scaling REAL DEFAULT 1.0,
            high_scaling REAL DEFAULT 0.7,
            ultra_scaling REAL DEFAULT 0.5,
            res_1080p_scaling REAL DEFAULT 1.0,
            res_1440p_scaling REAL DEFAULT 0.65,
            res_4k_scaling REAL DEFAULT 0.35,
            ram_sensitivity REAL DEFAULT 1.0,
            supports_rt INTEGER DEFAULT 0,
            supports_pt INTEGER DEFAULT 0
        )
    ''')
    
    # Add columns if they don't exist (for existing databases). ALTER TABLE
    # raises sqlite3.OperationalError when the column is already there —
    # that's the expected/benign case for a re-run migration. Anything
    # else (disk full, permissions, a typo'd column type) should not be
    # swallowed silently.
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN ram_sensitivity REAL DEFAULT 1.0")
    except sqlite3.OperationalError as e:
        logging.debug(f"Skipping 'ram_sensitivity' migration (likely already applied): {e}")
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN supports_rt INTEGER DEFAULT 0")
    except sqlite3.OperationalError as e:
        logging.debug(f"Skipping 'supports_rt' migration (likely already applied): {e}")
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN supports_pt INTEGER DEFAULT 0")
    except sqlite3.OperationalError as e:
        logging.debug(f"Skipping 'supports_pt' migration (likely already applied): {e}")

    conn.commit()
    conn.close()
    
    # Optionally populate with some initial data if empty
    _populate_initial_data()

def _populate_initial_data():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM cpus")
    if cursor.fetchone()[0] == 0:
        print("Veritabanı boş, başlangıç verileri yükleniyor...")
        
        # Initial CPUs
        cpus = [
            ("Intel Core i9-14900K", 24, 32, 3.2, 6.0, "Raptor Lake Refresh", 95.0),
            ("AMD Ryzen 9 7950X3D", 16, 32, 4.2, 5.7, "Zen 4", 96.0),
            ("Intel Core i5-13400F", 10, 16, 2.5, 4.6, "Raptor Lake", 65.0),
            ("AMD Ryzen 5 5600X", 6, 12, 3.7, 4.6, "Zen 3", 55.0),
            ("Intel Core i7-10700K", 8, 16, 3.8, 5.1, "Comet Lake", 50.0),
            # Ryzen 9000 series additions
            ("AMD Ryzen 9 9950X", 16, 32, 4.3, 5.7, "Zen 5", 98.0),
            ("AMD Ryzen 9 9900X", 12, 24, 4.4, 5.6, "Zen 5", 92.0),
            ("AMD Ryzen 7 9700X", 8, 16, 3.8, 5.5, "Zen 5", 85.0),
            ("AMD Ryzen 5 9600X", 6, 12, 3.9, 5.4, "Zen 5", 78.0),
            ("AMD Ryzen 7 9800X3D", 8, 16, 4.7, 5.2, "Zen 5", 94.0),
            ("AMD Ryzen 5 9600", 6, 12, 3.9, 5.1, "Zen 5", 75.0),
        ]
        cursor.executemany("INSERT INTO cpus (name, cores, threads, base_clock, boost_clock, architecture, power_score) VALUES (?, ?, ?, ?, ?, ?, ?)", cpus)

        # Initial GPUs
        gpus = [
            ("NVIDIA GeForce RTX 4090", 24, 2235, 1313, "Ada Lovelace", 100.0),
            ("AMD Radeon RX 7900 XTX", 24, 1855, 1250, "RDNA 3", 92.0),
            ("NVIDIA GeForce RTX 3060", 12, 1320, 937, "Ampere", 45.0),
            ("AMD Radeon RX 6700 XT", 12, 2321, 1000, "RDNA 2", 55.0),
            ("NVIDIA GeForce GTX 1650", 4, 1485, 2000, "Turing", 20.0),
        ]
        cursor.executemany("INSERT INTO gpus (name, vram, core_clock, memory_clock, architecture, power_score) VALUES (?, ?, ?, ?, ?, ?)", gpus)

        # Initial Games (with ram_sensitivity + RT/PT support: 0=no, 1=yes)
        # Format: (name, genre, diff_mult, low, med, high, ultra, 1080p, 1440p, 4k, ram_sens, rt, pt)
        games = [
            ("Cyberpunk 2077", "RPG", 1.8, 1.6, 1.0, 0.7, 0.4, 1.0, 0.6, 0.3, 1.3, 1, 1),  # RT + PT
            ("Red Dead Redemption 2", "Action", 1.5, 1.4, 1.0, 0.75, 0.5, 1.0, 0.65, 0.35, 1.2, 0, 0),  # No RT/PT
            ("Valorant", "FPS", 0.4, 1.8, 1.0, 0.9, 0.8, 1.0, 0.8, 0.6, 0.7, 0, 0),  # No RT/PT
            ("CS:GO 2", "FPS", 0.5, 1.7, 1.0, 0.85, 0.75, 1.0, 0.75, 0.5, 0.7, 0, 0),  # No RT/PT
            ("Hogwarts Legacy", "RPG", 1.6, 1.4, 1.0, 0.7, 0.45, 1.0, 0.65, 0.35, 1.6, 1, 0),  # RT only
        ]
        cursor.executemany("INSERT INTO games (name, genre, difficulty_multiplier, low_scaling, med_scaling, high_scaling, ultra_scaling, res_1080p_scaling, res_1440p_scaling, res_4k_scaling, ram_sensitivity, supports_rt, supports_pt) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", games)

        conn.commit()
    conn.close()

def find_cpu(search_name):
    """Finds a CPU by matching the name robustly.
    Handles WMI suffixes like 'with Radeon Graphics', 'Processor', etc.
    """
    import re
    conn = get_connection()
    cursor = conn.cursor()

    def _row_to_dict(row):
        return {
            "id": row[0], "name": row[1], "cores": row[2],
            "threads": row[3], "base_clock": row[4], "boost_clock": row[5],
            "architecture": row[6], "power_score": row[7]
        }

    def _try(term):
        cursor.execute("SELECT * FROM cpus WHERE name LIKE ?", (f"%{term}%",))
        return cursor.fetchone()

    # 1. Direct LIKE search
    result = _try(search_name)
    if result:
        conn.close(); return _row_to_dict(result)

    # 2. Strip common WMI / marketing suffixes/prefixes and retry
    cleaned = search_name
    # (a) Strip embedded (R) and (TM) anywhere (with or without space)
    cleaned = re.sub(r"\(R\)|\(TM\)", "", cleaned, flags=re.IGNORECASE)
    # (b) Strip "Nth Gen" prefix: "12th Gen Intel" → "Intel"
    cleaned = re.sub(r"^\d+(?:st|nd|rd|th)\s+Gen\s+", "", cleaned, flags=re.IGNORECASE)
    # (c) Strip " @ 3.60GHz" frequency suffix
    cleaned = re.sub(r"\s*@\s*\d+[\.,]\d+\s*GHz.*", "", cleaned, flags=re.IGNORECASE)
    # (d) Other common suffixes
    STRIP_PATTERNS = [
        r"\s+with\s+Radeon\s+Graphics.*",   # AMD APU
        r"\s+with\s+Intel.*Graphics.*",      # Intel iGPU
        r"\s+Processor\b",
        r"\s+CPU\b",
        r"\s+\d+-Core\s+Processor.*",
        r"\s+\d+\.\d+GHz.*",
        r"\s+Gen\s+\d+.*",
        r"\s+Laptop\b",
        r"\s+Mobile\b",
    ]
    for pat in STRIP_PATTERNS:
        cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)
    # Normalize whitespace
    cleaned = " ".join(cleaned.split()).strip()

    if cleaned != search_name:
        result = _try(cleaned)
        if result:
            conn.close(); return _row_to_dict(result)

    # 3. Token-based: try progressively shorter name tokens
    tokens = cleaned.split()
    for n_tokens in range(len(tokens), 1, -1):
        term = " ".join(tokens[:n_tokens])
        result = _try(term)
        if result:
            conn.close(); return _row_to_dict(result)

    conn.close()
    return None

def find_gpu(search_name):
    """Finds a GPU by matching the name roughly."""
    conn = get_connection()
    cursor = conn.cursor()
    # Remove some common generic terms from query if needed
    search_term = search_name.replace("NVIDIA", "").replace("AMD", "").strip()
    cursor.execute("SELECT * FROM gpus WHERE name LIKE ?", (f"%{search_term}%",))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "id": result[0],
            "name": result[1],
            "vram": result[2],
            "core_clock": result[3],
            "memory_clock": result[4],
            "architecture": result[5],
            "power_score": result[6]
        }
    return None

def get_all_games():
    """Returns a list of all games and their stats."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM games")
    columns = [column[0] for column in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    conn.close()
    return results
def get_all_cpus():
    """Returns a list of all CPUs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cpus ORDER BY name")
    columns = [column[0] for column in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    conn.close()
    return results

def get_all_gpus():
    """Returns a list of all GPUs."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gpus ORDER BY name")
    columns = [column[0] for column in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    conn.close()
    return results

def is_laptop_hardware(name: str, is_cpu: bool) -> bool:
    """Checks if hardware is a laptop/mobile variant."""
    name_upper = name.upper()
    if is_cpu:
        laptop_indicators = ['HX', 'HS', 'H ', '-H', ' H', 'U ', '-U', ' U', 'P ', '-P', ' P', 'MOBILE']
        # Check for patterns like "13700H" (ends with H)
        if name_upper.endswith('H') or name_upper.endswith('U') or name_upper.endswith('P'):
            return True
        return any(indicator in name_upper for indicator in laptop_indicators)
    else:
        return 'LAPTOP' in name_upper or 'MOBILE' in name_upper


def get_recommended_upgrades(target_score: float, is_cpu: bool = True, 
                             current_hardware_name: str = "", count: int = 3) -> list:
    """
    Returns multiple upgrade recommendations with diverse options.
    
    Args:
        target_score: Target performance score
        is_cpu: True for CPU, False for GPU
        current_hardware_name: Current hardware to check if laptop
        count: Number of recommendations to return
    
    Returns:
        List of hardware names (diverse brands/models)
    """
    conn = get_connection()
    cursor = conn.cursor()
    table = "cpus" if is_cpu else "gpus"
    if table not in ("cpus", "gpus"):
        # Table names can't be passed as query parameters (the sqlite3
        # driver only parameterizes values, not identifiers), so this
        # whitelist is what actually guards the f-string below from
        # ever interpolating an untrusted table name.
        raise ValueError(f"Invalid table name: {table!r}")

    # Check if current hardware is laptop
    is_current_laptop = is_laptop_hardware(current_hardware_name, is_cpu)
    
    # Search bounds: prefer upgrades (higher scores)
    low_bound = target_score + 5.0
    high_bound = target_score + 25.0
    
    query = f"SELECT name, power_score FROM {table} WHERE power_score >= ? AND power_score <= ? "
    
    if is_cpu:
        # ── Exclude laptop CPUs ────────────────────────────────────────────────
        query += " AND name NOT LIKE '%HX%' AND name NOT LIKE '%HS%' "
        query += " AND name NOT LIKE '% H%' AND name NOT LIKE '%-H%' "
        query += " AND name NOT LIKE '% U%' AND name NOT LIKE '%-U%' "
        query += " AND name NOT LIKE '% P%' AND name NOT LIKE '%-P%' "
        query += " AND name NOT LIKE '%Mobile%' "
        query += " AND name NOT LIKE '%H ' AND name NOT LIKE '%U ' AND name NOT LIKE '%P ' "
        # ── Exclude workstation / server CPUs (gamers NEVER need these) ────────
        query += " AND name NOT LIKE '%Threadripper%' "   # AMD HEDT / workstation
        query += " AND name NOT LIKE '%Xeon%' "           # Intel server / workstation
        query += " AND name NOT LIKE '%EPYC%' "           # AMD server
        query += " AND name NOT LIKE '%Opteron%' "        # AMD server (legacy)
        query += " AND name NOT LIKE '%W-%' "             # Intel W-series workstation
        query += " AND name NOT LIKE '%W3%' "             # Intel Xeon W3xxx
        query += " AND name NOT LIKE '%W5%' "             # Intel Xeon W5xxx
        query += " AND name NOT LIKE '%W7%' "             # Intel Xeon W7xxx
        query += " AND name NOT LIKE '%W9%' "             # Intel Xeon W9xxx
        # ── Exclude Apple Silicon (macOS only, can't be used in PC gaming builds) ─
        query += " AND name NOT LIKE '%Apple%' "          # Apple M1/M2/M3/M4/M5 series
    else:
        # ── Exclude laptop GPUs ────────────────────────────────────────────────
        query += " AND name NOT LIKE '%Laptop%' AND name NOT LIKE '%Mobile%' "
        # ── Exclude professional / workstation GPUs ───────────────────────────
        query += " AND name NOT LIKE '%Quadro%' "         # NVIDIA professional series
        query += " AND name NOT LIKE '% RTX A%' "        # NVIDIA RTX A-series (A2000, A4000…)
        query += " AND name NOT LIKE '%Tesla%' "          # NVIDIA compute (T4, V100…)
        query += " AND name NOT LIKE '%A100%' "           # NVIDIA data center
        query += " AND name NOT LIKE '%H100%' "
        query += " AND name NOT LIKE '%Instinct%' "       # AMD compute (MI series)
        query += " AND name NOT LIKE '%Radeon Pro%' "     # AMD professional
        query += " AND name NOT LIKE '%FirePro%' "        # AMD legacy professional
        query += " AND name NOT LIKE '%WX%' "             # AMD Radeon Pro WX series
    
    query += " ORDER BY power_score DESC"

    
    try:
        cursor.execute(query, (low_bound, high_bound))
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return []
        
        # Diversify recommendations: mix Intel/AMD for CPUs, NVIDIA/AMD/Intel for GPUs
        recommendations = []
        brands_seen = set()
        
        for name, score in results:
            if len(recommendations) >= count:
                break
            
            # Determine brand
            name_upper = name.upper()
            if is_cpu:
                if 'INTEL' in name_upper:
                    brand = 'INTEL'
                elif 'AMD' in name_upper:
                    brand = 'AMD'
                else:
                    brand = 'OTHER'
            else:
                if 'NVIDIA' in name_upper or 'RTX' in name_upper or 'GTX' in name_upper:
                    brand = 'NVIDIA'
                elif 'AMD' in name_upper or 'RADEON' in name_upper or 'RX' in name_upper:
                    brand = 'AMD'
                elif 'INTEL' in name_upper or 'ARC' in name_upper:
                    brand = 'INTEL'
                else:
                    brand = 'OTHER'
            
            # Add if we haven't seen this brand yet, or if we need more recommendations
            if brand not in brands_seen or len(recommendations) < count:
                recommendations.append(name)
                brands_seen.add(brand)
        
        # If we still don't have enough, add more from same brands
        if len(recommendations) < count:
            for name, score in results:
                if name not in recommendations:
                    recommendations.append(name)
                    if len(recommendations) >= count:
                        break
        
        return recommendations[:count]
        
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return []

def add_new_cpus():
    """Adds new CPUs to existing database if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    new_cpus = [
        # Ryzen 9000 series
        ("AMD Ryzen 9 9950X", 16, 32, 4.3, 5.7, "Zen 5", 98.0),
        ("AMD Ryzen 9 9900X", 12, 24, 4.4, 5.6, "Zen 5", 92.0),
        ("AMD Ryzen 7 9700X", 8, 16, 3.8, 5.5, "Zen 5", 85.0),
        ("AMD Ryzen 5 9600X", 6, 12, 3.9, 5.4, "Zen 5", 78.0),
        ("AMD Ryzen 7 9800X3D", 8, 16, 4.7, 5.2, "Zen 5", 94.0),
        ("AMD Ryzen 5 9600", 6, 12, 3.9, 5.1, "Zen 5", 75.0),
        # Intel Arrow Lake Refresh (hypothetical/future)
        ("Intel Core i9-15900K", 24, 32, 3.5, 6.2, "Arrow Lake Refresh", 97.0),
        ("Intel Core i7-15700K", 20, 28, 3.3, 5.8, "Arrow Lake Refresh", 90.0),
        ("Intel Core i5-15600K", 14, 20, 3.0, 5.5, "Arrow Lake Refresh", 82.0),
        # Additional Ryzen 7000 series
        ("AMD Ryzen 9 7950X", 16, 32, 4.5, 5.7, "Zen 4", 94.0),
        ("AMD Ryzen 9 7900X", 12, 24, 4.7, 5.6, "Zen 4", 90.0),
        ("AMD Ryzen 7 7800X3D", 8, 16, 4.2, 5.0, "Zen 4", 89.0),
        ("AMD Ryzen 7 7700X", 8, 16, 4.5, 5.4, "Zen 4", 82.0),
        ("AMD Ryzen 5 7600X", 6, 12, 4.7, 5.3, "Zen 4", 72.0),
        ("AMD Ryzen 5 7600", 6, 12, 3.8, 5.1, "Zen 4", 68.0),
    ]
    
    added_count = 0
    for cpu in new_cpus:
        try:
            cursor.execute("INSERT INTO cpus (name, cores, threads, base_clock, boost_clock, architecture, power_score) VALUES (?, ?, ?, ?, ?, ?, ?)", cpu)
            added_count += 1
            print(f"Added: {cpu[0]}")
        except sqlite3.IntegrityError:
            # CPU already exists
            pass
    
    conn.commit()
    conn.close()
    print(f"Added {added_count} new CPUs to database.")

def add_new_gpus():
    """Adds new GPUs to existing database if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    new_gpus = [
        # RTX 50 series desktop
        ("NVIDIA GeForce RTX 5090", 32, 2017, 1400, "Blackwell", 105.0),
        ("NVIDIA GeForce RTX 5080", 16, 2620, 1400, "Blackwell", 95.0),
        ("NVIDIA GeForce RTX 5070 Ti", 12, 2452, 1400, "Blackwell", 88.0),
        ("NVIDIA GeForce RTX 5070", 12, 2512, 1400, "Blackwell", 82.0),
        ("NVIDIA GeForce RTX 5060 Ti", 8, 2338, 1400, "Blackwell", 72.0),
        ("NVIDIA GeForce RTX 5060", 8, 2460, 1400, "Blackwell", 65.0),
        ("NVIDIA GeForce RTX 5050", 6, 2507, 1400, "Blackwell", 55.0),
        # RX 9000 series desktop
        ("AMD Radeon RX 9070 XT", 16, 2970, 2000, "RDNA 4", 90.0),
        ("AMD Radeon RX 9070", 16, 2502, 2000, "RDNA 4", 85.0),
        ("AMD Radeon RX 9060 XT", 12, 2615, 2000, "RDNA 4", 75.0),
        ("AMD Radeon RX 9060", 8, 2460, 2000, "RDNA 4", 68.0),
        # Intel Arc Battlemage
        ("Intel Arc B580", 12, 2670, 1900, "Battlemage", 62.0),
        ("Intel Arc B570", 10, 2500, 1900, "Battlemage", 55.0),
        # Additional RTX 40 series variants
        ("NVIDIA GeForce RTX 4090 D", 24, 2280, 1313, "Ada Lovelace", 98.0),
        ("NVIDIA GeForce RTX 4080 16GB", 16, 2505, 1400, "Ada Lovelace", 94.0),
        ("NVIDIA GeForce RTX 4070 Ti 16GB", 16, 2610, 1313, "Ada Lovelace", 86.0),
        # Additional RX 7000 series
        ("AMD Radeon RX 7900 GRE", 16, 2245, 1800, "RDNA 3", 82.0),
        ("AMD Radeon RX 7750 XT", 8, 2456, 1800, "RDNA 3", 58.0),
    ]
    
    added_count = 0
    for gpu in new_gpus:
        try:
            cursor.execute("INSERT INTO gpus (name, vram, core_clock, memory_clock, architecture, power_score) VALUES (?, ?, ?, ?, ?, ?)", gpu)
            added_count += 1
            print(f"Added: {gpu[0]}")
        except sqlite3.IntegrityError:
            # GPU already exists
            pass
    
    conn.commit()
    conn.close()
    print(f"Added {added_count} new GPUs to database.")

def fix_power_scores():
    """
    Removed. This used to overwrite power_score with hand-written values keyed
    to Cinebench R23 multi-core — the metric that put a Core Ultra 9 285K above
    a Ryzen 7 9800X3D, when the engine only ever asks these scores about games.
    Both ladders now come from published gaming hierarchies via
    scripts/calibrate_cpu_scores.py and scripts/calibrate_gpu_scores.py, so
    running this would undo them.
    """
    raise RuntimeError(
        "fix_power_scores() kaldirildi. Donanim puanlari icin "
        "scripts/calibrate_cpu_scores.py ve scripts/calibrate_gpu_scores.py "
        "kullanin.")


def add_new_games():
    """Adds new games with calibrated difficulty multipliers based on real benchmarks."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Games calibrated against Digital Foundry / Hardware Unboxed 2024 benchmarks
    # Format: (name, genre, diff_mult, low, med, high, ultra, 1080p, 1440p, 4k, ram_sens, rt, pt, dlss, fsr, xess)
    # diff_mult: Higher = more demanding (RTX 4090 gets lower FPS)
    # ram_sens: Higher = more RAM sensitive
    new_games = [
        # AAA Open World (Very Demanding)
        ("Alan Wake 2", "Horror", 2.2, 1.5, 1.0, 0.65, 0.4, 1.0, 0.55, 0.25, 1.8, 1, 1, 1, 1, 0),
        ("Starfield", "RPG", 1.9, 1.5, 1.0, 0.7, 0.45, 1.0, 0.6, 0.3, 1.5, 1, 0, 1, 1, 0),
        ("The Witcher 3: Wild Hunt", "RPG", 1.2, 1.5, 1.0, 0.8, 0.6, 1.0, 0.75, 0.45, 1.0, 0, 0, 0, 1, 0),
        
        # Competitive FPS (Light)
        ("Fortnite", "Battle Royale", 0.6, 1.7, 1.0, 0.9, 0.8, 1.0, 0.85, 0.65, 0.8, 0, 0, 1, 1, 1),
        ("Apex Legends", "Battle Royale", 0.7, 1.6, 1.0, 0.85, 0.75, 1.0, 0.8, 0.6, 0.9, 0, 0, 1, 1, 0),
        ("Overwatch 2", "FPS", 0.5, 1.8, 1.0, 0.9, 0.85, 1.0, 0.9, 0.7, 0.7, 0, 0, 1, 1, 0),
        
        # Modern AAA (Demanding)
        ("Elden Ring", "Action RPG", 1.4, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.4, 1.1, 0, 0, 0, 1, 0),
        ("God of War Ragnarok", "Action Adventure", 1.5, 1.4, 1.0, 0.75, 0.5, 1.0, 0.65, 0.35, 1.2, 0, 0, 0, 1, 0),
        ("Spider-Man 2", "Action Adventure", 1.6, 1.4, 1.0, 0.7, 0.45, 1.0, 0.65, 0.35, 1.3, 1, 0, 1, 1, 0),
        
        # Esports (Very Light)
        ("League of Legends", "MOBA", 0.3, 2.0, 1.0, 0.95, 0.9, 1.0, 0.95, 0.8, 0.5, 0, 0, 0, 0, 0),
        ("Dota 2", "MOBA", 0.4, 1.8, 1.0, 0.9, 0.85, 1.0, 0.85, 0.65, 0.6, 0, 0, 0, 0, 0),
        
        # RT Heavy Games
        ("Portal with RTX", "Puzzle", 1.7, 1.4, 1.0, 0.7, 0.45, 1.0, 0.65, 0.35, 1.2, 1, 0, 1, 0, 0),
        ("Quake II RTX", "FPS", 1.3, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.4, 1.0, 1, 0, 1, 0, 0),
        
        # Popular Recent Titles
        ("Baldur's Gate 3", "RPG", 1.3, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.4, 1.1, 0, 0, 0, 1, 0),
        ("Forza Horizon 5", "Racing", 1.1, 1.6, 1.0, 0.8, 0.65, 1.0, 0.8, 0.5, 1.0, 0, 0, 1, 1, 0),
        
        # CPU Heavy Games
        ("Microsoft Flight Simulator 2020", "Simulation", 1.7, 1.4, 1.0, 0.7, 0.45, 1.0, 0.65, 0.35, 1.4, 0, 0, 1, 1, 0),
        ("Cities: Skylines II", "Simulation", 1.5, 1.4, 1.0, 0.75, 0.5, 1.0, 0.65, 0.35, 1.3, 0, 0, 0, 0, 0),
        
        # VRAM Heavy Games
        ("The Last of Us Part I", "Action Adventure", 1.8, 1.4, 1.0, 0.7, 0.4, 1.0, 0.6, 0.3, 1.6, 1, 0, 1, 1, 0),
        ("Resident Evil 4 Remake", "Horror", 1.4, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.4, 1.2, 1, 0, 1, 1, 0),
    ]
    
    # Check if games table has dlss, fsr, xess columns. As above,
    # sqlite3.OperationalError here means "column already exists" on a
    # re-run — anything else should surface instead of being swallowed.
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN supports_dlss INTEGER DEFAULT 1")
    except sqlite3.OperationalError as e:
        logging.debug(f"Skipping 'supports_dlss' migration (likely already applied): {e}")
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN supports_fsr INTEGER DEFAULT 1")
    except sqlite3.OperationalError as e:
        logging.debug(f"Skipping 'supports_fsr' migration (likely already applied): {e}")
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN supports_xess INTEGER DEFAULT 0")
    except sqlite3.OperationalError as e:
        logging.debug(f"Skipping 'supports_xess' migration (likely already applied): {e}")
    
    added_count = 0
    for game in new_games:
        try:
            cursor.execute("""
                INSERT INTO games (name, genre, difficulty_multiplier, low_scaling, med_scaling, high_scaling, ultra_scaling, 
                res_1080p_scaling, res_1440p_scaling, res_4k_scaling, ram_sensitivity, supports_rt, supports_pt, supports_dlss, supports_fsr, supports_xess)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, game)
            added_count += 1
            print(f"Added game: {game[0]}")
        except sqlite3.IntegrityError:
            # Game already exists
            pass
    
    conn.commit()
    conn.close()
    print(f"Added {added_count} new games to database.")

def remove_duplicate_gpus():
    """Removes duplicate GPU entries (same model with different VRAM suffixes)."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # List of duplicates to remove (keep the base model, remove VRAM-specific variants)
    duplicates_to_remove = [
        # Keep base model, remove VRAM-specific
        "NVIDIA GeForce RTX 4060 Ti 16GB",  # Keep "NVIDIA GeForce RTX 4060 Ti"
        "NVIDIA GeForce RTX 4060 Ti 8GB",    # Keep "NVIDIA GeForce RTX 4060 Ti"
        "NVIDIA GeForce RTX 4070 12GB",      # Keep "NVIDIA GeForce RTX 4070"
        "NVIDIA GeForce RTX 4070 Ti 16GB",   # Keep "NVIDIA GeForce RTX 4070 Ti"
        "NVIDIA GeForce RTX 4080 16GB",      # Keep "NVIDIA GeForce RTX 4080"
        "NVIDIA GeForce RTX 5060 Ti 8GB",    # Keep "NVIDIA GeForce RTX 5060 Ti"
        "NVIDIA GeForce RTX 5060 Ti 16GB",   # Keep "NVIDIA GeForce RTX 5060 Ti"
    ]
    
    removed_count = 0
    for gpu_name in duplicates_to_remove:
        cursor.execute("DELETE FROM gpus WHERE name = ?", (gpu_name,))
        if cursor.rowcount > 0:
            removed_count += 1
            print(f"Removed duplicate: {gpu_name}")
    
    conn.commit()
    conn.close()
    print(f"Removed {removed_count} duplicate GPUs.")

if __name__ == "__main__":
    initialize_db()
    print("Database initialized successfully.")
    
    # Add new hardware
    print("\nAdding new CPUs...")
    add_new_cpus()
    print("\nAdding new GPUs...")
    add_new_gpus()
    
    # Add new games
    print("\nAdding new games...")
    add_new_games()
