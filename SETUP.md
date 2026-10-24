# Kurulum ve deneme (kendi bilgisayarında)

Bu belge, aracı ilk kez kendi bilgisayarında çalıştıracak ekip üyesi için yazıldı. Yaklaşık 15 dakika sürer.
Aracın ne yaptığı için [README.md](README.md), ilerleme ve kararlar için [PLAN.md](PLAN.md).

## 1. Gerekenler (bir kere)

| Program | Sürüm | Kontrol komutu | İndir |
|---|---|---|---|
| Git | herhangi | `git --version` | https://git-scm.com |
| Python | 3.11 ya da 3.12 | `python --version` (Mac: `python3 --version`) | https://www.python.org/downloads |
| Node.js | 20 ya da üstü | `node --version` | https://nodejs.org (LTS) |

Windows'ta Python kurulurken **"Add python.exe to PATH"** kutusunu işaretle.

Repo özeldir. GitHub'da gelen **davet e-postasını kabul etmiş** olman gerekir.

## 2. Kodu indir ve kur (bir kere)

Bir terminal aç (Windows: PowerShell, Mac: Terminal). Komutları sırayla çalıştır.

**Windows:**
```powershell
git clone https://github.com/Tunahann-coban/label-review-tool.git
cd label-review-tool
python -m venv .venv
.venv\Scripts\python -m pip install -r server\requirements.txt
.venv\Scripts\python make_sample_data.py
cd web
npm install
cd ..
```

**Mac / Linux:**
```bash
git clone https://github.com/Tunahann-coban/label-review-tool.git
cd label-review-tool
python3 -m venv .venv
.venv/bin/python -m pip install -r server/requirements.txt
.venv/bin/python make_sample_data.py
cd web
npm install
cd ..
```

`git clone` GitHub şifresi isterse tarayıcıdan giriş yap. Şifre yerine "token" isterse GitHub Desktop ile klonlamak daha kolay olur.

## 3. Aracı çalıştır

**İki terminal** gerekir: biri servis, biri arayüz. İkisi de `label-review-tool` klasöründe açılmalı.

**Terminal 1, servis** (`--reviewer` yerine kendi adını yaz):
```powershell
.venv\Scripts\python server\server.py --package sample_package --reviewer adin
```
Mac: `.venv/bin/python server/server.py --package sample_package --reviewer adin`

`Uvicorn running on http://127.0.0.1:8000` yazınca hazırdır.

**Terminal 2, arayüz:**
```powershell
cd web
npm run dev
```

Tarayıcıda **http://localhost:5173** adresini aç.

İki terminali de açık bırak. Kapatmak için ikisinde de `Ctrl + C`.

## 4. Önce örnek veriyle dene (5 dk)

`sample_package` sahte bir paket: düz zemin üzerinde renkli şekiller. Doğru cevaplar bilindiği için aracı öğrenmek için iyidir.

| İş | Nasıl |
|---|---|
| Nesne seç | Sağdaki listeden ya da resimdeki maskeye tıkla |
| Onayla | `Enter` |
| Sil (yanlışlıkla sildiysen geri al) | `Del` (geri al: `Enter`) |
| Sınıfı düzelt | Sağ üstteki **Sınıf** listesinden seç |
| Maske görünümü (dolu / kenar / gizli) | `M` |
| Kaçırılan nesneyi ekle | **Adayları göster** → kesikli çizgili parçaya tıkla → sınıf seç |
| Sonraki resim | `N` |
| Seçimi bırak | `Esc` |
| YOLO'ya aktar | Üstteki **Dışa aktar** → penceredeki **Dışa aktar** |

Kararlar her işlemde `sample_package/reviews/` klasörüne kaydedilir. Sayfayı yenilesen de durur. Baştan başlamak için o klasörü sil.

## 5. Gerçek fotoğraflarla dene

Gerçek paket (`bidvision_package.zip`) GitHub'da **yok**, çünkü müzayede fotoğrafları repoya konmuyor. Zip'i ekipten ayrıca al.

1. `label-review-tool` içinde `packages` adlı bir klasör oluştur.
2. Zip'i `packages\bidvision_pilot` klasörüne aç. İçinde `annotations.json` ve `images\` olmalı.
3. Terminal 1'de servisi durdur (`Ctrl + C`) ve bu paketle başlat:
   ```powershell
   .venv\Scripts\python server\server.py --package packages\bidvision_pilot --reviewer adin --export packages\bidvision_pilot_export
   ```
4. Tarayıcıda sayfayı yenile.

İpucu: Gerçek fotoğrafta **Kenar** görünümü (`M`) nesnenin kendisini gösterir, sınıfı ona bakarak seç.

## 6. Sorun çıkarsa

| Belirti | Çözüm |
|---|---|
| Sayfada "Servise ulaşılamıyor" | Terminal 1 çalışıyor mu? Hata varsa son satırları ekibe gönder. |
| `python` bulunamadı | Python kurulurken PATH seçilmemiş. Python'u yeniden kur, ya da Mac'te `python3` kullan. |
| `npm` bulunamadı | Node.js kurulu değil. |
| Servis `address already in use` diyor | 8000 portu dolu: başka bir terminalde servis açık kalmış, onu kapat. |
| `annotations.json not found` | `--package` yolu yanlış: klasörün içinde `annotations.json` olmalı. |
| `same file stem` hatası | Pakette aynı adlı iki fotoğraf var (örn. `a.jpg` ve `a.png`). Ekibe bildir. |
| `npm install` sırasında `npm warn allow-scripts ... esbuild` | Zararsız, bir şey yapma. Arayüz yine çalışır. |
| `pip` sırasında `A new release of pip is available` | Zararsız. |

Testleri çalıştırmak istersen (isteğe bağlı):
```powershell
.venv\Scripts\python server\test_review_store.py
.venv\Scripts\python server\test_exporter.py
cd web; npm test
```

## 7. Geri bildirim

Denedikten sonra şunları yaz:
- Kurulumda nerede takıldın?
- Hangi nesnede hangi kararı verdin? Pipeline'ın en çok yanıldığı sınıflar hangileri?
- Eksik bulduğun ya da kafa karıştıran bir şey var mı?

Kararların kendi bilgisayarındaki `reviews/` klasöründe. İstenirse o klasörü zip'leyip gönderebilirsin, iki kişinin kararları karşılaştırılabilir.
