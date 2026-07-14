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
import os
import firebase_admin
from firebase_admin import credentials
from app.routes.admin_routes import admin_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Firebase Admin
    firebase_cred_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'firebase.json')
    if os.path.exists(firebase_cred_path):
        if not firebase_admin._apps:
            cred = credentials.Certificate(firebase_cred_path)
            firebase_admin.initialize_app(cred)

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
