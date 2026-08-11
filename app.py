from flask import Flask, jsonify, request
from flask_cors import CORS
from analysis_engine import analyze_class_performance, analyze_performance
from firebase_config import db

app = Flask(__name__)
CORS(app)

def normalize(s):
    if not s:
        return ""
    return str(s).lower().replace(" ", "").replace("_", "").replace("-", "")

@app.route("/", methods=["GET"])
def home():
    return jsonify({"status": "AI Backend is running successfully!"})

@app.route("/analyze-class/<class_id>", methods=["GET"])
def analyze_class(class_id):
    try:
        raw_subject_id = request.args.get('subject_id')
        
        # Fast fetch users to find matching class ID
        users_ref = db.collection('users').stream()
        actual_class_id = class_id
        
        for doc in users_ref:
            data = doc.to_dict()
            db_class = data.get('classId', '')
            if normalize(db_class) == normalize(class_id):
                actual_class_id = db_class
                break

        # Subject normalization logic if subject is provided
        actual_subject_id = raw_subject_id
        if raw_subject_id and raw_subject_id != "All Subjects":
            sub_stream = db.collection('marks').document(actual_class_id).collection('students').stream()
            # Find a matching subject across records if needed, or normalize comparison
            found_sub = False
            for s_doc in sub_stream:
                # check student subjects collection
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
        class_id = data.get('class_id')
        student_query_name = data.get('student_name', '').lower().strip()
        
        if not class_id or not student_query_name:
            return jsonify({"error": "class_id and student_name are required"}), 400

        users_ref = db.collection('users').stream()
        matched_student = None
        student_id = None
        actual_class_id = class_id

        # Fast matching for student and class
        for doc in users_ref:
            user_data = doc.to_dict()
            db_class = user_data.get('classId', '')
            db_name = user_data.get('name', '')
            
            if normalize(db_class) == normalize(class_id):
                actual_class_id = db_class
                if student_query_name in normalize(db_name) or student_query_name in db_name.lower():
                    matched_student = user_data
                    student_id = doc.id
                    break

        if not matched_student:
            return jsonify({
                "result": f"Student '{student_query_name}' not found in class {class_id}.\n\n💡 Tip: Click on the 'Change Class' option below to switch your class or check the spelling."
            }), 200

        # Marks Calculation
        MAX_TOTAL_MARKS = 40.0
        marks_doc_ref = db.collection('marks').document(actual_class_id).collection('students').document(student_id).collection('subjects').stream()
        
        total_percentage = 0
        sub_count = 0
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

        # Attendance Calculation
        total_days = 0
        present_days = 0
        try:
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
            print(f"Error fetching student attendance: {e}")

        attendance_percentage = round((present_days / total_days * 100), 2) if total_days > 0 else 0
        student_real_name = matched_student.get('name', 'Unknown')

        return jsonify({
            "result": f"Result for {student_real_name}:\n• Average Marks: {avg_marks}%\n• Attendance: {attendance_percentage}% ({present_days}/{total_days} days)\n• Status: {'Good' if avg_marks >= 50 else 'Needs Improvement'}\n\n🔄 Click on 'Change Class' below if you want to switch class."
        }), 200

    except Exception as e:
        print(f"Error in student_query: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)