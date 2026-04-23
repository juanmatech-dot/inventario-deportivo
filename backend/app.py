from flask import Flask
from flask_cors import CORS
from routes.equipos  import equipos_bp
from routes.usuarios import usuarios_bp

import os

base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, '../frontend')

app = Flask(__name__, template_folder=template_dir)

app.secret_key = "bienestar_universitario_2024"
CORS(app, supports_credentials=True)

app.register_blueprint(equipos_bp)
app.register_blueprint(usuarios_bp)

from flask import render_template

@app.route("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)