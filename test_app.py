import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, send_from_directory, render_template
from flask_cors import CORS
from routes.security_officer.security_officer_routes import security_officer_bp
from routes.security_officer.security_officer_model import db

test_app = Flask(__name__)
CORS(test_app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)


# PostgreSQL config
test_app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:joshua1102@localhost:5432/CSIT321: Face Recognition'
test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(test_app)
with test_app.app_context():
    db.create_all()

# Register blueprint
test_app.register_blueprint(security_officer_bp, url_prefix="/api/security_officer")

# Serve main index page
@test_app.route("/")
def index():
    return render_template("index.html")

# Optional: serve static files if needed
@test_app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

if __name__ == "__main__":
    test_app.run(debug=True, port=5001)