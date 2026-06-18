# Halo bang
ini tugas SIG, tema kita yaitu Kesesuaian Lahan Jambu Mete

### Prasyarat
install :
1. Python 3.12
2. PostgreSQL 18
3. PostGIS Bundle Extension (Pastikan mencentang komponen Spasial saat instalasi PostgreSQL. bisa juga lewat Stack Builder caranya).
- Buka Start Menu di Windows, lalu cari dan buka aplikasi Application Stack Builder.
- Pilih koneksi PostgreSQL kamu (misalnya: PostgreSQL 16 on port 5432), lalu klik Next.
- Pada daftar aplikasi yang muncul, buka bagian Spatial Extensions.
- Berikan tanda centang (✓) pada PostGIS  Bundle for PostgreSQL (pilih versi terbaru yang tersedia).
- Klik Next terus dan ikuti proses download serta instalasinya sampai selesai. Saat muncul jendela instalasi PostGIS, setujui saja semua pengaturan default-nya (Next / I Agree).

---

### Langkah 1: Clone Repo
yagitulah

---

### Langkah 2: Instalasi Dependensi Python

Instal seluruh *library* Python yang dibutuhkan untuk menjalankan FastAPI dengan satu perintah berikut:

```bash
pip install -r requirements.txt
```

---

## Langkah 3: Setup & Restore Database
1. Buka **pgAdmin**.
2. Buat database baru bernama: **`sig_lahan`**.
3. Klik kanan pada database `sig_lahan` baru tersebut, lalu buka **Query Tool**.
4. Aktifkan modul ekstensi spasial PostGIS dengan menjalankan perintah berikut:
```sql
CREATE EXTENSION postgis;
```
5. Klik ikon **Folder (Open File)** di bagian atas editor Query Tool, cari dan pilih file **`sig_lahan_database.sql`** yang ada di dalam repository ini.
6. Tekan tombol **Execute / Run (F5)**. Tunggu hingga proses eksekusi tabel selesai.
7. Klik kanan folder **Tables** di bawah schema `public` -> **Refresh**. Pastikan tabel `wilayah`, `curah_hujan`, `kemiringan_lereng`, `pola_ruang`, dan `jambu_mete` sudah masuk sepenuhnya.

---

## Langkah 4: Konfigurasi Database

1. Buka file **`database.py`**.
2. Sesuaikan nilai `"password"` pada objek `DB_CONFIG` dengan password PostgreSQL laptop Anda sendiri.
```python
DB_CONFIG = {
    "dbname":   "sig_lahan",
    "user":     "postgres",
    "password": "PASSWORD_POSTGRES_ANDA",  # <-- Ganti dengan password laptop Anda
    "host":     "localhost",
    "port":     "5432"
}

```

---

## Langkah 5: Menjalankan Backend Server

Jalankan perintah berikut di terminal Anda untuk mengaktifkan server FastAPI:

```bash
uvicorn main:app --reload --port 5000

```

Backend sekarang aktif dan berjalan di URL lokal: **`http://127.0.0.1:5000`**

### Dokumentasi API 

Anda bisa melihat spesifikasi lengkap seluruh endpoint, parameter input, dan contoh struktur data JSON keluaran dengan membuka browser ke:
👉 **`http://127.0.0.1:5000/docs`**

---
yah seterusnya frontend nya mi hehe

---

## Langkah 6: Menjalankan Frontend Server

Frontend adalah aplikasi web statis (HTML + CSS + JavaScript). Anda bisa menjalankannya dengan salah satu cara berikut:

### Opsi A: Menggunakan Python SimpleHTTPServer (Paling Mudah)

1. Buka terminal dan navigasi ke folder `Frontend`:
```bash
cd Frontend
```

2. Jalankan local server:
```bash
# Python 3.x
python -m http.server 8000
```

3. Buka browser dan akses:
👉 **`http://localhost:8000`**

---

### Opsi B: Menggunakan Node.js http-server (Alternatif)

Jika Anda sudah install Node.js:

```bash
npm install -g http-server
cd Frontend
http-server -p 8000
```

Lalu buka di browser: **`http://localhost:8000`**

---

### Opsi C: Buka file langsung di browser (Tidak Rekomendasi)

Bisa juga buka `Frontend/index.html` langsung di browser dengan double-click, tapi lebih aman menggunakan local server untuk menghindari masalah CORS.

---

## Langkah 7: Verifikasi Aplikasi Berjalan

Sebelum memulai, pastikan kedua server sudah aktif:

1. ✅ **Backend FastAPI** berjalan di `http://127.0.0.1:5000`
   - Jalankan di terminal: `uvicorn main:app --reload --port 5000` (dari folder `Backend`)

2. ✅ **Frontend Web Server** berjalan di `http://localhost:8000`
   - Jalankan di terminal: `python -m http.server 8000` (dari folder `Frontend`)

3. ✅ **Database PostgreSQL** sudah aktif dan tabel sudah dibuat

Jika semua berjalan, buka browser ke `http://localhost:8000` dan Anda akan melihat peta interaktif dengan layer-layer spasial.

