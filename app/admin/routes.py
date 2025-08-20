from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import User, Employee
from app import db
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

admin = Blueprint('admin', __name__)

@admin.route('/admin/view_employees')
@login_required
@role_required(['admin'])
def view_employees():
    """Admin view to see all employees"""
    employees = Employee.query.all()
    employee_list = []
    for emp in employees:
        user = User.query.get(emp.user_id)
        employee_list.append({
            'id': emp.id,
            'name': emp.name,
            'gender': emp.gender,
            'address': emp.address,
            'phone_number': emp.phone_number,
            'unique_id_number': emp.unique_id_number,
            'username': user.username if user else '',
            'role': user.role if user else '',
            'job_role': emp.job_role
        })
    return render_template('admin/view_employees.html', employees=employee_list)

@admin.route('/admin/view_hr')
@login_required
@role_required(['admin'])
def view_hr():
    """Admin view to see all HR users"""
    hr_users = User.query.filter_by(role='hr').all()
    hr_list = []
    for user in hr_users:
        hr_list.append({
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'role': user.role
        })
    return render_template('admin/view_hr.html', hr_users=hr_list)

@admin.route('/admin/add_hr', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def add_hr():
    """Admin route to add new HR users"""
    message = None
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not name or not username or not password:
            message = 'Name, username and password are required.'
        elif password != confirm_password:
            message = 'Passwords do not match.'
        elif User.query.filter_by(username=username).first():
            message = 'Username already exists.'
        else:
            # Create new HR user with hashed password
            new_hr = User(username=username, role='hr', name=name)
            new_hr.set_password(password)
            db.session.add(new_hr)
            db.session.commit()
            message = 'HR user added successfully!'
    
    return render_template('admin/add_hr.html', message=message)

@admin.route('/admin/delete_hr/<int:hr_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def delete_hr(hr_id):
    """Admin route to delete HR users"""
    hr_user = User.query.get(hr_id)
    if hr_user and hr_user.role == 'hr':
        db.session.delete(hr_user)
        db.session.commit()
        flash('HR user deleted successfully.')
    else:
        flash('HR user not found.')
    
    return redirect(url_for('admin.view_hr'))

@admin.route('/admin/view_users')
@login_required
@role_required(['admin'])
def view_users():
    """Admin view to see all users with comprehensive details"""
    from app.models import Attendance, LeaveRequest
    from datetime import datetime, timedelta
    
    # Get all users
    all_users = User.query.all()
    users_data = []
    
    for user in all_users:
        user_info = {
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'name': user.name,
            'created_at': user.created_at if hasattr(user, 'created_at') else 'N/A',
            'last_login': user.last_login if hasattr(user, 'last_login') else 'N/A',
            'is_active': user.is_active if hasattr(user, 'is_active') else True,
            'employee_details': None,
            'attendance_stats': None,
            'leave_stats': None
        }
        
        # Get employee details if user is an employee (name and job role for system management)
        if user.role == 'employee':
            employee = Employee.query.filter_by(user_id=user.id).first()
            if employee:
                user_info['employee_details'] = {
                    'name': employee.name,
                    'job_role': employee.job_role
                }
                
                # Get attendance statistics
                total_attendance = Attendance.query.filter_by(employee_id=employee.id).count()
                today = datetime.now().date()
                today_attendance = Attendance.query.filter_by(employee_id=employee.id, date=today).first()
                
                user_info['attendance_stats'] = {
                    'total_records': total_attendance,
                    'today_status': 'Present' if today_attendance else 'Absent',
                    'login_time': None,
                    'last_checkout': None
                }
                
                # Get today's login time if present
                if today_attendance and today_attendance.checkin_time:
                    user_info['attendance_stats']['login_time'] = today_attendance.checkin_time.strftime('%I:%M %p')
                
                # Get last checkout time
                last_attendance = Attendance.query.filter_by(employee_id=employee.id).order_by(Attendance.date.desc()).first()
                if last_attendance and last_attendance.checkout_time:
                    user_info['attendance_stats']['last_checkout'] = last_attendance.checkout_time.strftime('%I:%M %p - %Y-%m-%d')
                
                # Get leave statistics
                total_leaves = LeaveRequest.query.filter_by(employee_id=employee.id).count()
                pending_leaves = LeaveRequest.query.filter_by(employee_id=employee.id, status='Pending').count()
                approved_leaves = LeaveRequest.query.filter_by(employee_id=employee.id, status='Accepted').count()
                
                user_info['leave_stats'] = {
                    'total_requests': total_leaves,
                    'pending': pending_leaves,
                    'approved': approved_leaves,
                    'rejected': total_leaves - pending_leaves - approved_leaves
                }
        
        users_data.append(user_info)
    
    # Sort users by role and then by username
    users_data.sort(key=lambda x: (x['role'], x['username']))
    
    return render_template('admin/view_users.html', users=users_data)
