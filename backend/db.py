import mysql.connector
from mysql.connector import Error

# Cambia estos datos por los de tu MySQL Workbench
DB_CONFIG = {
    "host":     "localhost",
    "user":     "root",         # tu usuario de MySQL
    "password": "1234",         # tu contraseña de MySQL
    "database": "inventario_deportivo"
}

def get_connection():
    """Retorna una conexión activa a la base de datos."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error conectando a MySQL: {e}")
        return None