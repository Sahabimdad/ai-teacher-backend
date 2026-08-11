import os
import json
from firebase_admin import credentials, initialize_app, get_app
from firebase_admin import firestore

# Check karein ke Render ya environment variable mojood hai ya nahi
firebase_config_str = os.environ.get('FIREBASE_CONFIG_JSON')

if firebase_config_str:
    # Agar cloud par hain toh variable se JSON load karein
    cred_dict = json.loads(firebase_config_str)
    cred = credentials.Certificate(cred_dict)
else:
    # PythonAnywhere ke liye absolute path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(base_dir, "serviceAccountKey.json")
    cred = credentials.Certificate(key_path)

# Firebase initialize karein (agar pehle se initialized nahi hai toh)
try:
    app = get_app()
except ValueError:
    app = initialize_app(cred)

db = firestore.client()

def get_student_data(student_id):
    # Yahan "students" ki jagah "users" kar diya hai kyunke aapka data users collection mein hai
    doc = db.collection("users").document(student_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

# 1. Marks fetch karne ka function (Screenshot 1 ke mutabiq)
def get_student_marks(class_id, student_id, subject_id):
    # Path: classes -> class_id -> students -> student_id -> subjects -> subject_id
    doc_ref = db.collection("classes").document(class_id) \
                .collection("students").document(student_id) \
                .collection("subjects").document(subject_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict() # Isme assignment, midterm, quiz mil jayenge
    return None

# 2. Attendance fetch karne ka function (Screenshot 2 ke mutabiq)
def get_student_attendance(class_id, student_id, subject_id, date_id):
    # Path: classes -> class_id -> students -> student_id -> subjects -> subject_id -> attendance -> date_id
    doc_ref = db.collection("classes").document(class_id) \
                .collection("students").document(student_id) \
                .collection("subjects").document(subject_id) \
                .collection("attendance").document(date_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict() # Isme status aur timestamp mil jayega
    return None