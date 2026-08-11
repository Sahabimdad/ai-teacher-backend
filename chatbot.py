from analysis_engine import analyze_performance

sessions = {}

def handle_chat(student_id, message, student_data):
    if student_id not in sessions:
        sessions[student_id] = {
            "stage": "start",
            "answers": {},
            "analysis": None
        }

    session = sessions[student_id]
    stage = session["stage"]
    message = message.strip().lower()

    # -------- STAGE: START --------
    if stage == "start" or message in ["hi", "hello", "start", "begin"]:
        analysis = analyze_performance(student_data)
        session["analysis"] = analysis
        session["stage"] = "ask_hours"

        weak_list = [w["subject"] for w in analysis["weaknesses"]]
        strong_list = [s["subject"] for s in analysis["strengths"]]

        reply = "📊 *Your Academic Analysis:*\n\n"

        if strong_list:
            reply += f"✅ You are performing well in: {', '.join(strong_list)}\n\n"

        if weak_list:
            reply += f"⚠️ You need improvement in: {', '.join(weak_list)}\n\n"
        else:
            reply += "🎉 No major weak areas found!\n\n"

        reply += "How many hours can you study daily? (e.g., 3 or 4)"
        return reply

    # -------- STAGE: ASK HOURS --------
    elif stage == "ask_hours":
        session["answers"]["hours"] = message
        session["stage"] = "ask_time"
        return "⏰ What time do you usually study?\n(e.g., 6 PM to 10 PM)"

    # -------- STAGE: ASK TIME --------
    elif stage == "ask_time":
        session["answers"]["time"] = message
        session["stage"] = "done"
        return generate_schedule(session["analysis"], session["answers"])

    # -------- STAGE: DONE --------
    elif stage == "done":
        if message in ["yes", "restart", "new"]:
            sessions[student_id]["stage"] = "start"
            return "Sure! Type 'hi' to start again."
        else:
            return "Type 'yes' to generate a new schedule or ask anything!"


def generate_schedule(analysis, answers):
    weak_subjects = [w["subject"] for w in analysis["weaknesses"]]
    strong_subjects = [s["subject"] for s in analysis["strengths"]]
    hours = answers.get("hours", "3")
    time_range = answers.get("time", "evening")

    try:
        total_hours = float(hours)
    except:
        total_hours = 3.0

    reply = f"📅 *Your Personalized Study Schedule*\n"
    reply += f"⏱️ Total Hours: {hours} | 🕐 Time: {time_range}\n\n"

    if weak_subjects:
        weak_time = round(total_hours * 0.5, 1)
        reply += f"🔴 *Weak Subjects ({weak_time} hrs):*\n"
        per_weak = round(weak_time / len(weak_subjects), 1)
        for s in weak_subjects:
            reply += f"   • {s}: {per_weak} hrs\n"
        reply += "\n"

    if strong_subjects:
        strong_time = round(total_hours * 0.3, 1)
        reply += f"🟢 *Revision ({strong_time} hrs):*\n"
        per_strong = round(strong_time / len(strong_subjects), 1)
        for s in strong_subjects:
            reply += f"   • {s}: {per_strong} hrs\n"
        reply += "\n"

    break_time = round(total_hours * 0.2, 1)
    reply += f"☕ *Break Time: {break_time} hrs*\n\n"
    reply += "💡 *Recommendations:*\n"

    for w in analysis["weaknesses"]:
        if w["level"] == "critical":
            reply += f"   • {w['subject']} score is {w['marks']}% — spend extra time daily.\n"
        else:
            reply += f"   • {w['subject']} needs improvement — practice regularly.\n"

    reply += "\nType 'yes' to generate a new schedule."
    return reply
