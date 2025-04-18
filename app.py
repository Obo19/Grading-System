from flask import Flask, render_template, request, redirect, url_for, flash
from models.models import StudentManager
import os
import uuid
import json
from werkzeug.utils import secure_filename
from datetime import datetime

# -----------------------------
# Initialize Flask App
# -----------------------------
app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# -----------------------------
# Set Upload Directory
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
# Load Grading Scale & Course Structure
# -----------------------------
with open(os.path.join("data", "grading_scale.json")) as f:
    grading_scale = json.load(f)

with open(os.path.join("data", "extracted_courses.json")) as f:
    program_courses = json.load(f)

# -----------------------------
# File Type Checker
# -----------------------------
def allowed_file(filename):
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# -----------------------------
# Home Page
# -----------------------------
@app.route('/')
def home():
    students = student_manager.get_all_students()
    grouped_students = {}

    for student in students:
        program = student.get_program().strip().upper()
        entry_year = student.get_entry_year().strip()
        grouped_students.setdefault(program, {}).setdefault(entry_year, []).append(student)

    return render_template("students.html", grouped_students=grouped_students)

# -----------------------------
# Register New Student
# -----------------------------
@app.route('/register', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        student_id = str(uuid.uuid4())
        name = request.form['name']
        nsin = request.form['nsin']
        unmeb_no = request.form['unmeb_no']
        nationality = request.form['nationality']
        program = request.form['program'].strip().upper()
        dob = request.form['dob']
        entry_year = request.form['entry_year']
        completion_year = request.form['completion_year']
        gender = request.form.get('gender')

        photo = request.files['photo']
        photo_filename = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            photo_filename = f"{uuid.uuid4()}_{filename}"
            photo.save(os.path.join(UPLOAD_FOLDER, photo_filename))

        student_manager.add_student(name, student_id, nsin, unmeb_no, nationality, program,
                                    dob, entry_year, completion_year, gender, photo_filename)
        student_manager.save_to_json()
        flash("Student registered successfully!")
        return redirect(url_for('home'))

    return render_template("register.html", is_edit=False)

# -----------------------------
# Edit Student by ID
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
# Delete Student by ID
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
# Grade Entry by ID
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

    return render_template("grade_entry.html", student=student, courses=courses,existing=existing, selected_semester=selected_semester,available_semesters=available_semesters, grading_scale=grading_scale)

# -----------------------------
# Testimonial by ID
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
# Transcript by ID
# -----------------------------
@app.route('/transcript_by_id/<student_id>')
def view_transcript_by_id(student_id):
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

# -----------------------------
# Run App
# -----------------------------
if __name__ == '__main__':
    app.run(debug=True)
