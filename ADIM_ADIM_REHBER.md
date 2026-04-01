# 🎯 PerfHub AI - Sitenize Ekleme (ADIM ADIM)

## 📋 Başlamadan Önce

Elimizde ne var?
- ✅ `dist/PerfHub_AI_WebApp.exe` (51 MB)
- ✅ Proje kodları (`C:\Users\Asus\OneDrive\Desktop\benchmark`)
- ✅ Siteniz: https://suleymankilinc.com/
- ✅ GitHub hesabınız

---

## 🎬 ADIM 1: Yeni GitHub Repo Oluştur

### 1.1 GitHub'a Git
- Tarayıcıda aç: https://github.com
- Sağ üstte profil fotoğrafınız → Tıkla

### 1.2 New Repository
- Yeşil "New" butonu → Tıkla
- VEYA: https://github.com/new

### 1.3 Repo Bilgilerini Doldur

```
Repository name: perfhub-ai

Description: AI-powered hardware analysis and FPS prediction tool

Public ✅ (İşaretle - portfolio için)

☐ Add a README file (İşaretleme - biz ekleyeceğiz)
☐ Add .gitignore (İşaretleme - zaten var)
☐ Choose a license (İşaretleme - sonra ekleriz)
```

### 1.4 Create Repository
- Yeşil "Create repository" butonu → Tıkla

### 1.5 Repo Linkini Kopyala
Ekranda göreceksiniz:
```
https://github.com/KULLANICIADI/perfhub-ai.git
```
Bu linki kopyalayın! (Sonra lazım olacak)

---

## 🎬 ADIM 2: Projeyi GitHub'a Yükle

### 2.1 Terminal Aç
- Windows tuşu + R
- `cmd` yaz
- Enter

### 2.2 Proje Klasörüne Git
```bash
cd C:\Users\Asus\OneDrive\Desktop\benchmark
```

### 2.3 Git Başlat
```bash
git init
```
Göreceksiniz: `Initialized empty Git repository...`

### 2.4 Dosyaları Ekle
```bash
git add .
```
(Nokta önemli! Tüm dosyaları ekler)

### 2.5 İlk Commit
```bash
git commit -m "Initial commit: PerfHub AI v2.1"
```

### 2.6 GitHub'a Bağla
```bash
git remote add origin https://github.com/KULLANICIADI/perfhub-ai.git
```
⚠️ **ÖNEMLİ:** `KULLANICIADI` yerine kendi GitHub kullanıcı adınızı yazın!

### 2.7 Ana Branch Ayarla
```bash
git branch -M main
```

### 2.8 GitHub'a Yükle
```bash
git push -u origin main
```

GitHub kullanıcı adı ve şifrenizi soracak:
- Kullanıcı adı: GitHub kullanıcı adınız
- Şifre: GitHub şifreniz (VEYA Personal Access Token)

⚠️ **Şifre çalışmazsa:**
1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Şifre yerine bu token'ı kullanın

### 2.9 Kontrol Et
Tarayıcıda: `https://github.com/KULLANICIADI/perfhub-ai`
Dosyalarınızı görmelisiniz! ✅

---

## 🎬 ADIM 3: GitHub Release Oluştur (EXE Yükle)

### 3.1 Releases Sayfasına Git
- GitHub reponuzda (perfhub-ai)
- Sağ tarafta "Releases" → Tıkla
- VEYA: `https://github.com/KULLANICIADI/perfhub-ai/releases`

### 3.2 Create a New Release
- "Create a new release" butonu → Tıkla

### 3.3 Tag Oluştur
```
Choose a tag: v2.1.0 (yaz ve "Create new tag: v2.1.0" tıkla)
Target: main ✅
```

### 3.4 Release Başlığı
```
Release title: PerfHub AI v2.1 - İlk Sürüm
```

### 3.5 Açıklama Yaz
```markdown
## 🎉 PerfHub AI v2.1

AI destekli donanım analizi ve FPS tahmin aracı.

### ✨ Özellikler
- 🔍 Otomatik donanım tespiti (CPU, GPU, RAM)
- 📊 Performans puanlama (0-100)
- ⚠️ Darboğaz analizi
- 🎮 40+ oyun için FPS tahmini
- 🛠️ PC Builder (hayalinizdeki sistemi kurun)
- 🤖 AI Asistan (donanım önerileri)
- 🔬 Detaylı donanım analizi

### 📦 Kurulum
1. `PerfHub_AI_WebApp.exe` dosyasını indirin
2. Çift tıklayın ve çalıştırın
3. İlk açılış 5-10 saniye sürebilir (normal)
4. API key gerekmez - hazır gelir!

### ⚠️ Windows Defender Uyarısı
İlk çalıştırmada uyarı verebilir (dijital imza yok):
- "Daha fazla bilgi" → "Yine de çalıştır"

### 💾 Boyut
~51 MB (tüm bağımlılıklar dahil)

### 🖥️ Sistem Gereksinimleri
- Windows 10/11 (64-bit)
- 4 GB RAM
- 100 MB boş alan
```

