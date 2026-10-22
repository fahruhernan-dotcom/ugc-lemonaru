# 05. Content Intelligence & Product Fidelity
**Navigasi:** [← 04. Product Discovery & Scoring](./04_product_discovery_and_scoring.md) | [Index Utama](./README.md) | [Berikutnya: AI Video Production Engine →](./06_ai_video_production_engine.md)

---

## 1. Tujuan Mesin Konten Pintar (*Content Intelligence*)

Content Intelligence Engine bertugas menerjemahkan produk fashion yang telah lolos kualifikasi menjadi strategi video vertikal yang memikat penonton, relevan dengan kebiasaan audiens TikTok Indonesia, dan memicu niat membeli (*commercial intent*).

Hermes Agent mengeksekusi sub-skill terfokus:
- `content-strategy`: Memilih pilar konten dan sudut pandang psikologis (*angle*).
- `fashion-scriptwriting`: Menulis naskah dengan struktur Hook – Body – CTA dalam bahasa Indonesia yang alami, persuasif, dan patuh pada fakta produk.
- `visual-planning`: Menyusun *shot list* dan arahan prompt generasi untuk setiap adegan.

---

## 2. Empat Pilar Konten Fashion Utama

Untuk menjaga variasi kreatif dan tidak terjebak dalam template yang membosankan, sistem menerapkan 4 pilar format:

| Pilar Konten | Deskripsi Format | Cocok Untuk Karakter Produk |
|:---|:---|:---|
| **1. Outfit Formula** | Kombinasi aturan padu padan sederhana (misal: "Rumus 3 Warna", "Atasan Oversize + Celana Kulot"). | Atasan kemeja, celana basic, blazer kerja. |
| **2. Product Detail & Comparison** | Penjelasan mendalam mengenai tekstur bahan, kerapian jahitan, ketebalan kain, dan spesifikasi fisik. | Pakaian dengan material premium (linen, knit, katun combed). |
| **3. Outfit by Budget** | Kurasi padu padan berpenampilan rapi dengan batasan anggaran nyata (misal: "Styling Kemeja di Kisaran Rp 100rb-an"). | Produk fashion harga bersahabat dengan visual menarik. |
| **4. One Item, Three Looks** | Satu pakaian utama di-styling untuk 3 suasana berbeda (misal: Casual Nongkrong, Semi-formal Kerja, Hijab Chic). | Outerwear, kardigan, rok plisket, dress serbaguna. |

---

## 3. Struktur Persyaratan Content Brief (Sanitasi Bebas Klaim Ilegal)

Setiap brief konten yang dibuat oleh Hermes Agent wajib memiliki skema terstruktur di Supabase (`content_briefs`), dengan contoh naskah yang mematuhi prinsip kejujuran informasi (*no unsupported claims*):

```json
{
  "product_id": "uuid-affiliate-product",
  "target_audience": "Wanita 18-28 tahun, mahasiswi & pekerja muda, gaya smart-casual",
  "content_goal": "Mendorong penonton memeriksa detail potongan kemeja di keranjang kuning",
  "content_pillar": "Outfit Formula",
  "hook": {
    "text_overlay": "Inspirasi styling kemeja loose-fit buat ngantor 🍃",
    "spoken_audio": "Kemeja dengan potongan loose-fit gini gampang banget di-mix and match buat outfit harian.",
    "visual_action": "Transisi transparan memperlihatkan potongan kemeja bahan katun rami warna beige"
  },
  "scene_breakdown": [
    {
      "scene_number": 1,
      "duration_sec": 3,
      "shot_type": "Close-up fabric texture",
      "visual_prompt": "Cinematic close-up of natural linen-cotton textured shirt fabric, beige color, clean studio lighting",
      "reference_image_asset_id": "asset-img-01",
      "voiceover_text": "Serat kainnya bertekstur katun rami ringan, jadi jatuh rapi saat dipakai."
    }
  ],
  "product_facts_used": [
    "Material: campuran katun rami ringan",
    "Tersedia ukuran M sampai XXL sesuai tabel ukuran seller",
    "Model kerah: Cuban collar dengan kancing kayu natural"
  ],
  "prohibited_claims": [
    "DILARANG mengklaim 'anti kusut 100%' jika deskripsi seller tidak menjaminnya",
    "DILARANG mengklaim 'warna best seller' tanpa data penjualan terverifikasi",
    "DILARANG menjanjikan klaim medis/pelangsing"
  ],
  "cta": "Cek pilihan warna dan detail ukuran lengkapnya di keranjang kuning.",
  "caption": "Inspirasi padu padan kemeja loose-fit buat kerja atau kuliah. Detail ukuran ada di keranjang kuning ya! #OOTDKerja #KemejaWanita #FashionInspo",
  "ai_disclosure_required": true,
  "expected_duration_seconds": 18
}
```

