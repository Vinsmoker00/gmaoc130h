import os
from pathlib import Path


class BaseConfig:
    SECRET_KEY = os.environ.get("GMAO_SECRET", "change-me")
    BASE_DIR = Path(__file__).resolve().parent
    DEFAULT_UPLOAD_ROOT = BASE_DIR.parent / "uploads"
    UPLOAD_ROOT = Path(os.environ.get("GMAO_UPLOAD_ROOT", DEFAULT_UPLOAD_ROOT)).expanduser().resolve()
    JOB_CARD_UPLOAD_SUBDIR = "job_cards"
    JOB_CARD_ALLOWED_MIME_TYPES = {"application/pdf"}
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "GMAO_DATABASE_URI", f"sqlite:///{BASE_DIR.parent / 'gmao.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECURITY_PASSWORD_SALT = os.environ.get("GMAO_PASSWORD_SALT", "gmao-salt")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
