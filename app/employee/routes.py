from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file, abort
from werkzeug.utils import secure_filename
import os
import io
from app.models import Employee, User

employee = Blueprint('employee', __name__)

@employee.route('/employee/profile_pic/<int:employee_id>')
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

@employee.route('/employee/edit_profile', methods=['GET', 'POST'])
def employee_edit_profile():
    user_id = session.get('user_id')
    if not user_id or session.get('role') != 'employee':
        return redirect(url_for('main.login'))
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

@employee.route('/employee/profile')
def employee_profile():
    user_id = session.get('user_id')
    if not user_id or session.get('role') != 'employee':
        return redirect(url_for('main.login'))
    user = User.query.get(user_id)
    employee_obj = Employee.query.filter_by(user_id=user_id).first()
    return render_template('employee/profile.html', user=user, employee=employee_obj)
