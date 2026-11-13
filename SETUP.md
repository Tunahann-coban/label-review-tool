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

**En kolayı (Windows): `baslat.bat` dosyasına çift tıkla.** İlk açılışta eksik kurulumları yapar, arayüzü derler, servisi başlatır ve tarayıcıyı açar. Kapatmak için açılan pencerede `Ctrl + C`. Mac / Linux: `./baslat.sh` (ilk seferde `chmod +x baslat.sh`). Kod güncellenince `baslat.bat yenile` arayüzü yeniden derler. Adın için: `baslat.bat --reviewer ayse`. Bu yolla aşağıdaki iki terminale gerek kalmaz, adres http://localhost:8000 olur.

Geliştirme için iki terminalli yol:

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

Tarayıcıda **http://localhost:5173** adresini aç. Açılan **Projeler** sayfasında `sample_package` görünür, **Aç** de.

İki terminali de açık bırak. Kapatmak için ikisinde de `Ctrl + C`.

Projeler listesi bilgisayarında `projects.json` dosyasında tutulur. Servisi bir kere `--package` ile başlattıktan sonra
`--package` vermeden de başlatabilirsin: `.venv\Scripts\python server\server.py`. Ana sayfadan istediğin projeyi seçersin.

Dışa aktarılanlar paket klasörünün **yanında**, her türün kendi büyük klasörüne yazılır: `<paket>_yolo`, `<paket>_coco` ve (düzenlenecekler için) `<paket>_duzenlenecek`. Örnek: paket `C:\...\bidvision_package2` ise YOLO çıktısı `C:\...\bidvision_package2_yolo\yolo_2026-11-10_23-45-12` olur, tam yol dışa aktarma penceresinde yazar. **Her dışa aktarma kendi klasörünü açar, adında gün ve saat olur.** Türler birbirine karışmaz, önceki dışa aktarmalar hiç silinmez ya da üzerine yazılmaz (eskileri istersen elle silersin). Başka bir yer istersen servise `--export <klasör>` ver, o klasörün içinde `yolo`, `coco`, `duzenlenecek` klasörleri açılır.
Her projenin kendi klasörü vardır. Başka bir yer istersen servise `--export <klasör>` ver.

## 4. Önce örnek veriyle dene (5 dk)

`sample_package` sahte bir paket: düz zemin üzerinde renkli şekiller. Doğru cevaplar bilindiği için aracı öğrenmek için iyidir.

| İş | Nasıl |
|---|---|
| Nesne seç | Sağdaki listeden ya da resimdeki maskeye tıkla |
| Nesneyi onayla (hattın sınıfı doğru) | `Enter`. Bunu her nesne için yapman gerekmez: **Tamamlandı**'ya basınca dokunulmamış nesneler otomatik onaylanır |
| Sil (yanlışlıkla sildiysen geri al) | `Del` (geri al: `Enter`) |
| Sınıfı düzelt | Sağ üstteki **Sınıf** listesinden seç |
| Maske görünümü (dolu / kenar / gizli) | `M` |
| Kaçırılan nesneyi ekle | **Adayları göster** → kesikli çizgili parçaya tıkla → sınıf seç |
| Resmi bitir (eklenecek bir şey yok) | Resmin altındaki **Tamamlandı olarak işaretle** ya da `T`; sıradaki bekleyen resim açılır. Tekrar basınca geri alınır |
| Elle maske / etiket eklenecek (Roboflow) | **Düzenlenecekler'e ekle** ya da `D`. Tamamlandı'dan bağımsız: bir resim hem tamamlanmış hem listede olabilir. Resim açık kalır |
| Gruplara göre resim listesi | Sağdaki **Resimler** sekmesi: Tümü / Bekleyen / Tamamlanan / Düzenlenecek. Birine tıklayınca açılır, tekrar düzeltebilirsin |
| Önceki / sonraki resim | Resmin hemen üstündeki **← Önceki** (`P`) ve **Sonraki →** (`N`). Sağdaki Resimler sekmesinde bir grup seçtiysen o grubun içinde gezer, çubuk bunu yazar |
| Henüz tamamlanmamış sıradaki resme atla | **Bekleyene geç** (`B`) |
| Seçimi bırak | `Esc` |
| YOLO ya da COCO'ya aktar (tamamlananlar, düzenlenecekler listesindekiler hariç) | Üstteki **Dışa aktar** → biçimi seç → penceredeki **Dışa aktar** |
| Düzenlenecekleri Roboflow'a götür | **Dışa aktar** → **Düzenlenecekler** → `<paket>_duzenlenecek\duzenlenecek_<tarih>` klasörünü yükle (resimler + `_annotations.coco.json`) |
| Başka projeye geç | Sol üstteki **← Projeler** |

