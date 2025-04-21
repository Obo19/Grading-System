from flask import Flask, render_template, request, redirect, url_for, flash
from models.models import StudentManager
import os
import uuid
import json
from werkzeug.utils import secure_filename
from datetime import datetime
from collections import defaultdict

# -----------------------------
# Initialize Flask App
# -----------------------------
app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# -----------------------------
# File Upload Configuration
# -----------------------------
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# -----------------------------
# Initialize Student Manager
# -----------------------------
student_manager = StudentManager()
student_manager.load_from_json()

# -----------------------------
# Load Grading Scale and Courses
# -----------------------------
with open(os.path.join("data", "grading_scale.json")) as f:
    grading_scale = json.load(f)

with open(os.path.join("data", "extracted_courses.json")) as f:
    program_courses = json.load(f)

# -----------------------------
# Allowed File Types
# -----------------------------
def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# -----------------------------
# Transcript Eligibility Check
# -----------------------------
def is_transcript_eligible(student):
    required_semesters = [
        'Year One Semester One',
        'Year One Semester Two',
        'Year Two Semester One',
        'Year Two Semester Two',
        'Year Three Semester One'
    ]

    for semester in required_semesters:
        courses = student.get_courses_by_semester(semester)
        if not courses:
            return False
        for course in courses:
            marks = course.get("marks")
            retake = course.get("retake")
            final_mark = retake if marks is not None and marks < 50 and retake is not None else marks
            if final_mark is None or final_mark < 50:
                return False
    return True

# -----------------------------
# Home Dashboard
# -----------------------------
@app.route('/')
def home():
    students = student_manager.get_all_students()
    semester_filter = request.args.get('semester')
    program_filter = request.args.get('program')

    ns = {
        "cn_total": 0,
        "cm_total": 0,
        "total_students": 0,
        "male_total": 0,
        "female_total": 0
    }

    course_marks = defaultdict(list)
    course_outcomes = defaultdict(lambda: {'pass': 0, 'fail': 0})
    all_semesters = set()
    all_programs = set()

    for student in students:
        program = student.get_program().strip().upper()
        all_programs.add(program)

        if program == 'CN':
            ns["cn_total"] += 1
        elif program == 'CM':
            ns["cm_total"] += 1
        ns["total_students"] += 1

        gender = student.get_gender()
        if gender == 'Male':
            ns["male_total"] += 1
        elif gender == 'Female':
            ns["female_total"] += 1

        if program_filter and program != program_filter:
            continue

        for semester, courses in student.get_all_courses().items():
            all_semesters.add(semester)

            if semester_filter and semester != semester_filter:
                continue

            for course in courses:
                if course.get("marks") is not None:
                    code = course.get("code")
                    marks = course["marks"]
                    course_marks[code].append(marks)
                    if marks >= 50:
                        course_outcomes[code]['pass'] += 1
                    else:
                        course_outcomes[code]['fail'] += 1

    avg_performance = {
        code: round(sum(marks)/len(marks), 2)
        for code, marks in course_marks.items()
    }

    pass_fail = {
        code: {
            'pass': course_outcomes[code]['pass'],
            'fail': course_outcomes[code]['fail']
        }
        for code in course_marks
    }

    return render_template(
        "home.html",
        ns=ns,
        performance=avg_performance,
        outcomes=pass_fail,
        semesters=sorted(all_semesters),
        programs=sorted(all_programs),
        selected_semester=semester_filter,
        selected_program=program_filter
    )

# -----------------------------
# Student Registration
# -----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        name = request.form['name']
        nsin = request.form['nsin']
        unmeb_no = request.form['unmeb_no']
        nationality = request.form['nationality']
        program = request.form['program'].strip().upper()
        dob = request.form['dob']
        entry_year = request.form['entry_year']
        completion_year = request.form['completion_year']
        gender = request.form.get('gender')

        if student_manager.get_student_by_nsin(nsin):
            flash(f"Student with NSIN {nsin} already exists.", "danger")
            return redirect(url_for('register_student'))

        photo = request.files['photo']
        photo_filename = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_filename = f"{uuid.uuid4()}_{filename}"
            photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

        student_id = str(uuid.uuid4())
        student_manager.add_student(
            name, student_id, nsin, unmeb_no, nationality, program,
            dob, entry_year, completion_year, gender, photo_filename
        )
        student_manager.save_to_json()
        flash("Student registered successfully!", "success")
        return redirect(url_for('home'))

    return render_template("register.html", is_edit=False)

# -----------------------------
# Edit Student
# -----------------------------
@app.route('/edit_student_by_id/<student_id>', methods=['GET', 'POST'])
def edit_student_by_id(student_id):
    student = student_manager.get_student(student_id)
    if not student:
        flash("Student not found.")
        return redirect(url_for('home'))

    if request.method == 'POST':
        student._name = request.form['name']
        student._nsin = request.form['nsin']
        student._unmeb_no = request.form['unmeb_no']
        student._nationality = request.form['nationality']
        student._program = request.form['program'].strip().upper()
        student._dob = request.form['dob']
        student._entry_year = request.form['entry_year']
        student._completion_year = request.form['completion_year']
        student._gender = request.form.get('gender')

        photo = request.files['photo']
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_filename = f"{uuid.uuid4()}_{filename}"
            photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))
            student._photo = photo_filename

        student_manager.save_to_json()
        flash("Student updated successfully!")
        return redirect(url_for('home'))

    return render_template("register.html", student=student, is_edit=True)

