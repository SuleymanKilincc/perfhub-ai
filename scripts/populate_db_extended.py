"""
Extended database population - adds MUCH more hardware
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core import db_manager

def add_extended_cpus():
    """Add extended CPU list including older Intel generations"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    extended_cpus = [
        # Intel 9th Gen (Coffee Lake Refresh)
        ("Intel Core i9-9900KS", 8, 16, 4.0, 5.0, "Coffee Lake Refresh", 68.0),
        ("Intel Core i9-9900K", 8, 16, 3.6, 5.0, "Coffee Lake Refresh", 66.0),
        ("Intel Core i7-9700K", 8, 8, 3.6, 4.9, "Coffee Lake Refresh", 60.0),
        ("Intel Core i5-9600K", 6, 6, 3.7, 4.6, "Coffee Lake Refresh", 52.0),
        ("Intel Core i5-9400F", 6, 6, 2.9, 4.1, "Coffee Lake Refresh", 46.0),
        ("Intel Core i3-9100F", 4, 4, 3.6, 4.2, "Coffee Lake Refresh", 34.0),
        
        # Intel 8th Gen (Coffee Lake)
        ("Intel Core i7-8700K", 6, 12, 3.7, 4.7, "Coffee Lake", 58.0),
        ("Intel Core i7-8700", 6, 12, 3.2, 4.6, "Coffee Lake", 54.0),
        ("Intel Core i5-8600K", 6, 6, 3.6, 4.3, "Coffee Lake", 50.0),
        ("Intel Core i5-8400", 6, 6, 2.8, 4.0, "Coffee Lake", 44.0),
        ("Intel Core i3-8100", 4, 4, 3.6, 3.6, "Coffee Lake", 32.0),
        
        # Intel 7th Gen (Kaby Lake)
        ("Intel Core i7-7700K", 4, 8, 4.2, 4.5, "Kaby Lake", 52.0),
        ("Intel Core i7-7700", 4, 8, 3.6, 4.2, "Kaby Lake", 48.0),
        ("Intel Core i5-7600K", 4, 4, 3.8, 4.2, "Kaby Lake", 44.0),
        ("Intel Core i5-7500", 4, 4, 3.4, 3.8, "Kaby Lake", 40.0),
        ("Intel Core i5-7400", 4, 4, 3.0, 3.5, "Kaby Lake", 38.0),
        ("Intel Core i3-7100", 2, 4, 3.9, 3.9, "Kaby Lake", 30.0),
        
        # Intel 6th Gen (Skylake)
        ("Intel Core i7-6700K", 4, 8, 4.0, 4.2, "Skylake", 50.0),
        ("Intel Core i7-6700", 4, 8, 3.4, 4.0, "Skylake", 46.0),
        ("Intel Core i5-6600K", 4, 4, 3.5, 3.9, "Skylake", 42.0),
        ("Intel Core i5-6500", 4, 4, 3.2, 3.6, "Skylake", 38.0),
        ("Intel Core i5-6400", 4, 4, 2.7, 3.3, "Skylake", 36.0),
        ("Intel Core i3-6100", 2, 4, 3.7, 3.7, "Skylake", 28.0),
        
        # Intel 5th Gen (Broadwell)
        ("Intel Core i7-5775C", 4, 8, 3.3, 3.7, "Broadwell", 48.0),
        ("Intel Core i5-5675C", 4, 4, 3.1, 3.6, "Broadwell", 40.0),
        
        # AMD Zen+ (Ryzen 2000)
        ("AMD Ryzen 7 2700X", 8, 16, 3.7, 4.3, "Zen+", 52.0),
        ("AMD Ryzen 7 2700", 8, 16, 3.2, 4.1, "Zen+", 48.0),
        ("AMD Ryzen 5 2600X", 6, 12, 3.6, 4.2, "Zen+", 44.0),
        ("AMD Ryzen 5 2600", 6, 12, 3.4, 3.9, "Zen+", 42.0),
        ("AMD Ryzen 5 2400G", 4, 8, 3.6, 3.9, "Zen+", 38.0),
        ("AMD Ryzen 3 2200G", 4, 4, 3.5, 3.7, "Zen+", 32.0),
        
        # AMD Zen (Ryzen 1000)
        ("AMD Ryzen 7 1800X", 8, 16, 3.6, 4.0, "Zen", 50.0),
        ("AMD Ryzen 7 1700X", 8, 16, 3.4, 3.8, "Zen", 48.0),
        ("AMD Ryzen 7 1700", 8, 16, 3.0, 3.7, "Zen", 46.0),
        ("AMD Ryzen 5 1600X", 6, 12, 3.6, 4.0, "Zen", 42.0),
        ("AMD Ryzen 5 1600", 6, 12, 3.2, 3.6, "Zen", 40.0),
        ("AMD Ryzen 5 1500X", 4, 8, 3.5, 3.7, "Zen", 36.0),
        ("AMD Ryzen 5 1400", 4, 8, 3.2, 3.4, "Zen", 34.0),
        ("AMD Ryzen 3 1300X", 4, 4, 3.5, 3.7, "Zen", 32.0),
        ("AMD Ryzen 3 1200", 4, 4, 3.1, 3.4, "Zen", 30.0),
        
        # More Laptop CPUs - Intel 11th Gen
        ("Intel Core i7-11800H", 8, 16, 2.3, 4.6, "Tiger Lake", 60.0),
        ("Intel Core i5-11400H", 6, 12, 2.7, 4.5, "Tiger Lake", 52.0),
        ("Intel Core i7-1185G7", 4, 8, 3.0, 4.8, "Tiger Lake", 48.0),
        ("Intel Core i5-1135G7", 4, 8, 2.4, 4.2, "Tiger Lake", 42.0),
        
        # More Laptop CPUs - Intel 10th Gen
        ("Intel Core i7-10875H", 8, 16, 2.3, 5.1, "Comet Lake", 58.0),
        ("Intel Core i7-10750H", 6, 12, 2.6, 5.0, "Comet Lake", 54.0),
        ("Intel Core i5-10300H", 4, 8, 2.5, 4.5, "Comet Lake", 46.0),
        ("Intel Core i7-1065G7", 4, 8, 1.3, 3.9, "Ice Lake", 44.0),
        
        # More Laptop CPUs - AMD Zen 2
        ("AMD Ryzen 9 4900HS", 8, 16, 3.0, 4.3, "Zen 2", 58.0),
        ("AMD Ryzen 7 4800H", 8, 16, 2.9, 4.2, "Zen 2", 56.0),
        ("AMD Ryzen 5 4600H", 6, 12, 3.0, 4.0, "Zen 2", 48.0),
        ("AMD Ryzen 7 4800U", 8, 16, 1.8, 4.2, "Zen 2", 50.0),
        ("AMD Ryzen 5 4500U", 6, 6, 2.3, 4.0, "Zen 2", 42.0),
    ]
    
    for cpu in extended_cpus:
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
    print(f"✓ Added {len(extended_cpus)} extended CPU models")

