from flask import Flask, render_template, request, redirect, url_for, session, flash
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import smtplib
import random
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "simobs_secret_key"

# =========================
# FIREBASE PENGGUNA
# =========================
cred_user = credentials.Certificate(
    "simobs-9257c-firebase-adminsdk-fbsvc-0fd79ebc26.json"
)

user_app = firebase_admin.initialize_app(
    cred_user,
    name="user"
)

db = firestore.client(user_app)

# =========================
# FIREBASE ADMIN
# =========================
cred_admin = credentials.Certificate(
    "simobs-bengkel-firebase-adminsdk-fbsvc-80c682d149.json"
)

admin_app = firebase_admin.initialize_app(
    cred_admin,
    name="admin"
)

db_admin = firestore.client(admin_app)

# =========================
# EMAIL CONFIG (WAJIB DIISI)
# =========================

EMAIL_ADDRESS = "exynoz26@gmail.com" 
EMAIL_PASSWORD = "isvlfkwlfaqhzwlr" 

# =========================
# OTP FUNCTION
# =========================

def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp(email, otp):
    try:
        msg = MIMEText(f"Kode OTP Anda untuk Login SIMOBS adalah: {otp}")
        msg["Subject"] = "SIMOBS - Kode OTP Login"
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        print("Error pengiriman email:", e)
        return False

# =========================
# HOME
# =========================

@app.route("/")
def home():
    return redirect("/login")

# =========================
# REGISTER (Langsung Simpan)
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        nama = request.form["nama"]
        email = request.form["email"]
        password = request.form["password"]
        konfirmasi = request.form["konfirmasi"]
        no_hp = request.form.get("no_hp", "") 

        if password != konfirmasi:
            flash("Password dan konfirmasi password tidak sama")
            return redirect("/register")

        # Cek apakah email sudah terdaftar
        existing = db.collection("users").where(
            "email", "==", email
        ).get()

        if len(existing) > 0:
            flash("Email sudah digunakan")
            return redirect("/register")

        # Langsung simpan ke Firebase tanpa OTP
        user_data = {
            "nama": nama,
            "email": email,
            "no_hp": no_hp,
            "password": password,
            "created_at": datetime.now()
}

            # Simpan ke database pengguna
        db.collection("users").add(user_data)

        # Simpan ke database admin -> pelanggan
        db_admin.collection("pelanggan").add({
            "nama": nama,
            "alamat": email,
            "telepon": no_hp
        })

        flash("Registrasi berhasil, silakan login.")
        return redirect("/login")

    return render_template("register.html")

# =========================
# LOGIN (Membutuhkan OTP)
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        user_input = request.form["user"]
        password = request.form["password"]

        # Cari berdasarkan email terlebih dahulu
        users = db.collection("users").where(
            "email", "==", user_input
        ).get()

        # Jika tidak ditemukan, cari berdasarkan nomor HP
        if len(users) == 0:
            users = db.collection("users").where(
                "no_hp", "==", user_input
            ).get()

        if len(users) == 0:
            flash("Email atau No HP tidak ditemukan")
            return redirect("/login")

        user = users[0].to_dict()

        if user["password"] != password:
            flash("Password salah")
            return redirect("/login")

        # Mulai proses pengiriman OTP
        email_tujuan = user.get("email")
        if not email_tujuan:
            flash("Akun ini tidak memiliki email yang valid untuk pengiriman OTP.")
            return redirect("/login")

        otp_code = generate_otp()
        sukses_kirim = send_otp(email_tujuan, otp_code)

        if sukses_kirim:
            # Simpan data login sementara
            session["pending_email"] = email_tujuan
            session["pending_nama"] = user["nama"]
            session["login_otp"] = otp_code
            
            flash("OTP telah dikirim ke email Anda.")
            return redirect("/verify-login-otp")
        else:
            flash("Gagal mengirim OTP. Pastikan konfigurasi email server sudah benar.")
            return redirect("/login")

    return render_template("login.html")

# =========================
# VERIFY LOGIN OTP
# =========================

@app.route("/verify-login-otp", methods=["GET", "POST"])
def verify_login_otp():

    # Cegah akses langsung jika tidak ada proses login yang sedang berjalan
    if "login_otp" not in session:
        return redirect("/login")

    if request.method == "POST":

        user_otp = request.form["otp"]

        if user_otp == session.get("login_otp"):
            
            # OTP Benar -> Buat session utama
            session["user_email"] = session.get("pending_email")
            session["user_name"] = session.get("pending_nama")

            # Bersihkan session sementara
            session.pop("login_otp", None)
            session.pop("pending_email", None)
            session.pop("pending_nama", None)

            return redirect("/dashboard")

        flash("OTP salah, silakan coba lagi.")

    # Pastikan kamu memiliki file otp.html di folder templates
    return render_template("otp.html")

