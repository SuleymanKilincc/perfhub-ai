// Internationalization (i18n) support

export type Language = 'tr' | 'en'

export interface Translations {
  // Navigation
  dashboard: string
  gameFps: string
  stressTest: string
  
  // Dashboard
  systemDashboard: string
  systemDashboardDesc: string
  processor: string
  graphicsCard: string
  memory: string
  score: string
  globalScore: string
  bottleneckAnalysis: string
  
  // Bottleneck messages
  perfectBalance: string
  perfectBalanceMsg: string
  cpuBottleneck: string
  cpuBottleneckMsg: string
  gpuBottleneck: string
  gpuBottleneckMsg: string
  
  // Upgrade recommendations
  upgradeRecommendations: string
  recommendedCpu: string
  recommendedGpu: string
  alternatives: string
  
  // Game FPS
  gameFpsEstimator: string
  gameFpsEstimatorDesc: string
  resolution: string
  quality: string
  low: string
  medium: string
  high: string
  ultra: string
  
  // Stress Test
  systemStressTest: string
  stressTestDesc: string
  igniteEngine: string
  adminRequired: string
  
  // Loading & Errors
  scanningHardware: string
  connectionError: string
  retryButton: string
  loadingGames: string
  
  // Common
  fps: string
  cores: string
}

export const translations: Record<Language, Translations> = {
  tr: {
    // Navigation
    dashboard: 'Dashboard',
    gameFps: 'Oyun FPS',
    stressTest: 'Stres Testi',
    
    // Dashboard
    systemDashboard: 'SİSTEM DASHBOARD',
    systemDashboardDesc: 'Gerçek zamanlı donanım analizi ve puanlama.',
    processor: 'İŞLEMCİ',
    graphicsCard: 'EKRAN KARTI',
    memory: 'BELLEK',
    score: 'Puan',
    globalScore: 'GENEL PUAN',
    bottleneckAnalysis: 'DARBOĞAZ ANALİZİ',
    
    // Bottleneck
    perfectBalance: '✅ MÜKEMMEL DENGE',
    perfectBalanceMsg: 'CPU ve GPU mükemmel eşleşiyor. Darboğaz minimumdur.',
    cpuBottleneck: 'CPU DARBOĞAZI',
    cpuBottleneckMsg: 'İşlemciniz ekran kartınızın gerisinde kalıyor. CPU yükseltmeyi düşünün.',
    gpuBottleneck: 'GPU DARBOĞAZI',
    gpuBottleneckMsg: 'Ekran kartınız üst düzey işlemcinizin önünü kesiyor. GPU yükseltmeyi düşünün.',
    
    // Upgrade
    upgradeRecommendations: 'YÜKSELTİM ÖNERİLERİ',
    recommendedCpu: 'Önerilen İşlemciler',
    recommendedGpu: 'Önerilen Ekran Kartları',
    alternatives: 'Alternatifler',
    
    // Game FPS
    gameFpsEstimator: 'OYUN FPS TAHMİNCİSİ',
    gameFpsEstimatorDesc: 'Donanımınıza göre AI destekli kare hızı tahminleri.',
    resolution: 'ÇÖZÜNÜRLÜK',
    quality: 'KALİTE',
    low: 'Düşük',
    medium: 'Orta',
    high: 'Yüksek',
    ultra: 'Ultra',
    
    // Stress Test
    systemStressTest: 'SİSTEM STRES TESTİ',
    stressTestDesc: 'C++ Donanım Motoru tüm CPU çekirdeklerini maksimuma çıkararak termal limitleri ve kararlılığı test eder.',
    igniteEngine: 'MOTORU ATEŞLE',
    adminRequired: 'Sıcaklık izleme için yönetici yetkileri gereklidir.',
    
    // Loading & Errors
    scanningHardware: 'Donanım taranıyor...',
    connectionError: 'Bağlantı Hatası',
    retryButton: 'Tekrar Dene',
    loadingGames: 'Oyun verileri yükleniyor...',
    
    // Common
    fps: 'FPS',
    cores: 'çekirdek',
  },
  
  en: {
    // Navigation
    dashboard: 'Dashboard',
    gameFps: 'Game FPS',
    stressTest: 'Stress Test',
    
    // Dashboard
    systemDashboard: 'SYSTEM DASHBOARD',
    systemDashboardDesc: 'Real-time hardware analysis and scoring.',
    processor: 'PROCESSOR',
    graphicsCard: 'GRAPHICS CARD',
    memory: 'MEMORY',
    score: 'Score',
    globalScore: 'GLOBAL SCORE',
    bottleneckAnalysis: 'BOTTLENECK ANALYSIS',
    
    // Bottleneck
    perfectBalance: '✅ PERFECT BALANCE',
    perfectBalanceMsg: 'CPU and GPU are perfectly matched. Bottleneck is minimal.',
    cpuBottleneck: 'CPU BOTTLENECK',
    cpuBottleneckMsg: 'Your processor is holding back your graphics card. Consider a CPU upgrade.',
    gpuBottleneck: 'GPU BOTTLENECK',
    gpuBottleneckMsg: 'Your graphics card is limiting your high-end processor. Consider a GPU upgrade.',
    
    // Upgrade
    upgradeRecommendations: 'UPGRADE RECOMMENDATIONS',
    recommendedCpu: 'Recommended CPUs',
    recommendedGpu: 'Recommended GPUs',
    alternatives: 'Alternatives',
    
    // Game FPS
    gameFpsEstimator: 'GAME FPS ESTIMATOR',
    gameFpsEstimatorDesc: 'AI-driven frame rate predictions based on your hardware.',
    resolution: 'RESOLUTION',
    quality: 'QUALITY',
    low: 'Low',
    medium: 'Medium',
    high: 'High',
    ultra: 'Ultra',
    
    // Stress Test
    systemStressTest: 'SYSTEM STRESS TEST',
    stressTestDesc: 'The C++ Hardware Engine will max out all CPU cores to test thermal limits and stability.',
    igniteEngine: 'IGNITE ENGINE',
    adminRequired: 'Admin privileges required for temperature monitoring.',
    
    // Loading & Errors
    scanningHardware: 'Scanning hardware...',
    connectionError: 'Connection Error',
    retryButton: 'Retry',
    loadingGames: 'Loading game data...',
    
    // Common
    fps: 'FPS',
    cores: 'cores',
  }
}

export function getTranslation(lang: Language): Translations {
  return translations[lang]
}
