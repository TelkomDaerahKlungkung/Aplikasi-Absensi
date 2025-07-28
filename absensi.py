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

# --- FUNGSI UNTUK INJEKSI CSS ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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

# --- FUNGSI KOMPRESI FOTO ---
def compress_and_encode_photo(photo_file, max_size_kb=45):
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
    .st-emotion-cache-1y4p8pa {
        padding-top: 2rem;
    }
    .st-form {
        border: 1px solid #262730;
        border-radius: 10px;
        padding: 20px;
        background-color: #0E1117;
    }
    .st-emotion-cache-16txtl3 {
        padding: 2rem 2rem;
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

    # LANGKAH 1: PILIH STATUS DULU
    status_kehadiran = st.selectbox(
        "Pilih Status Kehadiran Anda:",
        ["Hadir", "Izin", "Sakit"],
        key="status_kehadiran"
    )

    # Inisialisasi status validasi lokasi
    if 'lokasi_valid' not in st.session_state:
        st.session_state.lokasi_valid = False

    # LANGKAH 2: VALIDASI LOKASI (HANYA JIKA 'HADIR')
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
                st.session_state.lokasi_valid = True
            else:
                st.error(f"❌ Lokasi Tidak Valid! Jarak Anda: {jarak:.2f} meter. Harap mendekat ke lokasi kantor.")
                st.session_state.lokasi_valid = False
        else:
            st.warning("Harap izinkan akses lokasi di browser Anda untuk melanjutkan.")
            st.session_state.lokasi_valid = False
    else:
        # Jika status Izin atau Sakit, tidak perlu validasi lokasi
        st.info("ℹ️ Untuk status 'Izin' atau 'Sakit', verifikasi lokasi tidak diperlukan.")
        st.session_state.lokasi_valid = True # Anggap lokasi valid agar form bisa disubmit

    # LANGKAH 3: FORMULIR UTAMA
    st.markdown("---")
    with st.form("attendance_form", clear_on_submit=True):
        nama = st.text_input("👤 Nama Lengkap", placeholder="Masukkan nama Anda...")
        
        # Input keterangan izin jika status adalah "Izin"
        keterangan_izin = ""
        if status_kehadiran == "Izin":
            keterangan_izin = st.text_area(
                "📝 Keterangan Izin (Wajib)",
                placeholder="Jelaskan alasan izin Anda...",
                help="Contoh: Keperluan keluarga, urusan kampus, sakit ringan, dll."
            )
        
        # Upload foto dengan contoh sebelumnya
        if status_kehadiran == "Hadir":
            st.markdown("##### 📸 Upload Foto Selfie")
            
            # Tampilkan contoh foto sebelum upload
            st.markdown("**Contoh foto yang baik:**")
            st.image("https://raw.githubusercontent.com/TelkomDaerahKlungkung/Aplikasi-Absensi/main/images/Contoh%20Foto.jpg", caption="Contoh Foto Selfie", width=200)
            st.markdown("**Tips foto selfie yang baik:**")
            st.markdown("""
            - 📱 Pastikan wajah terlihat jelas dan tidak tertutup
            - 💡 Gunakan pencahayaan yang cukup
            - 🏢 Ambil foto di area kantor atau lokasi kerja
            - 📐 Posisikan kamera sejajar dengan wajah
            - 🚫 Hindari foto blur atau gelap
            """)
            
            uploaded_photo = st.file_uploader(
                "Pilih foto selfie untuk absensi",
                type=['png', 'jpg', 'jpeg'],
                help="Format yang didukung: PNG, JPG, JPEG. Maksimal ukuran akan dikompres otomatis."
            )
            
            if uploaded_photo is not None:
                st.image(uploaded_photo, caption="Preview foto yang akan diupload", width=200)
                file_size = len(uploaded_photo.getvalue())
                st.caption(f"📁 Ukuran file: {file_size / 1024:.1f} KB")
        else:
            uploaded_photo = None
        
        # Tombol submit hanya bisa diklik jika validasi terpenuhi
        submitted = st.form_submit_button(
            "SUBMIT ABSENSI", 
            type="primary", 
            use_container_width=True,
            disabled=not st.session_state.get('lokasi_valid', False)
        )

        if submitted:
            if not nama:
                st.error("❌ Nama tidak boleh kosong!")
            elif status_kehadiran == "Izin" and not keterangan_izin.strip():
                st.error("❌ Keterangan izin wajib diisi untuk status 'Izin'!")
            elif status_kehadiran == "Hadir" and not uploaded_photo:
                st.error("❌ Foto selfie wajib diunggah untuk status 'Hadir'!")
            else:
                with st.spinner("Sedang memproses absensi..."):
                    photo_base64 = ""
                    if uploaded_photo:
                        photo_base64 = compress_and_encode_photo(uploaded_photo)
                        if not photo_base64:
                            st.error("❌ Gagal memproses foto. Silakan coba lagi.")
                            st.stop()

                    bali_tz = pytz.timezone('Asia/Makassar')
                    timestamp = datetime.now(bali_tz).strftime("%Y-%m-%d %H:%M:%S WITA")
                    
                    # Update row structure untuk kolom baru
                    new_row = [timestamp, nama, status_kehadiran, photo_base64, keterangan_izin]
                    worksheet.append_row(new_row)
                    
                    st.success(f"✅ Absensi untuk **{nama}** dengan status **{status_kehadiran}** berhasil dicatat!")
                    if status_kehadiran == "Izin":
                        st.info(f"📝 Keterangan: {keterangan_izin}")
                    st.balloons()

# --- KOLOM KANAN UNTUK RIWAYAT ---
with col2:
    st.subheader("📜 Riwayat Absensi Terakhir")
    try:
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            # Tampilkan kolom yang relevan (tanpa foto untuk menghemat space)
            display_columns = ['Timestamp', 'Nama', 'Status Kehadiran', 'Keterangan Izin']
            df_display = df[display_columns].tail(10)
            
            # Ganti nilai kosong di Keterangan Izin dengan "-"
            df_display['Keterangan Izin'] = df_display['Keterangan Izin'].fillna("-").replace("", "-")
            
            st.dataframe(
                df_display, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Timestamp": st.column_config.TextColumn("⏰ Waktu", width="medium"),
                    "Nama": st.column_config.TextColumn("👤 Nama", width="medium"),
                    "Status Kehadiran": st.column_config.TextColumn("📊 Status", width="small"),
                    "Keterangan Izin": st.column_config.TextColumn("📝 Keterangan", width="large")
                }
            )
            
            # Statistik singkat
            st.markdown("---")
            st.markdown("**📊 Statistik Hari Ini:**")
            today = datetime.now(pytz.timezone('Asia/Makassar')).strftime("%Y-%m-%d")
            today_data = df[df['Timestamp'].str.contains(today, na=False)]
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                hadir_count = len(today_data[today_data['Status Kehadiran'] == 'Hadir'])
                st.metric("✅ Hadir", hadir_count)
            with col_stat2:
                izin_count = len(today_data[today_data['Status Kehadiran'] == 'Izin'])
                st.metric("📝 Izin", izin_count)
            with col_stat3:
                sakit_count = len(today_data[today_data['Status Kehadiran'] == 'Sakit'])
                st.metric("🏥 Sakit", sakit_count)
                
        else:
            st.info("Belum ada data absensi yang tercatat.")
    except Exception as e:
        st.error(f"Gagal memuat riwayat absensi: {e}")