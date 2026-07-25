from flask import Blueprint, render_template, redirect, session, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from app.forms import LoginForm, RegisterForm
from app.extensions import db, limiter
from app.models import User

auth_bp = Blueprint('auth', __name__)

# Rate limiters for auth endpoints
login_limiter = Limiter(key_func=lambda: request.remote_addr)
register_limiter = Limiter(key_func=lambda: request.remote_addr)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip()
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            # Validate next parameter to prevent open redirect
            if next_page and not next_page.startswith('/'):
                next_page = None
            flash('Login successful!', 'success')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data.strip(), email=form.email.data.strip())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()  # Clear the session to remove any user-specific data
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))
