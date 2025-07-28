import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import io
import base64

scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scopes
)

client = gspread.authorize(creds)

# Google Drive client for photo uploads
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

drive_service = build('drive', 'v3', credentials=creds)

def upload_photo_to_drive(photo_file, nama):
    """Upload photo to Google Drive and return shareable link"""
    try:
        # Create a BytesIO object from the uploaded file
        file_bytes = io.BytesIO(photo_file.read())
        
        # File metadata
        file_metadata = {
            'name': f"absensi_{nama}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{photo_file.name.split('.')[-1]}",
            'parents': ['1ACue7dr_p8EXzLJbkZ85NnA6Sil9tHbe']  
        }
        
        # Upload file
        media = MediaIoBaseUpload(file_bytes, mimetype=photo_file.type, resumable=True)
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        
        # Make file publicly viewable
        drive_service.permissions().create(
            fileId=file.get('id'),
            body={'role': 'reader', 'type': 'anyone'}
        ).execute()
        
        # Return shareable link
        return f"https://drive.google.com/file/d/{file.get('id')}/view"
        
    except Exception as e:
        st.error(f"Error uploading photo: {e}")
        return None

spreadsheet = client.open("Absensi Kehadiran PKL") 
worksheet = spreadsheet.worksheet("Sheet1")

# Custom CSS for red color palette and professional styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #DC143C, #B22222);
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .form-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(220, 20, 60, 0.15);
        border: 2px solid #FFE4E1;
    }
    
    .stSelectbox > div > div {
        background-color: #FFF5F5;
        border: 2px solid #DC143C;
    }
    
    .stTextInput > div > div > input {
        background-color: #FFF5F5;
        border: 2px solid #DC143C;
    }
    
    .stButton > button {
        background: linear-gradient(45deg, #DC143C, #B22222);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 0 4px 15px rgba(220, 20, 60, 0.3);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(220, 20, 60, 0.4);
    }
    
    .history-section {
        background: #FFF8F8;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #DC143C;
    }
    
    .upload-section {
        background: #FFF5F5;
        padding: 1rem;
        border-radius: 8px;
        border: 1px dashed #DC143C;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="Absensi PKL", 
    layout="centered",
    page_icon="📝"
)

# Header with red gradient
st.markdown("""
<div class="main-header">
    <h1>📝 Aplikasi Absensi PKL</h1>
    <p>Sistem Absensi Digital untuk Praktek Kerja Lapangan</p>
</div>
""", unsafe_allow_html=True)

# Form container
with st.container():
    st.markdown('<div class="form-container">', unsafe_allow_html=True)
    
    with st.form("attendance_form", clear_on_submit=True):
        st.markdown("### 📋 Formulir Absensi")
        
        # Input fields
        col1, col2 = st.columns(2)
        
        with col1:
            nama = st.text_input(
                "👤 Nama Lengkap", 
                placeholder="Masukkan nama Anda...",
                help="Masukkan nama lengkap sesuai identitas"
            )
        
        with col2:
            status_kehadiran = st.selectbox(
                "📊 Status Kehadiran", 
                ["Hadir", "Izin", "Sakit"],
                help="Pilih status kehadiran Anda hari ini"
            )
        
        # Photo upload section
        st.markdown('<div class="upload-section">', unsafe_allow_html=True)
        st.markdown("### 📸 Upload Foto Selfie")
        uploaded_photo = st.file_uploader(
            "Pilih foto selfie untuk absensi",
            type=['png', 'jpg', 'jpeg'],
            help="Upload foto selfie sebagai bukti kehadiran. Format: PNG, JPG, JPEG. Maksimal 5MB."
        )
        
        if uploaded_photo is not None:
            st.image(uploaded_photo, caption="Preview foto yang akan diupload", width=200)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Submit button
        st.markdown("<br>", unsafe_allow_html=True)
        submitted = st.form_submit_button("🚀 SUBMIT ABSEN", use_container_width=True)

        if submitted:
            if not nama:
                st.error("❌ Nama tidak boleh kosong!")
            elif not uploaded_photo:
                st.error("❌ Foto selfie wajib diupload!")
            else:
                with st.spinner("⏳ Sedang memproses absensi..."):
                    try:
                        # Upload photo to Google Drive
                        photo_link = upload_photo_to_drive(uploaded_photo, nama)
                        
                        if photo_link:
                            # Save to spreadsheet
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            new_row = [timestamp, nama, status_kehadiran, photo_link]
                            worksheet.append_row(new_row)
                            
                            st.success(f"✅ Absensi untuk **{nama}** berhasil dicatat!")
                            st.balloons()
                        else:
                            st.error("❌ Gagal mengupload foto. Silakan coba lagi.")
                            
                    except Exception as e:
                        st.error(f"❌ Terjadi kesalahan: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# History section
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div class="history-section">', unsafe_allow_html=True)
st.markdown("### 🕰️ Riwayat Absensi Terakhir")

try:
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        # Format the dataframe for better display
        df_display = df.tail(5).copy()
        
        # Add clickable photo links
        if 'Foto' in df_display.columns:
            df_display['Foto'] = df_display['Foto'].apply(
                lambda x: f'[📷 Lihat Foto]({x})' if x else 'Tidak ada foto'
            )
        
        st.dataframe(
            df_display, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Timestamp": st.column_config.DatetimeColumn(
                    "⏰ Waktu",
                    format="DD/MM/YYYY HH:mm"
                ),
                "Nama": st.column_config.TextColumn(
                    "👤 Nama",
                    width="medium"
                ),
                "Status Kehadiran": st.column_config.TextColumn(
                    "📊 Status",
                    width="small"
                ),
                "Foto": st.column_config.LinkColumn(
                    "📸 Foto",
                    width="small"
                )
            }
        )
        
        # Statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            total_hadir = len(df[df['Status Kehadiran'] == 'Hadir'])
            st.metric("✅ Total Hadir", total_hadir)
        with col2:
            total_izin = len(df[df['Status Kehadiran'] == 'Izin'])
            st.metric("📝 Total Izin", total_izin)
        with col3:
            total_sakit = len(df[df['Status Kehadiran'] == 'Sakit'])
            st.metric("🏥 Total Sakit", total_sakit)
    else:
        st.info("📋 Belum ada data absensi yang tercatat.")
        
except Exception as e:
    st.error(f"❌ Gagal memuat riwayat absensi: {e}")

st.markdown('</div>', unsafe_allow_html=True)