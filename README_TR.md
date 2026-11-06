# NeoPac

**Prosedürel labirentler, kalıcı öğrenen yapay zekâ, altı oyun modu, erişilebilirlik profilleri ve klavye/fare destekli arayüze sahip neon bir siberpunk labirent oyunu.**

[English README](README.md)

NeoPac, klasik labirent-kovalama oyunlarından esinlenen bir Python/Pygame projesidir. Her seviyede üretilen yeni labirentler; kişilik sahibi Sentinel’lar; kalıcı Q-learning; farklı güç çekirdekleri; günlük mücadele; Türkçe/İngilizce arayüz; canlı performans tanılaması ve 4K’ya kadar çözünürlük bağımsız görüntü sunumu ekler.

Oyun varsayılan olarak Türkçe açılır. Dil `Görüntü → Dil` bölümünden veya aktif oyun dışında `L` tuşuyla değiştirilebilir.

## Öne Çıkan Özellikler

- Her seviyede yeni, bağlantılı ve tamamlanabilir prosedürel labirent
- Altı oyun modu ve dört zorluk seviyesi
- İsimleri doğrudan üzerlerinde görünen altı farklı güç çekirdeği
- Kendine özgü hedefi, ödülü, cezası ve özel yeteneği olan dört Sentinel
- Oyun sırasında gelişmeye devam eden kalıcı Q-learning belleği
- Türkçe ve İngilizce arayüz
- Fare, WASD, ok tuşları veya oyun koluyla kullanılabilen sekmeli menü
- Yeniden başlatma, ana menü, ses, dil, erişilebilirlik, kontrol ve güç etiketi seçenekli duraklatma menüsü
- Pencere ölçekleme, en-boy oranı koruma, hızlandırılmış tam ekran ve 4K desteği
- Az parlama, renk körü ve düşük hareket erişilebilirlik profilleri
- Her sistem için ayrı, boyutu sınırlı dönen loglar
- Canlı performans paneli ve otomatik regresyon testleri

## Gereksinimler

| Bileşen | Gereksinim |
|---|---|
| Python | 3.10 veya üzeri |
| Pygame | 2.6 veya üzeri |
| İşletim sistemi | Pygame destekli Linux, Windows veya macOS |

## Hızlı Kurulum

```bash
git clone https://github.com/ismailaydin28/neo-pac.git
cd neo-pac

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

python3 main.py
```

Windows ortamında sanal ortamı şu komutla etkinleştirin:

```powershell
.venv\Scripts\activate
```

## Oyun Kontrolleri

| Girdi | Eylem |
|---|---|
| `W` / `↑` | Yukarı hareket |
| `A` / `←` | Sola hareket |
| `S` / `↓` | Aşağı hareket |
| `D` / `→` | Sağa hareket |
| `Space` | Dash |
| `P` / `Esc` | Duraklat veya devam et |
| `R` | Mevcut oyunu yeniden başlat |
| `M` | Sesi aç/kapat |
| `F3` | Performans panelini aç/kapat |
| `F11` | Tam ekran/pencere geçişi |
| `L` | Aktif oyun dışında Türkçe/İngilizce geçişi |

Klavye düzeni `WASD + Oklar`, `Yalnız Oklar` veya `IJKL` olarak değiştirilebilir.

### Oyun Kolu

- Sol analog veya yön tuşları: hareket
- Birinci tuş: dash veya onay
- Start/Select: duraklat veya devam et
- Omuz tuşları: ana menü sekmesini değiştir

Oyun kolu bağlandığında veya çıkarıldığında cihazlar yeniden taranır.

## Sekmeli Ana Menü

Ana menü beş düzenli bölüme ayrılmıştır:

| Sekme | İçerik |
|---|---|
| Oyna | Oyunu başlat, günlük labirenti başlat, çıkış |
| Oyun | Oyun modu, zorluk, güç isimlerinin görünürlüğü |
| Görüntü | Erişilebilirlik, tam ekran, dil, performans paneli |
| Kontroller | Tuş düzeni, ses, fare durumu |
| İstatistik | Rekor, oyun sayısı, en yüksek seviye, enerji, Sentinel ve toplam puan |

### Menüde Gezinme

| Girdi | Eylem |
|---|---|
| `Q` / `E` veya `Tab` | Sekme değiştir |
| `W` / `S` veya `↑` / `↓` | Satır seç |
| `A` / `D` veya `←` / `→` | Seçili değeri değiştir |
| `Enter` / `Space` | Onayla veya çalıştır |
| Sol fare tuşu | Sekme/satır seç veya ayarı ileri değiştir |
| Sağ fare tuşu | Ayarı önceki değere getir |
| Fare tekerleği | Satırlar arasında ilerle |

