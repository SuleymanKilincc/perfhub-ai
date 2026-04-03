"""
PerfHub AI - Release ZIP Creator
Creates a distribution ZIP file for GitHub releases
"""
import zipfile
import os
import shutil

VERSION = "4.0.0"
ZIP_NAME = f"PerfHub_AI_v{VERSION}.zip"

print("="*60)
print(f"PerfHub AI - Release ZIP Creator v{VERSION}")
print("="*60)
print()

# Check if EXE exists
if not os.path.exists("dist/PerfHub_AI_WebApp.exe"):
    print("[ERROR] EXE bulunamadi! Once build yapin:")
    print("  python build_web_app_exe.py")
    exit(1)

print("[OK] EXE bulundu")

# Create README.txt for users
readme_content = """
╔══════════════════════════════════════════════════════════════╗
║           PerfHub AI - Donanım Analiz Uygulaması            ║
║                      Versiyon 4.0.0                          ║
╚══════════════════════════════════════════════════════════════╝

🎮 HAKKINDA
-----------
PerfHub AI, bilgisayarınızın donanımını analiz eder, performans 
skoru verir ve oyunlarda kaç FPS alacağınızı tahmin eder.

✨ ÖZELLİKLER
-------------
✅ Otomatik donanım tespiti (CPU, GPU, RAM)
✅ Performans skoru (0-100)
✅ Darboğaz analizi
✅ 30+ oyun için FPS tahmini
✅ Ray Tracing / Path Tracing desteği
✅ PC Builder (hayalinizdeki sistemi test edin)
✅ AI Asistan (Gemini 2.5 Flash)
✅ TR/EN dil desteği

🚀 KURULUM
----------
1. PerfHub_AI_WebApp.exe dosyasını çift tıklayın
2. Windows "Bilinmeyen yayıncı" uyarısı verirse:
   - "Daha fazla bilgi" tıklayın
   - "Yine de çalıştır" seçin
3. Uygulama açılacak, sistem taraması otomatik başlar

⚠️ GÜVENLİK
-----------
Bu uygulama 70+ antivirüs tarafından taranmıştır:
🔗 VirusTotal: https://www.virustotal.com/...

Açık kaynak kodlu: https://github.com/SuleymanKilincc/perfhub-ai

🛠️ SİSTEM GEREKSİNİMLERİ
-------------------------
• Windows 10/11 (64-bit)
• 100 MB boş disk alanı
• İnternet bağlantısı (AI özelliği için)

📧 DESTEK
---------
• GitHub: https://github.com/SuleymanKilincc/perfhub-ai
• Website: https://suleymankilinc.com/
• Issues: https://github.com/SuleymanKilincc/perfhub-ai/issues

📄 LİSANS
---------
MIT License - Ücretsiz kullanabilir, değiştirebilirsiniz.
Detaylar için LICENSE.txt dosyasına bakın.

═══════════════════════════════════════════════════════════════
© 2025 Süleyman Kılınç - Tüm hakları saklıdır.
═══════════════════════════════════════════════════════════════
"""

with open("README.txt", "w", encoding="utf-8") as f:
    f.write(readme_content)

print("[OK] README.txt olusturuldu")

# Create ZIP
print()
print(f"ZIP olusturuluyor: {ZIP_NAME}")
print()

with zipfile.ZipFile(ZIP_NAME, 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add EXE
    print("  [+] PerfHub_AI_WebApp.exe")
    zipf.write("dist/PerfHub_AI_WebApp.exe", "PerfHub_AI_WebApp.exe")
    
    # Add README
    print("  [+] README.txt")
    zipf.write("README.txt", "README.txt")
    
    # Add LICENSE
    if os.path.exists("LICENSE"):
        print("  [+] LICENSE.txt")
        zipf.write("LICENSE", "LICENSE.txt")

# Clean up temp files
os.remove("README.txt")

# Get file size
zip_size = os.path.getsize(ZIP_NAME) / (1024 * 1024)

print()
print("="*60)
print("[SUCCESS] ZIP olusturuldu!")
print("="*60)
print()
print(f"Dosya: {ZIP_NAME}")
print(f"Boyut: {zip_size:.2f} MB")
print()
print("GitHub Release'e yuklemek icin:")
print(f"  1. GitHub'da yeni release olustur (v{VERSION})")
print(f"  2. {ZIP_NAME} dosyasini yukle")
print(f"  3. VirusTotal linkini ekle")
print()
