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
