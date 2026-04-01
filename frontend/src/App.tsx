import { useState, useEffect } from 'react'
import type { SystemData, GameData, FPSParams, APIError } from './types'
import { getTranslation, type Language } from './i18n'

function App() {
    const [activeTab, setActiveTab] = useState('dashboard')
    const [sysData, setSysData] = useState<SystemData | null>(null)
    const [games, setGames] = useState<GameData[]>([])
    const [fpsParams, setFpsParams] = useState<FPSParams>({ res: '1080p', preset: 'High' })
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [language, setLanguage] = useState<Language>('tr')
    const [upgrades, setUpgrades] = useState<{ cpu: string[], gpu: string[] }>({ cpu: [], gpu: [] })
    
    const t = getTranslation(language)

    useEffect(() => {
        fetchSystemData()
    }, [])

    const fetchSystemData = async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch('http://localhost:8000/api/system')
            if (!res.ok) {
                throw new Error(`Backend hatası: ${res.status}`)
            }
            const data: SystemData = await res.json()
            setSysData(data)
            await fetchGamesFPS(data.cpu_data.power_score, data.gpu_data.power_score, fpsParams.res, fpsParams.preset)
            await fetchUpgradeRecommendations(data.cpu_data.power_score, data.gpu_data.power_score, data.hardware.cpu, data.hardware.gpu)
        } catch (err) {
            const errorMsg = err instanceof Error ? err.message : 'Backend bağlantısı kurulamadı'
            setError(errorMsg)
            console.error("API Error: ", err)
        } finally {
            setLoading(false)
        }
    }

    const fetchUpgradeRecommendations = async (cpuScore: number, gpuScore: number, cpuName: string, gpuName: string) => {
        try {
            const response = await fetch('http://localhost:8000/api/upgrades', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    cpu_score: cpuScore, 
                    gpu_score: gpuScore,
                    cpu_name: cpuName,
                    gpu_name: gpuName
                })
            })
            if (response.ok) {
                const data = await response.json()
                setUpgrades(data)
            }
        } catch (err) {
            console.error("Upgrade recommendations error:", err)
        }
    }

    const fetchGamesFPS = async (cpuScore: number, gpuScore: number, res: string, preset: string) => {
        try {
            const response = await fetch('http://localhost:8000/api/games/fps', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ res, preset, cpu_score: cpuScore, gpu_score: gpuScore })
            })
            if (!response.ok) {
                throw new Error('FPS verileri alınamadı')
            }
            const data = await response.json()
            setGames(data.games || [])
        } catch (err) {
            console.error("FPS fetch error:", err)
        }
    }

    const handleFpsChange = (type: 'res' | 'preset', val: string) => {
        const newParams = { ...fpsParams, [type]: val }
        setFpsParams(newParams)
        if (sysData) {
            fetchGamesFPS(sysData.cpu_data.power_score, sysData.gpu_data.power_score, newParams.res, newParams.preset)
        }
    }

    return (
        <div className="flex h-screen bg-dark-900 text-gray-200 overflow-hidden">

            {/* Sidebar */}
            <div className="w-64 bg-dark-800 border-r border-gray-800 flex flex-col items-center py-8">
                <div className="flex items-center justify-between w-full px-4 mb-6">
                    <h1 className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple text-center glow-blue">
                        PERFORMANCE<br />HUB <span className="text-sm font-mono text-neon-teal">v2.0</span>
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
                        onClick={() => setActiveTab('dashboard')}
                        className={`py-3 px-4 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'dashboard' ? 'bg-neon-blue text-dark-900 shadow-[0_0_15px_rgba(102,252,241,0.5)]' : 'hover:bg-gray-800/50 text-gray-400 hover:text-white'}`}>
                        <span className="text-xl">📊</span> {t.dashboard}
                    </button>
                    <button
                        onClick={() => setActiveTab('games')}
                        className={`py-3 px-4 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'games' ? 'bg-neon-purple text-white shadow-[0_0_15px_rgba(176,38,255,0.5)]' : 'hover:bg-gray-800/50 text-gray-400 hover:text-white'}`}>
                        <span className="text-xl">🎮</span> {t.gameFps}
                    </button>
                    <button
                        onClick={() => setActiveTab('stress')}
                        className={`py-3 px-4 rounded-xl font-bold transition-all duration-300 flex items-center gap-3 ${activeTab === 'stress' ? 'bg-neon-brand text-white shadow-[0_0_15px_rgba(255,70,85,0.5)]' : 'hover:bg-gray-800/50 text-gray-400 hover:text-white'}`}>
                        <span className="text-xl">🔥</span> {t.stressTest}
                    </button>
                </nav>
            </div>

            {/* Main Content */}
            <div className="flex-1 p-10 overflow-y-auto">
                {error ? (
                    <div className="h-full flex flex-col items-center justify-center">
                        <div className="text-6xl mb-6">⚠️</div>
                        <h2 className="text-2xl font-bold text-red-400 mb-4">{t.connectionError}</h2>
                        <p className="text-gray-400 mb-6 text-center max-w-md">{error}</p>
                        <button 
                            onClick={fetchSystemData}
                            className="bg-neon-blue hover:bg-blue-600 text-dark-900 font-bold py-3 px-8 rounded-lg transition-all">
                            {t.retryButton}
                        </button>
                    </div>
                ) : loading ? (
                    <div className="h-full flex flex-col items-center justify-center">
                        <div className="w-16 h-16 border-4 border-neon-blue border-t-transparent rounded-full animate-spin glow-blue"></div>
                        <p className="mt-4 text-neon-blue font-mono animate-pulse">{t.scanningHardware}</p>
                    </div>
                ) : sysData ? (
                    <div className="max-w-5xl mx-auto animation-fade-in">

                        {activeTab === 'dashboard' && (
                            <div className="space-y-8">
                                <header>
                                    <h2 className="text-4xl font-black mb-2">{t.systemDashboard}</h2>
                                    <p className="text-gray-400 font-mono">{t.systemDashboardDesc}</p>
                                </header>

                                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                    <div className="bg-dark-800 p-6 rounded-2xl border border-gray-800/50 hover:border-neon-teal/50 transition-colors">
                                        <p className="text-neon-teal font-bold mb-2">{t.processor}</p>
                                        <p className="text-xl">{sysData.hardware.cpu}</p>
                                        <p className="text-sm text-gray-500 mt-2 font-mono">{t.score}: {sysData.cpu_data.power_score}/100</p>
                                    </div>
                                    <div className="bg-dark-800 p-6 rounded-2xl border border-gray-800/50 hover:border-neon-purple/50 transition-colors">
                                        <p className="text-neon-purple font-bold mb-2">{t.graphicsCard}</p>
                                        <p className="text-xl">{sysData.hardware.gpu}</p>
                                        <p className="text-sm text-gray-500 mt-2 font-mono">{t.score}: {sysData.gpu_data.power_score}/100</p>
                                    </div>
                                    <div className="bg-dark-800 p-6 rounded-2xl border border-gray-800/50 hover:border-neon-green/50 transition-colors">
                                        <p className="text-neon-green font-bold mb-2">{t.memory}</p>
                                        <p className="text-xl">{sysData.hardware.ram} GB DDR4/5</p>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    <div className="bg-gradient-to-br from-dark-800 to-gray-900 p-8 rounded-3xl border border-gray-800 flex flex-col items-center justify-center relative overflow-hidden">
                                        <div className="absolute top-0 right-0 w-32 h-32 bg-neon-blue/10 blur-[50px] rounded-full"></div>
                                        <p className="text-gray-400 font-bold mb-4 tracking-widest">{t.globalScore}</p>
                                        <div className="text-7xl font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-gray-400 drop-shadow-[0_0_10px_rgba(255,255,255,0.2)]">
                                            {sysData.score}
                                        </div>
                                        <div className="w-full bg-gray-800 rounded-full h-3 mt-8 overflow-hidden">
                                            <div className="bg-gradient-to-r from-neon-teal to-neon-blue h-3 rounded-full" style={{ width: `${sysData.score}%` }}></div>
                                        </div>
                                    </div>

                                    <div className={`bg-dark-800 p-8 rounded-3xl border-2 flex flex-col justify-center ${sysData.bottleneck.color === '#10B981' ? 'border-neon-green/30' : 'border-orange-500/30'}`}>
                                        <h3 className="text-xl font-bold mb-4" style={{ color: sysData.bottleneck.color }}>
                                            {sysData.bottleneck.status}
                                        </h3>
                                        <p className="text-gray-300 leading-relaxed text-lg">
                                            {sysData.bottleneck.msg}
                                        </p>
                                    </div>
                                </div>

                                {/* Upgrade Recommendations */}
                                {(upgrades.cpu.length > 0 || upgrades.gpu.length > 0) && (
                                    <div className="bg-dark-800 p-8 rounded-3xl border border-gray-800">
                                        <h3 className="text-2xl font-bold mb-6 text-neon-blue">{t.upgradeRecommendations}</h3>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                            {upgrades.cpu.length > 0 && (
                                                <div>
                                                    <p className="text-neon-teal font-bold mb-3">{t.recommendedCpu}</p>
                                                    {upgrades.cpu.map((cpu, idx) => (
                                                        <div key={idx} className="bg-dark-900 p-4 rounded-lg mb-2 border border-gray-700 hover:border-neon-teal/50 transition-colors">
                                                            <p className="text-white font-semibold">{cpu}</p>
                                                            {idx === 0 && <span className="text-xs text-neon-teal">⭐ {language === 'tr' ? 'En İyi Seçim' : 'Best Choice'}</span>}
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                            {upgrades.gpu.length > 0 && (
                                                <div>
                                                    <p className="text-neon-purple font-bold mb-3">{t.recommendedGpu}</p>
                                                    {upgrades.gpu.map((gpu, idx) => (
                                                        <div key={idx} className="bg-dark-900 p-4 rounded-lg mb-2 border border-gray-700 hover:border-neon-purple/50 transition-colors">
                                                            <p className="text-white font-semibold">{gpu}</p>
                                                            {idx === 0 && <span className="text-xs text-neon-purple">⭐ {language === 'tr' ? 'En İyi Seçim' : 'Best Choice'}</span>}
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}

                        {activeTab === 'games' && (
                            <div className="space-y-8">
                                <header>
                                    <h2 className="text-4xl font-black mb-2">{t.gameFpsEstimator}</h2>
                                    <p className="text-gray-400 font-mono">{t.gameFpsEstimatorDesc}</p>
                                </header>

                                <div className="bg-dark-800 p-6 rounded-2xl flex items-center gap-8 border border-gray-800">
                                    <div className="flex items-center gap-4">
                                        <span className="font-bold text-gray-400">{t.resolution}</span>
                                        <select
                                            className="bg-dark-900 border border-gray-700 text-white rounded-lg px-4 py-2 focus:border-neon-purple focus:ring-1 focus:ring-neon-purple outline-none"
                                            value={fpsParams.res} onChange={(e) => handleFpsChange('res', e.target.value)}>
                                            <option value="1080p">1080p (FHD)</option>
                                            <option value="1440p">1440p (QHD)</option>
                                            <option value="4k">4K (UHD)</option>
                                        </select>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <span className="font-bold text-gray-400">{t.quality}</span>
                                        <select
                                            className="bg-dark-900 border border-gray-700 text-white rounded-lg px-4 py-2 focus:border-neon-purple focus:ring-1 focus:ring-neon-purple outline-none"
                                            value={fpsParams.preset} onChange={(e) => handleFpsChange('preset', e.target.value)}>
                                            <option value="Low">{t.low}</option>
                                            <option value="Medium">{t.medium}</option>
                                            <option value="High">{t.high}</option>
                                            <option value="Ultra">{t.ultra}</option>
                                        </select>
                                    </div>
                                </div>

                                <div className="grid grid-cols-1 gap-4">
                                    {games.length === 0 ? (
                                        <div className="text-center py-10 text-gray-500">
                                            <p>{t.loadingGames}</p>
                                        </div>
                                    ) : (
                                        games.map(game => (
                                            <div key={game.id} className="bg-dark-800/50 hover:bg-dark-800 p-5 rounded-xl border border-gray-800/50 flex items-center justify-between transition-colors">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-12 h-12 bg-gray-900 rounded-lg flex items-center justify-center text-2xl">🎮</div>
                                                    <div>
                                                        <h4 className="text-xl font-bold">{game.name}</h4>
                                                        <p className="text-gray-500 text-sm font-mono">{game.genre}</p>
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

                        {activeTab === 'stress' && (
                            <div className="space-y-8 h-full flex flex-col justify-center items-center text-center">
                                <div className="w-32 h-32 rounded-full bg-neon-brand/20 flex items-center justify-center mb-6 animate-pulse">
                                    <span className="text-6xl">🔥</span>
                                </div>
                                <h2 className="text-4xl font-black text-white mb-4">{t.systemStressTest}</h2>
                                <p className="text-xl text-gray-400 max-w-lg">
                                    {t.stressTestDesc.replace('{cores}', sysData.hardware.cpu_cores?.toString() || 'available')}
                                </p>
                                <button className="mt-8 bg-neon-brand hover:bg-red-600 text-white font-black text-xl py-4 px-12 rounded-full shadow-[0_0_30px_rgba(255,70,85,0.6)] hover:shadow-[0_0_50px_rgba(255,70,85,0.8)] transition-all transform hover:scale-105">
                                    {t.igniteEngine}
                                </button>
                                <p className="text-orange-500 font-mono mt-8 border border-orange-500/30 p-4 rounded-lg bg-orange-500/10">
                                    {t.adminRequired}
                                </p>
                            </div>
                        )}

                    </div>
                ) : null}
            </div>
        </div>
    )
}

export default App