# -----------------------------
# Delete Student
# -----------------------------
@app.route('/delete_student_by_id/<student_id>')
def delete_student_by_id(student_id):
    student = student_manager.get_student(student_id)
    if not student:
        flash("Student not found.")
        return redirect(url_for('home'))

    if student.get_photo():
        photo_path = os.path.join(UPLOAD_FOLDER, student.get_photo())
        if os.path.exists(photo_path):
            os.remove(photo_path)

    student_manager.delete_student_by_id(student_id)
    student_manager.save_to_json()
    flash("Student deleted successfully!")
    return redirect(url_for('home'))

# -----------------------------
# Grade Entry
# -----------------------------
@app.route('/grades_by_id/<student_id>', methods=['GET', 'POST'])
def grade_entry_by_id(student_id):
    student = student_manager.get_student(student_id)
    if not student:
        flash("Student not found.")
        return redirect(url_for('home'))

    student_program = student.get_program().strip().upper()
    program_data = program_courses.get(student_program, {})
    available_semesters = list(program_data.keys())

    selected_semester = request.form.get('semester') or request.args.get('semester') or (available_semesters[0] if available_semesters else None)
    courses = program_data.get(selected_semester, []) if selected_semester else []
    existing = student.get_courses_by_semester(selected_semester) if selected_semester else []

    if request.method == 'POST' and 'submit_grades' in request.form:
        updated_courses = []

        for i in range(len(courses)):
            code = request.form.get(f'code_{i}')
            title = request.form.get(f'title_{i}')
            marks = request.form.get(f'marks_{i}')
            retake = request.form.get(f'retake_{i}')

            if code and title:
                course_data = {
                    "semester": selected_semester,
                    "code": code,
                    "title": title,
                    "marks": int(marks) if marks else None
                }

                if marks and int(marks) < 50 and retake:
                    course_data["retake"] = int(retake)

                updated_courses.append(course_data)

        student.update_grades(selected_semester, updated_courses)
        student_manager.save_to_json()
        flash("Grades saved successfully!")
        return redirect(url_for('home'))

    return render_template("grade_entry.html", student=student, courses=courses, existing=existing, selected_semester=selected_semester, available_semesters=available_semesters, grading_scale=grading_scale)

# -----------------------------
# View Testimonial
# -----------------------------
@app.route('/testimonial_by_id/<student_id>')
def view_testimonial_by_id(student_id):
    student = student_manager.get_student(student_id)
    if not student:
        flash("Student not found.")
        return redirect(url_for('home'))

    current_date = datetime.now().strftime("%d %B %Y")
    return render_template("testimonial.html", student=student, current_date=current_date)

# -----------------------------
# View Transcript (with eligibility check)
# -----------------------------
@app.route('/transcript_by_id/<student_id>')
def view_transcript_by_id(student_id):
    student = student_manager.get_student(student_id)
    if not student:
        flash("Student not found.")
        return redirect(url_for('home'))

    all_filled = is_transcript_eligible(student)
    current_date = datetime.now().strftime("%d %B %Y")

    return render_template("transcript.html", student=student, current_date=current_date, all_filled=all_filled)

# -----------------------------
# CN Students Only
# -----------------------------
@app.route('/cn_students')
def view_cn_students():
    students = student_manager.get_all_students()
    grouped_students = {'CN': {}}
    ns = {"cn_total": 0, "cm_total": 0, "total_students": 0, "male_total": 0, "female_total": 0}

    for student in students:
        if student.get_program().strip().upper() == 'CN':
            year = student.get_entry_year().strip()
            grouped_students['CN'].setdefault(year, []).append(student)
            ns["cn_total"] += 1
            ns["total_students"] += 1
            if student.get_gender() == 'Male':
                ns["male_total"] += 1
            elif student.get_gender() == 'Female':
                ns["female_total"] += 1

    return render_template('students.html', grouped_students=grouped_students, ns=ns, program='CN')

# -----------------------------
# CM Students Only
# -----------------------------
@app.route('/cm_students')
def view_cm_students():
    students = student_manager.get_all_students()
    grouped_students = {'CM': {}}
    ns = {"cn_total": 0, "cm_total": 0, "total_students": 0, "male_total": 0, "female_total": 0}

    for student in students:
        if student.get_program().strip().upper() == 'CM':
            year = student.get_entry_year().strip()
            grouped_students['CM'].setdefault(year, []).append(student)
            ns["cm_total"] += 1
            ns["total_students"] += 1
            if student.get_gender() == 'Male':
                ns["male_total"] += 1
            elif student.get_gender() == 'Female':
                ns["female_total"] += 1

    return render_template('students.html', grouped_students=grouped_students, ns=ns, program='CM')

# -----------------------------
# Run Server
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
