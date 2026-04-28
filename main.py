"""
main.py — Binance Smart Money Monitor + Telegram Bot
-----------------------------------------------------
Render'da 7/24 çalışır, yeni pozisyon açılınca/kapanınca Telegram'a bildirir.
"""

import os
import requests
import time
from datetime import datetime

# ── Ayarlar ──────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
CHECK_INTERVAL   = int(os.getenv("CHECK_INTERVAL", "60"))
TRADER_IDS       = os.getenv("TRADER_IDS", "").split(",")
BINANCE_COOKIE   = os.getenv("BINANCE_COOKIE", "")
BINANCE_CSRF     = os.getenv("BINANCE_CSRF", "")
BINANCE_UUID     = os.getenv("BINANCE_UUID", "")
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "accept":        "*/*",
    "clienttype":    "web",
    "content-type":  "application/json",
    "lang":          "en",
    "bnc-uuid":      BINANCE_UUID,
    "csrftoken":     BINANCE_CSRF,
    "user-agent":    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "referer":       "https://www.binance.com/en/smart-money",
}


# ── Telegram ──────────────────────────────────────────────────────────────────
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            print(f"  [TG] Mesaj gönderildi ✓")
        else:
            print(f"  [TG] Hata: {r.text}")
    except Exception as e:
        print(f"  [TG] Bağlantı hatası: {e}")


# ── Binance API ───────────────────────────────────────────────────────────────
def get_cookies() -> dict:
    cookies = {}
    for part in BINANCE_COOKIE.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


def get_positions(trader_id: str) -> list:
    url = "https://www.binance.com/bapi/asset/v1/private/future/smart-money/profile/query-positions"
    params = {"topTraderId": trader_id, "marketType": "UM", "page": 1, "rows": 20}
    try:
        r = requests.get(url, headers=HEADERS, cookies=get_cookies(), params=params, timeout=10)
        print(f"  [API] {trader_id[:12]}... status: {r.status_code}")
        data = r.json()
        code = data.get("code")
        print(f"  [API] code: {code} | veri sayısı: {len(data.get('data', []))}")
        if code == "000000":
            return data.get("data", [])
        else:
            print(f"  [API] Hata mesajı: {data.get('message')}")
    except Exception as e:
        print(f"  [API] İstek hatası: {e}")
    return []


def get_profile(trader_id: str) -> dict:
    url = f"https://www.binance.com/bapi/asset/v1/private/future/smart-money/profile?topTraderId={trader_id}"
    try:
        r = requests.get(url, headers=HEADERS, cookies=get_cookies(), timeout=10)
        data = r.json()
        return data.get("data", {})
    except Exception as e:
        print(f"  [API] Profil hatası: {e}")
        return {}


# ── Karşılaştırma ─────────────────────────────────────────────────────────────
def compare_positions(old_map: dict, new_list: list) -> dict:
    new_map = {p["symbol"]: p for p in new_list}
    opened = [p for sym, p in new_map.items() if sym not in old_map]
    closed = [p for sym, p in old_map.items() if sym not in new_map]
    return {"opened": opened, "closed": closed, "new_map": new_map}


# ── Mesaj Formatları ──────────────────────────────────────────────────────────
def format_open_msg(trader_name: str, pos: dict) -> str:
    emoji = "🟢" if pos["side"] == "LONG" else "🔴"
    return (
        f"{emoji} <b>YENİ POZİSYON AÇILDI</b>\n"
        f"👤 Trader: <b>{trader_name}</b>\n"
        f"📊 Sembol: <b>{pos['symbol']}</b>\n"
        f"📍 Yön: <b>{pos['side']}</b>\n"
        f"💰 Giriş: <b>{pos['entryPrice']:.6f}</b>\n"
        f"📦 Miktar: <b>{pos['amount']}</b>\n"
        f"⚡ Kaldıraç: <b>{pos['leverage']}x</b>\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
    )


