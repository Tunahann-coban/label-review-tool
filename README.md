# Etiket İnceleme Aracı

Otomatik hattın (RAM++, Grounding DINO, SAM2) çıkardığı etiketli maskeleri resim üstünde gösteren, yanlış etiketleri düzeltmeye yarayan, kendi bilgisayarında çalışan küçük bir uygulama. Çıktısı, YOLO segmentasyon modelini eğiteceğimiz veri seti.

Bu belge hem seni (Tunahan) hem de yardım aldığın yapay zekâ asistanını yönlendirmek için yazıldı. Asistana bu dosyanın tamamını ver ve hangi adımda olduğunu söyle.

## 1. Neyi yapıyoruz

Hat her resim için nesneleri bulur: sınıf adı, maske, güven skoru. Bazıları yanlış olur. Bu araçla:

- resim üstünde maskeleri görürüz,
- yanlış sınıfı düzeltiriz, yanlış nesneyi sileriz, doğru olanı onaylarız,
- güven skoru düşük olanları (şüpheliler) öne alırız,
- hattın kaçırdığı nesneyi, hattın önceden bulduğu "aday maskeler" arasından seçip ona bir sınıf vererek ekleriz,
- sonuçları YOLO-seg biçiminde dışarı aktarırız.

Her ekip üyesi kendi bilgisayarında çalıştırır. Veritabanı, sunucu, giriş sistemi yoktur. Her şey dosya.

## 2. Kapsam

**Yapılacak:** yukarıdaki beş madde.

**Yapılmayacak (ilk sürümde):** maske çizme veya maskenin kenarını düzeltme, giriş yapma ve kullanıcı yönetimi, veritabanı, internete açma, canlı yapay zekâ ile maske çıkarma. Bunlar sonraya. Yapay zekâ asistanı: listede olmayan bir özellik eklemeyi önerme, önce sor.

## 3. Mimari

İki parça, aynı bilgisayarda çalışır:

- **Servis:** Python + FastAPI. Paket klasörünü okur, arayüze verir, kararları klasöre yazar, dışa aktarır.
- **Arayüz:** React (Vite). Resmi ve maskeleri gösterir, kullanıcı etkileşimini alır.

Arayüz ve servis arasındaki bağlantıyı (aşağıdaki API) temiz tut. İleride servise "tıkla, maske çıkar" gibi yeni uç noktalar ekleyeceğiz.

Çalıştırma tek komutla olsun. Örneğin servis `python server.py --package sample_package --reviewer tunahan` ile, arayüz `npm run dev` ile başlasın.

## 4. Klasör yapısı

```
etiket-araci/
  README.md
  make_sample_data.py          sahte paket üretir
  server/                      FastAPI servisi
  web/                         React arayüzü
  sample_package/              (make_sample_data.py üretir)
    images/img_001.jpg ...
    annotations.json
    reviews/                   (araç oluşturur)
      img_001.json
  export/                      (dışa aktarma buraya yazar)
    images/ labels/ data.yaml
```

## 5. Veri biçimi

### 5.1 Paket: `annotations.json` (COCO benzeri)

Tüm koordinatlar **piksel** cinsinden. Maske, çokgen noktalarının düz listesi: `[x1, y1, x2, y2, ...]`.

```json
{
  "info": {"version": 1},
  "categories": [{"id": 1, "name": "cardboard box"}, {"id": 2, "name": "plastic tote"}],
  "images": [{"id": 1, "file_name": "img_001.jpg", "width": 800, "height": 600}],
  "annotations": [
    {"id": 1, "image_id": 1, "category_id": 1,
     "bbox": [x, y, w, h],
     "segmentation": [[x1, y1, x2, y2, ...]],
     "score": 0.82, "source": "pipeline"}
  ],
  "candidates": [
    {"id": 1001, "image_id": 1, "segmentation": [[...]], "area": 1234.5}
  ]
}
```

- `annotations`: hattın bulduğu nesneler.
- `candidates`: hattın seçmediği ama SAM2'nin otomatik bulduğu parçalar. Etiketi yoktur.
- Sınıf listesini koda gömme, her zaman `categories` içinden oku. Listede `unknown` adlı bir sınıf olabilir.
- Gerçek paketi Gölge sonradan verecek. `make_sample_data.py` aynı biçimde sahte bir paket üretir, geliştirmeyi onunla yap.

### 5.2 Karar dosyası: `reviews/<resim_adı>.json`

Resim başına bir dosya. Kullanıcı bir şey değiştirdikçe güncellenir.

```json
{
  "image_id": 1,
  "status": "reviewed",
  "reviewer": "tunahan",
  "updated": "2026-10-24T10:30:00",
  "objects": [
    {"ann_id": 1, "category_id": 2, "state": "changed", "orig_category_id": 1},
    {"ann_id": 2, "category_id": 1, "state": "accepted"},
    {"ann_id": 3, "state": "deleted"},
    {"ann_id": "new-1", "category_id": 4, "state": "added",
     "from_candidate": 1001, "segmentation": [[...]]}
  ],
  "log": [
    {"t": "2026-10-24T10:29:10", "ann_id": 1, "action": "change", "from": 1, "to": 2}
  ]
}
```

- `status`: `pending` (bekliyor) ya da `reviewed` (incelendi).
- `state`: `auto` (dokunulmadı), `accepted`, `changed`, `deleted`, `added`.
- `log` değişiklik geçmişidir, geri almak için kullanılır.
- Resim hiç incelenmediyse dosya yoktur ve durum `pending`'dir.

