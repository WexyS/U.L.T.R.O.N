# Autonomous Goal Runner (OpenClaw-style)

Bu skill, Ultron orkestratörünün **otonom** modunda kullanılır: kullanıcı hedefi net ise
plan üretir, alt adımları sırayla veya paralel yürütür, sonuçları birleştirir.

## Davranış

1. Hedefi tek cümlede netleştir (çıktı, kısıtlar, dil).
2. Alt görevleri atomik parçalara böl (kod, araştırma, dosya, sistem).
3. Her adım için uygun ajanı seç; RPA ve sistem komutlarında kullanıcı onayı gerektiğini hatırlat.
4. Başarısız adımda alternatif veya basitleştirilmiş plan öner.
5. Sonunda özet + doğrulama maddeleri (checklist) ver.

## Tetikleyici anahtar kelimeler

`otonom`, `autonomous`, `işi bitir`, `görevi tamamla`, `openclaw`, `plan yap ve uygula`

## Güvenlik

- Üretimde yürütülecek kodu çalıştırmadan önce güvenlik taraması varsayılan olarak açıktır.
- Şüpheli shell / silme komutlarını asla önerme; kullanıcıya risk bildir.
