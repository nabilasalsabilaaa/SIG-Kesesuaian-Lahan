const API_BASE_URL = "http://127.0.0.1:5000/api";

// 1. Inisialisasi Peta (Set center otomatis ke koordinat Sulawesi Selatan / Wilayah Kerja)
const map = L.map('map').setView([-5.14, 119.48], 10);

// 2. Tambahkan Peta Dasar (Basemap)
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
});

// 3. Siapkan Layer Groups (Tempat menampung data spasial dari backend)
const layerWilayah = new L.LayerGroup();
const layerHujan = new L.LayerGroup();
const layerLereng = new L.LayerGroup();
const layerPolaRuang = new L.LayerGroup();
const layerJambuMete = new L.LayerGroup().addTo(map); // Default langsung aktif di peta

// Fungsi pembantu untuk memberikan warna dinamis pada layer Jambu Mete & Kesesuaian Lahan
function getKesesuaianColor(kelas) {
    if (!kelas) return '#7f8c8d';
    let val = kelas.toLowerCase();
    if (val.includes('s1') || val.includes('sangat sesuai')) return '#1e824c'; // Green
    if (val.includes('s2') || val.includes('cukup sesuai')) return '#2cc5c6';  // Light Green/Teal
    if (val.includes('s3') || val.includes('sesuai bersyarat')) return '#f39c12'; // Yellow/Orange
    return '#c0392b'; // Red (Tidak Sesuai / TS)
}

// 4. Fetch dan Load Data dari Backend API untuk Masing-masing Layer

// Fungsi pembantu untuk fetch dengan error handling
function loadLayer(layerName, layerGroup, popupField, popupLabel) {
    fetch(`${API_BASE_URL}/layer/${layerName}/geojson`)
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            return res.json();
        })
        .then(data => {
            L.geoJSON(data, {
                style: (feature) => ({
                    fillColor: layerName === 'jambu_mete' ? getKesesuaianColor(feature.properties.suai_lahan || feature.properties.kelas) : '#2c3e50',
                    weight: 1, 
                    color: '#fff', 
                    fillOpacity: layerName === 'jambu_mete' ? 0.6 : 0.1
                }),
                onEachFeature: (feature, layer) => {
                    const popup = `<b>${popupLabel}:</b> ${feature.properties[popupField] || 'Tidak Diketahui'}`;
                    layer.bindPopup(popup);
                }
            }).addTo(layerGroup);
            console.log(`✓ Layer ${layerName} berhasil dimuat`);
        })
        .catch(err => {
            console.error(`✗ Gagal memuat layer ${layerName}:`, err);
            console.log(`Pastikan backend berjalan di http://127.0.0.1:5000`);
        });
}

// --- Layer 1: Jambu Mete ---
loadLayer('jambu_mete', layerJambuMete, 'suai_lahan', 'Kesesuaian Jambu Mete');

// --- Layer 2: Administrasi Wilayah ---
loadLayer('wilayah', layerWilayah, 'wadmkc', 'Desa/Kelurahan');

// --- Layer 3: Curah Hujan ---
loadLayer('curah_hujan', layerHujan, 'ch', 'Curah Hujan (mm/tahun)');

// --- Layer 4: Kemiringan Lereng ---
loadLayer('kemiringan', layerLereng, 'kl', 'Kelas Lereng');

// --- Layer 5: Pola Ruang ---
loadLayer('pola_ruang', layerPolaRuang, 'namobj', 'Zona Pola Ruang');

// 5. Membuat Kontrol Layer (Checkbox di pojok kanan atas)
const baseMaps = {
    "OpenStreetMap": osm,
    "Satelit (Esri)": satellite
};

const overlayMaps = {
    "Kesesuaian Jambu Mete 🌟": layerJambuMete,
    "Batas Administrasi Wilayah": layerWilayah,
    "Data Curah Hujan": layerHujan,
    "Kemiringan Lereng": layerLereng,
    "Pola Ruang (RTRW)": layerPolaRuang
};

L.control.layers(baseMaps, overlayMaps, { collapsed: false }).addTo(map);

// 6. Integrasi Geoman (Alat Gambar Poligon untuk Endpoint /analyze)
map.pm.addControls({
    position: 'topleft',
    drawMarker: false, drawPolyline: false, drawRectangle: false, drawCircle: false, drawCircleMarker: false,
    cutPolygon: false, editMode: false, removalMode: true
});

map.on('pm:create', function(e) {
    const layer = e.layer;
    const drawnGeoJSON = layer.toGeoJSON();

    // Kirim data bentuk geometri ke POST /api/analyze di FastAPI
    fetch(`${API_BASE_URL}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ polygon: drawnGeoJSON.geometry })
    })
    .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        return res.json();
    })
    .then(data => {
        let popupText = `<h4>Hasil Analisis Luas Area:</h4>`;
        if (data.jambu_mete && data.jambu_mete.length > 0) {
            data.jambu_mete.forEach(item => {
                popupText += `<b>Kelas ${item.kelas}:</b> ${item.luas_ha} Hektar<br>`;
            });
        } else {
            popupText += `<p style="color:red;">Tidak menemukan irisan lahan Jambu Mete di area ini.</p>`;
        }
        layer.bindPopup(popupText).openPopup();
    })
    .catch(err => {
        console.error("✗ Gagal memproses analisis spasial:", err);
        alert(`Error: ${err.message}\n\nPastikan backend berjalan di http://127.0.0.1:5000`);
    });
});

// 7. Klik Bebas Pada Peta untuk Mengetahui Detail Titik Spesifik (/api/suitability)
map.on('click', function(e) {
    // Lewati jika user mengklik bagian menu Geoman kontrol
    if (e.originalEvent.target.closest('.leaflet-pm-toolbar')) return;

    const lat = e.latlng.lat;
    const lon = e.latlng.lng;

    fetch(`${API_BASE_URL}/suitability?lat=${lat}&lon=${lon}`)
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            return res.json();
        })
        .then(data => {
            let info = `<h4>Identifikasi Lokasi:</h4>`;
            // Tampilkan isi properti koordinat dari database response
            info += `<p><b>Garis Lintang:</b> ${lat.toFixed(5)}<br><b>Garis Bujur:</b> ${lon.toFixed(5)}</p>`;
            info += `<pre style="background:#f4f4f4; padding:5px; border-radius:3px; max-height:300px; overflow-y:auto;">${JSON.stringify(data, null, 2)}</pre>`;
            
            L.popup()
                .setLatLng(e.latlng)
                .setContent(info)
                .openOn(map);
        })
        .catch(err => {
            console.error("✗ Error fetching suitability point:", err);
            L.popup()
                .setLatLng(e.latlng)
                .setContent(`<p style="color:red;"><b>Error:</b> ${err.message}</p>`)
                .openOn(map);
        });
});

// 8. Menambahkan Legenda Statis di Pojok Kanan Bawah
const legend = L.control({ position: 'bottomright' });
legend.onAdd = function (map) {
    const div = L.DomUtil.create('div', 'info legend');
    const grades = ['S1 (Sangat Sesuai)', 'S2 (Cukup Sesuai)', 'S3 (Sesuai Bersyarat)', 'TS (Tidak Sesuai)'];
    const colors = ['#1e824c', '#2cc5c6', '#f39c12', '#c0392b'];

    div.innerHTML += '<strong>Legenda Kesesuaian Lahan</strong><br><br>';
    for (let i = 0; i < grades.length; i++) {
        div.innerHTML += '<i style="background:' + colors[i] + '"></i> ' + grades[i] + '<br>';
    }
    return div;
};
legend.addTo(map);