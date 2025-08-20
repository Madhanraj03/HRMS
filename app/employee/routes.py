from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, abort
from werkzeug.utils import secure_filename
import os
import io
from app.models import Employee, User
from functools import wraps

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

# Role-based access decorator
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('main.login'))
            if session.get('role') not in allowed_roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

employee = Blueprint('employee', __name__)

@employee.route('/profile_pic/<int:employee_id>')
@login_required
def employee_profile_pic(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    if not employee.profile_pic:
        abort(404)
    return send_file(
        io.BytesIO(employee.profile_pic),
        mimetype=employee.profile_pic_mimetype,
        as_attachment=False,
        download_name=f"profile_{employee_id}.jpg"
    )

@employee.app_context_processor
def inject_profile_pic_url():
    user_id = session.get('user_id')
    profile_pic_url = None
    if user_id:
        employee_obj = Employee.query.filter_by(user_id=user_id).first()
        if employee_obj and employee_obj.profile_pic:
            profile_pic_url = url_for('employee.employee_profile_pic', employee_id=employee_obj.id)
    return dict(profile_pic_url=profile_pic_url)

@employee.route('/edit_profile', methods=['GET', 'POST'])
@login_required
@role_required(['employee'])
def employee_edit_profile():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    employee_obj = Employee.query.filter_by(user_id=user_id).first()
    profile_pic_url = url_for('employee.employee_profile_pic', employee_id=employee_obj.id) if employee_obj and employee_obj.profile_pic else None

    if request.method == 'POST':
        employee_obj.phone_number = request.form.get('phone_number')
        employee_obj.address = request.form.get('address')
        file = request.files.get('profile_pic')
        if file and file.filename:
            employee_obj.profile_pic = file.read()
            employee_obj.profile_pic_mimetype = file.mimetype
        from app import db
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('employee.employee_profile'))

    return render_template('employee/profile_edit.html', user=user, employee=employee_obj, profile_pic_url=profile_pic_url)

@employee.route('/profile')
@login_required
@role_required(['employee'])
def employee_profile():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    employee_obj = Employee.query.filter_by(user_id=user_id).first()
    return render_template('employee/profile.html', user=user, employee=employee_obj)

@employee.route('/change_password', methods=['GET', 'POST'])
@login_required
@role_required(['employee'])
def change_password():
    """Allow employees to change their password from temporary to permanent"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate current password
        if not user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return render_template('employee/change_password.html', show_password_change_form=True)
        
        # Validate new password
        if new_password != confirm_password:
            flash('New password and confirm password do not match.', 'danger')
            return render_template('employee/change_password.html', show_password_change_form=True)
        
        # Check password strength
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'danger')
            return render_template('employee/change_password.html', show_password_change_form=True)
        
        # Set new password (this will hash it automatically)
        user.set_password(new_password)
        
        # Commit to database
        from app import db
        db.session.commit()
        
        flash('Password changed successfully! You can now use your new password for future logins.', 'success')
        
        # Show success message instead of form
        return render_template('employee/change_password.html', show_password_change_form=False)
    
    # GET request - show the password change form
    return render_template('employee/change_password.html', show_password_change_form=True)
