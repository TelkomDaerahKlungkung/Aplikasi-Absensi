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
# Konfigurasi dasar
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
KANTOR_LAT = -8.5259272
KANTOR_LON = 115.40337
RADIUS_MAKSIMAL_METER = 50

# Inisialisasi koneksi (dibuat cache agar tidak konek ulang terus-menerus)
@st.cache_resource
def connect_to_google_sheets():
    try:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open("Absensi Kehadiran PKL")
        worksheet = spreadsheet.worksheet("Sheet1")
        return worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Spreadsheet 'Absensi Kehadiran PKL' tidak ditemukan. Pastikan nama sudah benar dan Service Account memiliki akses.")
        st.stop()
    except Exception as e:
        st.error(f"Gagal terhubung ke Google Sheets: {e}")
        st.stop()

worksheet = connect_to_google_sheets()

# --- FUNGSI BANTUAN ---
def compress_and_encode_photo(photo_file, max_size_kb=45):
    """Mengompres foto dan mengubahnya menjadi Base64."""
    try:
        image = Image.open(photo_file)
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        max_dimension = 400
        quality = 85
        if max(image.size) > max_dimension:
            ratio = max_dimension / max(image.size)
            new_size = tuple([int(x * ratio) for x in image.size])
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        for _ in range(5):
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=quality, optimize=True)
            if (len(buffer.getvalue()) * 4 / 3) < max_size_kb * 1024:
                buffer.seek(0)
                encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
                return f"data:image/jpeg;base64,{encoded_string}"
            quality -= 15
        st.warning("Ukuran foto terlalu besar setelah kompresi. Silakan gunakan foto lain.")
        return None
    except Exception as e:
        st.error(f"Error saat kompresi foto: {e}")
        return None

# --- UI APLIKASI ---
st.set_page_config(page_title="Absensi PKL", layout="wide", page_icon="🏢")

# Injeksi CSS untuk styling
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .st-form {
        border: 1px solid #262730;
        border-radius: 10px;
        padding: 20px;
        background-color: #0E1117;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.title("🏢 Sistem Absensi Digital PKL")
st.markdown("Selamat datang! Silakan lakukan absensi sesuai dengan status kehadiran Anda hari ini.")
st.divider()

# --- ALUR UTAMA APLIKASI ---
col1, col2 = st.columns([0.6, 0.4])

with col1:
    st.subheader("📋 Formulir Kehadiran")

    # Menggunakan form untuk semua input
    with st.form("attendance_form", clear_on_submit=True):
        nama = st.text_input("👤 Nama Lengkap", placeholder="Masukkan nama Anda...")
        status_kehadiran = st.selectbox(
            "Pilih Status Kehadiran Anda:",
            ["Hadir", "Izin", "Sakit"],
            key="status_kehadiran"
        )
        
        # Inisialisasi variabel default
        keterangan_izin = ""
        uploaded_photo = None
        is_location_verified = False

        # --- LOGIKA KONDISIONAL BERDASARKAN STATUS ---
        if status_kehadiran == "Hadir":
            st.markdown("---")
            st.markdown("##### 📍 Verifikasi Lokasi (Wajib untuk status Hadir)")
            location_data = streamlit_geolocation()

            if location_data and location_data.get('latitude'):
                user_coords = (location_data['latitude'], location_data['longitude'])
                kantor_coords = (KANTOR_LAT, KANTOR_LON)
                jarak = geodesic(user_coords, kantor_coords).meters

                if jarak <= RADIUS_MAKSIMAL_METER:
                    st.success(f"✅ Lokasi Terverifikasi! Jarak Anda dari kantor: {jarak:.2f} meter.")
                    is_location_verified = True
                else:
                    st.error(f"❌ Lokasi Tidak Valid! Jarak Anda: {jarak:.2f} meter. Harap mendekat ke lokasi kantor.")
                    is_location_verified = False
            else:
                st.warning("Harap izinkan akses lokasi di browser untuk melanjutkan.")
                is_location_verified = False
            
            st.markdown("---")
            st.markdown("##### 📸 Unggah Foto Selfie (Wajib untuk status Hadir)")
            with st.expander("Lihat Contoh Foto Absensi yang Benar"):
                st.image("https://raw.githubusercontent.com/TelkomDaerahKlungkung/Aplikasi-Absensi/main/images/Contoh%20Foto.jpg", caption="Contoh foto yang menampilkan titik koordinat dan timestamp.", width=300)
            uploaded_photo = st.file_uploader("Pilih foto selfie Anda", type=['png', 'jpg', 'jpeg'])

        elif status_kehadiran == "Izin":
            st.markdown("---")
            st.markdown("##### ✍️ Keterangan Izin (Wajib diisi)")
            st.info("Untuk status 'Izin', verifikasi lokasi tidak diperlukan.")
            keterangan_izin = st.text_area("Tuliskan alasan izin Anda di sini...", height=150, key="keterangan_izin_input")
        
        elif status_kehadiran == "Sakit":
            st.markdown("---")
            st.info("ℹ️ Untuk status 'Sakit', Anda bisa langsung mengirim absensi. Verifikasi lokasi tidak diperlukan.")

        st.markdown("---")
        
        # Menentukan apakah tombol submit harus aktif
        if status_kehadiran == "Hadir":
            can_submit = is_location_verified and uploaded_photo is not None and nama.strip()
        elif status_kehadiran == "Izin":
            can_submit = bool(keterangan_izin.strip()) and nama.strip()
        else:  # Sakit
            can_submit = bool(nama.strip())

        submitted = st.form_submit_button(
            "SUBMIT ABSENSI", 
            type="primary", 
            use_container_width=True,
            disabled=not can_submit
        )

        if submitted:
            # Validasi input setelah tombol ditekan
            if not nama:
                st.error("Nama tidak boleh kosong!")
            elif status_kehadiran == "Hadir" and not uploaded_photo:
                st.error("Foto selfie wajib diunggah untuk status 'Hadir'!")
            elif status_kehadiran == "Hadir" and not is_location_verified:
                st.error("Lokasi belum terverifikasi untuk status 'Hadir'!")
            elif status_kehadiran == "Izin" and not keterangan_izin.strip():
                st.error("Keterangan Izin wajib diisi!")
            else:
                with st.spinner("Sedang memproses absensi..."):
                    photo_base64 = ""
                    if uploaded_photo:
                        photo_base64 = compress_and_encode_photo(uploaded_photo)

                    bali_tz = pytz.timezone('Asia/Makassar')
                    timestamp = datetime.now(bali_tz).strftime("%Y-%m-%d %H:%M:%S WITA")
                    
                    # Membuat baris data sesuai urutan kolom baru
                    new_row = [timestamp, nama, status_kehadiran, photo_base64, keterangan_izin]
                    worksheet.append_row(new_row)
                    
                    st.success(f"Absensi untuk **{nama}** dengan status **{status_kehadiran}** berhasil dicatat!")
                    st.balloons()

# --- KOLOM KANAN UNTUK RIWAYAT ---
with col2:
    st.subheader("📜 Riwayat Absensi Terakhir")
    try:
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            # Tampilkan semua kolom kecuali kolom foto dan keterangan
            st.dataframe(
                df.tail(10).drop(columns=['Foto', 'Keterangan Izin'], errors='ignore'), 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("Belum ada data absensi yang tercatat.")
    except Exception as e:
        st.error(f"Gagal memuat riwayat absensi: {e}")
