import sqlite3
import os
import json

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
    
    # Add columns if they don't exist (for existing databases)
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN ram_sensitivity REAL DEFAULT 1.0")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN supports_rt INTEGER DEFAULT 0")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE games ADD COLUMN supports_pt INTEGER DEFAULT 0")
    except:
        pass

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
    """Finds a CPU by matching the name roughly."""
    conn = get_connection()
    cursor = conn.cursor()
    # Simple LIKE search for now
    cursor.execute("SELECT * FROM cpus WHERE name LIKE ?", (f"%{search_name}%",))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "id": result[0],
            "name": result[1],
            "cores": result[2],
            "threads": result[3],
            "base_clock": result[4],
            "boost_clock": result[5],
            "architecture": result[6],
            "power_score": result[7]
        }
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
    
    # Check if current hardware is laptop
    is_current_laptop = is_laptop_hardware(current_hardware_name, is_cpu)
    
    # Search bounds: prefer upgrades (higher scores)
    low_bound = target_score + 5.0
    high_bound = target_score + 25.0
    
    query = f"SELECT name, power_score FROM {table} WHERE power_score >= ? AND power_score <= ? "
    
    # Exclude laptop hardware from recommendations
    if is_cpu:
        query += " AND name NOT LIKE '%HX%' AND name NOT LIKE '%HS%' "
        query += " AND name NOT LIKE '% H%' AND name NOT LIKE '%-H%' "
        query += " AND name NOT LIKE '% U%' AND name NOT LIKE '%-U%' "
        query += " AND name NOT LIKE '% P%' AND name NOT LIKE '%-P%' "
        query += " AND name NOT LIKE '%Mobile%' "
        query += " AND name NOT LIKE '%H ' AND name NOT LIKE '%U ' AND name NOT LIKE '%P ' "
    else:
        query += " AND name NOT LIKE '%Laptop%' AND name NOT LIKE '%Mobile%' "
    
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

if __name__ == "__main__":
    initialize_db()
    print("Database initialized successfully.")
