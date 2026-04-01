"""
Script to populate database with more hardware models
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core import db_manager

def add_more_cpus():
    """Add more CPU models to database"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    new_cpus = [
        # Intel 14th Gen
        ("Intel Core i9-14900KS", 24, 32, 3.2, 6.2, "Raptor Lake Refresh", 98.0),
        ("Intel Core i7-14700K", 20, 28, 3.4, 5.6, "Raptor Lake Refresh", 88.0),
        ("Intel Core i5-14600K", 14, 20, 3.5, 5.3, "Raptor Lake Refresh", 72.0),
        
        # AMD Zen 5
        ("AMD Ryzen 9 9950X", 16, 32, 4.3, 5.7, "Zen 5", 97.0),
        ("AMD Ryzen 9 9900X", 12, 24, 4.4, 5.6, "Zen 5", 92.0),
        ("AMD Ryzen 7 9700X", 8, 16, 3.8, 5.5, "Zen 5", 82.0),
        ("AMD Ryzen 5 9600X", 6, 12, 3.9, 5.4, "Zen 5", 70.0),
        
        # AMD Zen 4 X3D
        ("AMD Ryzen 9 7950X", 16, 32, 4.5, 5.7, "Zen 4", 94.0),
        ("AMD Ryzen 7 7800X3D", 8, 16, 4.2, 5.0, "Zen 4", 89.0),
        ("AMD Ryzen 5 7600X3D", 6, 12, 4.1, 4.7, "Zen 4", 68.0),
        
        # Intel 13th Gen
        ("Intel Core i9-13900K", 24, 32, 3.0, 5.8, "Raptor Lake", 93.0),
        ("Intel Core i7-13700K", 16, 24, 3.4, 5.4, "Raptor Lake", 85.0),
        ("Intel Core i5-13600K", 14, 20, 3.5, 5.1, "Raptor Lake", 70.0),
        
        # Laptop CPUs
        ("AMD Ryzen 9 7945HX", 16, 32, 2.5, 5.4, "Zen 4", 85.0),
        ("Intel Core i9-14900HX", 24, 32, 2.2, 5.8, "Raptor Lake", 87.0),
        ("AMD Ryzen 7 7735HS", 8, 16, 3.2, 4.75, "Zen 3+", 62.0),
        ("Intel Core i7-13700H", 14, 20, 2.4, 5.0, "Raptor Lake", 68.0),
        
        # Budget/Older
        ("AMD Ryzen 7 5800X", 8, 16, 3.8, 4.7, "Zen 3", 58.0),
        ("Intel Core i5-12400F", 6, 12, 2.5, 4.4, "Alder Lake", 52.0),
        ("AMD Ryzen 5 5500", 6, 12, 3.6, 4.2, "Zen 3", 42.0),
    ]
    
    for cpu in new_cpus:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO cpus 
                (name, cores, threads, base_clock, boost_clock, architecture, power_score) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, cpu)
        except Exception as e:
            print(f"Error adding {cpu[0]}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✓ Added {len(new_cpus)} CPU models")

