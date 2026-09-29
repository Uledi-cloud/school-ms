from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
from decorators import admin_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password) and user.is_active_flag:
            login_user(user, remember=True)
            if user.role == 'parent':
                return redirect(url_for('parent.dashboard'))
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    first_user = User.query.count() == 0
    if not first_user and (not current_user.is_authenticated or current_user.role != 'admin'):
        flash('Only an admin can register new users.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        role = request.form.get('role', 'teacher')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('auth.register'))

        u = User(username=username, email=email, role=role,
                 phone=request.form.get('phone', ''))
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash(f'User {username} created!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', first_user=first_user)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/users')
@admin_required
def users_list():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('auth/users.html', users=users)


@auth_bp.route('/users/toggle/<int:id>')
@admin_required
def toggle_user(id):
    u = User.query.get_or_404(id)
    if u.id == current_user.id:
        flash('You cannot deactivate yourself.', 'warning')
        return redirect(url_for('auth.users_list'))
    u.is_active_flag = not u.is_active_flag
    db.session.commit()
    flash('User updated.', 'success')
    return redirect(url_for('auth.users_list'))