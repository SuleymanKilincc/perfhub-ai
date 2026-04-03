# 🚀 PerfHub AI

AI-powered hardware analysis and FPS prediction tool for PC gaming enthusiasts.

![Version](https://img.shields.io/badge/version-4.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

## ✨ Features

- 🔍 **Automatic Hardware Detection** - Detects CPU, GPU, RAM, and storage automatically
- 📊 **Performance Scoring** - Calculates system performance score (0-100)
- ⚠️ **Bottleneck Analysis** - Identifies CPU/GPU imbalances
- 🎮 **FPS Prediction** - Estimates FPS for 32+ popular games with RT/PT support
- 🌟 **Ray Tracing / Path Tracing** - Toggle RT/PT for supported games
- 💾 **RAM Impact** - Game-specific RAM sensitivity (4GB-128GB)
- 🛠️ **PC Builder** - Build and test theoretical PC configurations
- 🤖 **AI Assistant** - Powered by Google Gemini 2.5 Flash
- 🔬 **Hardware Analysis** - Detailed component analysis with AI insights
- 🌐 **Multi-Language** - Turkish & English support
- 🖥️ **Intel iGPU Support** - Integrated graphics detection

## 📦 Download

Download the latest version from [Releases](https://github.com/SuleymanKilincc/perfhub-ai/releases)

**Latest:** [PerfHub AI v4.0.0](https://github.com/SuleymanKilincc/perfhub-ai/releases/download/v4.0.0/PerfHub_AI_v4.0.0.zip) (52.77 MB)

## 🖥️ System Requirements

- Windows 10/11 (64-bit)
- 4 GB RAM
- 100 MB free disk space

## 🚀 Quick Start

1. Download `PerfHub_AI_v4.0.0.zip` from [Releases](https://github.com/SuleymanKilincc/perfhub-ai/releases)
2. Extract the ZIP file
3. Run `PerfHub_AI_WebApp.exe`
4. First launch may take 5-10 seconds (normal)
5. No API key required - AI works out of the box!

## ⚠️ Windows Security Warning

On first run, Windows may show a "Unknown publisher" warning:
1. Click **"More info"**
2. Click **"Run anyway"**

**Security:** This app is safe and open-source. VirusTotal scan: [68/70 clean](https://www.virustotal.com/gui/file/6e43f2c8ef3efc586f752222c554046ff1ae204a114bfc947749da2fb346842d/detection)

## 🛠️ Development

### Prerequisites

- Python 3.8+
- PyQt6
- Required packages (see `backend/requirements.txt`)

### Setup

```bash
# Clone the repository
git clone https://github.com/KULLANICIADI/perfhub-ai.git
cd perfhub-ai

# Install dependencies
pip install -r backend/requirements.txt
pip install PyQt6 wmi psutil GPUtil

# Run the application
python modern_desktop_app.py
```

### Building EXE

```bash
# Install PyInstaller
pip install pyinstaller

# Build
python build_web_app_exe.py

# Output: dist/PerfHub_AI_WebApp.exe
```

## 📊 Database

- **156+ CPUs** (Intel, AMD, Apple Silicon)
- **137+ GPUs** (NVIDIA, AMD, Intel ARC + iGPUs)
- **32 Games** with RT/PT support and RAM sensitivity data

Database location: `data/hardware_db.sqlite`

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
