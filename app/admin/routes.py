from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import User, Employee
from app import db

admin = Blueprint('admin', __name__)

@admin.route('/admin/view_employees')
def view_employees():
    """Admin view to see all employees"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.login'))
    
    employees = Employee.query.all()
    employee_list = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        employee_list.append({
            'id': emp.id,
            'name': emp.name,
            'address': emp.address,
            'phone_number': emp.phone_number,
            'unique_id_number': emp.unique_id_number,
            'username': user.username if user else '',
            'role': user.role if user else '',
            'job_role': emp.job_role
        })
    return render_template('admin/view_employees.html', employees=employee_list)

@admin.route('/admin/view_hr')
def view_hr():
    """Admin view to see all HR users"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.login'))
    
    hr_users = User.query.filter_by(role='hr').all()
    hr_list = []
    for user in hr_users:
        hr_list.append({
            'id': user.id,
            'username': user.username,
            'role': user.role
        })
    return render_template('admin/view_hr.html', hr_users=hr_list)

@admin.route('/admin/add_hr', methods=['GET', 'POST'])
def add_hr():
    """Admin route to add new HR users"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.login'))
    
    message = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not username or not password:
            message = 'Username and password are required.'
        elif password != confirm_password:
            message = 'Passwords do not match.'
        elif User.query.filter_by(username=username).first():
            message = 'Username already exists.'
        else:
            # Create new HR user
            new_hr = User(username=username, password=password, role='hr')
            db.session.add(new_hr)
            db.session.commit()
            message = 'HR user added successfully!'
    
    return render_template('admin/add_hr.html', message=message)

@admin.route('/admin/delete_hr/<int:hr_id>', methods=['POST'])
def delete_hr(hr_id):
    """Admin route to delete HR users"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Access denied. Admin privileges required.')
        return redirect(url_for('main.login'))
    
    hr_user = User.query.get(hr_id)
    if hr_user and hr_user.role == 'hr':
        db.session.delete(hr_user)
        db.session.commit()
        flash('HR user deleted successfully.')
    else:
        flash('HR user not found.')
    
    return redirect(url_for('admin.view_hr'))
