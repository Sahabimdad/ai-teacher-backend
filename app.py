from flask import Flask, jsonify, request
from flask_cors import CORS
from analysis_engine import analyze_class_performance, analyze_performance
from firebase_config import db

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "AI Backend is running successfully!"})

@app.route("/analyze-class/<class_id>", methods=["GET"])
def analyze_class(class_id):
    try:
        subject_id = request.args.get('subject_id')
        
        users_ref = db.collection('users').get()
        actual_class_id = class_id
        
        def normalize(s):
            return str(s).lower().replace(" ", "").replace("_", "").replace("-", "")

        for doc in users_ref:
            data = doc.to_dict()
            db_class = data.get('classId', '')
            if normalize(db_class) == normalize(class_id):
                actual_class_id = db_class
                break

        result = analyze_class_performance(actual_class_id, subject_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"Error in analyze_class: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/student-query", methods=["POST"])
def student_query():
    try:
        data = request.json
        class_id = data.get('class_id')
        query_text = data.get('student_name', '').lower().strip()
        
        if not class_id or not query_text:
            return jsonify({"error": "class_id and student_name are required"}), 400

        def normalize(s):
            return str(s).lower().replace(" ", "").replace("_", "").replace("-", "")

        # 1. Pehle check karein ke kya yeh koi Subject Code ho sakta hai?
        if "-" in query_text or len(query_text) <= 8:
            try:
                result = analyze_class_performance(class_id, subject_id=query_text.upper())
                if result and result.get("class_average") is not None:
                    top_list = "\n".join([f"• {s}" for s in result.get("top_students_details", [])[:5]])
                    return jsonify({
                        "result": f"Analysis for Subject ({query_text.upper()}):\n• Class Average: {result.get('class_average')}%\nTop Students:\n{top_list}"
                    }), 200
            except Exception as sub_err:
                print(f"Not a subject or analysis error: {sub_err}")

        # 2. Agar subject nahi, toh students mein naam dhoondhein
        users_ref = db.collection('users').get()
        matched_student = None
        student_id = None

        for doc in users_ref:
            user_data = doc.to_dict()
            db_class = user_data.get('classId', '')
            db_name = user_data.get('name', '').lower()
            
            if normalize(db_class) == normalize(class_id) and query_text in db_name:
                matched_student = user_data
                student_id = doc.id
                break

        if not matched_student:
            return jsonify({"result": f"Student or Subject '{query_text}' not found in class {class_id}."}), 200

        # Student mil gaya, ab marks aur attendance calculate karein
        student_real_name = matched_student.get('name', 'Unknown')
        MAX_TOTAL_MARKS = 40.0
        percentage_list = []

        try:
            marks_doc_ref = db.collection('marks').document(class_id).collection('students').document(student_id).collection('subjects').get()
            for sub_doc in marks_doc_ref:
                sub_data = sub_doc.to_dict()
                total_obtained = sub_data.get('total')
                if total_obtained is not None:
                    percentage_list.append((float(total_obtained) / MAX_TOTAL_MARKS) * 100)
                else:
                    calc_tot = float(sub_data.get('assignment', 0)) + float(sub_data.get('midterm', 0)) + float(sub_data.get('quiz', 0))
                    percentage_list.append((calc_tot / MAX_TOTAL_MARKS) * 100)
        except Exception as e:
            print(f"Error fetching marks: {e}")

        avg_marks = round(sum(percentage_list) / len(percentage_list), 2) if percentage_list else 0

        # Attendance calculation
        total_days = 0
        present_days = 0
        try:
            sub_docs = db.collection('classes').document(class_id).collection('students').document(student_id).collection('subjects').stream()
            for sub in sub_docs:
                att_ref = db.collection('classes').document(class_id).collection('students').document(student_id).collection('subjects').document(sub.id).collection('attendance').stream()
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


