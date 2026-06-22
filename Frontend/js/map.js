const API_BASE_URL = "http://127.0.0.1:5000/api";

// Add sidebar CSS dynamically
const style = document.createElement('style');
style.innerHTML = `
    .glass-maroon {
        transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1), 
                    padding 0.4s cubic-bezier(0.4, 0, 0.2, 1), 
                    opacity 0.3s ease;
        overflow-x: hidden;
        overflow-y: auto;
    }
    .sidebar-collapsed {
        width: 0 !important;
        padding: 0 !important;
        opacity: 0; 
        pointer-events: none;
    }
    #toggle-sidebar-btn {
        position: fixed;
        right: 20px;
        bottom: 20px;
        z-index: 1001;
        background: #2c3e50;
        color: white;
        border: none;
        border-radius: 50%;
        width: 45px;
        height: 45px;
        cursor: pointer;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }
`;
document.head.appendChild(style);

// Initialize map centered on South Sulawesi
const map = L.map('map').setView([-5.14, 119.48], 10);

// Add base maps (OSM and Satellite)
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map);

const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles © Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
});

// Initialize layer groups
const layerWilayah = new L.LayerGroup();
const layerHujan = new L.LayerGroup();
const layerLereng = new L.LayerGroup();
const layerPolaRuang = new L.LayerGroup();
const layerJambuMete = new L.LayerGroup().addTo(map);
const layerRekomendasiOptimal = new L.LayerGroup();

// Color suitability classes dynamically
function getKesesuaianColor(kelas) {
    if (!kelas) return '#7f8c8d';
    let val = kelas.toString().toUpperCase();
    if (val === 'N') val = 'TS';
    val = val.toLowerCase();

    if (val.includes('s1') || val.includes('sangat sesuai')) return '#1e824c';
    if (val.includes('s2') || val.includes('cukup sesuai')) return '#2cc5c6';
    if (val.includes('s3') || val.includes('sesuai bersyarat')) return '#f39c12';
    return '#e74c3c';
}

