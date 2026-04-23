from flask import Blueprint, request, jsonify
from db import get_connection

equipos_bp = Blueprint("equipos", __name__)

# ── GET /api/equipos ───────────────────────────────────────
@equipos_bp.route("/api/equipos", methods=["GET"])
def get_equipos():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.id, e.nombre, e.descripcion,
               e.stock_total, e.stock_disponible, e.stock_minimo,
               c.nombre AS categoria
        FROM equipos e
        JOIN categorias c ON e.id_categoria = c.id
        WHERE e.activo = 1 ORDER BY e.nombre
    """)
    equipos = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(equipos), 200

# ── GET /api/equipos/stock-bajo ────────────────────────────
@equipos_bp.route("/api/equipos/stock-bajo", methods=["GET"])
def stock_bajo():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM vista_stock_bajo")
    r = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(r), 200

# ── POST /api/equipos ──────────────────────────────────────
@equipos_bp.route("/api/equipos", methods=["POST"])
def crear_equipo():
    data = request.get_json()
    for campo in ["nombre", "stock_total", "id_categoria"]:
        if not data.get(campo) and data.get(campo) != 0:
            return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    stock = int(data["stock_total"])
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO equipos (nombre, descripcion, id_categoria, stock_total, stock_disponible, stock_minimo)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (data["nombre"], data.get("descripcion",""), data["id_categoria"],
          stock, stock, data.get("stock_minimo", 2)))
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close(); conn.close()
    return jsonify({"mensaje": "Equipo registrado", "id": nuevo_id}), 201

# ── PUT /api/equipos/<id> ──────────────────────────────────
@equipos_bp.route("/api/equipos/<int:id>", methods=["PUT"])
def actualizar_equipo(id):
    data = request.get_json()
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE equipos SET nombre=%s, descripcion=%s,
               stock_total=%s, stock_minimo=%s, id_categoria=%s
        WHERE id=%s AND activo=1
    """, (data["nombre"], data.get("descripcion",""),
          data["stock_total"], data.get("stock_minimo",2),
          data["id_categoria"], id))
    conn.commit()
    filas = cursor.rowcount
    cursor.close(); conn.close()
    if filas == 0:
        return jsonify({"error": "Equipo no encontrado"}), 404
    return jsonify({"mensaje": "Equipo actualizado"}), 200

