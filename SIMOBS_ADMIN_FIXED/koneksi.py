import firebase_admin
from firebase_admin import credentials, firestore

# =========================
# KONEKSI 1 - DATABASE ADMIN (simobs-bengkel)
# Untuk: admins, sparepart, customer_service, detail_booking
# =========================
cred_admin = credentials.Certificate(
    "simobs-bengkel-firebase-adminsdk-fbsvc-80c682d149.json"
)
app_admin = firebase_admin.initialize_app(cred_admin, name="admin")
db = firestore.client(app=app_admin)


# =========================
# KONEKSI 2 - DATABASE PENGGUNA (simobs-9257c)
# Untuk: users, bookings
# File JSON ini dicopy dari folder project pengguna
# =========================
cred_user = credentials.Certificate(
    "simobs-9257c-firebase-adminsdk-fbsvc-0fd79ebc26.json"
)
app_user = firebase_admin.initialize_app(cred_user, name="user")
db_user = firestore.client(app=app_user)