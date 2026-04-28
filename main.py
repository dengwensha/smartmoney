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
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)

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
            headers={"bnc-uuid": BINANCE_UUID, "csrftoken": BINANCE_CSRF,
                     "clienttype": "web", "lang": "en",
                     "user-agent": "Mozilla/5.0", "referer": "https://www.binance.com/en/smart-money"},
            cookies=get_cookies(),
            params={"topTraderId": tid, "marketType": "UM", "page": 1, "rows": 20},
            timeout=10)
        print(f"[API] {tid[:12]} | status:{r.status_code} | code:{r.json().get('code')} | count:{len(r.json().get('data',[]))}")
        return r.json().get("data", [])
    except Exception as e:
        print(f"[API] Hata: {e}")
        return []

def main():
    print("Bot baslatildi")
    send_telegram("🚀 Bot başlatıldı! Test mesajı.")
    cache = {}
    for tid in TRADER_IDS:
        pos = get_positions(tid)
        cache[tid] = {p["symbol"]: p for p in pos}
        print(f"[INIT] {tid[:12]} | {len(pos)} pozisyon")
        send_telegram(f"👤 Trader {tid[:12]}\nPozisyon: {len(pos)}\nKod kontrol: logları gör")
        time.sleep(1)
    while True:
        time.sleep(CHECK_INTERVAL)
        print(f"[CHECK] {datetime.now().strftime('%H:%M:%S')}")
        for tid in TRADER_IDS:
            new = get_positions(tid)
            new_map = {p["symbol"]: p for p in new}
            for sym, p in new_map.items():
                if sym not in cache[tid]:
                    send_telegram(f"🟢 YENİ POZİSYON\n{p['symbol']} {p['side']}\nGiriş: {p['entryPrice']}")
            for sym, p in cache[tid].items():
                if sym not in new_map:
                    send_telegram(f"❌ KAPANDI\n{p['symbol']} PnL: {p['pnl']:+.2f}")
            cache[tid] = new_map

if __name__ == "__main__":
    main()
