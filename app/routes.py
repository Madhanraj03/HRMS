import pytz
from flask import render_template, request, redirect, url_for, session, flash, Blueprint, send_file, abort
from functools import wraps
from app import db
from app.models import User, Employee, Attendance, LeaveRequest
from datetime import datetime, date, timedelta
import calendar

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

main = Blueprint('main', __name__)

@main.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to appropriate dashboard
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('main.admin_dashboard'))
        elif role == 'hr':
            return redirect(url_for('main.hr_dashboard'))
        elif role == 'employee':
            return redirect(url_for('main.employee_attendance'))
        else:
            return redirect(url_for('main.login'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.permanent = True  # Make session permanent with timeout
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
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@main.route('/unauthorized')
def unauthorized():
    flash('You do not have permission to access this page.', 'error')
    return redirect(url_for('main.login'))

@main.errorhandler(404)
def not_found_error(error):
    flash('Page not found.', 'error')
    return redirect(url_for('main.login'))


@main.route('/employee/attendance', methods=['GET', 'POST'])
@login_required
@role_required(['employee'])
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
                # Check if login is late (after 9:30 AM)
                late_login = now > datetime.strptime('09:30:00', '%H:%M:%S').time()
                new_attendance = Attendance(
                    employee_id=employee.id, 
                    date=today, 
                    checkin_time=now, 
                    checkout_time=None,
                    late_login=late_login
                )
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
            # Convert UTC to IST for check-in and check-out times
            utc = pytz.utc
            ist = pytz.timezone('Asia/Kolkata')
            if latest.checkin_time:
                dt_utc = datetime.combine(today, latest.checkin_time).replace(tzinfo=utc)
                dt_ist = dt_utc.astimezone(ist)
                today_checkin_24 = dt_ist.strftime('%H:%M:%S')
                today_checkin_12 = dt_ist.strftime('%I:%M:%S %p')
            if latest.checkout_time:
                dt_utc = datetime.combine(today, latest.checkout_time).replace(tzinfo=utc)
                dt_ist = dt_utc.astimezone(ist)
                today_checkout_24 = dt_ist.strftime('%H:%M:%S')
                today_checkout_12 = dt_ist.strftime('%I:%M:%S %p')
    else:
        print("No employee record found for this user.")
    # Check if today's check-in was late
    late_login = False
    if employee:
        today_attendance = Attendance.query.filter_by(employee_id=employee.id, date=today).order_by(Attendance.checkin_time.desc()).first()
        if today_attendance and today_attendance.late_login:
            late_login = True
    
    print("today_checkin:", today_checkin_12, "today_checkout:", today_checkout_12)
    return render_template(
        'employee/attendance.html',
        today_checkin=today_checkin_12,
        today_checkout=today_checkout_12,
        today_checkin_24=today_checkin_24,
        today_checkout_24=today_checkout_24,
        worked_seconds=worked_seconds,
        late_login=late_login
    )


@main.route('/employee/dashboard')
@login_required
@role_required(['employee'])
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
            employee = Employee.query.filter_by(user_id=user.id).first()
            if employee:
                employee_name = employee.name
            if employee:
                today = date.today()
                attendances = Attendance.query.filter_by(employee_id=employee.id, date=today).order_by(Attendance.checkin_time).all()
                if attendances:
                    latest = attendances[-1]
                    # Convert UTC to IST for check-in and check-out times
                    utc = pytz.utc
                    ist = pytz.timezone('Asia/Kolkata')
                    if latest.checkin_time:
                        dt_utc = datetime.combine(today, latest.checkin_time).replace(tzinfo=utc)
                        dt_ist = dt_utc.astimezone(ist)
                        today_checkin_24 = dt_ist.strftime('%H:%M:%S')
                        today_checkin_12 = dt_ist.strftime('%I:%M:%S %p')
                    if latest.checkout_time:
                        dt_utc = datetime.combine(today, latest.checkout_time).replace(tzinfo=utc)
                        dt_ist = dt_utc.astimezone(ist)
                        today_checkout_24 = dt_ist.strftime('%H:%M:%S')
                        today_checkout_12 = dt_ist.strftime('%I:%M:%S %p')
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
    
    # Check if today's check-in was late
    late_login = False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            employee = Employee.query.filter_by(user_id=user.id).first()
            if employee:
                today_attendance = Attendance.query.filter_by(employee_id=employee.id, date=today).order_by(Attendance.checkin_time.desc()).first()
                if today_attendance and today_attendance.late_login:
                    late_login = True
    
    return render_template(
        'employee/dashboard.html',
        employee_name=employee_name,
        today_checkin=today_checkin_12,
        today_checkout=today_checkout_12,
        today_checkin_24=today_checkin_24,
        today_checkout_24=today_checkout_24,
        worked_seconds=worked_seconds,
        late_login=late_login
    )


@main.route('/hr/dashboard')
@login_required
@role_required(['hr', 'admin'])
def hr_dashboard():
    from app.models import Employee, User, LeaveRequest, Attendance
    from datetime import date
    hr_name = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            hr_name = user.username
    total_employees = Employee.query.count()
    pending_leaves = LeaveRequest.query.filter_by(status='Pending').count()
    
    # Count late logins for today
    today = date.today()
    late_logins_today = Attendance.query.filter_by(date=today, late_login=True).count()
    
    return render_template(
        'hr/dashboard.html',
        hr_name=hr_name,
        total_employees=total_employees,
        pending_leaves=pending_leaves,
        attendance_issues=late_logins_today
    )

@main.route('/admin/dashboard')
@login_required
@role_required(['admin'])
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
@login_required
@role_required(['hr', 'admin'])
def add_employee():
    message = None
    if request.method == 'POST':
        # Extract form data
        name = request.form.get('name')
        gender = request.form.get('gender')
        address = request.form.get('address')
        phone_number = request.form.get('phone_number')
        unique_id_number = request.form.get('unique_id_number')
        username = request.form.get('username')
        # Password will be auto-generated
        job_role = request.form.get('job_role')
        salary = float(request.form.get('salary', 0)) if request.form.get('salary') else None
        # Check if username or unique_id_number already exists
        from app.models import User, Employee
        if User.query.filter_by(username=username).first():
            message = 'Username already exists.'
        elif Employee.query.filter_by(unique_id_number=unique_id_number).first():
            message = 'Unique ID number already exists.'
        else:
            # Generate a simple random password
            import secrets
            import string
            
            def generate_simple_password():
                # Simple password: 8 characters with letters and numbers
                letters = string.ascii_lowercase  # Only lowercase for simplicity
                digits = string.digits
                # Ensure at least 2 letters and 2 digits
                password = ''.join(secrets.choice(letters) for _ in range(3))
                password += ''.join(secrets.choice(digits) for _ in range(3))
                password += ''.join(secrets.choice(letters + digits) for _ in range(2))
                # Shuffle the password
                password_list = list(password)
                secrets.SystemRandom().shuffle(password_list)
                return ''.join(password_list)
            
            generated_password = generate_simple_password()
            
            # Create user with generated password
            user = User(username=username, role='employee', name=name)
            user.set_password(generated_password)  # This will hash the password
            user.temporary_password = True  # Mark as temporary password
            db.session.add(user)
            db.session.commit()
            
            employee = Employee(
                name=name,
                gender=gender,
                address=address,
                phone_number=phone_number,
                unique_id_number=unique_id_number,
                job_role=job_role,
                salary=salary,
                user_id=user.id
            )
            db.session.add(employee)
            db.session.commit()
            
            message = f'Employee added successfully! Generated password: {generated_password}'
            # Store generated password in session for display
            session['generated_password'] = generated_password
            session['new_employee_name'] = name
            session['new_employee_username'] = username
            
            return redirect(url_for('main.view_new_employee_password'))
    return render_template('hr/add_employee.html', message=message)

@main.route('/hr/view_new_employee_password')
@login_required
@role_required(['hr', 'admin'])
def view_new_employee_password():
    """Display the generated password for a new employee"""
    generated_password = session.get('generated_password')
    employee_name = session.get('new_employee_name')
    username = session.get('new_employee_username')
    
    if not generated_password:
        flash('No password information found.', 'error')
        return redirect(url_for('main.view_employees'))
    
    # Clear the session data after displaying
    session.pop('generated_password', None)
    session.pop('new_employee_name', None)
    session.pop('new_employee_username', None)
    
    return render_template('hr/new_employee_password.html', 
                         generated_password=generated_password,
                         employee_name=employee_name,
                         username=username)

@main.route('/hr/employees')
@login_required
@role_required(['hr', 'admin'])
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
            'gender': emp.gender,
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
@login_required
@role_required(['hr', 'admin'])
def employee_list():
    from app.models import Employee
    employees = Employee.query.all()
    return render_template('hr/employee_list.html', employees=employees)

@main.route('/hr/attendance/<int:employee_id>')
@login_required
@role_required(['hr', 'admin'])
def employee_attendance_detail(employee_id):
    from app.models import Employee, Attendance
    from datetime import datetime, date, timedelta
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Default to current month if no dates provided
    if not start_date:
        start_date = (date.today().replace(day=1)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = date.today().strftime('%Y-%m-%d')
    
    # Convert string dates to date objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Validate date range
    if start_date_obj > end_date_obj:
        flash('Start date cannot be after end date.')
        start_date_obj, end_date_obj = end_date_obj, start_date_obj
        start_date, end_date = end_date, start_date
    
    employee = Employee.query.get_or_404(employee_id)
    
    # Get attendance records for the employee in the date range
    records = Attendance.query.filter_by(employee_id=employee_id)\
        .filter(Attendance.date >= start_date_obj, Attendance.date <= end_date_obj)\
        .order_by(Attendance.date.desc()).all()
    
    # Create a dictionary of attendance records by date for quick lookup
    attendance_dict = {}
    for rec in records:
        attendance_dict[rec.date] = rec
    
    # Generate all dates in the range
    current_date = start_date_obj
    attendance_list = []
    total_hours = 0
    total_days = 0
    present_days = 0
    holiday_days = 0
    
    while current_date <= end_date_obj:
        total_days += 1
        
        if current_date in attendance_dict:
            rec = attendance_dict[current_date]
            # Calculate duration
            duration = ""
            duration_hours = 0
            if rec.checkin_time and rec.checkout_time:
                delta = (
                    datetime.combine(rec.date, rec.checkout_time) -
                    datetime.combine(rec.date, rec.checkin_time)
                )
                total_seconds = int(delta.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                duration = f"{hours:02}:{minutes:02}"
                duration_hours = hours + (minutes / 60)
                total_hours += duration_hours
                present_days += 1
            
            # Determine status
            status = "Complete"
            if not rec.checkin_time:
                status = "No Record"
            elif not rec.checkout_time:
                status = "Checked In"
            
            import pytz
            utc = pytz.utc
            ist = pytz.timezone('Asia/Kolkata')
            if rec.checkin_time:
                dt_utc = datetime.combine(rec.date, rec.checkin_time).replace(tzinfo=utc)
                dt_ist = dt_utc.astimezone(ist)
                checkin_time_str = dt_ist.strftime('%I:%M %p')
                # Calculate late login based on IST
                late_login = dt_ist.time() > datetime.strptime('09:30:00', '%H:%M:%S').time()
            else:
                checkin_time_str = '-'
                late_login = False
            if rec.checkout_time:
                dt_utc = datetime.combine(rec.date, rec.checkout_time).replace(tzinfo=utc)
                dt_ist = dt_utc.astimezone(ist)
                checkout_time_str = dt_ist.strftime('%I:%M %p')
            else:
                checkout_time_str = '-'
            attendance_list.append({
                'date': rec.date.strftime('%Y-%m-%d'),
                'day_name': rec.date.strftime('%A'),
                'checkin_time': checkin_time_str,
                'checkout_time': checkout_time_str,
                'duration': duration or '-',
                'duration_hours': duration_hours,
                'status': status,
                'late_login': late_login
            })
        else:
            # Check if it's a holiday (Sunday or second Saturday)
            day_name = current_date.strftime('%A')
            day_of_month = current_date.day
            
            # Check if it's Sunday
            is_sunday = day_name == 'Sunday'
            
            # Check if it's second Saturday (second Saturday of the month)
            is_second_saturday = False
            if day_name == 'Saturday':
                # Count how many Saturdays have occurred in this month up to this date
                saturday_count = 0
                for i in range(1, day_of_month + 1):
                    check_date = current_date.replace(day=i)
                    if check_date.strftime('%A') == 'Saturday':
                        saturday_count += 1
                is_second_saturday = saturday_count == 2
            
            if is_sunday or is_second_saturday:
                # Mark as holiday
                holiday_days += 1
                attendance_list.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day_name': current_date.strftime('%A'),
                    'checkin_time': '-',
                    'checkout_time': '-',
                    'duration': '-',
                    'duration_hours': 0,
                    'status': 'Holiday',
                    'late_login': False
                })
            else:
                # No attendance record for this date - mark as absent
                attendance_list.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day_name': current_date.strftime('%A'),
                    'checkin_time': '-',
                    'checkout_time': '-',
                    'duration': '-',
                    'duration_hours': 0,
                    'status': 'Absent',
                    'late_login': False
                })
        
        current_date += timedelta(days=1)
    
    # Sort by date (newest first) - convert string date back to date object for proper sorting
    attendance_list.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d').date(), reverse=True)
    
    # Calculate working days (excluding holidays)
    working_days = total_days - holiday_days
    
    return render_template('hr/employee_attendance.html', 
                         employee=employee, 
                         attendance_records=attendance_list,
                         processed_records=attendance_list,
                         total_hours=round(total_hours, 2),
                         total_days=total_days,
                         present_days=present_days,
                         working_days=working_days,
                         start_date=start_date,
                         end_date=end_date)

