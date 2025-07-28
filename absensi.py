import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
import io
import base64
from PIL import Image
from streamlit_geolocation import streamlit_geolocation
from geopy.distance import geodesic

# --- KONFIGURASI & KONEKSI ---
# Pastikan scope untuk Sheets dan Drive ada
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Ambil kredensial dari Streamlit Secrets
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scopes
)

# Otorisasi koneksi
client = gspread.authorize(creds)

# Buka Spreadsheet dan Worksheet
try:
    spreadsheet = client.open("Absensi Kehadiran PKL")
    worksheet = spreadsheet.worksheet("Sheet1")
except gspread.exceptions.SpreadsheetNotFound:
    st.error("Spreadsheet 'Absensi Kehadiran PKL' tidak ditemukan. Pastikan nama sudah benar dan Service Account memiliki akses.")
    st.stop()

# --- PENGATURAN LOKASI KANTOR ---
# Koordinat Kantor Telkom Klungkung
KANTOR_LAT = -8.5361
KANTOR_LON = 115.4023
# Radius maksimal absensi dalam meter
RADIUS_MAKSIMAL_METER = 50

# --- FUNGSI KOMPRESI FOTO ---
def compress_and_encode_photo(photo_file, max_size_kb=45):
    """
    Mengompres foto, mengubahnya menjadi Base64, dan memastikan ukurannya
    di bawah batas aman sel Google Sheets.
    """
    try:
        image = Image.open(photo_file)
        # Konversi gambar yang memiliki alpha channel (transparansi) ke RGB
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')

        # Pengaturan awal
        max_dimension = 400
        quality = 85

        # Resize jika gambar terlalu besar
        if max(image.size) > max_dimension:
            ratio = max_dimension / max(image.size)
            new_size = tuple([int(x * ratio) for x in image.size])
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Loop untuk mencoba kompresi hingga ukuran sesuai
        for _ in range(5):
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=quality, optimize=True)
            
            # Cek ukuran Base64, Google Sheet punya limit ~50KB per sel
            # Kita targetkan di bawah 45KB agar aman
            if (len(buffer.getvalue()) * 4 / 3) < max_size_kb * 1024:
                buffer.seek(0)
                encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return f"data:image/jpeg;base64,{encoded_string}"
            
            # Kurangi kualitas jika masih terlalu besar
            quality -= 15
        
        st.warning("Ukuran foto terlalu besar bahkan setelah kompresi maksimal. Silakan gunakan foto lain.")
        return None

    except Exception as e:
        st.error(f"Error saat kompresi foto: {e}")
        return None

# --- UI APLIKASI ---
st.set_page_config(page_title="Absensi PKL", layout="centered", page_icon="📝")
st.title("📝 Aplikasi Absensi PKL")
st.write("Sistem Absensi Digital untuk Praktek Kerja Lapangan.")
st.divider()

# --- BAGIAN VERIFIKASI LOKASI ---
st.subheader("📍 Langkah 1: Verifikasi Lokasi Anda")
st.info(f"Anda harus berada dalam radius {RADIUS_MAKSIMAL_METER} meter dari Kantor Telkom Klungkung untuk bisa absen.")

location_data = streamlit_geolocation(key="user_location_key")

# Simpan lokasi di session state agar tidak hilang saat interaksi lain
if location_data and location_data['latitude']:
    st.session_state.user_location = location_data

# Periksa dan tampilkan status lokasi jika data sudah ada
if 'user_location' in st.session_state:
    user_coords = (st.session_state.user_location['latitude'], st.session_state.user_location['longitude'])
    kantor_coords = (KANTOR_LAT, KANTOR_LON)
    
    jarak = geodesic(user_coords, kantor_coords).meters
    
    if jarak <= RADIUS_MAKSIMAL_METER:
        st.success(f"✅ Lokasi Terverifikasi! Jarak Anda dari kantor: {jarak:.2f} meter.")
        st.session_state.lokasi_valid = True
    else:
        st.error(f"❌ Lokasi Tidak Valid! Jarak Anda dari kantor: {jarak:.2f} meter. Harap mendekat ke lokasi kantor.")
        st.session_state.lokasi_valid = False
else:
    st.warning("Klik tombol 'Get Location' dan izinkan akses lokasi di browser Anda.")
    if 'lokasi_valid' not in st.session_state:
        st.session_state.lokasi_valid = False

st.divider()

# --- BAGIAN FORMULIR ABSENSI ---
with st.form("attendance_form", clear_on_submit=True):
    st.subheader("📝 Langkah 2: Isi Formulir Absensi")
    
    nama = st.text_input("Nama Lengkap", placeholder="Masukkan nama Anda...")
    status_kehadiran = st.selectbox("Status Kehadiran", ["Hadir", "Izin", "Sakit"])
    
    st.info("Foto akan dikompres secara otomatis. Wajib untuk status 'Hadir'.")
    uploaded_photo = st.file_uploader("Pilih foto selfie sebagai bukti", type=['png', 'jpg', 'jpeg'])
    
    # Tombol submit hanya bisa diklik jika lokasi valid
    submitted = st.form_submit_button("SUBMIT ABSEN", type="primary", disabled=not st.session_state.get('lokasi_valid', False))

    if submitted:
        # Validasi input
        if not nama:
            st.error("Nama tidak boleh kosong!")
        elif status_kehadiran == "Hadir" and not uploaded_photo:
            st.error("Foto selfie wajib diunggah untuk status 'Hadir'!")
        else:
            with st.spinner("Sedang memproses absensi..."):
                photo_base64 = ""
                # Hanya proses foto jika ada yang diunggah
                if uploaded_photo:
                    photo_base64 = compress_and_encode_photo(uploaded_photo)

                # Dapatkan timestamp WITA
                bali_tz = pytz.timezone('Asia/Makassar')
                timestamp = datetime.now(bali_tz).strftime("%Y-%m-%d %H:%M:%S WITA")
                
                # Simpan ke Google Sheets
                new_row = [timestamp, nama, status_kehadiran, photo_base64]
                worksheet.append_row(new_row)
                
                st.success(f"Absensi untuk **{nama}** berhasil dicatat!")
                st.balloons()

# --- BAGIAN RIWAYAT ABSENSI ---
st.divider()
st.subheader("Riwayat Absensi Terakhir")
try:
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        # Tampilkan semua kolom kecuali kolom foto
        st.dataframe(df.tail(10).drop(columns=['Foto'], errors='ignore'), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data absensi yang tercatat.")
except Exception as e:
    st.error(f"Gagal memuat riwayat absensi: {e}")