Kararlar her işlemde `sample_package/reviews/` klasörüne kaydedilir. Sayfayı yenilesen de durur. Baştan başlamak için o klasörü sil.

## 5. Gerçek fotoğraflarla dene

**Notebook çalıştırmadan, hemen dene:** repoda `example_package` klasörü var. Bu, Kaggle hattının 5 gerçek fotoğraf için ürettiği hazır çıktıdır (etiketli nesneler, maskeler, adaylar). GPU ya da notebook gerekmez. Projeler sayfasında **+ Klasör ekle** de, klasör yolu olarak `label-review-tool\example_package` klasörünün tam yolunu, bir ad ve kendi adını yaz, **Ekle**, sonra **Aç**. Kararların `example_package\reviews\` içine yazılır ve git'e girmez.

Tam gerçek paket (`bidvision_package.zip`) GitHub'da **yok**, çünkü müzayede fotoğrafları repoya konmuyor, yalnızca bu 5 fotoğraflık örnek var. Tam paketi ekipten ayrıca al.

1. `label-review-tool` içinde `packages` adlı bir klasör oluştur.
2. Zip'i `packages\bidvision_pilot` klasörüne aç. İçinde `annotations.json` ve `images\` olmalı.
3. Projeler sayfasında **+ Klasör ekle** de. Klasör yolunu (örn. `C:\...\label-review-tool\packages\bidvision_pilot`), bir ad ve kendi adını yaz, **Ekle**.
   Komut satırını tercih edersen servisi bununla da başlatabilirsin:
   ```powershell
   .venv\Scripts\python server\server.py --package packages\bidvision_pilot --reviewer adin
   ```
4. Projeyi **Aç**.

**+ Görsel yükle** tarayıcıdan fotoğraf (ve isteğe bağlı `annotations.json`) yükleyerek proje oluşturur. Etiket dosyası
yüklenmezse proje sınıfsız ve nesnesiz olur. Bu araç maske çizmediği için asıl yol Kaggle'dan gelen pakettir.

İpucu: Gerçek fotoğrafta **Kenar** görünümü (`M`) nesnenin kendisini gösterir, sınıfı ona bakarak seç.

## 6. Sorun çıkarsa

| Belirti | Çözüm |
|---|---|
| Sayfada "Servise ulaşılamıyor" | Terminal 1 çalışıyor mu? Hata varsa son satırları ekibe gönder. |
| `python` bulunamadı | Python kurulurken PATH seçilmemiş. Python'u yeniden kur, ya da Mac'te `python3` kullan. |
| `npm` bulunamadı | Node.js kurulu değil. |
| Servis `address already in use` / `portu dolu` diyor, ya da `baslat.bat` açılıyor ama sayfa **eski** | 8000 portunda aracın eski bir kopyası hâlâ çalışıyor (görünmeyen ya da küçültülmüş bir pencere). `baslat.bat` bunu kendisi kapatır; başka yolla açtıysan eski pencerede `Ctrl+C` yap. |
| `annotations.json not found` | `--package` yolu yanlış: klasörün içinde `annotations.json` olmalı. |
| `same file stem` hatası | Pakette aynı adlı iki fotoğraf var (örn. `a.jpg` ve `a.png`). Ekibe bildir. |
| `npm install` sırasında `npm warn allow-scripts ... esbuild` | Zararsız, bir şey yapma. Arayüz yine çalışır. |
| `pip` sırasında `A new release of pip is available` | Zararsız. |

| Sayfada "istek aracın kendi sayfasından gelmedi" | Aracı `http://localhost:5173` adresinden aç; başka bir adres ya da uzantı istek gönderiyor olabilir. |

Testleri çalıştırmak istersen (isteğe bağlı):
```powershell
.venv\Scripts\python -m pip install -r server\requirements-dev.txt
.venv\Scripts\python server\test_review_store.py
.venv\Scripts\python server\test_exporter.py
.venv\Scripts\python server\test_projects.py
cd web; npm test
```

## 7. Geri bildirim

Denedikten sonra şunları yaz:
- Kurulumda nerede takıldın?
- Hangi nesnede hangi kararı verdin? Pipeline'ın en çok yanıldığı sınıflar hangileri?
- Eksik bulduğun ya da kafa karıştıran bir şey var mı?

Kararların kendi bilgisayarındaki `reviews/` klasöründe. İstenirse o klasörü zip'leyip gönderebilirsin, iki kişinin kararları karşılaştırılabilir.
