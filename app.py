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
        
        # Case insensitive aur spacing/underscore ignore karne ke liye normalization
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)