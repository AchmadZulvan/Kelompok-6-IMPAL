import time
from flask import Flask, render_template, request, redirect, session
from koneksi import db, db_user  # db = admin, db_user = pengguna
from google.cloud.firestore_v1.base_query import FieldFilter

app = Flask(__name__)
app.secret_key = "simobs_admin"


# =========================
# HELPER: Sinkronisasi booking dari DB pengguna ke DB admin
# Dipanggil setiap kali halaman booking dibuka
# =========================

def sinkron_booking_pengguna():
    """
    Baca semua booking dari DB pengguna (bookings),
    lalu simpan ke DB admin (booking) jika belum ada.
    Gunakan field 'user_booking_id' sebagai penanda agar tidak duplikat.
    """
    try:
        docs_user = db_user.collection("bookings").stream()
        jumlah_baru = 0
        for doc in docs_user:
            item = doc.to_dict()
            user_booking_id = doc.id

            # Cek apakah sudah ada di DB admin berdasarkan user_booking_id
            existing = db.collection("booking") \
                         .where(filter=FieldFilter("user_booking_id", "==", user_booking_id)) \
                         .limit(1) \
                         .stream()

            if not list(existing):
                # Belum ada → simpan ke DB admin
                db.collection("booking").add({
                    "user_booking_id": user_booking_id,
                    "nama_pelanggan": (
                        item.get('nama_pelanggan') or
                        item.get('nama') or
                        item.get('nama_user') or
                        item.get('name') or ''
                    ),
                    "motor": item.get('motor', ''),
                    "keluhan": item.get('keluhan', ''),
                    "mekanik": item.get('mekanik', ''),
                    "status": item.get('status', 'Menunggu'),
                    "tanggal": item.get('tanggal', ''),
                    "waktu": item.get('waktu', ''),
                    "jenis_servis": item.get('jenis_servis', ''),
                    "plat": item.get('plat', ''),
                    "user_email": item.get('user_email', '') or item.get('email', ''),
                    "created_at": item.get('created_at', ''),
                    "source": "pengguna"
                })
                jumlah_baru += 1
                print(f"[SINKRON] Booking baru disimpan: {user_booking_id}")
        print(f"[SINKRON] Selesai. {jumlah_baru} booking baru ditambahkan.")
    except Exception as e:
        print(f"[SINKRON] Error: {e}")


# =========================
# HOME
# =========================

@app.route('/')
def home():
    return redirect('/login')


# =========================
# REGISTER
# =========================

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        nama = request.form['nama']
        username = request.form['username']
        password = request.form['password']

        cek = db.collection("admins").where(filter=FieldFilter("username", "==", username)).stream()
        if list(cek):
            error = "Username sudah digunakan"
            return render_template('register.html', error=error)

        db.collection("admins").add({
            "nama": nama,
            "username": username,
            "password": password
        })
        return redirect('/login')

    return render_template('register.html', error=error)


# =========================
# LOGIN
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        docs = db.collection("admins") \
                 .where(filter=FieldFilter("username", "==", username)) \
                 .where(filter=FieldFilter("password", "==", password)) \
                 .stream()
        admin = None
        for doc in docs:
            admin = doc.to_dict()
            break

        if admin:
            session['admin'] = admin['username']
            session['nama'] = admin['nama']
            session['username'] = admin['username']
            return redirect('/dashboard')

        error = "Username atau Password Salah"

    return render_template('login.html', error=error)


@app.route('/profil')
def profil():
    return redirect('/dashboard')


# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
def dashboard():
    start = time.time()

    if 'admin' not in session:
        return redirect('/login')

    total_sparepart = len(db.collection("sparepart").get())
    total_admin = len(db.collection("admins").get())


    total_pelanggan = len(db_user.collection("users").get())
    total_booking = len(db.collection("booking").get())  # ambil dari DB admin (sudah tersinkron)

    print(f"Dashboard load: {round(time.time() - start, 2)} detik")

    return render_template(
        'dashboard.html',
        admin=session.get('admin', ''),
        nama=session.get('nama', ''),
        username=session.get('username', ''),
        pelanggan=total_pelanggan,
        booking=total_booking,
        sparepart=total_sparepart,
        total_admin=total_admin,
    )


# =========================
# PELANGGAN
# =========================

