from fastapi import APIRouter, HTTPException, Query
from database import get_connection, release_connection, LAYER_CONFIG

router = APIRouter()


@router.get("/suitability")
def get_suitability(
    lat: float = Query(..., description="Latitude of clicked point"),
    lon: float = Query(..., description="Longitude of clicked point")
):
    """Return suitability information for a coordinate: region, rainfall, slope, zoning, and land suitability."""

    conn = get_connection()
    cur  = conn.cursor()

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
            if row and row[0] is not None:
                val = str(row[0]).strip().upper()
                return "TS" if val == "N" else val
            return "Tidak ada data"
        except Exception:
            return "Tidak tersedia"

    try:
        cfg = LAYER_CONFIG
        
        # Extract information from spatial layers
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
            cfg["kemiringan"]["table"],
                cfg["kemiringan"]["col_kelas"]
            ),
            "zona_pola_ruang": query_point(
                cfg["pola_ruang"]["table"], 
                cfg["pola_ruang"]["col_zona"]
            ),
            "kelas_kesesuaian": "Belum Dianalisis (File Kosong)",
            
            "kelas_jambu_mete": query_point(
                cfg["jambu_mete"]["table"],
                cfg["jambu_mete"]["col_kelas"]
            ),
        }
        return {"status": "ok", "data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()
        if conn:
            release_connection(conn)