from flask import (Flask, render_template, redirect, url_for, flash,
                   request, abort, Blueprint, jsonify)
from flask_login import LoginManager, login_required, current_user
from datetime import datetime, date

from config import Config
from models import (db, User, Class, Stream, Staff, Pupil, Examination,
                    Subject, Result, Notification, AuditLog, TermBoundary,
                    Attendance, School, PupilShift)
from forms import (PupilForm, ClassForm, StreamForm, StaffForm,
                   ExaminationForm, NotificationForm)
from auth import auth_bp
from decorators import admin_required, teacher_required, parent_required
from notifications import notify_results_published, send_sms, send_email
from excel_import import import_pupils_from_excel

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'


@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


app.register_blueprint(auth_bp)


# ===================== HELPERS =====================

def current_school_id():
    if not current_user.is_authenticated:
        return None
    return current_user.school_id


CURRICULUM_SUBJECTS = {
    'Baby Class':     ['Kiswahili', 'English', 'Mathematics', 'Arts and Sports',
                       'Health Care and Environment', 'Computer', 'French'],
    'Middle Class':   ['Kiswahili', 'English', 'Mathematics', 'Arts and Sports',
                       'Health Care and Environment', 'Computer', 'French'],
    'Top Class':      ['Kiswahili', 'English', 'Mathematics', 'Arts and Sports',
                       'Health Care and Environment', 'Computer', 'French'],
    'Standard One':   ['Kiswahili', 'English', 'Mathematics', 'Arts and Sports',
                       'Health Care and Environment', 'Computer', 'French'],
    'Standard Two':   ['Kiswahili', 'English', 'Mathematics', 'Arts and Sports',
                       'Health Care and Environment', 'Computer', 'French'],
    'Standard Three': ['Kiswahili', 'English', 'Mathematics', 'Science',
                       'Geography and Environment', 'Historia ya Tanzania na Maadili',
                       'Arts and Sports', 'Computer', 'French'],
    'Standard Four':  ['Kiswahili', 'English', 'Mathematics', 'Science',
                       'Geography and Environment', 'Historia ya Tanzania na Maadili',
                       'Arts and Sports', 'Computer', 'French'],
    'Standard Five':  ['Kiswahili', 'English', 'Mathematics', 'Science',
                       'Geography and Environment', 'Historia ya Tanzania na Maadili',
                       'Arts and Sports', 'Computer', 'French'],
    'Standard Six':   ['Kiswahili', 'English', 'Mathematics', 'Science',
                       'Social Studies', 'Civic and Moral Education',
                       'Vocational Skills and Fine Arts', 'Computer', 'French'],
    'Standard Seven': ['Kiswahili', 'English', 'Mathematics', 'Science',
                       'Social Studies', 'Civic and Moral Education']
}

ACADEMIC_SCHEDULE = {
    'Term I': {
        'January':   'January Monthly Exam',
        'February':  'February Monthly Exam',
        'March':     'March Mid-Term Exam',
        'April':     'April Monthly Exam',
        'May':       'May Terminal Exam'
    },
    'Term II': {
        'July':      'July Monthly Exam',
        'August':    'August Monthly Exam',
        'September': 'Mid-Term II',
        'October':   'October Monthly Exam',
        'November':  'Annual Exam'
    }
}

SUBJECT_COLORS = {
    'Kiswahili': {'border': '#3b82f6', 'bg': '#eff6ff', 'text': '#1d4ed8'},
    'English':   {'border': '#ec4899', 'bg': '#fdf2f8', 'text': '#be185d'},
    'Mathematics': {'border': '#f59e0b', 'bg': '#fef3c7', 'text': '#b45309'},
    'Science':   {'border': '#10b981', 'bg': '#ecfdf5', 'text': '#047857'},
    'Geography and Environment': {'border': '#8b5cf6', 'bg': '#f5f3ff', 'text': '#6d28d9'},
    'Social Studies': {'border': '#8b5cf6', 'bg': '#f5f3ff', 'text': '#6d28d9'},
    'Historia ya Tanzania na Maadili': {'border': '#06b6d4', 'bg': '#ecfeff', 'text': '#0e7490'},
    'Civic and Moral Education': {'border': '#06b6d4', 'bg': '#ecfeff', 'text': '#0e7490'},
    'Arts and Sports': {'border': '#f43f5e', 'bg': '#fff1f2', 'text': '#be123c'},
    'Vocational Skills and Fine Arts': {'border': '#f43f5e', 'bg': '#fff1f2', 'text': '#be123c'},
    'Health Care and Environment': {'border': '#10b981', 'bg': '#ecfdf5', 'text': '#047857'},
    'Computer': {'border': '#64748b', 'bg': '#f1f5f9', 'text': '#475569'},
    'French':   {'border': '#a855f7', 'bg': '#faf5ff', 'text': '#7e22ce'}
}


@app.context_processor
def inject_globals():
    school = None
    try:
        if current_user.is_authenticated and current_user.school_id:
            school = School.query.get(current_user.school_id)
        else:
            school = School.query.first()
    except Exception:
        school = None
    return {
        'academic_schedule': ACADEMIC_SCHEDULE,
        'subject_colors': SUBJECT_COLORS,
        'curriculum_subjects': CURRICULUM_SUBJECTS,
        'current_year': datetime.utcnow().year,
        'school': school,
    }


def tanzanian_grade(average):
    if average is None: return {'grade': '-', 'remarks': '-'}
    if average >= 81: return {'grade': 'A', 'remarks': 'Excellent'}
    if average >= 61: return {'grade': 'B', 'remarks': 'Very Good'}
    if average >= 41: return {'grade': 'C', 'remarks': 'Good'}
    if average >= 21: return {'grade': 'D', 'remarks': 'Satisfactory'}
    return {'grade': 'E', 'remarks': 'Fail'}


def head_teacher_comment(avg):
    if avg >= 81: return "An exceptional academic performance overall. Keep maintaining this golden benchmark."
    if avg >= 61: return "A highly commendable term transcript showing great devotion."
    if avg >= 41: return "Satisfactory progress achieved. Room for enhancement remains vast."
    if avg >= 21: return "Academic performance is currently precarious. Weekend clinics are advised."
    return "Critical academic intervention required. Please meet the office."


def dean_comment(avg):
    if avg >= 81: return "Mastery of core syllabus objectives clearly visible across all metrics."
    if avg >= 61: return "Good curriculum milestone absorption. Pushing further will yield stellar outcomes."
    if avg >= 41: return "Basic competencies verified. Remediation during holidays is advised."
    if avg >= 21: return "Syllabus assimilation tracking below institutional expectations."
    return "Core curriculum performance metrics fail to meet standard validation criteria."


# ===================== SEED =====================

def seed_data_for_school(school_id):
    all_subjects = set()
    for subs in CURRICULUM_SUBJECTS.values():
        all_subjects.update(subs)
    for s in sorted(all_subjects):
        if not Subject.query.filter_by(name=s, school_id=school_id).first():
            db.session.add(Subject(name=s, school_id=school_id))

    for name, level in [
        ('Baby Class', 'Pre-Primary'), ('Middle Class', 'Pre-Primary'),
        ('Top Class', 'Pre-Primary'), ('Standard One', 'Primary'),
        ('Standard Two', 'Primary'), ('Standard Three', 'Primary'),
        ('Standard Four', 'Primary'), ('Standard Five', 'Primary'),
        ('Standard Six', 'Primary'), ('Standard Seven', 'Primary'),
    ]:
        if not Class.query.filter_by(name=name, school_id=school_id).first():
            db.session.add(Class(name=name, level=level, school_id=school_id))

    if not TermBoundary.query.filter_by(school_id=school_id).first():
        db.session.add(TermBoundary(term_name='Term I', academic_year='2026', school_id=school_id))
        db.session.add(TermBoundary(term_name='Term II', academic_year='2026', school_id=school_id))
    db.session.commit()


