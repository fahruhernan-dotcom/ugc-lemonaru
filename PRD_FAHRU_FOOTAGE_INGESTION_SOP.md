# MASTER SOP: 10-Frame Multi-Vision Footage Ingestion Protocol (DoniesDaily)

## 📌 Deskripsi & Filosofi
Protokol ini mengunci (*LOCKED STANDARD*) tata cara penerimaan, analisis perilaku, penamaan deskriptif, dan pendaftaran otomatis footage asli kiriman Mas Fahru (`category: fahru_sent`) ke dalam katalog aset DoniesDaily (`cat_assets_catalog.json`).

> [!CRITICAL]
> **Hukum Besi Ingestion #14 (10-Frame Temporal Arc):**
> *\"DILARANG KERAS mengevaluasi klip hanya dari 1 frame statis. Setiap video wajib diekstrak tepat 10 frame berurutan (kronologis 9% s/d 91% durasi) agar AI memahami alur pergerakan, emosi, dan tindakan kucing secara utuh dari awal hingga akhir video.\"*

---

## 🛠️ Spesifikasi Teknis Engine (`tools/ingest_fahru_footage.py`)

### 1. Ekstraksi 10-Frame Kronologis
- Menggunakan `ffmpeg` untuk mengambil 10 cuplikan frame JPEG (resolusi hemat `scale='min(720,iw)':-1`, `q:v 3`) pada interval:
  `ts = duration * ((i + 1) / 11)` untuk $i = 0, 1, \dots, 9$.
- Menghasilkan 10 frame base64 yang mewakili:
  - Frame 1–2: Kondisi awal / ancang-ancang.
  - Frame 3–7: Aksi pergerakan inti / interaksi objek / ekspresi dinamis.
  - Frame 8–10: Reaksi puncak / hasil akhir / transisi.

### 2. Vision Brief Baku (Locked LLM Prompt)
Engine mengirim ke-10 frame secara paralel ke **`gemini-3.8-flash-high`** dengan instruksi ketat:
1. **`slug`:** Nama file *snake_case* deskriptif spesifik (huruf kecil, underscore, 4–6 kata, contoh: `kucing_belang_muka_sedih_pasrah`). Dilarang memakai kata generik seperti `video_kucing`.
2. **`title`:** Judul deskriptif singkat (Title Case, 4–7 kata).
3. **`description`:** Tepat 2 kalimat naratif Bahasa Indonesia yang menceritakan alur nyata di sepanjang 10 frame.
4. **`tags`:** 12–18 kata kunci dwibahasa (ciri fisik, gestur tubuh, aksi gerak, objek interaksi, emosi).
5. **`emotion`:** Santai, penasaran, marah, takut, lucu, sedih, berburu, manja.
6. **`action`:** Tidur, lari, lompat, makan, gigit, cakar, bengong, elus, kepo.

### 3. Otomasi File & Database
- File video otomatis di-rename menjadi `{slug}.mp4` dan dipindahkan ke folder:
  `/home/ubuntu/apps/ugc-lemonaru/assets/cat_videos/fahru_clips/{slug}.mp4`
- Metadata disisipkan ke indeks teratas `data/cat_assets_catalog.json` dengan:
  - `category: "fahru_sent"` (mendapat prioritas tinggi di `doni_hybrid_renderer.py`).
  - `cluster: "fahru_clips"`.
- Log verifikasi dikirimkan ke database SQLite `agents_chat.db` channel `#donies` sebagai laporan otomatis kepada seluruh agen (Doni, Luna, Milo, Cleo).

---

## 📲 Cara Penggunaan / Jalur Intake
1. **Via Telegram Chat Hermes:**
   Kirimkan video/dokumen ke chat DM Mas Fahru. Hermes otomatis memanggil:
   `python3 /home/ubuntu/tools/ingest_fahru_footage.py --file <path_video>`
2. **Via Drop Folder VPS (Batch):**
   Taruh file `.mp4`/`.mov` di folder:
   `/home/ubuntu/apps/ugc-lemonaru/assets/cat_videos/fahru_clips/`
   Lalu jalankan:
   `python3 /home/ubuntu/tools/ingest_fahru_footage.py --scan`