def add_more_gpus():
    """Add more GPU models to database"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    new_gpus = [
        # NVIDIA Blackwell (RTX 5000)
        ("NVIDIA GeForce RTX 5090", 32, 2520, 1400, "Blackwell", 105.0),
        ("NVIDIA GeForce RTX 5080", 16, 2295, 1350, "Blackwell", 95.0),
        ("NVIDIA GeForce RTX 5070 Ti", 12, 2100, 1300, "Blackwell", 88.0),
        ("NVIDIA GeForce RTX 5070", 12, 1950, 1250, "Blackwell", 82.0),
        
        # AMD RDNA 4 (RX 9000)
        ("AMD Radeon RX 9070 XT", 16, 2500, 1300, "RDNA 4", 90.0),
        ("AMD Radeon RX 9070", 16, 2300, 1250, "RDNA 4", 85.0),
        
        # NVIDIA Ada (RTX 4000)
        ("NVIDIA GeForce RTX 4080 SUPER", 16, 2295, 1400, "Ada Lovelace", 96.0),
        ("NVIDIA GeForce RTX 4070 Ti SUPER", 16, 2340, 1313, "Ada Lovelace", 88.0),
        ("NVIDIA GeForce RTX 4070 SUPER", 12, 1980, 1313, "Ada Lovelace", 80.0),
        ("NVIDIA GeForce RTX 4070", 12, 1920, 1313, "Ada Lovelace", 72.0),
        ("NVIDIA GeForce RTX 4060 Ti", 8, 2310, 1125, "Ada Lovelace", 58.0),
        
        # AMD RDNA 3
        ("AMD Radeon RX 7900 XT", 20, 1900, 1250, "RDNA 3", 88.0),
        ("AMD Radeon RX 7800 XT", 16, 2124, 1219, "RDNA 3", 78.0),
        ("AMD Radeon RX 7700 XT", 12, 2171, 1125, "RDNA 3", 68.0),
        ("AMD Radeon RX 7600 XT", 8, 2539, 1125, "RDNA 3", 52.0),
        
        # Intel Arc
        ("Intel Arc B580", 12, 2670, 1219, "Battlemage", 62.0),
        ("Intel Arc A770", 16, 2100, 1094, "Alchemist", 55.0),
        ("Intel Arc A750", 8, 2050, 1000, "Alchemist", 48.0),
        
        # Laptop GPUs
        ("NVIDIA GeForce RTX 4090 Laptop GPU", 16, 1455, 1125, "Ada Lovelace", 82.0),
        ("NVIDIA GeForce RTX 4080 Laptop GPU", 12, 1350, 1125, "Ada Lovelace", 75.0),
        ("NVIDIA GeForce RTX 4070 Laptop GPU", 8, 1230, 1000, "Ada Lovelace", 65.0),
        ("AMD Radeon RX 7900M", 16, 2090, 1125, "RDNA 3", 72.0),
        
        # Budget/Older
        ("NVIDIA GeForce RTX 3070", 8, 1500, 875, "Ampere", 62.0),
        ("NVIDIA GeForce RTX 3060 Ti", 8, 1410, 875, "Ampere", 55.0),
        ("AMD Radeon RX 6800 XT", 16, 2015, 1000, "RDNA 2", 68.0),
        ("AMD Radeon RX 6600 XT", 8, 2359, 1000, "RDNA 2", 48.0),
    ]
    
    for gpu in new_gpus:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO gpus 
                (name, vram, core_clock, memory_clock, architecture, power_score) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, gpu)
        except Exception as e:
            print(f"Error adding {gpu[0]}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✓ Added {len(new_gpus)} GPU models")

def add_more_games():
    """Add more games to database"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    new_games = [
        # AAA Games
        ("Starfield", "RPG", 1.7, 1.5, 1.0, 0.65, 0.4, 1.0, 0.6, 0.32),
        ("Alan Wake 2", "Horror", 1.9, 1.4, 1.0, 0.6, 0.35, 1.0, 0.58, 0.28),
        ("The Last of Us Part I", "Action", 1.6, 1.5, 1.0, 0.7, 0.45, 1.0, 0.62, 0.33),
        ("Spider-Man Remastered", "Action", 1.4, 1.6, 1.0, 0.75, 0.5, 1.0, 0.68, 0.38),
        ("God of War", "Action", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.35),
        
        # Competitive FPS
        ("Apex Legends", "FPS", 0.6, 1.7, 1.0, 0.85, 0.75, 1.0, 0.78, 0.55),
        ("Overwatch 2", "FPS", 0.5, 1.8, 1.0, 0.9, 0.8, 1.0, 0.8, 0.6),
        ("Rainbow Six Siege", "FPS", 0.55, 1.7, 1.0, 0.88, 0.78, 1.0, 0.75, 0.52),
        ("Fortnite", "FPS", 0.5, 1.8, 1.0, 0.9, 0.82, 1.0, 0.82, 0.62),
        
        # Racing
        ("Forza Horizon 5", "Racing", 1.2, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.42),
        ("F1 2024", "Racing", 1.3, 1.4, 1.0, 0.72, 0.52, 1.0, 0.68, 0.4),
        
        # Strategy
        ("Civilization VI", "Strategy", 0.8, 1.6, 1.0, 0.85, 0.7, 1.0, 0.75, 0.5),
        ("Total War: Warhammer III", "Strategy", 1.4, 1.5, 1.0, 0.7, 0.5, 1.0, 0.65, 0.38),
        
        # Simulation
        ("Microsoft Flight Simulator", "Simulation", 2.0, 1.3, 1.0, 0.6, 0.35, 1.0, 0.55, 0.25),
        ("Cities: Skylines II", "Simulation", 1.6, 1.4, 1.0, 0.68, 0.45, 1.0, 0.62, 0.35),
        
        # Indie/Light
        ("Hades", "Roguelike", 0.3, 2.0, 1.0, 0.95, 0.9, 1.0, 0.9, 0.8),
        ("Stardew Valley", "Simulation", 0.2, 2.2, 1.0, 1.0, 0.95, 1.0, 0.95, 0.9),
        ("Terraria", "Sandbox", 0.25, 2.1, 1.0, 0.98, 0.92, 1.0, 0.92, 0.85),
        
        # Recent AAA
        ("Elden Ring", "RPG", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.36),
        ("Resident Evil 4 Remake", "Horror", 1.6, 1.4, 1.0, 0.7, 0.45, 1.0, 0.63, 0.34),
        ("Street Fighter 6", "Fighting", 0.7, 1.7, 1.0, 0.85, 0.75, 1.0, 0.78, 0.58),
        ("Baldur's Gate 3", "RPG", 1.4, 1.5, 1.0, 0.73, 0.5, 1.0, 0.66, 0.37),
        ("Diablo IV", "RPG", 1.3, 1.5, 1.0, 0.75, 0.52, 1.0, 0.68, 0.4),
        ("Palworld", "Survival", 1.1, 1.6, 1.0, 0.78, 0.6, 1.0, 0.72, 0.45),
        ("Helldivers 2", "Shooter", 1.2, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.43),
    ]
    
    for game in new_games:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO games 
                (name, genre, difficulty_multiplier, low_scaling, med_scaling, high_scaling, 
                 ultra_scaling, res_1080p_scaling, res_1440p_scaling, res_4k_scaling) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, game)
        except Exception as e:
            print(f"Error adding {game[0]}: {e}")
    
    conn.commit()
    conn.close()
    print(f"✓ Added {len(new_games)} games")

if __name__ == "__main__":
    print("Populating database with additional hardware and games...\n")
    db_manager.initialize_db()
    add_more_cpus()
    add_more_gpus()
    add_more_games()
    print("\n✅ Database population completed!")
