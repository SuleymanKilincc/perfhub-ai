"""
Improved stress test module with proper monitoring
"""
import psutil
import time
import multiprocessing as mp
from typing import Callable, Optional

def cpu_stress_worker(duration: int):
    """Worker function that stresses a single CPU core"""
    end_time = time.time() + duration
    while time.time() < end_time:
        # Intensive calculation to max out CPU
        _ = sum(i * i for i in range(10000))

def run_stress_test(duration: int = 20, callback: Optional[Callable] = None) -> dict:
    """
    Runs a CPU stress test for specified duration.
    
    Args:
        duration: Test duration in seconds
        callback: Optional callback function called each second with stats
    
    Returns:
        dict with test results
    """
    cpu_count = psutil.cpu_count(logical=True)
    processes = []
    
    # Start stress workers
    for _ in range(cpu_count):
        p = mp.Process(target=cpu_stress_worker, args=(duration,))
        p.start()
        processes.append(p)
    
    # Monitor
    stats = []
    start_time = time.time()
    
    for i in range(duration):
        time.sleep(1)
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_freq = psutil.cpu_freq()
        temps = psutil.sensors_temperatures() if hasattr(psutil, 'sensors_temperatures') else {}
        
        stat = {
            "elapsed": i + 1,
            "cpu_percent": cpu_percent,
            "cpu_freq_mhz": cpu_freq.current if cpu_freq else 0,
            "temperature": None
        }
        
        # Try to get CPU temperature
        if temps and 'coretemp' in temps:
            stat["temperature"] = temps['coretemp'][0].current
        
        stats.append(stat)
        
        if callback:
            callback(stat)
    
    # Cleanup
    for p in processes:
        p.terminate()
        p.join()
    
    return {
        "duration": duration,
        "cpu_cores": cpu_count,
        "stats": stats,
        "avg_load": sum(s["cpu_percent"] for s in stats) / len(stats),
        "max_load": max(s["cpu_percent"] for s in stats)
    }

if __name__ == "__main__":
    print("Starting 10-second stress test...")
    
    def print_stat(stat):
        temp_str = f"{stat['temperature']:.1f}°C" if stat['temperature'] else "N/A"
        print(f"T-{stat['elapsed']}s | CPU: {stat['cpu_percent']:.1f}% | Freq: {stat['cpu_freq_mhz']:.0f} MHz | Temp: {temp_str}")
    
    result = run_stress_test(10, print_stat)
    print(f"\n✅ Test completed. Avg load: {result['avg_load']:.1f}%")
