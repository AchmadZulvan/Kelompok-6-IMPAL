from koneksi import db

db.collection("test").add({
    "status": "berhasil"
})

print("Firebase Connected!")