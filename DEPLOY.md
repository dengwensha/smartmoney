# Smart Money Bot — Render Deploy Rehberi

## 1. GitHub'a Yükle

```bash
git init
git add .
git commit -m "Smart Money Bot"
git remote add origin https://github.com/KULLANICI_ADIN/smart-money-bot.git
git push -u origin main
```

## 2. Render'da Servis Oluştur

1. render.com → "New +" → "Web Service"
2. GitHub repo'nu bağla
3. Şu ayarları gir:

| Alan | Değer |
|------|-------|
| Name | smart-money-bot |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python server.py` |
| Plan | Free |

## 3. Environment Variables Ekle

Render → servis → "Environment" sekmesi:

| Key | Value |
|-----|-------|
| TELEGRAM_TOKEN | 8480918512:AAEGmuyQ... |
| TELEGRAM_CHAT_ID | 1134337706 |
| TRADER_IDS | 4936522826423009536 |
| CHECK_INTERVAL | 60 |
| BINANCE_COOKIE | (tarayıcıdan kopyala - aşağıda açıklama) |
| BINANCE_CSRF | 1e4aa841fbe01d92daba3491229579a0 |
| BINANCE_UUID | 13c0ac09-10b9-416c-ba88-83dd8cab7078 |

## 4. BINANCE_COOKIE Nasıl Alınır

1. Chrome → Binance Smart Money sayfası
2. F12 → Network → isteğe sağ tıkla → "Copy as cURL"
3. cURL içindeki `-b "..."` kısmındaki tüm cookie string'ini kopyala
4. Render'da BINANCE_COOKIE değerine yapıştır

## 5. Cookie Süresi Dolarsa

Cookie birkaç günde bir süresi dolar. Dolduğunda:
1. Telegram'dan "boş pozisyon" bildirimleri gelmeye başlar
2. Tarayıcıdan yeni cookie al
3. Render → Environment → BINANCE_COOKIE güncelle → "Save Changes"
4. Servis otomatik yeniden başlar

## Birden Fazla Trader Takibi

TRADER_IDS değerine virgülle ekle:
```
4936522826423009536,1234567890123456789,9876543210987654321
```
