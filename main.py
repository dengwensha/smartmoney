import os, requests, time, threading
from datetime import datetime

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CHECK_INTERVAL   = int(os.getenv("CHECK_INTERVAL", "60"))
TRADER_IDS       = [t.strip() for t in os.getenv("TRADER_IDS", "").split(",")]
BINANCE_CSRF     = os.getenv("BINANCE_CSRF", "")
BINANCE_UUID     = os.getenv("BINANCE_UUID", "")

# Cookie bellekte tutulur, /cookie komutuyla güncellenir
current_cookie = {"value": os.getenv("BINANCE_COOKIE", "")}
cookie_expired = {"status": False}
last_update_id = {"id": 0}


# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print(f"[TG] Hata: {e}")


def get_updates():
    """Telegram'dan yeni mesajları çeker."""
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"offset": last_update_id["id"] + 1, "timeout": 5},
            timeout=10
        )
        return r.json().get("result", [])
    except:
        return []


def handle_commands():
    """Telegram komutlarını dinler ve işler."""
    while True:
        updates = get_updates()
        for update in updates:
            last_update_id["id"] = update["update_id"]
            msg = update.get("message", {})
            text = msg.get("text", "")
            chat_id = str(msg.get("chat", {}).get("id", ""))

            # Sadece kendi chat ID'mizden gelen komutları kabul et
            if chat_id != TELEGRAM_CHAT_ID:
                continue

            if text.startswith("/cookie "):
                new_cookie = text[8:].strip()
                if len(new_cookie) > 50:
                    current_cookie["value"] = new_cookie
                    cookie_expired["status"] = False
                    send_telegram(
                        "✅ <b>Cookie güncellendi!</b>\n"
                        f"Uzunluk: {len(new_cookie)} karakter\n"
                        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                    )
                    print(f"[CMD] Cookie güncellendi ({len(new_cookie)} karakter)")
                else:
                    send_telegram("❌ Cookie çok kısa, tekrar dene.")

            elif text == "/status":
                total_pos = sum(len(v) for v in position_cache.values())
                cookie_ok = "✅ Geçerli" if not cookie_expired["status"] else "❌ Süresi dolmuş"
                send_telegram(
                    f"📊 <b>BOT DURUMU</b>\n"
                    f"Cookie: {cookie_ok}\n"
                    f"Açık pozisyon: {total_pos}\n"
                    f"Trader sayısı: {len(TRADER_IDS)}\n"
                    f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                )

            elif text == "/pozisyonlar":
                for tid, pos_map in position_cache.items():
                    if pos_map:
                        msg_text = f"📊 <b>POZİSYONLAR</b>\n"
                        for p in pos_map.values():
                            emoji = "🟢" if p["side"] == "LONG" else "🔴"
                            msg_text += f"{emoji} {p['symbol']} | {p['entryPrice']:.4f} | PnL: {p['pnl']:+.2f}\n"
                        send_telegram(msg_text)
                    else:
                        send_telegram(f"📭 {tid[:12]} — açık pozisyon yok")

            elif text == "/yardim":
                send_telegram(
                    "🤖 <b>KOMUTLAR</b>\n\n"
                    "/status — bot durumu\n"
                    "/pozisyonlar — açık pozisyonlar\n"
                    "/cookie XXXX — cookie güncelle\n"
                    "/yardim — bu menü\n\n"
                    "<b>Cookie nasıl alınır?</b>\n"
                    "1. Binance Smart Money sayfasını aç\n"
                    "2. F12 → Network → query-positions\n"
                    "3. Sağ tıkla → Copy as cURL\n"
                    "4. cURL içindeki -b \"...\" kısmını kopyala\n"
                    "5. /cookie BURAYA_YAPISTIR"
                )

        time.sleep(3)


# ── Binance API ───────────────────────────────────────────────────────────────
def get_cookies():
    c = {}
    for p in current_cookie["value"].split(";"):
        p = p.strip()
        if "=" in p:
            k, v = p.split("=", 1)
            c[k.strip()] = v.strip()
    return c


