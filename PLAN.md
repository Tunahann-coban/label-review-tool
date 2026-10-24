# Çalışma Planı

Ayrıntılı kapsam ve veri biçimi için [README.md](README.md). Bu dosya sadece takvim ve ilerleme durumunu tutar.

Durum: ✅ bitti · ⏳ sürüyor · ⬜ başlamadı · 📸 Gölge'ye ekran görüntüsü

## Hafta 1 (21–27 Ekim 2026)

| Gün | Adım | İş | Durum |
|---|---|---|---|
| Çar 21 | — | Repo kurulumu (`label-review-tool`), `.gitignore`, plan | ✅ |
| Çar 21 | 0 | FastAPI servisi ↔ React sayfası "merhaba" | ⬜ |
| Çar 21 | 1 | Sahte paket, `annotations.json` okuma, önceki/sonraki | ⬜ |
| Per 22 | 2 | Maskeleri SVG ile çiz, etiket adları 📸 | ⬜ |
| Cum 23 | 3 | Nesne listesi, seçme, resme tıklayarak seçme | ⬜ |
| Cum 23 | 4 | Onayla / sınıf değiştir / sil, `reviews/` kaydı 📸 | ⬜ |
| Cmt 24 | 5 | Şüpheliler: eşik kaydırıcısı, rozet, öne alma | ⬜ |
| Cmt 24 | 6 | Resim durumu, ilerleme sayacı, sıradaki bekleyen | ⬜ |
| Paz 25 | 7 | YOLO-seg dışa aktarma 📸 | ⬜ |
| Pzt 26 | 8 | Aday maskeler: göster, tıkla, sınıf ver, ekle | ⬜ |
| Sal 27 | — | Tampon: hata düzeltme, çalıştırma talimatları | ⬜ |

## Git düzeni

İsimlendirmeler İngilizce: repo, dal, etiket, commit mesajı, dosya/klasör, değişken ve fonksiyon adları. Belgeler (README, PLAN) Türkçe kalır.

- GitHub reposu: `label-review-tool`
- Şimdilik tek dal: `main`. Her adım bir veya birkaç commit, mesaj biçimi: `step-N: short description` (örn. `step-2: draw masks as SVG overlay`).
- Her adım bitince etiket: `step-N` (örn. `git checkout step-4` ile o anki hâline dönülebilir).
- Ekip katıldığında: her iş için `step-N-short-name` dalı açılır (örn. `step-5-suspect-filter`), Pull Request ile `main`'e birleştirilir.

## Günlük

Her gün sonunda bir satır: ne yapıldı, ne kaldı, sorun var mı.

- **21 Ekim:** Yerel repo kuruldu, plan yazıldı.
- **24 Ekim:** GitHub reposu bağlandı: https://github.com/Tunahann-coban/label-review-tool
