from datetime import datetime
import os

from flask import Flask, render_template, request, redirect, session, jsonify

from firebase_admin import firestore

from koneksi import db

app = Flask(__name__)
app.secret_key = "simobs_admin"


def _firestore_project_id() -> str | None:
    return getattr(db, "project", None)


@app.route('/__debug/firebase')
def debug_firebase():
    """Debug endpoint (local use) to verify Firestore connectivity.

    Returns the Firestore project id used by the running server and writes
    one heartbeat document into collection '__debug'.
    """

    # Write a heartbeat doc so you can confirm it appears in the console.
    _, doc_ref = db.collection('__debug').add({
        'source': 'flask-app',
        'ts': _now_string(),
        'created_at': firestore.SERVER_TIMESTAMP,
    })

    service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH', '')
    return jsonify({
        'firestore_project': _firestore_project_id(),
        'service_account_file': os.path.basename(service_account_path) if service_account_path else None,
        'wrote_collection': '__debug',
        'wrote_doc_id': doc_ref.id,
    })


def _doc_to_tuple(doc, field_order):
    data = doc.to_dict() or {}
    return (doc.id, *[data.get(f) for f in field_order])


def _contains_keyword(value, keyword: str) -> bool:
    if value is None:
        return False
    return keyword.lower() in str(value).lower()


def _now_string() -> str:
    # Simple local timestamp string for UI (kept compatible with existing templates)
    return datetime.now().strftime("%Y-%m-%d %H:%M")


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

    if request.method == 'POST':

        nama = request.form['nama']
        username = request.form['username']
        password = request.form['password']

        _, doc_ref = db.collection('admin').add({
            'nama': nama,
            'username': username,
            'password': password,
            'created_at': firestore.SERVER_TIMESTAMP,
        })
        app.logger.info(
            "Firestore add admin id=%s project=%s",
            doc_ref.id,
            _firestore_project_id(),
        )

        return redirect('/login')

    return render_template('register.html')


# =========================
# LOGIN
# =========================

@app.route('/login', methods=['GET', 'POST'])
def login():

    error = None

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        query = (
            db.collection('admin')
            .where('username', '==', username)
            .where('password', '==', password)
            .limit(1)
        )
        docs = list(query.stream())
        admin = _doc_to_tuple(docs[0], ['nama', 'username', 'password']) if docs else None

        if admin:

            session['admin'] = admin[2]
            session['nama'] = admin[1]
            session['username'] = admin[2]

            return redirect('/dashboard')

        error = "Username atau Password Salah"

    return render_template(
        'login.html',
        error=error
    )
# profile
@app.route('/profil')
def profil():
    return redirect('/dashboard')
# =========================
# DASHBOARD
# =========================

@app.route('/dashboard')
def dashboard():

    if 'admin' not in session:
        return redirect('/login')

    # Firestore doesn't provide COUNT(*) via simple API in all SDK versions;
    # for this app size, streaming and len() is acceptable.
    try:
        total_pelanggan = len(list(db.collection('pelanggan').stream()))
    except Exception:
        total_pelanggan = 0

    try:
        total_booking = len(list(db.collection('booking').stream()))
    except Exception:
        total_booking = 0

    try:
        total_sparepart = len(list(db.collection('sparepart').stream()))
    except Exception:
        total_sparepart = 0

    try:
        total_admin = len(list(db.collection('admin').stream()))
    except Exception:
        total_admin = 0

    try:
        total_cs = len(list(db.collection('customer_service').stream()))
    except Exception:
        total_cs = 0

    return render_template(
     'dashboard.html',
    admin=session.get('admin', ''),
    nama=session.get('nama', ''),
    username=session.get('username', ''),
    pelanggan=total_pelanggan,
    booking=total_booking,
    sparepart=total_sparepart,
    total_admin=total_admin,
    total_cs=total_cs
)


# =========================
# PELANGGAN
# =========================

@app.route('/pelanggan')
def pelanggan():

    if 'admin' not in session:
        return redirect('/login')

    keyword = request.args.get('keyword', '')

    docs = list(db.collection('pelanggan').stream())
    rows = [_doc_to_tuple(d, ['nama', 'alamat', 'telepon']) for d in docs]

    if keyword:
        rows = [
            r for r in rows
            if _contains_keyword(r[1], keyword)
            or _contains_keyword(r[2], keyword)
            or _contains_keyword(r[3], keyword)
        ]

    data = rows

    return render_template(
        'pelanggan.html',
        data=data,
        keyword=keyword
    )