---

## 4. Pemisahan Sistem Anti-Repetisi: Hash Eksak vs Fuzzy Similarity

Untuk menghindari penolakan konten oleh algoritma TikTok Shop, sistem membedakan secara tegas dua tingkatan deteksi duplikasi:

### A. Exact Deduplication (Pendeteksi Naskah/Angle Kembar)
Menggunakan algoritma kriptografis deterministik:

$$\text{Fingerprint Hash} = \text{SHA-256}(\text{Product ID} \parallel \text{Hook Identifier} \parallel \text{Content Pillar} \parallel \text{Angle Identifier})$$

- Nilai hash disimpan unik di tabel `content_briefs.fingerprint_hash`.
- Jika hash sudah pernah dibuat dalam 60 hari terakhir, brief otomatis ditolak.

### B. Fuzzy Similarity Detection (Pendeteksi Kemiripan Substansial)
- Menggunakan analisis N-Gram Jaccard overlap dan semantic sentence similarity terhadap riwayat naskah 30 hari terakhir.
- Konten tidak boleh dianggap berbeda hanya karena beberapa kata diganti sinonimnya jika struktur adegan dan argumen persuasinya $> 70\%$ mirip. Jika similarity score $> 0.70$, Hermes wajib menolak brief dan merancang konsep baru.

---

## 5. Menghindari Blind Spot Kritis: Fidelitas Produk Fashion (*Product Fidelity*)

> [!CAUTION]
> **Blind Spot Terbesar: Konten Kelihatan Indah Namun Gagal Menjual (*Doesn't Sell*)**  
> AI generatif sering kali menghasilkan video yang sangat estetik secara sinematik, namun **mengubah bentuk asli pakaian**: kancing hilang, kerah berubah bentuk, warna meleset dari kenyataan, atau detail bordir terdistorsi. Hal ini memicu pembatalan pesanan (*order cancellation*), ulasan negatif pembeli, atau penolakan iklan.

### Aturan Ketat Fidelitas Produk:
1. **Integritas Atribut Fisik:** Model AI dilarang keras memodifikasi potongan baju, garis jahitan, warna asli, motif kain, letak saku, atau bentuk kerah produk.
2. **Penggunaan Aset Asli sebagai Panduan Visual (*Image Conditioning*):** Generasi video/gambar melalui Flow Agent atau Media Adapter wajib menyertakan foto resmi dari seller sebagai *image-to-image guidance* / *reference asset*.
3. **Fallback ke Aset Nyata (*Real Media Insertion*):** Jika hasil generasi AI terbukti tidak mampu mempertahankan kemiripan pakaian (misal: motif batik yang terlalu rumit), sistem **wajib menggabungkan foto produk asli yang di-motion (zoom/pan dinamis) daripada membiarkan visual AI yang berhalusinasi.**
4. **Verifikasi Hak Cipta & Lisensi Aset:** Setiap aset foto seller yang digunakan dicatat sumber URL, jenis izin pemanfaatan affiliate di platform TikTok Shop, dan waktu pengambilannya pada tabel `content_assets`.

---

**Langkah Selanjutnya:** Pelajari bagaimana Media Adapter merender video dan menjalankan QA otomatis pada [06_ai_video_production_engine.md](./06_ai_video_production_engine.md).