# ── DELETE /api/equipos/<id> ───────────────────────────────
@equipos_bp.route("/api/equipos/<int:id>", methods=["DELETE"])
def eliminar_equipo(id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor()
    cursor.execute("UPDATE equipos SET activo=0 WHERE id=%s", (id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"mensaje": "Equipo eliminado"}), 200

# ── POST /api/prestamos ────────────────────────────────────
# El estudiante solicita un préstamo → baja stock_disponible
@equipos_bp.route("/api/prestamos", methods=["POST"])
def crear_prestamo():
    data = request.get_json()
    id_equipo  = data.get("id_equipo")
    id_usuario = data.get("id_usuario")
    cantidad   = int(data.get("cantidad", 1))
    if not id_equipo or not id_usuario:
        return jsonify({"error": "Datos incompletos"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    # Verificar disponibilidad
    cursor.execute("SELECT stock_disponible, nombre FROM equipos WHERE id=%s AND activo=1", (id_equipo,))
    equipo = cursor.fetchone()
    if not equipo:
        cursor.close(); conn.close()
        return jsonify({"error": "Equipo no encontrado"}), 404
    if equipo["stock_disponible"] < cantidad:
        cursor.close(); conn.close()
        return jsonify({"error": f"Solo hay {equipo['stock_disponible']} unidades disponibles"}), 400
    # Registrar préstamo y descontar stock
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO prestamos (id_equipo, id_usuario, cantidad) VALUES (%s, %s, %s)
    """, (id_equipo, id_usuario, cantidad))
    cursor.execute("""
        UPDATE equipos SET stock_disponible = stock_disponible - %s WHERE id = %s
    """, (cantidad, id_equipo))
    conn.commit()
    nuevo_id = cursor.lastrowid
    cursor.close(); conn.close()
    return jsonify({"mensaje": "Préstamo registrado exitosamente", "id": nuevo_id}), 201

# ── GET /api/prestamos ─────────────────────────────────────
@equipos_bp.route("/api/prestamos", methods=["GET"])
def get_prestamos():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.id, p.fecha_prestamo, p.fecha_devolucion,
               p.cantidad, p.estado,
               e.nombre AS equipo, u.nombre AS usuario, u.email
        FROM prestamos p
        JOIN equipos  e ON p.id_equipo  = e.id
        JOIN usuarios u ON p.id_usuario = u.id
        ORDER BY p.fecha_prestamo DESC
    """)
    prestamos = cursor.fetchall()
    for p in prestamos:
        if p["fecha_prestamo"]:
            p["fecha_prestamo"] = p["fecha_prestamo"].strftime("%Y-%m-%d %H:%M")
        if p["fecha_devolucion"]:
            p["fecha_devolucion"] = p["fecha_devolucion"].strftime("%Y-%m-%d %H:%M")
    cursor.close(); conn.close()
    return jsonify(prestamos), 200

# ── PUT /api/prestamos/<id>/devolver ──────────────────────
# Devuelve el equipo → sube stock_disponible
@equipos_bp.route("/api/prestamos/<int:id>/devolver", methods=["PUT"])
def devolver(id):
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_equipo, cantidad, estado FROM prestamos WHERE id=%s", (id,))
    prestamo = cursor.fetchone()
    if not prestamo:
        cursor.close(); conn.close()
        return jsonify({"error": "Préstamo no encontrado"}), 404
    if prestamo["estado"] == "devuelto":
        cursor.close(); conn.close()
        return jsonify({"error": "Este préstamo ya fue devuelto"}), 400
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE prestamos SET estado='devuelto', fecha_devolucion=NOW() WHERE id=%s
    """, (id,))
    cursor.execute("""
        UPDATE equipos SET stock_disponible = stock_disponible + %s WHERE id=%s
    """, (prestamo["cantidad"], prestamo["id_equipo"]))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"mensaje": "Devolución registrada"}), 200

# ── POST /api/reportes ─────────────────────────────────────
@equipos_bp.route("/api/reportes", methods=["POST"])
def crear_reporte():
    data = request.get_json()
    for campo in ["id_prestamo", "id_usuario", "tipo", "descripcion"]:
        if not data.get(campo):
            return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reportes (id_prestamo, id_usuario, tipo, descripcion)
        VALUES (%s, %s, %s, %s)
    """, (data["id_prestamo"], data["id_usuario"], data["tipo"], data["descripcion"]))
    # Marcar el préstamo con novedad
    cursor.execute("UPDATE prestamos SET estado='con_novedad' WHERE id=%s", (data["id_prestamo"],))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"mensaje": "Reporte enviado"}), 201

# ── GET /api/reportes ──────────────────────────────────────
@equipos_bp.route("/api/reportes", methods=["GET"])
def get_reportes():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id, r.tipo, r.descripcion, r.fecha,
               e.nombre AS equipo,
               u.nombre AS usuario,
               p.cantidad, p.estado AS estado_prestamo
        FROM reportes r
        JOIN prestamos p ON r.id_prestamo = p.id
        JOIN equipos   e ON p.id_equipo   = e.id
        JOIN usuarios  u ON r.id_usuario  = u.id
        ORDER BY r.fecha DESC
    """)
    reportes = cursor.fetchall()
    for rep in reportes:
        if rep["fecha"]:
            rep["fecha"] = rep["fecha"].strftime("%Y-%m-%d %H:%M")
    cursor.close(); conn.close()
    return jsonify(reportes), 200