// Fetch and load data from backend API
function loadLayer(layerName, layerGroup, popupField, popupLabel) {
    const url = layerName === 'overlay-rekomendasi'
        ? `${API_BASE_URL}/overlay-rekomendasi`
        : layerName === 'rekomendasi-optimal'
        ? `${API_BASE_URL}/rekomendasi-optimal-geojson`
        : `${API_BASE_URL}/layer/${layerName}/geojson`;

    fetch(url)
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            return res.json();
        })
        .then(data => {
            L.geoJSON(data, {
                pmIgnore: true, // Mencegah layer database dihapus oleh user
                style: (feature) => ({
                    fillColor: (layerName === 'jambu_mete')
                        ? getKesesuaianColor(feature.properties.suai_lahan || feature.properties.kelas_kesesuaian)
                        : (layerName === 'rekomendasi-optimal') ? '#2ecc71' : '#2c3e50',
                    weight: (layerName === 'rekomendasi-optimal') ? 2 : 1,
                    color: (layerName === 'rekomendasi-optimal') ? '#2ecc71' : '#fff',
                    fillOpacity: (layerName === 'jambu_mete') ? 0.6 : (layerName === 'rekomendasi-optimal') ? 0.5 : 0.1
                })
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

// Optimasi: Muat layer lain hanya saat checkbox dicentang (Lazy Loading) agar load awal lebih cepat
map.on('overlayadd', function (e) {
    if (e.name === "Batas Administrasi Wilayah" && layerWilayah.getLayers().length === 0) {
        loadLayer('wilayah', layerWilayah, 'wadmkc', 'Desa/Kelurahan');
    }
    if (e.name === "Data Curah Hujan" && layerHujan.getLayers().length === 0) {
        loadLayer('curah_hujan', layerHujan, 'ch', 'Curah Hujan');
    }
    if (e.name === "Kemiringan Lereng" && layerLereng.getLayers().length === 0) {
        loadLayer('kemiringan', layerLereng, 'kl', 'Kelas Lereng');
    }
    if (e.name === "Pola Ruang (RTRW)" && layerPolaRuang.getLayers().length === 0) {
        loadLayer('pola_ruang', layerPolaRuang, 'namobj', 'Zona Pola Ruang');
    }
    if (e.name === "Rekomendasi Lahan Optimal (4 Kriteria)" && layerRekomendasiOptimal.getLayers().length === 0) {
        loadLayer('rekomendasi-optimal', layerRekomendasiOptimal, '', 'Rekomendasi Lahan Optimal');
    }
});

// 5. Membuat Kontrol Layer (Checkbox di pojok kanan atas)
const baseMaps = {
    "OpenStreetMap": osm,
    "Satelit (Esri)": satellite
};
const overlayMaps = {
    "Kesesuaian Jambu Mete": layerJambuMete,
    "Batas Administrasi Wilayah": layerWilayah,
    "Data Curah Hujan": layerHujan,
    "Kemiringan Lereng": layerLereng,
    "Pola Ruang (RTRW)": layerPolaRuang,
    "Rekomendasi Lahan Optimal (4 Kriteria)": layerRekomendasiOptimal
};

// =========================================================================
// 8. Menambahkan Legenda Statis di Pojok Kanan Bawah (Sekarang diatur di bottomleft)
// =========================================================================
const legend = L.control({ position: 'bottomleft' });
legend.onAdd = function (map) {
    const div = L.DomUtil.create('div', 'info legend');
    div.style.padding = '8px';
    div.style.border = 'none';
    div.style.marginBottom = '5px'; // Memberi sedikit jarak dengan kontrol layer di bawahnya

    const grades = ['S1', 'S2', 'S3', 'TS'];
    const labels = ['Sangat Sesuai', 'Cukup Sesuai', 'Sesuai Bersyarat', 'Tidak Sesuai'];
    const colors = ['#1e824c', '#2cc5c6', '#f39c12', '#c0392b'];

    div.innerHTML += '<b>Legenda Kesesuaian</b><br>';
    for (let i = 0; i < grades.length; i++) {
        div.innerHTML += `<i style="background:${colors[i]}; width:18px; height:18px; float:left; margin-right:8px; opacity:0.7;"></i> <b>${grades[i]}</b>: ${labels[i]}<br>`;
    }
    return div;
};

// Tambahkan legenda terlebih dahulu
legend.addTo(map);

// =========================================================================
// 5. Membuat Kontrol Layer (Checkbox)
// =========================================================================
const layerControl = L.control.layers(baseMaps, overlayMaps, {
    collapsed: false,
    position: 'bottomleft'
}).addTo(map);

// --- SOLUSI AMPUH VIA MANIPULASI DOM ---
// Kita ambil container pembungkus kontrol layer, lalu paksa posisinya berada di bawah legenda
const layerControlContainer = layerControl.getContainer();
if (layerControlContainer) {
    // Memberikan margin atas agar tidak menempel, dan memastikan urutan visualnya di bawah
    layerControlContainer.style.marginTop = '10px';
    const parent = layerControlContainer.parentNode;
    if (parent && parent.lastChild !== layerControlContainer) {
        parent.appendChild(layerControlContainer); // Memindahkan kontrol layer ke tumpukan paling bawah
    }
}

// Helper function for generating table rows
function generateInfoRow(label, value) {
    return `<tr style="border-bottom:1px solid #eee;"><td style="padding:4px 0;">${label}</td><td style="text-align:right;">${value}</td></tr>`;
}

// 6. Integrasi Geoman (Alat Gambar Poligon untuk Endpoint /analyze)
map.pm.addControls({
    position: 'topleft',
    drawMarker: false, drawPolyline: false, drawRectangle: false, drawCircle: false, drawCircleMarker: false,
    cutPolygon: false, editMode: true, removalMode: true
});

// Fungsi untuk buka/tutup sidebar
// Fungsi untuk buka/tutup sidebar
window.toggleSidebar = function () {
    const sidebar = document.querySelector('.glass-maroon');
    sidebar.classList.toggle('sidebar-collapsed');
    const btn = document.getElementById('toggle-sidebar-btn');
    const isHidden = sidebar.classList.contains('sidebar-collapsed');
    btn.innerHTML = isHidden ? '📊' : '✕';

    setTimeout(() => {
        map.invalidateSize({ animate: true });
    }, 400);
};

map.on('pm:create', function (e) {
    const layer = e.layer;
    const drawnGeoJSON = layer.toGeoJSON();

    // Tampilkan loading di sidebar
    const resultContent = document.getElementById('analysis-result-content');
    const placeholder = document.getElementById('analysis-placeholder');

    // Pastikan sidebar terbuka saat analisis dimulai
    const sidebar = document.querySelector('.glass-maroon');
    if (sidebar.classList.contains('sidebar-collapsed')) {
        window.toggleSidebar();
    }

    if (placeholder) placeholder.style.display = 'none';
    if (resultContent) {
        resultContent.style.display = 'block';
        resultContent.innerHTML = '<p style="text-align:center;">Menganalisis area...</p>';
    }

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
            updateSidebarUI(data, drawnGeoJSON, layer);
        })
        .catch(err => {
            console.error("✗ Gagal memproses analisis spasial:", err);
            resultContent.innerHTML = `<p style="color:red;">Gagal menganalisis area: ${err.message}</p>`;
        });
});

// Fungsi Baru: Update Sidebar daripada Popup
function updateSidebarUI(data, drawnGeoJSON, layer) {
    const resultContent = document.getElementById('analysis-result-content');

    // Calculate total area for drawn polygon
    const totalDrawnArea = data.jambu_mete.reduce((sum, item) => sum + item.luas_ha, 0);
    // Calculate total area for recommended polygon
    const totalRecommendedArea = data.jambu_mete_rekomendasi.reduce((sum, item) => sum + item.luas_ha, 0);

    // Prepare data for bar chart
    const allClasses = [...new Set([
        ...data.jambu_mete.map(item => item.kelas === 'N' ? 'TS' : item.kelas),
        ...data.jambu_mete_rekomendasi.map(item => item.kelas === 'N' ? 'TS' : item.kelas)
    ])].sort(); // Get unique sorted classes

    const drawnAreaPercentages = allClasses.map(cls => {
        const item = data.jambu_mete.find(i => (i.kelas === 'N' ? 'TS' : i.kelas) === cls);
        return totalDrawnArea > 0 ? ((item ? item.luas_ha : 0) / totalDrawnArea * 100).toFixed(2) : 0;
    });

    const recommendedAreaPercentages = allClasses.map(cls => {
        const item = data.jambu_mete_rekomendasi.find(i => (i.kelas === 'N' ? 'TS' : i.kelas) === cls);
        return totalRecommendedArea > 0 ? ((item ? item.luas_ha : 0) / totalRecommendedArea * 100).toFixed(2) : 0;
    });

    const pct = totalDrawnArea > 0 ? (data.rekomendasi_optimal_ha / totalDrawnArea * 100) : 0;

    let statusClass = 'status-fail';
    let statusText = '✗ POTENSI RENDAH (TIDAK DIREKOMENDASIKAN)';
    let polyColor = '#e74c3c';

    if (data.rekomendasi_optimal_ha > 0) {
        if (pct >= 50.0) {
            statusClass = 'status-ok';
            statusText = '✓ REKOMENDASI OPTIMAL (POTENSI TINGGI)';
            polyColor = '#2ecc71';
        } else {
            statusClass = 'status-warning';
            statusText = '⚠ POTENSI TERBATAS (PERLU PENINGKATAN)';
            polyColor = '#f39c12';
        }
    }

    // Update warna poligon di peta
    layer.setStyle({
        color: polyColor,
        fillColor: polyColor
    });

    let html = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3 style="margin:0;">Hasil Analisis</h3>
            <button onclick="toggleSidebar()" style="background:none; border:none; color:white; cursor:pointer; font-size:1.2rem;">✕</button>
        </div>
        <div class="status-box ${statusClass}">
            ${statusText}<br>
            <span style="font-size:1.2rem;">${data.rekomendasi_optimal_ha} Ha (${pct.toFixed(1)}%)</span>
        </div>
        <div class="export-container">
            <button class="btn-export" onclick="downloadCSV('${JSON.stringify(drawnGeoJSON.geometry).replace(/"/g, '&quot;')}')">Ekspor CSV</button>
            <button class="btn-export" onclick="downloadSHP('${JSON.stringify(drawnGeoJSON.geometry).replace(/"/g, '&quot;')}')">Ekspor SHP</button>
        </div>
        
        <h4>Ringkasan Kriteria:</h4>
        <table class="analysis-table">
            <thead>
                <tr><th>Kriteria</th><th>Syarat</th><th>Data</th><th>Status</th></tr>
            </thead>
            <tbody>`;

    Object.values(data.kriteria_summary).forEach(item => {
        let displayActual = item.actual === 'N' ? 'TS' : item.actual;
        html += `<tr>
            <td>${item.label}</td>
            <td>${item.requirement}</td>
            <td>${displayActual}</td>
            <td>${item.status ? '✓' : '✕'}</td>
        </tr>`;
    });

    html += `</tbody></table>
        <h4>Perbandingan Kelas Kesesuaian:</h4>
        <div style="height: 250px; margin-bottom: 20px;">
            <canvas id="sidebarChart"></canvas>
        </div>
    `;

    resultContent.innerHTML = html;

    if (data.rekomendasi_geojson) {
        if (window.currentRecommendationLayer) map.removeLayer(window.currentRecommendationLayer);
        window.currentRecommendationLayer = L.geoJSON(data.rekomendasi_geojson, {
            style: { color: "#64ffda", weight: 3, fillOpacity: 0.4, dashArray: '5, 5' },
            interactive: false
        }).addTo(map);
    }

    // Only render chart if there's data

    // Inisialisasi Chart di Sidebar
    if (allClasses.length > 0) {
        const ctx = document.getElementById('sidebarChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar', // Changed to bar chart
            data: {
                labels: allClasses,
                datasets: [
                    {
                        label: 'Area Digambar (%)',
                        data: drawnAreaPercentages,
                        backgroundColor: 'rgba(75, 192, 192, 0.6)', // Greenish-blue
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Area Rekomendasi (%)',
                        data: recommendedAreaPercentages,
                        backgroundColor: 'rgba(255, 99, 132, 0.6)', // Reddish
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: 'white',
                            font: { size: 10 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y + '%';
                                }
                                return label;
                            }
                        }
                    }
                }
            }
        });
    }
}

// Logika Hapus: Bersihkan layer analisis saat poligon dihapus
map.on('pm:remove', function (e) {
    if (window.currentRecommendationLayer) {
        map.removeLayer(window.currentRecommendationLayer);
        window.currentRecommendationLayer = null;
    }
    document.getElementById('analysis-result-content').style.display = 'none';
    document.getElementById('analysis-placeholder').style.display = 'block';
});

// Fungsi Global untuk Download CSV
window.downloadCSV = function (geom) {
    const geojson = JSON.parse(geom);
    fetch(`${API_BASE_URL}/analyze/csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ polygon: geojson })
    })
        .then(res => res.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = "hasil_analisis_lahan.csv";
            document.body.appendChild(a);
            a.click();
            a.remove();
        })
        .catch(err => alert("Gagal mengunduh CSV: " + err.message));
};

