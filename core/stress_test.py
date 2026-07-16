"""
Improved stress test module with proper monitoring
"""
import psutil
import time
import multiprocessing as mp
from typing import Callable, Optional

try:
    from core import hardware_detector
except ImportError:
    # Running this file directly (python core/stress_test.py) puts
    # core/ itself on sys.path rather than the project root.
    import hardware_detector

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

    try:
        for i in range(duration):
            time.sleep(1)
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_freq = psutil.cpu_freq()

            # psutil.sensors_temperatures() only reads Linux's lm-sensors
            # /sys interface and is unimplemented on Windows (always
            # empty/None there) — use the WMI-based reader instead, which
            # returns a real Celsius value or explicitly None if this
            # system's ACPI tables don't expose a thermal zone.
            temp_c = hardware_detector.detect_cpu_temperature()

            stat = {
                "elapsed": i + 1,
                "cpu_percent": cpu_percent,
                "cpu_freq_mhz": cpu_freq.current if cpu_freq else 0,
                "temperature": temp_c,
                "temperature_available": temp_c is not None,
            }

            stats.append(stat)

            if callback:
                callback(stat)
    finally:
        # Always terminate worker processes, even if the loop above
        # raises (e.g. a bad callback or psutil call) — otherwise the
        # CPU-stress workers keep running in the background indefinitely.
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
        if stat["temperature_available"]:
            temp_str = f"{stat['temperature']:.1f}°C"
        else:
            temp_str = "N/A (sıcaklık verisi bu sistemde okunamıyor)"
        print(f"T-{stat['elapsed']}s | CPU: {stat['cpu_percent']:.1f}% | Freq: {stat['cpu_freq_mhz']:.0f} MHz | Temp: {temp_str}")
    
    result = run_stress_test(10, print_stat)
    print(f"\n✅ Test completed. Avg load: {result['avg_load']:.1f}%")
