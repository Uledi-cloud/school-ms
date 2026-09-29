from flask import (Flask, render_template, redirect, url_for, flash,
                   request, abort, Blueprint)
from flask_login import LoginManager, login_required, current_user
from datetime import datetime

from config import Config
from models import (db, User, Class, Stream, Staff, Pupil, Examination,
                    Subject, Result, Notification, AuditLog)
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


# ---------------- Parent portal ----------------
parent_bp = Blueprint('parent', __name__, url_prefix='/parent')


@parent_bp.route('/')
@parent_required
def dashboard():
    pupil = Pupil.query.get(current_user.pupil_id) if current_user.pupil_id else None
    exams = Examination.query.filter_by(is_published=True).order_by(
        Examination.year.desc()).all()
    return render_template('parent/dashboard.html', pupil=pupil, exams=exams)


@parent_bp.route('/child/<int:pupil_id>/<int:exam_id>')
@parent_required
def child_view(pupil_id, exam_id):
    if current_user.pupil_id != pupil_id:
        abort(403)
    pupil = Pupil.query.get_or_404(pupil_id)
    exam = Examination.query.get_or_404(exam_id)
    if not exam.is_published:
        abort(403)
    results = Result.query.filter_by(pupil_id=pupil_id, examination_id=exam_id).all()
    total = sum(r.marks for r in results if r.marks)
    avg = round(total / len(results), 2) if results else 0
    grade = Result.calculate_grade(avg)
    return render_template('parent/child_view.html', pupil=pupil, exam=exam,
                           results=results, total=total, average=avg,
                           overall_grade=grade)


app.register_blueprint(parent_bp)


# ---------------- Seed data + setup ----------------
def seed_data():
    if Subject.query.count() == 0:
        for s in ['Mathematics', 'English', 'Kiswahili', 'Science',
                  'Social Studies', 'Religious Education', 'ICT']:
            db.session.add(Subject(name=s))
        db.session.commit()

    if Class.query.count() == 0:
        for name, level in [
            ('Baby Class', 'Pre-Primary'), ('Middle Class', 'Pre-Primary'),
            ('Top Class', 'Pre-Primary'), ('Standard One', 'Primary'),
            ('Standard Two', 'Primary'), ('Standard Three', 'Primary'),
            ('Standard Four', 'Primary'), ('Standard Five', 'Primary'),
            ('Standard Six', 'Primary'), ('Standard Seven', 'Primary'),
        ]:
            db.session.add(Class(name=name, level=level))
        db.session.commit()


@app.route('/setup-db-<token>')
def setup_db(token):
    if token != app.config['SETUP_TOKEN']:
        abort(404)
    db.create_all()
    seed_data()
    if User.query.count() == 0:
        admin = User(username='admin', email='admin@school.com', role='admin')
        admin.set_password('ChangeMe123!')
        db.session.add(admin)
        db.session.commit()
        return 'DB ready. Login with admin / ChangeMe123!'
    return 'DB already initialized.'


def log_action(action, detail=''):
    if current_user.is_authenticated:
        db.session.add(AuditLog(user_id=current_user.id, action=action,
                                detail=detail, ip=request.remote_addr or ''))
        db.session.commit()


# ---------------- Home ----------------
@app.route('/')
@login_required
def index():
    stats = {
        'pupils': Pupil.query.count(),
        'classes': Class.query.count(),
        'streams': Stream.query.count(),
        'staff': Staff.query.count(),
        'exams': Examination.query.count(),
        'users': User.query.count(),
    }
    recent = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
    return render_template('index.html', stats=stats, recent=recent)


# ---------------- Pupils ----------------
@app.route('/pupils')
@teacher_required
def pupils():
    q = Pupil.query
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
                           classes=Class.query.all(), class_id=class_id,
                           stream_id=stream_id, search=search)


