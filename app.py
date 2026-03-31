from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime, timedelta
import random
import string
import qrcode
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_db():
    conn = sqlite3.connect("parkir.db")
    conn.row_factory = sqlite3.Row
    return conn

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == "userparkir" and password == "mantap":
            session["user"] = username
            return redirect("/dashboard")

    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT id, plat, jenis, waktu_masuk, kode_bayar
        FROM parkir
        WHERE waktu_keluar IS NULL
        ORDER BY waktu_masuk DESC
    """)
    aktif = c.fetchall()
    conn.close()

    return render_template("dashboard.html", data=aktif)

# ================= HISTORY =================
@app.route("/history")
def history():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT plat, jenis, waktu_masuk, waktu_keluar
        FROM parkir
        WHERE waktu_keluar IS NOT NULL
        ORDER BY waktu_keluar DESC
    """)
    history_data = c.fetchall()
    conn.close()

    # Hitung total bayar per row
    history = []
    for h in history_data:
        masuk = datetime.strptime(h["waktu_masuk"], "%Y-%m-%d %H:%M:%S")
        keluar = datetime.strptime(h["waktu_keluar"], "%Y-%m-%d %H:%M:%S")
        total_menit = max(1, int((keluar - masuk).total_seconds() / 60))
        tarif_per_menit = 2000/60 if h["jenis"].lower() == "motor" else 5000/60
        total_bayar = int(total_menit * tarif_per_menit)
        history.append({
            "plat": h["plat"],
            "jenis": h["jenis"],
            "masuk": h["waktu_masuk"],
            "keluar": h["waktu_keluar"],
            "total_bayar": total_bayar
        })

    return render_template("history.html", history=history)

# ================= PENDAPATAN =================
@app.route("/pendapatan")
def pendapatan():
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT jenis, waktu_masuk, waktu_keluar
        FROM parkir
        WHERE waktu_keluar IS NOT NULL
    """)
    data_bayar = c.fetchall()
    conn.close()

    # Inisialisasi counters
    hari_ini = datetime.now().date()
    kemarin = hari_ini - timedelta(days=1)
    bulan_ini = hari_ini.replace(day=1)

    hari_ini_pendapatan = hari_ini_kendaraan = 0
    kemarin_pendapatan = kemarin_kendaraan = 0
    bulan_ini_pendapatan = bulan_ini_kendaraan = 0

    for row in data_bayar:
        masuk = datetime.strptime(row["waktu_masuk"], "%Y-%m-%d %H:%M:%S")
        keluar = datetime.strptime(row["waktu_keluar"], "%Y-%m-%d %H:%M:%S")
        total_menit = max(1, int((keluar - masuk).total_seconds() / 60))
        tarif_per_menit = 2000/60 if row["jenis"].lower() == "motor" else 5000/60
        total_bayar = int(total_menit * tarif_per_menit)

        # Hari ini
        if keluar.date() == hari_ini:
            hari_ini_pendapatan += total_bayar
            hari_ini_kendaraan += 1
        # Kemarin
        elif keluar.date() == kemarin:
            kemarin_pendapatan += total_bayar
            kemarin_kendaraan += 1
        # Bulan ini
        if keluar.date() >= bulan_ini:
            bulan_ini_pendapatan += total_bayar
            bulan_ini_kendaraan += 1

    return render_template(
        "pendapatan.html",
        hari_ini_pendapatan=hari_ini_pendapatan,
        hari_ini_kendaraan=hari_ini_kendaraan,
        kemarin_pendapatan=kemarin_pendapatan,
        kemarin_kendaraan=kemarin_kendaraan,
        bulan_ini_pendapatan=bulan_ini_pendapatan,
        bulan_ini_kendaraan=bulan_ini_kendaraan
    )
# ================= PARKIR MASUK =================
@app.route("/parkir_masuk", methods=["GET", "POST"])
def parkir_masuk():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        plat = request.form.get("plat", "").strip()
        jenis = request.form.get("jenis", "").strip().lower()

        if not plat or not jenis:
            return "Data tidak lengkap!"

        waktu_masuk = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        kode_bayar = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        conn = get_db()
        c = conn.cursor()

        c.execute("""
            INSERT INTO parkir (plat, jenis, waktu_masuk, kode_bayar)
            VALUES (?, ?, ?, ?)
        """, (plat, jenis, waktu_masuk, kode_bayar))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("parkir_masuk.html")

# ================= PARKIR KELUAR =================
@app.route("/parkir_keluar/<int:id>", methods=["GET", "POST"])
def parkir_keluar(id):
    if "user" not in session:
        return redirect("/")

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM parkir WHERE id = ?", (id,))
    data = c.fetchone()

    if not data:
        conn.close()
        return redirect("/dashboard")

    waktu_masuk = datetime.strptime(data["waktu_masuk"], "%Y-%m-%d %H:%M:%S")
    waktu_sekarang = datetime.now()
    total_menit = max(1, int((waktu_sekarang - waktu_masuk).total_seconds() / 60))

    jam = total_menit // 60
    menit = total_menit % 60
    durasi_text = f"{jam} jam {menit} menit" if jam > 0 else f"{menit} menit"

    # ===== TARIF LANGSUNG DI SINI (ANTI ERROR) =====
    TARIF_PER_MENIT = {
        "motor": 1000,
        "mobil": 2000,
        "truk": 3000,
        "bus": 1000000
    }

    tarif = TARIF_PER_MENIT.get(data["jenis"].lower(), 0)
    estimasi_biaya = int(total_menit * tarif)

    error = None

    if request.method == "POST":
        kode_input = request.form.get("kode", "").strip()

        if not kode_input:
            error = "Kode pembayaran harus diisi!"
        elif kode_input != str(data["kode_bayar"]):
            error = "Kode pembayaran salah!"
        else:
            no_transaksi = "TRX" + ''.join(random.choices(string.digits, k=6))

            c.execute(
                "UPDATE parkir SET waktu_keluar = ? WHERE id = ?",
                (waktu_sekarang.strftime("%Y-%m-%d %H:%M:%S"), id)
            )
            conn.commit()

            qr_data = f"""No: {no_transaksi}
Plat: {data['plat']}
Jenis: {data['jenis']}
Durasi: {durasi_text}
Total: Rp {estimasi_biaya}
"""

            img = qrcode.make(qr_data)
            os.makedirs("static/qrcode", exist_ok=True)
            qr_path = f"static/qrcode/{no_transaksi}.png"
            img.save(qr_path)

            conn.close()

            return render_template(
                "struk.html",
                plat=data["plat"],
                jenis=data["jenis"],
                durasi=durasi_text,
                biaya=estimasi_biaya,
                no_transaksi=no_transaksi,
                qr_image=qr_path
            )

    conn.close()

    return render_template(
        "konfirmasi_kode.html",
        plat=data["plat"],
        jenis=data["jenis"],
        durasi=durasi_text,
        biaya=estimasi_biaya,
        error=error
    )
# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)