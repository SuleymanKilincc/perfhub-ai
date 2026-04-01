import wmi
import psutil
import GPUtil
import os
import pythoncom

# ---- RAM Type mapping (SMBIOS spec) ----
SMBIOS_MEM_TYPE = {
    20: "DDR",
    21: "DDR2",
    22: "DDR2 FB-DIMM",
    24: "DDR3",
    26: "DDR4",
    34: "DDR5",
    35: "LPDDR5",
    36: "DDR5",
}

# ---- Bus type mapping for disks ----
BUS_TYPE = {
    3: "SATA",
    4: "ATAPI",
    5: "RAID",
    6: "SAS",
    7: "SCSI",
    8: "Storage Spaces",
    9: "NVMe",
    10: "USB",
    11: "iSCSI",
    12: "SAS",
    13: "SD",
    14: "MMC",
    17: "NVMe",
}

MEDIA_TYPE = {
    3: "HDD",
    4: "SSD",
    5: "SCM",
}


def detect_cpu():
    """Detects the exact CPU model name using WMI."""
    try:
        pythoncom.CoInitialize()
        w = wmi.WMI()
        for processor in w.Win32_Processor():
            name = processor.Name
            clean_name = name.replace("(R)", "").replace("(TM)", "").replace(" CPU", "")
            if " @ " in clean_name:
                clean_name = clean_name.split(" @ ")[0]
            return clean_name.strip()
    except Exception as e:
        print(f"Error detecting CPU: {e}")
        return "Unknown CPU"


def detect_gpu():
    """Detects the exact GPU model name."""
    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            return gpus[0].name
        pythoncom.CoInitialize()
        w = wmi.WMI()
        for vc in w.Win32_VideoController():
            if vc.CurrentHorizontalResolution:
                return vc.Name.strip()
    except Exception as e:
        print(f"Error detecting GPU: {e}")
        return "Unknown GPU"


def detect_ram_gb():
    """Detects total installed RAM in GB (fast path via psutil)."""
    try:
        return round(psutil.virtual_memory().total / (1024 ** 3))
    except Exception:
        return 0


def detect_ram_details():
    """
    Returns a list of dicts with detailed RAM info per DIMM:
      - capacity_gb, speed_mhz, configured_mhz, mem_type, manufacturer, part_number
    """
    try:
        pythoncom.CoInitialize()
        w = wmi.WMI()
        sticks = []
        for mem in w.Win32_PhysicalMemory():
            try:
                cap_gb = int(mem.Capacity) // 1024 // 1024 // 1024
            except (TypeError, ValueError):
                cap_gb = 0
            try:
                speed = int(mem.Speed) if mem.Speed else 0
            except (TypeError, ValueError):
                speed = 0
            try:
                configured = int(mem.ConfiguredClockSpeed) if mem.ConfiguredClockSpeed else speed
            except (TypeError, ValueError):
                configured = speed
            smbios_type = getattr(mem, 'SMBIOSMemoryType', 0) or 0
            mem_type = SMBIOS_MEM_TYPE.get(smbios_type, f"RAM (code {smbios_type})")
            manufacturer = (mem.Manufacturer or "").strip()
            part = (mem.PartNumber or "").strip()
            sticks.append({
                "capacity_gb": cap_gb,
                "speed_mhz": speed,
                "configured_mhz": configured,
                "mem_type": mem_type,
                "manufacturer": manufacturer,
                "part_number": part,
            })
        return sticks
    except Exception as e:
        print(f"Error detecting RAM details: {e}")
        return []


def detect_storage():
    """
    Returns a list of dicts with SSD/HDD info:
      - name, size_gb, media_type (SSD/HDD), bus_type (NVMe/SATA/...)
    """
    drives = []
    try:
        pythoncom.CoInitialize()
        w = wmi.WMI(namespace='root/microsoft/windows/storage')
        for d in w.MSFT_PhysicalDisk():
            try:
                size_gb = int(d.Size) // 1024 // 1024 // 1024
            except (TypeError, ValueError):
                size_gb = 0
            media = MEDIA_TYPE.get(getattr(d, 'MediaType', 0), "Unknown")
            bus   = BUS_TYPE.get(getattr(d, 'BusType', 0), "Unknown")
            name  = (getattr(d, 'FriendlyName', '') or "").strip()
            drives.append({
                "name": name,
                "size_gb": size_gb,
                "media_type": media,
                "bus_type": bus,
            })
    except Exception as e:
        # Fallback to Win32_DiskDrive
        try:
            w2 = wmi.WMI()
            for disk in w2.Win32_DiskDrive():
                try:
                    size_gb = int(disk.Size) // 1024 // 1024 // 1024
                except (TypeError, ValueError):
                    size_gb = 0
                interface = (disk.InterfaceType or "").strip()
                model     = (disk.Model or "").strip()
                # Guess media type from name
                media = "SSD" if any(k in model.upper() for k in ["SSD", "NVMe", "NVME", "SOLID"]) else "HDD"
                drives.append({
                    "name": model,
                    "size_gb": size_gb,
                    "media_type": media,
                    "bus_type": interface,
                })
        except Exception as e2:
            print(f"Error detecting storage (fallback): {e2}")
    return drives


def get_system_info():
    """Returns a dictionary containing all detected hardware."""
    ram_sticks = detect_ram_details()

    # Build a human-readable RAM summary
    total_ram_gb = sum(s["capacity_gb"] for s in ram_sticks) or detect_ram_gb()
    if ram_sticks:
        s0 = ram_sticks[0]
        mhz = s0["configured_mhz"] or s0["speed_mhz"]
        ram_label = f"{total_ram_gb} GB {s0['mem_type']} @ {mhz} MHz"
    else:
        ram_label = f"{detect_ram_gb()} GB RAM"

    return {
        "cpu": detect_cpu(),
        "gpu": detect_gpu(),
        "ram": detect_ram_gb(),          # kept as int for score calculation
        "ram_label": ram_label,           # e.g. "16 GB DDR5 @ 4800 MHz"
        "ram_details": ram_sticks,        # full per-DIMM info
        "storage": detect_storage(),      # list of drives
    }


if __name__ == "__main__":
    import json
    print("Detecting system hardware...")
    info = get_system_info()
    print(json.dumps(info, indent=2, default=str))