## 6. Servis API'si

| Yöntem | Yol | Ne yapar |
|---|---|---|
| GET | `/api/package` | Sınıf listesi ve resim listesi (id, ad, durum) |
| GET | `/api/images/{id}` | Resim bilgisi, nesneler (karar dosyasıyla birleştirilmiş), adaylar |
| GET | `/api/images/{id}/file` | Resim dosyası |
| POST | `/api/images/{id}/review` | Kararları kaydeder (`reviews/` içine yazar) |
| POST | `/api/export` | İncelenen resimleri YOLO-seg olarak `export/` içine yazar |

## 7. Arayüz davranışı

- **Ana ekran:** Resim ortada, üstünde maskeler yarı saydam ve farklı renklerde, etiket adı yazılı. Sağda nesne listesi. Üstte önceki/sonraki ve ilerleme sayacı (örn. 12 / 100 incelendi).
- **Nesne seçme:** Listeden ya da resme tıklayarak. Seçilen nesne vurgulanır (kalın kenar).
- **İşlem:** Seçili nesne için üç düğme: Onayla, Sınıfı değiştir (açılır liste), Sil. Klavye kısayolları olsun (örn. `Enter` onayla, `Del` sil, `N` sonraki resim).
- **Şüpheliler:** Güven skoru eşiğin altında olanlar ve sınıfı `unknown` olanlar listenin başında, "şüpheli" rozetiyle. Eşik arayüzde bir kaydırıcı, varsayılan 0,5.
- **Aday maskeler:** Bir düğmeyle açılır/kapanır. Açılınca resim üstünde adaylar çizgiyle görünür. Birine tıklayınca sınıf seçtirilir ve listeye yeni nesne olarak eklenir.
- **Resim durumu:** İşlem yapılan resim otomatik "incelendi" olur. "Sıradaki bekleyen" düğmesi bekleyen ilk resme atlar.
- **Her işlem anında kaydedilir.** Sayfa kapanıp açılınca kararlar yerinde olmalı.

## 8. Dışa aktarma (YOLO-seg)

Sadece `reviewed` resimler, silinen nesneler hariç. Her resim için `export/labels/<resim>.txt`, her satır bir nesne:

```
<sınıf_no> x1 y1 x2 y2 x3 y3 ...
```

- `sınıf_no`: `categories` sırasına göre 0'dan başlayan numara.
- Koordinatlar resim genişliğine ve yüksekliğine bölünmüş, 0–1 arası.
- Resimler `export/images/` içine kopyalanır.
- `export/data.yaml` içinde `names:` listesi (sınıf adları, sıra aynı) bulunur.

## 9. Adımlar

Her adımı bitirince çalıştığını kontrol et ve Gölge'ye göster, sonra sonrakine geç. Her adım küçük tutuldu. Takılırsan Gölge'ye yaz.

| Adım | İş | Bitti sayılır |
|---|---|---|
| 0 | Ortamı kur: Python servisi ve React sayfası konuşuyor | Sayfada servisten gelen "merhaba" yazısı görünüyor |
| 1 | `make_sample_data.py` ile sahte paketi üret. Servis `annotations.json`'u okusun, arayüz resmi göstersin, önceki/sonraki çalışsın | 3 resim arasında gezilebiliyor |
| 2 | Maskeleri resmin üstüne çiz (SVG ya da canvas), etiket adıyla | Her nesne farklı renkte, etiket adı yazıyor |
| 3 | Nesne listesi, seçince vurgulama, resme tıklayınca seçme | Tıklanan nesne öne çıkıyor |
| 4 | Sınıfı değiştir, sil, onayla. Servis `reviews/`'a kaydeder | Sayfa yenilenince kararlar duruyor |
| 5 | Şüpheliler: eşik kaydırıcısı, listede öne alma, rozet | Eşik değişince liste değişiyor |
| 6 | Resim durumu ve ilerleme sayacı, "sıradaki bekleyen" | Bekleyen resme atlıyor |
| 7 | Dışa aktarma | `export/` doğru biçimde oluşuyor, bir `.txt` dosyasını elle kontrol et |
| 8 | Aday maskeler: göster, tıkla, sınıf ver, ekle | Yeni nesne listeye eklenip kaydediliyor ve dışa aktarmaya giriyor |
| 9 | (İsteğe bağlı, sonraya) | — |

Önerilen kontrol: adım 2'den sonra, adım 4'ten sonra ve adım 7'den sonra Gölge'ye ekran görüntüsü at.

## 10. Yapay zekâ asistanı için notlar

- Bu belgedeki kapsamın dışına çıkma. Yeni özellik veya yeni kütüphane önermeden önce sor.
- Adım adım ilerle. Bir seferde bir adımın kodunu yaz, çalıştığını doğrula, sonra devam et.
- Dosyaları küçük ve okunur tut. Karmaşık yapı kurma, ilk hedef çalışan basit bir araç.
- Koordinatlar her yerde piksel cinsinden. Dışa aktarırken normalize et.
- Arayüzü ve servisi ayrı çalıştır, aralarındaki tek bağ API.
- Maskeyi resme çizerken resmin gerçek boyutu ile ekranda görünen boyut farklı olabilir. Ölçek oranını hesaba kat, tıklamayı da aynı oranla çevir.
