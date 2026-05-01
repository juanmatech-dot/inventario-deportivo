from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
from routes.equipos  import equipos_bp
from routes.usuarios import usuarios_bp

import os

base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, '../frontend')

app = Flask(__name__, template_folder=template_dir)

app.secret_key = "bienestar_universitario_2024"
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
CORS(app, supports_credentials=True, origins=[
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "null",
])

app.register_blueprint(equipos_bp)
app.register_blueprint(usuarios_bp)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/<page>")
def pages(page):
    allowed_pages = {"index.html", "registro.html", "inventario.html", "reportes.html"}
    if page in allowed_pages:
        return render_template(page)
    return render_template("index.html"), 404

@app.route("/assets/<path:filename>")
def frontend_assets(filename):
    return send_from_directory(os.path.join(template_dir, "assets"), filename)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
