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
| Pzt 26 | 4 | Onayla / sınıf değiştir / sil, `reviews/` kaydı 📸 | ⬜ |
| Sal 27 | 5 | Şüpheliler: eşik kaydırıcısı, rozet, öne alma | ⬜ |
| Sal 27 | 6 | Resim durumu, ilerleme sayacı, sıradaki bekleyen | ⬜ |
| Çar 28 | 7 | YOLO-seg dışa aktarma 📸 | ⬜ |
| Per 29 | 8 | Aday maskeler: göster, tıkla, sınıf ver, ekle | ⬜ |
| Cum 30 | — | Tampon: hata düzeltme, çalıştırma talimatları | ⬜ |

## Çalıştırma

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

## Git düzeni

İsimlendirmeler İngilizce: repo, dal, etiket, commit mesajı, dosya/klasör, değişken ve fonksiyon adları. Belgeler (README, PLAN) Türkçe kalır.

- GitHub reposu: `label-review-tool`
- Şimdilik tek dal: `main`. Her adım bir veya birkaç commit, mesaj biçimi: `step-N: short description` (örn. `step-2: draw masks as SVG overlay`).
- Her adım bitince etiket: `step-N` (örn. `git checkout step-4` ile o anki hâline dönülebilir).
- Ekip katıldığında: her iş için `step-N-short-name` dalı açılır (örn. `step-5-suspect-filter`), Pull Request ile `main`'e birleştirilir.

## Günlük

Her gün sonunda bir satır: ne yapıldı, ne kaldı, sorun var mı.

- **21 Ekim:** Yerel repo kuruldu, plan yazıldı.
- **24 Ekim:** GitHub reposu bağlandı: https://github.com/Tunahann-coban/label-review-tool. Takvim 3 gün kaydırıldı. Adım 0 ve 1 bitti: servis paketi okuyor, sayfa 3 resim arasında geziyor. Servis kapalıyken sayfa uyarı verip tekrar deniyor. Adım 2 de bitti: maskeler her nesneye ayrı renkle, sınıf adı ve skorla çiziliyor. Ekran küçülünce de hizalı kalıyor (%59 ölçekte test edildi). Adım 3 bitti: sağda nesne listesi, listeden ya da resimden seçme, kalın kenarla vurgu. Örtüşen maskelerde küçük olan seçiliyor. Boş alana tıklayınca seçim kalkıyor, resim değişince sıfırlanıyor.