// Fungsi Global untuk Download Shapefile
window.downloadSHP = function (geom) {
    const geojson = JSON.parse(geom);
    fetch(`${API_BASE_URL}/analyze/shapefile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ polygon: geojson })
    })
        .then(res => {
            if (!res.ok) throw new Error("Tidak ada area rekomendasi untuk diekspor atau error server.");
            return res.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = "rekomendasi_optimal.zip";
            document.body.appendChild(a);
            a.click();
            a.remove();
        })
        .catch(err => alert("Gagal mengunduh Shapefile: " + err.message));
};

// 7. Klik Bebas Pada Peta untuk Mengetahui Detail Titik Spesifik (/api/suitability)
map.on('click', function (e) {
    // Abaikan klik jika sedang dalam mode menggambar poligon
    if (map.pm.Draw.getActiveShape()) return;

    const lat = e.latlng.lat;
    const lon = e.latlng.lng;

    fetch(`${API_BASE_URL}/suitability?lat=${lat}&lon=${lon}`)
        .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
            return res.json();
        })
        .then(data => {
            const d = data.data;
            // Clear any existing recommendation layer when clicking a point
            if (window.currentRecommendationLayer) {
                map.removeLayer(window.currentRecommendationLayer);
                window.currentRecommendationLayer = null;
            }
            let info = `
                <div style="min-width:200px;">
                    <b>Info Lokasi</b><hr>
                    <table style="width:100%; font-size:11px; border-collapse:collapse;">
                        ${generateInfoRow('Wilayah', d.nama_wilayah)}
                        ${generateInfoRow('Curah Hujan', d.curah_hujan.kelas)}
                        ${generateInfoRow('Kemiringan', d.kemiringan)}
                        ${generateInfoRow('Pola Ruang', d.zona_pola_ruang)}
                        ${generateInfoRow('Kesesuaian', `<span style="color:${getKesesuaianColor(d.kelas_jambu_mete)}; font-weight:bold;">${d.kelas_jambu_mete}</span>`)}
                    </table>
                </div>`;

            L.popup().setLatLng(e.latlng).setContent(info).openOn(map);
        })
        .catch(err => {
            console.error("✗ Error fetching suitability point:", err);
            L.popup().setLatLng(e.latlng).setContent("Gagal mengambil info lokasi.").openOn(map);
        });
});

// Tambahkan tombol toggle melayang ke body
document.body.insertAdjacentHTML('beforeend', `
    <button id="toggle-sidebar-btn" onclick="toggleSidebar()" title="Buka/Tutup Panel Analisis">
        ✕
    </button>
`);

console.log("✓ Fitur toggle dashboard berhasil diinisialisasi");