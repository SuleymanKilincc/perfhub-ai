"""
PerfHub AI - Web App EXE Builder
modern_desktop_app.py'yi EXE yapar (PyQt6 uygulaması)
"""
import os
import sys
import subprocess

print("="*60)
print("PerfHub AI - Web App EXE Builder")
print("modern_desktop_app.py → EXE")
print("="*60)
print()

# Check PyInstaller
try:
    import PyInstaller
    print("✓ PyInstaller bulundu")
except ImportError:
    print("❌ PyInstaller bulunamadı!")
    print("Kurulum: pip install pyinstaller")
    sys.exit(1)

# Check PyQt6
try:
    import PyQt6
    print("✓ PyQt6 bulundu")
except ImportError:
    print("❌ PyQt6 bulunamadı!")
    print("Kurulum: pip install PyQt6")
    sys.exit(1)

# Build command
cmd = [
    "python", "-m", "PyInstaller",
    "--onefile",                    # Tek dosya
    "--windowed",                   # Console gizle
    "--name=PerfHub_AI_WebApp",    # Exe adı
    "--add-data=data;data",        # Database dahil et
    "--add-data=backend;backend",  # Backend dahil et
    "--hidden-import=core.hardware_detector",
    "--hidden-import=core.db_manager",
    "--hidden-import=core.scoring_engine",
    "--hidden-import=core.ai_assistant",
    "--hidden-import=wmi",
    "--hidden-import=psutil",
    "--hidden-import=GPUtil",
    "--hidden-import=PyQt6",
    "--hidden-import=PyQt6.QtCore",
    "--hidden-import=PyQt6.QtGui",
    "--hidden-import=PyQt6.QtWidgets",
    "--hidden-import=uvicorn",
    "--hidden-import=fastapi",
    "modern_desktop_app.py"        # Ana dosya
]

# Add icon if exists
if os.path.exists("icon.ico"):
    cmd.insert(5, "--icon=icon.ico")
    print("✓ Icon bulundu, ekleniyor...")

# Add .env if exists
if os.path.exists(".env"):
    cmd.insert(-1, "--add-data=.env;.")
    print("✓ .env bulundu, ekleniyor...")

print()
print("Build başlatılıyor...")
print("⏱️  Bu 3-7 dakika sürebilir...")
print()

result = subprocess.run(cmd)

if result.returncode == 0:
    print()
    print("="*60)
    print("✅ Build başarılı!")
    print("="*60)
    print()
    print("EXE dosyası: dist/PerfHub_AI_WebApp.exe")
    print("Boyut: ~100-150 MB (tüm bağımlılıklar dahil)")
    print()
    print("Test etmek için:")
    print("  cd dist")
    print("  PerfHub_AI_WebApp.exe")
else:
    print()
    print("❌ Build başarısız!")
    print("Hata kodunu kontrol edin.")
