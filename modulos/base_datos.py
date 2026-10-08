import sqlite3
from modulos.configuracion import DATABASE

def get_db_connection():
    """Establece y devuelve una conexión a la base de datos SQLite."""
    conn = sqlite3.connect(DATABASE)
    # Permite acceder a las columnas por nombre (ej. fila['titulo']) en vez de índice numérico
    conn.row_factory = sqlite3.Row 
    return conn

def init_configuracion_table():
    """Crea la tabla de configuración si no existe e inserta valores por defecto."""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS configuracion (
            clave TEXT PRIMARY KEY,
            valor TEXT NOT NULL,
            descripcion TEXT
        )
    ''')
    defaults = [
        ('limite_libros_prestamo', '3', 'Límite máximo de libros en préstamo activo por lector'),
        ('dias_plazo_devolucion', '14', 'Días de plazo para devolver un libro antes de entrar en mora')
    ]
    for clave, val, desc in defaults:
        conn.execute('INSERT OR IGNORE INTO configuracion (clave, valor, descripcion) VALUES (?, ?, ?)', (clave, val, desc))
    conn.commit()
    conn.close()

def get_config(clave, default=None):
    """Obtiene el valor de una clave de configuración."""
    try:
        conn = get_db_connection()
        row = conn.execute('SELECT valor FROM configuracion WHERE clave = ?', (clave,)).fetchone()
        conn.close()
        if row:
            return row['valor']
    except Exception:
        pass
    return default

def get_all_config():
    """Retorna un diccionario con todas las claves y valores de configuración."""
    init_configuracion_table()
    conn = get_db_connection()
    rows = conn.execute('SELECT clave, valor, descripcion FROM configuracion').fetchall()
    conn.close()
    return {r['clave']: r['valor'] for r in rows}

def set_config(clave, valor):
    """Inserta o actualiza un parámetro de configuración."""
    init_configuracion_table()
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO configuracion (clave, valor) VALUES (?, ?)
        ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
    ''', (clave, str(valor)))
    conn.commit()
    conn.close()
