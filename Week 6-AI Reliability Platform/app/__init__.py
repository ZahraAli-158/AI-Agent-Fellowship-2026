import os
import logging

from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

from config import Config
from app.models.models import db, User
from app.services import gemini_service, email_service
from app.services.skill_service import seed_skills

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # Bulletproof fix for "unable to open database file" on Windows: no
    # matter what DATABASE_URL is set to (relative, absolute, forward or
    # back slashes), always ensure the directory that will hold the SQLite
    # file actually exists BEFORE SQLAlchemy tries to open a connection to
    # it. This is almost always the real cause of that error.
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite:///"):
        db_file_path = db_uri[len("sqlite:///"):]
        db_dir = os.path.dirname(db_file_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    logging.basicConfig(level=logging.INFO)

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)

    gemini_service.configure(app.config.get("GEMINI_API_KEY", ""))
    email_service.configure(app.config.get("GMAIL_ADDRESS", ""), app.config.get("GMAIL_APP_PASSWORD", ""))

    from app.routes.auth_routes import auth_bp
    from app.routes.workspace_routes import workspace_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.knowledge_routes import knowledge_bp
    from app.routes.prompt_routes import prompt_bp
    from app.routes.skill_routes import skill_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.agent_routes import agent_bp
    from app.routes.observability_routes import observability_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(workspace_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(prompt_bp)
    app.register_blueprint(skill_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(agent_bp)
    app.register_blueprint(observability_bp)

    with app.app_context():
        db.create_all()
        seed_skills()

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.context_processor
    def inject_globals():
        return {"gemini_configured": gemini_service.is_configured()}

    return app
