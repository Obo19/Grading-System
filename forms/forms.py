from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class RegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    student_id = StringField('Student ID', validators=[DataRequired(), Length(min=2, max=20)])
    program = StringField('Program', validators=[DataRequired(), Length(min=2, max=100)])
    year = IntegerField('Year of Admission', validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    submit = SubmitField('Register Student')

class GradeEntryForm(FlaskForm):
    course1 = IntegerField('Course 1 Marks', validators=[DataRequired(), NumberRange(min=0, max=100)])
    course2 = IntegerField('Course 2 Marks', validators=[DataRequired(), NumberRange(min=0, max=100)])
    course3 = IntegerField('Course 3 Marks', validators=[DataRequired(), NumberRange(min=0, max=100)])
    course4 = IntegerField('Course 4 Marks', validators=[DataRequired(), NumberRange(min=0, max=100)])
    submit = SubmitField('Submit Grades')