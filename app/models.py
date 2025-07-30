from app import db
from datetime import date
from flask import url_for

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  # Plain text password (not secure)
    role = db.Column(db.String(20), nullable=False)  # 'employee', 'hr', 'admin'

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
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