@main.route('/hr/attendance')
@login_required
@role_required(['hr', 'admin'])
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
        import pytz
        utc = pytz.utc
        ist = pytz.timezone('Asia/Kolkata')
        if rec.checkin_time:
            dt_utc = datetime.combine(rec.date, rec.checkin_time).replace(tzinfo=utc)
            dt_ist = dt_utc.astimezone(ist)
            checkin_time_str = dt_ist.strftime('%I:%M:%S %p')
            # Calculate late login based on IST
            late_login = dt_ist.time() > datetime.strptime('09:30:00', '%H:%M:%S').time()
        else:
            checkin_time_str = '-'
            late_login = False
        if rec.checkout_time:
            dt_utc = datetime.combine(rec.date, rec.checkout_time).replace(tzinfo=utc)
            dt_ist = dt_utc.astimezone(ist)
            checkout_time_str = dt_ist.strftime('%I:%M:%S %p')
        else:
            checkout_time_str = '-'
        attendance_list.append({
            'employee_name': rec.employee.name,
            'date': rec.date.strftime('%Y-%m-%d'),
            'checkin_time': checkin_time_str,
            'checkout_time': checkout_time_str,
            'duration': duration or '-',
            'late_login': late_login
        })
    return render_template('hr/view_attendance.html', attendance=attendance_list)

