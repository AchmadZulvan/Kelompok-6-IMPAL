import firebase_admin
from firebase_admin import credentials, firestore

# Firebase pengguna
cred_user = credentials.Certificate(
    "simobs-9257c-firebase-adminsdk-fbsvc-0fd79ebc26.json"
)
firebase_admin.initialize_app(cred_user)

db = firestore.client()

# Firebase admin
cred_admin = credentials.Certificate(
    "simobs-bengkel-firebase-adminsdk-fbsvc-80c682d149.json"
)

admin_app = firebase_admin.initialize_app(
    cred_admin,
    name="admin"
)

db_admin = firestore.client(admin_app)