def format_close_msg(trader_name: str, pos: dict) -> str:
    emoji = "✅" if pos["pnl"] >= 0 else "❌"
    return (
        f"{emoji} <b>POZİSYON KAPATILDI</b>\n"
        f"👤 Trader: <b>{trader_name}</b>\n"
        f"📊 Sembol: <b>{pos['symbol']}</b>\n"
        f"📍 Yön: <b>{pos['side']}</b>\n"
        f"💵 PnL: <b>{pos['pnl']:+.2f} USDT</b>\n"
        f"📈 ROI: <b>{pos['roi']*100:+.2f}%</b>\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
    )


# ── Ana Döngü ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  Smart Money Monitor başlatıldı")
    print(f"  Trader sayısı  : {len(TRADER_IDS)}")
    print(f"  Check interval : {CHECK_INTERVAL}s")
    print(f"  Cookie uzunluğu: {len(BINANCE_COOKIE)} karakter")
    print("=" * 55)

    # Başlangıç snapshot
    position_cache = {}
    trader_names   = {}
    startup_msg    = f"🚀 <b>Smart Money Monitor başlatıldı!</b>\n👥 {len(TRADER_IDS)} trader takip ediliyor.\n\n"

    for tid in TRADER_IDS:
        tid = tid.strip()
        print(f"\n[INIT] Trader yükleniyor: {tid}")
        profile = get_profile(tid)
        name    = profile.get("traderName", f"Trader_{tid[:8]}")
        sharing = profile.get("sharingPosition", False)
        trader_names[tid] = name

        positions = get_positions(tid)
        position_cache[tid] = {p["symbol"]: p for p in positions}

        print(f"  → {name} | paylaşım:{sharing} | pozisyon:{len(positions)}")
        startup_msg += f"👤 {name}\n   Paylaşım: {'✅' if sharing else '❌'} | Pozisyon: {len(positions)}\n"
        time.sleep(1)

    send_telegram(startup_msg)

    # Mevcut açık pozisyonları bildir
    for tid, pos_map in position_cache.items():
        if pos_map:
            name = trader_names[tid]
            msg  = f"📊 <b>MEVCUT POZİSYONLAR — {name}</b>\n\n"
            for p in pos_map.values():
                emoji = "🟢" if p["side"] == "LONG" else "🔴"
                msg  += f"{emoji} {p['symbol']} {p['side']} | {p['entryPrice']:.4f} | PnL: {p['pnl']:+.2f}\n"
            send_telegram(msg)

    summary_counter = 0

    while True:
        time.sleep(CHECK_INTERVAL)
        summary_counter += 1
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Kontrol #{summary_counter}")

        for tid in TRADER_IDS:
            tid  = tid.strip()
            name = trader_names.get(tid, tid[:12])
            new_positions = get_positions(tid)
            diff = compare_positions(position_cache[tid], new_positions)

            for pos in diff["opened"]:
                print(f"  🟢 YENİ: {pos['symbol']} {pos['side']} [{name}]")
                send_telegram(format_open_msg(name, pos))

            for pos in diff["closed"]:
                print(f"  ❌ KAPANDI: {pos['symbol']} [{name}]")
                send_telegram(format_close_msg(name, pos))

            position_cache[tid] = diff["new_map"]
            time.sleep(0.5)

        total = sum(len(v) for v in position_cache.values())
        print(f"  Toplam açık: {total} | Sonraki kontrol: {CHECK_INTERVAL}s")

        # Her 30 kontrolde bir özet
        if summary_counter % 30 == 0:
            msg = f"📋 <b>DURUM ÖZETİ</b>\n🕐 {datetime.now().strftime('%H:%M')}\n\n"
            for tid, pos_map in position_cache.items():
                name = trader_names.get(tid, tid[:12])
                total_pnl = sum(p["pnl"] for p in pos_map.values())
                msg += f"👤 {name} | {len(pos_map)} pozisyon | PnL: {total_pnl:+.2f}\n"
            send_telegram(msg)
            summary_counter = 0


if __name__ == "__main__":
    main()
