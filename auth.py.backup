import re
import os
import uuid
import secrets
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, jsonify)
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from models import db, User, School, Pupil, Payment

auth_bp = Blueprint('auth', __name__)
DEFAULT_PASSWORD = 'Myschool@123'


def is_email(s):
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', s or ''))


def is_phone(s):
    return bool(re.match(r'^\+?\d{9,15}$', (s or '').replace(' ', '').replace('-', '')))


def normalize_login(s):
    s = (s or '').strip()
    return s.lower() if is_email(s) else s


def slugify(name):
    s = re.sub(r'[^a-zA-Z0-9]+', '-', (name or '').lower()).strip('-')
    return s or 'school'


def generate_payment_token():
    return 'SCH-' + secrets.token_hex(5).upper()


@auth_bp.route('/api/schools', methods=['GET'])
def api_schools():
    schools = School.query.filter_by(is_active=True).order_by(School.name).all()
    return jsonify([{'id': s.id, 'name': s.name} for s in schools])


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        role = (request.form.get('role') or '').strip()
        school_id = request.form.get('school_id')
        username = normalize_login(request.form.get('username', ''))
        password = request.form.get('password', '')

        if not role:
            flash('Please select your role.', 'danger')
            return redirect(url_for('auth.login'))

        if role == 'developer':
            user = User.query.filter_by(role='developer').filter(
                (User.username == username) | (User.email == username)
            ).first()
            if user and user.check_password(password):
                if not user.is_active_flag:
                    flash('Account deactivated.', 'danger')
                    return redirect(url_for('auth.login'))
                login_user(user, remember=True)
                user.last_login = datetime.utcnow()
                db.session.commit()
                flash('Logged in as Developer!', 'success')
                return redirect(url_for('auth.developer_schools'))
            flash('Invalid Developer credentials.', 'danger')
            return redirect(url_for('auth.login'))

        if not school_id:
            flash('Please select your school.', 'danger')
            return redirect(url_for('auth.login'))

        try:
            school_id = int(school_id)
        except (TypeError, ValueError):
            flash('Invalid school.', 'danger')
            return redirect(url_for('auth.login'))

        if role == 'pupil':
            pupil = Pupil.query.filter_by(admission_no=username, school_id=school_id).first()
            user = User.query.filter_by(role='pupil', pupil_id=pupil.id).first() if pupil else None
        else:
            user = User.query.filter_by(role=role, school_id=school_id).filter(
                (User.username == username) |
                (User.email == username) |
                (User.phone == username)
            ).first()

        if user and user.check_password(password):
            if not user.is_active_flag:
                flash('Your account is deactivated.', 'danger')
                return redirect(url_for('auth.login'))

            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')

            if getattr(user, 'must_change_password', False):
                flash('Please change your default password.', 'warning')
                return redirect(url_for('auth.change_password'))

            if user.role == 'parent': return redirect(url_for('parent.dashboard'))
            if user.role == 'pupil': return redirect(url_for('auth.pupil_portal'))
            return redirect(url_for('index'))

        flash('Invalid credentials.', 'danger')
        return redirect(url_for('auth.login'))

    return render_template('auth/login.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old = request.form.get('old_password', '')
        new = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        if not current_user.check_password(old):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))
        if len(new) < 6:
            flash('New password must be at least 6 characters.', 'danger')
            return redirect(url_for('auth.change_password'))
        if new != confirm:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('auth.change_password'))
        current_user.set_password(new)
        current_user.must_change_password = False
        db.session.commit()
        flash('Password changed successfully.', 'success')
        if current_user.role == 'parent': return redirect(url_for('parent.dashboard'))
        if current_user.role == 'pupil': return redirect(url_for('auth.pupil_portal'))
        if current_user.role == 'developer': return redirect(url_for('auth.developer_schools'))
        return redirect(url_for('index'))
    return render_template('auth/change_password.html')


@auth_bp.route('/pupil-portal')
@login_required
def pupil_portal():
    if current_user.role != 'pupil':
        flash('Pupil portal only.', 'warning')
        return redirect(url_for('index'))
    pupil = Pupil.query.get(current_user.pupil_id) if current_user.pupil_id else None
    return render_template('pupil/portal.html', pupil=pupil)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ===================== DEVELOPER: SCHOOLS =====================

@auth_bp.route('/developer/schools')
@login_required
def developer_schools():
    if current_user.role != 'developer':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('index'))
    schools = School.query.order_by(School.created_at.desc()).all()
    return render_template('auth/developer_schools.html', schools=schools)


