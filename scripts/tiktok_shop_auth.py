"""Interactive TikTok Shop OAuth Authorization Helper.
Launches authorization flow, starts a temporary callback listener on port 3000,
and exchanges authorization code for official TikTok Shop access tokens.
"""

import http.server
import json
import logging
import socketserver
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tiktok_shop_service import TikTokShopService
from src.config import TIKTOK_SHOP_APP_KEY, TIKTOK_SHOP_APP_SECRET, TIKTOK_SHOP_REDIRECT_URI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("tiktok_shop_auth")

captured_auth_code = None
server_instance = None


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global captured_auth_code, server_instance
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        if "code" in query_params or "auth_code" in query_params:
            captured_auth_code = query_params.get("code", query_params.get("auth_code"))[0]
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            success_html = """
            <html>
            <head><title>TikTok Shop Authorization Success</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px; background: #0f172a; color: white;">
                <h1 style="color: #22c55e;">✅ Autentikasi TikTok Shop Berhasil!</h1>
                <p>Kode otorisasi berhasil ditangkap oleh sistem Velora AI.</p>
                <p>Anda dapat menutup jendela browser ini dan kembali ke terminal Anda.</p>
            </body>
            </html>
            """
            self.wfile.write(success_html.encode("utf-8"))
            logger.info("Captured authorization code: %s", captured_auth_code)

            # Shutdown server in separate thread after responding
            def stop():
                if server_instance:
                    server_instance.shutdown()
            threading.Thread(target=stop).start()
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Waiting for authorization code...")

    def log_message(self, format, *args):
        # Silence standard HTTP access logs
        pass


def start_callback_listener(port: int = 3000):
    global server_instance
    try:
        server_instance = socketserver.TCPServer(("127.0.0.1", port), CallbackHandler)
        logger.info("Local callback server listening at http://127.0.0.1:%d/callback", port)
        server_instance.serve_forever()
    except Exception as e:
        logger.warning("Could not start local listener on port %d: %s", port, e)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    service = TikTokShopService()

    if not service.app_key or not service.app_secret:
        print("❌ Kredensial TIKTOK_SHOP_APP_KEY atau TIKTOK_SHOP_APP_SECRET belum diisi di .env!")
        return

    creator_url = service.get_creator_auth_url()
    seller_url = service.get_seller_auth_url()

    print("=" * 65)
    print("🛍️ VELORA AI — TIKTOK SHOP OPEN PLATFORM OAUTH HELPER")
    print("=" * 65)
    print(f"App Key   : {service.app_key}")
    print(f"App Secret: {'*' * 10} (Terdaftar)")
    print(f"Callback  : {service.redirect_uri}")
    print("-" * 65)
    print("Pilih tipe otorisasi yang ingin Anda gunakan:")
    print("1. Otorisasi Creator Affiliate (Etalase & Showcase Keranjang Kuning)")
    print("2. Otorisasi Toko Penjual / Seller Center")
    print("3. Masukkan Authorization Code secara manual")
    print("4. Cek Status Token Saat Ini")
    print("5. Keluar")
    print("=" * 65)

    choice = input("👉 Pilihan [1-5]: ").strip()

    if choice == "1":
        print("\n🌐 Buka URL berikut di browser Anda untuk mengotorisasi Creator Affiliate:")
        print(f"👉 {creator_url}\n")
        print("⏳ Menunggu redirect ke http://127.0.0.1:3000/callback...")
        t = threading.Thread(target=start_callback_listener, args=(3000,), daemon=True)
        t.start()
        try:
            webbrowser.open(creator_url)
        except Exception:
            pass

        # Also provide manual input option
        print("Jika browser tidak otomatis me-redirect, salin kode dari URL browser dan paste di sini.")
        code_input = input("👉 Masukkan kode (atau tekan ENTER jika sudah redirect otomatis): ").strip()
        auth_code = code_input or captured_auth_code

        if auth_code:
            print(f"\n🔄 Menukarkan kode '{auth_code}' dengan Access Token...")
            res = service.exchange_code_for_token(auth_code)
            print("Hasil Pertukaran Token:")
            print(json.dumps(res, indent=2))
        else:
            print("⚠️ Belum ada kode yang diterima.")

    elif choice == "2":
        print("\n🌐 Buka URL berikut di browser Anda untuk mengotorisasi Toko Penjual:")
        print(f"👉 {seller_url}\n")
        print("⏳ Menunggu redirect ke http://127.0.0.1:3000/callback...")
        t = threading.Thread(target=start_callback_listener, args=(3000,), daemon=True)
        t.start()
        try:
            webbrowser.open(seller_url)
        except Exception:
            pass

        code_input = input("👉 Masukkan kode (atau tekan ENTER jika sudah redirect otomatis): ").strip()
        auth_code = code_input or captured_auth_code

        if auth_code:
            print(f"\n🔄 Menukarkan kode '{auth_code}' dengan Access Token...")
            res = service.exchange_code_for_token(auth_code)
            print("Hasil Pertukaran Token:")
            print(json.dumps(res, indent=2))
        else:
            print("⚠️ Belum ada kode yang diterima.")

    elif choice == "3":
        code_input = input("👉 Paste Authorization Code dari URL callback: ").strip()
        if code_input:
            res = service.exchange_code_for_token(code_input)
            print("Hasil Pertukaran Token:")
            print(json.dumps(res, indent=2))

    elif choice == "4":
        tokens = service.load_tokens()
        if tokens:
            print("\n✅ Token TikTok Shop Tersimpan:")
            print(json.dumps({k: ("***" if "token" in k else v) for k, v in tokens.items()}, indent=2))
        else:
            print("\n⚠️ Belum ada token yang tersimpan di cookies/tiktok_shop_tokens.json.")

    else:
        print("Selesai.")


if __name__ == "__main__":
    main()
