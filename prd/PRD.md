# PRODUCT REQUIREMENTS DOCUMENT (PRD)
# AI Fashion Affiliate Engine

**Versi:** 1.1  
**Status:** `AUDITED & HARMONIZED (READY FOR POC REVIEW)`  
**Platform:** TikTok Shop Indonesia  
**Kategori:** Data-driven Fashion Affiliate  
**Konten:** Faceless AI Video (9:16 Vertical)  
**Orchestrator:** Hermes Agent  
**Database:** Supabase / PostgreSQL (15 Tabel Kanonis)  
**Visual Generation:** Google Flow melalui Flow Agent (dengan Provider Abstraction)  
**Infrastruktur:** VPS + Docker (Local-first Testing)  
**Workflow Automation:** Hermes-native, tanpa n8n  

---

## 1. Ringkasan Produk

AI Fashion Affiliate Engine adalah sistem otomatis berbasis AI yang bertugas menjalankan operasional bisnis TikTok Shop Affiliate dari riset produk sampai evaluasi performa konten.

Sistem menggunakan Hermes Agent sebagai AI orchestrator utama yang mampu mengambil keputusan, menggunakan tools, menjalankan skill, mengelola jadwal otomatis, dan mengoordinasikan berbagai komponen melalui API maupun MCP.

Sistem tidak menggunakan n8n. Tidak ada workflow n8n yang menjadi ketergantungan dalam operasional.

Hermes mengelola proses bisnis dan keputusan berbasis AI, sedangkan layanan pendukung menyediakan eksekusi yang terukur, penyimpanan data persisten, pemrosesan video, integrasi platform, serta mekanisme retry dan pemulihan error.

### Tujuan utama
Membangun sistem yang mampu:
- Menemukan produk fashion dengan peluang affiliate yang layak berdasarkan data.
- Memilih produk menggunakan scoring dan analisis AI matematis terstandarisasi.
- Menyusun strategi konten, script, hook, visual, dan CTA secara otomatis tanpa klaim spekulatif.
- Menghasilkan video faceless menggunakan Flow Agent dan media-processing tools dengan fidelitas produk tinggi.
- Memeriksa kualitas teknis, akurasi produk, dan kelayakan publikasi.
- Mempublikasikan konten melalui jalur TikTok yang resmi dan diizinkan (evaluasi Shoppable Video API vs Assisted Draft Mode).
- Memverifikasi status publikasi dan keterkaitan produk affiliate secara terpisah.
- Mengumpulkan metrik performa dan komisi per item pesanan (*order line items*).
- Menggunakan hasil analisis sebagai dasar untuk memilih produk serta strategi konten berikutnya berbasis laba operasional riil (ROOC).

**Prinsip utama:** sistem dioptimalkan untuk menghasilkan komisi bersih yang berkelanjutan (*net operating profit*), bukan sekadar memperbanyak video atau views.

---

## 2. Latar Belakang dan Masalah

Operasional affiliate secara manual memerlukan pekerjaan berulang dalam pencarian produk, riset seller, pembuatan ide, produksi video, editing, publikasi, dan analisis performa.

Otomatisasi sederhana hanya memindahkan proses manual ke workflow otomatis. Sistem ini harus melangkah lebih jauh dengan membuat keputusan berdasarkan data dan memperbaiki strategi berdasarkan hasil yang terukur.

### Masalah yang hendak diselesaikan:
- Pemilihan produk belum didasarkan pada kombinasi komisi, kualitas produk, demand, dan potensi konten.
- Produksi konten secara manual sulit diskalakan secara konsisten.
- Video AI dapat menghasilkan representasi produk yang tidak akurat (halusinasi potongan, jahitan, atau bahan).
- Otomatisasi posting tidak menjamin produk affiliate tertaut dengan benar.
- Data views dan engagement tidak selalu berbanding lurus dengan komisi.
- Kegagalan pada satu layanan dapat mengganggu seluruh proses.
- Tanpa pencatatan biaya dan komisi, bisnis berisiko menghasilkan banyak konten tetapi merugi.

---

## 3. Visi Produk

Menciptakan AI-operated affiliate business yang memiliki loop operasional mandiri:
`Discover → Evaluate → Strategize → Produce → Validate → Publish → Measure → Learn → Repeat`.

Hermes bertindak sebagai pusat pengambilan keputusan dan orkestrasi. Sistem pendukung menjalankan pekerjaan teknis sesuai instruksi dan kontrak yang telah ditentukan.