@main.route('/hr/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
@login_required
@role_required(['hr', 'admin'])
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
            db.session.commit()
            message = 'Employee details updated successfully!'
    return render_template('hr/edit_employee.html', employee=employee, user=user, message=message)

@main.route('/hr/reset_employee_password/<int:employee_id>', methods=['POST'])
@login_required
@role_required(['hr', 'admin'])
def reset_employee_password(employee_id):
    """Backwards-compatible: redirect to interactive reset page."""
    return redirect(url_for('main.reset_password', employee_id=employee_id))

@main.route('/hr/reset_password/<int:employee_id>', methods=['GET', 'POST'])
@login_required
@role_required(['hr', 'admin'])
def reset_password(employee_id):
    """Show confirmation page; generate password only on POST."""
    from app.models import Employee, User
    import secrets
    import string
    
    employee = Employee.query.get_or_404(employee_id)
    user = User.query.get(employee.user_id)
    if not user:
        flash('User account not found for this employee.', 'error')
        return redirect('/hr/employees')
    
    if request.method == 'POST':
        def generate_temp_password():
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            return ''.join(secrets.choice(alphabet) for i in range(12))
        temp_password = generate_temp_password()
        user.set_password(temp_password)
        user.temporary_password = True
        db.session.commit()
        return render_template('hr/reset_password_confirmation.html',
                               temp_password=temp_password,
                               employee_name=employee.name,
                               employee_id=employee_id)
    
    return render_template('hr/reset_password_confirmation.html',
                           temp_password=None,
                           employee_name=employee.name,
                           employee_id=employee_id)

@main.route('/hr/view_reset_password')
@login_required
@role_required(['hr', 'admin'])
def view_reset_password():
    """Display the temporary password after reset"""
    temp_password = session.get('temp_password')
    employee_name = session.get('reset_employee_name')
    
    if not temp_password or not employee_name:
        flash('No password reset information found.', 'error')
        return redirect('/hr/employees')
    
    # Clear the session data after displaying
    session.pop('temp_password', None)
    session.pop('reset_employee_name', None)
    employee_id = session.pop('reset_employee_id', None)
    
    return render_template('hr/reset_password_confirmation.html', 
                         temp_password=temp_password, 
                         employee_name=employee_name,
                         employee_id=employee_id)

@main.route('/hr/delete_employee/<int:employee_id>', methods=['POST'])
@login_required
@role_required(['hr', 'admin'])
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
    session.permanent = False  # Reset session to non-permanent
    return redirect(url_for('main.login'))

@main.route('/employee/leave_request', methods=['GET', 'POST'])
@login_required
@role_required(['employee'])
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
@login_required
@role_required(['hr', 'admin'])
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
@login_required
@role_required(['employee'])
def leave_status():
    from app.models import Employee, LeaveRequest
    leave_requests = []
    if 'user_id' in session:
        employee = Employee.query.filter_by(user_id=session['user_id']).first()
        if employee:
            leave_requests = LeaveRequest.query.filter_by(employee_id=employee.id).order_by(LeaveRequest.request_date.desc()).all()
    return render_template('employee/leave_status.html', leave_requests=leave_requests)


@main.route('/employee/profile')
@login_required
@role_required(['employee'])
def employee_profile():
    user_id = session.get('user_id')
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

@main.route('/employee/attendance_report', methods=['GET'])
@login_required
@role_required(['employee'])
def employee_attendance_report():
    from app.models import Employee, Attendance, User
    from datetime import date, datetime, timedelta
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Default to current month if no dates provided
    if not start_date:
        start_date = (date.today().replace(day=1)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = date.today().strftime('%Y-%m-%d')
    
    # Convert string dates to date objects
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Validate date range
    if start_date_obj > end_date_obj:
        flash('Start date cannot be after end date.')
        start_date_obj, end_date_obj = end_date_obj, start_date_obj
        start_date, end_date = end_date, start_date
    
    # Get current employee
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    employee = Employee.query.filter_by(user_id=user_id).first() if user_id else None
    
    if not employee:
        flash('Employee record not found.')
        return redirect(url_for('main.employee_dashboard'))
    
    # Get attendance records for the employee in the date range
    records = Attendance.query.filter_by(employee_id=employee.id)\
        .filter(Attendance.date >= start_date_obj, Attendance.date <= end_date_obj)\
        .order_by(Attendance.date.desc()).all()
    
    # Create a dictionary of attendance records by date for quick lookup
    attendance_dict = {}
    for rec in records:
        attendance_dict[rec.date] = rec
    
    # Generate all dates in the range
    current_date = start_date_obj
    attendance_list = []
    total_hours = 0
    total_days = 0
    present_days = 0
    
    while current_date <= end_date_obj:
        total_days += 1
        
        if current_date in attendance_dict:
            rec = attendance_dict[current_date]
            # Calculate duration
            duration = ""
            duration_hours = 0
            if rec.checkin_time and rec.checkout_time:
                delta = (
                    datetime.combine(rec.date, rec.checkout_time) -
                    datetime.combine(rec.date, rec.checkin_time)
                )
                total_seconds = int(delta.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                duration = f"{hours:02}:{minutes:02}"
                duration_hours = hours + (minutes / 60)
                total_hours += duration_hours
                present_days += 1
            
            # Determine status
            status = "Present"
            if not rec.checkin_time:
                status = "Absent"
            elif not rec.checkout_time:
                status = "Checked In"
            
            import pytz
            utc = pytz.utc
            ist = pytz.timezone('Asia/Kolkata')
            if rec.checkin_time:
                dt_utc = datetime.combine(rec.date, rec.checkin_time).replace(tzinfo=utc)
                dt_ist = dt_utc.astimezone(ist)
                checkin_time_str = dt_ist.strftime('%I:%M %p')
            else:
                checkin_time_str = '-'
            if rec.checkout_time:
                dt_utc = datetime.combine(rec.date, rec.checkout_time).replace(tzinfo=utc)
                dt_ist = dt_utc.astimezone(ist)
                checkout_time_str = dt_ist.strftime('%I:%M %p')
            else:
                checkout_time_str = '-'
            attendance_list.append({
                'date': rec.date.strftime('%Y-%m-%d'),
                'day_name': rec.date.strftime('%A'),
                'checkin_time': checkin_time_str,
                'checkout_time': checkout_time_str,
                'duration': duration or '-',
                'duration_hours': duration_hours,
                'status': status,
                'late_login': rec.late_login
            })
        else:
            # Check if it's a holiday (Sunday or second Saturday)
            day_name = current_date.strftime('%A')
            day_of_month = current_date.day
            
            # Check if it's Sunday
            is_sunday = day_name == 'Sunday'
            
            # Check if it's second Saturday (second Saturday of the month)
            is_second_saturday = False
            if day_name == 'Saturday':
                # Count how many Saturdays have occurred in this month up to this date
                saturday_count = 0
                for i in range(1, day_of_month + 1):
                    check_date = current_date.replace(day=i)
                    if check_date.strftime('%A') == 'Saturday':
                        saturday_count += 1
                is_second_saturday = saturday_count == 2
            
            if is_sunday or is_second_saturday:
                # Mark as holiday
                attendance_list.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day_name': current_date.strftime('%A'),
                    'checkin_time': '-',
                    'checkout_time': '-',
                    'duration': '-',
                    'duration_hours': 0,
                    'status': 'Holiday',
                    'late_login': False
                })
            else:
                # No attendance record for this date - mark as absent
                attendance_list.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day_name': current_date.strftime('%A'),
                    'checkin_time': '-',
                    'checkout_time': '-',
                    'duration': '-',
                    'duration_hours': 0,
                    'status': 'Absent',
                    'late_login': False
                })
        
        current_date += timedelta(days=1)
    
    # Sort by date (newest first) - convert string date back to date object for proper sorting
    attendance_list.sort(key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d').date(), reverse=True)
    
    return render_template('employee/attendance_report.html', 
                         attendance=attendance_list,
                         employee=employee,
                         start_date=start_date,
                         end_date=end_date,
                         total_hours=round(total_hours, 2),
                         total_days=total_days,
                         present_days=present_days)
