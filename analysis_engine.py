from firebase_config import db

def analyze_class_performance(class_id, subject_id=None):
    users_ref = db.collection('users').get()
    
    class_students = []
    target_class = str(class_id).strip()
    
    for doc in users_ref:
        data = doc.to_dict()
        db_class = str(data.get('classId', '')).strip()
        
        if db_class.lower() == target_class.lower():
            student_info = data
            student_info['id'] = doc.id
            class_students.append(student_info)

    if not class_students:
        return {
            "predicted_performance": "Good",
            "class_average": "0%",
            "top_students_details": [],
            "weak_students_details": [],
            "risk_students_details": []
        }

    top_students = []
    weak_students = []
    risk_students = []
    total_marks_sum = 0
    valid_student_count = len(class_students)

    MAX_TOTAL_MARKS = 40.0  # Quiz(5) + Assignment(10) + Midterm(25)

    for student in class_students:
        name = student.get('name', 'Unknown Student')
        student_id = student['id']
        
        percentage_list = []
        
        try:
            if subject_id and subject_id != "All Subjects":
                sub_doc_ref = db.collection('marks').document(class_id).collection('students').document(student_id).collection('subjects').document(subject_id).get()
                if sub_doc_ref.exists:
                    sub_data = sub_doc_ref.to_dict()
                    total_obtained = sub_data.get('total')
                    if total_obtained is not None:
                        percentage_list.append((float(total_obtained) / MAX_TOTAL_MARKS) * 100)
                    else:
                        calc_tot = float(sub_data.get('assignment', 0)) + float(sub_data.get('midterm', 0)) + float(sub_data.get('quiz', 0))
                        percentage_list.append((calc_tot / MAX_TOTAL_MARKS) * 100)
            else:
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
            print(f"Error fetching marks for {name}: {e}")

        avg_percentage = (sum(percentage_list) / len(percentage_list)) if percentage_list else 0
        total_marks_sum += avg_percentage

        # --- CORRECTED ATTENDANCE FETCHING (.stream() for date document IDs) ---
        total_days = 0
        present_days = 0
        
        try:
            if subject_id and subject_id != "All Subjects":
                att_ref = db.collection('classes').document(class_id).collection('students').document(student_id).collection('subjects').document(subject_id).collection('attendance').stream()
                for att_doc in att_ref:
                    total_days += 1
                    att_data = att_doc.to_dict()
                    status = str(att_data.get('status', '')).strip().lower()
                    if status in ['present', 'p', 'true', '1']:
                        present_days += 1
            else:
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
            print(f"Error fetching attendance for {name}: {e}")

        attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0

        # Final score calculation (70% Marks + 30% Attendance)
        final_score = (avg_percentage * 0.7) + (attendance_percentage * 0.3)

        if final_score >= 70:
            top_students.append(f"{name} (Score: {round(final_score)}%, Marks: {round(avg_percentage)}%, Att: {round(attendance_percentage)}%)")
        else:
            weak_students.append(f"{name} (Score: {round(final_score)}%, Marks: {round(avg_percentage)}%, Att: {round(attendance_percentage)}%)")
            risk_students.append(f"{name} - Academic Risk")

    class_average = round(total_marks_sum / valid_student_count, 2) if valid_student_count > 0 else 0

    return {
        "predicted_performance": "Excellent" if class_average >= 60 else "Good",
        "class_average": f"{class_average}%",
        "top_students_details": top_students,
        "weak_students_details": weak_students,
        "risk_students_details": risk_students
    }

def analyze_performance(data):
    results = data.get("results", {})
    attendance = data.get("attendance", {})
    weaknesses = []
    strengths = []

    for subject, marks in results.items():
        if marks < 50:
            weaknesses.append({"subject": subject, "marks": marks, "level": "critical"})
        elif marks < 65:
            weaknesses.append({"subject": subject, "marks": marks, "level": "average"})
        else:
            strengths.append({"subject": subject, "marks": marks})

    return {
        "weaknesses": weaknesses,
        "strengths": strengths,
        "attendance": attendance
    }