@auth_bp.route('/developer/schools/new', methods=['GET', 'POST'])
@login_required
def developer_school_new():
    if current_user.role != 'developer':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        if not name:
            flash('School name is required.', 'danger')
            return redirect(url_for('auth.developer_school_new'))

        slug = slugify(name)
        base = slug
        i = 1
        while School.query.filter_by(slug=slug).first():
            i += 1
            slug = f'{base}-{i}'

        now = datetime.utcnow()
        school = School(
            name=name, slug=slug,
            motto=request.form.get('motto', '').strip(),
            address=request.form.get('address', '').strip(),
            region=request.form.get('region', '').strip(),
            district=request.form.get('district', '').strip(),
            phone=request.form.get('phone', '').strip(),
            phone_2=request.form.get('phone_2', '').strip(),
            email=request.form.get('email', '').strip(),
            website=request.form.get('website', '').strip(),
            postal_address=request.form.get('postal_address', '').strip(),
            registration_number=request.form.get('registration_number', '').strip(),
            necta_number=request.form.get('necta_number', '').strip(),
            head_teacher_name=request.form.get('head_teacher_name', '').strip(),
            established_year=request.form.get('established_year', '').strip(),
            payment_token=generate_payment_token(),
            monthly_fee=70000,
            first_due_at=now + timedelta(hours=1),
            next_due_at=now + timedelta(hours=1),
            payment_status='pending',
        )
        db.session.add(school)
        db.session.flush()

        # Logo upload
        logo = request.files.get('logo')
        if logo and logo.filename:
            ext = os.path.splitext(logo.filename)[1].lower()
            if ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
                upload_dir = os.path.join('static', 'uploads', 'logos')
                os.makedirs(upload_dir, exist_ok=True)
                fname = f'logo_{uuid.uuid4().hex}{ext}'
                logo.save(os.path.join(upload_dir, fname))
                school.logo_path = f'/static/uploads/logos/{fname}'

        # First admin
        admin_contact = normalize_login(request.form.get('admin_contact', ''))
        admin_full_name = request.form.get('admin_full_name', '').strip()
        admin_password = request.form.get('admin_password', '').strip() or DEFAULT_PASSWORD

        if not admin_contact:
            db.session.rollback()
            flash('Admin email or phone is required.', 'danger')
            return redirect(url_for('auth.developer_school_new'))

        admin = User(
            username=admin_contact,
            email=admin_contact if is_email(admin_contact) else None,
            phone=admin_contact if is_phone(admin_contact) else None,
            full_name=admin_full_name or admin_contact,
            role='admin',
            school_id=school.id,
            is_active_flag=True,
            must_change_password=True,
            created_by=current_user.id,
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()

        flash(f'School "{school.name}" created! Payment token: {school.payment_token}. '
              f'First payment of TZS {school.monthly_fee:,} due within 1 hour.',
              'success')
        return redirect(url_for('auth.developer_schools'))

    return render_template('auth/developer_school_new.html', default_password=DEFAULT_PASSWORD)


@auth_bp.route('/developer/schools/<int:school_id>/edit', methods=['GET', 'POST'])
@login_required
def developer_school_edit(school_id):
    if current_user.role != 'developer':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('index'))
    school = School.query.get_or_404(school_id)

    if request.method == 'POST':
        school.name = request.form.get('name', '').strip() or school.name
        school.motto = request.form.get('motto', '').strip()
        school.address = request.form.get('address', '').strip()
        school.region = request.form.get('region', '').strip()
        school.district = request.form.get('district', '').strip()
        school.phone = request.form.get('phone', '').strip()
        school.phone_2 = request.form.get('phone_2', '').strip()
        school.email = request.form.get('email', '').strip()
        school.website = request.form.get('website', '').strip()
        school.postal_address = request.form.get('postal_address', '').strip()
        school.registration_number = request.form.get('registration_number', '').strip()
        school.necta_number = request.form.get('necta_number', '').strip()
        school.head_teacher_name = request.form.get('head_teacher_name', '').strip()
        school.established_year = request.form.get('established_year', '').strip()

        logo = request.files.get('logo')
        if logo and logo.filename:
            ext = os.path.splitext(logo.filename)[1].lower()
            if ext in ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'):
                upload_dir = os.path.join('static', 'uploads', 'logos')
                os.makedirs(upload_dir, exist_ok=True)
                fname = f'logo_{uuid.uuid4().hex}{ext}'
                logo.save(os.path.join(upload_dir, fname))
                school.logo_path = f'/static/uploads/logos/{fname}'

        db.session.commit()
        flash('School updated.', 'success')
        return redirect(url_for('auth.developer_schools'))

    return render_template('auth/developer_school_new.html',
                           school=school, default_password=DEFAULT_PASSWORD)


