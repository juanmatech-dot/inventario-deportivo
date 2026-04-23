-- ============================================================
--  SISTEMA DE PRÉSTAMOS - BIENESTAR UNIVERSITARIO
--  Base de datos MySQL
-- ============================================================
--  USUARIOS DE PRUEBA:
--  Admin → admin@universidad.edu.co  / admin123
--  User  → carlos@universidad.edu.co / user123
-- ============================================================

DROP DATABASE IF EXISTS inventario_deportivo;
CREATE DATABASE inventario_deportivo
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE inventario_deportivo;

-- Roles
CREATE TABLE roles (
  id     INT         NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(50) NOT NULL,
  PRIMARY KEY (id)
);

-- Usuarios
CREATE TABLE usuarios (
  id         INT          NOT NULL AUTO_INCREMENT,
  nombre     VARCHAR(100) NOT NULL,
  email      VARCHAR(100) NOT NULL UNIQUE,
  password   VARCHAR(255) NOT NULL,
  id_rol     INT          NOT NULL DEFAULT 2,
  activo     TINYINT(1)   NOT NULL DEFAULT 1,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  FOREIGN KEY (id_rol) REFERENCES roles(id)
);

-- Categorías
CREATE TABLE categorias (
  id     INT          NOT NULL AUTO_INCREMENT,
  nombre VARCHAR(100) NOT NULL,
  PRIMARY KEY (id)
);

-- Equipos (reemplaza "productos", sin precio)
CREATE TABLE equipos (
  id               INT          NOT NULL AUTO_INCREMENT,
  nombre           VARCHAR(150) NOT NULL,
  descripcion      TEXT,
  id_categoria     INT          NOT NULL,
  stock_total      INT          NOT NULL DEFAULT 0,
  stock_disponible INT          NOT NULL DEFAULT 0,
  stock_minimo     INT          NOT NULL DEFAULT 2,
  activo           TINYINT(1)   NOT NULL DEFAULT 1,
  created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  FOREIGN KEY (id_categoria) REFERENCES categorias(id)
);

-- Préstamos
CREATE TABLE prestamos (
  id          INT      NOT NULL AUTO_INCREMENT,
  id_equipo   INT      NOT NULL,
  id_usuario  INT      NOT NULL,
  cantidad    INT      NOT NULL DEFAULT 1,
  fecha_prestamo  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_devolucion DATETIME,
  estado      ENUM('activo','devuelto','con_novedad') NOT NULL DEFAULT 'activo',
  PRIMARY KEY (id),
  FOREIGN KEY (id_equipo)  REFERENCES equipos(id),
  FOREIGN KEY (id_usuario) REFERENCES usuarios(id)
);

-- Reportes de novedades
CREATE TABLE reportes (
  id          INT      NOT NULL AUTO_INCREMENT,
  id_prestamo INT      NOT NULL,
  id_usuario  INT      NOT NULL,
  tipo        ENUM('daño','perdida','retraso','otro') NOT NULL,
  descripcion TEXT     NOT NULL,
  fecha       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  FOREIGN KEY (id_prestamo) REFERENCES prestamos(id),
  FOREIGN KEY (id_usuario)  REFERENCES usuarios(id)
);

-- ============================================================
-- DATOS DE PRUEBA
-- ============================================================
INSERT INTO roles (nombre) VALUES ('admin'), ('usuario');

INSERT INTO usuarios (nombre, email, password, id_rol) VALUES
  ('Administrador','admin@universidad.edu.co',
   'scrypt:32768:8:1$gaap8Sb59igKUB4R$3127e3b2f1824ec8188e0712e37e329552dc2ccc1d0bd63919257b0ecb416de07a9855078a85b11d15646d57be5e5b4c5d15e334cdabf6aaf7d1d17f0dad3f7e',1),
  ('Carlos Pérez','carlos@universidad.edu.co',
   'scrypt:32768:8:1$T8dJYrdG2Jn4tRZx$31c0c6d5c77d7e1431787899b1f45a2e9deeb5979be25dd5714309ceb704ebfadc57b33c9b5cd192897f29a1fd65a34ed4f2773b3c597659ddbd99e6faa4e357',2);