@app.route('/tambah_pelanggan', methods=['GET', 'POST'])
def tambah_pelanggan():

    if request.method == 'POST':
        _, doc_ref = db.collection('pelanggan').add({
            'nama': request.form['nama'],
            'alamat': request.form['alamat'],
            'telepon': request.form['telepon'],
            'created_at': firestore.SERVER_TIMESTAMP,
        })
        app.logger.info(
            "Firestore add pelanggan id=%s project=%s",
            doc_ref.id,
            _firestore_project_id(),
        )

        return redirect('/pelanggan')

    return render_template(
        'tambah_pelanggan.html'
    )


@app.route('/edit_pelanggan/<id>', methods=['GET', 'POST'])
def edit_pelanggan(id):

    if request.method == 'POST':
        db.collection('pelanggan').document(id).set({
            'nama': request.form['nama'],
            'alamat': request.form['alamat'],
            'telepon': request.form['telepon'],
            'updated_at': firestore.SERVER_TIMESTAMP,
        }, merge=True)

        return redirect('/pelanggan')

    doc = db.collection('pelanggan').document(id).get()
    if not doc.exists:
        return redirect('/pelanggan')
    data = _doc_to_tuple(doc, ['nama', 'alamat', 'telepon'])

    return render_template(
        'edit_pelanggan.html',
        data=data
    )


@app.route('/hapus_pelanggan/<id>')
def hapus_pelanggan(id):

    db.collection('pelanggan').document(id).delete()

    return redirect('/pelanggan')


# =========================
# BOOKING
# =========================

@app.route('/booking')
def booking():

    if 'admin' not in session:
        return redirect('/login')

    keyword = request.args.get('keyword', '')

    docs = list(db.collection('booking').stream())
    rows = [_doc_to_tuple(d, ['nama_pelanggan', 'motor', 'keluhan', 'mekanik', 'status']) for d in docs]

    if keyword:
        rows = [
            r for r in rows
            if _contains_keyword(r[1], keyword)
            or _contains_keyword(r[2], keyword)
            or _contains_keyword(r[3], keyword)
            or _contains_keyword(r[4], keyword)
            or _contains_keyword(r[5], keyword)
        ]

    data = rows

    return render_template(
        'booking.html',
        data=data,
        keyword=keyword
    )


@app.route('/tambah_booking', methods=['GET', 'POST'])
def tambah_booking():

    if request.method == 'POST':
        _, doc_ref = db.collection('booking').add({
            'nama_pelanggan': request.form['nama_pelanggan'],
            'motor': request.form['motor'],
            'keluhan': request.form['keluhan'],
            'mekanik': request.form['mekanik'],
            'status': request.form['status'],
            'created_at': firestore.SERVER_TIMESTAMP,
        })
        app.logger.info(
            "Firestore add booking id=%s project=%s",
            doc_ref.id,
            _firestore_project_id(),
        )

        return redirect('/booking')

    return render_template(
        'tambah_booking.html'
    )


@app.route('/edit_booking/<id>',
methods=['GET', 'POST'])
def edit_booking(id):

    if request.method == 'POST':
        db.collection('booking').document(id).set({
            'nama_pelanggan': request.form['nama_pelanggan'],
            'motor': request.form['motor'],
            'keluhan': request.form['keluhan'],
            'mekanik': request.form['mekanik'],
            'status': request.form['status'],
            'updated_at': firestore.SERVER_TIMESTAMP,
        }, merge=True)

        return redirect('/booking')

    doc = db.collection('booking').document(id).get()
    if not doc.exists:
        return redirect('/booking')
    data = _doc_to_tuple(doc, ['nama_pelanggan', 'motor', 'keluhan', 'mekanik', 'status'])

    return render_template(
        'edit_booking.html',
        data=data
    )

@app.route('/hapus_booking/<id>')
def hapus_booking(id):

    db.collection('booking').document(id).delete()

    return redirect('/booking')

# =========================
# SPAREPART
# =========================

@app.route('/sparepart')
def sparepart():

    if 'admin' not in session:
        return redirect('/login')

    keyword = request.args.get('keyword', '')
    kategori = request.args.get('kategori', '')

    docs = list(db.collection('sparepart').stream())
    # rows = (id, nama_sparepart, stok, harga)
    result = [_doc_to_tuple(d, ['nama_sparepart', 'stok', 'harga']) for d in docs]

    data = []

    for item in result:

        nama = (item[1] or "").lower()

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

        if keyword:
            if keyword.lower() not in nama:
                continue

        if kategori:
            if kategori != jenis:
                continue

        data.append((
            item[0],      # id (Firestore document id)
            item[1],      # nama sparepart
            jenis,        # kategori
            item[2],      # stok
            item[3]       # harga
        ))

    return render_template(
        'sparepart.html',
        data=data,
        keyword=keyword,
        kategori=kategori
    )


