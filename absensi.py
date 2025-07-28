import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pytz
import io
import base64
from PIL import Image
import math

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

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2) * math.sin(delta_lat/2) + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon/2) * math.sin(delta_lon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c * 1000  # Convert to meters
    return distance

def check_location_telkom_klungkung(user_lat, user_lon):
    """Check if user is within Telkom Klungkung area"""
    # Koordinat Telkom Klungkung (perkiraan - sesuaikan dengan lokasi sebenarnya)
    telkom_lat = -8.531819
    telkom_lon = 115.384186
    
    # Radius yang diizinkan (dalam meter) - misal 500 meter dari kantor Telkom
    allowed_radius = 500
    
    distance = calculate_distance(user_lat, user_lon, telkom_lat, telkom_lon)
    return distance <= allowed_radius, distance

with st.form("attendance_form", clear_on_submit=True):
    st.subheader("Formulir Absensi")
    
    # Location check section
    st.subheader("📍 Verifikasi Lokasi")
    st.info("Absensi hanya dapat dilakukan di area Telkom Klungkung")
    
    # Get user location
    location_container = st.container()
    
    with location_container:
        col1, col2 = st.columns(2)
        with col1:
            user_latitude = st.number_input(
                "Latitude", 
                value=0.0, 
                format="%.6f",
                help="Latitude koordinat Anda"
            )
        with col2:
            user_longitude = st.number_input(
                "Longitude", 
                value=0.0, 
                format="%.6f",
                help="Longitude koordinat Anda"
            )
        
        # Location check button
        if st.button("🗺️ Cek Lokasi"):
            if user_latitude != 0.0 and user_longitude != 0.0:
                is_valid_location, distance = check_location_telkom_klungkung(user_latitude, user_longitude)
                
                if is_valid_location:
                    st.success(f"✅ Lokasi valid! Jarak dari Telkom Klungkung: {distance:.0f} meter")
                    st.session_state.location_verified = True
                    st.session_state.user_coordinates = (user_latitude, user_longitude)
                else:
                    st.error(f"❌ Lokasi tidak valid! Jarak dari Telkom Klungkung: {distance:.0f} meter")
                    st.warning("Absensi hanya dapat dilakukan dalam radius 500 meter dari kantor Telkom Klungkung")
                    st.session_state.location_verified = False
            else:
                st.warning("Masukkan koordinat lokasi yang valid!")
    
    st.markdown("---")
    
    # Auto-detect location using JavaScript (optional enhancement)
    st.markdown("""
    ### 🌐 Deteksi Lokasi Otomatis
    Klik tombol di bawah untuk mendapatkan lokasi otomatis dari browser:
    """)
    
    # JavaScript for location detection
    location_js = """
    <script>
    function getLocation() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(showPosition, showError);
        } else {
            alert("Geolocation tidak didukung oleh browser ini.");
        }
    }
    
    function showPosition(position) {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        
        // Update the input fields
        const latInput = parent.document.querySelector('input[aria-label="Latitude"]');
        const lonInput = parent.document.querySelector('input[aria-label="Longitude"]');
        
        if (latInput && lonInput) {
            latInput.value = lat.toFixed(6);
            lonInput.value = lon.toFixed(6);
            
            // Trigger change event
            latInput.dispatchEvent(new Event('input', { bubbles: true }));
            lonInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        
        alert(`Lokasi terdeteksi: ${lat.toFixed(6)}, ${lon.toFixed(6)}`);
    }
    
    function showError(error) {
        switch(error.code) {
            case error.PERMISSION_DENIED:
                alert("User menolak permintaan Geolocation.");
                break;
            case error.POSITION_UNAVAILABLE:
                alert("Informasi lokasi tidak tersedia.");
                break;
            case error.TIMEOUT:
                alert("Permintaan user location timeout.");
                break;
            case error.UNKNOWN_ERROR:
                alert("Terjadi error yang tidak diketahui.");
                break;
        }
    }
    </script>
    
    <button onclick="getLocation()" style="background-color: #4CAF50; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer;">
        📍 Dapatkan Lokasi Saya
    </button>
    """
    
    st.components.v1.html(location_js, height=100)
    
    st.markdown("---")
    
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
    st.subheader("Upload Foto Sebagai Bukti Kehadiran")
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
        # Check location verification first
        if not hasattr(st.session_state, 'location_verified') or not st.session_state.location_verified:
            st.error("❌ Silakan verifikasi lokasi terlebih dahulu!")
        elif not nama:
            st.error("❌ Nama tidak boleh kosong!")
        elif not uploaded_photo:
            st.error("❌ Foto wajib diupload!")
        else:
            # Double check location before submitting
            user_coords = st.session_state.user_coordinates
            is_valid, distance = check_location_telkom_klungkung(user_coords[0], user_coords[1])
            
            if not is_valid:
                st.error(f"❌ Lokasi tidak valid saat submit! Jarak: {distance:.0f} meter dari Telkom Klungkung")
                st.session_state.location_verified = False
            else:
                with st.spinner("Sedang memproses absensi..."):
                    try:
                        # Compress and encode photo
                        photo_base64 = compress_and_encode_photo(uploaded_photo)
                        
                        if photo_base64:
                            # Show compression info
                            compressed_size = len(photo_base64)
                            st.info(f"Foto dikompres menjadi {compressed_size / 1024:.1f} KB")
                            
                            # Bali time (WITA - UTC+8)
                            bali_tz = pytz.timezone('Asia/Makassar')
                            bali_time = datetime.now(bali_tz)
                            timestamp = bali_time.strftime("%Y-%m-%d %H:%M:%S WITA")
                            
                            # Include location data
                            location_info = f"{user_coords[0]:.6f},{user_coords[1]:.6f} (Jarak: {distance:.0f}m)"
                            
                            new_row = [timestamp, nama, status_kehadiran, photo_base64, location_info]
                            worksheet.append_row(new_row)
                            
                            st.success(f"✅ Absensi untuk {nama} berhasil dicatat!")
                            st.info(f"🕐 Waktu absensi: {timestamp}")
                            st.info(f"📍 Lokasi: {location_info}")
                            st.balloons()
                            
                            # Reset location verification
                            st.session_state.location_verified = False
                        else:
                            st.error("❌ Gagal memproses foto. Silakan coba lagi.")
                            
                    except Exception as e:
                        if "50000 characters" in str(e):
                            st.error("❌ Foto terlalu besar. Silakan gunakan foto dengan resolusi lebih kecil.")
                        else:
                            st.error(f"❌ Terjadi kesalahan: {e}")

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
