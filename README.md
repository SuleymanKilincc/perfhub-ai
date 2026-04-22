# 🚀 PerfHub AI

AI-powered hardware analysis and FPS prediction tool for PC gaming enthusiasts.

![Version](https://img.shields.io/badge/version-5.1.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## ✨ Features

### 🎮 Gaming & Performance
- 🔍 **Automatic Hardware Detection** - Detects CPU, GPU, RAM, and storage automatically with precise WMI cleaning for laptops
- 📊 **Performance Scoring** - Calculates system performance score (0-100)
- ⚠️ **Bottleneck Analysis** - Identifies CPU/GPU imbalances with recommendations
- 🎯 **Massive FPS Prediction Database** - Estimates FPS for **160+ popular games** across all presets
- 🌟 **Intelligent Upscaling Engine** - Accurately predicts DLSS, FSR, and XeSS performance. Warns if a game doesn't support the selected technology
- 💡 **Ray Tracing / Path Tracing** - Toggle RT/PT for supported games with realistic, calibrated performance impacts (-40% for RT, -55% for PT)
- 💾 **RAM Impact Analysis** - Game-specific RAM sensitivity with accurate FPS penalties

### 🤖 AI-Powered Features
- 🧠 **AI Assistant** - Powered by Groq Cloud (Llama 3.3 70B Versatile) for lightning-fast hardware consulting
- 🔬 **Hardware Analysis** - Detailed component analysis with AI-generated insights
- 💡 **Smart Recommendations** - AI suggests optimal hardware upgrades (filters out workstation/server components for gamers)
- 🌐 **Multi-Language** - Turkish & English support with AI responses in your language

### 🛠️ PC Building Tools
- 🖥️ **PC Builder & Compare Tool** - Build and test theoretical PC configurations and compare FPS across 160+ games
- 📈 **Upgrade Simulator** - Compare current vs. target system performance
- 🔌 **PSU Calculator** - Automatic power supply recommendations
- 🛒 **Dynamic Store Integration** - Compare prices instantly on Amazon, Trendyol, and Hepsiburada

### 🖥️ Hardware Support
- **170+ CPUs** - Intel, AMD, Apple Silicon (M1-M5)
- **144+ GPUs** - NVIDIA, AMD, Intel ARC + integrated graphics
- **Intel iGPU Support** - Proper detection and scoring for integrated graphics
- **Laptop Detection** - Accurate laptop vs desktop hardware differentiation

## 📦 Download

Download the latest version from [Releases](https://github.com/SuleymanKilincc/perfhub-ai/releases)

**Latest:** [PerfHub AI v5.1.0](https://github.com/SuleymanKilincc/perfhub-ai/releases/tag/v5.1.0) (64.50 MB)

## 🖥️ System Requirements

- **OS**: Windows 10/11 (64-bit)
- **RAM**: 4 GB minimum
- **Storage**: 150 MB free disk space
- **Internet**: Required for AI features

## 🚀 Quick Start

### Installation
1. Download `PerfHub_AI_v5.1.0.zip` from [Releases](https://github.com/SuleymanKilincc/perfhub-ai/releases/tag/v5.1.0)
2. Extract the ZIP file to any folder
3. Run `PerfHub_AI_WebApp.exe`
4. First launch may take 5-10 seconds (normal)
5. **No API key required** - AI works out of the box!

### Windows Security Warning
On first run, Windows may show an "Unknown publisher" warning:
1. Click **"More info"**
2. Click **"Run anyway"**

**Security Note**: This app is safe and open-source.  
🔒 **VirusTotal Scan**: Clean (Lütfen yayınladıktan sonra linki güncelleyin)

## 🎮 Supported Games (160+)

### Games with Ray Tracing + Path Tracing
- Cyberpunk 2077
- Alan Wake 2
- Portal RTX
- Minecraft RTX
- Quake II RTX
- Pragmata

### Games with Ray Tracing Only
- Spider-Man Remastered
- Hogwarts Legacy
- Forza Horizon 5
- F1 25 & F1 2024
- Resident Evil 4 Remake
- Control
- Metro Exodus Enhanced Edition
- Dying Light 2
- Watch Dogs Legion
- ...and dozens more!

### E-Sports & Competitive (Native Rendering)
- Valorant
- CS2 (Counter-Strike 2)
- Apex Legends
- Fortnite
- League of Legends
- Dota 2
- Overwatch 2

## 🛠️ Development

### Prerequisites

- Python 3.8+
- PyQt6
- Required packages (see `backend/requirements.txt`)

### Setup

```bash
# Clone the repository
git clone https://github.com/SuleymanKilincc/perfhub-ai.git
cd perfhub-ai

# Install dependencies
pip install -r backend/requirements.txt
pip install PyQt6 wmi psutil GPUtil openai python-dotenv

# Run the application
python modern_desktop_app.py
```

### Building EXE

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
python -m PyInstaller PerfHub_AI_WebApp.spec --noconfirm

# Output: dist/PerfHub_AI_WebApp.exe
```

### Creating Release ZIP

```bash
# Build EXE first, then create release ZIP
python create_release_zip.py

# Output: PerfHub_AI_v5.1.0.zip
```

## 📊 Database

- **170+ CPUs** - Intel (Core 5-14 Gen, Xeon), AMD (Ryzen 1000-9000, Threadripper), Apple Silicon (M1-M5)
- **144+ GPUs** - NVIDIA (GTX 700-RTX 5000), AMD (Polaris-RDNA 4), Intel ARC + iGPUs
- **160+ Games** - Complete RT/PT support data, DLSS/FSR/XeSS flags, and RAM sensitivity profiles
- **Accurate Scoring** - Real-world benchmarks and performance data

Database location: `data/hardware_db.sqlite`

## 🏗️ Architecture

```
perfhub-ai/
├── modern_desktop_app.py    # Main PyQt6 application
├── PerfHub_AI_WebApp.spec   # PyInstaller spec file
├── create_release_zip.py    # ZIP builder script
├── backend/                 # FastAPI backend (Web Version)
├── core/                    # Core modules
│   ├── hardware_detector.py # Hardware detection
│   ├── db_manager.py        # Database operations
│   ├── scoring_engine.py    # Performance scoring
│   └── ai_assistant.py      # AI integration
├── data/                    # Database
│   └── hardware_db.sqlite
├── frontend/                # React web interface (Web Version)
└── scripts/                 # Utility scripts
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨💻 Author

**Süleyman Kılınç**
- Website: [suleymankilinc.com](https://suleymankilinc.com)
- GitHub: [@SuleymanKilincc](https://github.com/SuleymanKilincc)

## 🙏 Acknowledgments

- Hardware data sourced from various benchmarking databases
- AI powered by Groq Cloud (Llama 3.3)
- Built with PyQt6, FastAPI, and React
- RT/PT support data from game documentation

## 📸 Screenshots

### Dashboard
![Dashboard](screenshots/dashboard.png)

### FPS Prediction
![FPS Prediction](screenshots/results.png)
