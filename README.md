# 🚀 PerfHub AI

AI-powered hardware analysis and FPS prediction tool for PC gaming enthusiasts.

![Version](https://img.shields.io/badge/version-4.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## ✨ Features

### 🎮 Gaming & Performance
- 🔍 **Automatic Hardware Detection** - Detects CPU, GPU, RAM, and storage automatically
- 📊 **Performance Scoring** - Calculates system performance score (0-100)
- ⚠️ **Bottleneck Analysis** - Identifies CPU/GPU imbalances with recommendations
- 🎯 **FPS Prediction** - Estimates FPS for 32+ popular games across all presets
- 🌟 **Ray Tracing / Path Tracing** - Toggle RT/PT for supported games with realistic performance impact
- 💾 **RAM Impact Analysis** - Game-specific RAM sensitivity (4GB-128GB) with accurate FPS penalties

### 🤖 AI-Powered Features
- 🧠 **AI Assistant** - Powered by Google Gemini 2.5 Flash (no API key needed!)
- 🔬 **Hardware Analysis** - Detailed component analysis with AI-generated insights
- 💡 **Smart Recommendations** - AI suggests optimal hardware upgrades
- 🌐 **Multi-Language** - Turkish & English support with AI responses in your language

### 🛠️ PC Building Tools
- 🖥️ **PC Builder** - Build and test theoretical PC configurations
- 📈 **Upgrade Simulator** - Compare current vs. target system performance
- 🔌 **PSU Calculator** - Automatic power supply recommendations
- 💰 **Price/Performance** - Smart hardware value analysis

### 🖥️ Hardware Support
- **156+ CPUs** - Intel, AMD, Apple Silicon (M1-M5)
- **137+ GPUs** - NVIDIA, AMD, Intel ARC + integrated graphics
- **Intel iGPU Support** - Proper detection and scoring for integrated graphics
- **Laptop Detection** - Accurate laptop vs desktop hardware differentiation

## 📦 Download

Download the latest version from [Releases](https://github.com/SuleymanKilincc/perfhub-ai/releases)

**Latest:** [PerfHub AI v4.0.0](https://github.com/SuleymanKilincc/perfhub-ai/releases/tag/v4.0.0) (52.77 MB)

## 🖥️ System Requirements

- **OS**: Windows 10/11 (64-bit)
- **RAM**: 4 GB minimum
- **Storage**: 100 MB free disk space
- **Internet**: Required for AI features

## 🚀 Quick Start

### Installation
1. Download `PerfHub_AI_v4.0.0.zip` from [Releases](https://github.com/SuleymanKilincc/perfhub-ai/releases/tag/v4.0.0)
2. Extract the ZIP file to any folder
3. Run `PerfHub_AI_WebApp.exe`
4. First launch may take 5-10 seconds (normal)
5. **No API key required** - AI works out of the box!

### Windows Security Warning
On first run, Windows may show a "Unknown publisher" warning:
1. Click **"More info"**
2. Click **"Run anyway"**

**Security Note**: This app is safe and open-source.  
🔒 **VirusTotal Scan**: [68/70 clean](https://www.virustotal.com/gui/file/6e43f2c8ef3efc586f752222c554046ff1ae204a114bfc947749da2fb346842d/detection) (2 false positives - common for PyInstaller apps)

## 🎮 Supported Games

### Games with Ray Tracing + Path Tracing
- Cyberpunk 2077
- Alan Wake 2
- Portal RTX
- Minecraft RTX
- Quake II RTX

### Games with Ray Tracing Only
- Spider-Man Remastered
- Hogwarts Legacy
- Forza Horizon 5
- F1 2024
- Resident Evil 4 Remake
- Control
- Metro Exodus Enhanced Edition
- Dying Light 2
- Watch Dogs Legion
- Shadow of the Tomb Raider
- ...and 22 more!

### Competitive Games (Low RAM Impact)
- Valorant
- CS:GO 2
- Apex Legends
- Fortnite
- League of Legends
- Overwatch 2

### RAM-Intensive Games
- Cities Skylines 2 (1.8x RAM impact)
- Microsoft Flight Simulator (1.7x)
- Hogwarts Legacy (1.6x)
- Cyberpunk 2077 (1.3x)

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
pip install PyQt6 wmi psutil GPUtil google-genai

# Run the application
python modern_desktop_app.py
```

### Building EXE

```bash
# Install PyInstaller
pip install pyinstaller

# Build the executable
python build_web_app_exe.py

# Output: dist/PerfHub_AI_WebApp.exe
```

### Creating Release ZIP

```bash
# Build EXE first, then create release ZIP
python create_release_zip.py

# Output: PerfHub_AI_v4.0.0.zip
```

## 📊 Database

- **156+ CPUs** - Intel (Core, Xeon), AMD (Ryzen, Threadripper), Apple Silicon (M1-M5)
- **137+ GPUs** - NVIDIA (RTX 50/40/30/20 series), AMD (RX 7000/6000), Intel ARC + iGPUs
- **32 Games** - Complete RT/PT support data and RAM sensitivity profiles
- **Accurate Scoring** - Real-world benchmarks and performance data

Database location: `data/hardware_db.sqlite`

### Intel iGPU Models Supported
- Intel Iris Xe Graphics (18 score)
- Intel Iris Xe Graphics G7 (20 score)
- Intel Iris Plus Graphics (15 score)
- Intel UHD Graphics 770 (12 score)
- Intel UHD Graphics 730 (10 score)
- Intel UHD Graphics 630 (8 score)

## 🏗️ Architecture

```
perfhub-ai/
├── modern_desktop_app.py    # Main PyQt6 application
├── build_web_app_exe.py     # EXE builder script
├── backend/                 # FastAPI backend
│   ├── main.py
│   └── requirements.txt
├── core/                    # Core modules
│   ├── hardware_detector.py # Hardware detection
│   ├── db_manager.py        # Database operations
│   ├── scoring_engine.py    # Performance scoring
│   └── ai_assistant.py      # AI integration
├── data/                    # Database
│   └── hardware_db.sqlite
├── frontend/                # React web interface
└── scripts/                 # Utility scripts
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Süleyman Kılınç**
- Website: [suleymankilinc.com](https://suleymankilinc.com)
- GitHub: [@SuleymanKilincc](https://github.com/SuleymanKilincc)

## 🙏 Acknowledgments

- Hardware data sourced from various benchmarking databases
- AI powered by Google Gemini 2.5 Flash
- Built with PyQt6, FastAPI, and React
- RT/PT support data from game documentation

## 📸 Screenshots

### Dashboard
![Dashboard](https://via.placeholder.com/800x500?text=Dashboard+Screenshot)

### FPS Prediction
![FPS Prediction](https://via.placeholder.com/800x500?text=FPS+Prediction+Screenshot)

### PC Builder
![PC Builder](https://via.placeholder.com/800x500?text=PC+Builder+Screenshot)

---

⭐ Star this repo if you find it useful!
