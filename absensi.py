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

def encode_photo_to_base64(photo_file):
    """Convert uploaded photo to base64 string for storage in spreadsheet"""
    try:
        # Read the photo file
        photo_bytes = photo_file.read()
        
        # Encode to base64
        encoded_string = base64.b64encode(photo_bytes).decode('utf-8')
        
        # Create data URL with proper MIME type
        mime_type = photo_file.type
        data_url = f"data:{mime_type};base64,{encoded_string}"
        
        return data_url
        
    except Exception as e:
        st.error(f"Error encoding photo: {e}")
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
    
    .photo-preview {
        border: 2px solid #DC143C;
        border-radius: 8px;
        padding: 10px;
        margin: 10px 0;
        background: white;
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
            help="Upload foto selfie sebagai bukti kehadiran. Format: PNG, JPG, JPEG. Maksimal 2MB untuk performa optimal."
        )
        
        if uploaded_photo is not None:
            # Check file size (limit to 2MB for better performance)
            file_size = len(uploaded_photo.getvalue())
            if file_size > 2 * 1024 * 1024:  # 2MB
                st.warning("⚠️ Ukuran file terlalu besar. Maksimal 2MB. Silakan kompres foto Anda.")
            else:
                st.markdown('<div class="photo-preview">', unsafe_allow_html=True)
                st.image(uploaded_photo, caption="Preview foto yang akan diupload", width=200)
                st.markdown('</div>', unsafe_allow_html=True)
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
                # Check file size again
                file_size = len(uploaded_photo.getvalue())
                if file_size > 2 * 1024 * 1024:  # 2MB
                    st.error("❌ Ukuran file terlalu besar. Maksimal 2MB.")
                else:
                    with st.spinner("⏳ Sedang memproses absensi..."):
                        try:
                            # Encode photo to base64
                            photo_base64 = encode_photo_to_base64(uploaded_photo)
                            
                            if photo_base64:
                                # Save to spreadsheet
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                new_row = [timestamp, nama, status_kehadiran, photo_base64]
                                worksheet.append_row(new_row)
                                
                                st.success(f"✅ Absensi untuk **{nama}** berhasil dicatat!")
                                st.balloons()
                            else:
                                st.error("❌ Gagal memproses foto. Silakan coba lagi.")
                                
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
        df_display = df.tail(10).copy()
        
        # Display records with photos
        for index, row in df_display.iterrows():
            with st.expander(f"📅 {row['Timestamp']} - {row['Nama']} ({row['Status Kehadiran']})"):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.markdown("**📸 Foto Absensi:**")
                    if 'Foto' in row and row['Foto']:
                        display_photo_from_base64(row['Foto'], width=150)
                    else:
                        st.text("Tidak ada foto")
                
                with col2:
                    st.markdown("**📋 Detail Absensi:**")
                    st.markdown(f"**👤 Nama:** {row['Nama']}")
                    st.markdown(f"**📊 Status:** {row['Status Kehadiran']}")
                    st.markdown(f"**⏰ Waktu:** {row['Timestamp']}")
        
        st.markdown("---")
        
        # Statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_entries = len(df)
            st.metric("📊 Total Absensi", total_entries)
        with col2:
            total_hadir = len(df[df['Status Kehadiran'] == 'Hadir'])
            st.metric("✅ Total Hadir", total_hadir)
        with col3:
            total_izin = len(df[df['Status Kehadiran'] == 'Izin'])
            st.metric("📝 Total Izin", total_izin)
        with col4:
            total_sakit = len(df[df['Status Kehadiran'] == 'Sakit'])
            st.metric("🏥 Total Sakit", total_sakit)
            
        # Attendance rate
        if total_entries > 0:
            attendance_rate = (total_hadir / total_entries) * 100
            st.markdown(f"### 📈 Tingkat Kehadiran: {attendance_rate:.1f}%")
            st.progress(attendance_rate / 100)
        
    else:
        st.info("📋 Belum ada data absensi yang tercatat.")
        
except Exception as e:
    st.error(f"❌ Gagal memuat riwayat absensi: {e}")

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 1rem;'>"
    "📱 Aplikasi Absensi PKL - Sistem Digital Terintegrasi<br>"
    "🔒 Data tersimpan aman di Google Sheets"
    "</div>", 
    unsafe_allow_html=True
)