Sistem diharapkan dapat berjalan rutin di VPS tanpa membutuhkan instruksi manual untuk setiap siklus operasional setelah konfigurasi awal, otorisasi akun, dan seluruh akses yang diperlukan tersedia.

Otomatisasi tidak boleh melewati persyaratan otorisasi, consent, audit aplikasi, atau ketentuan TikTok Shop.

---

## 4. Target Pengguna & Klasifikasi Dua Level Otomatisasi

### Primary user
Pemilik bisnis affiliate yang ingin mengoperasikan akun TikTok fashion dengan keterlibatan manual seminimal mungkin.

### Karakteristik bisnis
- Akun TikTok baru di pasar Indonesia.
- Berfokus pada produk fashion yang dipilih melalui riset data.
- Tidak mengharuskan pemilik tampil di kamera (*faceless*).
- Mengutamakan kualitas konten dan peluang komisi riil.
- Beroperasi pada satu akun terlebih dahulu dengan 1 unit VPS.
- Menggunakan Hermes sebagai AI utama.

### Mengurai Blind Spot "Full Automation":
1. **Level 1 — Autonomous Operations (Fondasi Utama):** Hermes menentukan tugas, menyeleksi produk, menyusun brief, memicu pembuatan video, menjalankan QA, memantau retry, dan mengevaluasi komisi tanpa instruksi manusia pada setiap siklus.
2. **Level 2 — Unattended Platform Actions & Realita Kebijakan TikTok:**
   - Panduan resmi TikTok Developer mewajibkan aplikasi Direct Post memberikan kontrol kepada pengguna/kreator, menampilkan pratinjau, dan meminta persetujuan pengguna sebelum posting. TikTok secara eksplisit menolak aplikasi utilitas tanpa UI yang semata-mata mengunggah konten ke akun pembuat aplikasi sendiri.
   - Oleh karena itu, sistem mengadopsi 3 jalur penerbitan bertingkat:
     - **Jalur A (TikTok Shop Shoppable Video API v202607):** Jalur partner resmi e-commerce jika akses disetujui.
     - **Jalur B (Assisted / Draft Publishing Mode — Default MVP):** Hermes secara 100% otonom memproduksi konten dan menyiapkan brief di draft; kreator cukup melakukan 1-klik konfirmasi penautan di aplikasi resmi TikTok.
     - **Jalur C (Content Posting API dengan Consent UI):** Diaktifkan jika aplikasi developer lolos audit resmi platform.

---

## 5. Prinsip Arsitektur

### 5.1 Hermes sebagai orchestrator utama
Hermes harus menjadi satu-satunya AI agent utama yang mengoordinasikan operasional bisnis.
Hermes bertanggung jawab untuk:
- Menentukan tugas yang harus dijalankan.
- Memanggil tools yang relevan melalui antarmuka MCP.
- Membaca dan memperbarui state bisnis di Supabase.
- Mengatur siklus rutin melalui cron scheduler bawaan Hermes.
- Menganalisis kegagalan dan menentukan tindakan pemulihan.
- Membandingkan performa konten dan memperbarui prioritas eksperimen.

Hermes tidak boleh mengandalkan seluruh state bisnis dari riwayat percakapan atau context window. Semua data operasional yang diperlukan harus disimpan secara persisten di Supabase.

### 5.2 Pemisahan Konteks Otorisasi Dual-OAuth
- **Konteks 1: TikTok for Developers** (`client_key`, `client_secret`) untuk Content Posting API.
- **Konteks 2: TikTok Shop Partner Center** (`app_key`, `app_secret`) untuk Shoppable Video & Affiliate API.

### 5.3 Layanan pendukung berbasis Adapter Pattern
Layanan pendukung tidak bertindak sebagai workflow orchestrator terpisah. Mereka menjalankan tugas spesifik yang diminta Hermes:
- **Commerce Adapter:** Mengelola katalog produk, verifikasi seller, dan histori harga.
- **Media Adapter (Provider-Agnostic):** Mengontrol Flow Agent (Google Flow) dengan fallback API (Fal.ai/Kling), audio TTS, dan FFmpeg worker.
- **Publishing Adapter:** Menjalankan operasi posting terotorisasi dan verifikasi anchor.
- **Analytics Adapter:** Menarik metrik performa, mengagregasi order line items, dan menghitung laba bersih.

### 5.4 Kontrak Worker Lease Atomik (`production_jobs`)
Pekerjaan render video dikunci secara atomik dengan status transisi kanonis:
$$\text{queued} \longrightarrow \text{claimed} \longrightarrow \text{generating\_visuals} \longrightarrow \text{assembling\_ffmpeg} \longrightarrow \text{qa\_running} \longrightarrow \text{completed} \mid \text{failed} \mid \text{dead\_letter}$$
Worker mengunci pekerjaan menggunakan kolom `locked_by`, `locked_at`, dan `lease_expires_at` (timeout 15 menit) untuk menjamin auto-recovery saat crash tanpa menghasilkan duplikasi.

