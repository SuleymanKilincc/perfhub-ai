// Internationalization (i18n) support

export type Language = 'tr' | 'en'

export interface Translations {
  // Navigation
  navBuilder: string
  navGameFps: string

  // System Builder
  builderTitle: string
  builderDesc: string
  selectCpu: string
  selectGpu: string
  selectRam: string
  cpuPlaceholder: string
  gpuPlaceholder: string
  resolution: string
  quality: string
  low: string
  medium: string
  high: string
  ultra: string
  calculateFps: string
  calculating: string
  builderIncomplete: string

  // Game FPS
  gameFpsEstimator: string
  gameFpsEstimatorDesc: string
  currentBuild: string
  editBuild: string

  // Loading & Errors
  loadingHardware: string
  connectionError: string
  retryButton: string
  loadingGames: string
  noBuildYet: string

  // Common
  fps: string
}

export const translations: Record<Language, Translations> = {
  tr: {
    // Navigation
    navBuilder: 'Sistem Kur',
    navGameFps: 'Oyun FPS',

    // System Builder
    builderTitle: 'SİSTEM KUR',
    builderDesc: 'CPU, GPU ve RAM seçerek hayalindeki (veya mevcut) sistemin FPS tahminini gör.',
    selectCpu: 'İşlemci',
    selectGpu: 'Ekran Kartı',
    selectRam: 'RAM',
    cpuPlaceholder: '-- İşlemci seçin --',
    gpuPlaceholder: '-- Ekran kartı seçin --',
    resolution: 'ÇÖZÜNÜRLÜK',
    quality: 'KALİTE',
    low: 'Düşük',
    medium: 'Orta',
    high: 'Yüksek',
    ultra: 'Ultra',
    calculateFps: 'FPS Hesapla',
    calculating: 'Hesaplanıyor...',
    builderIncomplete: 'Devam etmek için bir işlemci ve ekran kartı seçin.',

    // Game FPS
    gameFpsEstimator: 'OYUN FPS TAHMİNCİSİ',
    gameFpsEstimatorDesc: 'Seçtiğin donanıma göre kare hızı tahminleri.',
    currentBuild: 'Seçili Sistem',
    editBuild: 'Sistemi Değiştir',

    // Loading & Errors
    loadingHardware: 'Donanım listesi yükleniyor...',
    connectionError: 'Bağlantı Hatası',
    retryButton: 'Tekrar Dene',
    loadingGames: 'Oyun verileri yükleniyor...',
    noBuildYet: 'Henüz bir sistem hesaplanmadı. Önce "Sistem Kur" sayfasından bir işlemci ve ekran kartı seç.',

    // Common
    fps: 'FPS',
  },

  en: {
    // Navigation
    navBuilder: 'Build System',
    navGameFps: 'Game FPS',

    // System Builder
    builderTitle: 'BUILD YOUR SYSTEM',
    builderDesc: 'Pick a CPU, GPU, and RAM to see FPS estimates for your dream (or current) system.',
    selectCpu: 'Processor',
    selectGpu: 'Graphics Card',
    selectRam: 'RAM',
    cpuPlaceholder: '-- Select a CPU --',
    gpuPlaceholder: '-- Select a GPU --',
    resolution: 'RESOLUTION',
    quality: 'QUALITY',
    low: 'Low',
    medium: 'Medium',
    high: 'High',
    ultra: 'Ultra',
    calculateFps: 'Calculate FPS',
    calculating: 'Calculating...',
    builderIncomplete: 'Select a CPU and GPU to continue.',

    // Game FPS
    gameFpsEstimator: 'GAME FPS ESTIMATOR',
    gameFpsEstimatorDesc: 'Frame rate predictions based on the hardware you picked.',
    currentBuild: 'Current Build',
    editBuild: 'Edit Build',

    // Loading & Errors
    loadingHardware: 'Loading hardware list...',
    connectionError: 'Connection Error',
    retryButton: 'Retry',
    loadingGames: 'Loading game data...',
    noBuildYet: 'No build calculated yet. Pick a CPU and GPU on the "Build System" page first.',

    // Common
    fps: 'FPS',
  }
}

export function getTranslation(lang: Language): Translations {
  return translations[lang]
}
