# Game Development — UE5 Blueprint & Production

Unreal Engine 5 ve büyük ölçekli oyun motorları için pratik rehber. Blueprint ile hızlı iterasyon;
performans kritik yollarda C++ / Nativize değerlendirilir.

## Blueprint çekirdeği

- **Event Graph**: `Event BeginPlay`, `Tick`, custom events; maliyetli işleri Tick’ten çıkar.
- **Veri**: `Blueprint Interface` ile gevşek bağlantı; `Gameplay Tags` ile durum filtresi.
- **Input**: Enhanced Input Actions / Mapping Context; platform farklarını burada soyutla.
- **UI**: UMG widget’ları ile model–view ayrımı; oyun durumu için MVVM benzeri katman.

## Mimari

- **Subsystems** (Game Instance / World): oturum ve dünya ömrü servisleri.
- **GAS (Gameplay Ability System)**: yetenek, efekt, öznitelik; çok oyunculu senk için tercih.
- **Replication**: minimal RPC; mümkün olduğunca `FastArraySerializer` ve property replication.

## İçerik ve seviye

- Streaming Level / World Partition büyük dünyalar için.
- LOD, Nanite (statik mesh), Lumen (global aydınlatma) ayarları hedef platforma göre.

## UE ↔ harici AI çoklu ajan

- Tasarım dokümanını (GDD) tek kaynak yap; kod üreten ajan ile Blueprint taslağı üreten ajanı aynı şema üzerinde tut.
- Otomasyon: Data Asset / Primary Data Asset ile parametrik içerik.

## Çıktı formatı

Kullanıcı isteğine göre: node listesi, pseudo-C++/Blueprint isimleri, risk uyarıları ve test adımları.
