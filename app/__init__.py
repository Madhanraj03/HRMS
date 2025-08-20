from flask import Flask, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint
import base64

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    db.init_app(app)

    # Configure session security
    app.config['PERMANENT_SESSION_LIFETIME'] = app.config.get('PERMANENT_SESSION_LIFETIME')
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('SESSION_COOKIE_SECURE', False)
    app.config['SESSION_COOKIE_HTTPONLY'] = app.config.get('SESSION_COOKIE_HTTPONLY', True)
    app.config['SESSION_COOKIE_SAMESITE'] = app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')

    # Create database tables after everything is set up
    with app.app_context():
        db.create_all()

    # Register custom Jinja2 filters
    @app.template_filter('b64encode')
    def b64encode_filter(data):
        if data:
            return base64.b64encode(data).decode('utf-8')
        return ''

    @app.template_filter('user_by_id')
    def user_by_id_filter(user_id):
        from app.models import User
        return User.query.get(user_id)

    # Global login guard: allow only whitelisted endpoints without auth
    @app.before_request
    def require_login_for_all():
        # Allow static files and favicon
        if request.endpoint in (None, 'static'):
            return None
        # Allow login and logout routes
        if request.endpoint in (
            'main.login',
            'main.logout',
            'main.unauthorized',
        ):
            return None
        # If not logged in, redirect to login
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        return None

    from app.routes import main
    app.register_blueprint(main)

    from app.employee.routes import employee as employee_blueprint
    app.register_blueprint(employee_blueprint)

    from app.admin.routes import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    return app
