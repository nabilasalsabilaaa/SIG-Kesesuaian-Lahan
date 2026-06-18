import psycopg2
import psycopg2.extras
from psycopg2 import pool

DB_CONFIG = {
    "dbname":   "sig_lahan",
    "user":     "postgres",
    "password": "12345678sall",  
    "host":     "localhost",
    "port":     "5432"
}

# Inisialisasi Connection Pool (Min 1, Max 10 koneksi)
try:
    db_pool = pool.SimpleConnectionPool(1, 10, **DB_CONFIG)
except Exception as e:
    print(f"Error creating connection pool: {e}")

def get_connection():
    return db_pool.getconn()

def release_connection(conn):
    db_pool.putconn(conn)

LAYER_CONFIG = {
    "wilayah": {
        "label":    "Administrasi Wilayah",
        "table":    "wilayah",
        "col_nama": "wadmkd"          
    },
    "curah_hujan": {
        "label":     "Curah Hujan",
        "table":     "curah_hujan",
        "col_kelas": "ch",      
        "col_nilai": "ch"    
    },
    "kemiringan": {
        "label":     "Kemiringan Lereng",
        "table":     "kemiringan",
        "col_kelas": "kl"      
    },
    "pola_ruang": {
        "label":    "Pola Ruang (RTRW)",
        "table":    "pola_ruang",
        "col_zona": "namobj"         
    },
    "jambu_mete": {
        "label":     "Kesesuaian Jambu Mete",
        "table":     "jambu_mete",
        "col_kelas": "suai_lahan"        
    }
}