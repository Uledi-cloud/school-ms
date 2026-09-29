from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, DateField, IntegerField,
                     SubmitField, PasswordField)
from wtforms.validators import DataRequired, Optional, Email, Length


class PupilForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    admission_no = StringField('Admission No.')
    gender = SelectField('Gender', choices=[('Male', 'Male'), ('Female', 'Female')])
    date_of_birth = DateField('Date of Birth', validators=[Optional()])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    stream_id = SelectField('Stream', coerce=int, validators=[Optional()])
    parent_name = StringField('Parent/Guardian Name')
    parent_phone = StringField('Parent Phone')
    parent_email = StringField('Parent Email', validators=[Optional(), Email()])
    address = StringField('Address')
    submit = SubmitField('Save Pupil')


class ClassForm(FlaskForm):
    name = StringField('Class Name', validators=[DataRequired()])
    level = SelectField('Level', choices=[
        ('Pre-Primary', 'Pre-Primary'), ('Primary', 'Primary'), ('Secondary', 'Secondary')
    ])
    submit = SubmitField('Save Class')


class StreamForm(FlaskForm):
    name = StringField('Stream Name', validators=[DataRequired()])
    class_id = SelectField('Class', coerce=int, validators=[DataRequired()])
    class_teacher_id = SelectField('Class Teacher', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Stream')


class StaffForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])
    role = SelectField('Role', choices=[
        ('Teacher', 'Teacher'), ('Head Teacher', 'Head Teacher'),
        ('Assistant Teacher', 'Assistant Teacher'), ('Support Staff', 'Support Staff')
    ])
    phone = StringField('Phone')
    email = StringField('Email', validators=[Optional(), Email()])
    submit = SubmitField('Save Staff')


class ExaminationForm(FlaskForm):
    name = StringField('Examination Name', validators=[DataRequired()])
    term = SelectField('Term', choices=[
        ('Term 1', 'Term 1'), ('Term 2', 'Term 2'), ('Term 3', 'Term 3')
    ])
    year = IntegerField('Year', validators=[DataRequired()])
    submit = SubmitField('Save Examination')


class NotificationForm(FlaskForm):
    channel = SelectField('Channel', choices=[('sms', 'SMS'), ('email', 'Email')])
    recipients = StringField('Recipients (comma-separated)', validators=[DataRequired()])
    subject = StringField('Subject (email only)')
    message = StringField('Message', validators=[DataRequired(), Length(max=500)])
    submit = SubmitField('Send')