# ===================== SETUP =====================

@app.route('/setup-db-<token>')
def setup_db(token):
    if token != app.config['SETUP_TOKEN']:
        abort(404)
    db.create_all()
    if User.query.filter_by(role='developer').count() == 0:
        dev = User(
            username='developer',
            email='dev@school.com',
            full_name='System Developer',
            role='developer',
            is_active_flag=True,
            must_change_password=False,
        )
        dev.set_password('Dev@12345')
        db.session.add(dev)
        db.session.commit()
        return 'Developer created. Login: developer / Dev@12345'
    return 'Developer already exists.'


@app.route('/reset-db-<token>')
def reset_db(token):
    if token != app.config['SETUP_TOKEN']:
        abort(404)
    db.drop_all()
    db.create_all()
    dev = User(
        username='developer',
        email='dev@school.com',
        full_name='System Developer',
        role='developer',
        is_active_flag=True,
        must_change_password=False,
    )
    dev.set_password('Dev@12345')
    db.session.add(dev)
    db.session.commit()
    return 'DB reset. Developer login: developer / Dev@12345'


def log_action(action, detail=''):
    if current_user.is_authenticated:
        db.session.add(AuditLog(user_id=current_user.id, action=action,
                                detail=detail, ip=request.remote_addr or '',
                                school_id=current_user.school_id))
        db.session.commit()


# ===================== DASHBOARD =====================

@app.route('/')
@login_required
def index():
    if current_user.role == 'developer':
        return redirect(url_for('auth.developer_schools'))

    sid = current_user.school_id
    stats = {
        'pupils': Pupil.query.filter_by(status='Active', school_id=sid).count(),
        'classes': Class.query.filter_by(school_id=sid).count(),
        'streams': Stream.query.filter_by(school_id=sid).count(),
        'staff': Staff.query.filter_by(school_id=sid).count(),
        'exams': Examination.query.filter_by(school_id=sid).count(),
        'users': User.query.filter_by(school_id=sid).count(),
    }
    recent_pupils = Pupil.query.filter_by(school_id=sid).order_by(Pupil.created_at.desc()).limit(5).all()
    recent = AuditLog.query.filter_by(school_id=sid).order_by(AuditLog.created_at.desc()).limit(8).all()
    return render_template('index.html', stats=stats,
                           recent_pupils=recent_pupils, recent=recent)


# ===================== PUPILS =====================

@app.route('/pupils')
@teacher_required
def pupils():
    sid = current_user.school_id
    q = Pupil.query.filter_by(school_id=sid)
    class_id = request.args.get('class_id', type=int)
    stream_id = request.args.get('stream_id', type=int)
    search = request.args.get('q', '').strip()
    if class_id:
        q = q.filter_by(class_id=class_id)
    if stream_id:
        q = q.filter_by(stream_id=stream_id)
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(Pupil.first_name.ilike(like),
                            Pupil.last_name.ilike(like),
                            Pupil.admission_no.ilike(like)))
    all_pupils = q.order_by(Pupil.first_name).all()
    return render_template('pupils/list.html', pupils=all_pupils,
                           classes=Class.query.filter_by(school_id=sid).all(),
                           class_id=class_id, stream_id=stream_id, search=search)


@app.route('/pupils/add', methods=['GET', 'POST'])
@teacher_required
def add_pupil():
    sid = current_user.school_id
    form = PupilForm()
    form.class_id.choices = [(c.id, c.name) for c in Class.query.filter_by(school_id=sid).all()]
    form.stream_id.choices = [(0, '-- None --')] + [
        (s.id, f'{s.class_.name} - {s.name}') for s in Stream.query.filter_by(school_id=sid).all()
    ]
    if form.validate_on_submit():
        p = Pupil(
            first_name=form.first_name.data,
            middle_name=request.form.get('middle_name', '').strip() or None,
            last_name=form.last_name.data,
            admission_no=form.admission_no.data, gender=form.gender.data,
            date_of_birth=form.date_of_birth.data, class_id=form.class_id.data,
            stream_id=form.stream_id.data or None,
            parent_name=form.parent_name.data, parent_phone=form.parent_phone.data,
            parent_email=form.parent_email.data, address=form.address.data,
            school_id=sid,
        )
        db.session.add(p)
        db.session.commit()
        log_action('create_pupil', p.full_name)
        flash('Pupil registered!', 'success')
        return redirect(url_for('pupils'))
    return render_template('pupils/form.html', form=form, title='Register Pupil', pupil=None)


@app.route('/pupils/edit/<int:id>', methods=['GET', 'POST'])
@teacher_required
def edit_pupil(id):
    p = Pupil.query.get_or_404(id)
    if p.school_id != current_user.school_id:
        abort(403)
    sid = current_user.school_id
    form = PupilForm(obj=p)
    form.class_id.choices = [(c.id, c.name) for c in Class.query.filter_by(school_id=sid).all()]
    form.stream_id.choices = [(0, '-- None --')] + [
        (s.id, f'{s.class_.name} - {s.name}') for s in Stream.query.filter_by(school_id=sid).all()
    ]
    if form.validate_on_submit():
        p.first_name = form.first_name.data
        p.middle_name = request.form.get('middle_name', '').strip() or None
        p.last_name = form.last_name.data
        p.admission_no = form.admission_no.data
        p.gender = form.gender.data
        p.date_of_birth = form.date_of_birth.data
        p.class_id = form.class_id.data
        p.stream_id = form.stream_id.data or None
        p.parent_name = form.parent_name.data
        p.parent_phone = form.parent_phone.data
        p.parent_email = form.parent_email.data
        p.address = form.address.data
        db.session.commit()
        flash('Pupil updated!', 'success')
        return redirect(url_for('pupils'))
    return render_template('pupils/form.html', form=form, title='Edit Pupil', pupil=p)


@app.route('/pupils/delete/<int:id>')
@teacher_required
def delete_pupil(id):
    p = Pupil.query.get_or_404(id)
    if p.school_id != current_user.school_id:
        abort(403)
    db.session.delete(p)
    db.session.commit()
    flash('Pupil deleted.', 'info')
    return redirect(url_for('pupils'))


# ===================== SHIFT / DROP / REACTIVATE =====================

@app.route('/pupils/shift/<int:id>', methods=['GET', 'POST'])
@teacher_required
def shift_pupil(id):
    p = Pupil.query.get_or_404(id)
    if p.school_id != current_user.school_id:
        abort(403)
    sid = current_user.school_id

    if request.method == 'POST':
        new_class_id = request.form.get('new_class_id', type=int)
        new_stream_id = request.form.get('new_stream_id', type=int) or None
        reason = request.form.get('reason', '')

        if not new_class_id:
            flash('Please select a new class.', 'danger')
            return redirect(url_for('shift_pupil', id=id))

        log = PupilShift(
            pupil_id=p.id,
            from_class_id=p.class_id, to_class_id=new_class_id,
            from_stream_id=p.stream_id, to_stream_id=new_stream_id,
            reason=reason, shifted_by=current_user.id
        )
        db.session.add(log)

        p.class_id = new_class_id
        p.stream_id = new_stream_id
        db.session.commit()
        log_action('shift_pupil', f'{p.full_name} -> class {new_class_id}')
        flash(f'{p.full_name} shifted successfully.', 'success')
        return redirect(url_for('pupils'))

    classes = Class.query.filter_by(school_id=sid).order_by(Class.id).all()
    streams = Stream.query.filter_by(school_id=sid).all()
    return render_template('pupils/shift.html', pupil=p, classes=classes, streams=streams)