### 5.5 Supabase sebagai source of truth
Supabase menyimpan seluruh state bisnis kanonis dalam 15 tabel relasional terstruktur.

### 5.6 Tool-first & Evidence-based execution
Hermes wajib menggunakan bukti respon platform (bukan asumsi) untuk menyatakan suatu tindakan berhasil.

---

## 6. Ruang Lingkup MVP

### In scope
- Setup satu akun TikTok Shop kreator di Indonesia.
- Riset data produk fashion dan pencatatan histori harga/komisi.
- Normalisasi, deduplikasi eksak, dan scoring matematis 6 dimensi.
- Perencanaan brief naskah faktual (bebas klaim spekulatif).
- Produksi video vertikal 9:16 melalui Flow Agent (dengan 3-tier health check) dan FFmpeg.
- Pengujian QA teknis dan fidelitas visual pakaian.
- Evaluasi jalur publikasi (Shoppable API vs Assisted Draft Mode).
- Pemisahan status verifikasi video dan penautan anchor keranjang kuning.
- Pengambilan metrik performa dan komisi per item pesanan (*order line items*).
- Siklus pembelajaran otonom berbasis ROOC.
- Pengujian awal di lingkungan lokal Windows sebelum deployment ke VPS Docker.

### Out of scope
- Penggunaan n8n.
- Penggunaan browser automation untuk membypass sistem deteksi platform.
- Penggunaan endpoint internal TikTok yang tidak terdokumentasi.
- Pengelolaan banyak akun pada MVP.
- Produksi konten untuk platform lain.
- Sistem iklan berbayar atau live streaming AI.

---

## 7. Product Discovery Engine

### 7.1 Objective
Menemukan kandidat produk fashion berdasarkan data yang tersedia, memverifikasi kelayakannya, dan menyusun daftar prioritas untuk produksi konten.
Sumber data utama adalah API resmi atau sumber katalog yang akses dan penggunaannya sah.

### 7.2 Data yang dikumpulkan
- External product ID, nama produk, kategori path.
- Harga jual aktual (IDR) dan mata uang.
- Identitas seller dan rating reputasi toko.
- Nilai komisi (rate 0.00–1.00) dan estimasi nominal rupiah.
- Rating bintang (1.0–5.0) dan jumlah ulasan riil.
- Ketersediaan stok dan varian.
- URL produk dan metadata aset media yang sah.
- Data yang tidak tersedia wajib ditandai `null`/`unavailable`, dilarang dihalusinasikan.

### 7.3 Formula Matematis 6-Dimensi Product Scoring
$$\text{Total Score} = \sum_{i=1}^{6} (w_i \times S_i) \quad \text{di mana } w_i \in [0.0, 1.0], \; \sum_{i=1}^{6} w_i = 1.0, \; S_i \in [0, 100]$$

| Dimensi Scoring ($S_i$) | Bobot ($w_i$) | Parameter Evaluasi |
|:---|:---:|:---|
| 1. Kecocokan Target Audiens | $0.20$ | Kesesuaian gaya busana dengan demografi TikTok Indonesia. |
| 2. Potensi Komisi Bersih | $0.20$ | Normalisasi min-max nominal komisi bersih (Rp 5.000 s.d. Rp 50.000 diskalakan ke 0–100). |
| 3. Kualitas Produk & Seller | $0.20$ | Rating produk ($\ge 4.7$), ulasan riil, reputasi pemenuhan toko. |
| 4. Daya Tarik Konten (*Visual Hook*) | $0.15$ | Estetika visual, tekstur kain, siluet potongan. |
| 5. Harga dan Nilai (*Value for Money*) | $0.15$ | Keterjangkauan harga pasar lokal (Rp 75.000 – Rp 250.000). |
| 6. Ketersediaan & Stabilitas Listing | $0.10$ | Stabilitas stok dan konsistensi harga seller. |

### Ambang Batas Numerik & Histori Harga:
- **`MIN_APPROVAL_SCORE = 70.0`**: Hanya produk dengan skor $\ge 70.0$ yang disetujui untuk diproduksi.
- Perubahan harga dan komisi dicatat ke tabel `product_price_history`. Jika seller memotong komisi $> 30\%$, promosi otomatis di-pause.