Fare ana menü ve duraklatma menüsünde görünür; oyun başladığında otomatik gizlenir.

## Oyun Modları

| Mod | Kural |
|---|---|
| Klasik | Standart seviye ilerlemesi |
| Süreye Karşı | 120 saniye dolmadan mümkün olan en yüksek puan |
| Tek Can | Oyun yalnız bir canla başlar |
| Dash Yasak | Dash kullanılamaz |
| Günlük Labirent | Tarihe bağlı sabit tohum sayesinde aynı gün aynı harita oluşur |
| Sonsuz | Labirent bitince oyun durmadan sonraki seviyeye geçer |

## Zorluk Seviyeleri

Zorluk yalnız düşman hızını değil, birden fazla sistemi birlikte değiştirir.

| Zorluk | Can | Sentinel hızı | Güç süresi | AI keşfi |
|---|---:|---:|---:|---:|
| Rahat | 5 | %82 | %130 | %125 |
| Normal | 3 | %100 | %100 | %100 |
| Zor | 2 | %116 | %82 | %72 |
| Siber Kâbus | 1 | %130 | %65 | %45 |

Yüksek zorlukta keşif oranının düşmesi, eğitilmiş kararların daha tutarlı ve daha az rastgele uygulanmasını sağlar.

## Toplanabilir Nesneler ve Güç Çekirdekleri

| Nesne | Puan | Etki |
|---|---:|---|
| Enerji küresi | 10 | Standart labirent hedefi |
| Güç çekirdeği | 50 | Altı özel güçten birini etkinleştirir |
| Portal | — | Oyuncuyu tünelin diğer çıkışına taşır |

Her prosedürel labirentte altı güç çekirdeğinin her birinden tam bir tane bulunur. Renk ezberlemeye gerek kalmaması için adları çekirdeklerin doğrudan üzerinde gösterilir. İsimler `Oyun → Güç İsimleri` veya duraklatma menüsünden açılıp kapatılabilir.

| Güç | Etki |
|---|---|
| Aşırı Güç | Sentinel’ları yenilebilir yapar ve kombo puanını açar |
| Kalkan | Bir düşman darbesini engeller; en fazla iki yük tutulur |
| Zaman Dondurma | Sentinel hareketlerini geçici durdurur |
| Enerji Mıknatısı | Yakındaki enerji kürelerini otomatik toplar |
| Sahte Oyuncu | Sentinel hedefini sahte konuma yönlendirir |
| Zincir Dash | Dash bekleme süresini büyük ölçüde azaltır |

Savunmasız Sentinel’ları art arda yemek `200`, `400`, `800` ve `1600` puan verir.

## Sentinel Yapay Zekâsı

Her Sentinel’ın farklı kişiliği, hedef üretme yöntemi, öğrenme tablosu ve ödül modeli vardır.

| Sentinel | Kişilik | Temel davranış |
|---|---|---|
| Kırmızı | Chaser | Oyuncuya geçerli en kısa yoldan yaklaşır |
| Turuncu | Ambusher | Oyuncunun hareket yönündeki ileri konumu hedefler |
| Teal | Flanker | Oyuncuyu çevrelemek için yan hedeften yaklaşır |
| Mor | Explorer | Oyuncunun çevresinde kalırken yeni koridorları ödüllendirir |

### Özel Yetenekler

Özel yetenekler etkinleşmeden önce görsel uyarı verir:

- Kırmızı: geçici hızlanma
- Turuncu: pusu hedefine kilitlenme
- Teal: çevreleme hız artışı
- Mor: geçici görünmezlik/pelerin

Sentinel savunmasızken veya yeniden doğarken yetenekler devre dışıdır. Dondurulmuş Sentinel oyuncuya hasar veremez.

### Kalıcı Q-Learning

Yapay zekâ, harici makine öğrenmesi kütüphanesi gerektirmeyen hafif tabular Q-learning kullanır. Durum kodlamasında yakın duvarlar, hedefin göreli yönü, uzaklık, mevcut yön ve davranış modu bulunur.

Her kişilik farklı hareket ve olay ödülleri alır. Oyuncuyu yakalamak ödül, Aşırı Güç sırasında yenilmek cezadır. Eğitilmiş tablolar `ai_memory.json` içinde tutulur, başlangıçta yüklenir ve gerçek oyun sırasında güncellenmeye devam eder.

