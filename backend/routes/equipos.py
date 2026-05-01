from flask import Blueprint, request, jsonify, session
from db import get_connection

equipos_bp = Blueprint("equipos", __name__)


def es_admin():
    return session.get("rol") == "admin"


def usuario_actual_id():
    return session.get("usuario_id")


def requiere_login():
    if not usuario_actual_id():
        return jsonify({"error": "Debes iniciar sesión"}), 401
    return None


def requiere_admin():
    auth = requiere_login()
    if auth:
        return auth
    if not es_admin():
        return jsonify({"error": "No tienes permisos para realizar esta acción"}), 403
    return None


def formatear_fecha(valor):
    return valor.strftime("%Y-%m-%d %H:%M") if valor else None


@equipos_bp.route("/api/equipos", methods=["GET"])
def get_equipos():
    auth = requiere_login()
    if auth:
        return auth
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


@equipos_bp.route("/api/equipos/stock-bajo", methods=["GET"])
def stock_bajo():
    auth = requiere_admin()
    if auth:
        return auth
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM vista_stock_bajo")
    r = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(r), 200


@equipos_bp.route("/api/equipos", methods=["POST"])
def crear_equipo():
    auth = requiere_admin()
    if auth:
        return auth
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


@equipos_bp.route("/api/equipos/<int:id>", methods=["PUT"])
def actualizar_equipo(id):
    auth = requiere_admin()
    if auth:
        return auth
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


@equipos_bp.route("/api/equipos/<int:id>", methods=["DELETE"])
def eliminar_equipo(id):
    auth = requiere_admin()
    if auth:
        return auth
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor()
    cursor.execute("UPDATE equipos SET activo=0 WHERE id=%s", (id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"mensaje": "Equipo eliminado"}), 200


@equipos_bp.route("/api/prestamos", methods=["POST"])
def crear_prestamo():
    auth = requiere_login()
    if auth:
        return auth
    data = request.get_json()
    id_equipo = data.get("id_equipo")
    id_usuario = usuario_actual_id()
    cantidad = int(data.get("cantidad", 1))
    if not id_equipo:
        return jsonify({"error": "Datos incompletos"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM reportes
        WHERE id_usuario=%s AND tipo='daño'
    """, (id_usuario,))
    reportes_dano = cursor.fetchone()["total"]
    if reportes_dano > 5:
        cursor.close(); conn.close()
        return jsonify({"error": "No se puede prestar: el estudiante tiene más de 5 reportes por daño"}), 403
    cursor.execute("SELECT stock_disponible, nombre FROM equipos WHERE id=%s AND activo=1", (id_equipo,))
    equipo = cursor.fetchone()
    if not equipo:
        cursor.close(); conn.close()
        return jsonify({"error": "Equipo no encontrado"}), 404
    if equipo["stock_disponible"] < cantidad:
        cursor.close(); conn.close()
        return jsonify({"error": f"Solo hay {equipo['stock_disponible']} unidades disponibles"}), 400
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO prestamos (id_equipo, id_usuario, cantidad) VALUES (%s, %s, %s)
    """, (id_equipo, id_usuario, cantidad))
    nuevo_id = cursor.lastrowid
    cursor.execute("""
        UPDATE equipos SET stock_disponible = stock_disponible - %s WHERE id = %s
    """, (cantidad, id_equipo))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"mensaje": "Préstamo registrado exitosamente", "id": nuevo_id}), 201


@equipos_bp.route("/api/prestamos", methods=["GET"])
def get_prestamos():
    auth = requiere_login()
    if auth:
        return auth
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    filtro_usuario = "" if es_admin() else "WHERE p.id_usuario = %s"
    params = () if es_admin() else (usuario_actual_id(),)
    cursor.execute(f"""
        SELECT p.id, p.id_usuario, p.fecha_prestamo, p.fecha_devolucion,
               p.cantidad, p.estado,
               e.nombre AS equipo, u.nombre AS usuario, u.email
        FROM prestamos p
        JOIN equipos  e ON p.id_equipo  = e.id
        JOIN usuarios u ON p.id_usuario = u.id
        {filtro_usuario}
        ORDER BY p.fecha_prestamo DESC
    """, params)
    prestamos = cursor.fetchall()
    for p in prestamos:
        p["fecha_prestamo"] = formatear_fecha(p["fecha_prestamo"])
        p["fecha_devolucion"] = formatear_fecha(p["fecha_devolucion"])
    cursor.close(); conn.close()
    return jsonify(prestamos), 200


@equipos_bp.route("/api/prestamos/<int:id>/solicitar-devolucion", methods=["PUT"])
def solicitar_devolucion(id):
    auth = requiere_login()
    if auth:
        return auth
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_usuario, estado FROM prestamos WHERE id=%s", (id,))
    prestamo = cursor.fetchone()
    if not prestamo:
        cursor.close(); conn.close()
        return jsonify({"error": "Préstamo no encontrado"}), 404
    if not es_admin() and prestamo["id_usuario"] != usuario_actual_id():
        cursor.close(); conn.close()
        return jsonify({"error": "No puedes marcar préstamos de otro usuario"}), 403
    if prestamo["estado"] != "activo":
        cursor.close(); conn.close()
        return jsonify({"error": "Este préstamo no está activo"}), 400
    cursor = conn.cursor()
    cursor.execute("UPDATE prestamos SET estado='devolucion_pendiente' WHERE id=%s", (id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"mensaje": "Devolución marcada para revisión del administrador"}), 200


