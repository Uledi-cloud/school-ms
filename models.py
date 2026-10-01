from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

db = SQLAlchemy()


class School(db.Model):
    __tablename__ = 'schools'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(80), unique=True)
    motto = db.Column(db.String(200))
    address = db.Column(db.String(255))
    region = db.Column(db.String(100))
    district = db.Column(db.String(100))
    phone = db.Column(db.String(30))
    phone_2 = db.Column(db.String(30))
    email = db.Column(db.String(120))
    website = db.Column(db.String(120))
    postal_address = db.Column(db.String(100))
    registration_number = db.Column(db.String(50))
    necta_number = db.Column(db.String(50))
    head_teacher_name = db.Column(db.String(100))
    established_year = db.Column(db.String(10))
    logo_path = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Payment fields
    payment_token = db.Column(db.String(50), unique=True)
    monthly_fee = db.Column(db.Integer, default=70000)
    first_due_at = db.Column(db.DateTime)
    last_paid_at = db.Column(db.DateTime)
    next_due_at = db.Column(db.DateTime)
    payment_status = db.Column(db.String(20), default='pending')  # pending / paid / overdue


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    token_used = db.Column(db.String(50))
    reference = db.Column(db.String(100))
    method = db.Column(db.String(50))
    period_start = db.Column(db.DateTime)
    period_end = db.Column(db.DateTime)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    school = db.relationship('School', backref='payments')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), default='teacher')
    full_name = db.Column(db.String(120))
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'))
    staff_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'))
    is_active_flag = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    school = db.relationship('School', backref='users')

    __table_args__ = (
        db.UniqueConstraint('school_id', 'username', name='uq_school_username'),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_developer(self): return self.role == 'developer'
    @property
    def is_admin(self): return self.role in ('developer', 'admin')
    @property
    def is_teacher(self): return self.role in ('developer', 'admin', 'teacher')
    @property
    def is_parent(self): return self.role == 'parent'
    @property
    def is_pupil(self): return self.role == 'pupil'


class Class(db.Model):
    __tablename__ = 'classes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    level = db.Column(db.String(30))
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    streams = db.relationship('Stream', backref='class_', cascade='all, delete-orphan')
    pupils = db.relationship('Pupil', backref='class_', cascade='all, delete-orphan')


class Stream(db.Model):
    __tablename__ = 'streams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    class_teacher_id = db.Column(db.Integer, db.ForeignKey('staff.id'))
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    pupils = db.relationship('Pupil', backref='stream', cascade='all, delete-orphan')


class Staff(db.Model):
    __tablename__ = 'staff'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    streams = db.relationship('Stream', backref='class_teacher')


class Pupil(db.Model):
    __tablename__ = 'pupils'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50), nullable=False)
    admission_no = db.Column(db.String(30), nullable=False)
    gender = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    stream_id = db.Column(db.Integer, db.ForeignKey('streams.id'))
    parent_name = db.Column(db.String(100))
    parent_phone = db.Column(db.String(20))
    parent_phone_2 = db.Column(db.String(20))
    parent_email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    photo_path = db.Column(db.String(255))
    status = db.Column(db.String(20), default='Active')
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    results = db.relationship('Result', backref='pupil', cascade='all, delete-orphan')

    __table_args__ = (db.UniqueConstraint('school_id', 'admission_no', name='uq_school_admission'),)

    @property
    def full_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        return ' '.join(p for p in parts if p)


class Examination(db.Model):
    __tablename__ = 'examinations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    term = db.Column(db.String(30))
    year = db.Column(db.Integer)
    month_tag = db.Column(db.String(20))
    is_published = db.Column(db.Boolean, default=False)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    results = db.relationship('Result', backref='examination', cascade='all, delete-orphan')


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False)
    code = db.Column(db.String(20))
    class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    order_index = db.Column(db.Integer, default=0)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
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
    assessment_type = db.Column(db.String(60))
    academic_year = db.Column(db.String(10))
    term_name = db.Column(db.String(30))
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('pupil_id', 'subject_id', 'examination_id'),)

    @staticmethod
    def calculate_grade(marks):
        if marks is None: return None
        if marks >= 81: return 'A'
        if marks >= 61: return 'B'
        if marks >= 41: return 'C'
        if marks >= 21: return 'D'
        return 'E'


class TermBoundary(db.Model):
    __tablename__ = 'term_boundaries'
    id = db.Column(db.Integer, primary_key=True)
    term_name = db.Column(db.String(50), nullable=False)
    opening_date = db.Column(db.Date)
    closing_date = db.Column(db.Date)
    next_opening_date = db.Column(db.Date)
    academic_year = db.Column(db.String(10))
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)


class PupilShift(db.Model):
    __tablename__ = 'pupil_shifts'
    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    from_class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    to_class_id = db.Column(db.Integer, db.ForeignKey('classes.id'))
    from_stream_id = db.Column(db.Integer, db.ForeignKey('streams.id'))
    to_stream_id = db.Column(db.Integer, db.ForeignKey('streams.id'))
    reason = db.Column(db.String(255))
    shifted_at = db.Column(db.DateTime, default=datetime.utcnow)
    shifted_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    pupil = db.relationship('Pupil', backref='shift_history')


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    pupil_id = db.Column(db.Integer, db.ForeignKey('pupils.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Present')
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'), nullable=False)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)
    pupil = db.relationship('Pupil', backref='attendance_records')
    __table_args__ = (db.UniqueConstraint('pupil_id', 'attendance_date'),)


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(10))
    recipient = db.Column(db.String(100))
    subject = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    error = db.Column(db.Text)
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(50))
    detail = db.Column(db.Text)
    ip = db.Column(db.String(45))
    school_id = db.Column(db.Integer, db.ForeignKey('schools.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