### 7.4 Eligibility gate
Produk disetujui jika: ID valid, komisi affiliate jelas, data tersinkronisasi $< 24$ jam, aset asli seller tersedia, total skor $\ge 70.0$, dan tidak ada klaim terlarang.

---

## 8. Content Intelligence Engine

### 8.1 Pilar Konten Fashion
1. **Outfit Formula:** Panduan rumus padu padan sederhana.
2. **Product Detail & Comparison:** Penjelasan mendalam tekstur bahan dan potongan.
3. **Outfit by Budget:** Styling terjangkau dengan rentang harga nyata.
4. **One Item, Three Looks:** 1 pakaian utama untuk 3 aktivitas berbeda.

### 8.2 Persyaratan Content Brief & Sanitasi Klaim
Setiap brief wajib memiliki naskah faktual. Dilarang menyertakan klaim spekulatif tanpa bukti (seperti *"sebelum kehabisan warna best seller"* atau *"anti gerah seharian"*). Seluruh naskah wajib merujuk pada spesifikasi bahan dan panduan ukuran resmi seller.

### 8.3 Pemisahan Sistem Anti-Repetisi
- **Exact Deduplication:** SHA-256 hash dari `(product_id + hook_id + pillar + angle_id)` disimpan unik di `content_briefs.fingerprint_hash`.
- **Fuzzy Similarity Detection:** Analisis overlap n-gram dan semantic similarity untuk mendeteksi naskah yang hanya diubah sinonimnya. Kemiripan $> 70\%$ wajib ditolak.

---

## 9. AI Video Production Engine

### 9.1 Teknologi
- **Hermes:** Koordinasi dan perencanaan shot list.
- **Flow Agent:** Generasi klip gambar/video via REST API lokal (dengan dukungan rasio portrait 9:16).
- **FFmpeg & FFprobe:** Penggabungan klip, sulih suara bahasa Indonesia, subtitle hardcoded, dan inspeksi teknis stream.
- **Supabase & Storage Persisten:** Metadata, status lease worker, dan aset video master.

### 9.2 Keandalan Flow Agent: 3-Tier Health Check
1. **Tier 1 (`service_health`):** Endpoint `GET /health` merespons HTTP 200.
2. **Tier 2 (`session_health`):** Sesi akun Google Flow aktif terautentikasi (bukan prompt login/2FA).
3. **Tier 3 (`generation_smoke_test`):** Uji coba prompt mini berhasil tanpa penolakan HTTP 502 dari upstream Google.
Jika terjadi HTTP 502 upstream rejection berulang, sistem menerapkan cooldown 3 menit dan mengalihkan job ke Provider Fallback (Fal.ai / Kling API) atau menahan produksi dengan budget guard.

### 9.3 Product Fidelity Rules
AI dilarang mengubah potongan baju, jahitan, warna asli, kancing, dan motif kain. Foto produk asli seller wajib disertakan sebagai referensi visual (*image conditioning*), dan aset nyata yang di-motion dapat disisipkan jika generasi AI berhalusinasi.

---

## 10. TikTok Publishing & Publish State Machine

### 10.1 Pemisahan Domain
Penerbitan video (*Publishing*) dan penautan keranjang kuning (*Anchor Management*) adalah dua proses terpisah. Keberhasilan upload bukan bukti anchor terpasang.

### 10.2 Koreksi Mekanisme Recovery Timeout (Strict Anti-Duplicate)
- Sistem **tidak menggunakan `GET /video/list/` atau kueri video publik** untuk rekonsiliasi karena video dari aplikasi belum diaudit dibatasi ke status privat (`SELF_ONLY`).
- Rekonsiliasi resmi menggunakan polling `POST /v2/post/publish/status/fetch/` menggunakan `publish_id`.
- Jika request putus sebelum `publish_id` tersimpan, job masuk ke `publish_unknown` $\rightarrow$ `manual_reconciliation_required`. **DILARANG KERAS MELAKUKAN UPLOAD ULANG OTOMATIS.**

### 10.3 Publish State Machine
$$\text{queued} \rightarrow \text{uploading} \rightarrow \text{processing} \rightarrow \text{published} \rightarrow \text{anchor\_pending} \rightarrow \text{published\_with\_verified\_anchor}$$
*(Dengan cabang penanganan kegagalan: `preflight_failed`, `publish_failed`, `publish_unknown`, `anchor_failed`).*

---

## 11. Affiliate Analytics & Learning Engine

