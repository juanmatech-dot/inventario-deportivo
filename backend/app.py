from flask import Flask
from flask_cors import CORS
from routes.equipos  import equipos_bp
from routes.usuarios import usuarios_bp

app = Flask(__name__)
app.secret_key = "bienestar_universitario_2024"
CORS(app, supports_credentials=True)

app.register_blueprint(equipos_bp)
app.register_blueprint(usuarios_bp)

@app.route("/")
def index():
    return {"mensaje": "Sistema de Préstamos Bienestar Universitario ✓"}

if __name__ == "__main__":
    app.run(debug=True, port=5000)