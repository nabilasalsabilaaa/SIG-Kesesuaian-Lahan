from fastapi import APIRouter, HTTPException
from database import get_connection, LAYER_CONFIG

router = APIRouter()

@router.get("/overlay-rekomendasi")
def get_overlay_rekomendasi():
    """
    Menampilkan area kesesuaian S1/S2 jambu mete yang TIDAK berada
    di zona pertanian (rekomendasi perluasan lahan ke zona potensial lain).
    """
    conn = get_connection()
    cur  = conn.cursor()

    zona_ruang_col = LAYER_CONFIG["pola_ruang"]["col_zona"]
    kelas_jambu_col = LAYER_CONFIG["jambu_mete"]["col_kelas"]

    try:
        cur.execute(f"""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type',     'Feature',
                        'geometry', ST_AsGeoJSON(
                            ST_Intersection(jm.wkb_geometry, pr.wkb_geometry)
                        )::json,
                        'properties', json_build_object(
                            'kelas_kesesuaian', jm.{kelas_jambu_col},
                            'zona_ruang',       pr.{zona_ruang_col},
                            'luas_ha', ROUND(
                                CAST(
                                    ST_Area(ST_Intersection(
                                        jm.wkb_geometry, pr.wkb_geometry
                                    )::geography) / 10000
                                AS numeric), 2
                            ),
                            'keterangan', 'Lahan sesuai di luar zona pertanian utamanya'
                        )
                    )
                ), '[]'::json)
            )
            FROM jambu_mete jm
            JOIN pola_ruang pr
                ON ST_Intersects(jm.wkb_geometry, pr.wkb_geometry)
            WHERE
                (jm.{kelas_jambu_col} ILIKE '%S1%' OR jm.{kelas_jambu_col} ILIKE '%S2%' OR jm.{kelas_jambu_col} ILIKE '%Sesuai%')
                AND pr.{zona_ruang_col} NOT IN (
                    'Pertanian',
                    'Pertanian Lahan Basah',
                    'Pertanian Lahan Kering',
                    'Perkebunan'
                )
                AND NOT ST_IsEmpty(
                    ST_Intersection(jm.wkb_geometry, pr.wkb_geometry)
                );
        """)
        result = cur.fetchone()[0]
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error di overlay-rekomendasi: {str(e)}")
    finally:
        cur.close()
        conn.close()


@router.get("/rekomendasi")
def get_rekomendasi():
    """
    Rekomendasi lokasi terbaik perluasan lahan berdasarkan irisan:
    - Wilayah Administrasi
    - Kelas kesesuaian Jambu Mete yang bernilai Sesuai (S1/S2)
    Hasilnya dikelompokkan per desa beserta luas rekomendasi (hektar).
    """
    conn = get_connection()
    cur  = conn.cursor()

    cfg = LAYER_CONFIG

    try:
        cur.execute(f"""
            SELECT
                w.{cfg['wilayah']['col_nama']}   AS nama_desa,
                ROUND(
                    CAST(
                        SUM(ST_Area(
                            ST_Intersection(
                                jm.wkb_geometry, w.wkb_geometry
                            )::geography
                        )) / 10000
                    AS numeric), 2
                ) AS luas_rekomendasi_ha
            FROM jambu_mete jm
            JOIN wilayah w
                ON ST_Intersects(jm.wkb_geometry, w.wkb_geometry)
            WHERE
                jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%S1%' 
                OR jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%S2%'
                OR jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%Sesuai%'
            GROUP BY w.{cfg['wilayah']['col_nama']}
            HAVING SUM(ST_Area(
                ST_Intersection(jm.wkb_geometry, w.wkb_geometry)::geography
            )) > 0
            ORDER BY luas_rekomendasi_ha DESC;
        """)

        rows = cur.fetchall()
        return {
            "status": "ok",
            "total_desa": len(rows),
            "rekomendasi_per_desa": [
                {"desa": r[0] if r[0] else "Tanpa Nama", "luas_ha": float(r[1])} for r in rows
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error di rekomendasi: {str(e)}")
    finally:
        cur.close()
        conn.close()