from flask import render_template, request, redirect, url_for, session, flash, Blueprint, send_file, abort
from app.models import User, Employee
from app import db
from datetime import datetime, date
from app.models import LeaveRequest
from flask import url_for
import io

main = Blueprint('main', __name__)

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['role'] = user.role
            if user.role == 'employee':
                return redirect(url_for('main.employee_attendance'))
            elif user.role == 'hr':
                return redirect(url_for('main.hr_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('main.admin_dashboard'))
            else:
                flash('Unknown user role.')
                return redirect(url_for('main.login'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')


@main.route('/employee/attendance', methods=['GET', 'POST'])
def employee_attendance():
    from app.models import Employee, Attendance, User
    from datetime import datetime, date
    today = date.today()
    today_checkin_12 = None
    today_checkout_12 = None
    today_checkin_24 = None
    today_checkout_24 = None
    worked_seconds = 0

    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    employee = Employee.query.filter_by(user_id=user_id).first() if user_id else None

    print(f"User ID: {user_id}, Employee: {employee}")

    if employee:
        if request.method == 'POST':
            action = request.form.get('action')
            now = datetime.now().time()
            if action == 'checkin':
                new_attendance = Attendance(employee_id=employee.id, date=today, checkin_time=now, checkout_time=None)
                db.session.add(new_attendance)
                db.session.commit()
            elif action == 'checkout':
                latest = Attendance.query.filter_by(employee_id=employee.id, date=today, checkout_time=None).order_by(Attendance.checkin_time.desc()).first()
                if latest:
                    latest.checkout_time = now
                    db.session.commit()
        attendances = Attendance.query.filter_by(employee_id=employee.id, date=today).order_by(Attendance.checkin_time).all()
        if attendances:
            latest = attendances[-1]
            if latest.checkin_time and latest.checkout_time:
                worked_seconds = (
                    datetime.combine(today, latest.checkout_time) -
                    datetime.combine(today, latest.checkin_time)
                ).seconds
            elif latest.checkin_time and not latest.checkout_time:
                worked_seconds = (
                    datetime.combine(today, datetime.now().time()) -
                    datetime.combine(today, latest.checkin_time)
                ).seconds
            today_checkin_24 = latest.checkin_time.strftime('%H:%M:%S') if latest.checkin_time else None
            today_checkout_24 = latest.checkout_time.strftime('%H:%M:%S') if latest.checkout_time else None
            today_checkin_12 = latest.checkin_time.strftime('%I:%M:%S %p') if latest.checkin_time else None
            today_checkout_12 = latest.checkout_time.strftime('%I:%M:%S %p') if latest.checkout_time else None
    else:
        print("No employee record found for this user.")
    print("today_checkin:", today_checkin_12, "today_checkout:", today_checkout_12)
    return render_template(
        'employee/attendance.html',
        today_checkin=today_checkin_12,
        today_checkout=today_checkout_12,
        today_checkin_24=today_checkin_24,
        today_checkout_24=today_checkout_24,
        worked_seconds=worked_seconds
    )


@main.route('/employee/dashboard')
def employee_dashboard():
    from app.models import User, Employee, Attendance
    from datetime import date, datetime
    employee_name = None
    today_checkin_12 = None
    today_checkout_12 = None
    today_checkin_24 = None
    today_checkout_24 = None
    worked_seconds = 0

    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            employee_name = user.username
            employee = Employee.query.filter_by(user_id=user.id).first()
            if employee:
                today = date.today()
                attendances = Attendance.query.filter_by(employee_id=employee.id, date=today).order_by(Attendance.checkin_time).all()
                if attendances:
                    latest = attendances[-1]
                    if latest.checkin_time:
                        today_checkin_24 = latest.checkin_time.strftime('%H:%M:%S')
                        today_checkin_12 = latest.checkin_time.strftime('%I:%M:%S %p')
                    if latest.checkout_time:
                        today_checkout_24 = latest.checkout_time.strftime('%H:%M:%S')
                        today_checkout_12 = latest.checkout_time.strftime('%I:%M:%S %p')
                    if latest.checkin_time and latest.checkout_time:
                        worked_seconds = (
                            datetime.combine(today, latest.checkout_time) -
                            datetime.combine(today, latest.checkin_time)
                        ).seconds
                    elif latest.checkin_time and not latest.checkout_time:
                        worked_seconds = (
                            datetime.combine(today, datetime.now().time()) -
                            datetime.combine(today, latest.checkin_time)
                        ).seconds
    return render_template(
        'employee/dashboard.html',
        employee_name=employee_name,
        today_checkin=today_checkin_12,
        today_checkout=today_checkout_12,
        today_checkin_24=today_checkin_24,
        today_checkout_24=today_checkout_24,
        worked_seconds=worked_seconds
    )


@main.route('/hr/dashboard')
def hr_dashboard():
    from app.models import Employee, User, LeaveRequest
    hr_name = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            hr_name = user.username
    total_employees = Employee.query.count()
    pending_leaves = LeaveRequest.query.filter_by(status='Pending').count()
    attendance_issues = 0  # Or your logic for issues
    return render_template(
        'hr/dashboard.html',
        hr_name=hr_name,
        total_employees=total_employees,
        pending_leaves=pending_leaves,
        attendance_issues=attendance_issues
    )

@main.route('/admin/dashboard')
def admin_dashboard():
    from app.models import User
    admin_name = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            admin_name = user.username
    total_users = User.query.count()
    # You can add logic for system_health and recent_activity as needed
    return render_template(
        'admin/dashboard.html',
        admin_name=admin_name,
        total_users=total_users,
        system_health='Good',
        recent_activity=0
    )

@main.route('/hr/add_employee', methods=['GET', 'POST'])
def add_employee():
    message = None
    if request.method == 'POST':
        # Extract form data
        name = request.form.get('name')
        address = request.form.get('address')
        phone_number = request.form.get('phone_number')
        unique_id_number = request.form.get('unique_id_number')
        username = request.form.get('username')
        password = request.form.get('password')
        job_role = request.form.get('job_role')
        salary = float(request.form.get('salary', 0)) if request.form.get('salary') else None
        # Check if username or unique_id_number already exists
        from app.models import User, Employee
        if User.query.filter_by(username=username).first():
            message = 'Username already exists.'
        elif Employee.query.filter_by(unique_id_number=unique_id_number).first():
            message = 'Unique ID number already exists.'
        else:
            # Create user and employee
            user = User(username=username, password=password, role='employee')
            db.session.add(user)
            db.session.commit()
            employee = Employee(
                name=name,
                address=address,
                phone_number=phone_number,
                unique_id_number=unique_id_number,
                job_role=job_role,
                salary=salary,
                user_id=user.id
            )
            db.session.add(employee)
            db.session.commit()
            message = 'Employee added successfully!'
    return render_template('hr/add_employee.html', message=message)

@main.route('/hr/employees')
def view_employees():
    from app.models import Employee, User
    employees = Employee.query.all()
    # Prepare a list of dicts with employee and user info
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
            'job_role': emp.job_role,
            'salary': emp.salary
        })
    return render_template('hr/view_employees.html', employees=employee_list)

@main.route('/hr/employee_list')
def employee_list():
    from app.models import Employee
    employees = Employee.query.all()
    return render_template('hr/employee_list.html', employees=employees)

@main.route('/hr/attendance/<int:employee_id>')
def employee_attendance_detail(employee_id):
    from app.models import Employee, Attendance
    employee = Employee.query.get_or_404(employee_id)
    attendance_records = Attendance.query.filter_by(employee_id=employee_id).order_by(Attendance.date.desc()).all()
    return render_template('hr/employee_attendance.html', employee=employee, attendance_records=attendance_records)

@main.route('/hr/attendance')
def view_attendance():
    from app.models import Attendance, Employee
    from datetime import date, datetime
    today = date.today()
    records = Attendance.query.join(Employee).filter(Attendance.date == today).order_by(Attendance.date.desc()).all()
    attendance_list = []
    for rec in records:
        # Calculate duration
        duration = ""
        if rec.checkin_time and rec.checkout_time:
            delta = (
                datetime.combine(rec.date, rec.checkout_time) -
                datetime.combine(rec.date, rec.checkin_time)
            )
            total_seconds = int(delta.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            duration = f"{hours:02}:{minutes:02}:{seconds:02}"
        attendance_list.append({
            'employee_name': rec.employee.name,
            'date': rec.date.strftime('%Y-%m-%d'),
            'checkin_time': rec.checkin_time.strftime('%I:%M:%S %p') if rec.checkin_time else '-',
            'checkout_time': rec.checkout_time.strftime('%I:%M:%S %p') if rec.checkout_time else '-',
            'duration': duration or '-'
        })
    return render_template('hr/view_attendance.html', attendance=attendance_list)

@main.route('/hr/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    from app.models import Employee, User
    message = None
    employee = Employee.query.get_or_404(employee_id)
    user = User.query.get(employee.user_id)
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name')
        address = request.form.get('address')
        phone_number = request.form.get('phone_number')
        unique_id_number = request.form.get('unique_id_number')
        username = request.form.get('username')
        password = request.form.get('password')
        job_role = request.form.get('job_role')
        salary = float(request.form.get('salary', 0)) if request.form.get('salary') else None
        # Check for unique username and unique_id_number (excluding current)
        if User.query.filter(User.username == username, User.id != user.id).first():
            message = 'Username already exists.'
        elif Employee.query.filter(Employee.unique_id_number == unique_id_number, Employee.id != employee.id).first():
            message = 'Unique ID number already exists.'
        else:
            employee.name = name
            employee.address = address
            employee.phone_number = phone_number
            employee.unique_id_number = unique_id_number
            employee.job_role = job_role
            employee.salary = salary
            user.username = username
            user.password = password
            db.session.commit()
            message = 'Employee details updated successfully!'
    return render_template('hr/edit_employee.html', employee=employee, user=user, message=message)

@main.route('/hr/delete_employee/<int:employee_id>', methods=['POST'])
def delete_employee(employee_id):
    from app.models import Employee, User, Attendance, LeaveRequest
    try:
        employee = Employee.query.get_or_404(employee_id)
        user = User.query.get(employee.user_id)
        
        # First, delete all related records manually to avoid foreign key issues
        # Delete attendance records
        attendance_records = Attendance.query.filter_by(employee_id=employee_id).all()
        for record in attendance_records:
            db.session.delete(record)
        print(f"Deleted {len(attendance_records)} attendance records")
        
        # Delete leave requests
        leave_records = LeaveRequest.query.filter_by(employee_id=employee_id).all()
        for record in leave_records:
            db.session.delete(record)
        print(f"Deleted {len(leave_records)} leave request records")
        
        # Commit the deletion of related records first
        db.session.commit()
        
        # Now delete the employee
        db.session.delete(employee)
        
        # Delete the user account
        if user:
            db.session.delete(user)
        
        # Final commit
        db.session.commit()
        flash('Employee and all related records deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        error_msg = f'Error deleting employee: {str(e)}'
        flash(error_msg, 'error')
        print(f"Error deleting employee {employee_id}: {str(e)}")
        
        # If it's a foreign key constraint error, provide more specific guidance
        if "IntegrityError" in str(type(e)) or "foreign key" in str(e).lower():
            flash('This employee has related records that could not be deleted. Please contact the administrator.', 'error')
    
    return redirect('/hr/employees')

@main.route('/')
def home():
    return redirect(url_for('main.login'))

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.login'))

@main.route('/employee/leave_request', methods=['GET', 'POST'])
def leave_request():
    from app.models import Employee, LeaveRequest
    message = None
    if request.method == 'POST':
        leave_type = request.form.get('leave_type')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        reason = request.form.get('reason')
        user_id = session.get('user_id')
        employee = Employee.query.filter_by(user_id=user_id).first() if user_id else None
        if employee:
            leave = LeaveRequest(
                employee_id=employee.id,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                status='Pending'
            )
            db.session.add(leave)
            db.session.commit()
            message = "Leave request submitted successfully!"
    return render_template('employee/leave_request.html', message=message)

@main.route('/hr/leave_requests', methods=['GET', 'POST'])
def hr_leave_requests():
    from app.models import LeaveRequest, Employee
    message = None
    if request.method == 'POST':
        leave_id = request.form.get('leave_id')
        action = request.form.get('action')
        leave = LeaveRequest.query.get(leave_id)
        if leave and action in ['Accepted', 'Rejected']:
            leave.status = action
            db.session.commit()
            message = f"Leave request {action.lower()}."
    leave_requests = LeaveRequest.query.join(Employee).order_by(LeaveRequest.request_date.desc()).all()
    return render_template('hr/leave_requests.html', leave_requests=leave_requests, message=message)

@main.route('/employee/leave_status')
def leave_status():
    from app.models import Employee, LeaveRequest
    leave_requests = []
    if 'user_id' in session:
        employee = Employee.query.filter_by(user_id=session['user_id']).first()
        if employee:
            leave_requests = LeaveRequest.query.filter_by(employee_id=employee.id).order_by(LeaveRequest.request_date.desc()).all()
    return render_template('employee/leave_status.html', leave_requests=leave_requests)


@main.route('/employee/profile')
def employee_profile():
    user_id = session.get('user_id')
    if not user_id or session.get('role') != 'employee':
        return redirect(url_for('main.login'))
    user = User.query.get(user_id)
    employee_obj = Employee.query.filter_by(user_id=user_id).first()
    return render_template('employee/profile.html', user=user, employee=employee_obj)

@main.app_context_processor
def inject_profile_pic_url():
    user_id = session.get('user_id')
    profile_pic_url = None
    if user_id:
        employee = Employee.query.filter_by(user_id=user_id).first()
        if employee and employee.profile_pic:
            profile_pic_url = url_for('employee.employee_profile_pic', employee_id=employee.id)
    return dict(profile_pic_url=profile_pic_url)