@app.route('/pupils/drop/<int:id>')
@teacher_required
def drop_pupil(id):
    p = Pupil.query.get_or_404(id)
    if p.school_id != current_user.school_id:
        abort(403)
    p.status = 'Dropped'
    db.session.commit()
    log_action('drop_pupil', p.full_name)
    flash(f'{p.full_name} marked as Dropped.', 'info')
    return redirect(url_for('pupils'))


@app.route('/pupils/reactivate/<int:id>')
@teacher_required
def reactivate_pupil(id):
    p = Pupil.query.get_or_404(id)
    if p.school_id != current_user.school_id:
        abort(403)
    p.status = 'Active'
    db.session.commit()
    flash(f'{p.full_name} reactivated.', 'success')
    return redirect(url_for('pupils'))


# ===================== CLASSES =====================

@app.route('/classes')
@teacher_required
def classes():
    sid = current_user.school_id
    return render_template('classes/list.html',
                           classes=Class.query.filter_by(school_id=sid).all())


@app.route('/classes/add', methods=['GET', 'POST'])
@admin_required
def add_class():
    form = ClassForm()
    if form.validate_on_submit():
        db.session.add(Class(name=form.name.data, level=form.level.data,
                             school_id=current_user.school_id))
        db.session.commit()
        flash('Class added!', 'success')
        return redirect(url_for('classes'))
    return render_template('classes/form.html', form=form, title='Add Class')