Periyodik kayıt oyunu bekletmez: tablolar oyun karesinde hızlıca kopyalanır, JSON kodlama ve disk yazımı arka planda yapılır. Oyun kapanırken son kayıt güvenli biçimde tamamlanır.

### İsteğe Bağlı Çevrimdışı Eğitim

```bash
python3 train_ai.py --episodes 500 --steps 80
```

Daha büyük bir eğitim çalışması:

```bash
python3 train_ai.py --episodes 5000 --steps 80
```

Sonlu durum tablosu yeterince keşfedildiğinde büyük eğitimleri tekrar tekrar çalıştırmanın getirisi azalır. Normal oyun aynı beyinleri eğitmeye devam eder.

## Prosedürel Labirent Üretimi

Labirentler; deterministik tohum, derinlik öncelikli oyma, ek döngüler, bağlantılı merkez alanı, sabit portal tünelleri ve doğrulanmış doğma noktalarıyla üretilir.

Üretim garantileri:

- Her toplanabilir nesne erişilebilir bileşendedir
- Oyuncu ve Sentinel doğma noktaları açıktır
- Portal girişleri bağlı kalır
- Altı güç çekirdeği tam birer kez bulunur
- Aynı tohum aynı labirenti tekrar üretir
- Günlük mod tarihe bağlı kararlı tohum oluşturur

Sentinel yol haritaları boyutu sınırlı ortak bir LRU önbelleğinde tutulur. Aynı hedefe giden Sentinel’lar bütün labirenti ayrı ayrı taramak yerine aynı BFS uzaklık haritasını kullanır.

## Erişilebilirlik

| Profil | Değişiklik |
|---|---|
| Standart | Tam efektler ve özgün renk paleti |
| Az Parlama | Ekran parlamasını azaltır |
| Renk Körü | Renk körü dostu Sentinel paleti kullanır |
| Düşük Hareket | Parçacık ve parlamayı azaltır; tarama çizgisi ve ekran sarsıntısını kapatır |

Erişilebilirlik oyunu yeniden başlatmadan ana menüden veya duraklatma menüsünden değiştirilebilir.

## Görüntü ve Performans

NeoPac sabit `672 × 804` mantıksal tuvale çizilir. Tuval farklı pencere boyutlarına en-boy oranı korunarak ve gerekirse siyah şerit eklenerek sunulur.

Tam ekran önce SDL donanım ölçeklemesini dener. Hızlandırılmış görüntüleyici kullanılamıyorsa oyun kapanmak yerine otomatik olarak boyutu sınırlı yazılım ölçeklemesine döner.

`F3` paneli şunları gösterir:

- Anlık FPS ve toplam kare süresi
- Olay işleme süresi
- Oyun güncelleme/çizim süresi
- Görüntü sunum/ölçekleme süresi
- Parçacık sayısı
- AI durum sayısı, mod, zorluk ve labirent tohumu

25 ms veya daha uzun süren kareler aşama süreleriyle tanılama loguna yazılır.

## Ses Sistemi

- `assets/music/neopac_theme.ogg`, döngüye uygun 16 saniyelik arka plan müziğidir
- OGG yüklenemezse sentezlenmiş yedek ses kullanılır
- Enerji, güç, dash, ölüm, seviye ve Sentinel yetenek uyarısı efektleri bulunur
- Ses aygıtı olmasa bile oyun çalışmaya devam eder

## Kalıcı ve Çalışma Zamanı Dosyaları

| Yol | Amaç | Git’e eklenir mi? |
|---|---|---|
| `ai_memory.json` | Paketlenmiş ve gelişmeye devam eden Sentinel Q tabloları | Evet |
| `profile.json` | Yerel ayarlar, skorlar ve oyuncu istatistikleri | Hayır |
| `logs/` | Tanılama ve modül logları | Hayır |
| `assets/music/neopac_theme.ogg` | Arka plan müziği | Evet |

Profil ve AI belleği, bozulma riskini azaltmak için geçici dosyaya yazılıp atomik olarak değiştirilir.

## Loglar

Loglar boyut sınırına ulaştığında otomatik döner.

