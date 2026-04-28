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
        print(f"[TG] Hata: {e}")

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
                "bnc-uuid":    BINANCE_UUID,
                "csrftoken":   BINANCE_CSRF,
                "clienttype":  "web",
                "lang":        "en",
                "user-agent":  "Mozilla/5.0",
                "referer":     "https://www.binance.com/en/smart-money",
            },
            cookies=get_cookies(),
            params={"topTraderId": tid, "marketType": "UM", "page": 1, "rows": 20},
            timeout=10
        )
        data = r.json()
        code  = data.get("code")
        items = data.get("data", [])
        print(f"[API] {tid[:12]} | status:{r.status_code} | code:{code} | count:{len(items)}")
        if code == "000000":
            return items
        else:
            print(f"[API] Hata mesaji: {data.get('message')}")
            return []
    except Exception as e:
        print(f"[API] Istek hatasi: {e}")
        return []

def main():
    print("Bot baslatildi")
    print(f"Trader sayisi: {len(TRADER_IDS)}")
    print(f"Cookie uzunlugu: {len(BINANCE_COOKIE)}")

    send_telegram("🚀 <b>Bot başlatıldı!</b>")

    cache = {}
    for tid in TRADER_IDS:
        print(f"[INIT] {tid}")
        pos = get_positions(tid)
        cache[tid] = {p["symbol"]: p for p in pos}
        print(f"[INIT] {tid[:12]} | {len(pos)} pozisyon")

        if pos:
            msg = f"📊 <b>MEVCUT POZİSYONLAR</b>\n"
            for p in pos:
                emoji = "🟢" if p["side"] == "LONG" else "🔴"
                msg += f"{emoji} {p['symbol']} {p['side']} | Giriş: {p['entryPrice']:.4f} | PnL: {p['pnl']:+.2f}\n"
            send_telegram(msg)
        else:
            send_telegram(f"⚠️ Trader {tid[:12]} — açık pozisyon yok")
        time.sleep(1)

    while True:
        time.sleep(CHECK_INTERVAL)
        print(f"[CHECK] {datetime.now().strftime('%H:%M:%S')}")
        for tid in TRADER_IDS:
            new     = get_positions(tid)
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