@app.route('/classes/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_class(id):
    c = Class.query.get_or_404(id)
    if c.school_id != current_user.school_id:
        abort(403)
    form = ClassForm(obj=c)
    if form.validate_on_submit():
        c.name = form.name.data
        c.level = form.level.data
        db.session.commit()
        flash('Class updated!', 'success')
        return redirect(url_for('classes'))
    return render_template('classes/form.html', form=form, title='Edit Class')


@app.route('/classes/delete/<int:id>')
@admin_required
def delete_class(id):
    c = Class.query.get_or_404(id)
    if c.school_id != current_user.school_id:
        abort(403)
    db.session.delete(c)
    db.session.commit()
    flash('Class deleted.', 'info')
    return redirect(url_for('classes'))


@app.route('/classes/<int:id>/subjects', methods=['GET', 'POST'])
@admin_required
def class_subjects(id):
    cls = Class.query.get_or_404(id)
    if cls.school_id != current_user.school_id:
        abort(403)
    sid = current_user.school_id

    if request.method == 'POST':
        chosen_ids = [int(x) for x in request.form.getlist('subject_ids')]
        Subject.query.filter_by(class_id=cls.id).update({'class_id': None})
        db.session.commit()
        for sub_id in chosen_ids:
            sub = Subject.query.get(sub_id)
            if sub and sub.school_id == sid:
                sub.class_id = cls.id
        db.session.commit()
        flash(f'Subjects updated for {cls.name}.', 'success')
        return redirect(url_for('class_subjects', id=cls.id))

    all_subjects = Subject.query.filter_by(school_id=sid).order_by(Subject.name).all()
    selected_ids = [s.id for s in Subject.query.filter_by(class_id=cls.id).all()]
    return render_template('subjects/class_subjects.html',
                           cls=cls, all_subjects=all_subjects, selected_ids=selected_ids)


# ===================== STREAMS =====================

@app.route('/streams')
@teacher_required
def streams():
    sid = current_user.school_id
    return render_template('streams/list.html',
                           streams=Stream.query.filter_by(school_id=sid).all())


@app.route('/streams/add', methods=['GET', 'POST'])
@admin_required
def add_stream():
    sid = current_user.school_id
    form = StreamForm()
    form.class_id.choices = [(c.id, c.name) for c in Class.query.filter_by(school_id=sid).all()]
    form.class_teacher_id.choices = [(0, '-- None --')] + [
        (s.id, f'{s.first_name} {s.last_name}') for s in Staff.query.filter_by(school_id=sid).all()
    ]
    if form.validate_on_submit():
        s = Stream(name=form.name.data, class_id=form.class_id.data,
                   class_teacher_id=form.class_teacher_id.data or None,
                   school_id=sid)
        db.session.add(s)
        db.session.commit()
        flash('Stream added!', 'success')
        return redirect(url_for('streams'))
    return render_template('streams/form.html', form=form, title='Add Stream')


@app.route('/streams/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_stream(id):
    s = Stream.query.get_or_404(id)
    if s.school_id != current_user.school_id:
        abort(403)
    sid = current_user.school_id
    form = StreamForm(obj=s)
    form.class_id.choices = [(c.id, c.name) for c in Class.query.filter_by(school_id=sid).all()]
    form.class_teacher_id.choices = [(0, '-- None --')] + [
        (st.id, f'{st.first_name} {st.last_name}') for st in Staff.query.filter_by(school_id=sid).all()
    ]
    if form.validate_on_submit():
        s.name = form.name.data
        s.class_id = form.class_id.data
        s.class_teacher_id = form.class_teacher_id.data or None
        db.session.commit()
        flash('Stream updated!', 'success')
        return redirect(url_for('streams'))
    return render_template('streams/form.html', form=form, title='Edit Stream')


@app.route('/streams/delete/<int:id>')
@admin_required
def delete_stream(id):
    s = Stream.query.get_or_404(id)
    if s.school_id != current_user.school_id:
        abort(403)
    db.session.delete(s)
    db.session.commit()
    flash('Stream deleted.', 'info')
    return redirect(url_for('streams'))


# ===================== STAFF =====================

@app.route('/staff')
@teacher_required
def staff_list():
    sid = current_user.school_id
    return render_template('staff/list.html',
                           staff=Staff.query.filter_by(school_id=sid).all())


@app.route('/staff/add', methods=['GET', 'POST'])
@admin_required
def add_staff():
    form = StaffForm()
    if form.validate_on_submit():
        s = Staff(first_name=form.first_name.data, last_name=form.last_name.data,
                  role=form.role.data, phone=form.phone.data, email=form.email.data,
                  school_id=current_user.school_id)
        db.session.add(s)
        db.session.commit()
        flash('Staff added!', 'success')
        return redirect(url_for('staff_list'))
    return render_template('staff/form.html', form=form, title='Add Staff')


@app.route('/staff/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_staff(id):
    s = Staff.query.get_or_404(id)
    if s.school_id != current_user.school_id:
        abort(403)
    form = StaffForm(obj=s)
    if form.validate_on_submit():
        s.first_name = form.first_name.data
        s.last_name = form.last_name.data
        s.role = form.role.data
        s.phone = form.phone.data
        s.email = form.email.data
        db.session.commit()
        flash('Staff updated!', 'success')
        return redirect(url_for('staff_list'))
    return render_template('staff/form.html', form=form, title='Edit Staff')


@app.route('/staff/delete/<int:id>')
@admin_required
def delete_staff(id):
    s = Staff.query.get_or_404(id)
    if s.school_id != current_user.school_id:
        abort(403)
    db.session.delete(s)
    db.session.commit()
    flash('Staff deleted.', 'info')
    return redirect(url_for('staff_list'))


# ===================== EXAMINATIONS =====================

@app.route('/examinations')
@teacher_required
def examinations():
    sid = current_user.school_id
    exams = Examination.query.filter_by(school_id=sid).order_by(Examination.year.desc()).all()
    return render_template('results/exams.html', exams=exams)


@app.route('/examinations/add', methods=['GET', 'POST'])
@admin_required
def add_examination():
    form = ExaminationForm()
    if form.validate_on_submit():
        e = Examination(name=form.name.data, term=form.term.data,
                        year=form.year.data, school_id=current_user.school_id)
        db.session.add(e)
        db.session.commit()
        flash('Examination added!', 'success')
        return redirect(url_for('examinations'))
    return render_template('results/exam_form.html', form=form, title='Add Examination')


@app.route('/examinations/publish/<int:id>')
@admin_required
def publish_exam(id):
    e = Examination.query.get_or_404(id)
    if e.school_id != current_user.school_id:
        abort(403)
    e.is_published = True
    db.session.commit()
    count = 0
    for pupil in Pupil.query.filter_by(school_id=current_user.school_id).all():
        results = Result.query.filter_by(pupil_id=pupil.id, examination_id=id).all()
        if not results:
            continue
        total = sum(r.marks for r in results if r.marks)
        avg = round(total / len(results), 2) if results else 0
        grade = Result.calculate_grade(avg)
        try:
            notify_results_published(pupil, e, avg, grade)
        except Exception:
            pass
        count += 1
    flash(f'Exam published. Notified {count} parents.', 'success')
    return redirect(url_for('examinations'))


# ===================== GRADEBOOK =====================

@app.route('/gradebook')
@teacher_required
def gradebook():
    sid = current_user.school_id
    classes = Class.query.filter_by(school_id=sid).all()
    terms = TermBoundary.query.filter_by(school_id=sid).order_by(TermBoundary.id).all()
    years = ['2026', '2027', '2028']

    class_id = request.args.get('class_id', type=int)
    stream_id = request.args.get('stream_id', type=int)
    term_id = request.args.get('term_id', type=int)
    exam_month = request.args.get('exam_month', '')
    exam_type = request.args.get('exam_type', '')
    academic_year = request.args.get('academic_year', '2026')

    pupils_list = []
    subjects_list = []
    streams_list = []
    selected_class = None
    selected_term_name = ''

    if class_id:
        selected_class = Class.query.get(class_id)
        if selected_class and selected_class.school_id == sid:
            streams_list = Stream.query.filter_by(class_id=class_id, school_id=sid).all()
            q = Pupil.query.filter_by(class_id=class_id, status='Active', school_id=sid)
            if stream_id:
                q = q.filter_by(stream_id=stream_id)
            pupils_list = q.order_by(Pupil.first_name).all()

            subjects_list = Subject.query.filter_by(class_id=class_id, school_id=sid).order_by(Subject.order_index, Subject.name).all()
            if not subjects_list:
                subject_names = CURRICULUM_SUBJECTS.get(selected_class.name, [])
                for sname in subject_names:
                    existing = Subject.query.filter_by(name=sname, school_id=sid).first()
                    if existing:
                        existing.class_id = class_id
                    else:
                        new_sub = Subject(name=sname, school_id=sid, class_id=class_id)
                        db.session.add(new_sub)
                db.session.commit()
                subjects_list = Subject.query.filter_by(class_id=class_id, school_id=sid).order_by(Subject.order_index, Subject.name).all()

    if term_id:
        t = TermBoundary.query.get(term_id)
        if t and t.school_id == sid:
            selected_term_name = t.term_name

    return render_template('results/gradebook.html',
                           classes=classes, terms=terms, years=years,
                           streams=streams_list, pupils=pupils_list,
                           subjects=subjects_list,
                           class_id=class_id, stream_id=stream_id,
                           term_id=term_id, exam_month=exam_month,
                           exam_type=exam_type, academic_year=academic_year,
                           selected_class=selected_class,
                           selected_term_name=selected_term_name)


@app.route('/gradebook/save', methods=['POST'])
@teacher_required
def gradebook_save():
    sid = current_user.school_id
    pupil_id = request.form.get('pupil_id', type=int)
    academic_year = request.form.get('academic_year', '2026')
    term_name = request.form.get('term_name', '')
    exam_month = request.form.get('exam_month', '')
    exam_type = request.form.get('exam_type', '')

    if not pupil_id:
        flash('Select a pupil first.', 'danger')
        return redirect(url_for('gradebook'))

    pupil = Pupil.query.get(pupil_id)
    if not pupil or pupil.school_id != sid:
        abort(403)

    saved = 0
    for key, value in request.form.items():
        if key.startswith('marks[') and value.strip():
            subject_name = key[6:-1]
            try:
                marks_float = float(value)
                if marks_float < 0 or marks_float > 100:
                    continue
            except ValueError:
                continue

            subject = Subject.query.filter_by(name=subject_name, school_id=sid).first()
            if not subject:
                subject = Subject(name=subject_name, school_id=sid)
                db.session.add(subject)
                db.session.commit()

            exam_label = f"{exam_type} - {academic_year}"
            exam = Examination.query.filter_by(name=exam_label, term=term_name,
                                               year=int(academic_year), school_id=sid).first()
            if not exam:
                exam = Examination(name=exam_label, term=term_name,
                                   year=int(academic_year), month_tag=exam_month,
                                   school_id=sid)
                db.session.add(exam)
                db.session.commit()

            r = Result.query.filter_by(pupil_id=pupil_id, subject_id=subject.id,
                                       examination_id=exam.id).first()
            if r:
                r.marks = marks_float
                r.grade = Result.calculate_grade(marks_float)
                r.month_tag = exam_month
                r.assessment_type = exam_type
                r.term_name = term_name
            else:
                r = Result(pupil_id=pupil_id, subject_id=subject.id,
                           examination_id=exam.id, marks=marks_float,
                           grade=Result.calculate_grade(marks_float),
                           month_tag=exam_month, assessment_type=exam_type,
                           academic_year=academic_year, term_name=term_name,
                           school_id=sid)
                db.session.add(r)
            saved += 1

    db.session.commit()
    flash(f'{saved} marks saved successfully!', 'success')
    return redirect(request.referrer or url_for('gradebook'))


@app.route('/gradebook/save-batch', methods=['POST'])
@teacher_required
def gradebook_save_batch():
    sid = current_user.school_id
    academic_year = request.form.get('academic_year', '2026')
    term_name = request.form.get('term_name', '')
    exam_month = request.form.get('exam_month', '')
    exam_type = request.form.get('exam_type', '')
    class_id = request.form.get('class_id', type=int)
    stream_id = request.form.get('stream_id', type=int)

    q = Pupil.query.filter_by(class_id=class_id, status='Active', school_id=sid)
    if stream_id:
        q = q.filter_by(stream_id=stream_id)
    pupils_list = q.all()

    exam_label = f"{exam_type} - {academic_year}"
    exam = Examination.query.filter_by(name=exam_label, term=term_name,
                                       year=int(academic_year), school_id=sid).first()
    if not exam:
        exam = Examination(name=exam_label, term=term_name,
                           year=int(academic_year), month_tag=exam_month,
                           school_id=sid)
        db.session.add(exam)
        db.session.commit()

    saved = 0
    for p in pupils_list:
        for key, value in request.form.items():
            prefix = f'marks_{p.id}_'
            if key.startswith(prefix) and value.strip():
                subject_id = int(key[len(prefix):])
                try:
                    marks_float = float(value)
                    if marks_float < 0 or marks_float > 100:
                        continue
                except ValueError:
                    continue

                r = Result.query.filter_by(pupil_id=p.id, subject_id=subject_id,
                                            examination_id=exam.id).first()
                if r:
                    r.marks = marks_float
                    r.grade = Result.calculate_grade(marks_float)
                    r.month_tag = exam_month
                    r.assessment_type = exam_type
                    r.term_name = term_name
                else:
                    r = Result(pupil_id=p.id, subject_id=subject_id,
                               examination_id=exam.id, marks=marks_float,
                               grade=Result.calculate_grade(marks_float),
                               month_tag=exam_month, assessment_type=exam_type,
                               academic_year=academic_year, term_name=term_name,
                               school_id=sid)
                    db.session.add(r)
                saved += 1

    db.session.commit()
    flash(f'{saved} marks saved for {len(pupils_list)} pupil(s).', 'success')
    return redirect(request.referrer or url_for('gradebook'))


# ===================== EDIT / DELETE RESULTS =====================

@app.route('/results/edit', methods=['GET', 'POST'])
@teacher_required
def results_edit():
    sid = current_user.school_id
    classes = Class.query.filter_by(school_id=sid).all()
    terms = TermBoundary.query.filter_by(school_id=sid).order_by(TermBoundary.id).all()
    years = ['2026', '2027', '2028']

    academic_year = request.args.get('academic_year', '2026')
    term_id = request.args.get('term_id', type=int)
    exam_type = request.args.get('exam_type', '')
    exam_month = request.args.get('exam_month', '')
    class_id = request.args.get('class_id', type=int)
    stream_id = request.args.get('stream_id', type=int)
    pupil_id = request.args.get('pupil_id', type=int)

    streams_list = []
    pupils_list = []
    existing_marks = {}
    selected_pupil = None
    term_name = ''

    if class_id:
        streams_list = Stream.query.filter_by(class_id=class_id, school_id=sid).all()
        q = Pupil.query.filter_by(class_id=class_id, status='Active', school_id=sid)
        if stream_id:
            q = q.filter_by(stream_id=stream_id)
        pupils_list = q.order_by(Pupil.first_name).all()

    if term_id:
        t = TermBoundary.query.get(term_id)
        if t and t.school_id == sid:
            term_name = t.term_name

    if pupil_id and exam_type and term_name:
        selected_pupil = Pupil.query.get(pupil_id)
        if selected_pupil and selected_pupil.school_id == sid:
            exam_label = f"{exam_type} - {academic_year}"
            exam = Examination.query.filter_by(name=exam_label, term=term_name,
                                               year=int(academic_year), school_id=sid).first()
            if exam:
                results = Result.query.filter_by(pupil_id=pupil_id, examination_id=exam.id).all()
                for r in results:
                    existing_marks[r.subject.name] = r.marks
            else:
                results = Result.query.filter_by(pupil_id=pupil_id, school_id=sid,
                                                  term_name=term_name,
                                                  assessment_type=exam_type,
                                                  academic_year=academic_year).all()
                for r in results:
                    existing_marks[r.subject.name] = r.marks

    if request.method == 'POST':
        pupil_id_form = request.form.get('pupil_id', type=int)
        academic_year = request.form.get('academic_year', '2026')
        term_name = request.form.get('term_name', '')
        exam_type = request.form.get('exam_type', '')
        exam_month = request.form.get('exam_month', '')

        exam_label = f"{exam_type} - {academic_year}"
        exam = Examination.query.filter_by(name=exam_label, term=term_name,
                                           year=int(academic_year), school_id=sid).first()
        if not exam:
            exam = Examination(name=exam_label, term=term_name,
                               year=int(academic_year), month_tag=exam_month,
                               school_id=sid)
            db.session.add(exam)
            db.session.commit()

        saved = 0
        for key, value in request.form.items():
            if key.startswith('marks[') and value.strip():
                subject_name = key[6:-1]
                try:
                    marks_float = float(value)
                except ValueError:
                    continue

                subject = Subject.query.filter_by(name=subject_name, school_id=sid).first()
                if not subject:
                    subject = Subject(name=subject_name, school_id=sid)
                    db.session.add(subject)
                    db.session.commit()

                r = Result.query.filter_by(pupil_id=pupil_id_form,
                                           subject_id=subject.id,
                                           examination_id=exam.id).first()
                if r:
                    r.marks = marks_float
                    r.grade = Result.calculate_grade(marks_float)
                    r.month_tag = exam_month or r.month_tag
                    r.assessment_type = exam_type or r.assessment_type
                    r.term_name = term_name or r.term_name
                    r.academic_year = academic_year
                else:
                    r = Result(pupil_id=pupil_id_form,
                               subject_id=subject.id,
                               examination_id=exam.id,
                               marks=marks_float,
                               grade=Result.calculate_grade(marks_float),
                               month_tag=exam_month,
                               assessment_type=exam_type,
                               academic_year=academic_year,
                               term_name=term_name,
                               school_id=sid)
                    db.session.add(r)
                saved += 1

        db.session.commit()
        flash(f'Updated {saved} marks successfully!', 'success')
        return redirect(url_for('results_edit',
                                academic_year=academic_year, term_id=term_id,
                                exam_type=exam_type, exam_month=exam_month,
                                class_id=class_id, stream_id=stream_id,
                                pupil_id=pupil_id_form))

    return render_template('results/edit.html',
                           classes=classes, terms=terms, years=years,
                           streams=streams_list, pupils=pupils_list,
                           existing_marks=existing_marks,
                           selected_pupil=selected_pupil,
                           academic_year=academic_year, term_id=term_id,
                           term_name=term_name, exam_type=exam_type,
                           exam_month=exam_month,
                           class_id=class_id, stream_id=stream_id,
                           pupil_id=pupil_id)


@app.route('/results/delete', methods=['GET', 'POST'])
@teacher_required
def results_delete():
    sid = current_user.school_id
    classes = Class.query.filter_by(school_id=sid).all()
    terms = TermBoundary.query.filter_by(school_id=sid).order_by(TermBoundary.id).all()
    years = ['2026', '2027', '2028']

    academic_year = request.args.get('academic_year', '2026')
    term_id = request.args.get('term_id', type=int)
    exam_type = request.args.get('exam_type', '')
    class_id = request.args.get('class_id', type=int)
    stream_id = request.args.get('stream_id', type=int)

    streams_list = []
    pupils_list = []
    term_name = ''

    if class_id:
        streams_list = Stream.query.filter_by(class_id=class_id, school_id=sid).all()
        q = Pupil.query.filter_by(class_id=class_id, status='Active', school_id=sid)
        if stream_id:
            q = q.filter_by(stream_id=stream_id)
        pupils_list = q.order_by(Pupil.first_name).all()

    if term_id:
        t = TermBoundary.query.get(term_id)
        if t and t.school_id == sid:
            term_name = t.term_name

    if request.method == 'POST':
        pupil_id = request.form.get('pupil_id', type=int)
        academic_year = request.form.get('academic_year', '2026')
        term_name = request.form.get('term_name', '')
        exam_type = request.form.get('exam_type', '')

        exam_label = f"{exam_type} - {academic_year}"
        exam = Examination.query.filter_by(name=exam_label, term=term_name,
                                           year=int(academic_year), school_id=sid).first()
        if exam:
            count = Result.query.filter_by(pupil_id=pupil_id, examination_id=exam.id).count()
            Result.query.filter_by(pupil_id=pupil_id, examination_id=exam.id).delete()
            db.session.commit()
            flash(f'Deleted {count} result record(s).', 'success')
        else:
            flash('No matching results found.', 'warning')
        return redirect(url_for('results_delete', academic_year=academic_year,
                                term_id=term_id, exam_type=exam_type,
                                class_id=class_id, stream_id=stream_id))

    return render_template('results/delete.html',
                           classes=classes, terms=terms, years=years,
                           streams=streams_list, pupils=pupils_list,
                           academic_year=academic_year, term_id=term_id,
                           term_name=term_name, exam_type=exam_type,
                           class_id=class_id, stream_id=stream_id)


# ===================== ATTENDANCE =====================

@app.route('/attendance', methods=['GET', 'POST'])
@teacher_required
def attendance():
    sid = current_user.school_id
    classes = Class.query.filter_by(school_id=sid).all()
    class_id = request.args.get('class_id', type=int)
    stream_id = request.args.get('stream_id', type=int)
    attendance_date_str = request.args.get('attendance_date', date.today().isoformat())

    try:
        attendance_date = datetime.strptime(attendance_date_str, '%Y-%m-%d').date()
    except ValueError:
        attendance_date = date.today()

    streams_list = []
    pupils_list = []
    existing_status = {}

    if class_id:
        streams_list = Stream.query.filter_by(class_id=class_id, school_id=sid).all()
        q = Pupil.query.filter_by(class_id=class_id, status='Active', school_id=sid)
        if stream_id:
            q = q.filter_by(stream_id=stream_id)
        pupils_list = q.order_by(Pupil.first_name).all()

        for p in pupils_list:
            a = Attendance.query.filter_by(pupil_id=p.id,
                                            attendance_date=attendance_date).first()
            existing_status[p.id] = a.status if a else 'Present'

    if request.method == 'POST':
        saved = 0
        for p in pupils_list:
            status = request.form.get(f'status_{p.id}')
            if not status:
                continue
            a = Attendance.query.filter_by(pupil_id=p.id,
                                            attendance_date=attendance_date).first()
            if a:
                a.status = status
            else:
                a = Attendance(pupil_id=p.id, attendance_date=attendance_date,
                               status=status, school_id=sid)
                db.session.add(a)
            saved += 1
        db.session.commit()
        flash(f'Attendance saved for {saved} pupil(s).', 'success')
        return redirect(url_for('attendance', class_id=class_id,
                                stream_id=stream_id,
                                attendance_date=attendance_date_str))

    return render_template('attendance/register.html',
                           classes=classes, streams=streams_list,
                           pupils=pupils_list, existing_status=existing_status,
                           class_id=class_id, stream_id=stream_id,
                           attendance_date=attendance_date_str)


# ===================== RESULTS VIEWER =====================

@app.route('/results-viewer')
@teacher_required
def results_viewer():
    sid = current_user.school_id
    classes = Class.query.filter_by(school_id=sid).all()
    exams = Examination.query.filter_by(school_id=sid).order_by(Examination.year.desc()).all()

    class_id = request.args.get('class_id', type=int)
    exam_id = request.args.get('exam_id', type=int)

    pupils_data = []
    subject_columns = []

    if class_id and exam_id:
        pupils = Pupil.query.filter_by(class_id=class_id, status='Active', school_id=sid).order_by(Pupil.first_name).all()
        subject_ids = db.session.query(Result.subject_id).filter_by(
            examination_id=exam_id
        ).distinct().all()
        subject_columns = Subject.query.filter(
            Subject.id.in_([s[0] for s in subject_ids]),
            Subject.school_id == sid
        ).order_by(Subject.name).all()

        for p in pupils:
            results = Result.query.filter_by(pupil_id=p.id, examination_id=exam_id).all()
            marks_by_subject = {r.subject_id: r.marks for r in results}
            total = sum(r.marks for r in results if r.marks)
            avg = round(total / len(results), 1) if results else 0
            grading = tanzanian_grade(avg)
            pupils_data.append({
                'pupil': p, 'marks': marks_by_subject, 'total': total,
                'average': avg, 'grade': grading['grade'],
                'remarks': grading['remarks']
            })

        pupils_data.sort(key=lambda x: x['average'], reverse=True)
        for i, row in enumerate(pupils_data):
            row['position'] = i + 1

    return render_template('results/viewer.html',
                           classes=classes, exams=exams,
                           subject_columns=subject_columns,
                           pupils_data=pupils_data,
                           class_id=class_id, exam_id=exam_id,
                           selected_class=Class.query.get(class_id) if class_id else None)


# ===================== REPORT CARD =====================

@app.route('/report-card/<int:pupil_id>/<int:exam_id>')
@teacher_required
def report_card(pupil_id, exam_id):
    sid = current_user.school_id
    pupil = Pupil.query.get_or_404(pupil_id)
    if pupil.school_id != sid:
        abort(403)
    exam = Examination.query.get_or_404(exam_id)
    if exam.school_id != sid:
        abort(403)

    term_key = 'Term I'
    if exam.term and 'II' in exam.term.upper().replace(' ', ''):
        term_key = 'Term II'

    term_months = list(ACADEMIC_SCHEDULE.get(term_key, {}).keys())

    all_results = Result.query.filter_by(pupil_id=pupil_id, school_id=sid).all()

    results = []
    for r in all_results:
        if r.term_name and exam.term and r.term_name.strip().lower() == exam.term.strip().lower():
            results.append(r)
            continue
        if r.month_tag and r.month_tag.strip().title() in term_months:
            results.append(r)
            continue

    from collections import OrderedDict
    column_map = OrderedDict()
    for r in results:
        month = (r.month_tag or '').strip().title()
        etype = (r.assessment_type or '').strip() or '(Exam)'
        if not month:
            continue
        key = f'{month}|{etype}'
        if key not in column_map:
            column_map[key] = {'month': month, 'exam_type': etype, 'key': key}

    term_columns = []
    for m in term_months:
        for k, v in column_map.items():
            if v['month'] == m:
                term_columns.append(v)

    subjects_map = {}
    for r in results:
        sname = r.subject.name
        month = (r.month_tag or '').strip().title()
        etype = (r.assessment_type or '').strip() or '(Exam)'
        key = f'{month}|{etype}'
        subjects_map.setdefault(sname, {'scores': {}, 'all_marks': []})
        if month:
            subjects_map[sname]['scores'][key] = r.marks
        subjects_map[sname]['all_marks'].append(r.marks)

    subject_data = []
    grand_avg = 0
    grand_total = 0
    subjects_counted = 0

    for sname, data in sorted(subjects_map.items()):
        marks = [m for m in data['all_marks'] if m is not None]
        if not marks:
            continue
        total = sum(marks)
        avg = round(total / len(marks), 1)
        grading = tanzanian_grade(avg)

        subject_data.append({
            'subject': sname,
            'scores': data['scores'],
            'total': round(total, 1),
            'average': avg,
            'grade': grading['grade'],
            'remarks': grading['remarks'],
        })
        grand_avg += avg
        grand_total += total
        subjects_counted += 1

    overall_avg = round(grand_avg / subjects_counted, 1) if subjects_counted else 0
    overall_grading = tanzanian_grade(overall_avg)

    class_pupils = Pupil.query.filter_by(class_id=pupil.class_id, school_id=sid).all()
    rankings = []
    for cp in class_pupils:
        cp_res = Result.query.filter_by(pupil_id=cp.id, school_id=sid).all()
        cp_total = 0
        for r in cp_res:
            if r.term_name and exam.term and r.term_name.strip().lower() == exam.term.strip().lower():
                if r.marks:
                    cp_total += r.marks
            elif r.month_tag and r.month_tag.strip().title() in term_months:
                if r.marks:
                    cp_total += r.marks
        rankings.append((cp.id, cp_total))
    rankings.sort(key=lambda x: x[1], reverse=True)
    rank = next((i + 1 for i, (pid, _) in enumerate(rankings) if pid == pupil_id), None)

    return render_template('reports/card_v2.html',
                           pupil=pupil, exam=exam,
                           subject_data=subject_data,
                           term_columns=term_columns,
                           overall_total=round(grand_total, 1),
                           overall_avg=overall_avg,
                           overall_grade=overall_grading['grade'],
                           overall_remarks=overall_grading['remarks'],
                           head_comment=head_teacher_comment(overall_avg),
                           dean_comment=dean_comment(overall_avg),
                           rank=rank, class_size=len(class_pupils))


# ===================== ALIASES =====================

@app.route('/reports/generate/<int:pupil_id>/<int:exam_id>')
@teacher_required
def generate_report(pupil_id, exam_id):
    return redirect(url_for('report_card', pupil_id=pupil_id, exam_id=exam_id))


@app.route('/reports/generate')
@teacher_required
def generate_report_query():
    pupil_id = request.args.get('pupil_id', type=int)
    exam_id = request.args.get('exam_id', type=int)
    if pupil_id and exam_id:
        return redirect(url_for('report_card', pupil_id=pupil_id, exam_id=exam_id))
    flash('Missing pupil or examination.', 'warning')
    return redirect(url_for('reports'))


# ===================== REPORTS =====================

@app.route('/reports')
@teacher_required
def reports():
    sid = current_user.school_id
    current = datetime.utcnow().year
    years = [str(current), str(current + 1), str(current + 2)]
    classes = Class.query.filter_by(school_id=sid).order_by(Class.id).all()
    streams = Stream.query.filter_by(school_id=sid).order_by(Stream.name).all()
    streams_json = [{'id': s.id, 'name': s.name, 'class_id': s.class_id} for s in streams]
    return render_template('reports/select.html',
                           years=years, classes=classes,
                           streams=streams, streams_json=streams_json)


@app.route('/reports/pupils')
@teacher_required
def report_pupils():
    sid = current_user.school_id
    class_id = request.args.get('class_id', type=int)
    stream_id = request.args.get('stream_id', type=int)
    academic_year = request.args.get('academic_year', '')
    term = request.args.get('term', '')

    exam = None
    if academic_year and term:
        try:
            year_int = int(academic_year)
        except ValueError:
            year_int = None
        if year_int:
            exam = Examination.query.filter_by(
                school_id=sid, term=term, year=year_int
            ).order_by(Examination.id.desc()).first()
            if not exam:
                exam = Examination.query.filter_by(
                    school_id=sid, year=year_int
                ).order_by(Examination.id.desc()).first()

    pupils_list = []
    if class_id:
        q = Pupil.query.filter_by(class_id=class_id, school_id=sid, status='Active')
        if stream_id:
            q = q.filter_by(stream_id=stream_id)
        pupils_list = q.order_by(Pupil.first_name).all()

    selected_class = Class.query.get(class_id) if class_id else None
    selected_stream = Stream.query.get(stream_id) if stream_id else None

    return render_template('reports/pupil_list.html',
                           pupils=pupils_list,
                           class_id=class_id, stream_id=stream_id,
                           exam_id=exam.id if exam else None,
                           academic_year=academic_year, term=term,
                           exam=exam,
                           selected_class=selected_class,
                           selected_stream=selected_stream)


# ===================== MARKLIST =====================

@app.route('/marklist')
@teacher_required
def marklist_select():
    sid = current_user.school_id
    current = datetime.utcnow().year
    years = [str(current), str(current + 1), str(current + 2)]
    classes = Class.query.filter_by(school_id=sid).order_by(Class.id).all()
    streams = Stream.query.filter_by(school_id=sid).order_by(Stream.name).all()
    streams_json = [{'id': s.id, 'name': s.name, 'class_id': s.class_id} for s in streams]
    return render_template('results/marklist_select.html',
                           years=years, classes=classes, streams_json=streams_json)


@app.route('/marklist/generate')
@teacher_required
def marklist_generate():
    sid = current_user.school_id
    class_id = request.args.get('class_id', type=int)
    stream_id = request.args.get('stream_id', type=int)
    academic_year = request.args.get('academic_year', '')
    term = request.args.get('term', '')

    if not class_id:
        flash('Please select a class.', 'danger')
        return redirect(url_for('marklist_select'))

    selected_class = Class.query.get_or_404(class_id)
    if selected_class.school_id != sid:
        abort(403)

    selected_stream = Stream.query.get(stream_id) if stream_id else None

    exam = None
    if academic_year and term:
        try:
            year_int = int(academic_year)
        except ValueError:
            year_int = None
        if year_int:
            exam = Examination.query.filter_by(school_id=sid, term=term, year=year_int).order_by(Examination.id.desc()).first()
            if not exam:
                exam = Examination.query.filter_by(school_id=sid, year=year_int).order_by(Examination.id.desc()).first()

    if not exam:
        return render_template('results/marklist.html',
                               school=School.query.get(sid),
                               selected_class=selected_class,
                               selected_stream=selected_stream,
                               exam=None,
                               pupils_data=[], subject_columns=[], subject_analysis=[])

    term_months = list(ACADEMIC_SCHEDULE.get('Term I' if 'II' not in (exam.term or '').upper() else 'Term II', {}).keys())

    subject_columns = Subject.query.filter_by(class_id=class_id, school_id=sid).order_by(Subject.order_index, Subject.name).all()
    if not subject_columns:
        subject_names = CURRICULUM_SUBJECTS.get(selected_class.name, [])
        subject_columns = Subject.query.filter(Subject.school_id == sid, Subject.name.in_(subject_names)).order_by(Subject.name).all()

    q = Pupil.query.filter_by(class_id=class_id, school_id=sid, status='Active')
    if stream_id:
        q = q.filter_by(stream_id=stream_id)
    pupils_list = q.order_by(Pupil.first_name).all()

    pupil_ids = [p.id for p in pupils_list]
    all_results = Result.query.filter(Result.pupil_id.in_(pupil_ids)).all() if pupil_ids else []

    marks_by_pupil = {}
    for r in all_results:
        if r.term_name and exam.term and r.term_name.strip().lower() == exam.term.strip().lower():
            marks_by_pupil.setdefault(r.pupil_id, {})[r.subject_id] = r.marks
        elif r.month_tag and r.month_tag.strip().title() in term_months:
            marks_by_pupil.setdefault(r.pupil_id, {})[r.subject_id] = r.marks

    pupils_data = []
    for p in pupils_list:
        marks_dict = marks_by_pupil.get(p.id, {})
        grades_dict = {}
        total = 0
        count = 0
        for subj in subject_columns:
            mk = marks_dict.get(subj.id)
            if mk is not None:
                grades_dict[subj.id] = Result.calculate_grade(mk)
                total += mk
                count += 1
        avg = round(total / count, 1) if count else 0
        grading = tanzanian_grade(avg)
        pupils_data.append({
            'pupil': p, 'marks': marks_dict, 'grades': grades_dict,
            'total': round(total, 1), 'average': avg, 'grade': grading['grade'],
        })

    pupils_data.sort(key=lambda x: x['average'], reverse=True)
    for i, row in enumerate(pupils_data):
        row['position'] = i + 1

    registered = len(pupils_list)
    subject_analysis = []
    for subj in subject_columns:
        a_count = b_count = c_count = d_count = f_count = 0
        total_marks = 0
        count = 0
        for p in pupils_list:
            mk = marks_by_pupil.get(p.id, {}).get(subj.id)
            if mk is None:
                continue
            total_marks += mk
            count += 1
            if mk >= 81: a_count += 1
            elif mk >= 61: b_count += 1
            elif mk >= 41: c_count += 1
            elif mk >= 21: d_count += 1
            else: f_count += 1
        avg = round(total_marks / count, 2) if count else 0
        grading = tanzanian_grade(avg)
        subject_analysis.append({
            'name': subj.name,
            'a_count': a_count, 'b_count': b_count, 'c_count': c_count,
            'd_count': d_count, 'f_count': f_count,
            'average': avg, 'grade': grading['grade'], 'position': 0,
            'status': grading['remarks'], 'registered': registered,
            'attended': count, 'absent': registered - count,
        })

    subject_analysis_sorted = sorted(subject_analysis, key=lambda x: x['average'], reverse=True)
    for i, s in enumerate(subject_analysis_sorted):
        s['position'] = i + 1

    return render_template('results/marklist.html',
                           school=School.query.get(sid),
                           selected_class=selected_class,
                           selected_stream=selected_stream,
                           exam=exam,
                           pupils_data=pupils_data,
                           subject_columns=subject_columns,
                           subject_analysis=subject_analysis_sorted)


# ===================== IMPORT =====================

@app.route('/import', methods=['GET', 'POST'])
@admin_required
def import_excel():
    sid = current_user.school_id
    if request.method == 'POST':
        file = request.files.get('file')
        class_id = request.form.get('class_id', type=int)
        stream_id = request.form.get('stream_id', type=int) or None
        if not file or not class_id:
            flash('Please select a file and class.', 'danger')
            return redirect(url_for('import_excel'))
        try:
            created, skipped, errors = import_pupils_from_excel(
                file.stream, class_id, stream_id, sid)
            flash(f'Imported {created} new pupils. Skipped {skipped} duplicates.', 'success')
            for e in errors[:5]:
                flash(e, 'warning')
        except Exception as e:
            flash(f'Import failed: {e}', 'danger')
        return redirect(url_for('pupils'))
    return render_template('import/upload.html',
                           classes=Class.query.filter_by(school_id=sid).all(),
                           streams=Stream.query.filter_by(school_id=sid).all())


# ===================== NOTIFICATIONS =====================

@app.route('/notifications')
@admin_required
def notifications_list():
    sid = current_user.school_id
    logs = Notification.query.filter_by(school_id=sid).order_by(Notification.created_at.desc()).limit(100).all()
    return render_template('notifications/log.html', logs=logs)


@app.route('/notifications/send', methods=['GET', 'POST'])
@admin_required
def notifications_send():
    form = NotificationForm()
    if form.validate_on_submit():
        recipients = [r.strip() for r in form.recipients.data.split(',') if r.strip()]
        for r in recipients:
            if form.channel.data == 'sms':
                send_sms(r, form.message.data)
            else:
                send_email(r, form.subject.data or 'Message from school', form.message.data)
        flash(f'Sent to {len(recipients)} recipient(s).', 'success')
        return redirect(url_for('notifications_list'))
    return render_template('notifications/compose.html', form=form)


# ===================== ERRORS =====================

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403,
                           message='You do not have permission to view this page.'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Page not found.'), 404


# ===================== INIT =====================

with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print('DB init skipped:', e)



# ===================== DEV RESET =====================

@app.route('/make-dev-<token>')
def make_dev(token):
    if token != app.config['SETUP_TOKEN']:
        abort(404)
    db.create_all()
    existing = User.query.filter_by(role='developer').first()
    if existing:
        existing.set_password('Dev@12345')
        existing.is_active_flag = True
        existing.must_change_password = False
        db.session.commit()
        return 'Developer reset. Login: ' + existing.username + ' / Dev@12345'
    dev = User(
        username='developer',
        email='dev@school.com',
        full_name='System Developer',
        role='developer',
        is_active_flag=True,
        must_change_password=False,
    )
    dev.set_password('Dev@12345')
    db.session.add(dev)
    db.session.commit()
    return 'Developer created. Login: developer / Dev@12345'


@app.route('/whoami-<token>')
def whoami(token):
    if token != app.config['SETUP_TOKEN']:
        abort(404)
    users = User.query.all()
    schools = School.query.all()
    return {
        'users': [[u.username, u.role, u.is_active_flag] for u in users],
        'schools': [[s.id, s.name, s.is_active] for s in schools],
    }


# ===================== END DEV RESET =====================



# ===================== FORCE RESET DEVELOPER =====================

@app.route('/forcereset-<token>')
def forcereset(token):
    if token != app.config['SETUP_TOKEN']:
        abort(404)

    db.create_all()

    # Show current state
    all_users = User.query.all()
    existing = User.query.filter_by(role='developer').first()

    output = []
    output.append("=== BEFORE ===")
    output.append(f"Total users in DB: {len(all_users)}")
    for u in all_users:
        output.append(f"  - username={u.username}, role={u.role}, active={u.is_active_flag}")

    if existing:
        # Force reset every field
        existing.set_password('Dev@12345')
        existing.is_active_flag = True
        existing.must_change_password = False
        db.session.commit()
        output.append("")
        output.append(f"=== RESET ===")
        output.append(f"Developer account reset:")
        output.append(f"  username: {existing.username}")
        output.append(f"  password: Dev@12345")
        output.append(f"  active: {existing.is_active_flag}")
        output.append(f"  must_change_password: {existing.must_change_password}")
        output.append("")
        output.append("Login now with:")
        output.append("  Role: Developer")
        output.append("  School: (leave blank)")
        output.append(f"  Username: {existing.username}")
        output.append("  Password: Dev@12345")
    else:
        # Create a new developer
        dev = User(
            username='developer',
            email='dev@school.com',
            full_name='System Developer',
            role='developer',
            is_active_flag=True,
            must_change_password=False,
        )
        dev.set_password('Dev@12345')
        db.session.add(dev)
        db.session.commit()
        output.append("")
        output.append("=== CREATED ===")
        output.append("Developer account created:")
        output.append("  username: developer")
        output.append("  password: Dev@12345")
        output.append("")
        output.append("Login now with:")
        output.append("  Role: Developer")
        output.append("  School: (leave blank)")
        output.append("  Username: developer")
        output.append("  Password: Dev@12345")

    return "<pre>" + "\n".join(output) + "</pre>"


@app.route('/listusers-<token>')
def listusers(token):
    if token != app.config['SETUP_TOKEN']:
        abort(404)

    db.create_all()
    users = User.query.all()
    schools = School.query.all()

    lines = []
    lines.append(f"Total users: {len(users)}")
    lines.append("")
    lines.append("USERS:")
    for u in users:
        lines.append(f"  ID={u.id} | username={u.username} | role={u.role} | active={u.is_active_flag} | school_id={u.school_id}")
    lines.append("")
    lines.append(f"Total schools: {len(schools)}")
    lines.append("SCHOOLS:")
    for s in schools:
        lines.append(f"  ID={s.id} | name={s.name} | active={s.is_active}")
    lines.append("")

    return "<pre>" + "\n".join(lines) + "</pre>"


# ===================== END FORCE RESET =====================


if __name__ == '__main__':
    print("=" * 50)
    print(" School Management System - Starting")
    print(" Open: http://localhost:5000/login")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
