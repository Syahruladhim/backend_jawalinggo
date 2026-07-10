from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.db import init_db
from app.routes.auth_routes import auth_bp
from app.routes.health_routes import health_bp
from app.routes.profile_routes import profile_bp
from app.routes.progress_routes import progress_bp
from app.routes.leaderboard_routes import leaderboard_bp
from app.routes.translate_routes import translate_bp
from app.routes.quiz_routes import quiz_bp
from app.routes.admin_routes import admin_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)
    init_db(app)

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(profile_bp, url_prefix="/api/profiles")
    app.register_blueprint(progress_bp, url_prefix="/api/progress")
    app.register_blueprint(translate_bp, url_prefix="/api/translate")
    app.register_blueprint(leaderboard_bp, url_prefix="/api/leaderboard")
    app.register_blueprint(quiz_bp, url_prefix="/api/quizzes")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    return app
