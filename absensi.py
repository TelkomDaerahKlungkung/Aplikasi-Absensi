import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import io

# --- KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Absensi PKL - Telkom", 
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    
    .sub-header {
        text-align: center;
        color: #666;
        font-size: 1.2rem;
        margin-bottom: 2rem;
    }
    
    .stForm {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .form-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
    }
    
    .success-container {
        background: linear-gradient(90deg, #56ab2f, #a8e6cf);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        font-weight: bold;
    }
    
    .info-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #4ECDC4;
        margin: 1rem 0;
    }
    
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scopes
)

client = gspread.authorize(creds)
spreadsheet = client.open("Absensi Kehadiran PKL") 
worksheet = spreadsheet.worksheet("Sheet1")

# ID Folder di Google Drive tempat menyimpan foto
GDRIVE_FOLDER_ID = "your_folder_id_here"  # Ganti dengan ID folder Google Drive Anda

# --- FUNGSI UNTUK UPLOAD KE GOOGLE DRIVE ---
def upload_photo_to_drive(photo_bytes, photo_name):
    """Mengunggah file foto ke folder Google Drive dan mengembalikan link publik."""
    try:
        drive_service = build('drive', 'v3', credentials=creds)
        
        # Metadata file
        file_metadata = {
            'name': photo_name,
            'parents': [GDRIVE_FOLDER_ID]
        }
        
        # Membuat media dari bytes
        media = MediaIoBaseUpload(io.BytesIO(photo_bytes), mimetype='image/jpeg', resumable=True)
        
        # Upload file
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        # Dapatkan ID file yang baru diupload
        file_id = file.get('id')

        # Berikan izin akses publik (siapa saja dengan link bisa melihat)
        drive_service.permissions().create(fileId=file_id, body={'role': 'reader', 'type': 'anyone'}).execute()
        
        # Kembalikan link untuk dilihat
        return file.get('webViewLink')

    except Exception as e:
        st.error(f"Gagal mengunggah ke Google Drive: {e}")
        return None

# --- ANTARMUKA APLIKASI STREAMLIT ---
# Header Section
st.markdown('<h1 class="main-header">🎓 ABSENSI PKL TELKOM</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">📱 Sistem Absensi Digital untuk Peserta PKL</p>', unsafe_allow_html=True)

# Welcome Message
current_time = datetime.now()
current_hour = current_time.hour

if 5 <= current_hour < 12:
    greeting = "🌅 Selamat Pagi"
elif 12 <= current_hour < 17:
    greeting = "☀️ Selamat Siang"
elif 17 <= current_hour < 19:
    greeting = "🌆 Selamat Sore"
else:
    greeting = "🌙 Selamat Malam"

st.markdown(f"""
<div class="info-card">
    <h3>{greeting}, Peserta PKL! 👋</h3>
    <p>📅 <strong>Hari ini:</strong> {current_time.strftime('%A, %d %B %Y')}</p>
    <p>🕒 <strong>Waktu:</strong> {current_time.strftime('%H:%M:%S WIB')}</p>
</div>
""", unsafe_allow_html=True)