@auth_bp.route('/developer/schools/<int:school_id>/toggle')
@login_required
def developer_school_toggle(school_id):
    if current_user.role != 'developer':
        abort(403)
    s = School.query.get_or_404(school_id)
    s.is_active = not s.is_active
    db.session.commit()
    flash(f'School "{s.name}" is now {"active" if s.is_active else "inactive"}.', 'success')
    return redirect(url_for('auth.developer_schools'))


@auth_bp.route('/developer/schools/<int:school_id>/mark-paid', methods=['POST'])
@login_required
def developer_mark_paid(school_id):
    if current_user.role != 'developer':
        abort(403)
    school = School.query.get_or_404(school_id)

    amount = int(request.form.get('amount', school.monthly_fee) or school.monthly_fee)
    token = request.form.get('token_used', school.payment_token)
    reference = request.form.get('reference', '')
    method = request.form.get('method', 'Cash')

    now = datetime.utcnow()
    p = Payment(
        school_id=school.id,
        amount=amount,
        token_used=token,
        reference=reference,
        method=method,
        period_start=now,
        period_end=now + timedelta(days=30),
        recorded_by=current_user.id,
    )
    db.session.add(p)

    school.last_paid_at = now
    school.next_due_at = now + timedelta(days=30)
    school.payment_status = 'paid'
    db.session.commit()

    flash(f'Payment of TZS {amount:,} recorded for {school.name}.', 'success')
    return redirect(url_for('auth.developer_schools'))


@auth_bp.route('/developer/schools/<int:school_id>')
@login_required
def developer_school_detail(school_id):
    if current_user.role != 'developer':
        abort(403)
    school = School.query.get_or_404(school_id)
    admins = User.query.filter_by(school_id=school.id, role='admin').all()
    teachers = User.query.filter_by(school_id=school.id, role='teacher').all()
    parents = User.query.filter_by(school_id=school.id, role='parent').all()
    pupils = User.query.filter_by(school_id=school.id, role='pupil').all()
    payments = Payment.query.filter_by(school_id=school.id).order_by(Payment.created_at.desc()).all()
    return render_template('auth/developer_school_detail.html',
                           school=school, admins=admins,
                           teachers=teachers, parents=parents, pupils=pupils,
                           payments=payments,
                           default_password=DEFAULT_PASSWORD)


# ===================== ADMIN: USERS =====================

@auth_bp.route('/admin/users', methods=['GET', 'POST'])
@login_required
def admin_users():
    if current_user.role not in ('admin', 'developer'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('index'))
    if current_user.role == 'developer':
        return redirect(url_for('auth.developer_schools'))

    school_id = current_user.school_id

    if request.method == 'POST':
        contact = normalize_login(request.form.get('contact', ''))
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'teacher')

        if not contact:
            flash('Email or phone required.', 'danger')
            return redirect(url_for('auth.admin_users'))
        if User.query.filter_by(username=contact, school_id=school_id).first():
            flash('Account already exists.', 'danger')
            return redirect(url_for('auth.admin_users'))

        u = User(
            username=contact,
            email=contact if is_email(contact) else None,
            phone=contact if is_phone(contact) else None,
            full_name=full_name or contact,
            role=role,
            school_id=school_id,
            is_active_flag=True,
            must_change_password=True,
            created_by=current_user.id,
        )
        u.set_password(DEFAULT_PASSWORD)
        db.session.add(u)
        db.session.commit()
        flash(f'{role.title()} created: {contact} / {DEFAULT_PASSWORD}', 'success')
        return redirect(url_for('auth.admin_users'))

    teachers = User.query.filter_by(role='teacher', school_id=school_id).order_by(User.created_at.desc()).all()
    parents = User.query.filter_by(role='parent', school_id=school_id).order_by(User.created_at.desc()).all()
    return render_template('auth/admin_users.html',
                           teachers=teachers, parents=parents,
                           default_password=DEFAULT_PASSWORD)


