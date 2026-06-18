from fastapi import APIRouter, HTTPException
from database import get_connection, release_connection, LAYER_CONFIG

router = APIRouter()


@router.get("/layers")
def get_layers():
    """Mengembalikan daftar semua layer yang tersedia."""
    result = {
        key: {"label": cfg["label"], "table": cfg["table"]}
        for key, cfg in LAYER_CONFIG.items()
    }
    return {"status": "ok", "layers": result}


@router.get("/layer/{nama_layer}/geojson")
def get_layer_geojson(nama_layer: str):
    """Mengembalikan seluruh data layer dalam format GeoJSON FeatureCollection."""

    if nama_layer not in LAYER_CONFIG:
        raise HTTPException(
            status_code=404,
            detail=f"Layer '{nama_layer}' tidak ditemukan. "
                   f"Pilihan: {list(LAYER_CONFIG.keys())}"
        )

    table = LAYER_CONFIG[nama_layer]["table"]
    
    # KOREKSI OTOMATIS: Menyesuaikan nama tabel kemiringan dengan yang ada di pgAdmin kamu
    if table == "kemiringan":
        table = "kemiringan"

    conn  = get_connection()
    cur   = conn.cursor()

    try:
        # Menggunakan query SQL bawaan PostGIS untuk mengubah baris tabel menjadi format GeoJSON resmi
        cur.execute(f"""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(
                    json_build_object(
                        'type',       'Feature',
                        'geometry',   ST_AsGeoJSON(
                            ST_SimplifyPreserveTopology(
                                ST_MakeValid(wkb_geometry), 
                                0.001 -- Tingkatkan toleransi (0.0001 -> 0.001) agar ukuran file GeoJSON jauh lebih ringan
                            ), 
                            6 -- Batasi presisi desimal koordinat menjadi 6 angka
                        )::json,
                        'properties', to_jsonb(t) - 'wkb_geometry' - 'ogc_fid'
                    )
                ), '[]'::json)
            )
            FROM {table} t
            WHERE wkb_geometry IS NOT NULL;
        """)
        
        row = cur.fetchone()
        if not row or row[0] is None:
            return {"type": "FeatureCollection", "features": []}
            
        return row[0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memuat layer '{nama_layer}': {str(e)}")

    finally:
        cur.close()
        if conn:
            release_connection(conn)