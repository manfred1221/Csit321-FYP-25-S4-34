from flask import Flask
from flask_cors import CORS

# import blueprints
from routes.auth_routes import auth_bp
from routes.resident_routes import resident_bp
from routes.visitor_routes import visitor_bp


app = Flask(__name__)
CORS(app)

# register blueprints
app.register_blueprint(auth_bp, url_prefix="/api/auth")
app.register_blueprint(resident_bp, url_prefix="/api/resident")
app.register_blueprint(visitor_bp, url_prefix="/api/visitor")


@app.route("/")   # simple health check
def home():
    return {"message": "Resident Backend Running"}, 200


if __name__ == "__main__":
    app.run(debug=True, port=5001)