@auth_bp.route('/admin/pupil-user/<int:pupil_id>', methods=['POST', 'GET'])
@login_required
def create_pupil_user(pupil_id):
    if current_user.role not in ('admin', 'developer'):
        abort(403)
    p = Pupil.query.get_or_404(pupil_id)
    if p.school_id != current_user.school_id and current_user.role != 'developer':
        abort(403)

    if User.query.filter_by(username=p.admission_no, school_id=p.school_id).first():
        flash('Login already exists.', 'warning')
        return redirect(url_for('edit_pupil', id=p.id))

    u = User(
        username=p.admission_no, full_name=p.full_name,
        role='pupil', pupil_id=p.id, school_id=p.school_id,
        is_active_flag=True, must_change_password=True,
        created_by=current_user.id,
    )
    u.set_password(p.last_name or DEFAULT_PASSWORD)
    db.session.add(u)
    db.session.commit()
    flash(f'Pupil login: {p.admission_no} / {p.last_name}', 'success')
    return redirect(url_for('edit_pupil', id=p.id))


@auth_bp.route('/admin/reset-default/<int:user_id>')
@login_required
def reset_default(user_id):
    if current_user.role not in ('admin', 'developer'):
        abort(403)
    u = User.query.get_or_404(user_id)
    if u.role == 'developer':
        flash('Cannot reset developer.', 'danger')
        return redirect(url_for('auth.admin_users'))
    u.set_password(DEFAULT_PASSWORD)
    u.must_change_password = True
    db.session.commit()
    flash(f'Password reset to {DEFAULT_PASSWORD} for {u.username}.', 'success')
    return redirect(request.referrer or url_for('auth.admin_users'))


@auth_bp.route('/admin/toggle/<int:user_id>')
@login_required
def toggle_user(user_id):
    if current_user.role not in ('admin', 'developer'):
        abort(403)
    u = User.query.get_or_404(user_id)
    if u.id == current_user.id:
        flash('Cannot deactivate yourself.', 'warning')
        return redirect(request.referrer or url_for('auth.admin_users'))
    u.is_active_flag = not u.is_active_flag
    db.session.commit()
    flash(f'{u.username} is now {"active" if u.is_active_flag else "inactive"}.', 'success')
    return redirect(request.referrer or url_for('auth.admin_users'))