### 3.6 EXE Dosyasını Ekle
- "Attach binaries..." altına
- `dist/PerfHub_AI_WebApp.exe` dosyasını sürükle
- VEYA "choose them" tıkla → Dosyayı seç

Yükleme başlayacak... Bekleyin (51 MB)

### 3.7 Publish Release
- Yeşil "Publish release" butonu → Tıkla

### 3.8 İndirme Linkini Kopyala
Release sayfasında göreceksiniz:
```
PerfHub_AI_WebApp.exe (51 MB)
```
Sağ tık → "Copy link address"

Link şöyle olacak:
```
https://github.com/KULLANICIADI/perfhub-ai/releases/download/v2.1.0/PerfHub_AI_WebApp.exe
```

Bu linki bir yere kaydedin! ✅

---

## 🎬 ADIM 4: Sitenize Proje Sayfası Ekle

### 4.1 Site Reponuzu Klonlayın (Yoksa)

Terminal'de:
```bash
cd C:\Users\Asus\OneDrive\Desktop
git clone https://github.com/KULLANICIADI/suleymankilinc.com.git
cd suleymankilinc.com
```

### 4.2 Proje Klasörü Oluştur

```bash
# Eğer yoksa
mkdir projeler
cd projeler
```

### 4.3 HTML Dosyası Oluştur

`projeler/perfhub-ai.html` dosyası oluşturun.

İçeriği `ornek_site_sayfasi.html` dosyasından kopyalayın.

⚠️ **ÖNEMLİ:** İçindeki linki değiştirin:

```html
<!-- BUNU BULUN: -->
<a href="https://github.com/KULLANICIADI/perfhub-ai/releases/download/v2.1.0/PerfHub_AI_WebApp.exe"

<!-- KULLANICIADI yerine kendi GitHub kullanıcı adınızı yazın! -->
<a href="https://github.com/suleymankilinc/perfhub-ai/releases/download/v2.1.0/PerfHub_AI_WebApp.exe"
```

### 4.4 Git'e Ekle

```bash
git add projeler/perfhub-ai.html
git commit -m "Add PerfHub AI project page"
git push
```

### 4.5 Netlify Otomatik Deploy Eder

2-3 dakika bekleyin...

Sonra: `https://suleymankilinc.com/projeler/perfhub-ai.html`

---

## 🎬 ADIM 5: Ana Sayfaya Link Ekle (Opsiyonel)

### 5.1 Ana Sayfanızı Açın

`index.html` veya ana sayfa dosyanız

### 5.2 Projeler Bölümüne Ekle

```html
<!-- Projeler bölümünde -->
<div class="project-card">
    <h3>🚀 PerfHub AI</h3>
    <p>AI destekli donanım analizi ve FPS tahmin aracı</p>
    <a href="/projeler/perfhub-ai.html">Detaylar ve İndir →</a>
</div>
```

### 5.3 Git'e Ekle

```bash
git add index.html
git commit -m "Add PerfHub AI to projects"
git push
```

---

## ✅ TAMAMLANDI!

Artık sitenizde:
```
https://suleymankilinc.com/projeler/perfhub-ai.html
```

Kullanıcılar:
1. Sayfayı açar
2. "İndir" butonuna tıklar
3. EXE indirilir
4. Çalıştırır
5. API key gerekmez - hazır gelir! ✅

---

## 🔄 Güncelleme Yapmak İsterseniz

### Yeni Versiyon (v2.2) Çıkarmak:

1. **Kodu Güncelleyin**
   ```bash
   cd C:\Users\Asus\OneDrive\Desktop\benchmark
   # Değişikliklerinizi yapın
   ```

2. **Yeni EXE Oluşturun**
   ```bash
   python build_web_app_exe.py
   ```

3. **GitHub'a Push**
   ```bash
   git add .
   git commit -m "Update to v2.2"
   git push
   ```

4. **Yeni Release**
   - GitHub → Releases → New release
   - Tag: `v2.2.0`
   - Yeni EXE'yi ekle
   - Publish

5. **Site Linkini Güncelle**
   ```html
   <!-- perfhub-ai.html içinde -->
   v2.1.0 → v2.2.0
   ```

---

## ❓ Sorun Giderme

### "git: command not found"
Git yüklü değil:
1. https://git-scm.com/download/win
2. İndir ve kur
3. Terminal'i yeniden aç

### "Permission denied (publickey)"
SSH key gerekli:
1. HTTPS kullanın (yukarıdaki komutlar HTTPS)
2. VEYA: https://docs.github.com/en/authentication/connecting-to-github-with-ssh

### "Failed to push"
1. GitHub kullanıcı adı/şifre doğru mu?
2. Personal Access Token kullanın:
   - GitHub → Settings → Developer settings
   - Personal access tokens → Generate new token
   - Şifre yerine token'ı kullanın

### "EXE çalışmıyor"
1. Windows Defender uyarısı → "Yine de çalıştır"
2. Antivirus kapalı mı kontrol edin
3. `dist/PerfHub_AI_WebApp.exe` doğru dosya mı?

---

## 📞 Yardım

Takıldığınız adımı söyleyin, yardımcı olayım! 😊

---

Hazır! 🎉