# Info Section
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("""
    <div class="stat-card">
        <h4>📋 MUDAH</h4>
        <p>Absen dengan cepat</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="stat-card">
        <h4>📸 SELFIE</h4>
        <p>Upload foto absen</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="stat-card">
        <h4>☁️ CLOUD</h4>
        <p>Data tersimpan aman</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Form Section
st.markdown("### 📝 Form Absensi")

with st.form("attendance_form", clear_on_submit=True):
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    
    # Input Nama dengan icon
    nama_PKL = st.text_input(
        "👤 Nama Lengkap PKL", 
        placeholder="Masukkan nama lengkap Anda...",
        help="Pastikan nama sesuai dengan data PKL Anda"
    )
    
    # Status Kehadiran dengan emoji
    status_options = {
        "Hadir": "✅ Hadir",
        "Izin": "📝 Izin", 
        "Sakit": "🏥 Sakit"
    }
    status_kehadiran = st.selectbox(
        "📊 Status Kehadiran", 
        options=list(status_options.keys()),
        format_func=lambda x: status_options[x]
    )
    
    # Upload foto dengan styling
    st.markdown("📸 **Upload Foto Selfie**")
    uploaded_photo = st.file_uploader(
        "Pilih foto selfie Anda", 
        type=['jpg', 'png', 'jpeg'],
        help="Format yang didukung: JPG, PNG, JPEG (Maksimal 5MB)"
    )
    
    if uploaded_photo is not None:
        st.image(uploaded_photo, caption="Preview foto Anda", width=200)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Submit button dengan styling
    submitted = st.form_submit_button(
        "🚀 SUBMIT ABSENSI", 
        use_container_width=True,
        type="primary"
    )

    if submitted:
        if not nama_PKL:
            st.error("❌ Nama PKL tidak boleh kosong!")
        else:
            # Progress bar untuk user experience
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            link_foto = ""
            if uploaded_photo is not None:
                status_text.text("📤 Mengunggah foto...")
                progress_bar.progress(25)
                
                # Baca file sebagai bytes
                photo_bytes = uploaded_photo.getvalue()
                # Buat nama file unik
                photo_name = f"{nama_PKL.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                
                progress_bar.progress(50)
                link_foto = upload_photo_to_drive(photo_bytes, photo_name)
                progress_bar.progress(75)

            if link_foto or uploaded_photo is None:
                status_text.text("💾 Menyimpan data absensi...")
                progress_bar.progress(90)
                
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Tambahkan link_foto ke baris baru
                new_row = [timestamp, nama_PKL, status_kehadiran, link_foto]
                worksheet.append_row(new_row)
                
                progress_bar.progress(100)
                status_text.empty()
                progress_bar.empty()
                
                # Success message dengan styling
                st.markdown(f"""
                <div class="success-container">
                    <h3>🎉 ABSENSI BERHASIL! 🎉</h3>
                    <p>Terima kasih <strong>{nama_PKL}</strong>!</p>
                    <p>Status: <strong>{status_options[status_kehadiran]}</strong></p>
                    <p>Waktu: <strong>{timestamp}</strong></p>
                </div>
                """, unsafe_allow_html=True)
                
                if link_foto:
                    st.success("📸 Foto berhasil diunggah ke Google Drive!")
                
                st.balloons()
                
                # Tips motivasi untuk PKL
                tips = [
                    "💪 Tetap semangat menjalani PKL!",
                    "🌟 Setiap hari adalah kesempatan belajar baru!",
                    "🚀 Jangan lupa catat pengalaman belajar hari ini!",
                    "📚 PKL adalah investasi untuk masa depan!",
                    "🎯 Konsistensi adalah kunci kesuksesan!"
                ]
                import random
                st.info(f"💡 **Tips Hari Ini:** {random.choice(tips)}")
                
            else:
                st.error("❌ Gagal mencatat absensi karena foto tidak berhasil diunggah.")

# --- RIWAYAT ABSENSI ---
st.markdown("---")
st.markdown("### 📊 Riwayat Absensi Terkini")

try:
    # Ambil data dari Google Sheets
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        
        # Tampilkan 5 data terakhir
        if len(df) > 0:
            recent_data = df.tail(5).iloc[::-1]  # 5 data terakhir, dibalik urutannya
            
            for index, row in recent_data.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**👤 {row.get('Nama', 'N/A')}**")
                        st.markdown(f"🕒 {row.get('Timestamp', 'N/A')}")
                    
                    with col2:
                        status = row.get('Status', 'N/A')
                        if status == 'Hadir':
                            st.markdown("✅ **Hadir**")
                        elif status == 'Izin':
                            st.markdown("📝 **Izin**")
                        elif status == 'Sakit':
                            st.markdown("🏥 **Sakit**")
                    
                    with col3:
                        if row.get('Link Foto'):
                            st.markdown("[📸 Lihat Foto]("+row.get('Link Foto')+")")
                        else:
                            st.markdown("📷 No Photo")
                    
                    st.markdown("---")
        else:
            st.info("📝 Belum ada data absensi.")
    else:
        st.info("📝 Belum ada data absensi.")
        
except Exception as e:
    st.error(f"❌ Error mengambil data: {e}")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 1rem;">
    <p>🏢 <strong>PT Telkom Indonesia</strong></p>
    <p>📧 Butuh bantuan? Hubungi pembimbing PKL Anda</p>
    <p>Made with ❤️ for PKL Students</p>
</div>
""", unsafe_allow_html=True)