@auth_bp.route('/admin/delete/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role not in ('admin', 'developer'):
        abort(403)
    u = User.query.get_or_404(user_id)
    if u.id == current_user.id:
        flash('Cannot delete yourself.', 'warning')
        return redirect(request.referrer or url_for('auth.admin_users'))
    if u.role == 'developer':
        flash('Cannot delete developer.', 'danger')
        return redirect(request.referrer or url_for('auth.admin_users'))
    db.session.delete(u)
    db.session.commit()
    flash('User deleted.', 'info')
    return redirect(request.referrer or url_for('auth.admin_users'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name', current_user.full_name)
        current_user.email = (request.form.get('email') or '').strip() or current_user.email
        current_user.phone = (request.form.get('phone') or '').strip() or current_user.phone
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('auth.profile'))
    return render_template('auth/profile.html')

# ===================== DEVELOPER: REGISTER ADMIN =====================

@auth_bp.route('/developer/admins/new', methods=['POST'])
@login_required
def developer_admin_new():
    if current_user.role != 'developer':
        abort(403)

    school_id = request.form.get('school_id', type=int)
    admin_id = request.form.get('admin_id', type=int)   # if editing existing
    contact = (request.form.get('contact') or '').strip()
    full_name = (request.form.get('full_name') or '').strip()
    password = (request.form.get('password') or '').strip()

    if not school_id or not contact:
        flash('School and Admin email/phone are required.', 'danger')
        return redirect(url_for('auth.developer_schools'))

    school = School.query.get(school_id)
    if not school:
        flash('School not found.', 'danger')
        return redirect(url_for('auth.developer_schools'))

    contact_norm = contact.lower() if is_email(contact) else contact

    # EDIT EXISTING ADMIN
    if admin_id:
        u = User.query.get(admin_id)
        if not u:
            flash('Admin not found.', 'danger')
            return redirect(url_for('auth.developer_schools'))

        # Contact change: ensure no clash with other users in the same school
        clash = User.query.filter(
            User.school_id == school.id,
            User.id != u.id,
            User.username == contact_norm
        ).first()
        if clash:
            flash(f'Another account already uses {contact_norm} in {school.name}.', 'danger')
            return redirect(url_for('auth.developer_schools'))

        u.username = contact_norm
        u.email = contact_norm if is_email(contact_norm) else None
        u.phone = None if is_email(contact_norm) else contact_norm
        u.full_name = full_name or u.full_name
        u.school_id = school.id
        if password:
            u.set_password(password)
            u.must_change_password = True
        db.session.commit()
        flash(f'Admin updated: {contact_norm} in {school.name}.', 'success')
        return redirect(url_for('auth.developer_schools'))

    # CREATE NEW ADMIN
    if not password:
        password = 'Myschool@123'

    clash = User.query.filter_by(username=contact_norm, school_id=school.id).first()
    if clash:
        flash(f'An account with {contact_norm} already exists in {school.name}. '
              f'Edit that account instead.', 'warning')
        return redirect(url_for('auth.developer_schools'))

    u = User(
        username=contact_norm,
        email=contact_norm if is_email(contact_norm) else None,
        phone=None if is_email(contact_norm) else contact_norm,
        full_name=full_name or contact_norm,
        role='admin',
        school_id=school.id,
        is_active_flag=True,
        must_change_password=True,
        created_by=current_user.id,
    )
    u.set_password(password)
    db.session.add(u)
    db.session.commit()

    flash(f'Admin created for {school.name}: {contact_norm} / {password}', 'success')
    return redirect(url_for('auth.developer_schools'))


# ===================== END DEV ADMINS =====================

# ===================== DEVELOPER: RESET ADMIN PASSWORD =====================

@auth_bp.route('/developer/admins/<int:user_id>/reset', methods=['POST'])
@login_required
def developer_admin_reset(user_id):
    if current_user.role != 'developer':
        abort(403)

    u = User.query.get_or_404(user_id)

    # Only allow resetting admins
    if u.role != 'admin':
        flash('This account is not an admin.', 'danger')
        return redirect(url_for('auth.developer_schools'))

    new_password = (request.form.get('new_password') or 'Myschool@123').strip()
    u.set_password(new_password)
    u.must_change_password = True
    u.is_active_flag = True
    db.session.commit()

    flash(f'Password for {u.username} reset to: {new_password}', 'success')
    return redirect(url_for('auth.developer_schools'))


@auth_bp.route('/developer/admins/<int:user_id>/toggle', methods=['POST'])
@login_required
def developer_admin_toggle(user_id):
    if current_user.role != 'developer':
        abort(403)

    u = User.query.get_or_404(user_id)
    if u.role != 'admin':
        flash('Not an admin.', 'danger')
        return redirect(url_for('auth.developer_schools'))

    u.is_active_flag = not u.is_active_flag
    db.session.commit()
    flash(f'{u.username} is now {"active" if u.is_active_flag else "inactive"}.', 'success')
    return redirect(url_for('auth.developer_schools'))


@auth_bp.route('/developer/admins/<int:user_id>/delete', methods=['POST'])
@login_required
def developer_admin_delete(user_id):
    if current_user.role != 'developer':
        abort(403)

    u = User.query.get_or_404(user_id)
    if u.role != 'admin':
        flash('Not an admin.', 'danger')
        return redirect(url_for('auth.developer_schools'))

    db.session.delete(u)
    db.session.commit()
    flash('Admin deleted.', 'info')
    return redirect(url_for('auth.developer_schools'))


# ===================== ADMIN: RESET USER PASSWORD =====================

@auth_bp.route('/admin/users/<int:user_id>/reset', methods=['POST'])
@login_required
def admin_user_reset(user_id):
    if current_user.role not in ('admin', 'developer'):
        abort(403)
    if current_user.role == 'developer':
        return redirect(url_for('auth.developer_schools'))

    u = User.query.get_or_404(user_id)
    if u.school_id != current_user.school_id:
        flash('Not your school.', 'danger')
        return redirect(url_for('auth.admin_users'))
    if u.role == 'developer':
        flash('Cannot reset developer.', 'danger')
        return redirect(url_for('auth.admin_users'))

    # Pupils get their last name as default; others get Myschool@123
    if u.role == 'pupil' and u.pupil_id:
        p = Pupil.query.get(u.pupil_id)
        new_password = (p.last_name if p else 'Myschool@123')
    else:
        new_password = (request.form.get('new_password') or 'Myschool@123').strip()

    u.set_password(new_password)
    u.must_change_password = True
    u.is_active_flag = True
    db.session.commit()

    flash(f'Password for {u.username} reset to: {new_password}', 'success')
    return redirect(url_for('auth.admin_users'))


# ===================== END RESET ROUTES =====================
