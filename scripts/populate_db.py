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
        ("Intel Core i9-14900K", 24, 32, 3.2, 6.0, "Raptor Lake Refresh", 95.0),
        ("Intel Core i7-14700K", 20, 28, 3.4, 5.6, "Raptor Lake Refresh", 88.0),
        ("Intel Core i7-14700", 20, 28, 2.1, 5.4, "Raptor Lake Refresh", 82.0),
        ("Intel Core i5-14600K", 14, 20, 3.5, 5.3, "Raptor Lake Refresh", 72.0),
        ("Intel Core i5-14600", 14, 20, 2.7, 5.2, "Raptor Lake Refresh", 68.0),
        ("Intel Core i5-14500", 14, 20, 2.6, 5.0, "Raptor Lake Refresh", 64.0),
        ("Intel Core i5-14400", 10, 16, 2.5, 4.7, "Raptor Lake Refresh", 58.0),
        ("Intel Core i3-14100", 4, 8, 3.5, 4.7, "Raptor Lake Refresh", 42.0),
        
        # AMD Zen 5
        ("AMD Ryzen 9 9950X", 16, 32, 4.3, 5.7, "Zen 5", 97.0),
        ("AMD Ryzen 9 9900X", 12, 24, 4.4, 5.6, "Zen 5", 92.0),
        ("AMD Ryzen 7 9700X", 8, 16, 3.8, 5.5, "Zen 5", 82.0),
        ("AMD Ryzen 5 9600X", 6, 12, 3.9, 5.4, "Zen 5", 70.0),
        
        # AMD Zen 4 X3D
        ("AMD Ryzen 9 7950X3D", 16, 32, 4.2, 5.7, "Zen 4", 96.0),
        ("AMD Ryzen 9 7950X", 16, 32, 4.5, 5.7, "Zen 4", 94.0),
        ("AMD Ryzen 9 7900X3D", 12, 24, 4.4, 5.6, "Zen 4", 91.0),
        ("AMD Ryzen 9 7900X", 12, 24, 4.7, 5.4, "Zen 4", 89.0),
        ("AMD Ryzen 7 7800X3D", 8, 16, 4.2, 5.0, "Zen 4", 89.0),
        ("AMD Ryzen 7 7700X", 8, 16, 4.5, 5.4, "Zen 4", 80.0),
        ("AMD Ryzen 7 7700", 8, 16, 3.8, 5.3, "Zen 4", 76.0),
        ("AMD Ryzen 5 7600X3D", 6, 12, 4.1, 4.7, "Zen 4", 68.0),
        ("AMD Ryzen 5 7600X", 6, 12, 4.7, 5.3, "Zen 4", 66.0),
        ("AMD Ryzen 5 7600", 6, 12, 3.8, 5.1, "Zen 4", 62.0),
        ("AMD Ryzen 5 7500F", 6, 12, 3.7, 5.0, "Zen 4", 58.0),
        
        # Intel 13th Gen
        ("Intel Core i9-13900KS", 24, 32, 3.2, 6.0, "Raptor Lake", 96.0),
        ("Intel Core i9-13900K", 24, 32, 3.0, 5.8, "Raptor Lake", 93.0),
        ("Intel Core i9-13900", 24, 32, 2.0, 5.6, "Raptor Lake", 88.0),
        ("Intel Core i7-13700K", 16, 24, 3.4, 5.4, "Raptor Lake", 85.0),
        ("Intel Core i7-13700", 16, 24, 2.1, 5.2, "Raptor Lake", 80.0),
        ("Intel Core i5-13600K", 14, 20, 3.5, 5.1, "Raptor Lake", 70.0),
        ("Intel Core i5-13600", 14, 20, 2.7, 5.0, "Raptor Lake", 66.0),
        ("Intel Core i5-13500", 14, 20, 2.5, 4.8, "Raptor Lake", 62.0),
        ("Intel Core i5-13400", 10, 16, 2.5, 4.6, "Raptor Lake", 56.0),
        ("Intel Core i3-13100", 4, 8, 3.4, 4.5, "Raptor Lake", 40.0),
        
        # Intel 12th Gen
        ("Intel Core i9-12900KS", 16, 24, 3.4, 5.5, "Alder Lake", 90.0),
        ("Intel Core i9-12900K", 16, 24, 3.2, 5.2, "Alder Lake", 87.0),
        ("Intel Core i7-12700K", 12, 20, 3.6, 5.0, "Alder Lake", 78.0),
        ("Intel Core i7-12700", 12, 20, 2.1, 4.9, "Alder Lake", 74.0),
        ("Intel Core i5-12600K", 10, 16, 3.7, 4.9, "Alder Lake", 66.0),
        ("Intel Core i5-12600", 6, 12, 3.3, 4.8, "Alder Lake", 60.0),
        ("Intel Core i5-12400F", 6, 12, 2.5, 4.4, "Alder Lake", 52.0),
        ("Intel Core i5-12400", 6, 12, 2.5, 4.4, "Alder Lake", 52.0),
        ("Intel Core i3-12100F", 4, 8, 3.3, 4.3, "Alder Lake", 38.0),
        
        # AMD Zen 3
        ("AMD Ryzen 9 5950X", 16, 32, 3.4, 4.9, "Zen 3", 82.0),
        ("AMD Ryzen 9 5900X", 12, 24, 3.7, 4.8, "Zen 3", 76.0),
        ("AMD Ryzen 7 5800X3D", 8, 16, 3.4, 4.5, "Zen 3", 74.0),
        ("AMD Ryzen 7 5800X", 8, 16, 3.8, 4.7, "Zen 3", 68.0),
        ("AMD Ryzen 7 5700X", 8, 16, 3.4, 4.6, "Zen 3", 64.0),
        ("AMD Ryzen 5 5600X", 6, 12, 3.7, 4.6, "Zen 3", 58.0),
        ("AMD Ryzen 5 5600", 6, 12, 3.5, 4.4, "Zen 3", 54.0),
        ("AMD Ryzen 5 5500", 6, 12, 3.6, 4.2, "Zen 3", 48.0),
        ("AMD Ryzen 3 5300G", 4, 8, 4.0, 4.2, "Zen 3", 42.0),
        
        # Intel 11th Gen
        ("Intel Core i9-11900K", 8, 16, 3.5, 5.3, "Rocket Lake", 72.0),
        ("Intel Core i7-11700K", 8, 16, 3.6, 5.0, "Rocket Lake", 66.0),
        ("Intel Core i5-11600K", 6, 12, 3.9, 4.9, "Rocket Lake", 58.0),
        ("Intel Core i5-11400", 6, 12, 2.6, 4.4, "Rocket Lake", 50.0),
        
        # Intel 10th Gen
        ("Intel Core i9-10900K", 10, 20, 3.7, 5.3, "Comet Lake", 70.0),
        ("Intel Core i7-10700K", 8, 16, 3.8, 5.1, "Comet Lake", 62.0),
        ("Intel Core i5-10600K", 6, 12, 4.1, 4.8, "Comet Lake", 54.0),
        ("Intel Core i5-10400F", 6, 12, 2.9, 4.3, "Comet Lake", 48.0),
        
        # AMD Zen 2
        ("AMD Ryzen 9 3950X", 16, 32, 3.5, 4.7, "Zen 2", 70.0),
        ("AMD Ryzen 9 3900X", 12, 24, 3.8, 4.6, "Zen 2", 64.0),
        ("AMD Ryzen 7 3800X", 8, 16, 3.9, 4.5, "Zen 2", 56.0),
        ("AMD Ryzen 7 3700X", 8, 16, 3.6, 4.4, "Zen 2", 54.0),
        ("AMD Ryzen 5 3600X", 6, 12, 3.8, 4.4, "Zen 2", 48.0),
        ("AMD Ryzen 5 3600", 6, 12, 3.6, 4.2, "Zen 2", 46.0),
        
        # Laptop CPUs - Intel
        ("Intel Core i9-14900HX", 24, 32, 2.2, 5.8, "Raptor Lake", 87.0),
        ("Intel Core i9-13900HX", 24, 32, 2.2, 5.4, "Raptor Lake", 84.0),
        ("Intel Core i9-12900HX", 16, 24, 2.3, 5.0, "Alder Lake", 76.0),
        ("Intel Core i7-14700HX", 20, 28, 2.1, 5.5, "Raptor Lake", 80.0),
        ("Intel Core i7-13700H", 14, 20, 2.4, 5.0, "Raptor Lake", 68.0),
        ("Intel Core i7-12700H", 14, 20, 2.3, 4.7, "Alder Lake", 62.0),
        ("Intel Core i7-1365U", 10, 12, 1.3, 5.2, "Raptor Lake", 52.0),
        ("Intel Core i5-13500H", 12, 16, 2.6, 4.7, "Raptor Lake", 58.0),
        ("Intel Core i5-12500H", 12, 16, 2.5, 4.5, "Alder Lake", 54.0),
        ("Intel Core i5-1335U", 10, 12, 1.3, 4.6, "Raptor Lake", 46.0),
        
        # Laptop CPUs - AMD
        ("AMD Ryzen 9 7945HX", 16, 32, 2.5, 5.4, "Zen 4", 85.0),
        ("AMD Ryzen 9 7940HS", 8, 16, 4.0, 5.2, "Zen 4", 72.0),
        ("AMD Ryzen 9 6900HX", 8, 16, 3.3, 4.9, "Zen 3+", 66.0),
        ("AMD Ryzen 7 7840HS", 8, 16, 3.8, 5.1, "Zen 4", 68.0),
        ("AMD Ryzen 7 7735HS", 8, 16, 3.2, 4.75, "Zen 3+", 62.0),
        ("AMD Ryzen 7 6800H", 8, 16, 3.2, 4.7, "Zen 3+", 60.0),
        ("AMD Ryzen 5 7640HS", 6, 12, 4.3, 5.0, "Zen 4", 58.0),
        ("AMD Ryzen 5 7535HS", 6, 12, 3.3, 4.55, "Zen 3+", 52.0),
        ("AMD Ryzen 5 6600H", 6, 12, 3.3, 4.5, "Zen 3+", 50.0),
        
        # Apple Silicon
        ("Apple M5 Max", 16, 16, 4.5, 4.5, "Apple Silicon", 105.0),
        ("Apple M5 Pro", 14, 14, 4.3, 4.3, "Apple Silicon", 95.0),
        ("Apple M5", 10, 10, 4.0, 4.0, "Apple Silicon", 85.0),
        ("Apple M4 Max", 16, 16, 4.4, 4.4, "Apple Silicon", 100.0),
        ("Apple M4 Pro", 14, 14, 4.2, 4.2, "Apple Silicon", 90.0),
        ("Apple M4", 10, 10, 3.9, 3.9, "Apple Silicon", 80.0),
        ("Apple M3 Max", 16, 16, 4.05, 4.05, "Apple Silicon", 92.0),
        ("Apple M3 Pro", 12, 12, 4.0, 4.0, "Apple Silicon", 82.0),
        ("Apple M3", 8, 8, 3.7, 3.7, "Apple Silicon", 72.0),
        ("Apple M2 Ultra", 24, 24, 3.5, 3.5, "Apple Silicon", 98.0),
        ("Apple M2 Max", 12, 12, 3.7, 3.7, "Apple Silicon", 85.0),
        ("Apple M2 Pro", 12, 12, 3.5, 3.5, "Apple Silicon", 75.0),
        ("Apple M2", 8, 8, 3.5, 3.5, "Apple Silicon", 65.0),
        ("Apple M1 Ultra", 20, 20, 3.2, 3.2, "Apple Silicon", 88.0),
        ("Apple M1 Max", 10, 10, 3.2, 3.2, "Apple Silicon", 78.0),
        ("Apple M1 Pro", 10, 10, 3.2, 3.2, "Apple Silicon", 68.0),
        ("Apple M1", 8, 8, 3.2, 3.2, "Apple Silicon", 58.0),
        
        # Workstation CPUs
        ("AMD Ryzen Threadripper PRO 7995WX", 96, 192, 2.5, 5.1, "Zen 4", 110.0),
        ("AMD Ryzen Threadripper PRO 7985WX", 64, 128, 3.2, 5.1, "Zen 4", 108.0),
        ("AMD Ryzen Threadripper PRO 7975WX", 32, 64, 4.0, 5.3, "Zen 4", 105.0),
        ("AMD Ryzen Threadripper 7980X", 64, 128, 3.2, 5.1, "Zen 4", 106.0),
        ("AMD Ryzen Threadripper 7970X", 32, 64, 4.0, 5.3, "Zen 4", 103.0),
        ("AMD Ryzen Threadripper 7960X", 24, 48, 4.2, 5.3, "Zen 4", 100.0),
        ("Intel Xeon W9-3495X", 56, 112, 1.9, 4.8, "Sapphire Rapids", 102.0),
        ("Intel Xeon W9-3475X", 36, 72, 2.2, 4.8, "Sapphire Rapids", 98.0),
        ("Intel Xeon W7-3465X", 28, 56, 2.5, 4.8, "Sapphire Rapids", 94.0),
        
        # Budget/Older
        ("Intel Core i3-10100", 4, 8, 3.6, 4.3, "Comet Lake", 36.0),
        ("AMD Ryzen 3 3300X", 4, 8, 3.8, 4.3, "Zen 2", 40.0),
        ("AMD Ryzen 3 3100", 4, 8, 3.6, 3.9, "Zen 2", 36.0),
        ("Intel Pentium Gold G7400", 2, 4, 3.7, 3.7, "Alder Lake", 28.0),
        ("AMD Athlon 3000G", 2, 4, 3.5, 3.5, "Zen+", 24.0),
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
        # Intel iGPUs (Integrated Graphics)
        ("Intel Iris Xe Graphics", 0, 1350, 0, "Xe", 18.0),
        ("Intel UHD Graphics 770", 0, 1550, 0, "Xe", 12.0),
        ("Intel UHD Graphics 730", 0, 1500, 0, "Xe", 10.0),
        ("Intel UHD Graphics 630", 0, 1200, 0, "Gen 9.5", 8.0),
        ("Intel Iris Xe Graphics G7", 0, 1350, 0, "Xe", 20.0),
        ("Intel Iris Plus Graphics", 0, 1100, 0, "Gen 11", 15.0),
        
        # NVIDIA Blackwell (RTX 5000)
        ("NVIDIA GeForce RTX 5090", 32, 2520, 1400, "Blackwell", 105.0),
        ("NVIDIA GeForce RTX 5080", 16, 2295, 1350, "Blackwell", 95.0),
        ("NVIDIA GeForce RTX 5070 Ti", 12, 2100, 1300, "Blackwell", 88.0),
        ("NVIDIA GeForce RTX 5070", 12, 1950, 1250, "Blackwell", 82.0),
        ("NVIDIA GeForce RTX 5060 Ti", 8, 1850, 1200, "Blackwell", 70.0),
        ("NVIDIA GeForce RTX 5060", 8, 1750, 1150, "Blackwell", 65.0),
        
        # AMD RDNA 4 (RX 9000)
        ("AMD Radeon RX 9070 XT", 16, 2500, 1300, "RDNA 4", 90.0),
        ("AMD Radeon RX 9070", 16, 2300, 1250, "RDNA 4", 85.0),
        ("AMD Radeon RX 9060 XT", 12, 2200, 1200, "RDNA 4", 75.0),
        ("AMD Radeon RX 9060", 12, 2000, 1150, "RDNA 4", 68.0),
        
        # NVIDIA Ada (RTX 4000)
        ("NVIDIA GeForce RTX 4090", 24, 2235, 1313, "Ada Lovelace", 100.0),
        ("NVIDIA GeForce RTX 4080 SUPER", 16, 2295, 1400, "Ada Lovelace", 96.0),
        ("NVIDIA GeForce RTX 4080", 16, 2205, 1313, "Ada Lovelace", 92.0),
        ("NVIDIA GeForce RTX 4070 Ti SUPER", 16, 2340, 1313, "Ada Lovelace", 88.0),
        ("NVIDIA GeForce RTX 4070 Ti", 12, 2310, 1313, "Ada Lovelace", 84.0),
        ("NVIDIA GeForce RTX 4070 SUPER", 12, 1980, 1313, "Ada Lovelace", 80.0),
        ("NVIDIA GeForce RTX 4070", 12, 1920, 1313, "Ada Lovelace", 72.0),
        ("NVIDIA GeForce RTX 4060 Ti 16GB", 8, 2535, 1125, "Ada Lovelace", 62.0),
        ("NVIDIA GeForce RTX 4060 Ti", 8, 2310, 1125, "Ada Lovelace", 58.0),
        ("NVIDIA GeForce RTX 4060", 8, 1830, 1063, "Ada Lovelace", 52.0),
        
        # AMD RDNA 3
        ("AMD Radeon RX 7900 XTX", 24, 1855, 1250, "RDNA 3", 92.0),
        ("AMD Radeon RX 7900 XT", 20, 1900, 1250, "RDNA 3", 88.0),
        ("AMD Radeon RX 7900 GRE", 16, 1880, 1219, "RDNA 3", 82.0),
        ("AMD Radeon RX 7800 XT", 16, 2124, 1219, "RDNA 3", 78.0),
        ("AMD Radeon RX 7700 XT", 12, 2171, 1125, "RDNA 3", 68.0),
        ("AMD Radeon RX 7600 XT", 8, 2539, 1125, "RDNA 3", 58.0),
        ("AMD Radeon RX 7600", 8, 2250, 1125, "RDNA 3", 52.0),
        
        # Intel Arc
        ("Intel Arc B580", 12, 2670, 1219, "Battlemage", 62.0),
        ("Intel Arc B570", 10, 2500, 1125, "Battlemage", 55.0),
        ("Intel Arc A770", 16, 2100, 1094, "Alchemist", 55.0),
        ("Intel Arc A750", 8, 2050, 1000, "Alchemist", 48.0),
        ("Intel Arc A580", 8, 1700, 1000, "Alchemist", 42.0),
        ("Intel Arc A380", 6, 2000, 937, "Alchemist", 35.0),
        
        # NVIDIA Ampere (RTX 3000)
        ("NVIDIA GeForce RTX 3090 Ti", 24, 1560, 1094, "Ampere", 82.0),
        ("NVIDIA GeForce RTX 3090", 24, 1395, 1219, "Ampere", 78.0),
        ("NVIDIA GeForce RTX 3080 Ti", 12, 1365, 1188, "Ampere", 74.0),
        ("NVIDIA GeForce RTX 3080", 10, 1440, 1188, "Ampere", 70.0),
        ("NVIDIA GeForce RTX 3070 Ti", 8, 1575, 1188, "Ampere", 64.0),
        ("NVIDIA GeForce RTX 3070", 8, 1500, 875, "Ampere", 62.0),
        ("NVIDIA GeForce RTX 3060 Ti", 8, 1410, 875, "Ampere", 55.0),
        ("NVIDIA GeForce RTX 3060", 12, 1320, 938, "Ampere", 50.0),
        ("NVIDIA GeForce RTX 3050", 8, 1552, 875, "Ampere", 42.0),
        
        # AMD RDNA 2
        ("AMD Radeon RX 6950 XT", 16, 2100, 1125, "RDNA 2", 76.0),
        ("AMD Radeon RX 6900 XT", 16, 2015, 1000, "RDNA 2", 72.0),
        ("AMD Radeon RX 6800 XT", 16, 2015, 1000, "RDNA 2", 68.0),
        ("AMD Radeon RX 6800", 16, 1815, 1000, "RDNA 2", 64.0),
        ("AMD Radeon RX 6750 XT", 12, 2150, 1125, "RDNA 2", 58.0),
        ("AMD Radeon RX 6700 XT", 12, 2321, 1000, "RDNA 2", 54.0),
        ("AMD Radeon RX 6700", 10, 2174, 1000, "RDNA 2", 50.0),
        ("AMD Radeon RX 6650 XT", 8, 2055, 1094, "RDNA 2", 50.0),
        ("AMD Radeon RX 6600 XT", 8, 2359, 1000, "RDNA 2", 48.0),
        ("AMD Radeon RX 6600", 8, 1626, 875, "RDNA 2", 44.0),
        ("AMD Radeon RX 6500 XT", 4, 2310, 1125, "RDNA 2", 36.0),
        ("AMD Radeon RX 6400", 4, 2039, 1000, "RDNA 2", 30.0),
        
        # NVIDIA Turing (RTX 2000 / GTX 1600)
        ("NVIDIA GeForce RTX 2080 Ti", 11, 1350, 875, "Turing", 60.0),
        ("NVIDIA GeForce RTX 2080 SUPER", 8, 1650, 938, "Turing", 56.0),
        ("NVIDIA GeForce RTX 2080", 8, 1515, 875, "Turing", 54.0),
        ("NVIDIA GeForce RTX 2070 SUPER", 8, 1605, 875, "Turing", 52.0),
        ("NVIDIA GeForce RTX 2070", 8, 1410, 875, "Turing", 48.0),
        ("NVIDIA GeForce RTX 2060 SUPER", 8, 1470, 875, "Turing", 46.0),
        ("NVIDIA GeForce RTX 2060", 6, 1365, 875, "Turing", 42.0),
        ("NVIDIA GeForce GTX 1660 Ti", 6, 1500, 750, "Turing", 40.0),
        ("NVIDIA GeForce GTX 1660 SUPER", 6, 1530, 875, "Turing", 38.0),
        ("NVIDIA GeForce GTX 1660", 6, 1530, 1001, "Turing", 36.0),
        ("NVIDIA GeForce GTX 1650 SUPER", 4, 1530, 750, "Turing", 32.0),
        ("NVIDIA GeForce GTX 1650", 4, 1485, 1001, "Turing", 28.0),
        
        # Laptop GPUs - NVIDIA
        ("NVIDIA GeForce RTX 4090 Laptop GPU", 16, 1455, 1125, "Ada Lovelace", 82.0),
        ("NVIDIA GeForce RTX 4080 Laptop GPU", 12, 1350, 1125, "Ada Lovelace", 75.0),
        ("NVIDIA GeForce RTX 4070 Laptop GPU", 8, 1230, 1000, "Ada Lovelace", 65.0),
        ("NVIDIA GeForce RTX 4060 Laptop GPU", 8, 1350, 1000, "Ada Lovelace", 58.0),
        ("NVIDIA GeForce RTX 4050 Laptop GPU", 6, 1605, 1000, "Ada Lovelace", 48.0),
        ("NVIDIA GeForce RTX 3080 Ti Laptop GPU", 16, 1125, 875, "Ampere", 68.0),
        ("NVIDIA GeForce RTX 3080 Laptop GPU", 16, 1110, 875, "Ampere", 64.0),
        ("NVIDIA GeForce RTX 3070 Ti Laptop GPU", 8, 1035, 875, "Ampere", 58.0),
        ("NVIDIA GeForce RTX 3070 Laptop GPU", 8, 1290, 875, "Ampere", 56.0),
        ("NVIDIA GeForce RTX 3060 Laptop GPU", 6, 1283, 875, "Ampere", 48.0),
        ("NVIDIA GeForce RTX 3050 Ti Laptop GPU", 4, 1035, 750, "Ampere", 38.0),
        ("NVIDIA GeForce RTX 3050 Laptop GPU", 4, 1057, 750, "Ampere", 36.0),
        
        # Laptop GPUs - AMD
        ("AMD Radeon RX 7900M", 16, 2090, 1125, "RDNA 3", 72.0),
        ("AMD Radeon RX 7800M", 12, 2145, 1125, "RDNA 3", 64.0),
        ("AMD Radeon RX 7700S", 8, 2200, 1125, "RDNA 3", 56.0),
        ("AMD Radeon RX 7600M XT", 8, 2300, 1125, "RDNA 3", 52.0),
        ("AMD Radeon RX 7600M", 8, 2070, 1125, "RDNA 3", 48.0),
        ("AMD Radeon RX 6850M XT", 12, 2300, 1125, "RDNA 2", 58.0),
        ("AMD Radeon RX 6800M", 12, 2300, 1000, "RDNA 2", 54.0),
        ("AMD Radeon RX 6700M", 10, 2300, 1000, "RDNA 2", 48.0),
        ("AMD Radeon RX 6600M", 8, 2177, 875, "RDNA 2", 42.0),
        
        # Older/Budget Desktop
        ("NVIDIA GeForce GTX 1080 Ti", 11, 1480, 688, "Pascal", 52.0),
        ("NVIDIA GeForce GTX 1080", 8, 1607, 625, "Pascal", 46.0),
        ("NVIDIA GeForce GTX 1070 Ti", 8, 1607, 1002, "Pascal", 44.0),
        ("NVIDIA GeForce GTX 1070", 8, 1506, 1002, "Pascal", 42.0),
        ("NVIDIA GeForce GTX 1060 6GB", 6, 1506, 1002, "Pascal", 36.0),
        ("NVIDIA GeForce GTX 1060 3GB", 3, 1506, 1002, "Pascal", 32.0),
        ("NVIDIA GeForce GTX 1050 Ti", 4, 1290, 875, "Pascal", 26.0),
        ("NVIDIA GeForce GTX 1050", 2, 1354, 875, "Pascal", 22.0),
        ("AMD Radeon RX 590", 8, 1469, 1000, "Polaris", 38.0),
        ("AMD Radeon RX 580", 8, 1257, 1000, "Polaris", 34.0),
        ("AMD Radeon RX 570", 4, 1168, 875, "Polaris", 30.0),
        ("AMD Radeon RX 560", 4, 1175, 875, "Polaris", 24.0),
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
    
    # ram_sensitivity: 0.7=low RAM usage, 1.0=normal, 1.3=high, 1.6=very high
    # RT support: 1=yes, 0=no | PT support: 1=yes, 0=no
    # Format: (name, genre, diff, low, med, high, ultra, 1080p, 1440p, 4k, ram, rt, pt)
    new_games = [
        # AAA Games with RT/PT
        ("Starfield", "RPG", 1.7, 1.5, 1.0, 0.65, 0.4, 1.0, 0.6, 0.32, 1.4, 0, 0),  # No RT/PT
        ("Alan Wake 2", "Horror", 1.9, 1.4, 1.0, 0.6, 0.35, 1.0, 0.58, 0.28, 1.3, 1, 1),  # RT + PT
        ("The Last of Us Part I", "Action", 1.6, 1.5, 1.0, 0.7, 0.45, 1.0, 0.62, 0.33, 1.2, 0, 0),  # No RT/PT
        ("Spider-Man Remastered", "Action", 1.4, 1.6, 1.0, 0.75, 0.5, 1.0, 0.68, 0.38, 1.1, 1, 0),  # RT only
        ("God of War", "Action", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.35, 1.2, 0, 0),  # No RT/PT
        ("Ratchet & Clank: Rift Apart", "Action", 1.7, 1.4, 1.0, 0.65, 0.4, 1.0, 0.6, 0.32, 1.3, 1, 0),  # RT only
        ("Returnal", "Roguelike", 1.6, 1.5, 1.0, 0.7, 0.45, 1.0, 0.63, 0.34, 1.2, 1, 0),  # RT only
        
        # Competitive FPS (no RT/PT)
        ("Apex Legends", "FPS", 0.6, 1.7, 1.0, 0.85, 0.75, 1.0, 0.78, 0.55, 0.8, 0, 0),
        ("Overwatch 2", "FPS", 0.5, 1.8, 1.0, 0.9, 0.8, 1.0, 0.8, 0.6, 0.7, 0, 0),
        ("Rainbow Six Siege", "FPS", 0.55, 1.7, 1.0, 0.88, 0.78, 1.0, 0.75, 0.52, 0.8, 0, 0),
        ("Fortnite", "FPS", 0.5, 1.8, 1.0, 0.9, 0.82, 1.0, 0.82, 0.62, 0.8, 0, 0),
        ("Call of Duty: Warzone", "FPS", 1.3, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.42, 1.1, 0, 0),
        ("PUBG", "FPS", 1.2, 1.5, 1.0, 0.78, 0.6, 1.0, 0.72, 0.45, 1.0, 0, 0),
        
        # Racing with RT
        ("Forza Horizon 5", "Racing", 1.2, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.42, 1.1, 1, 0),  # RT only
        ("F1 2024", "Racing", 1.3, 1.4, 1.0, 0.72, 0.52, 1.0, 0.68, 0.4, 1.0, 1, 0),  # RT only
        ("Assetto Corsa Competizione", "Racing", 1.4, 1.4, 1.0, 0.7, 0.5, 1.0, 0.65, 0.38, 1.1, 0, 0),
        ("Gran Turismo 7", "Racing", 1.3, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.42, 1.0, 1, 0),  # RT only
        
        # Strategy (no RT/PT)
        ("Civilization VI", "Strategy", 0.8, 1.6, 1.0, 0.85, 0.7, 1.0, 0.75, 0.5, 1.3, 0, 0),
        ("Total War: Warhammer III", "Strategy", 1.4, 1.5, 1.0, 0.7, 0.5, 1.0, 0.65, 0.38, 1.4, 0, 0),
        ("Age of Empires IV", "Strategy", 1.0, 1.6, 1.0, 0.8, 0.65, 1.0, 0.75, 0.5, 1.2, 0, 0),
        ("Stellaris", "Strategy", 0.9, 1.6, 1.0, 0.82, 0.68, 1.0, 0.76, 0.52, 1.5, 0, 0),
        
        # Simulation (no RT/PT)
        ("Microsoft Flight Simulator", "Simulation", 2.0, 1.3, 1.0, 0.6, 0.35, 1.0, 0.55, 0.25, 1.7, 0, 0),
        ("Cities: Skylines II", "Simulation", 1.6, 1.4, 1.0, 0.68, 0.45, 1.0, 0.62, 0.35, 1.8, 0, 0),
        ("Euro Truck Simulator 2", "Simulation", 0.7, 1.7, 1.0, 0.85, 0.72, 1.0, 0.78, 0.55, 0.9, 0, 0),
        ("BeamNG.drive", "Simulation", 1.3, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.43, 1.2, 0, 0),
        
        # Indie/Light (no RT/PT)
        ("Hades", "Roguelike", 0.3, 2.0, 1.0, 0.95, 0.9, 1.0, 0.9, 0.8, 0.6, 0, 0),
        ("Stardew Valley", "Simulation", 0.2, 2.2, 1.0, 1.0, 0.95, 1.0, 0.95, 0.9, 0.5, 0, 0),
        ("Terraria", "Sandbox", 0.25, 2.1, 1.0, 0.98, 0.92, 1.0, 0.92, 0.85, 0.6, 0, 0),
        ("Hollow Knight", "Metroidvania", 0.3, 2.0, 1.0, 0.95, 0.9, 1.0, 0.9, 0.82, 0.6, 0, 0),
        ("Dead Cells", "Roguelike", 0.35, 1.9, 1.0, 0.92, 0.88, 1.0, 0.88, 0.78, 0.7, 0, 0),
        
        # Recent AAA with RT
        ("Elden Ring", "RPG", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.36, 1.2, 0, 0),  # No RT/PT
        ("Resident Evil 4 Remake", "Horror", 1.6, 1.4, 1.0, 0.7, 0.45, 1.0, 0.63, 0.34, 1.1, 1, 0),  # RT only
        ("Street Fighter 6", "Fighting", 0.7, 1.7, 1.0, 0.85, 0.75, 1.0, 0.78, 0.58, 0.8, 0, 0),  # No RT/PT
        ("Baldur's Gate 3", "RPG", 1.4, 1.5, 1.0, 0.73, 0.5, 1.0, 0.66, 0.37, 1.3, 0, 0),  # No RT/PT
        ("Diablo IV", "RPG", 1.3, 1.5, 1.0, 0.75, 0.52, 1.0, 0.68, 0.4, 1.1, 0, 0),  # No RT/PT
        ("Palworld", "Survival", 1.1, 1.6, 1.0, 0.78, 0.6, 1.0, 0.72, 0.45, 1.2, 0, 0),  # No RT/PT
        ("Helldivers 2", "Shooter", 1.2, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.43, 1.0, 0, 0),  # No RT/PT
        ("Tekken 8", "Fighting", 1.3, 1.5, 1.0, 0.75, 0.55, 1.0, 0.7, 0.42, 0.9, 0, 0),
        ("Dragon's Dogma 2", "RPG", 1.7, 1.4, 1.0, 0.65, 0.42, 1.0, 0.6, 0.33, 1.3, 0, 0),
        
        # RT/PT Showcase Games
        ("Portal RTX", "Puzzle", 1.8, 1.3, 1.0, 0.6, 0.35, 1.0, 0.55, 0.28, 1.1, 1, 1),  # RT + PT (Full PT Remake)
        ("Control", "Action", 1.5, 1.5, 1.0, 0.7, 0.45, 1.0, 0.63, 0.33, 1.2, 1, 0),  # RT only
        ("Metro Exodus Enhanced", "FPS", 1.7, 1.4, 1.0, 0.65, 0.4, 1.0, 0.6, 0.32, 1.2, 1, 0),  # RT only
        ("Dying Light 2", "Action", 1.6, 1.5, 1.0, 0.7, 0.45, 1.0, 0.62, 0.33, 1.3, 1, 0),  # RT only
        ("Watch Dogs Legion", "Action", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.35, 1.2, 1, 0),  # RT only
        ("Minecraft RTX", "Sandbox", 1.4, 1.6, 1.0, 0.75, 0.5, 1.0, 0.68, 0.38, 0.8, 1, 1),  # RT + PT
        ("Quake II RTX", "FPS", 1.3, 1.6, 1.0, 0.75, 0.5, 1.0, 0.68, 0.38, 0.7, 1, 1),  # RT + PT (Full PT)
        ("Ghostwire: Tokyo", "Action", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.35, 1.2, 1, 0),  # RT only
        ("Hitman 3", "Stealth", 1.4, 1.5, 1.0, 0.73, 0.5, 1.0, 0.66, 0.37, 1.1, 1, 0),  # RT only
        ("Atomic Heart", "FPS", 1.6, 1.4, 1.0, 0.7, 0.45, 1.0, 0.63, 0.34, 1.2, 1, 0),  # RT only
        ("The Witcher 3 Next-Gen", "RPG", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.35, 1.2, 1, 0),  # RT only
        ("Doom Eternal", "FPS", 1.2, 1.6, 1.0, 0.78, 0.6, 1.0, 0.72, 0.45, 0.9, 1, 0),  # RT only
        ("Call of Duty: Modern Warfare III", "FPS", 1.4, 1.5, 1.0, 0.73, 0.5, 1.0, 0.66, 0.37, 1.1, 1, 0),  # RT only
        ("Battlefield 2042", "FPS", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.35, 1.2, 1, 0),  # RT only
        ("Far Cry 6", "FPS", 1.4, 1.5, 1.0, 0.73, 0.5, 1.0, 0.66, 0.37, 1.2, 1, 0),  # RT only
        ("Assassin's Creed Valhalla", "RPG", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.35, 1.3, 0, 0),
        ("Spider-Man: Miles Morales", "Action", 1.4, 1.6, 1.0, 0.75, 0.5, 1.0, 0.68, 0.38, 1.1, 1, 0),  # RT only
        ("Deathloop", "FPS", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.35, 1.2, 1, 0),  # RT only
        ("Guardians of the Galaxy", "Action", 1.5, 1.5, 1.0, 0.72, 0.48, 1.0, 0.65, 0.35, 1.2, 1, 0),  # RT only
        ("Forza Motorsport", "Racing", 1.4, 1.5, 1.0, 0.73, 0.5, 1.0, 0.66, 0.37, 1.1, 1, 0),  # RT only
        ("Avatar: Frontiers of Pandora", "Action", 1.8, 1.4, 1.0, 0.65, 0.4, 1.0, 0.6, 0.32, 1.4, 1, 0),  # RT only
        ("Black Myth: Wukong", "Action", 1.7, 1.4, 1.0, 0.65, 0.42, 1.0, 0.6, 0.33, 1.3, 1, 1),  # RT + PT
    ]
    
    for game in new_games:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO games 
                (name, genre, difficulty_multiplier, low_scaling, med_scaling, high_scaling, 
                 ultra_scaling, res_1080p_scaling, res_1440p_scaling, res_4k_scaling, ram_sensitivity, supports_rt, supports_pt) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
