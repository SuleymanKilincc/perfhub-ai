// Type definitions for PerfHub AI

export interface HardwareData {
  cpu: string
  gpu: string
  ram: number
  ram_label?: string
  cpu_cores?: number
}

export interface CPUData {
  id?: number
  name: string
  cores?: number
  threads?: number
  base_clock?: number
  boost_clock?: number
  architecture?: string
  power_score: number
}

export interface GPUData {
  id?: number
  name: string
  vram?: number
  core_clock?: number
  memory_clock?: number
  architecture?: string
  power_score: number
}

export interface BottleneckData {
  status: string
  msg: string
  color: string
  percentage: number
}

export interface SystemData {
  hardware: HardwareData
  cpu_data: CPUData
  gpu_data: GPUData
  score: number
  bottleneck: BottleneckData
}

export interface GameData {
  id: number
  name: string
  genre: string
  fps: number
  difficulty_multiplier?: number
}

export interface FPSParams {
  res: string
  preset: string
}

// Manual hardware catalog for the web demo's System Builder (no local WMI
// access, so hardware can't be auto-detected — the user picks from this list).
export interface HardwareLists {
  cpus: CPUData[]
  gpus: GPUData[]
}

export interface APIError {
  detail?: string
  error?: string
  message?: string
}
