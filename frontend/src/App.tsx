import { useState } from 'react'
import type { CPUData, GPUData, GameData, FPSParams } from './types'
import { getTranslation, type Language } from './i18n'
import { cpus, gpus, predictAll } from './engine/catalog'
import SystemBuilder from './SystemBuilder'

function App() {
    const [activeTab, setActiveTab] = useState<'builder' | 'games'>('builder')
    const [selectedCpu, setSelectedCpu] = useState<CPUData | null>(null)
    const [selectedGpu, setSelectedGpu] = useState<GPUData | null>(null)
    const [ramGb, setRamGb] = useState(16)
    const [fpsParams, setFpsParams] = useState<FPSParams>({ res: '1080p', preset: 'High' })
    const [games, setGames] = useState<GameData[]>([])
    const [language, setLanguage] = useState<Language>('tr')

    const t = getTranslation(language)

    // The engine and the catalogue are bundled into the page, so there is no
    // fetch, no loading state and no backend to be down. The prediction for all
    // 180 games takes single-digit milliseconds; scoring_engine.py stays the
    // source of truth and scripts/conformance_test.py proves the two agree.
    const handleCalculate = () => {
        if (!selectedCpu || !selectedGpu) return
        setGames(predictAll({
            cpu: selectedCpu,
            gpu: selectedGpu,
            ramGb,
            resolution: fpsParams.res,
            preset: fpsParams.preset,
        }))
        setActiveTab('games')
    }

    return (
        <div className="flex h-screen bg-dark-900 text-gray-200 overflow-hidden">

            {/* Sidebar */}
            <div className="w-64 bg-dark-800 border-r border-gray-800 flex flex-col items-center py-8">
                <div className="flex items-center justify-between w-full px-4 mb-6">
                    <h1 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple text-center glow-blue">
                        PERFORMANCE<br />HUB <span className="text-sm font-mono text-neon-teal">v5.1</span>
                    </h1>
                </div>

                {/* Language Switcher */}
                <div className="flex gap-2 mb-8 bg-dark-900 rounded-lg p-1">
                    <button
                        onClick={() => setLanguage('tr')}
                        className={`px-4 py-2 rounded-md font-bold transition-all ${language === 'tr' ? 'bg-neon-blue text-dark-900' : 'text-gray-400 hover:text-white'}`}>
                        🇹🇷 TR
                    </button>
                    <button
                        onClick={() => setLanguage('en')}
                        className={`px-4 py-2 rounded-md font-bold transition-all ${language === 'en' ? 'bg-neon-blue text-dark-900' : 'text-gray-400 hover:text-white'}`}>
                        🇬🇧 EN
                    </button>
                </div>

                <nav className="flex flex-col w-full px-4 gap-4">
                    <button
                        onClick={() => setActiveTab('builder')}
                        className={`py-3 px-4 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'builder' ? 'bg-neon-blue text-dark-900 shadow-[0_0_15px_rgba(102,252,241,0.5)]' : 'hover:bg-gray-800/50 text-gray-400 hover:text-white'}`}>
                        <span className="text-xl">🛠️</span> {t.navBuilder}
                    </button>
                    <button
                        onClick={() => setActiveTab('games')}
                        className={`py-3 px-4 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'games' ? 'bg-neon-purple text-white shadow-[0_0_15px_rgba(176,38,255,0.5)]' : 'hover:bg-gray-800/50 text-gray-400 hover:text-white'}`}>
                        <span className="text-xl">🎮</span> {t.navGameFps}
                    </button>
                </nav>
            </div>

            {/* Main Content */}
            <div className="flex-1 p-10 overflow-y-auto">
                    <div className="max-w-5xl mx-auto animation-fade-in">

                        {activeTab === 'builder' && (
                            <SystemBuilder
                                cpus={cpus}
                                gpus={gpus}
                                selectedCpu={selectedCpu}
                                selectedGpu={selectedGpu}
                                ramGb={ramGb}
                                fpsParams={fpsParams}
                                t={t}
                                onSelectCpu={setSelectedCpu}
                                onSelectGpu={setSelectedGpu}
                                onRamChange={setRamGb}
                                onFpsParamsChange={setFpsParams}
                                onCalculate={handleCalculate}
                            />
                        )}

                        {activeTab === 'games' && (
                            <div className="space-y-8">
                                <header className="flex items-center justify-between flex-wrap gap-4">
                                    <div>
                                        <h2 className="text-4xl font-black mb-2">{t.gameFpsEstimator}</h2>
                                        <p className="text-gray-400 font-mono">{t.gameFpsEstimatorDesc}</p>
                                    </div>
                                    <button
                                        onClick={() => setActiveTab('builder')}
                                        className="bg-dark-800 hover:bg-gray-800 border border-gray-700 text-gray-300 font-bold py-2 px-5 rounded-lg transition-all">
                                        🛠️ {t.editBuild}
                                    </button>
                                </header>

                                {selectedCpu && selectedGpu && (
                                    <div className="bg-dark-800 p-5 rounded-2xl border border-gray-800 font-mono text-sm text-gray-400">
                                        <span className="text-neon-teal">{t.currentBuild}:</span>{' '}
                                        {selectedCpu.name} + {selectedGpu.name} · {ramGb} GB RAM · {fpsParams.res} {fpsParams.preset}
                                    </div>
                                )}

                                <div className="grid grid-cols-1 gap-4">
                                    {games.length === 0 ? (
                                        <div className="text-center py-10 text-gray-500">
                                            <p>{t.noBuildYet}</p>
                                        </div>
                                    ) : (
                                        games.map(game => (
                                            <div key={game.id} className="bg-dark-800/50 hover:bg-dark-800 p-5 rounded-xl border border-gray-800/50 flex items-center justify-between transition-colors">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-12 h-12 bg-gray-900 rounded-lg flex items-center justify-center text-2xl">🎮</div>
                                                    <div>
                                                        <h4 className="text-xl font-bold">{game.name}</h4>
                                                        <div className="flex items-center gap-2">
                                                            <p className="text-gray-500 text-sm font-mono">{game.genre}</p>
                                                            {game.status && game.status !== 'ok' && (
                                                                <span
                                                                    title={game.warnings?.join('\n')}
                                                                    className={`text-xs font-bold px-2 py-0.5 rounded cursor-help ${
                                                                        game.status === 'unplayable'
                                                                            ? 'bg-neon-brand/20 text-neon-brand border border-neon-brand/40'
                                                                            : game.status === 'vram_spill'
                                                                            ? 'bg-orange-500/20 text-orange-400 border border-orange-500/40'
                                                                            : 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/30'
                                                                    }`}
                                                                >
                                                                    {game.status === 'unplayable' ? '🚫' : game.status === 'vram_spill' ? '⚠️' : '⚡'}
                                                                    {game.vram_needed_gb ? ` ${game.vram_needed_gb} GB VRAM` : ''}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    <div className={`text-4xl font-black ${game.fps >= 60 ? 'text-neon-green glow-green' : game.fps >= 30 ? 'text-orange-400' : 'text-neon-brand blur-none'}`}>
                                                        {game.fps} <span className="text-sm text-gray-500 font-normal">{t.fps}</span>
                                                    </div>
                                                </div>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>
                        )}

                    </div>
            </div>
        </div>
    )
}

export default App