---

## Fitur-Fitur Frontend

### 1. **Peta Interaktif (Leaflet.js)**
   - Menampilkan peta dasar dari OpenStreetMap dan Satelit (Esri)
   - Zoom, pan, dan layer control tersedia di sudut peta

### 2. **Layer Data Spasial**
Beberapa layer dapat di-toggle melalui kontrol di sudut kanan atas:
   - 🌟 **Kesesuaian Jambu Mete** — Menampilkan zona kesesuaian lahan (warna hijau-merah)
   - 📍 **Batas Administrasi Wilayah** — Batas desa/kelurahan
   - 💧 **Data Curah Hujan** — Distribusi curah hujan per wilayah
   - ⛰️ **Kemiringan Lereng** — Klasifikasi kemiringan lahan
   - 📐 **Pola Ruang (RTRW)** — Rencana tata ruang wilayah

### 3. **Analisis Spasial (Geoman)**
   - Gunakan tool gambar di sudut kiri atas untuk menggambar poligon di peta
   - Setelah selesai gambar, sistem akan otomatis menghitung luas area yang sesuai untuk Jambu Mete
   - Hasil analisis ditampilkan di popup

### 4. **Query Titik Spesifik**
   - Klik di mana saja pada peta untuk mengetahui detail informasi di lokasi tersebut
   - Hasil query menampilkan semua data spasial yang relevan di titik itu

### 5. **Legenda Kesesuaian Lahan**
   - Warna di sudut kanan bawah menjelaskan klasifikasi:
     - 🟢 **S1 (Sangat Sesuai)** — Optimal untuk Jambu Mete
     - 🔵 **S2 (Cukup Sesuai)** — Cukup cocok dengan beberapa pembatasan
     - 🟡 **S3 (Sesuai Bersyarat)** — Terbatas, perlu manajemen khusus
     - 🔴 **TS (Tidak Sesuai)** — Tidak cocok untuk Jambu Mete

---

## Troubleshooting

### ❌ Frontend tidak bisa terhubung ke Backend

**Error:** `AggregateError: at internalConnectMultiple (node:net:1193:18)`

**Solusi:**
1. Pastikan backend sudah berjalan di `http://127.0.0.1:5000`
2. Buka browser console (F12 → Console) dan cari pesan `✗ Gagal memuat layer...`
3. Pastikan tidak ada firewall yang memblokir port 5000
4. Coba refresh halaman (Ctrl + F5)

---

### ❌ Data layer tidak muncul di peta

**Penyebab:**
- Database belum di-setup dengan benar
- Tabel kosong atau belum ada data
- Backend belum dijalankan

**Solusi:**
1. Verifikasi di pgAdmin bahwa tabel berisi data:
   ```sql
   SELECT COUNT(*) FROM jambu_mete;
   SELECT COUNT(*) FROM wilayah;
   ```
2. Buka `http://127.0.0.1:5000/api/layers` di browser untuk cek status semua layer
3. Lihat console browser (F12) untuk error messages

---

### ❌ Port 5000 atau 8000 sudah terpakai

**Solusi:**
```bash
# Ganti port backend (misalnya 5001)
uvicorn main:app --reload --port 5001

# Ganti port frontend (misalnya 8001)
python -m http.server 8001
```

Lalu update `API_BASE_URL` di file `Frontend/js/map.js`:
```javascript
const API_BASE_URL = "http://127.0.0.1:5001/api";  // Sesuaikan port
```

---

## Struktur Folder

```
SIG-Kesesuaian-Lahan/
├── README.md                          # File ini
├── sig_lahan_database.sql             # Dump database PostgreSQL
├── Backend/
│   ├── main.py                        # Entry point FastAPI
│   ├── database.py                    # Konfigurasi database
│   ├── requirements.txt               # Python dependencies
│   └── routers/
│       ├── layers.py                  # Endpoint untuk fetch layer data
│       ├── suitability.py             # Endpoint untuk query titik spesifik
│       ├── analyze.py                 # Endpoint untuk analisis poligon
│       └── rekomendasi.py             # Endpoint untuk rekomendasi lahan
├── Frontend/
│   ├── index.html                     # Halaman utama
│   ├── js/
│   │   └── map.js                     # Logika peta & komunikasi API
│   └── css/
│       └── (styling files jika ada)
└── Data/
    ├── geojson_administrasi_wilayah.geojson
    ├── geojson_curah_hujan.geojson
    ├── geojson_jambu_mete.json
    ├── geojson_kemiringan_lereng.geojson
    ├── geojson_kesesuaian_lahan.geojson
    └── geojson_pola_ruang.geojson
```

---

## Teknologi yang Digunakan

- **Backend:** FastAPI (Python), PostgreSQL + PostGIS
- **Frontend:** Leaflet.js (peta), Geoman (drawing tools), Chart.js (statistik), vanilla JavaScript
- **Database:** PostgreSQL 18 dengan extensi PostGIS 3.x
- **Data Format:** GeoJSON untuk pertukaran data spasial

---
