import json
import os
from abc import ABC, abstractmethod

# ------------------------------------------------------
# Load Grading Scale from JSON and Shared Logic Function
# ------------------------------------------------------
GRADING_FILE = os.path.join("data", "grading_scale.json")
with open(GRADING_FILE) as f:
    GRADING_SCALE = json.load(f)

def get_grade_and_point(marks):
    for rule in GRADING_SCALE:
        if rule['min'] <= marks <= rule['max']:
            return rule['grade'], rule['point']
    return None, None

# ------------------------------------------------------
# Abstract Class (Abstraction) for Person
# ------------------------------------------------------
class Person(ABC):
    def __init__(self, name, nationality, dob):
        self._name = name
        self._nationality = nationality
        self._dob = dob

    @abstractmethod
    def get_name(self): pass

    @abstractmethod
    def get_nationality(self): pass

    @abstractmethod
    def get_dob(self): pass

# ------------------------------------------------------
# Encapsulation: Course Class
# ------------------------------------------------------
class Course:
    def __init__(self, semester, code, title, marks=None, grade=None, grade_point=None):
        self.__semester = semester
        self.__code = code
        self.__title = title
        self.__marks = marks
        self.__grade = grade
        self.__grade_point = grade_point

    def to_dict(self):
        return {
            "semester": self.__semester,
            "code": self.__code,
            "title": self.__title,
            "marks": self.__marks,
            "grade": self.__grade,
            "grade_point": self.__grade_point
        }

# ------------------------------------------------------
# Inheritance: Student inherits from Person
# ------------------------------------------------------
class Student(Person):
    def __init__(self, id, name, nsin, unmeb_no, nationality, program, dob,entry_year, completion_year, photo=None, grades=None):
        super().__init__(name, nationality, dob)
        self.__id = id
        self.__nsin = nsin
        self.__unmeb_no = unmeb_no
        self.__program = program
        self.__entry_year = entry_year
        self.__completion_year = completion_year
        self.__photo = photo
        self.__grades = grades or {}

    # --- Getters ---
    def get_id(self): return self.__id
    def get_name(self): return self._name
    def get_nsin(self): return self.__nsin
    def get_unmeb_no(self): return self.__unmeb_no
    def get_nationality(self): return self._nationality
    def get_program(self): return self.__program
    def get_dob(self): return self._dob
    def get_entry_year(self): return self.__entry_year
    def get_completion_year(self): return self.__completion_year
    def get_photo(self): return self.__photo

    def get_semesters(self):
        return list(self.__grades.keys())

    def get_courses_by_semester(self, semester):
        return self.__grades.get(semester, [])

    def update_grades(self, semester, course_list):
        updated = []
        for course in course_list:
            marks = course.get("marks")
            if marks is not None:
                grade, point = get_grade_and_point(marks)
            else:
                grade, point = None, None
            updated.append({
                "semester": semester,
                "code": course["code"],
                "title": course["title"],
                "marks": marks,
                "grade": grade,
                "grade_point": point
            })
        self.__grades[semester] = updated

    def calculate_gpa(self, semester):
        courses = self.get_courses_by_semester(semester)
        total_points = sum(course["grade_point"] for course in courses if course.get("grade_point") is not None)
        count = sum(1 for course in courses if course.get("grade_point") is not None)
        return round(total_points / count, 2) if count > 0 else None

    def calculate_cgpa(self):
        total_points = 0
        total_units = 0
        for semester in self.get_semesters():
            for course in self.get_courses_by_semester(semester):
                if course.get("grade_point") is not None:
                    total_points += course["grade_point"]
                    total_units += 1
        return round(total_points / total_units, 2) if total_units > 0 else None

    def to_dict(self):
        return {
            "id": self.__id,
            "name": self._name,
            "nsin": self.__nsin,
            "unmeb_no": self.__unmeb_no,
            "nationality": self._nationality,
            "program": self.__program,
            "dob": self._dob,
            "entry_year": self.__entry_year,
            "completion_year": self.__completion_year,
            "photo": self.__photo,
            "grades": self.__grades
        }

# ------------------------------------------------------
# Polymorphism: DataStore Interface
# ------------------------------------------------------
class DataStore(ABC):
    @abstractmethod
    def load_from_json(self): pass

    @abstractmethod
    def save_to_json(self): pass

# ------------------------------------------------------
# StudentManager Implements DataStore
# ------------------------------------------------------
class StudentManager(DataStore):
    def __init__(self, json_path="data/students.json"):
        self._json_path = json_path
        self._students = []

    def load_from_json(self):
        if os.path.exists(self._json_path):
            with open(self._json_path, "r") as f:
                data = json.load(f)
                self._students = [Student(**student_data) for student_data in data]

    def save_to_json(self):
        with open(self._json_path, "w") as f:
            json.dump([student.to_dict() for student in self._students], f, indent=4)

    def add_student(self, name, student_id, nsin, unmeb_no, nationality, program,
                    dob, entry_year, completion_year, photo):
        student = Student(
            id=student_id,
            name=name,
            nsin=nsin,
            unmeb_no=unmeb_no,
            nationality=nationality,
            program=program,
            dob=dob,
            entry_year=entry_year,
            completion_year=completion_year,
            photo=photo,
            grades={}
        )
        self._students.append(student)

    def get_student(self, student_id):
        for student in self._students:
            if student.get_id() == student_id:
                return student
        return None

    def get_all_students(self):
        return self._students

    # method for deletion
    def delete_student(self, student_id):
        self._students = [s for s in self._students if s.get_id() != student_id]
