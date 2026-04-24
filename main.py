"""
main.py — Binance Smart Money Monitor + Telegram Bot
-----------------------------------------------------
Render'da 7/24 çalışır, yeni pozisyon açılınca/kapanınca Telegram'a bildirir.
"""

import os
import requests
import time
import json
from datetime import datetime

# ── Ayarlar (environment variable olarak set edilecek) ───────────────────────
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN", "8480918512:AAEGmuyQ3hd2rbUcV8tj1dD0RyI_3KS3qnY")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1134337706")
CHECK_INTERVAL  = int(os.getenv("CHECK_INTERVAL", "60"))  # saniye

# Takip edilecek trader ID'leri (virgülle ayır)
TRADER_IDS = os.getenv("TRADER_IDS", "4936522826423009536").split(",")

# Binance cookie (Render'da env var olarak sakla)
BINANCE_COOKIE  = os.getenv("BINANCE_COOKIE", "")
BINANCE_CSRF    = os.getenv("BINANCE_CSRF", "1e4aa841fbe01d92daba3491229579a0")
BINANCE_UUID    = os.getenv("BINANCE_UUID", "13c0ac09-10b9-416c-ba88-83dd8cab7078")
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
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       message,
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code != 200:
            print(f"Telegram hata: {r.text}")
    except Exception as e:
        print(f"Telegram bağlantı hatası: {e}")


# ── Binance API ───────────────────────────────────────────────────────────────
def get_cookies() -> dict:
    """Her istekte güncel cookie'yi env'den okur."""
    cookie_str = os.getenv("BINANCE_COOKIE", "")
    cookies = {}
    for part in cookie_str.split(";"):
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
        data = r.json()
        if data.get("code") == "000000":
            return data.get("data", [])
    except Exception as e:
        print(f"Pozisyon fetch hatası ({trader_id}): {e}")
    return []


def get_profile(trader_id: str) -> dict:
    url = f"https://www.binance.com/bapi/asset/v1/private/future/smart-money/profile?topTraderId={trader_id}"
    try:
        r = requests.get(url, headers=HEADERS, cookies=get_cookies(), timeout=10)
        return r.json().get("data", {})
    except:
        return {}


# ── Pozisyon Karşılaştırma ────────────────────────────────────────────────────
def compare_positions(old: list, new: list) -> dict:
    """Eski ve yeni pozisyonları karşılaştırır."""
    old_map = {p["symbol"]: p for p in old}
    new_map = {p["symbol"]: p for p in new}

    opened = []   # yeni açılan
    closed = []   # kapanan
    changed = []  # değişen (PnL güncelleme)

    for sym, pos in new_map.items():
        if sym not in old_map:
            opened.append(pos)

    for sym, pos in old_map.items():
        if sym not in new_map:
            closed.append(pos)

    return {"opened": opened, "closed": closed}


# ── Bildirim Mesajları ────────────────────────────────────────────────────────
def format_open_msg(trader_name: str, pos: dict) -> str:
    emoji = "🟢" if pos["side"] == "LONG" else "🔴"
    pnl_emoji = "📈" if pos["pnl"] >= 0 else "📉"
    return (
        f"{emoji} <b>YENİ POZİSYON AÇILDI</b>\n"
        f"👤 Trader: <b>{trader_name}</b>\n"
        f"📊 Sembol: <b>{pos['symbol']}</b>\n"
        f"📍 Yön: <b>{pos['side']}</b>\n"
        f"💰 Giriş Fiyatı: <b>{pos['entryPrice']:.6f}</b>\n"
        f"📦 Miktar: <b>{pos['amount']}</b>\n"
        f"⚡ Kaldıraç: <b>{pos['leverage']}x</b>\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
    )


def format_close_msg(trader_name: str, pos: dict) -> str:
    pnl = pos["pnl"]
    roi = pos["roi"] * 100
    emoji = "✅" if pnl >= 0 else "❌"
    return (
        f"{emoji} <b>POZİSYON KAPATILDI</b>\n"
        f"👤 Trader: <b>{trader_name}</b>\n"
        f"📊 Sembol: <b>{pos['symbol']}</b>\n"
        f"📍 Yön: <b>{pos['side']}</b>\n"
        f"💵 PnL: <b>{pnl:+.2f} USDT</b>\n"
        f"📈 ROI: <b>{roi:+.2f}%</b>\n"
        f"🕐 {datetime.now().strftime('%H:%M:%S')}"
    )


def format_summary(profiles: list) -> str:
    lines = ["📋 <b>DURUM ÖZETİ</b>\n"]
    for name, positions in profiles:
        total_pnl = sum(p["pnl"] for p in positions)
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        lines.append(
            f"👤 {name}\n"
            f"   Açık Pozisyon: {len(positions)}\n"
            f"   {pnl_emoji} Toplam PnL: {total_pnl:+.2f} USDT\n"
        )
    lines.append(f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    return "\n".join(lines)


# ── Ana Döngü ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  Smart Money Monitor başlatıldı")
    print(f"  Trader sayısı : {len(TRADER_IDS)}")
    print(f"  Kontrol aralığı: {CHECK_INTERVAL}s")
    print("=" * 55)

    send_telegram(
        "🚀 <b>Smart Money Monitor başlatıldı!</b>\n"
        f"👥 {len(TRADER_IDS)} trader takip ediliyor.\n"
        f"⏱ Her {CHECK_INTERVAL} saniyede kontrol edilecek."
    )

    # Başlangıç snapshot
    position_cache = {}
    trader_names   = {}

    for tid in TRADER_IDS:
        profile = get_profile(tid)
        trader_names[tid] = profile.get("traderName", f"Trader_{tid[:8]}")
        position_cache[tid] = {p["symbol"]: p for p in get_positions(tid)}
        print(f"  ✓ {trader_names[tid]} — {len(position_cache[tid])} pozisyon yüklendi")
        time.sleep(0.5)

    summary_counter = 0

    while True:
        time.sleep(CHECK_INTERVAL)
        summary_counter += 1
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Kontrol ediliyor...")

        current_profiles = []

        for tid in TRADER_IDS:
            name      = trader_names[tid]
            new_pos   = get_positions(tid)
            new_map   = {p["symbol"]: p for p in new_pos}
            old_map   = position_cache[tid]

            current_profiles.append((name, new_pos))

            diff = compare_positions(list(old_map.values()), new_pos)

            for pos in diff["opened"]:
                print(f"  🟢 YENİ: {pos['symbol']} {pos['side']} [{name}]")
                send_telegram(format_open_msg(name, pos))

            for pos in diff["closed"]:
                print(f"  ❌ KAPANDI: {pos['symbol']} [{name}]")
                send_telegram(format_close_msg(name, pos))

            position_cache[tid] = new_map
            time.sleep(0.5)

        # Her 30 kontrolde bir özet gönder
        if summary_counter % 30 == 0:
            send_telegram(format_summary(current_profiles))
            summary_counter = 0

        print(f"  Toplam açık pozisyon: {sum(len(v) for v in position_cache.values())}")


if __name__ == "__main__":
    main()
