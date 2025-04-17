from flask import Flask, render_template, request, redirect, url_for, flash
from models.models import StudentManager
import os
import uuid
import json
from werkzeug.utils import secure_filename
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Upload directory
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Init student manager
student_manager = StudentManager()
student_manager.load_from_json()

# Load courses
with open(os.path.join("data", "extracted_courses.json")) as f:
    raw_courses = json.load(f)

seen = set()
grouped_courses = defaultdict(list)
for course in raw_courses:
    semester = course['semester'].strip()
    code = course['code'].strip()
    title = course['title'].strip()
    key = (semester, code)
    if key not in seen:
        seen.add(key)
        grouped_courses[semester].append({'semester': semester, 'code': code, 'title': title})

cleaned_courses = []
for sem_courses in grouped_courses.values():
    cleaned_courses.extend(sem_courses[:4])  # max 4 per semester

# Grading scale
with open(os.path.join("data", "grading_scale.json")) as f:
    grading_scale = json.load(f)

# ---------------- ROUTES ----------------

@app.route('/')
def home():
    students = student_manager.get_all_students()
    return render_template("students.html", students=students)

@app.route('/register', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        student_id = str(uuid.uuid4())
        name = request.form['name']
        nsin = request.form['nsin']
        unmeb_no = request.form['unmeb_no']
        nationality = request.form['nationality']
        program = request.form['program']
        dob = request.form['dob']
        entry_year = request.form['entry_year']
        completion_year = request.form['completion_year']

        photo = request.files['photo']
        photo_filename = None
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo_filename = f"{uuid.uuid4()}_{filename}"
            photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

        student_manager.add_student(name, student_id, nsin, unmeb_no, nationality, program,
                                    dob, entry_year, completion_year, photo_filename)
        student_manager.save_to_json()
        flash("Student registered successfully!")
        return redirect(url_for('home'))

    return render_template("register.html", is_edit=False)

@app.route('/edit_student/<student_id>', methods=['GET', 'POST'])
def edit_student(student_id):
    student = student_manager.get_student(student_id)
    if not student:
        flash("Student not found.")
        return redirect(url_for('home'))

    if request.method == 'POST':
        student.name = request.form['name']
        student.nsin = request.form['nsin']
        student.unmeb_no = request.form['unmeb_no']
        student.nationality = request.form['nationality']
        student.program = request.form['program']
        student.dob = request.form['dob']
        student.entry_year = request.form['entry_year']
        student.completion_year = request.form['completion_year']

        photo = request.files['photo']
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo_filename = f"{uuid.uuid4()}_{filename}"
            photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))
            student.photo = photo_filename

        student_manager.save_to_json()
        flash("Student updated successfully!")
        return redirect(url_for('home'))

    return render_template("register.html", student=student, is_edit=True)

@app.route('/delete_student/<student_id>')
def delete_student(student_id):
    student = student_manager.get_student(student_id)
    if not student:
        flash("Student not found.")
        return redirect(url_for('home'))

    photo_path = os.path.join(UPLOAD_FOLDER, student.get_photo()) if student.get_photo() else None
    if photo_path and os.path.exists(photo_path):
        os.remove(photo_path)

    student_manager.delete_student(student_id)
    student_manager.save_to_json()
    flash("🗑️ Student deleted successfully!")
    return redirect(url_for('home'))

@app.route('/grades/<student_id>', methods=['GET', 'POST'])
def grade_entry(student_id):
    student = student_manager.get_student(student_id)
    if not student:
        flash("Student not found.")
        return redirect(url_for('home'))

    selected_semester = request.form.get('semester') or request.args.get('semester')
    available_semesters = sorted(list(set([c['semester'] for c in cleaned_courses])))
    courses = [c for c in cleaned_courses if c['semester'] == selected_semester] if selected_semester else []
    existing = student.get_courses_by_semester(selected_semester) if selected_semester else []

    if request.method == 'POST' and 'submit_grades' in request.form:
        updated_courses = []
        for i in range(4):
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

    return render_template("grade_entry.html", student=student, courses=courses,
                           existing=existing, selected_semester=selected_semester,
                           available_semesters=available_semesters, grading_scale=grading_scale)

@app.route('/testimonial/<student_id>')
def view_testimonial(student_id):
    student = student_manager.get_student(student_id)
    if not student:
        flash("Student not found.")
        return redirect(url_for('home'))

    current_date = datetime.now().strftime("%d %B %Y")
    return render_template("testimonial.html", student=student, current_date=current_date)

@app.route('/transcript/<student_id>')
def view_transcript(student_id):
    student = student_manager.get_student(student_id)
    if not student:
        flash("Student not found.")
        return redirect(url_for('home'))

    required_semesters = [
        'Year One Semester One',
        'Year One Semester Two',
        'Year Two Semester One',
        'Year Two Semester Two',
        'Year Three Semester One'
    ]

    all_filled = all(len(student.get_courses_by_semester(sem)) > 0 for sem in required_semesters)

    current_date = datetime.now().strftime("%d %B %Y")
    return render_template("transcript.html", student=student, current_date=current_date, all_filled=all_filled)

# ------------------ START APP ------------------

if __name__ == '__main__':
    app.run(debug=True)