| Log | İçerik |
|---|---|
| `logs/neopac.log` | Oyun yaşam döngüsü, yavaş kareler, performans özetleri, oyun olayları |
| `logs/profile.log` | Profil yükleme ve kayıt |
| `logs/game_modes.log` | Mod seçimi ve sayaçlar |
| `logs/difficulty.log` | Zorluk değişiklikleri |
| `logs/powerups.log` | Güç etkinleşme/bitiş ve kalkan kullanımı |
| `logs/sentinel_abilities.log` | Sentinel yetenek uyarıları ve etkinleşmeleri |
| `logs/accessibility.log` | Erişilebilirlik değişiklikleri |
| `logs/controls.log` | Klavye düzeni ve oyun kolu algılama |
| `logs/audio.log` | Müzik, efekt ve ses aygıtı hataları |
| `logs/menu.log` | Ana menü sekme hareketleri |

Ana log 512 KB ve üç yedekle; özellik logları 256 KB ve iki yedekle sınırlandırılmıştır.

## Proje Yapısı

```text
neo-pac/
├── main.py                    # Giriş ve ekran başlatma
├── game.py                    # Oyun döngüsü ve üst seviye durum makinesi
├── settings.py                # Genel sabitler ve renkler
├── maze.py                    # Üretim, çizim, çarpışma, yol önbelleği
├── player.py                  # Hareket, dash, çarpışma, toplama
├── enemy.py                   # Sentinel hareketi, hedefleme ve çizim
├── learning_ai.py             # Kalıcı tabular Q-learning
├── train_ai.py                # Çevrimdışı eğitim aracı
├── sentinel_abilities.py      # Kişiliğe özel yetenekler
├── powerups.py                # Altı güç ve sayaçları
├── game_modes.py              # Bağımsız oyun modu kuralları
├── difficulty.py              # Zorluk profilleri
├── accessibility.py           # Erişilebilirlik ve renk profilleri
├── controls.py                # Klavye ve oyun kolu girişi
├── menu_system.py             # Sekme ve menü seçim durumu
├── ui.py                      # HUD, menü, parçacık ve katmanlar
├── audio_manager.py           # Hata toleranslı ses yöneticisi
├── pellets.py                 # Ses sentezi ve dosya yükleme
├── profile.py                 # Kalıcı ayar ve istatistikler
├── localization.py            # Türkçe ve İngilizce metinler
├── diagnostics.py             # Dönen log ve kare izleme
├── ai_memory.json             # Eğitilmiş AI belleği
├── requirements.txt
├── assets/music/neopac_theme.ogg
└── test_*.py                  # Birim, entegrasyon, regresyon ve performans testleri
```

## Testler

Tüm testleri çalıştırmak için:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python3 -m unittest -v
```

Test kapsamı:

- Prosedürel labirent benzersizliği, bağlantısı, doğma noktaları, portallar ve güç dağılımı
- Duvara dash sonrası hareket regresyonu
- Sentinel yeniden doğuşu ve Aşırı Güç savunmasızlığı
- Üretilen labirentlerde duran oyuncunun yakalanması
- Tüm güçler, modlar, zorluklar ve erişilebilirlik profilleri
- Klavye düzenleri ve oyun kolu olayları
- Sekme hareketi, fare tıklaması ve güç ismi çizimi
- Profil kalıcılığı ve dil desteği
- Ses aygıtı hata güvenliği
- Ayrı dönen loglar
- Paylaşılan, boyutu sınırlı yol önbelleği
- Oyunu bekletmeyen AI kaydı

## Sorun Giderme

### Oyun açılıp hemen kapanıyor

Terminalden çalıştırıp `logs/neopac.log` dosyasını kontrol edin:

```bash
python3 main.py
```

### Tam ekran yavaş

`F3` ile olay, oyun veya sunum aşamalarından hangisinin yüksek olduğuna bakın. Aynı bilgiler `logs/neopac.log` içine yazılır. SDL hızlandırıcısı yoksa pencere modunu veya Düşük Hareket profilini deneyin.

### Ses gelmiyor

Oyun ses olmadan çalışmaya devam eder. Kesin aygıt veya mixer hatası `logs/audio.log` içinde bulunur.

### AI belleği bozuldu

JSON okunamazsa yükleyici güvenli biçimde boş/varsayılan tabloya döner. Eğitilmiş tabloları elle değiştirmeden önce `ai_memory.json` dosyasının kopyasını alın.

## Geliştirme Notları

- Proje bilinçli olarak hafiftir; çalışma zamanında yalnız Pygame gerekir.
- Çalışma logları ve kişisel profil Git tarafından yok sayılır.
- Paketlenmiş AI belleği oyun davranışının parçası olduğu için sürüm kontrolündedir.
- Yeni oyun sistemlerinin ayrı modül, durum tutuyorsa ayrı dönen log ve en az bir regresyon/entegrasyon testi içermesi önerilir.

