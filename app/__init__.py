from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint
import base64

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('../config.py')
    db.init_app(app)

    # Register custom Jinja2 filters
    @app.template_filter('b64encode')
    def b64encode_filter(data):
        if data:
            return base64.b64encode(data).decode('utf-8')
        return ''

    from app.routes import main
    app.register_blueprint(main)

    from app.employee.routes import employee as employee_blueprint
    app.register_blueprint(employee_blueprint)

    from app.admin.routes import admin as admin_blueprint
    app.register_blueprint(admin_blueprint)

    return app
