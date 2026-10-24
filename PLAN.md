# Çalışma Planı

Ayrıntılı kapsam ve veri biçimi için [README.md](README.md). Bu dosya sadece takvim ve ilerleme durumunu tutar.

Durum: ✅ bitti · ⏳ sürüyor · ⬜ başlamadı · 📸 Gölge'ye ekran görüntüsü

## Hafta 1 (21–30 Ekim 2026)

Takvim 24 Ekim'de 3 gün kaydırıldı. Önde gidebildiğimiz gün sonraki adıma geçeriz.

| Gün | Adım | İş | Durum |
|---|---|---|---|
| Çar 21 | — | Repo kurulumu (`label-review-tool`), `.gitignore`, plan | ✅ |
| Cmt 24 | 0 | FastAPI servisi ↔ React sayfası "merhaba" | ✅ |
| Cmt 24 | 1 | Sahte paket, `annotations.json` okuma, önceki/sonraki | ✅ |
| Paz 25 | 2 | Maskeleri SVG ile çiz, etiket adları 📸 | ✅ (24 Ekim'de, bir gün önden) |
| Pzt 26 | 3 | Nesne listesi, seçme, resme tıklayarak seçme | ✅ (24 Ekim'de, iki gün önden) |
| Pzt 26 | 4 | Onayla / sınıf değiştir / sil, `reviews/` kaydı 📸 | ✅ (24 Ekim'de, iki gün önden) |
| Sal 27 | 5 | Şüpheliler: eşik kaydırıcısı, rozet, öne alma | ✅ (24 Ekim'de, üç gün önden) |
| Sal 27 | 6 | Resim durumu, ilerleme sayacı, sıradaki bekleyen | ✅ (24 Ekim'de, üç gün önden) |
| Çar 28 | 7 | YOLO-seg dışa aktarma 📸 | ✅ (24 Ekim'de, dört gün önden) |
| Per 29 | 8 | Aday maskeler: göster, tıkla, sınıf ver, ekle | ✅ (24 Ekim'de, beş gün önden) |
| Cum 30 | — | Tampon: hata düzeltme, çalıştırma talimatları | ⬜ |

## Çalıştırma

Yeni bir bilgisayarda ilk kez kurulum için: [SETUP.md](SETUP.md) (Windows ve Mac, adım adım).

İlk kurulum (bir kere, proje klasöründe):

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r server\requirements.txt
.venv\Scripts\python make_sample_data.py
cd web && npm install
```

Her seferinde iki terminal:

```bash
.venv\Scripts\python server\server.py --package sample_package --reviewer tunahan
```

```bash
cd web && npm run dev
```

Sonra tarayıcıda http://localhost:5173 açılır.

Kısayollar: `Enter` onayla (silinmişse geri al), `Del` sil, `N` sonraki resim, `Esc` seçimi bırak.

Aday eklemek: listenin üstündeki "Adayları göster" düğmesi, sonra resimde kesikli çizgili bir adaya tıkla ve sınıfını seç. Sınıfı seçtiğin an nesne eklenir.

Kararları sıfırlamak için `sample_package\reviews` klasörünü silmek yeterli.

Servis testleri (geçici kopya üzerinde çalışır, kararlarına dokunmaz):

```bash
.venv\Scripts\python server\test_review_store.py
```

Dışa aktarma testleri:

```bash
.venv\Scripts\python server\test_exporter.py
```

Dışa aktarma klasörü `--export` ile değiştirilebilir (varsayılan: `export`).

Arayüz testleri (şüpheli mantığı):

```bash
cd web && npm test
```

## Pipeline (Kaggle) → araç

`pipeline/` klasörü Kaggle'daki RAM++ / Grounding DINO / SAM 2 notebook'unu araca bağlar.

- `make_package.py`: tespit sonuçlarını araç paketine çevirir (`annotations.json` + `images/`). Fotoğraf yönünü (EXIF) düzeltir, maskeleri sadeleştirilmiş çokgene çevirir, kopya kutuları temizler, adayları seçer.
- `build_notebook.py`: arkadaşımızın notebook'una dokunmadan "Bölüm 3: paket üret" hücrelerini ekler ve `bidvision_pilot.ipynb` dosyasını yazar. Arkadaşımızın bütün hücreleri aynen ve aynı sırada kalır. Bölüm 3, kurulumun hemen arkasına ve onun tek fotoğraflık testlerinin önüne girer, çünkü o testler yer tutucu yol yüzünden hata verip "Run All"ı durdurur.
- `test_make_package.py`: GPU'suz testler (27 test).

```bash
.venv\Scripts\python -m pip install -r pipeline\requirements.txt
.venv\Scripts\python pipeline\test_make_package.py
.venv\Scripts\python pipeline\build_notebook.py pipeline\<arkadaşın-notebook'u>.ipynb
```

- `clean_package.py`: notebook'a sonradan eklenen temizlik kurallarını eski bir pakete uygular, Kaggle'ı yeniden çalıştırmak gerekmez.

Notebook dosyaları (`*.ipynb`) ve gerçek paketler (`packages/`, `*.zip`) git'e girmez.

**Pilot 1 (24 Ekim, 4 fotoğraf, T4):** Fotoğraf başına ~11 saniye, 40 nesne, 140 aday. Maskeler iyi. Sorunlar: aynı nesneye 2–3 etiket (maske örtüşmesi %75–95) ve gürültülü adaylar (yarısı kırıntı). Çözüm: maske bazlı kopya temizliği (örtüşme > %70 ise yüksek skor kalır) ve aday kuralları (%0,5–30 arası boyut, kopyalar atılır, en fazla 20). Temiz paket: 37 nesne, 48 aday. Skorların hepsi 0,36–0,85 arasında. Eşik 0,50'de çoğu "şüpheli".
RAM++ ile Grounding DINO farklı sınıflar buluyor. depo1'de RAM++ "cardboard box, bagged contents, mattress" buldu, DINO bulmadı. DINO "plastic tote, table" buldu, RAM++ bulmadı. RAM++ ile ön filtreleme bu ikisini hiç aratmazdı. Ekiple konuşulacak.

Notebook incelemesinden çıkan notlar (ekiple paylaşılmalı):
- `predict_with_classes()` sınıfları ayrı işlemiyor. O da tek metin kullanıp sonucu kelime içermeye göre eşliyor. Çözüm her sınıfı ayrı sormak, Bölüm 3 böyle yapıyor.
- Koddaki liste 17 sınıf, belgede "18 + misc_item" yazıyor. Pilot 17 + `misc_item` kullanıyor.
- RAM++ çıktısı Grounding DINO'ya bağlı değildi. Pilotta RAM++ atlanıyor.
- ~~Grounding DINO eklentisi `CUDA_HOME=""` ile GPU desteksiz kalabilir~~. Pilotta "Compiling with CUDA" yazdı ve GPU'da çalıştı, endişe yersizdi. Bölüm 3'teki güvenlik ağı yine duruyor.
- Telefon fotoğraflarının EXIF yönü: Grounding DINO'nun yükleyicisi uygulamıyor, tarayıcı uyguluyor. Paket düzeltilmiş resmi kullanıyor.

## Git düzeni

İsimlendirmeler İngilizce: repo, dal, etiket, commit mesajı, dosya/klasör, değişken ve fonksiyon adları. Belgeler (README, PLAN) Türkçe kalır.

- GitHub reposu: `label-review-tool`
- Şimdilik tek dal: `main`. Her adım bir veya birkaç commit, mesaj biçimi: `step-N: short description` (örn. `step-2: draw masks as SVG overlay`).
- Her adım bitince etiket: `step-N` (örn. `git checkout step-4` ile o anki hâline dönülebilir).
- Ekip katıldığında: her iş için `step-N-short-name` dalı açılır (örn. `step-5-suspect-filter`), Pull Request ile `main`'e birleştirilir.

## Günlük

Her gün sonunda bir satır: ne yapıldı, ne kaldı, sorun var mı.

- **21 Ekim:** Yerel repo kuruldu, plan yazıldı.
- **24 Ekim:** GitHub reposu bağlandı: https://github.com/Tunahann-coban/label-review-tool. Takvim 3 gün kaydırıldı. Adım 0 ve 1 bitti: servis paketi okuyor, sayfa 3 resim arasında geziyor. Servis kapalıyken sayfa uyarı verip tekrar deniyor. Adım 2 de bitti: maskeler her nesneye ayrı renkle, sınıf adı ve skorla çiziliyor. Ekran küçülünce de hizalı kalıyor (%59 ölçekte test edildi). Adım 3 bitti: sağda nesne listesi, listeden ya da resimden seçme, kalın kenarla vurgu. Örtüşen maskelerde küçük olan seçiliyor. Boş alana tıklayınca seçim kalkıyor, resim değişince sıfırlanıyor. Adım 4 bitti: onayla / sınıf değiştir / sil, `Enter` / `Del` / `N` kısayolları. Kararlar `reviews/` klasörüne README biçiminde yazılıyor, sayfa yenilenince yerinde duruyor. Silinen nesne geri alınabiliyor. Servis için 20 testlik bir dosya eklendi (40 eşzamanlı yazma dahil). Adım 5 bitti: eşik kaydırıcısı (varsayılan 0,50), şüpheliler en düşük skordan başlayarak listenin başında, "şüpheli" rozeti ve sebebi. Şüphelilik hattın orijinal çıktısına göre belirleniyor, böylece karar verirken liste zıplamıyor. Seçili nesne paneli sabit yükseklikte, seçim yapınca liste kaymıyor. Arayüz testleri: `cd web && npm test`. Adım 6 bitti: üstte "x / y incelendi" sayacı ve ilerleme çubuğu, resim durumu etiketi (bekliyor / incelendi), "Sıradaki bekleyen" düğmesi. Düğme ileriye doğru arıyor, sona gelince başa dönüyor. Bekleyen kalmayınca pasif oluyor. Üst çubuktaki düğmeler dosya adı uzunluğundan bağımsız olarak sabit yerde duruyor. Adım 7 bitti: "Dışa aktar" düğmesi `export/` klasörüne `images/`, `labels/` ve `data.yaml` yazıyor. Sınıf numarası listedeki sıra (id değil), koordinatlar 0–1 arasında ve sıkıştırılmış. Eski dosyalar temizleniyor, bu araca ait olmayan klasörün üzerine yazılmıyor. 25 test (kodun içine bilerek sokulan 3 hatanın hepsini yakaladı), elle hesap ve bağımsız çizimle doğrulandı. Gölge'ye sorulacaklar: (1) Resmi "incelendi" saymak için bütün nesnelere karar verilmesi gerekmeli mi? Tek kararla, dokunulmamış yanlış etiketler eğitime giriyor (`img_002`'de 3 tane). (2) Maske rengi alttaki nesneyi örtüyor, maskeyi gizleme ya da yalnızca kenar çizgisi seçeneği eklensin mi? (3) Çok parçalı maskeler ayrı satır olarak mı yazılsın, birleştirilsin mi? Adım 8 bitti: "Adayları göster" ile adaylar kesikli çizgiyle görünüyor. Tıklayıp sınıf seçince `new-N` olarak ekleniyor, kaydediliyor ve dışa aktarmaya giriyor. Aynı aday iki kere eklenemiyor. Eklenen nesne silinirse şekli saklanıyor ve geri alınabiliyor. Geri alma, aynı adaydan ikinci bir nesne oluşturamıyor. Elle eklenen nesneler şüpheli sayılmıyor.
- **24 Ekim (ek):** Dışa aktarma artık bir pencereden yapılıyor. Pencere önce önizleme gösteriyor ve hiçbir şey yazmıyor: kaç resim ve nesne, sınıf dağılımı, kaç resmin incelenmediği, kaç nesneye hiç dokunulmadığı, uyarılar. Penceredeki "Dışa aktar" düğmesi aktarıyor. Bitince sağ altta bildirim çıkıyor (başarılıysa yeşil, hata varsa kırmızı). Pencere açıkken `Enter`/`Del` arkadaki nesneye dokunmuyor.

## Gölge'ye sorulacaklar

1. Bir resim ne zaman "incelendi" sayılsın? Şu an tek kararla sayılıyor, dokunulmamış nesneler olduğu gibi aktarılıyor. Dışa aktarma penceresi bu sayıyı artık gösteriyor.
2. Maske rengi alttaki nesneyi örtüyor. Maskeyi gizleme ya da yalnızca kenar çizgisi seçeneği eklensin mi?
3. Çok parçalı maskeler ayrı satır olarak mı yazılsın, birleştirilsin mi?
4. Projede bilinmeyen sınıfın adı `misc_item` (18 + 1 sınıf). Araç şu an yalnızca `unknown` adlı sınıfı şüpheli sayıyor. `misc_item` de şüpheli sayılsın mı?
5. Proje belgesindeki üç katmanlı triage (sınıf bazlı eşik, kalibrasyon, maliyet modeli) bu araca girecek mi? Şu an tek ve sabit bir eşik var.
6. Gerçek paketten 2–3 resimlik bir örnek alabilir miyiz?
