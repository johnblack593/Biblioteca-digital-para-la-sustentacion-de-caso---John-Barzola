import sqlite3
import os
from werkzeug.security import generate_password_hash

def init_db():
    # Obtener la ruta absoluta a la base de datos
    db_path = os.path.join(os.path.dirname(__file__), 'biblioteca.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tabla Generos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS generos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Tabla Autores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS autores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Tabla Libros (con FK a genero)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            genero_id INTEGER NOT NULL,
            anio INTEGER NOT NULL,
            edicion TEXT,
            resumen TEXT,
            portada_path TEXT,
            pdf_path TEXT,
            FOREIGN KEY (genero_id) REFERENCES generos (id)
        )
    ''')
    
    # Tabla Intermedia AutoresLibros
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS autores_libros (
            libro_id INTEGER NOT NULL,
            autor_id INTEGER NOT NULL,
            PRIMARY KEY (libro_id, autor_id),
            FOREIGN KEY (libro_id) REFERENCES books (id) ON DELETE CASCADE,
            FOREIGN KEY (autor_id) REFERENCES autores (id) ON DELETE CASCADE
        )
    ''')
    
    # Tabla Prestamos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prestamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            libro_id INTEGER NOT NULL,
            fecha_prestamo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_devolucion TIMESTAMP,
            estado TEXT DEFAULT 'Activo',
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (libro_id) REFERENCES books (id)
        )
    ''')

    # Tabla Reseñas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resenas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            libro_id INTEGER NOT NULL,
            calificacion INTEGER NOT NULL CHECK(calificacion BETWEEN 1 AND 5),
            comentario TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (libro_id) REFERENCES books (id)
        )
    ''')
    
    # Tabla Users (con rol y fecha de registro)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            nombres TEXT,
            apellidos TEXT,
            cedula TEXT,
            pregunta_seguridad TEXT,
            respuesta_seguridad TEXT,
            rol TEXT NOT NULL DEFAULT 'usuario',
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla Configuración Global del Sistema
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL,
            descripcion TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor, descripcion) VALUES ('limite_libros_prestamo', '3', 'Límite máximo de libros simultáneos por usuario')")
    cursor.execute("INSERT OR IGNORE INTO configuracion (clave, valor, descripcion) VALUES ('dias_plazo_devolucion', '14', 'Días calendario de plazo para devolución antes de mora')")

    # Migración de columnas por si la tabla ya existía sin ellas
    cursor.execute("PRAGMA table_info(users)")
    columnas_users = [col[1] for col in cursor.fetchall()]
    
    if 'rol' not in columnas_users:
        cursor.execute("ALTER TABLE users ADD COLUMN rol TEXT NOT NULL DEFAULT 'usuario'")
        print("Columna 'rol' agregada a la tabla users.")
        
    if 'fecha_registro' not in columnas_users:
        cursor.execute("ALTER TABLE users ADD COLUMN fecha_registro TIMESTAMP")
        cursor.execute("UPDATE users SET fecha_registro = CURRENT_TIMESTAMP WHERE fecha_registro IS NULL")
        print("Columna 'fecha_registro' agregada a la tabla users.")

    # Asegurar la existencia del Administrador por defecto
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_pass_hash = generate_password_hash('admin')
        cursor.execute(
            '''INSERT INTO users (username, password, email, nombres, apellidos, cedula, pregunta_seguridad, respuesta_seguridad, rol)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            ('admin', admin_pass_hash, 'admin@biblioteca.com', 'Administrador', 'del Sistema', '0000000001', '¿En qué ciudad naciste?', 'quito', 'admin')
        )
        print("Usuario 'admin' creado con éxito (contraseña: admin).")

    # Asegurar que el usuario 'user' tenga rol 'usuario'
    cursor.execute("SELECT id FROM users WHERE username = 'user'")
    user_row = cursor.fetchone()
    if user_row:
        cursor.execute("UPDATE users SET rol = 'usuario' WHERE username = 'user'")
        print("Usuario 'user' configurado con rol 'usuario'.")

    conn.commit()
    conn.close()
    print("Base de datos y roles inicializados correctamente.")

if __name__ == '__main__':
    init_db()