def add_extended_gpus():
    """Add extended GPU list including NVIDIA 900 series and more laptop GPUs"""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    extended_gpus = [
        # NVIDIA Maxwell (GTX 900 series)
        ("NVIDIA GeForce GTX 980 Ti", 6, 1000, 875, "Maxwell", 48.0),
        ("NVIDIA GeForce GTX 980", 4, 1126, 875, "Maxwell", 44.0),
        ("NVIDIA GeForce GTX 970", 4, 1050, 875, "Maxwell", 40.0),
        ("NVIDIA GeForce GTX 960", 2, 1126, 875, "Maxwell", 32.0),
        ("NVIDIA GeForce GTX 950", 2, 1024, 825, "Maxwell", 28.0),
        
        # NVIDIA Kepler (GTX 700 series)
        ("NVIDIA GeForce GTX 780 Ti", 3, 876, 875, "Kepler", 42.0),
        ("NVIDIA GeForce GTX 780", 3, 863, 750, "Kepler", 40.0),
        ("NVIDIA GeForce GTX 770", 2, 1046, 875, "Kepler", 36.0),
        ("NVIDIA GeForce GTX 760", 2, 980, 750, "Kepler", 32.0),
        ("NVIDIA GeForce GTX 750 Ti", 2, 1020, 675, "Kepler", 26.0),
        
        # More NVIDIA Laptop GPUs - RTX 2000 Mobile
        ("NVIDIA GeForce RTX 2080 SUPER Max-Q", 8, 735, 875, "Turing", 50.0),
        ("NVIDIA GeForce RTX 2080 Max-Q", 8, 735, 875, "Turing", 48.0),
        ("NVIDIA GeForce RTX 2070 SUPER Max-Q", 8, 930, 875, "Turing", 46.0),
        ("NVIDIA GeForce RTX 2070 Max-Q", 8, 885, 875, "Turing", 44.0),
        ("NVIDIA GeForce RTX 2060 Max-Q", 6, 975, 875, "Turing", 38.0),
        
        # NVIDIA GTX 1000 Mobile
        ("NVIDIA GeForce GTX 1080 Mobile", 8, 1566, 625, "Pascal", 44.0),
        ("NVIDIA GeForce GTX 1070 Mobile", 8, 1443, 1001, "Pascal", 40.0),
        ("NVIDIA GeForce GTX 1060 Mobile", 6, 1404, 1001, "Pascal", 34.0),
        ("NVIDIA GeForce GTX 1050 Ti Mobile", 4, 1493, 875, "Pascal", 26.0),
        ("NVIDIA GeForce GTX 1050 Mobile", 4, 1354, 875, "Pascal", 22.0),
        
        # NVIDIA GTX 900M Series
        ("NVIDIA GeForce GTX 980M", 4, 1038, 625, "Maxwell", 36.0),
        ("NVIDIA GeForce GTX 970M", 3, 924, 625, "Maxwell", 32.0),
        ("NVIDIA GeForce GTX 960M", 2, 1029, 625, "Maxwell", 26.0),
        ("NVIDIA GeForce GTX 950M", 2, 914, 625, "Maxwell", 22.0),
        
        # AMD Vega
        ("AMD Radeon RX Vega 64", 8, 1247, 945, "Vega", 50.0),
        ("AMD Radeon RX Vega 56", 8, 1156, 800, "Vega", 46.0),
        ("AMD Radeon RX Vega 11 (iGPU)", 0, 1300, 0, "Vega", 16.0),
        ("AMD Radeon RX Vega 8 (iGPU)", 0, 1200, 0, "Vega", 14.0),
        
        # AMD Polaris (More models)
        ("AMD Radeon RX 480", 8, 1120, 1000, "Polaris", 36.0),
        ("AMD Radeon RX 470", 4, 926, 875, "Polaris", 32.0),
        ("AMD Radeon RX 460", 2, 1090, 875, "Polaris", 22.0),
        
        # AMD Laptop GPUs - RX 6000M
        ("AMD Radeon RX 6650M", 8, 2222, 875, "RDNA 2", 40.0),
        ("AMD Radeon RX 6550M", 4, 2464, 875, "RDNA 2", 32.0),
        
        # AMD Laptop GPUs - RX 5000M
        ("AMD Radeon RX 5700M", 10, 1720, 875, "RDNA", 44.0),
        ("AMD Radeon RX 5600M", 6, 1265, 875, "RDNA", 38.0),
        ("AMD Radeon RX 5500M", 4, 1327, 875, "RDNA", 32.0),
        
        # Intel Arc Laptop
        ("Intel Arc A730M", 12, 1100, 1000, "Alchemist", 46.0),
        ("Intel Arc A550M", 8, 900, 875, "Alchemist", 38.0),
        ("Intel Arc A370M", 4, 1550, 875, "Alchemist", 30.0),
    ]
    
    for gpu in extended_gpus:
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
    print(f"✓ Added {len(extended_gpus)} extended GPU models")

if __name__ == "__main__":
    print("Adding extended hardware to database...\n")
    add_extended_cpus()
    add_extended_gpus()
    print("\n✅ Extended database population completed!")
