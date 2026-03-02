from flask import Blueprint

legal_bp = Blueprint('legal', __name__)

from app.legal import routes
