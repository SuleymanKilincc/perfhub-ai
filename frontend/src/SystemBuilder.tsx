import type { CPUData, GPUData, FPSParams } from './types'
import type { Translations } from './i18n'

const RAM_OPTIONS_GB = [4, 8, 16, 32, 64, 128]

interface SystemBuilderProps {
  cpus: CPUData[]
  gpus: GPUData[]
  selectedCpu: CPUData | null
  selectedGpu: GPUData | null
  ramGb: number
  fpsParams: FPSParams
  calculating: boolean
  t: Translations
  onSelectCpu: (cpu: CPUData | null) => void
  onSelectGpu: (gpu: GPUData | null) => void
  onRamChange: (ramGb: number) => void
  onFpsParamsChange: (params: FPSParams) => void
  onCalculate: () => void
}

function SystemBuilder({
  cpus, gpus, selectedCpu, selectedGpu, ramGb, fpsParams, calculating, t,
  onSelectCpu, onSelectGpu, onRamChange, onFpsParamsChange, onCalculate,
}: SystemBuilderProps) {
  const canCalculate = !!selectedCpu && !!selectedGpu && !calculating

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      <header>
        <h2 className="text-4xl font-black mb-2">{t.builderTitle}</h2>
        <p className="text-gray-400 font-mono">{t.builderDesc}</p>
      </header>

      <div className="bg-dark-800 p-8 rounded-3xl border border-gray-800 space-y-6">
        {/* CPU */}
        <div>
          <label className="block text-neon-teal font-bold mb-2">{t.selectCpu}</label>
          <select
            className="w-full bg-dark-900 border border-gray-700 text-white rounded-lg px-4 py-3 focus:border-neon-teal focus:ring-1 focus:ring-neon-teal outline-none"
            value={selectedCpu?.name ?? ''}
            onChange={(e) => onSelectCpu(cpus.find((c) => c.name === e.target.value) ?? null)}
          >
            <option value="">{t.cpuPlaceholder}</option>
            {cpus.map((cpu) => (
              <option key={cpu.name} value={cpu.name}>
                {cpu.name} ({cpu.power_score.toFixed(0)})
              </option>
            ))}
          </select>
        </div>

        {/* GPU */}
        <div>
          <label className="block text-neon-purple font-bold mb-2">{t.selectGpu}</label>
          <select
            className="w-full bg-dark-900 border border-gray-700 text-white rounded-lg px-4 py-3 focus:border-neon-purple focus:ring-1 focus:ring-neon-purple outline-none"
            value={selectedGpu?.name ?? ''}
            onChange={(e) => onSelectGpu(gpus.find((g) => g.name === e.target.value) ?? null)}
          >
            <option value="">{t.gpuPlaceholder}</option>
            {gpus.map((gpu) => (
              <option key={gpu.name} value={gpu.name}>
                {gpu.name} ({gpu.power_score.toFixed(0)}{gpu.vram ? `, ${gpu.vram}GB` : ''})
              </option>
            ))}
          </select>
        </div>

        {/* RAM / Resolution / Quality */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="block text-neon-green font-bold mb-2">{t.selectRam}</label>
            <select
              className="w-full bg-dark-900 border border-gray-700 text-white rounded-lg px-4 py-3 focus:border-neon-green focus:ring-1 focus:ring-neon-green outline-none"
              value={ramGb}
              onChange={(e) => onRamChange(Number(e.target.value))}
            >
              {RAM_OPTIONS_GB.map((gb) => (
                <option key={gb} value={gb}>{gb} GB</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-gray-400 font-bold mb-2">{t.resolution}</label>
            <select
              className="w-full bg-dark-900 border border-gray-700 text-white rounded-lg px-4 py-3 focus:border-neon-blue focus:ring-1 focus:ring-neon-blue outline-none"
              value={fpsParams.res}
              onChange={(e) => onFpsParamsChange({ ...fpsParams, res: e.target.value })}
            >
              <option value="1080p">1080p (FHD)</option>
              <option value="1440p">1440p (QHD)</option>
              <option value="4k">4K (UHD)</option>
            </select>
          </div>

          <div>
            <label className="block text-gray-400 font-bold mb-2">{t.quality}</label>
            <select
              className="w-full bg-dark-900 border border-gray-700 text-white rounded-lg px-4 py-3 focus:border-neon-blue focus:ring-1 focus:ring-neon-blue outline-none"
              value={fpsParams.preset}
              onChange={(e) => onFpsParamsChange({ ...fpsParams, preset: e.target.value })}
            >
              <option value="Low">{t.low}</option>
              <option value="Medium">{t.medium}</option>
              <option value="High">{t.high}</option>
              <option value="Ultra">{t.ultra}</option>
            </select>
          </div>
        </div>

        <button
          onClick={onCalculate}
          disabled={!canCalculate}
          className={`w-full font-black text-xl py-4 rounded-xl transition-all ${
            canCalculate
              ? 'bg-neon-blue hover:bg-blue-600 text-dark-900 shadow-[0_0_25px_rgba(102,252,241,0.4)]'
              : 'bg-gray-800 text-gray-600 cursor-not-allowed'
          }`}
        >
          {calculating ? t.calculating : t.calculateFps}
        </button>

        {!selectedCpu || !selectedGpu ? (
          <p className="text-center text-gray-500 font-mono text-sm">{t.builderIncomplete}</p>
        ) : null}
      </div>
    </div>
  )
}

export default SystemBuilder
