"""
server.py — Render'ın uyutmaması için minimal web sunucusu
Bot arka planda çalışırken bu sunucu Render'ı uyanık tutar.
"""

import threading
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import main as bot

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Smart Money Bot is running!")

    def log_message(self, format, *args):
        pass  # log spam'i engelle

def run_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health server port {port} üzerinde çalışıyor")
    server.serve_forever()

if __name__ == "__main__":
    # Web sunucusunu arka planda başlat
    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    # Botu çalıştır
    bot.main()