@app.route('/pelanggan')
def pelanggan():
    if 'admin' not in session:
        return redirect('/login')

    kw = request.args.get('keyword', '')
    data = []

    docs_user = db_user.collection("users").stream()
    for doc in docs_user:
        item = doc.to_dict()
        nama = item.get("nama", "")
        alamat = item.get("email", "")
        telepon = item.get("no_hp", "")
        if kw:
            text = f"{nama} {alamat} {telepon}".lower()
            if kw.lower() not in text:
                continue
        data.append({"id": doc.id, "source": "user", "nama": nama, "alamat": alamat, "telepon": telepon})

    docs_admin = db.collection("pelanggan").stream()
    for doc in docs_admin:
        item = doc.to_dict()
        nama = item.get("nama", "")
        alamat = item.get("alamat", "")
        telepon = item.get("telepon", "")
        if kw:
            text = f"{nama} {alamat} {telepon}".lower()
            if kw.lower() not in text:
                continue
        data.append({"id": doc.id, "source": "admin", "nama": nama, "alamat": alamat, "telepon": telepon})

    return render_template('pelanggan.html', data=data, keyword=kw)


@app.route('/tambah_pelanggan', methods=['GET', 'POST'])
def tambah_pelanggan():
    if request.method == 'POST':
        db.collection("pelanggan").add({
            "nama": request.form['nama'],
            "alamat": request.form['alamat'],
            "telepon": request.form['telepon']
        })
        return redirect('/pelanggan')
    return render_template('tambah_pelanggan.html')


@app.route('/edit_pelanggan/<id>', methods=['GET', 'POST'])
def edit_pelanggan(id):
    doc_ref = db.collection("pelanggan").document(id)
    if request.method == 'POST':
        doc_ref.update({
            "nama": request.form['nama'],
            "alamat": request.form['alamat'],
            "telepon": request.form['telepon']
        })
        return redirect('/pelanggan')
    data = doc_ref.get().to_dict()
    data['id'] = id
    return render_template('edit_pelanggan.html', data=data)


@app.route('/hapus_pelanggan/<source>/<id>')
def hapus_pelanggan(source, id):
    if source == "admin":
        db.collection("pelanggan").document(id).delete()
    elif source == "user":
        db_user.collection("users").document(id).delete()
    return redirect('/pelanggan')


# =========================
# BOOKING
# Semua booking (dari pengguna maupun admin) disimpan di DB admin collection "booking"
# Saat halaman dibuka, data dari DB pengguna otomatis disinkronkan ke DB admin
# =========================

@app.route('/booking')
def booking():
    if 'admin' not in session:
        return redirect('/login')

    # Sinkronkan dulu booking dari pengguna ke DB admin
    sinkron_booking_pengguna()

    kw = request.args.get('keyword', '')
    data = []

    # Baca semua booking dari DB admin (sudah lengkap termasuk dari pengguna)
    docs = db.collection("booking").stream()
    for doc in docs:
        item = doc.to_dict()
        item['id'] = doc.id
        item['nama_pelanggan'] = item.get('nama_pelanggan') or item.get('nama') or ''
        item['mekanik'] = item.get('mekanik') or ''

        if kw:
            text = (
                f"{item.get('nama_pelanggan','')} "
                f"{item.get('motor','')} "
                f"{item.get('keluhan','')} "
                f"{item.get('mekanik','')} "
                f"{item.get('status','')}"
            ).lower()
            if kw.lower() not in text:
                continue
        data.append(item)

    return render_template('booking.html', data=data, keyword=kw)


@app.route('/tambah_booking', methods=['GET', 'POST'])
def tambah_booking():
    if request.method == 'POST':
        db.collection("booking").add({
            "nama_pelanggan": request.form['nama_pelanggan'],
            "motor": request.form['motor'],
            "keluhan": request.form['keluhan'],
            "sparepart_diganti": request.form.get('sparepart_diganti', ''),
            "total_sparepart": request.form.get('total_sparepart', 0),
            "mekanik": request.form.get('mekanik', ''),
            "status": request.form['status'],
            "source": "admin"
        })
        return redirect('/booking')
    return render_template('tambah_booking.html')


@app.route('/edit_booking/<id>', methods=['GET', 'POST'])
def edit_booking(id):
    doc_ref = db.collection("booking").document(id)
    data = doc_ref.get().to_dict()

    if not data:
        return redirect('/booking')

    if request.method == 'POST':
        doc_ref.update({
            "nama_pelanggan": request.form['nama_pelanggan'],
            "motor": request.form['motor'],
            "keluhan": request.form['keluhan'],
            "mekanik": request.form.get('mekanik', ''),
            "status": request.form['status']
        })
        return redirect('/booking')

    data['id'] = id
    data['nama_pelanggan'] = data.get('nama_pelanggan') or data.get('nama') or ''
    data['mekanik'] = data.get('mekanik') or ''

    return render_template('edit_booking.html', data=data)


@app.route('/hapus_booking/<id>')
def hapus_booking(id):
    # Hapus dari DB admin
    doc = db.collection("booking").document(id).get()
    if doc.exists:
        data = doc.to_dict()
        # Kalau ini data dari pengguna, hapus juga dari DB pengguna
        user_booking_id = data.get('user_booking_id')
        if user_booking_id:
            try:
                db_user.collection("bookings").document(user_booking_id).delete()
            except Exception:
                pass
        db.collection("booking").document(id).delete()
    return redirect('/booking')


