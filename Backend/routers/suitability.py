from fastapi import APIRouter, HTTPException, Query
from database import get_connection, LAYER_CONFIG

router = APIRouter()


@router.get("/suitability")
def get_suitability(
    lat: float = Query(..., description="Latitude titik yang diklik di peta"),
    lon: float = Query(..., description="Longitude titik yang diklik di peta")
):
    """
    Mengembalikan informasi lengkap untuk satu titik koordinat:
    nama wilayah, curah hujan, kemiringan, pola ruang,
    dan kelas kesesuaian jambu mete.
    """

    conn = get_connection()
    cur  = conn.cursor()

    # Fungsi pembantu untuk mengecek data spasial berdasarkan titik koordinat
    def query_point(table: str, col: str) -> str:
        try:
            cur.execute(f"""
                SELECT {col}
                FROM {table}
                WHERE ST_Intersects(
                    wkb_geometry,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                )
                LIMIT 1;
            """, (lon, lat))
            row = cur.fetchone()
            return str(row[0]) if row and row[0] is not None else "Tidak ada data"
        except Exception:
            # Jika ada tabel yang bermasalah/belum ada di database (seperti kesesuaian_lahan)
            return "Tidak tersedia"

    try:
        cfg = LAYER_CONFIG
        
        # Ekstraksi informasi dari tiap layer spasial
        data = {
            "koordinat": {"lat": lat, "lon": lon},
            "nama_wilayah": query_point(
                cfg["wilayah"]["table"], 
                cfg["wilayah"]["col_nama"]
            ),
            "curah_hujan": {
                "kelas": query_point(
                    cfg["curah_hujan"]["table"], 
                    cfg["curah_hujan"]["col_kelas"]
                ),
                "nilai_mm": query_point(
                    cfg["curah_hujan"]["table"], 
                    cfg["curah_hujan"]["col_nilai"]
                )
            },
            "kemiringan": query_point(
                "kemiringan_lereng",  # Disesuaikan langsung dengan nama tabel asli di pgAdmin kamu
                cfg["kemiringan"]["col_kelas"]
            ),
            "zona_pola_ruang": query_point(
                cfg["pola_ruang"]["table"], 
                cfg["pola_ruang"]["col_zona"]
            ),
            "kelas_kesesuaian": "Belum Dianalisis (File Kosong)", # Menghindari crash karena file kosong
            
            "kelas_jambu_mete": query_point(
                cfg["jambu_mete"]["table"],   # Menggunakan key config 'jambu_mete'
                cfg["jambu_mete"]["col_kelas"]
            ),
        }
        return {"status": "ok", "data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()
        conn.close()