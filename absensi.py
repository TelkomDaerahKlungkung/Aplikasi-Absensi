import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
import io

# --- KONFIGURASI KONEKSI ---
# Pastikan kedua scope ini ada
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
GDRIVE_FOLDER_ID = "178Sd_teFZ9_tI6yvmwqjeV5GAxXHTOVD" 

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

st.set_page_config(
    page_title="Absensi PKL Telkom",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background-color: #f5f7ff;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .title-container {
        background-color: #E31937;
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
    }
    .form-header {
        background-color: #005593;
        color: white;
        padding: 0.8rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        text-align: center;
    }
    .stButton>button {
        background-color: #E31937;
        color: white;
        border: none;
        width: 100%;
        padding: 0.5rem 0;
        font-weight: bold;
        border-radius: 5px;
    }
    .stButton>button:hover {
        background-color: #c0142d;
    }
    .history-header {
        background-color: #005593;
        color: white;
        padding: 0.8rem;
        border-radius: 5px;
        margin: 2rem 0 1rem 0;
        text-align: center;
    }
    .status-hadir {
        background-color: #28a745;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
    }
    .status-izin {
        background-color: #ffc107;
        color: black;
        padding: 3px 8px;
        border-radius: 12px;
    }
    .status-sakit {
        background-color: #dc3545;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
    }
    .stSelectbox label, .stFileUploader label, .stTextInput label {
        font-weight: bold;
    }
    footer {
        text-align: center;
        margin-top: 2rem;
        color: #6c757d;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# --- HEADER APLIKASI ---
st.markdown('<div class="title-container"><h1>📝 SISTEM ABSENSI PKL TELKOM</h1><p>Monitoring Kehadiran Peserta PKL PT. Telkom Indonesia</p></div>', unsafe_allow_html=True)

# --- TAMPILAN APLIKASI ---
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="form-header"><h3>📋 Form Absensi Harian</h3></div>', unsafe_allow_html=True)
    
    with st.form("attendance_form", clear_on_submit=True):
        nama_PKL = st.text_input("👤 Nama Lengkap PKL", placeholder="Masukkan nama Anda...")
        
        col_status, col_date = st.columns(2)
        with col_status:
            status_kehadiran = st.selectbox("🔵 Status Kehadiran", ["Hadir", "Izin", "Sakit"])
        with col_date:
            current_date = datetime.now().strftime("%d/%m/%Y")
            st.info(f"📅 Tanggal: {current_date}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 📷 Unggah Bukti Kehadiran")
        uploaded_photo = st.file_uploader("Unggah Foto Selfie", type=['jpg', 'png', 'jpeg'])
        
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("📤 SUBMIT ABSEN")

        if submitted:
            if not nama_PKL:
                st.warning("⚠️ Nama PKL tidak boleh kosong!")
            else:
                link_foto = ""
                if uploaded_photo is not None:
                   
                    photo_bytes = uploaded_photo.getvalue()
                   
                    photo_name = f"{nama_PKL.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                    
                    with st.spinner("⏳ Mengunggah foto..."):
                        link_foto = upload_photo_to_drive(photo_bytes, photo_name)

                if link_foto or uploaded_photo is None:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # Tambahkan link_foto ke baris baru
                    new_row = [timestamp, nama_PKL, status_kehadiran, link_foto]
                    worksheet.append_row(new_row)
                    st.success(f"✅ Absensi untuk **{nama_PKL}** berhasil dicatat!")
                    if link_foto:
                        st.markdown("##### 📸 Bukti Absensi:")
                        st.image(uploaded_photo, width=300)
                    st.balloons()
                else:
                    # Jika upload gagal tapi foto diunggah
                    st.error("❌ Gagal mencatat absensi karena foto tidak berhasil diunggah.")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="form-header"><h3>ℹ️ Informasi Absensi</h3></div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 📜 Petunjuk Absensi
    1. Isi form dengan data yang lengkap dan valid
    2. Upload foto selfie sebagai bukti kehadiran
    3. Pilih status sesuai kondisi Anda:
        - **Hadir** - Untuk kehadiran normal
        - **Izin** - Untuk ketidakhadiran dengan izin
        - **Sakit** - Untuk ketidakhadiran karena sakit
    4. Klik "SUBMIT ABSEN" untuk mengirimkan data
    
    ### ⏰ Waktu Absensi
    - **Masuk**: 08.00 - 09.00 WIB
    - **Pulang**: 16.00 - 17.00 WIB
    
    ### 🔔 Pemberitahuan
    Pastikan Anda melakukan absensi tepat waktu untuk menghindari keterlambatan!
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- RIWAYAT ABSENSI ---
st.markdown('<div class="history-header"><h2>📊 RIWAYAT ABSENSI</h2></div>', unsafe_allow_html=True)
st.markdown('<div class="card">', unsafe_allow_html=True)

# Tampilkan riwayat absensi dari Google Sheets
data = worksheet.get_all_records()
if data:
    df = pd.DataFrame(data)
    
    # Menambahkan styling ke DataFrame
    def highlight_status(val):
        if val == 'Hadir':
            return '<span class="status-hadir">Hadir</span>'
        elif val == 'Izin':
            return '<span class="status-izin">Izin</span>'
        elif val == 'Sakit':
            return '<span class="status-sakit">Sakit</span>'
        return val
    
    # Mengubah kolom timestamp untuk tampilan yang lebih baik
    if 'Timestamp' in df.columns:
        try:
            df['Tanggal'] = pd.to_datetime(df['Timestamp']).dt.strftime('%d/%m/%Y')
            df['Waktu'] = pd.to_datetime(df['Timestamp']).dt.strftime('%H:%M')
            df = df.drop('Timestamp', axis=1)
            
            # Reorganisasi kolom
            columns_order = ['Tanggal', 'Waktu', 'Nama PKL', 'Status Kehadiran', 'Link Foto']
            df = df.reindex(columns=columns_order)
        except Exception as e:
            st.warning(f"Format tanggal tidak dapat diproses: {e}")
    
    # Mengubah nama kolom jika diperlukan
    df = df.rename(columns={
        'nama_PKL': 'Nama PKL',
        'status_kehadiran': 'Status Kehadiran', 
        'link_foto': 'Link Foto'
    })
    
    # Tampilkan tabel dengan styling
    st.markdown(
        df.style.format({
            'Status Kehadiran': lambda x: highlight_status(x)
        }).to_html(escape=False, index=False),
        unsafe_allow_html=True
    )
else:
    st.info("🔍 Belum ada riwayat absensi yang dicatat.")

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown('<footer>© 2023 Aplikasi Absensi PKL Telkom | Developed by Mahasiswa PKL Telkom</footer>', unsafe_allow_html=True)