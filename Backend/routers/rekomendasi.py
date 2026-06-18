from fastapi import APIRouter, HTTPException
from database import get_connection, release_connection, LAYER_CONFIG

router = APIRouter()

@router.get("/overlay-rekomendasi")
def get_overlay_rekomendasi():
    """Display S1/S2 suitability areas outside agricultural zones (expansion recommendation)."""
    conn = get_connection()
    cur  = conn.cursor()

    zona_ruang_col = LAYER_CONFIG["pola_ruang"]["col_zona"]
    kelas_jambu_col = LAYER_CONFIG["jambu_mete"]["col_kelas"]

    try:
        # Extract and build GeoJSON from intersection
        cur.execute(f"""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type',     'Feature',
                        'geometry', ST_AsGeoJSON(
                            ST_CollectionExtract(
                                ST_Intersection(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(pr.wkb_geometry)),
                                3
                            )
                        )::json,
                        'properties', json_build_object(
                            'kelas_kesesuaian', jm.{kelas_jambu_col},
                            'zona_ruang',       pr.{zona_ruang_col},
                            'luas_ha', ROUND(
                                CAST(
                                    ST_Area(
                                        ST_CollectionExtract(
                                            ST_Intersection(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(pr.wkb_geometry)),
                                            3
                                        )::geography
                                    ) / 10000
                                AS numeric), 2
                            ),
                            'keterangan', 'Lahan sesuai di luar zona pertanian utamanya'
                        )
                    )
                ), '[]'::json)
            )
            FROM {LAYER_CONFIG["jambu_mete"]["table"]} jm
            JOIN {LAYER_CONFIG["pola_ruang"]["table"]} pr
                ON ST_Intersects(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(pr.wkb_geometry))
            WHERE
                (jm.{kelas_jambu_col} ILIKE '%S1%' OR jm.{kelas_jambu_col} ILIKE '%S2%' OR jm.{kelas_jambu_col} ILIKE '%Sesuai%')
                AND pr.{zona_ruang_col} NOT IN (
                    'Pertanian',
                    'Pertanian Lahan Basah',
                    'Pertanian Lahan Kering',
                    'Perkebunan'
                )
                AND NOT ST_IsEmpty(
                    ST_CollectionExtract(ST_Intersection(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(pr.wkb_geometry)), 3)
                );
        """)
        result = cur.fetchone()[0]
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error di overlay-rekomendasi: {str(e)}")
    finally:
        if cur: cur.close()
        if conn: release_connection(conn)


@router.get("/rekomendasi")
def get_rekomendasi():
    """Recommend best expansion locations based on: rainfall, slope, zoning, and suitability."""
    conn = get_connection()
    cur  = conn.cursor()

    cfg = LAYER_CONFIG
    # Slope table configuration
    table_lereng = cfg['kemiringan']['table']
    col_lereng   = cfg['kemiringan']['col_kelas']

    try:
        # Spatial join across 5 layers for optimal areas
        cur.execute(f"""
            SELECT
                w.{cfg['wilayah']['col_nama']}   AS nama_desa,
                ROUND(
                    CAST(
                        SUM(ST_Area(
                            ST_CollectionExtract(
                                ST_Intersection(
                                    ST_Intersection(
                                        ST_Intersection(
                                            ST_MakeValid(jm.wkb_geometry), 
                                            ST_MakeValid(w.wkb_geometry)
                                        ),
                                        ST_MakeValid(pr.wkb_geometry)
                                    ),
                                    ST_Intersection(
                                        ST_MakeValid(ch.wkb_geometry),
                                        ST_MakeValid(k.wkb_geometry)
                                    )
                                ),
                                3
                            )::geography
                        )) / 10000
                    AS numeric), 2
                ) AS luas_rekomendasi_ha
            FROM {cfg['jambu_mete']['table']} jm
            JOIN {cfg['wilayah']['table']} w
                ON ST_Intersects(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(w.wkb_geometry))
            JOIN {cfg['curah_hujan']['table']} ch
                ON ST_Intersects(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(ch.wkb_geometry))
            JOIN {table_lereng} k
                ON ST_Intersects(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(k.wkb_geometry))
            JOIN {cfg['pola_ruang']['table']} pr
                ON ST_Intersects(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(pr.wkb_geometry))
            WHERE
                -- Suitability: S1/S2
                (jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%S1%' OR jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%S2%')
                -- Rainfall: Moderate-High
                AND (ch.{cfg['curah_hujan']['col_kelas']} ILIKE '%Sedang%' OR ch.{cfg['curah_hujan']['col_kelas']} ILIKE '%Tinggi%')
                -- Slope: < 15%
                AND (k.{col_lereng} ILIKE '%0-8%' OR k.{col_lereng} ILIKE '%8-15%')
                -- Zoning: Agriculture/Plantation
                AND (pr.{cfg['pola_ruang']['col_zona']} ILIKE '%Pertanian%' OR pr.{cfg['pola_ruang']['col_zona']} ILIKE '%Perkebunan%')
            GROUP BY w.{cfg['wilayah']['col_nama']}
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
        if cur: cur.close()
        if conn: release_connection(conn)