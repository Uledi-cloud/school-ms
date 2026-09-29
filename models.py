from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='teacher')
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'))
    phone = db.Column(db.String(20))
    is_active_flag = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_teacher(self):
        return self.role in ('admin', 'teacher')

    @property
    def is_parent(self):
        return self.role == 'parent'


class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    streams = db.relationship('Stream', backref='class_', cascade='all, delete-orphan')
    pupils = db.relationship('Pupil', backref='class_', cascade='all, delete-orphan')


class Stream(db.Model):
    __tablename__ = 'streams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    class_teacher_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    pupils = db.relationship('Pupil', backref='stream', cascade='all, delete-orphan')


class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    streams = db.relationship('Stream', backref='class_teacher')


class Pupil(db.Model):
    __tablename__ = 'pupils'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50), nullable=False)
    admission_no = db.Column(db.String(20), unique=True)
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    stream_id = db.Column(db.Integer, db.ForeignKey('streams.id'))
    parent_name = db.Column(db.String(100))
    parent_phone = db.Column(db.String(20))
    parent_email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    photo_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    results = db.relationship('Result', backref='pupil', cascade='all, delete-orphan')

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p)


class Examination(db.Model):
    __tablename__ = 'examinations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    term = db.Column(db.String(20))
    year = db.Column(db.Integer)
    is_published = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    results = db.relationship('Result', backref='examination', cascade='all, delete-orphan')


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    code = db.Column(db.String(20))
    results = db.relationship('Result', backref='subject', cascade='all, delete-orphan')


class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    examination_id = db.Column(db.Integer, db.ForeignKey('examinations.id'), nullable=False)
    marks = db.Column(db.Float)
    grade = db.Column(db.String(5))
    month_tag = db.Column(db.String(20))
    assessment_type = db.Column(db.String(50))
    academic_year = db.Column(db.String(10))
    term_name = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('pupil_id', 'subject_id', 'examination_id'),)

    @staticmethod
    def calculate_grade(marks):
        """Tanzanian Primary Education grading scale"""
        if marks is None:
            return None
        if marks >= 81: return 'A'
        if marks >= 61: return 'B'
        if marks >= 41: return 'C'
        if marks >= 21: return 'D'
        return 'E'

    @staticmethod
    def grade_remark(grade):
        return {
            'A': 'Excellent', 'B': 'Very Good', 'C': 'Good',
            'D': 'Satisfactory', 'E': 'Fail'
        }.get(grade, '')


class TermBoundary(db.Model):
    __tablename__ = 'term_boundaries'
    id = db.Column(db.Integer, primary_key=True)
    term_name = db.Column(db.String(50), nullable=False)
    opening_date = db.Column(db.Date)
    closing_date = db.Column(db.Date)
    next_opening_date = db.Column(db.Date)
    academic_year = db.Column(db.String(10))


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(10))
    recipient = db.Column(db.String(100))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    error = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(50))
    detail = db.Column(db.Text)
    ip = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)