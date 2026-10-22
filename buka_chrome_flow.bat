@echo off
title Google Flow Login and Sync - Velora AI (Drive D Isolated)
echo =====================================================================
echo [DRIVE D ISOLATED] MEMBUKA CHROME UNTUK GOOGLE FLOW AND FLOW BRIDGE
echo =====================================================================
echo.
echo SEMUA DATA, CACHE, DAN PROFIL 100%% DI DRIVE D (Drive C Tidak Disentuh):
echo - User Data Dir: D:\Dokumen\02_Kerja_Profesional\Tiktok Project\data\chrome_profile_google_flow
echo - Disk Cache:    D:\Dokumen\02_Kerja_Profesional\Tiktok Project\data\temp\chrome_cache
echo - Extension:     D:\Dokumen\02_Kerja_Profesional\Tiktok Project\tools\flow-agent\flow-extension
echo =====================================================================
echo.

if not exist "D:\Dokumen\02_Kerja_Profesional\Tiktok Project\data\temp\chrome_cache" (
    mkdir "D:\Dokumen\02_Kerja_Profesional\Tiktok Project\data\temp\chrome_cache"
)

start chrome --user-data-dir="D:\Dokumen\02_Kerja_Profesional\Tiktok Project\data\chrome_profile_google_flow" --disk-cache-dir="D:\Dokumen\02_Kerja_Profesional\Tiktok Project\data\temp\chrome_cache" --load-extension="D:\Dokumen\02_Kerja_Profesional\Tiktok Project\tools\flow-agent\flow-extension" --new-window "https://labs.google/fx/tools/flow"

echo [OK] Chrome sudah dijalankan dengan profil murni di Drive D!
echo Silakan login akun Google Anda di jendela Chrome tersebut.
echo.
pause
