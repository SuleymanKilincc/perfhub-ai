# 🚀 PerfHub AI v4.0.0 - Release Notes

## 🎉 Major Release: AI-Powered Hardware Analysis

PerfHub AI v4.0.0 brings powerful new features including Gemini AI integration, Ray Tracing/Path Tracing support, and enhanced hardware detection.

---

## ✨ New Features

### 🤖 AI Assistant (Gemini 2.5 Flash)
- **Embedded API Key** - No user configuration needed
- **Hardware Analysis** - AI-powered CPU/GPU recommendations
- **General Chat** - Ask questions about PC building
- **Multi-Language** - Turkish & English support

### 🌟 Ray Tracing / Path Tracing Support
- **32 Games** with RT/PT data
- **Performance Toggles** - Enable/disable RT or PT per game
- **Realistic FPS Impact** - RT: -40% FPS, PT: -65% FPS
- **Game-Specific Support** - Auto-detects which games support RT/PT

### 💾 RAM Selector & Impact
- **Selectable RAM** - 4GB, 8GB, 16GB, 32GB, 64GB, 128GB
- **Game-Specific Sensitivity** - Different games affected differently
  - Cities Skylines 2: 1.8x RAM impact
  - Microsoft Flight Simulator: 1.7x
  - Cyberpunk 2077: 1.3x
  - Valorant/CS:GO: 0.7x (low impact)
- **Realistic Penalties** - 4GB: -65% FPS, 8GB: -12-22% FPS

### 🖥️ Intel iGPU Support
- **6 New Models Added**:
  - Intel Iris Xe Graphics (18 score)
  - Intel UHD Graphics 770 (12 score)
  - Intel UHD Graphics 730 (10 score)
  - Intel UHD Graphics 630 (8 score)
  - Intel Iris Xe Graphics G7 (20 score)
  - Intel Iris Plus Graphics (15 score)

### 🌐 Global Language Selector
- **Sidebar Language Picker** - 🇹🇷 Türkçe / 🇬🇧 English
- **AI Responses** - Language affects all AI interactions
- **Persistent Selection** - Remembers your choice

### 🎨 Application Icon
- **Custom Logo** - PerfHub AI branding
- **Taskbar Icon** - Professional appearance
- **Window Icon** - Consistent branding

---

## 🔧 Improvements

### Updated Google AI SDK
- Migrated from `google-generativeai` to `google.genai`
- Model: `gemini-2.5-flash` (faster, more accurate)
- Better error handling

### Enhanced UI/UX
- **Larger Fonts** - RT/PT support text now 13px bold
- **Better Readability** - Improved contrast and spacing
- **Responsive Design** - Smoother animations

### Database Expansion
- **156+ CPUs** - Intel, AMD, Apple Silicon
- **137+ GPUs** - NVIDIA, AMD, Intel ARC + iGPUs
- **32 Games** - RT/PT support + RAM sensitivity data

---

## 📦 Download & Installation

### System Requirements
- Windows 10/11 (64-bit)
- 100 MB free disk space
- Internet connection (for AI features)

### Installation Steps
1. Download `PerfHub_AI_v4.0.0.zip` (52.77 MB)
2. Extract the ZIP file
3. Run `PerfHub_AI_WebApp.exe`
4. First launch may take 5-10 seconds

### Windows Security Warning
On first run, Windows may show "Unknown publisher":
1. Click **"More info"**
2. Click **"Run anyway"**

---

## 🛡️ Security & Trust

### VirusTotal Scan Results
- **68/70 Clean** ✅
- 2 false positives (VIPRE, CrowdStrike) - common for PyInstaller apps
- **Scan Report**: [View on VirusTotal](https://www.virustotal.com/gui/file/6e43f2c8ef3efc586f752222c554046ff1ae204a114bfc947749da2fb346842d/detection)

### Open Source
- Full source code available on GitHub
- MIT License - free to use and modify
- Community-driven development

---

## 🎮 Supported Games (RT/PT)

### Ray Tracing + Path Tracing
- Cyberpunk 2077
- Alan Wake 2
- Portal RTX
- Minecraft RTX
- Quake II RTX

### Ray Tracing Only
- Spider-Man Remastered
- Hogwarts Legacy
- Forza Horizon 5
- F1 2024
- Resident Evil 4 Remake
- Control
- Metro Exodus Enhanced
- Dying Light 2
- Watch Dogs Legion
- ...and more!

---

## 🐛 Bug Fixes

- Fixed API key detection issues
- Resolved iGPU scoring (was showing 0)
- Fixed RAM impact not affecting FPS
- Corrected language selector placement
- Fixed icon not appearing in taskbar

---

## 📝 Technical Details

### Build Information
- **Version**: 4.0.0
- **Build Date**: April 3, 2026
- **File Size**: 52.77 MB (ZIP)
- **Python**: 3.8+
- **Framework**: PyQt6

### API Integration
- **AI Model**: Google Gemini 2.5 Flash
- **API Key**: Embedded (no user setup required)
- **Rate Limits**: Generous free tier

---

## 🙏 Acknowledgments

- Hardware data from various benchmarking databases
- AI powered by Google Gemini 2.5 Flash
- RT/PT support data from game documentation
- Community feedback and testing

---

## 📞 Support

- **GitHub Issues**: [Report bugs](https://github.com/SuleymanKilincc/perfhub-ai/issues)
- **Website**: [suleymankilinc.com](https://suleymankilinc.com)
- **Email**: Contact via GitHub

---

## 🔮 What's Next?

### Planned for v4.1.0
- More games with RT/PT support
- DLSS 4 Multi Frame Generation
- AMD FSR 3.1 support
- Laptop vs Desktop GPU comparison
- Power consumption estimates

---

⭐ **Star this repo if you find it useful!**

---

**Full Changelog**: [v3.0...v4.0.0](https://github.com/SuleymanKilincc/perfhub-ai/compare/v3.0...v4.0.0)
