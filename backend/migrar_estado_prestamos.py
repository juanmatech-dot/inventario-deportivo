from db import get_connection


SQL = """
ALTER TABLE prestamos
MODIFY estado ENUM('activo','devolucion_pendiente','devuelto','con_novedad')
NOT NULL DEFAULT 'activo'
"""


conn = get_connection()
cursor = conn.cursor()
cursor.execute(SQL)
conn.commit()
cursor.close()
conn.close()
print("ENUM de prestamos.estado actualizado")
