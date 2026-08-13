from flask import Flask, jsonify, request
from flask_cors import CORS
from analysis_engine import analyze_class_performance, analyze_performance
from firebase_config import db

app = Flask(__name__)
CORS(app)

def normalize(s):
    if not s:
        return ""
    return str(s).lower().strip().replace(" ", "").replace("_", "").replace("-", "")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "AI Backend is running successfully!"})

@app.route("/analyze-class/<class_id>", methods=["GET"])
def analyze_class(class_id):
    try:
        raw_subject_id = request.args.get('subject_id')
        
        users_ref = db.collection('users').stream()
        actual_class_id = class_id
        
        for doc in users_ref:
            data = doc.to_dict()
            db_class = data.get('classId', '')
            if normalize(db_class) == normalize(class_id):
                actual_class_id = db_class
                break

        actual_subject_id = raw_subject_id
        if raw_subject_id and raw_subject_id != "All Subjects":
            sub_stream = db.collection('marks').document(actual_class_id).collection('students').stream()
            found_sub = False
            for s_doc in sub_stream:
                stu_subs = db.collection('marks').document(actual_class_id).collection('students').document(s_doc.id).collection('subjects').stream()
                for sub_doc in stu_subs:
                    if normalize(sub_doc.id) == normalize(raw_subject_id):
                        actual_subject_id = sub_doc.id
                        found_sub = True
                        break
                if found_sub:
                    break

        result = analyze_class_performance(actual_class_id, actual_subject_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"Error in analyze_class: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/student-query", methods=["POST"])
def student_query():
    try:
        data = request.json
        input_class_id = data.get('class_id')
        student_query_name = data.get('student_name', '').lower().strip()
        subject_id = data.get('subject_id', 'All Subjects')
        
        if not input_class_id or not student_query_name:
            return jsonify({"error": "class_id and student_name are required"}), 400

        # --- INVALID TEXT / CASUAL WORDS CHECK ---
        invalid_keywords = ["hlo", "hello", "hi", "hey", "test", "ok", "yes", "no", "good", "morning", "evening"]
        if student_query_name in invalid_keywords or len(student_query_name) < 2:
            return jsonify({
                "result": "Invalid text! Barah-e-karam kisi student ka theek naam type karein ya neechay diye gaye options select karein."
            }), 200

        # 1. Case-insensitive class aur student matching
        users_ref = db.collection('users').stream()
        matched_student = None
        student_id = None
        student_real_name = ""
        actual_class_id = input_class_id

        for doc in users_ref:
            user_data = doc.to_dict()
            db_class = str(user_data.get('classId', '')).strip()
            db_name = str(user_data.get('name', '')).strip()
            
            # Case-insensitive class check
            if normalize(db_class) == normalize(input_class_id):
                actual_class_id = db_class # Database wali exact class ID utha lein ge
                if student_query_name in db_name.lower():
                    matched_student = user_data
                    student_id = doc.id
                    student_real_name = db_name
                    break

        # Fallback: Agar users collection mein direct match na ho toh marks collection check karein
        if not matched_student:
            try:
                marks_students_ref = db.collection('marks').stream()
                for m_doc in marks_students_ref:
                    if normalize(m_doc.id) == normalize(input_class_id):
                        actual_class_id = m_doc.id
                        stu_stream = db.collection('marks').document(m_doc.id).collection('students').stream()
                        for s_doc in stu_stream:
                            s_id = s_doc.id
                            user_doc = db.collection('users').document(s_id).get()
                            if user_doc.exists:
                                u_data = user_doc.to_dict()
                                u_name = str(u_data.get('name', '')).strip()
                                if student_query_name in u_name.lower():
                                    matched_student = u_data
                                    student_id = s_id
                                    student_real_name = u_name
                                    break
                        if matched_student:
                            break
            except Exception as ex:
                print(f"Fallback error: {ex}")

        if not matched_student or not student_id:
            return jsonify({
                "result": f"Student '{student_query_name}' is class mein nahi mila."
            }), 200

        # 2. Marks Calculation (Subject-wise or All Subjects)
        MAX_TOTAL_MARKS = 40.0
        total_percentage = 0
        sub_count = 0

        if subject_id and subject_id != "All Subjects":
            sub_ref = db.collection('marks').document(actual_class_id).collection('students').document(student_id).collection('subjects').document(subject_id).get()
            if sub_ref.exists:
                sub_data = sub_ref.to_dict()
                total_obtained = sub_data.get('total')
                if total_obtained is not None:
                    total_percentage = (float(total_obtained) / MAX_TOTAL_MARKS) * 100
                else:
                    calc_tot = float(sub_data.get('assignment', 0)) + float(sub_data.get('midterm', 0)) + float(sub_data.get('quiz', 0))
                    total_percentage = (calc_tot / MAX_TOTAL_MARKS) * 100
                sub_count = 1
        else:
            marks_doc_ref = db.collection('marks').document(actual_class_id).collection('students').document(student_id).collection('subjects').stream()
            for sub_doc in marks_doc_ref:
                sub_data = sub_doc.to_dict()
                total_obtained = sub_data.get('total')
                if total_obtained is not None:
                    total_percentage += (float(total_obtained) / MAX_TOTAL_MARKS) * 100
                else:
                    calc_tot = float(sub_data.get('assignment', 0)) + float(sub_data.get('midterm', 0)) + float(sub_data.get('quiz', 0))
                    total_percentage += (calc_tot / MAX_TOTAL_MARKS) * 100
                sub_count += 1

        avg_marks = round(total_percentage / sub_count, 2) if sub_count > 0 else 0

        # 3. Attendance Calculation
        total_days = 0
        present_days = 0
                
        try:
            if subject_id and subject_id != "All Subjects":
                att_ref = db.collection('classes').document(actual_class_id).collection('students').document(student_id).collection('subjects').document(subject_id).collection('attendance').stream()
                for att_doc in att_ref:
                    total_days += 1
                    att_data = att_doc.to_dict()
                    status = str(att_data.get('status', '')).strip().lower()
                    if status in ['present', 'p', 'true', '1']:
                        present_days += 1
            else:
                sub_docs = db.collection('classes').document(actual_class_id).collection('students').document(student_id).collection('subjects').stream()
                for sub in sub_docs:
                    att_ref = db.collection('classes').document(actual_class_id).collection('students').document(student_id).collection('subjects').document(sub.id).collection('attendance').stream()
                    for att_doc in att_ref:
                        total_days += 1
                        att_data = att_doc.to_dict()
                        status = str(att_data.get('status', '')).strip().lower()
                        if status in ['present', 'p', 'true', '1']:
                            present_days += 1
        except Exception as e:
            print(f"Error fetching attendance: {e}")
        
        attendance_percentage = round((present_days / total_days * 100), 2) if total_days > 0 else 0

        return jsonify({
            "result": f"Result for {student_real_name}:\n• Average Marks: {avg_marks}%\n• Attendance: {attendance_percentage}%\n• Status: {'Good' if avg_marks >= 50 else 'Needs Improvement'}"
        }), 200

    except Exception as e:
        print(f"Error in student_query: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
