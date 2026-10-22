@echo off
title TikTok Studio Login - Velora AI
echo =====================================================================
echo 🌐 MEMBUKA GOOGLE CHROME UNTUK TIKTOK CREATOR STUDIO
echo =====================================================================
echo.
echo Catatan: Jika Chrome tidak muncul, pastikan tab Chrome lama Anda ditutup.
echo.

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="D:\Dokumen\02_Kerja_Profesional\Tiktok Project\data\chrome_profile_tiktok" "https://www.tiktok.com/creator-center/content/post"

echo [OK] Perintah membuka Chrome sudah dijalankan!
echo Silakan periksa jendela Chrome yang terbuka dan scan QR code TikTok Anda.
echo.
pause