# =========================
# DASHBOARD
# =========================

@app.route("/dashboard")
def dashboard():

    if "user_email" not in session:
        return redirect("/login")

    return render_template(
        "dashboard.html",
        nama=session["user_name"]
    )

# =========================
# PROFILE
# =========================

@app.route("/profile")
def profile():

    if "user_email" not in session:
        return redirect("/login")

    users = db.collection("users").where(
        "email", "==", session["user_email"]
    ).get()

    # Mencegah error jika data user tidak ditemukan
    if len(users) == 0:
        flash("Sesi atau profil tidak ditemukan, silakan login kembali.")
        return redirect("/logout")

    user = users[0].to_dict()

    return render_template(
        "profile.html",
        user=user
    )

# =========================
# BOOKING
# =========================

@app.route("/booking", methods=["GET", "POST"])
def booking():

    if "user_email" not in session:
        return redirect("/login")

    return render_template("booking.html")

# =========================
# DO BOOKING
# =========================

@app.route("/do_booking", methods=["POST"])
def do_booking():

    if "user_email" not in session:
        return redirect("/login")

    booking_data = {
        "user_email": session["user_email"],
        "nama": session["user_name"],
        "motor": request.form["motor"],
        "plat": request.form.get("plat", ""),
        "jenis_servis": request.form.get("jenis_servis", ""),
        "tanggal": request.form.get("tanggal", ""),
        "waktu": request.form.get("waktu", ""),
        "keluhan": request.form.get("keluhan", ""),
        "status": "Menunggu",
        "created_at": datetime.now()
    }

    db.collection("bookings").add(booking_data)

    flash("Booking berhasil")
    return redirect("/riwayat")

# =========================
# RIWAYAT
# =========================

@app.route("/riwayat")
def riwayat():

    if "user_email" not in session:
        return redirect("/login")

    bookings = db.collection("bookings").where(
        "user_email",
        "==",
        session["user_email"]
    ).get()

    data = []

    for booking in bookings:
        temp = booking.to_dict()
        temp["id"] = booking.id
        data.append(temp)

    return render_template(
        "riwayat.html",
        bookings=data
    )

# =========================
# STATUS
# =========================

@app.route("/status")
def status_booking():

    if "user_email" not in session:
        return redirect("/login")

    bookings = db.collection("bookings").where(
        "user_email",
        "==",
        session["user_email"]
    ).get()

    data = []

    for booking in bookings:
        temp = booking.to_dict()
        temp["id"] = booking.id
        data.append(temp)

    return render_template(
        "status.html",
        bookings=data
    )

# =========================
# DETAIL SERVIS
# =========================

@app.route("/detail/<booking_id>")
def detail_servis(booking_id):
    
    # 1. Pastikan user sudah login
    if "user_email" not in session:
        return redirect("/login")

    # 2. Cari dokumen di koleksi "bookings" berdasarkan ID dari URL
    doc_ref = db.collection("bookings").document(booking_id)
    doc = doc_ref.get()

    if doc.exists:
        booking_data = doc.to_dict()
        booking_data["id"] = doc.id # Masukkan ID agar bisa dibaca di HTML
        
        # 3. Keamanan Tambahan: Pastikan data ini milik user yang sedang login
        if booking_data.get("user_email") != session["user_email"]:
            flash("Anda tidak memiliki akses ke halaman ini.")
            return redirect("/status")
            
        # 4. Lempar datanya ke detail.html
        return render_template("detail.html", booking=booking_data)
        
    else:
        # Jika ID tidak ditemukan di database
        flash("Data servis tidak ditemukan.")
        return redirect("/status")

# =========================
# SPAREPART & LAINNYA
# =========================

@app.route("/sparepart")
def sparepart():

    spareparts = db.collection(
        "spareparts"
    ).stream()

    data = []

    for item in spareparts:
        temp = item.to_dict()
        temp["id"] = item.id
        data.append(temp)

    return render_template(
        "sparepart.html",
        spareparts=data
    )

@app.route("/oli")
def oli(): return render_template("oli.html")

@app.route("/busi")
def busi(): return render_template("busi.html")

@app.route("/aki")
def aki(): return render_template("Aki.html")

@app.route("/vbelt")
def vbelt(): return render_template("vbelt.html")

@app.route("/rantai")
def rantai(): return render_template("rantai.html")

@app.route("/filter_udara")
def filter_udara(): return render_template("filter_udara.html")

@app.route("/kampas_rem")
def kampas_rem(): return render_template("kampas_rem.html")

@app.route("/notifikasi")
def notifikasi(): return render_template("notifikasi.html")

@app.route("/setting")
def setting(): return render_template("setting.html")

# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()
    return redirect("/login")

# =========================
# MAIN
# =========================

if __name__ == "__main__":
    app.run(debug=True)