@app.route('/pupils/add', methods=['GET', 'POST'])
@teacher_required
def add_pupil():
    form = PupilForm()
    form.class_id.choices = [(c.id, c.name) for c in Class.query.all()]
    form.stream_id.choices = [(0, '-- None --')] + [
        (s.id, f'{s.class_.name} - {s.name}') for s in Stream.query.all()
    ]
    if form.validate_on_submit():
        p = Pupil(
            first_name=form.first_name.data, last_name=form.last_name.data,
            admission_no=form.admission_no.data, gender=form.gender.data,
            date_of_birth=form.date_of_birth.data, class_id=form.class_id.data,
            stream_id=form.stream_id.data or None,
            parent_name=form.parent_name.data, parent_phone=form.parent_phone.data,
            parent_email=form.parent_email.data, address=form.address.data,
        )
        db.session.add(p)
        db.session.commit()
        log_action('create_pupil', p.full_name)
        flash('Pupil registered!', 'success')
        return redirect(url_for('pupils'))
    return render_template('pupils/form.html', form=form, title='Register Pupil')


@app.route('/pupils/edit/<int:id>', methods=['GET', 'POST'])
@teacher_required
def edit_pupil(id):
    p = Pupil.query.get_or_404(id)
    form = PupilForm(obj=p)
    form.class_id.choices = [(c.id, c.name) for c in Class.query.all()]
    form.stream_id.choices = [(0, '-- None --')] + [
        (s.id, f'{s.class_.name} - {s.name}') for s in Stream.query.all()
    ]
    if form.validate_on_submit():
        p.first_name = form.first_name.data
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
    return render_template('pupils/form.html', form=form, title='Edit Pupil')


@app.route('/pupils/delete/<int:id>')
@teacher_required
def delete_pupil(id):
    p = Pupil.query.get_or_404(id)
    db.session.delete(p)
    db.session.commit()
    flash('Pupil deleted.', 'info')
    return redirect(url_for('pupils'))


# ---------------- Classes ----------------
@app.route('/classes')
@teacher_required
def classes():
    return render_template('classes/list.html', classes=Class.query.all())


@app.route('/classes/add', methods=['GET', 'POST'])
@admin_required
def add_class():
    form = ClassForm()
    if form.validate_on_submit():
        db.session.add(Class(name=form.name.data, level=form.level.data))
        db.session.commit()
        flash('Class added!', 'success')
        return redirect(url_for('classes'))
    return render_template('classes/form.html', form=form, title='Add Class')


