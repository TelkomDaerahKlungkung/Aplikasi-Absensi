import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import io
import base64
from PIL import Image

scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scopes
)

client = gspread.authorize(creds)

def compress_and_encode_photo(photo_file, max_size_kb=30):
    """Compress and convert uploaded photo to base64 string with size limit"""
    try:
        # Open image with PIL
        image = Image.open(photo_file)
     
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
   
        max_dimension = 400  
        quality = 85
        
        # Resize image 
        if max(image.size) > max_dimension:
            ratio = max_dimension / max(image.size)
            new_size = tuple([int(x * ratio) for x in image.size])
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # Compress and encode
        for attempt in range(5):  
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=quality, optimize=True)
            
    
            buffer_size = len(buffer.getvalue())
            
           
            estimated_base64_size = (buffer_size * 4) // 3
            
            if estimated_base64_size < max_size_kb * 1024:  
                buffer.seek(0)
                encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
                data_url = f"data:image/jpeg;base64,{encoded_string}"
                
                
                if len(data_url) < 45000:  
                    return data_url
            
           
            quality -= 15
            if quality < 30:
                new_size = tuple([int(x * 0.8) for x in image.size])
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                quality = 85
        
        thumbnail_size = (100, 100)
        image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=50, optimize=True)
        buffer.seek(0)
        encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{encoded_string}"
        
        return data_url
        
    except Exception as e:
        st.error(f"Error compressing photo: {e}")
        return None

def display_photo_from_base64(base64_string, width=100):
    """Display photo from base64 string"""
    try:
        if base64_string and base64_string.startswith('data:'):
            st.image(base64_string, width=width)
        else:
            st.text("Foto tidak tersedia")
    except Exception as e:
        st.text("Error menampilkan foto")

spreadsheet = client.open("Absensi Kehadiran PKL") 
worksheet = spreadsheet.worksheet("Sheet1")

st.set_page_config(
    page_title="Absensi PKL", 
    layout="centered",
    page_icon="📝"
)

st.title("📝 Aplikasi Absensi PKL")
st.write("Sistem Absensi Digital untuk Praktek Kerja Lapangan")

st.divider()

# Simple form
with st.form("attendance_form", clear_on_submit=True):
    st.subheader("Formulir Absensi")
    
    # Input fields
    nama = st.text_input(
        "Nama Lengkap", 
        placeholder="Masukkan nama Anda..."
    )
    
    status_kehadiran = st.selectbox(
        "Status Kehadiran", 
        ["Hadir", "Izin", "Sakit"]
    )
    
    # Photo upload section
    st.subheader("Upload Foto Sebagi Bukti Kehadiran")
    st.info("Foto akan dikompres secara otomatis")
    uploaded_photo = st.file_uploader(
        "Pilih foto untuk absensi",
        type=['png', 'jpg', 'jpeg']
    )
    
    if uploaded_photo is not None:
        st.image(uploaded_photo, caption="Preview foto", width=200)
        file_size = len(uploaded_photo.getvalue())
        st.caption(f"Ukuran file: {file_size / 1024:.1f} KB")
    
    # Submit button
    submitted = st.form_submit_button("Submit Absen", type="primary")

    if submitted:
        if not nama:
            st.error("Nama tidak boleh kosong!")
        elif not uploaded_photo:
            st.error("Foto selfie wajib diupload!")
        else:
            with st.spinner("Sedang memproses absensi..."):
                try:
                  
                    photo_base64 = compress_and_encode_photo(uploaded_photo)
                    
                    if photo_base64:
                       
                        compressed_size = len(photo_base64)
                        st.info(f"Foto dikompres menjadi {compressed_size / 1024:.1f} KB")
                        
                     
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        new_row = [timestamp, nama, status_kehadiran, photo_base64]
                        worksheet.append_row(new_row)
                        
                        st.success(f"Absensi untuk {nama} berhasil dicatat!")
                        st.balloons()
                    else:
                        st.error("Gagal memproses foto. Silakan coba lagi.")
                        
                except Exception as e:
                    if "50000 characters" in str(e):
                        st.error("Foto terlalu besar. Silakan gunakan foto dengan resolusi lebih kecil.")
                    else:
                        st.error(f"Terjadi kesalahan: {e}")

st.divider()

st.subheader("Riwayat Absensi Terakhir")

try:
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        
        df_display = df.tail(10).copy()
        if 'Foto' in df_display.columns:
            df_display_table = df_display.drop(columns=['Foto'])
        else:
            df_display_table = df_display
        
        st.dataframe(df_display_table, use_container_width=True, hide_index=True)
        
    else:
        st.info("Belum ada data absensi yang tercatat.")
        
except Exception as e:
    st.error(f"Gagal memuat riwayat absensi: {e}")

st.divider()
