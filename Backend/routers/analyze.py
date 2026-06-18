from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Any
from database import get_connection, release_connection, LAYER_CONFIG
import json
import io
import csv
import os
import tempfile
import zipfile
import geopandas as gpd

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
    luas_rekomendasi = 0.0
    rows_mete_rekomendasi = [] # New variable for class distribution in recommended area
    rekomendasi_geojson = None
    kriteria_summary = {}
    cfg = LAYER_CONFIG

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

        # --- QUERY 3: ANALISIS REKOMENDASI OPTIMAL (4 KRITERIA) ---
        # Mencari irisan lahan yang: Jambu Mete S1/S2, Hujan Sedang/Tinggi, Lereng <15%, Pola Ruang Pertanian
        try:
            # 1. Ambil data aktual yang ditemukan di dalam poligon untuk tabel perbandingan
            # Gunakan ST_MakeValid pada input GeoJSON untuk mencegah error pada poligon yang tidak valid
            poly_query = "ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))"
            cur.execute(f"""
                SELECT 
                    (SELECT string_agg(DISTINCT jm.{cfg['jambu_mete']['col_kelas']}, ', ') FROM {cfg['jambu_mete']['table']} jm WHERE ST_Intersects(jm.wkb_geometry, {poly_query})),
                    (SELECT string_agg(DISTINCT ch.{cfg['curah_hujan']['col_kelas']}, ', ') FROM {cfg['curah_hujan']['table']} ch WHERE ST_Intersects(ch.wkb_geometry, {poly_query})),
                    (SELECT string_agg(DISTINCT k.{cfg['kemiringan']['col_kelas']}, ', ') FROM {cfg['kemiringan']['table']} k WHERE ST_Intersects(k.wkb_geometry, {poly_query})),
                    (SELECT string_agg(DISTINCT pr.{cfg['pola_ruang']['col_zona']}, ', ') FROM {cfg['pola_ruang']['table']} pr WHERE ST_Intersects(pr.wkb_geometry, {poly_query}))
            """, (geojson_str, geojson_str, geojson_str, geojson_str))
            
            actual = cur.fetchone()
            
            def format_label(val):
                if not val: return "N/A"
                v = val.strip().upper()
                return "TS" if v == "N" else v

            def check_match(val, keywords):
                if not val: return False
                return any(k.lower() in val.lower() for k in keywords)

            # 2. Susun ringkasan kriteria (Key ini harus lengkap agar map.js bisa menampilkan tabel)
            kriteria_summary = {
                "kesesuaian": {
                    "label": "Kesesuaian", 
                    "actual": format_label(actual[0]), 
                    "requirement": "S1 atau S2", "status": check_match(actual[0], ["S1", "S2"])
                },
                "hujan": {
                    "label": "Curah Hujan", "actual": format_label(actual[1]), 
                    "requirement": "Sdng-Tinggi", "status": check_match(actual[1], ["Sedang", "Tinggi"])
                },
                "lereng": {
                    "label": "Kemiringan", "actual": actual[2] or "N/A", 
                    "requirement": "< 15% (0-15)", "status": check_match(actual[2], ["0-8", "8-15"])
                },
                "pola_ruang": {
                    "label": "Pola Ruang", "actual": actual[3] or "N/A", 
                    "requirement": "Pertanian", "status": check_match(actual[3], ["Pertanian", "Perkebunan"])
                }
            }

            # Hitung Luas Optimal & Ambil Geometri (GeoJSON) untuk visualisasi peta
            cur.execute(f"""
                WITH raw_result AS (
                    SELECT ST_CollectionExtract(ST_Intersection(ST_Intersection(ST_Intersection(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(ch.wkb_geometry)), ST_Intersection(ST_MakeValid(k.wkb_geometry), ST_MakeValid(pr.wkb_geometry))), ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3) AS geom
                    FROM {cfg['jambu_mete']['table']} jm
                    JOIN {cfg['curah_hujan']['table']} ch ON ST_Intersects(jm.wkb_geometry, ch.wkb_geometry)
                    JOIN {cfg['kemiringan']['table']} k   ON ST_Intersects(jm.wkb_geometry, k.wkb_geometry)
                    JOIN {cfg['pola_ruang']['table']} pr  ON ST_Intersects(jm.wkb_geometry, pr.wkb_geometry)
                    WHERE ST_Intersects(jm.wkb_geometry, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
                        AND (jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%%S1%%' OR jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%%S2%%')
                        AND (ch.{cfg['curah_hujan']['col_kelas']} ILIKE '%%Sedang%%' OR ch.{cfg['curah_hujan']['col_kelas']} ILIKE '%%Tinggi%%')
                        AND (k.{cfg['kemiringan']['col_kelas']} ILIKE '%%0-8%%' OR k.{cfg['kemiringan']['col_kelas']} ILIKE '%%8-15%%')
                        AND (pr.{cfg['pola_ruang']['col_zona']} ILIKE '%%Pertanian%%' OR pr.{cfg['pola_ruang']['col_zona']} ILIKE '%%Perkebunan%%')
                )
                SELECT 
                    ROUND(CAST(SUM(ST_Area(geom::geography)) / 10000 AS numeric), 2) AS luas_ha,
                    ST_AsGeoJSON(ST_Union(geom))::json AS geojson
                FROM raw_result
                WHERE NOT ST_IsEmpty(geom);
            """, (geojson_str, geojson_str))
            
            res_rec = cur.fetchone()
            if res_rec:
                luas_rekomendasi = float(res_rec[0]) if res_rec[0] else 0.0
                rekomendasi_geojson = res_rec[1]

            # NEW QUERY: JAMBU METE CLASS DISTRIBUTION WITHIN RECOMMENDED AREA
            if rekomendasi_geojson: # Only query if there's a recommended area
                cur.execute(f"""
                    SELECT
                        jm.suai_lahan AS kelas,
                        ROUND(
                            CAST(
                                SUM(ST_Area(
                                    ST_Intersection(
                                        jm.wkb_geometry,
                                        ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326) -- Use the calculated rekomendasi_geojson here
                                    )::geography
                                )) / 10000
                            AS numeric), 2
                        ) AS luas_ha
                    FROM {cfg['jambu_mete']['table']} jm
                    WHERE ST_Intersects(
                        jm.wkb_geometry,
                        ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326) -- Use the calculated rekomendasi_geojson here
                    )
                    GROUP BY jm.suai_lahan
                    ORDER BY luas_ha DESC;
                """, (json.dumps(rekomendasi_geojson), json.dumps(rekomendasi_geojson)))
                rows_mete_rekomendasi = cur.fetchall()
        except Exception as e:
            print(f"Error logic rekomendasi: {e}")
            conn.rollback()
            luas_rekomendasi = 0.0

        return {
            "status": "ok",
            "kesesuaian_lahan": [
                {"kelas": r[0] if r[0] else "Tidak Diketahui", "luas_ha": float(r[1])} for r in rows_kesesuaian
            ],
            "jambu_mete": [
                {"kelas": r[0] if r[0] else "Tidak Diketahui", "luas_ha": float(r[1])} for r in rows_mete
            ],
            "jambu_mete_rekomendasi": [ # New field in response
                {"kelas": r[0] if r[0] else "Tidak Diketahui", "luas_ha": float(r[1])} for r in rows_mete_rekomendasi
            ],
            "rekomendasi_optimal_ha": luas_rekomendasi,
            "rekomendasi_geojson": rekomendasi_geojson,
            "kriteria_summary": kriteria_summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: release_connection(conn)

@router.post("/analyze/csv")
def export_analysis_csv(body: AnalyzeRequest):
    """
    Mengekspor hasil analisis poligon ke format CSV.
    """
    geojson_str = json.dumps(body.polygon)
    conn = get_connection()
    cur  = conn.cursor()
    cfg = LAYER_CONFIG

    try:
        # Ambil data Jambu Mete
        cur.execute(f"""
            SELECT jm.{cfg['jambu_mete']['col_kelas']}, 
                   ROUND(CAST(SUM(ST_Area(ST_Intersection(jm.wkb_geometry, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))::geography)) / 10000 AS numeric), 2)
            FROM {cfg['jambu_mete']['table']} jm
            WHERE ST_Intersects(jm.wkb_geometry, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            GROUP BY jm.{cfg['jambu_mete']['col_kelas']};
        """, (geojson_str, geojson_str))
        res_mete = cur.fetchall()

        # Ambil data Rekomendasi Optimal
        cur.execute(f"""
            SELECT ROUND(CAST(SUM(ST_Area(ST_Intersection(ST_Intersection(ST_Intersection(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(ch.wkb_geometry)), ST_Intersection(ST_MakeValid(k.wkb_geometry), ST_MakeValid(pr.wkb_geometry))), ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))::geography)) / 10000 AS numeric), 2)
            FROM {cfg['jambu_mete']['table']} jm
            JOIN {cfg['curah_hujan']['table']} ch ON ST_Intersects(jm.wkb_geometry, ch.wkb_geometry)
            JOIN {cfg['kemiringan']['table']} k   ON ST_Intersects(jm.wkb_geometry, k.wkb_geometry)
            JOIN {cfg['pola_ruang']['table']} pr  ON ST_Intersects(jm.wkb_geometry, pr.wkb_geometry)
            WHERE ST_Intersects(jm.wkb_geometry, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            AND (jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%%S1%%' OR jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%%S2%%')
            AND (ch.{cfg['curah_hujan']['col_kelas']} ILIKE '%%Sedang%%' OR ch.{cfg['curah_hujan']['col_kelas']} ILIKE '%%Tinggi%%')
            AND (k.{cfg['kemiringan']['col_kelas']} ILIKE '%%0-8%%' OR k.{cfg['kemiringan']['col_kelas']} ILIKE '%%8-15%%')
            AND (pr.{cfg['pola_ruang']['col_zona']} ILIKE '%%Pertanian%%' OR pr.{cfg['pola_ruang']['col_zona']} ILIKE '%%Perkebunan%%');
        """, (geojson_str, geojson_str))
        res_opt = cur.fetchone()

        # Membuat file CSV di dalam memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Kategori", "Kelas/Kriteria", "Luas (Hektar)"])
        
        for row in res_mete:
            writer.writerow(["Kesesuaian Jambu Mete", row[0], row[1]])
        
        if res_opt and res_opt[0]:
            writer.writerow(["Rekomendasi Optimal", "Total Lahan Optimal", res_opt[0]])

        output.seek(0)
        return StreamingResponse(
            output, 
            media_type="text/csv", 
            headers={"Content-Disposition": "attachment; filename=hasil_analisis_spasial.csv"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: release_connection(conn)

@router.post("/analyze/shapefile")
def export_analysis_shp(body: AnalyzeRequest):
    """
    Mengekspor area rekomendasi optimal ke format Shapefile (Zipped).
    """
    geojson_str = json.dumps(body.polygon)
    conn = get_connection()
    cur = conn.cursor()
    cfg = LAYER_CONFIG

    try:
        # Ambil geometri irisan hasil rekomendasi
        cur.execute(f"""
            SELECT ST_AsGeoJSON(ST_CollectionExtract(ST_Intersection(ST_Intersection(ST_Intersection(ST_MakeValid(jm.wkb_geometry), ST_MakeValid(ch.wkb_geometry)), ST_Intersection(ST_MakeValid(k.wkb_geometry), ST_MakeValid(pr.wkb_geometry))), ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3))
            FROM {cfg['jambu_mete']['table']} jm
            JOIN {cfg['curah_hujan']['table']} ch ON ST_Intersects(jm.wkb_geometry, ch.wkb_geometry)
            JOIN {cfg['kemiringan']['table']} k ON ST_Intersects(jm.wkb_geometry, k.wkb_geometry)
            JOIN {cfg['pola_ruang']['table']} pr ON ST_Intersects(jm.wkb_geometry, pr.wkb_geometry)
            WHERE ST_Intersects(jm.wkb_geometry, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            AND (jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%%S1%%' OR jm.{cfg['jambu_mete']['col_kelas']} ILIKE '%%S2%%')
            AND (ch.{cfg['curah_hujan']['col_kelas']} ILIKE '%%Sedang%%' OR ch.{cfg['curah_hujan']['col_kelas']} ILIKE '%%Tinggi%%')
            AND (k.{cfg['kemiringan']['col_kelas']} ILIKE '%%0-8%%' OR k.{cfg['kemiringan']['col_kelas']} ILIKE '%%8-15%%')
            AND (pr.{cfg['pola_ruang']['col_zona']} ILIKE '%%Pertanian%%' OR pr.{cfg['pola_ruang']['col_zona']} ILIKE '%%Perkebunan%%');
        """, (geojson_str, geojson_str))
        
        rows = cur.fetchall()
        
        geoms_to_export = []
        description = ""

        if rows:
            geoms_to_export = [json.loads(r[0]) for r in rows if r[0]]
            description = "Rekomendasi Optimal"
        else:
            # Jika tidak ada rekomendasi, ekspor poligon yang digambar pengguna
            geoms_to_export = [body.polygon]
            description = "Area Digambar (Tanpa Rekomendasi Optimal)"
            
        if not geoms_to_export:
            raise HTTPException(status_code=400, detail="Tidak ada geometri untuk diekspor.")

        # Convert ke GeoPandas
        gdf = gpd.GeoDataFrame({'id': range(len(geoms_to_export)), 'keterangan': description}, 
                               geometry=gpd.GeoSeries.from_iter([gpd.base.shape(g) for g in geoms_to_export]), 
                               crs="EPSG:4326")

        # Simpan ke folder temporary dan Zip
        with tempfile.TemporaryDirectory() as tmpdir:
            shp_path = os.path.join(tmpdir, "rekomendasi_optimal.shp")
            gdf.to_file(shp_path)
            zip_path = os.path.join(tempfile.gettempdir(), "rekomendasi.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for ext in ['.shp', '.shx', '.dbf', '.prj']:
                    file_to_zip = os.path.join(tmpdir, "rekomendasi_optimal" + ext)
                    if os.path.exists(file_to_zip):
                        zipf.write(file_to_zip, arcname="rekomendasi_optimal" + ext)
            return FileResponse(zip_path, media_type="application/zip", filename="rekomendasi_optimal_shp.zip")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur: cur.close()
        if conn: release_connection(conn)