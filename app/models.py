from app import db
from datetime import date
from flask import url_for
from app.password_utils import PasswordManager

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Hashed password (secure)
    salt = db.Column(db.String(255), nullable=True)  # Salt for encryption/decryption
    temporary_password = db.Column(db.Boolean, default=False)  # Flag for temporary passwords
    role = db.Column(db.String(20), nullable=False)  # 'employee', 'hr', 'admin'
    name = db.Column(db.String(100), nullable=True)  # Full name for HR and Admin users
    
    def set_password(self, password):
        """Set a hashed password for the user"""
        self.password = PasswordManager.hash_password(password)
        # Clear temporary password flag when setting new password
        self.temporary_password = False
    
    def check_password(self, password):
        """Check if the provided password matches the stored hash"""
        return PasswordManager.verify_password(self.password, password)
    
    def encrypt_sensitive_data(self, data, password):
        """Encrypt sensitive data using the user's password"""
        encrypted_data, salt = PasswordManager.encrypt_data(data, password)
        self.salt = PasswordManager.salt_to_string(salt)
        return encrypted_data
    
    def decrypt_sensitive_data(self, encrypted_data, password):
        """Decrypt sensitive data using the user's password"""
        if not self.salt:
            raise ValueError("No salt available for decryption")
        salt = PasswordManager.string_to_salt(self.salt)
        return PasswordManager.decrypt_data(encrypted_data, password, salt)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False)  # 'Male', 'Female', 'Other'
    address = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    unique_id_number = db.Column(db.String(50), unique=True, nullable=False)
    job_role = db.Column(db.String(100), nullable=True)
    salary = db.Column(db.Float, nullable=True)  # Employee salary
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('employee', uselist=False, cascade="all, delete"))
    profile_pic = db.Column(db.LargeBinary, nullable=True)  # Store image data as binary
    profile_pic_mimetype = db.Column(db.String(255), nullable=True)  # Store the image mimetype

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    checkin_time = db.Column(db.Time)
    checkout_time = db.Column(db.Time)
    late_login = db.Column(db.Boolean, default=False)  # Track if employee logged in after 9:30 AM
    employee = db.relationship('Employee', backref=db.backref('attendances', lazy=True, cascade="all, delete"))

class LeaveRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Pending')  # Pending, Accepted, Rejected
    request_date = db.Column(db.Date, default=date.today)
    employee = db.relationship('Employee', backref=db.backref('leave_requests', lazy=True, cascade="all, delete"))


