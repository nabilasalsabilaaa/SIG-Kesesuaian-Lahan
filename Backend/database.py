import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "dbname":   "sig_lahan",
    "user":     "postgres",
    "password": "postgres",  
    "host":     "localhost",
    "port":     "5432"
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

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