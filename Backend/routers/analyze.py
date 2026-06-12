from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from database import get_connection
import json

router = APIRouter()

class AnalyzeRequest(BaseModel):
    polygon: Any  

@router.post("/analyze")
def analyze_polygon(body: AnalyzeRequest):
    """
    Menerima polygon GeoJSON dari Leaflet,
    menghitung luas (hektar) per kelas kesesuaian lahan
    dan per kelas jambu mete dalam area yang digambar user.
    """

    geojson_str = json.dumps(body.polygon)
    conn = get_connection()
    cur  = conn.cursor()

    rows_kesesuaian = []
    rows_mete = []

    try:
        # --- QUERY 1: KESESUAIAN LAHAN (Dengan proteksi jika tabel belum ada)
        try:
            cur.execute("""
                SELECT
                    kl.suai_lahan AS kelas,  -- Disesuaikan jika nanti strukturnya mirip jambu_mete
                    ROUND(
                        CAST(
                            SUM(ST_Area(
                                ST_Intersection(
                                    kl.wkb_geometry,
                                    ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
                                )::geography
                            )) / 10000
                        AS numeric), 2
                    ) AS luas_ha
                FROM kesesuaian_lahan kl
                WHERE ST_Intersects(
                    kl.wkb_geometry,
                    ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
                )
                GROUP BY kl.suai_lahan
                ORDER BY luas_ha DESC;
            """, (geojson_str, geojson_str))
            rows_kesesuaian = cur.fetchall()
        except Exception:
            # Jika tabel kesesuaian_lahan belum ada/kosong di pgAdmin, 
            # bypass error agar aplikasi tidak crash dan kembalikan array kosong
            conn.rollback() 
            rows_kesesuaian = []

        # --- QUERY 2: JAMBU METE (Sudah diperbaiki total sesuai database asli)
        cur.execute("""
            SELECT
                jm.suai_lahan AS kelas,  -- Kolom ke-13 asli di pgAdmin kamu ('suai_lahan')
                ROUND(
                    CAST(
                        SUM(ST_Area(
                            ST_Intersection(
                                jm.wkb_geometry,
                                ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
                            )::geography
                        )) / 10000
                    AS numeric), 2
                ) AS luas_ha
            FROM jambu_mete jm          -- Nama tabel asli di pgAdmin kamu ('jambu_mete')
            WHERE ST_Intersects(
                jm.wkb_geometry,
                ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)
            )
            GROUP BY jm.suai_lahan
            ORDER BY luas_ha DESC;
        """, (geojson_str, geojson_str))
        rows_mete = cur.fetchall()

        return {
            "status": "ok",
            "kesesuaian_lahan": [
                {"kelas": r[0] if r[0] else "Tidak Diketahui", "luas_ha": float(r[1])} for r in rows_kesesuaian
            ],
            "jambu_mete": [
                {"kelas": r[0] if r[0] else "Tidak Diketahui", "luas_ha": float(r[1])} for r in rows_mete
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cur.close()
        conn.close()