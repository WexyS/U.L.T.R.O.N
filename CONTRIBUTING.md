# Ultron AGI Katkı Rehberi

Ultron AGI'ya hoş geldiniz! Bu proje, otonom ve sürekli gelişen bir yapay zeka ekosistemi inşa etmeyi hedefler.

## 🛠 Geliştirme Standartları

1. **Kod Stili:** Python için PEP 8, TypeScript/React için Airbnb standartlarını takip ediyoruz.
2. **Ajan Modülerliği:** Her yeni ajan `ultron/v2/agents/` altında izole bir sınıf olarak tanımlanmalıdır.
3. **Güvenlik:** Yeni eklenen hiçbir tool, kullanıcı onayı olmadan sistem dosyalarını silemez veya dış ağa kontrolsüz veri gönderemez.

## 🚀 Katkı Süreci

1. Projeyi çatallayın (Fork).
2. Özelliğinizi içeren bir dal (Branch) açın: `feature/yeni-ajan-adi`.
3. Testlerinizi çalıştırın: `python test_system.py`.
4. Değişikliklerinizi açıklayan detaylı bir Pull Request (PR) oluşturun.

## 💎 Arayüz Standartları

Ultron, **Premium Aesthetic** ilkesini benimser. Tüm UI bileşenleri:
- Modern, karanlık tema uyumlu olmalıdır.
- Akıcı animasyonlar içermelidir (Framer Motion).
- Responsive (mobil uyumlu) olmalıdır.

## 🤖 Ajan Geliştirme

Yeni bir yetenek eklerken `tools` klasörüne ilgili fonksiyonu ekleyin ve bu fonksiyonun dokümantasyonunu (Docstring) çok net yazın ki Ultron bu tool'un ne işe yaradığını anlayabilsin.

---
*Eren (Administrator) onayı olmadan ana dala (Main) kod kabul edilmez.*