@app.route('/tambah_sparepart', methods=['GET', 'POST'])
def tambah_sparepart():

    if request.method == 'POST':
        _, doc_ref = db.collection('sparepart').add({
            'nama_sparepart': request.form['nama_sparepart'],
            'stok': int(request.form['stok']) if str(request.form.get('stok', '')).strip() != '' else 0,
            'harga': float(str(request.form.get('harga', '0')).replace('.', '').replace(',', '.'))
            if request.form.get('harga') else 0,
            'created_at': firestore.SERVER_TIMESTAMP,
        })
        app.logger.info(
            "Firestore add sparepart id=%s project=%s",
            doc_ref.id,
            _firestore_project_id(),
        )

        return redirect('/sparepart')

    return render_template(
        'tambah_sparepart.html'
    )


@app.route('/edit_sparepart/<id>', methods=['GET', 'POST'])
def edit_sparepart(id):

    if request.method == 'POST':
        db.collection('sparepart').document(id).set({
            'nama_sparepart': request.form['nama_sparepart'],
            'stok': int(request.form['stok']) if str(request.form.get('stok', '')).strip() != '' else 0,
            'harga': float(str(request.form.get('harga', '0')).replace('.', '').replace(',', '.'))
            if request.form.get('harga') else 0,
            'updated_at': firestore.SERVER_TIMESTAMP,
        }, merge=True)

        return redirect('/sparepart')

    doc = db.collection('sparepart').document(id).get()
    if not doc.exists:
        return redirect('/sparepart')
    data = _doc_to_tuple(doc, ['nama_sparepart', 'stok', 'harga'])

    return render_template(
        'edit_sparepart.html',
        data=data
    )


@app.route('/hapus_sparepart/<id>')
def hapus_sparepart(id):

    db.collection('sparepart').document(id).delete()

    return redirect('/sparepart')


# =========================
# LOGOUT
# =========================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/login')

@app.route('/admin')
def admin():

    if 'admin' not in session:
        return redirect('/login')

    docs = list(db.collection('admin').stream())
    data = [_doc_to_tuple(d, ['nama', 'username', 'password']) for d in docs]

    return render_template(
        'admin.html',
        data=data
    )

@app.route('/detail_booking/<id>')
def detail_booking(id):

    # Detail booking stored as sub-collection: booking/{bookingId}/detail_booking
    docs = list(
        db.collection('booking')
        .document(id)
        .collection('detail_booking')
        .stream()
    )

    # Template expects: s[2]=sparepart, s[3]=qty, s[4]=harga, s[5]=subtotal
    sparepart = []
    for d in docs:
        data = d.to_dict() or {}
        sparepart.append((
            d.id,                  # [0]
            id,                    # [1] booking_id
            data.get('sparepart'), # [2]
            data.get('qty'),       # [3]
            data.get('harga'),     # [4]
            data.get('subtotal')   # [5]
        ))

    total = sum(float(x[5] or 0) for x in sparepart)

    return render_template(
        'detail_booking.html',
        sparepart=sparepart,
        total=total
    )

# =========================
# CUSTOMER SERVICE
# =========================

@app.route('/customer_service')
def customer_service():

    if 'admin' not in session:
        return redirect('/login')

    try:
        docs = list(
            db.collection('customer_service')
            .order_by('created_at', direction=firestore.Query.DESCENDING)
            .stream()
        )
    except Exception:
        # Fallback (no index / created_at missing)
        docs = list(db.collection('customer_service').stream())

    data = []
    for d in docs:
        row = _doc_to_tuple(d, ['nama_pelanggan', 'telepon', 'keluhan', 'status', 'tanggal'])
        # Ensure tanggal exists for older docs
        if not row[5]:
            data.append((row[0], row[1], row[2], row[3], row[4], _now_string()))
        else:
            data.append(row)

    return render_template(
        'customer_service.html',
        data=data
    )


@app.route('/tambah_customer_service',
methods=['GET', 'POST'])
def tambah_customer_service():

    if request.method == 'POST':
        _, doc_ref = db.collection('customer_service').add({
            'nama_pelanggan': request.form['nama_pelanggan'],
            'telepon': request.form['telepon'],
            'keluhan': request.form['keluhan'],
            'status': request.form['status'],
            'tanggal': _now_string(),
            'created_at': firestore.SERVER_TIMESTAMP,
        })
        app.logger.info(
            "Firestore add customer_service id=%s project=%s",
            doc_ref.id,
            _firestore_project_id(),
        )

        return redirect('/customer_service')

    return render_template(
        'tambah_customer_service.html'
    )


@app.route('/hapus_customer_service/<id>')
def hapus_customer_service(id):

    db.collection('customer_service').document(id).delete()

    return redirect('/customer_service')


# =========================
# RUN
# =========================

if __name__ == '__main__':
    # Note: use_reloader=False to avoid the parent process exiting after spawning
    # the reloader child process (which can look like an error in some terminals).
    app.run(debug=True, use_reloader=False)