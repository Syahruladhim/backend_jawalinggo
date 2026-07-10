import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    MONGO_URI = os.getenv("MONGO_URI", "")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "jawalinggo")
    GOOGLE_AI_API_KEY = os.getenv("GOOGLE_AI_API_KEY", "")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    BREVO_API_URL = os.getenv(
        "BREVO_API_URL", "https://api.brevo.com/v3/smtp/email"
    )
    BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
    BREVO_FROM_EMAIL = os.getenv("BREVO_FROM_EMAIL", "")
    BREVO_FROM_NAME = os.getenv("BREVO_FROM_NAME", "Jawalinggo")
    BREVO_TIMEOUT_SECONDS = int(os.getenv("BREVO_TIMEOUT_SECONDS", "15"))
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    PORT = int(os.getenv("PORT", "5000"))
