import psycopg2
from database import DB_CONFIG, LAYER_CONFIG

cfg = LAYER_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    # Kueri untuk mencari desa yang memiliki area rekomendasi optimal (S1/S2, Ch Sedang-Tinggi, Lereng <15%, Pola Ruang Pertanian/Perkebunan)
    query = f"""
        SELECT
            w.{cfg['wilayah']['col_nama']}   AS nama_desa,
            ROUND(
                CAST(
                    SUM(ST_Area(
                        ST_CollectionExtract(
                            ST_Intersection(
                                ST_Intersection(
                                    ST_Intersection(
                                        jm.wkb_geometry, 
                                        w.wkb_geometry
                                    ),
                                    pr.wkb_geometry
                                ),
                                ST_Intersection(
                                    ch.wkb_geometry,
                                    k.wkb_geometry
                                )
                            ),
                            3
                        )::geography
                    )) / 10000
                AS numeric), 2
            ) AS luas_rekomendasi_ha
        FROM {cfg['jambu_mete']['table']} jm
        JOIN {cfg['wilayah']['table']} w
            ON ST_Intersects(jm.wkb_geometry, w.wkb_geometry)
        JOIN {cfg['curah_hujan']['table']} ch
            ON ST_Intersects(jm.wkb_geometry, ch.wkb_geometry)
        JOIN {cfg['kemiringan']['table']} k
            ON ST_Intersects(jm.wkb_geometry, k.wkb_geometry)
        JOIN {cfg['pola_ruang']['table']} pr
            ON ST_Intersects(jm.wkb_geometry, pr.wkb_geometry)
        WHERE
            -- Suitability: S1/S2
            (jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%S1%' OR jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%S2%')
            -- Rainfall: Moderate-High
            AND ch.{cfg['curah_hujan']['col_kelas']} IN ('2300-2400', '2400-2500', '2500-2600', '2600-2700', '2700-2800')
            -- Slope: < 15%
            AND k.{cfg['kemiringan']['col_kelas']} IN ('0-3%', '3-8%', '8-15%')
            -- Zoning: Agriculture/Plantation
            AND (pr.{cfg['pola_ruang']['col_zona']} ILIKE '%Pertanian%' OR pr.{cfg['pola_ruang']['col_zona']} ILIKE '%Perkebunan%')
        GROUP BY w.{cfg['wilayah']['col_nama']}
        ORDER BY luas_rekomendasi_ha DESC;
    """
    
    print("Mencari desa yang direkomendasikan... (ini mungkin memakan waktu beberapa saat)")
    cur.execute(query)
    rows = cur.fetchall()
    
    print("\n=== DAFTAR DESA DENGAN LAHAN REKOMENDASI OPTIMAL ===")
    print(f"Total Desa Teridentifikasi: {len(rows)}")
    print("-" * 65)
    for i, r in enumerate(rows, 1):
        if r[1] > 0:
            print(f"{i:2d}. Desa/Kelurahan: {r[0]:<30} | Luas Rekomendasi: {r[1]:>8} Ha")
        
except Exception as e:
    print(f"Error querying database: {e}")
finally:
    if 'cur' in locals() and cur: cur.close()
    if 'conn' in locals() and conn: conn.close()
