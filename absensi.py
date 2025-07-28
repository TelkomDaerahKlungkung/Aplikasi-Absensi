import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- KONEKSI MENGGUNAKAN STREAMLIT SECRETS ---
scopes = ['https://www.googleapis.com/auth/spreadsheets']

# Mengambil kredensial dari st.secrets
# Nama "gcp_service_account" harus sama dengan nama kategori di file secrets.toml
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scopes
)

client = gspread.authorize(creds)
   

    # Buka spreadsheet berdasarkan namanya
spreadsheet = client.open("Absensi Kehadiran PKL") 
worksheet = spreadsheet.worksheet("Sheet1") # Ganti dengan nama sheet Anda

# --- ANTARMUKA APLIKASI STREAMLIT ---

st.set_page_config(page_title="Absensi Kantor", layout="centered")
st.title("📝 Aplikasi Absensi PKL")

with st.form("attendance_form", clear_on_submit=True):
    # Kolom isian
    nama = st.text_input("Nama Lengkap ", placeholder="Masukkan nama Anda...")
    status_kehadiran = st.selectbox("Status Kehadiran", ["Hadir", "Izin", "Sakit"])
    
    # Tombol submit
    submitted = st.form_submit_button("SUBMIT ABSEN")

    if submitted:
        if not nama:
            st.warning("Nama tidak boleh kosong!")
        else:
            try:
                # Dapatkan timestamp saat ini
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Buat baris data baru
                new_row = [timestamp, nama, status_kehadiran]
                
                # Tambahkan baris baru ke worksheet
                worksheet.append_row(new_row)
                
                st.success(f"Absensi untuk **{nama}** berhasil dicatat! ✅")
                st.balloons()
                
            except Exception as e:
                st.error(f"Terjadi kesalahan saat menyimpan data: {e}")

# Menampilkan data absensi terakhir (opsional)
st.divider()
st.header("🕰️ Riwayat Absensi Terakhir")
try:
    data = worksheet.get_all_records()
    if data:
        df = pd.DataFrame(data)
        # Tampilkan 5 baris terakhir
        st.dataframe(df.tail(), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data absensi yang tercatat.")
except Exception as e:
    st.error(f"Gagal memuat riwayat absensi: {e}")