@equipos_bp.route("/api/prestamos/<int:id>/devolver", methods=["PUT"])
def devolver(id):
    auth = requiere_admin()
    if auth:
        return auth
    data = request.get_json(silent=True) or {}
    estado_equipo = data.get("estado_equipo", "bueno")
    descripcion = data.get("descripcion", "").strip()
    if estado_equipo not in ["bueno", "danado"]:
        return jsonify({"error": "Estado de equipo inválido"}), 400
    if estado_equipo == "danado" and not descripcion:
        return jsonify({"error": "Describe el daño encontrado"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_equipo, id_usuario, cantidad, estado FROM prestamos WHERE id=%s", (id,))
    prestamo = cursor.fetchone()
    if not prestamo:
        cursor.close(); conn.close()
        return jsonify({"error": "Préstamo no encontrado"}), 404
    if prestamo["estado"] in ["devuelto", "con_novedad"]:
        cursor.close(); conn.close()
        return jsonify({"error": "Este préstamo ya fue cerrado"}), 400
    nuevo_estado = "devuelto" if estado_equipo == "bueno" else "con_novedad"
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE prestamos SET estado=%s, fecha_devolucion=NOW() WHERE id=%s
    """, (nuevo_estado, id))
    cursor.execute("""
        UPDATE equipos SET stock_disponible = stock_disponible + %s WHERE id=%s
    """, (prestamo["cantidad"], prestamo["id_equipo"]))
    if estado_equipo == "danado":
        cursor.execute("""
            INSERT INTO reportes (id_prestamo, id_usuario, tipo, descripcion)
            VALUES (%s, %s, 'daño', %s)
        """, (id, prestamo["id_usuario"], descripcion))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"mensaje": "Devolución registrada"}), 200


@equipos_bp.route("/api/reportes", methods=["POST"])
def crear_reporte():
    auth = requiere_admin()
    if auth:
        return auth
    data = request.get_json()
    for campo in ["id_prestamo", "tipo", "descripcion"]:
        if not data.get(campo):
            return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_usuario FROM prestamos WHERE id=%s", (data["id_prestamo"],))
    prestamo = cursor.fetchone()
    if not prestamo:
        cursor.close(); conn.close()
        return jsonify({"error": "Préstamo no encontrado"}), 404
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reportes (id_prestamo, id_usuario, tipo, descripcion)
        VALUES (%s, %s, %s, %s)
    """, (data["id_prestamo"], prestamo["id_usuario"], data["tipo"], data["descripcion"]))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({"mensaje": "Reporte enviado"}), 201


@equipos_bp.route("/api/reportes", methods=["GET"])
def get_reportes():
    auth = requiere_admin()
    if auth:
        return auth
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.id, r.tipo, r.descripcion, r.fecha,
               e.nombre AS equipo,
               u.nombre AS usuario,
               u.email,
               p.cantidad, p.estado AS estado_prestamo
        FROM reportes r
        JOIN prestamos p ON r.id_prestamo = p.id
        JOIN equipos   e ON p.id_equipo   = e.id
        JOIN usuarios  u ON r.id_usuario  = u.id
        ORDER BY r.fecha DESC
    """)
    reportes = cursor.fetchall()
    for rep in reportes:
        rep["fecha"] = formatear_fecha(rep["fecha"])
    cursor.close(); conn.close()
    return jsonify(reportes), 200


@equipos_bp.route("/api/reportes/resumen-estudiantes", methods=["GET"])
def resumen_reportes_estudiantes():
    auth = requiere_admin()
    if auth:
        return auth
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id, u.nombre, u.email,
               COUNT(r.id) AS total_reportes,
               SUM(CASE WHEN r.tipo='daño' THEN 1 ELSE 0 END) AS reportes_dano
        FROM usuarios u
        JOIN reportes r ON r.id_usuario = u.id
        GROUP BY u.id, u.nombre, u.email
        ORDER BY total_reportes DESC, u.nombre
    """)
    resumen = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(resumen), 200


@equipos_bp.route("/api/prestamos/mas-solicitados", methods=["GET"])
def mas_solicitados():
    auth = requiere_admin()
    if auth:
        return auth
    conn = get_connection()
    if not conn:
        return jsonify({"error": "Sin conexión"}), 500
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT e.id, e.nombre, c.nombre AS categoria,
               SUM(p.cantidad) AS total_solicitado,
               COUNT(p.id) AS veces_solicitado,
               e.stock_total, e.stock_disponible
        FROM prestamos p
        JOIN equipos e ON p.id_equipo = e.id
        JOIN categorias c ON e.id_categoria = c.id
        WHERE p.fecha_prestamo >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY e.id, e.nombre, c.nombre, e.stock_total, e.stock_disponible
        ORDER BY total_solicitado DESC, veces_solicitado DESC, e.nombre
    """)
    productos = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(productos), 200