def get_positions(tid):
    try:
        r = requests.get(
            "https://www.binance.com/bapi/asset/v1/private/future/smart-money/profile/query-positions",
            headers={
                "bnc-uuid":   BINANCE_UUID,
                "csrftoken":  BINANCE_CSRF,
                "clienttype": "web",
                "lang":       "en",
                "user-agent": "Mozilla/5.0",
                "referer":    "https://www.binance.com/en/smart-money",
            },
            cookies=get_cookies(),
            params={"topTraderId": tid, "marketType": "UM", "page": 1, "rows": 20},
            timeout=10
        )
        data  = r.json()
        code  = data.get("code")

        # Cookie süresi doldu
        if code == "100001005" or r.status_code == 401:
            if not cookie_expired["status"]:
                cookie_expired["status"] = True
                send_telegram(
                    "⚠️ <b>COOKİE SÜRESİ DOLDU!</b>\n\n"
                    "Botu güncellemek için:\n"
                    "1. Binance Smart Money sayfasını aç\n"
                    "2. F12 → Network → <code>query-positions</code> isteğine sağ tıkla\n"
                    "3. <b>Copy → Copy as cURL</b>\n"
                    "4. cURL içindeki <code>-b \"...\"</code> kısmını kopyala\n"
                    "5. Bota gönder: <code>/cookie BURAYA_YAPISTIR</code>"
                )
            return []

        if code == "000000":
            cookie_expired["status"] = False
            return data.get("data", [])
        return []
    except Exception as e:
        print(f"[API] Hata: {e}")
        return []


# ── Global pozisyon cache ─────────────────────────────────────────────────────
position_cache = {}


# ── Ana Döngü ─────────────────────────────────────────────────────────────────
def main():
    global position_cache

    send_telegram(
        "🚀 <b>Smart Money Bot başlatıldı!</b>\n"
        f"👥 {len(TRADER_IDS)} trader takip ediliyor.\n"
        f"⏱ Her {CHECK_INTERVAL}s kontrol edilecek.\n\n"
        "Komutlar için /yardim yaz."
    )

    # Telegram komut dinleyicisini arka planda başlat
    t = threading.Thread(target=handle_commands, daemon=True)
    t.start()

    # Başlangıç snapshot
    for tid in TRADER_IDS:
        pos = get_positions(tid)
        position_cache[tid] = {p["symbol"]: p for p in pos}
        if pos:
            msg = f"📊 <b>MEVCUT POZİSYONLAR</b>\n"
            for p in pos:
                emoji = "🟢" if p["side"] == "LONG" else "🔴"
                msg += f"{emoji} {p['symbol']} {p['side']} | {p['entryPrice']:.4f} | PnL: {p['pnl']:+.2f}\n"
            send_telegram(msg)
        time.sleep(1)

    while True:
        time.sleep(CHECK_INTERVAL)

        for tid in TRADER_IDS:
            new     = get_positions(tid)
            new_map = {p["symbol"]: p for p in new}

            # Yeni açılan pozisyonlar
            for sym, p in new_map.items():
                if sym not in position_cache.get(tid, {}):
                    emoji = "🟢" if p["side"] == "LONG" else "🔴"
                    send_telegram(
                        f"{emoji} <b>YENİ POZİSYON AÇILDI</b>\n"
                        f"📊 {p['symbol']} — {p['side']}\n"
                        f"💰 Giriş: <b>{p['entryPrice']:.6f}</b>\n"
                        f"⚡ Kaldıraç: <b>{p['leverage']}x</b>\n"
                        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                    )

            # Kapanan pozisyonlar
            for sym, p in position_cache.get(tid, {}).items():
                if sym not in new_map:
                    emoji = "✅" if p["pnl"] >= 0 else "❌"
                    send_telegram(
                        f"{emoji} <b>POZİSYON KAPANDI</b>\n"
                        f"📊 {p['symbol']} — {p['side']}\n"
                        f"💵 PnL: <b>{p['pnl']:+.2f} USDT</b>\n"
                        f"📈 ROI: <b>{p['roi']*100:+.2f}%</b>\n"
                        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                    )

            position_cache[tid] = new_map
            time.sleep(0.5)


if __name__ == "__main__":
    main()
