from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pymysql
from datetime import datetime

app = FastAPI(title="API Presensi Restoran Ria Galeria")

# Konfigurasi Koneksi Database Cloud ke TiDB Cloud
def get_db_connection():
    return pymysql.connect(
        host='gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
        port=4000,
        user='CbNvquGaRiEJBND.root',
        password='MEtvURW04X6aCj3a',
        database='db_presensi_restoran',
        ssl={'ssl': {}},  # TiDB Cloud memerlukan koneksi aman (SSL)
        cursorclass=pymysql.cursors.DictCursor
    )

# Model Data Input dari IoT Fingerprint / RFID
class PresensiInput(BaseModel):
    id_fingerprint: int
    mode: str  # MASUK / KELUAR / LEMBUR

@app.get("/")
def check_status():
    return {"status": "Online", "message": "Server Backend Restoran Berjalan Lancar di TiDB Cloud"}

# 1. Endpoint Menerima Data Scan Fingerprint dari IoT ESP32
@app.post("/api/presensi")
def receive_presensi(data: PresensiInput):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM karyawan WHERE id_fingerprint = %s", (data.id_fingerprint,))
            karyawan = cursor.fetchone()
            if not karyawan:
                raise HTTPException(status_code=404, detail="ID Fingerprint Tidak Terdaftar")
            
            waktu_sekarang = datetime.now()
            sql = "INSERT INTO log_presensi (id_fingerprint, mode, waktu_scan) VALUES (%s, %s, %s)"
            cursor.execute(sql, (data.id_fingerprint, data.mode, waktu_sekarang))
            connection.commit()
            
            return {
                "status": "Success", 
                "message": f"Presensi {data.mode} berhasil untuk {karyawan['nama']}",
                "nama": karyawan['nama']
            }
    finally:
        connection.close()

# 2. Endpoint Mengirim Data Presensi Real-Time ke Web Dashboard
@app.get("/api/presensi/realtime")
def get_realtime_presensi():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT p.id_presensi, k.nama, k.jabatan, p.mode, p.waktu_scan, p.status_anomali
                FROM log_presensi p
                JOIN karyawan k ON p.id_fingerprint = k.id_fingerprint
                ORDER BY p.waktu_scan DESC LIMIT 20
            """
            cursor.execute(sql)
            results = cursor.fetchall()
            return {"data": results}
    finally:
        connection.close()

# 3. Endpoint Mengambil Data Jadwal Shift
@app.get("/api/jadwal-shift")
def get_jadwal_shift():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT j.tanggal, k.nama, k.jabatan, j.jenis_shift
                FROM jadwal_shift j
                JOIN karyawan k ON j.id_karyawan = k.id_karyawan
                ORDER BY j.tanggal ASC
            """
            cursor.execute(sql)
            return {"jadwal": cursor.fetchall()}
    finally:
        connection.close()