### 11.1 Definisi Laba Operasional & Multi-Line Orders
$$\text{Confirmed Net Commission} = \sum_{\text{lines}} (\text{Commission Settled IDR} - \text{Refunds/Cancellations IDR})$$
$$\text{Operating Profit} = \text{Confirmed Net Commission} - \text{Production Costs} - \text{Operational Costs}$$
$$\text{ROOC} = \frac{\text{Operating Profit}}{\text{Production Costs} + \text{Operational Costs}} \times 100\%$$

### 11.2 Learning Loop 2-Tingkat
Setiap 24 jam, Hermes mengevaluasi performa konten (retensi hook, CTR) dan profitabilitas produk (ROOC, rasio retur) untuk memperbarui bobot scoring produk dan pedoman naskah hari berikutnya.

---

## 12. Data Model Kanonis (15 Tabel Supabase)

1. `affiliate_accounts`: Akun kreator, pemisahan kredensial Content Posting API & TikTok Shop Partner API.
2. `affiliate_products`: Katalog produk master dan lifecycle status.
3. `product_price_history`: Snapshot historis perubahan harga, komisi, dan stok seller.
4. `experiments`: Catatan hipotesis strategi dan bobot scoring A/B test.
5. `product_scores`: Nilai rincian 6 dimensi scoring dan alasan AI.
6. `content_briefs`: Naskah terstruktur, shot list, dan SHA-256 fingerprint hash.
7. `production_jobs`: Status render, worker lease (`locked_by`, `lease_expires_at`), retry count, dan idempotency key.
8. `content_assets`: File master video, klip, audio, lisensi sumber, dan metadata ukuran.
9. `publish_queue`: Antrean jadwal, `publish_id`, item ID, dan state machine status.
10. `affiliate_anchors`: Status verifikasi keranjang kuning dan bukti platform.
11. `post_metrics_daily`: Metrik harian views, likes, shares, dan klik produk.
12. `affiliate_orders`: Master data transaksi pesanan TikTok Shop.
13. `order_line_items`: Rincian per item dalam satu pesanan (kuantitas, estimasi komisi, komisi cair, status refund).
14. `cost_events`: Biaya komputasi token AI, generasi visual, audio, dan infra per job.
15. `workflow_events`: Audit trail menyeluruh mencatat seluruh event mutasi status.

---

## 13. Operasional, Keamanan & Roadmap

### Keamanan:
- Token OAuth dienkripsi menggunakan AES-256-GCM pada level aplikasi sebelum masuk ke Supabase.
- Penggunaan tag wajib *AI Generated Content disclosure*.

### Roadmap Berbasis Gerbang POC (Gate-Driven):
- **Fase 1 (POCs Wajib):**
  1. POC 1: Audit Akun & Jalur TikTok Shop ID
  2. POC 2: Publish & Shoppable Anchor PoC (Direct Post vs Assisted Mode)
  3. POC 3: Flow Agent 3-Tier Health Check (Lokal Windows $\rightarrow$ VPS)
  4. POC 4: Hermes State Persistence & Crash Recovery PoC
- **Fase 2:** Mesin Riset Katalog, 6D Scoring, dan Produksi Media FFmpeg.
- **Fase 3:** Integrasi Publishing, Anchor Verification, dan Closed-Loop Learning.

### Acceptance Criteria MVP:
- [NOT STARTED - AWAITING POC] Hermes menjalankan siklus otonom tanpa n8n.
- [NOT STARTED - AWAITING POC] Produk dipilih berdasarkan formula scoring terstandarisasi (skor $\ge 70.0$).
- [NOT STARTED - AWAITING POC] Video diproduksi dengan fidelitas tinggi dan lolos 3-tier health check.
- [NOT STARTED - AWAITING POC] Status publikasi diverifikasi via `publish_id` dan anchor dicek terpisah.
- [NOT STARTED - AWAITING POC] Tidak ada re-upload duplikat pasca timeout.
- [NOT STARTED - AWAITING POC] Biaya produksi dan komisi bersih tercatat per item pesanan untuk menghitung ROOC riil.

---

## 14. Keputusan Arsitektur Final

AI Fashion Affiliate Engine menggunakan Hermes sebagai AI orchestrator utama dan tidak menggunakan n8n.
Supabase merupakan source of truth dengan 15 tabel kanonis. Flow Agent menjalankan generasi visual dengan Provider Abstraction. TikTok dan affiliate integrations beroperasi melalui adapter resmi dengan pemisahan konteks OAuth.
Tujuan akhirnya adalah membuktikan satu siklus lengkap yang benar dan aman:  
**produk valid → video akurat → publikasi terkonfirmasi → affiliate anchor terverifikasi → komisi dan biaya dapat diukur.**