# =========================
# SPAREPART
# =========================

@app.route('/sparepart')
def sparepart():
    if 'admin' not in session:
        return redirect('/login')

    kw = request.args.get('keyword', '')
    kategori = request.args.get('kategori', '')
    docs = db.collection("sparepart").stream()
    data = []

    for doc in docs:
        item = doc.to_dict()
        nama = item.get("nama_sparepart", "").lower()

        if "oli" in nama or "yamalube" in nama or "mpx" in nama:
            jenis = "Oli"
        elif "busi" in nama:
            jenis = "Busi"
        elif "kampas rem" in nama:
            jenis = "Kampas Rem"
        elif "kampas" in nama:
            jenis = "Kampas Kopling"
        elif "filter" in nama:
            jenis = "Filter"
        elif "aki" in nama:
            jenis = "Aki"
        elif "ban" in nama:
            jenis = "Ban"
        else:
            jenis = "Lainnya"

        if kw and kw.lower() not in nama:
            continue
        if kategori and kategori != jenis:
            continue

        data.append({
            "id": doc.id,
            "nama_sparepart": item.get("nama_sparepart", ""),
            "kategori": jenis,
            "stok": item.get("stok", 0),
            "harga": item.get("harga", 0)
        })

    return render_template('sparepart.html', data=data, keyword=kw, kategori=kategori)


@app.route('/tambah_sparepart', methods=['GET', 'POST'])
def tambah_sparepart():
    if request.method == 'POST':
        db.collection("sparepart").add({
            "nama_sparepart": request.form['nama_sparepart'],
            "stok": request.form['stok'],
            "harga": request.form['harga']
        })
        return redirect('/sparepart')
    return render_template('tambah_sparepart.html')


@app.route('/edit_sparepart/<id>', methods=['GET', 'POST'])
def edit_sparepart(id):
    doc_ref = db.collection("sparepart").document(id)
    if request.method == 'POST':
        doc_ref.update({
            "nama_sparepart": request.form['nama_sparepart'],
            "stok": request.form['stok'],
            "harga": request.form['harga']
        })
        return redirect('/sparepart')
    data = doc_ref.get().to_dict()
    data['id'] = id
    return render_template('edit_sparepart.html', data=data)


@app.route('/hapus_sparepart/<id>')
def hapus_sparepart(id):
    db.collection("sparepart").document(id).delete()
    return redirect('/sparepart')




# =========================
# TEST KONEKSI
# =========================

@app.route('/test-koneksi')
def test_koneksi():
    try:
        users = db_user.collection("users").limit(1).get()
        bookings = db_user.collection("bookings").limit(1).get()
        return f"Koneksi db_user BERHASIL<br>Users: {len(users)}<br>Bookings: {len(bookings)}"
    except Exception as e:
        return f"Koneksi GAGAL: {str(e)}"


@app.route('/test-admin')
def test_admin():
    try:
        admins = db.collection("admins").limit(1).get()
        sp = db.collection("sparepart").limit(1).get()
        return f"Koneksi DB ADMIN BERHASIL<br>Admin: {len(admins)}<br>Sparepart: {len(sp)}"
    except Exception as e:
        return f"Koneksi DB ADMIN GAGAL: {str(e)}"


# =========================
# DEBUG SINKRON (opsional, bisa dihapus setelah testing)
# =========================

@app.route('/debug-sinkron')
def debug_sinkron():
    if 'admin' not in session:
        return redirect('/login')
    try:
        sinkron_booking_pengguna()
        docs = db.collection("booking").where(filter=FieldFilter("source", "==", "pengguna")).stream()
        hasil = [doc.to_dict() for doc in docs]
        return f"<b>Booking dari pengguna di DB admin: {len(hasil)}</b><br><br>" + \
               "<br><hr>".join([str(h) for h in hasil]) or "<b>Tidak ada data booking dari pengguna!</b>"
    except Exception as e:
        return f"<b>ERROR:</b> {str(e)}"


# =========================
# DEBUG SPAREPART
# =========================

@app.route('/debug-sparepart')
def debug_sparepart():
    if 'admin' not in session:
        return redirect('/login')
    try:
        docs = db.collection("sparepart").stream()
        hasil = ""
        for doc in docs:
            hasil += f"<b>ID:</b> {doc.id}<br><b>Fields:</b> {doc.to_dict()}<br><hr>"
        return hasil or "<b>Tidak ada data di collection sparepart!</b>"
    except Exception as e:
        return f"<b>ERROR:</b> {str(e)}"


# =========================
# LOGOUT & RUN
# =========================

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


print(app.url_map)
if __name__ == '__main__':
    app.run(debug=False)