INSERT INTO categorias (nombre) VALUES
  ('Balones'),('Uniformes'),('Calzado'),
  ('Protección'),('Equipamiento'),('Accesorios');

INSERT INTO equipos (nombre, descripcion, id_categoria, stock_total, stock_disponible, stock_minimo) VALUES
  ('Balón de fútbol N5',     'Balón oficial reglamentario',        1, 12, 12, 3),
  ('Balón de baloncesto',    'Balón cuero sintético talla 7',      1,  8,  8, 2),
  ('Balón de voleibol',      'Balón de competencia',               1,  6,  6, 2),
  ('Camiseta deportiva M',   'Poliéster transpirable talla M',     2, 20, 20, 5),
  ('Camiseta deportiva L',   'Poliéster transpirable talla L',     2, 15, 15, 5),
  ('Pantaloneta talla M',    'Pantaloneta deportiva unisex',       2, 18, 18, 5),
  ('Guayos fútbol talla 40', 'Guayos césped artificial',           3,  6,  6, 2),
  ('Tenis multideporte T42', 'Tenis para cancha múltiple',         3,  4,  4, 2),
  ('Rodilleras par',         'Protección espuma EVA',              4, 10, 10, 3),
  ('Canilleras fútbol',      'Par canilleras media caña',          4,  8,  8, 3),
  ('Red de voleibol',        'Red oficial medidas reglamentarias', 5,  3,  3, 1),
  ('Arco portátil fútbol',   'Arco plegable para entrenamiento',   5,  2,  2, 1),
  ('Silbato árbitro',        'Silbato metálico con cordón',        6, 15, 15, 4),
  ('Cono de entrenamiento',  'Cono plástico 30cm (unidad)',        6, 50, 50, 10),
  ('Cronómetro digital',     'Cronómetro deportivo waterproof',    6,  5,  5, 2);

-- Vistas
CREATE OR REPLACE VIEW vista_stock_bajo AS
  SELECT e.id, e.nombre, c.nombre AS categoria,
         e.stock_disponible, e.stock_minimo,
         (e.stock_minimo - e.stock_disponible) AS unidades_faltantes
  FROM equipos e JOIN categorias c ON e.id_categoria = c.id
  WHERE e.stock_disponible <= e.stock_minimo AND e.activo = 1;

CREATE OR REPLACE VIEW vista_prestamos_activos AS
  SELECT p.id, p.fecha_prestamo, p.cantidad, p.estado,
         e.nombre AS equipo, u.nombre AS usuario, u.email
  FROM prestamos p
  JOIN equipos  e ON p.id_equipo  = e.id
  JOIN usuarios u ON p.id_usuario = u.id
  WHERE p.estado = 'activo'
  ORDER BY p.fecha_prestamo DESC;

CREATE OR REPLACE VIEW vista_resumen_categorias AS
  SELECT c.nombre AS categoria,
         COUNT(e.id)              AS total_equipos,
         SUM(e.stock_disponible)  AS disponibles,
         SUM(e.stock_total - e.stock_disponible) AS prestados
  FROM categorias c
  LEFT JOIN equipos e ON e.id_categoria = c.id AND e.activo = 1
  GROUP BY c.id, c.nombre;

-- Verificación
SELECT 'roles' AS tabla, COUNT(*) AS registros FROM roles      UNION ALL
SELECT 'usuarios',        COUNT(*)              FROM usuarios   UNION ALL
SELECT 'categorias',      COUNT(*)              FROM categorias UNION ALL
SELECT 'equipos',         COUNT(*)              FROM equipos    UNION ALL
SELECT 'prestamos',       COUNT(*)              FROM prestamos  UNION ALL
SELECT 'reportes',        COUNT(*)              FROM reportes;