@app.route('/classes/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_class(id):
    c = Class.query.get_or_404(id)
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
    db.session.delete(c)
    db.session.commit()
    flash('Class deleted.', 'info')
    return redirect(url_for('classes'))


# ---------------- Streams ----------------
@app.route('/streams')
@teacher_required
def streams():
    return render_template('streams/list.html', streams=Stream.query.all())


@app.route('/streams/add', methods=['GET', 'POST'])
@admin_required
def add_stream():
    form = StreamForm()
    form.class_id.choices = [(c.id, c.name) for c in Class.query.all()]
    form.class_teacher_id.choices = [(0, '-- None --')] + [
        (s.id, f'{s.first_name} {s.last_name}') for s in Staff.query.all()
    ]
    if form.validate_on_submit():
        s = Stream(name=form.name.data, class_id=form.class_id.data,
                   class_teacher_id=form.class_teacher_id.data or None)
        db.session.add(s)
        db.session.commit()
        flash('Stream added!', 'success')
        return redirect(url_for('streams'))
    return render_template('streams/form.html', form=form, title='Add Stream')


@app.route('/streams/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_stream(id):
    s = Stream.query.get_or_404(id)
    form = StreamForm(obj=s)
    form.class_id.choices = [(c.id, c.name) for c in Class.query.all()]
    form.class_teacher_id.choices = [(0, '-- None --')] + [
        (st.id, f'{st.first_name} {st.last_name}') for st in Staff.query.all()
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
    db.session.delete(s)
    db.session.commit()
    flash('Stream deleted.', 'info')
    return redirect(url_for('streams'))


# ---------------- Staff ----------------
@app.route('/staff')
@teacher_required
def staff_list():
    return render_template('staff/list.html', staff=Staff.query.all())


@app.route('/staff/add', methods=['GET', 'POST'])
@admin_required
def add_staff():
    form = StaffForm()
    if form.validate_on_submit():
        s = Staff(first_name=form.first_name.data, last_name=form.last_name.data,
                  role=form.role.data, phone=form.phone.data, email=form.email.data)
        db.session.add(s)
        db.session.commit()
        flash('Staff added!', 'success')
        return redirect(url_for('staff_list'))
    return render_template('staff/form.html', form=form, title='Add Staff')


@app.route('/staff/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_staff(id):
    s = Staff.query.get_or_404(id)
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
    db.session.delete(s)
    db.session.commit()
    flash('Staff deleted.', 'info')
    return redirect(url_for('staff_list'))


# ---------------- Examinations ----------------
@app.route('/examinations')
@teacher_required
def examinations():
    exams = Examination.query.order_by(Examination.year.desc()).all()
    return render_template('results/exams.html', exams=exams)


@app.route('/examinations/add', methods=['GET', 'POST'])
@admin_required
def add_examination():
    form = ExaminationForm()
    if form.validate_on_submit():
        e = Examination(name=form.name.data, term=form.term.data, year=form.year.data)
        db.session.add(e)
        db.session.commit()
        flash('Examination added!', 'success')
        return redirect(url_for('examinations'))
    return render_template('results/exam_form.html', form=form, title='Add Examination')


@app.route('/examinations/publish/<int:id>')
@admin_required
def publish_exam(id):
    e = Examination.query.get_or_404(id)
    e.is_published = True
    db.session.commit()

    # Notify parents
    subjects = Subject.query.all()
    count = 0
    for pupil in Pupil.query.all():
        results = Result.query.filter_by(pupil_id=pupil.id, examination_id=id).all()
        if not results:
            continue
        total = sum(r.marks for r in results if r.marks)
        avg = round(total / len(results), 2) if results else 0
        grade = Result.calculate_grade(avg)
        notify_results_published(pupil, e, avg, grade)
        count += 1
    flash(f'Exam published. Notified {count} parents.', 'success')
    return redirect(url_for('examinations'))


# ---------------- Results entry ----------------
@app.route('/results/entry', methods=['GET', 'POST'])
@teacher_required
def result_entry():
    classes = Class.query.all()
    exams = Examination.query.all()
    subjects = Subject.query.all()

    class_id = request.args.get('class_id', type=int)
    stream_id = request.args.get('stream_id', type=int)
    exam_id = request.args.get('exam_id', type=int)
    subject_id = request.args.get('subject_id', type=int)

    pupils_list = []
    streams_list = []
    if class_id:
        streams_list = Stream.query.filter_by(class_id=class_id).all()
        q = Pupil.query.filter_by(class_id=class_id)
        if stream_id:
            q = q.filter_by(stream_id=stream_id)
        pupils_list = q.order_by(Pupil.first_name).all()

    existing = {}
    if exam_id and subject_id:
        for r in Result.query.filter_by(examination_id=exam_id, subject_id=subject_id).all():
            existing[r.pupil_id] = r.marks

    if request.method == 'POST':
        exam_id = int(request.form.get('exam_id'))
        subject_id = int(request.form.get('subject_id'))
        for p in pupils_list:
            mark = request.form.get(f'mark_{p.id}')
            if mark == '' or mark is None:
                continue
            mark = float(mark)
            r = Result.query.filter_by(pupil_id=p.id, subject_id=subject_id,
                                       examination_id=exam_id).first()
            if r:
                r.marks = mark
                r.grade = Result.calculate_grade(mark)
            else:
                r = Result(pupil_id=p.id, subject_id=subject_id,
                           examination_id=exam_id, marks=mark,
                           grade=Result.calculate_grade(mark))
                db.session.add(r)
        db.session.commit()
        flash('Results saved!', 'success')
        return redirect(url_for('result_entry', class_id=class_id,
                                stream_id=stream_id, exam_id=exam_id,
                                subject_id=subject_id))

    return render_template('results/entry.html', classes=classes,
                           streams=streams_list, exams=exams, subjects=subjects,
                           pupils=pupils_list, class_id=class_id,
                           stream_id=stream_id, exam_id=exam_id,
                           subject_id=subject_id, existing=existing)


# ---------------- Report card ----------------
@app.route('/reports')
@teacher_required
def reports():
    return render_template('reports/select.html',
                           classes=Class.query.all(),
                           exams=Examination.query.all())


@app.route('/reports/pupils')
@teacher_required
def report_pupils():
    class_id = request.args.get('class_id', type=int)
    stream_id = request.args.get('stream_id', type=int)
    exam_id = request.args.get('exam_id', type=int)
    pupils_list = []
    if class_id:
        q = Pupil.query.filter_by(class_id=class_id)
        if stream_id:
            q = q.filter_by(stream_id=stream_id)
        pupils_list = q.order_by(Pupil.first_name).all()
    return render_template('reports/pupil_list.html', pupils=pupils_list,
                           class_id=class_id, stream_id=stream_id, exam_id=exam_id)


@app.route('/reports/generate/<int:pupil_id>/<int:exam_id>')
@teacher_required
def generate_report(pupil_id, exam_id):
    pupil = Pupil.query.get_or_404(pupil_id)
    exam = Examination.query.get_or_404(exam_id)
    results = Result.query.filter_by(pupil_id=pupil_id, examination_id=exam_id).all()
    total = sum(r.marks for r in results if r.marks)
    avg = round(total / len(results), 2) if results else 0
    overall_grade = Result.calculate_grade(avg)

    class_pupils = Pupil.query.filter_by(class_id=pupil.class_id).all()
    rankings = []
    for cp in class_pupils:
        cp_res = Result.query.filter_by(pupil_id=cp.id, examination_id=exam_id).all()
        cp_total = sum(r.marks for r in cp_res if r.marks)
        rankings.append((cp.id, cp_total))
    rankings.sort(key=lambda x: x[1], reverse=True)
    rank = next((i + 1 for i, (pid, _) in enumerate(rankings) if pid == pupil_id), None)

    return render_template('reports/card.html', pupil=pupil, exam=exam,
                           results=results, total=total, average=avg,
                           overall_grade=overall_grade, rank=rank,
                           class_size=len(class_pupils))


# ---------------- Excel Import ----------------
@app.route('/import', methods=['GET', 'POST'])
@admin_required
def import_excel():
    if request.method == 'POST':
        file = request.files.get('file')
        class_id = request.form.get('class_id', type=int)
        stream_id = request.form.get('stream_id', type=int) or None
        if not file or not class_id:
            flash('Please select a file and class.', 'danger')
            return redirect(url_for('import_excel'))
        try:
            created, skipped, errors = import_pupils_from_excel(
                file.stream, class_id, stream_id)
            flash(f'Imported {created} new pupils. Skipped {skipped} duplicates.', 'success')
            for e in errors[:5]:
                flash(e, 'warning')
        except Exception as e:
            flash(f'Import failed: {e}', 'danger')
        return redirect(url_for('pupils'))
    return render_template('import/upload.html', classes=Class.query.all(),
                           streams=Stream.query.all())


# ---------------- Notifications ----------------
@app.route('/notifications')
@admin_required
def notifications_list():
    logs = Notification.query.order_by(Notification.created_at.desc()).limit(100).all()
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


# ---------------- Errors ----------------
@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403,
                           message='You do not have permission to view this page.'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404,
                           message='Page not found.'), 404


# ---------------- Init on first run ----------------
with app.app_context():
    try:
        db.create_all()
        seed_data()
    except Exception as e:
        print('DB init skipped:', e)


if __name__ == '__main__':
    app.run(debug=True, port=5000)