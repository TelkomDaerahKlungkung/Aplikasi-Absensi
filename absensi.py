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
GDRIVE_FOLDER_ID = "1ACue7dr_p8EXzLJbkZ85NnA6Sil9tHbe" 

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
st.set_page_config(page_title="Absensi Kantor", layout="centered")
st.title("📝 Aplikasi Absensi PKL")

with st.form("attendance_form", clear_on_submit=True):
    nama_PKL = st.text_input("Nama Lengkap PKL", placeholder="Masukkan nama Anda...")
    status_kehadiran = st.selectbox("Status Kehadiran", ["Hadir", "Izin", "Sakit"])
    
    # Widget untuk upload foto
    uploaded_photo = st.file_uploader("Unggah Foto Selfie", type=['jpg', 'png', 'jpeg'])
    
    submitted = st.form_submit_button("SUBMIT ABSEN")

    if submitted:
        if not nama_PKL:
            st.warning("Nama PKL tidak boleh kosong!")
        else:
            link_foto = ""
            if uploaded_photo is not None:
                # Baca file sebagai bytes
                photo_bytes = uploaded_photo.getvalue()
                # Buat nama file unik
                photo_name = f"{nama_PKL.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                
                with st.spinner("Mengunggah foto..."):
                    link_foto = upload_photo_to_drive(photo_bytes, photo_name)

            if link_foto or uploaded_photo is None:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                # Tambahkan link_foto ke baris baru
                new_row = [timestamp, nama_PKL, status_kehadiran, link_foto]
                worksheet.append_row(new_row)
                st.success(f"Absensi untuk **{nama_PKL}** berhasil dicatat! ✅")
                if link_foto:
                    st.image(uploaded_photo, width=200)
                st.balloons()
            else:
                # Jika upload gagal tapi foto diunggah
                st.error("Gagal mencatat absensi karena foto tidak berhasil diunggah.")

# --- RIWAYAT ABSENSI ---
st.divider()
st.subheader("📜 Riwayat Absensi")

# Tampilkan riwayat absensi dari Google Sheets
data = worksheet.get_all_records()
if data:
    df = pd.DataFrame(data)
    st.dataframe(df)
else:
    st.warning("Belum ada riwayat absensi yang dicatat.")