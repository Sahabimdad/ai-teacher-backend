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
        student_query_name = data.get('student_name', '').lower().strip()
        
        if not class_id or not student_query_name:
            return jsonify({"error": "class_id and student_name are required"}), 400

        users_ref = db.collection('users').get()
        matched_student = None
        student_id = None

        def normalize(s):
            return str(s).lower().replace(" ", "").replace("_", "").replace("-", "")

        for doc in users_ref:
            user_data = doc.to_dict()
            db_class = user_data.get('classId', '')
            db_name = user_data.get('name', '').lower()
            
            if normalize(db_class) == normalize(class_id) and student_query_name in db_name:
                matched_student = user_data
                student_id = doc.id
                break

        if not matched_student:
            return jsonify({"result": f"Student '{student_query_name}' not found in class {class_id}."}), 200

        MAX_TOTAL_MARKS = 40.0
        marks_doc_ref = db.collection('marks').document(class_id).collection('students').document(student_id).collection('subjects').get()
        
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
        student_real_name = matched_student.get('name', 'Unknown')

        return jsonify({
            "result": f"Result for {student_real_name}:\n• Average Marks: {avg_marks}%\n• Status: {'Good' if avg_marks >= 50 else 'Needs Improvement'}"
        }), 200

    except Exception as e:
        print(f"Error in student_query: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)