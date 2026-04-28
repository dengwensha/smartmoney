import os, requests, time
from datetime import datetime

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CHECK_INTERVAL   = int(os.getenv("CHECK_INTERVAL", "60"))
TRADER_IDS       = [t.strip() for t in os.getenv("TRADER_IDS", "").split(",")]
BINANCE_COOKIE   = os.getenv("BINANCE_COOKIE", "")
BINANCE_CSRF     = os.getenv("BINANCE_CSRF", "")
BINANCE_UUID     = os.getenv("BINANCE_UUID", "")

def send_telegram(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        pass

def get_cookies():
    c = {}
    for p in BINANCE_COOKIE.split(";"):
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
        items = data.get("data", [])
        msg   = data.get("message", "")
        return r.status_code, code, items, msg
    except Exception as e:
        return 0, "EXCEPTION", [], str(e)

def main():
    # Debug: cookie uzunluğu ve env kontrol
    send_telegram(
        f"🔧 <b>DEBUG BAŞLADI</b>\n"
        f"Cookie uzunluğu: {len(BINANCE_COOKIE)}\n"
        f"CSRF: {BINANCE_CSRF[:10]}...\n"
        f"UUID: {BINANCE_UUID[:10]}...\n"
        f"Trader sayısı: {len(TRADER_IDS)}"
    )

    cache = {}
    for tid in TRADER_IDS:
        status, code, items, msg = get_positions(tid)

        # API sonucunu Telegram'a gönder
        send_telegram(
            f"🔍 <b>API SONUCU</b>\n"
            f"Trader: {tid[:16]}\n"
            f"HTTP Status: {status}\n"
            f"API Code: {code}\n"
            f"Pozisyon: {len(items)}\n"
            f"Mesaj: {msg[:100] if msg else 'yok'}"
        )

        cache[tid] = {p["symbol"]: p for p in items}
        if items:
            pos_msg = f"📊 <b>AÇIK POZİSYONLAR</b>\n"
            for p in items:
                emoji = "🟢" if p["side"] == "LONG" else "🔴"
                pos_msg += f"{emoji} {p['symbol']} {p['side']} | {p['entryPrice']:.4f} | PnL: {p['pnl']:+.2f}\n"
            send_telegram(pos_msg)
        time.sleep(1)

    while True:
        time.sleep(CHECK_INTERVAL)
        for tid in TRADER_IDS:
            _, _, new, _ = get_positions(tid)
            new_map = {p["symbol"]: p for p in new}

            for sym, p in new_map.items():
                if sym not in cache[tid]:
                    emoji = "🟢" if p["side"] == "LONG" else "🔴"
                    send_telegram(
                        f"{emoji} <b>YENİ POZİSYON</b>\n"
                        f"📊 {p['symbol']} — {p['side']}\n"
                        f"💰 Giriş: {p['entryPrice']:.6f}\n"
                        f"⚡ Kaldıraç: {p['leverage']}x\n"
                        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                    )

            for sym, p in cache[tid].items():
                if sym not in new_map:
                    emoji = "✅" if p["pnl"] >= 0 else "❌"
                    send_telegram(
                        f"{emoji} <b>POZİSYON KAPANDI</b>\n"
                        f"📊 {p['symbol']} — {p['side']}\n"
                        f"💵 PnL: {p['pnl']:+.2f} USDT\n"
                        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
                    )

            cache[tid] = new_map
            time.sleep(0.5)

if __name__ == "__main__":
    main()
