import os
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory, make_response
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from modulos.base_datos import get_db_connection, get_config, set_config, get_all_config
from modulos.configuracion import UPLOAD_FOLDER, PORTADAS_FOLDER, ALLOWED_EXTENSIONS, ALLOWED_IMAGE_EXTENSIONS
from modulos.validadores import validar_cedula_ecuatoriana

web_bp = Blueprint('web', __name__)

@web_bp.before_request
def require_login():
    """Verifica que el usuario haya iniciado sesión antes de acceder a las rutas web."""
    if 'user_id' not in session:
        flash('Debes iniciar sesión para acceder a la biblioteca.', 'error')
        return redirect(url_for('auth.login'))

@web_bp.app_context_processor
def inject_user_context():
    """Inyecta variables de contexto de sesión y políticas configurables en todas las plantillas HTML."""
    rol = session.get('user_role', 'usuario')
    try:
        limite_libros = int(get_config('limite_libros_prestamo', '3'))
    except (ValueError, TypeError):
        limite_libros = 3
    try:
        dias_plazo = int(get_config('dias_plazo_devolucion', '14'))
    except (ValueError, TypeError):
        dias_plazo = 14
        
    return {
        'is_admin': (rol == 'admin'),
        'current_user_role': rol,
        'current_user_name': session.get('user_nombre', session.get('username', '')),
        'limite_libros_prestamo': limite_libros,
        'dias_plazo_devolucion': dias_plazo
    }

def admin_required(f):
    """Decorador para proteger rutas exclusivas del Administrador."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'admin':
            flash('Acceso restringido: Esta acción requiere permisos de Administrador.', 'error')
            return redirect(url_for('web.index'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    """Verifica si la extensión del archivo PDF es permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_image_file(filename):
    """Verifica si la extensión de la imagen de portada es permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def get_or_create_genero(conn, nombre_genero):
    """Obtiene el ID del género si existe, o lo crea de no existir."""
    genero = conn.execute('SELECT id FROM generos WHERE nombre = ?', (nombre_genero,)).fetchone()
    if genero:
        return genero['id']
    cursor = conn.execute('INSERT INTO generos (nombre) VALUES (?)', (nombre_genero,))
    return cursor.lastrowid

def get_or_create_autor(conn, nombre_autor):
    """Obtiene el ID del autor si existe, o lo crea de no existir."""
    autor = conn.execute('SELECT id FROM autores WHERE nombre = ?', (nombre_autor,)).fetchone()
    if autor:
        return autor['id']
    cursor = conn.execute('INSERT INTO autores (nombre) VALUES (?)', (nombre_autor,))
    return cursor.lastrowid

# =========================================================================
# RUTAS PÚBLICAS / COMUNES (Lector y Admin)
# =========================================================================

@web_bp.route('/')
def index():
    """Catálogo principal con secciones superiores (Top 5 más solicitados y Últimos 5 añadidos) y paginación de 10 libros."""
    query_text = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    if page < 1:
        page = 1
    per_page = 10
    user_id = session.get('user_id')
    
    conn = get_db_connection()
    
    # 1. Top 5 Libros Más Solicitados (según histórico de préstamos)
    top_solicitados_query = '''
        SELECT b.id, b.titulo, b.portada_path, b.anio, b.edicion,
               g.nombre AS genero, GROUP_CONCAT(DISTINCT a.nombre) AS autor,
               COUNT(p.id) AS total_prestamos,
               (SELECT COUNT(*) FROM prestamos p2 WHERE p2.libro_id = b.id AND p2.user_id = ? AND p2.estado = 'Activo') AS is_borrowed
        FROM books b
        LEFT JOIN generos g ON b.genero_id = g.id
        LEFT JOIN autores_libros al ON b.id = al.libro_id
        LEFT JOIN autores a ON al.autor_id = a.id
        LEFT JOIN prestamos p ON b.id = p.libro_id
        GROUP BY b.id
        ORDER BY total_prestamos DESC, b.id DESC
        LIMIT 5
    '''
    top_solicitados = conn.execute(top_solicitados_query, (user_id,)).fetchall()
    
    # 2. Últimos 5 Libros Añadidos al Catálogo (orden descendente por ID)
    ultimos_anadidos_query = '''
        SELECT b.id, b.titulo, b.portada_path, b.anio, b.edicion,
               g.nombre AS genero, GROUP_CONCAT(DISTINCT a.nombre) AS autor,
               (SELECT COUNT(*) FROM prestamos p2 WHERE p2.libro_id = b.id AND p2.user_id = ? AND p2.estado = 'Activo') AS is_borrowed
        FROM books b
        LEFT JOIN generos g ON b.genero_id = g.id
        LEFT JOIN autores_libros al ON b.id = al.libro_id
        LEFT JOIN autores a ON al.autor_id = a.id
        GROUP BY b.id
        ORDER BY b.id DESC
        LIMIT 5
    '''
    ultimos_anadidos = conn.execute(ultimos_anadidos_query, (user_id,)).fetchall()
    
    # 3. Cálculo de Paginación para la Lista Vertical (Máximo 10 libros por página)
    if query_text:
        count_query = '''
            SELECT COUNT(DISTINCT b.id)
            FROM books b
            LEFT JOIN generos g ON b.genero_id = g.id
            LEFT JOIN autores_libros al ON b.id = al.libro_id
            LEFT JOIN autores a ON al.autor_id = a.id
            WHERE b.titulo LIKE ? OR a.nombre LIKE ? OR g.nombre LIKE ?
        '''
        total_books = conn.execute(count_query, (f'%{query_text}%', f'%{query_text}%', f'%{query_text}%')).fetchone()[0]
    else:
        total_books = conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]
        
    total_pages = max(1, (total_books + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * per_page
    
    base_query = '''
        SELECT b.id, b.titulo, b.anio, b.edicion, b.resumen, b.portada_path, b.pdf_path, 
               g.nombre AS genero, GROUP_CONCAT(DISTINCT a.nombre) AS autor,
               (SELECT COUNT(*) FROM prestamos p WHERE p.libro_id = b.id AND p.user_id = ? AND p.estado = 'Activo') AS is_borrowed
        FROM books b
        LEFT JOIN generos g ON b.genero_id = g.id
        LEFT JOIN autores_libros al ON b.id = al.libro_id
        LEFT JOIN autores a ON al.autor_id = a.id
    '''
    
    if query_text:
        base_query += ' WHERE b.titulo LIKE ? OR a.nombre LIKE ? OR g.nombre LIKE ? GROUP BY b.id ORDER BY b.id ASC LIMIT ? OFFSET ?'
        books = conn.execute(base_query, (user_id, f'%{query_text}%', f'%{query_text}%', f'%{query_text}%', per_page, offset)).fetchall()
    else:
        base_query += ' GROUP BY b.id ORDER BY b.id ASC LIMIT ? OFFSET ?'
        books = conn.execute(base_query, (user_id, per_page, offset)).fetchall()
        
    conn.close()
    
    return render_template(
        'inicio.html',
        books=books,
        search_query=query_text,
        top_solicitados=top_solicitados,
        ultimos_anadidos=ultimos_anadidos,
        page=page,
        total_pages=total_pages,
        total_books=total_books,
        per_page=per_page
    )

@web_bp.route('/book/<int:id>')
def book_detail(id):
    """Vista detallada de un libro con opciones de lectura y sección de reseñas de la comunidad."""
    user_id = session.get('user_id')
    conn = get_db_connection()
    query = '''
        SELECT b.id, b.titulo, b.anio, b.edicion, b.resumen, b.portada_path, b.pdf_path, 
               g.nombre AS genero, GROUP_CONCAT(DISTINCT a.nombre) AS autor,
               (SELECT COUNT(*) FROM prestamos p WHERE p.libro_id = b.id AND p.user_id = ? AND p.estado = 'Activo') AS is_borrowed
        FROM books b
        LEFT JOIN generos g ON b.genero_id = g.id
        LEFT JOIN autores_libros al ON b.id = al.libro_id
        LEFT JOIN autores a ON al.autor_id = a.id
        WHERE b.id = ?
        GROUP BY b.id
    '''
    book = conn.execute(query, (user_id, id)).fetchone()
    
    if not book:
        conn.close()
        flash('El libro no existe en el catálogo.', 'error')
        return redirect(url_for('web.index'))
        
    # Obtener todas las reseñas comunitarias del libro
    resenas_query = '''
        SELECT r.id, r.calificacion, r.comentario, r.fecha,
               u.nombres, u.apellidos, u.username
        FROM resenas r
        JOIN users u ON r.user_id = u.id
        WHERE r.libro_id = ?
        ORDER BY r.fecha DESC
    '''
    resenas = conn.execute(resenas_query, (id,)).fetchall()
    conn.close()
    
    total_resenas = len(resenas)
    promedio_calificacion = round(sum(r['calificacion'] for r in resenas) / total_resenas, 1) if total_resenas > 0 else 0
    
    return render_template(
        'detalle_libro.html',
        book=book,
        resenas=resenas,
        total_resenas=total_resenas,
        promedio_calificacion=promedio_calificacion
    )

@web_bp.route('/prestar/<int:id>', methods=['POST'])
def prestar_libro(id):
    """Permite al usuario solicitar en préstamo un libro."""
    user_id = session.get('user_id')
    conn = get_db_connection()
    
    # Verificar si el usuario ya tiene este libro en préstamo activo
    prestamo = conn.execute(
        'SELECT * FROM prestamos WHERE user_id = ? AND libro_id = ? AND estado = "Activo"',
        (user_id, id)
    ).fetchone()
    
    if prestamo:
        flash('Ya tienes este libro actualmente en préstamo.', 'error')
    else:
        # Control dinámico de límite de libros prestados simultáneos según configuración administrativa
        try:
            max_prestamos = int(get_config('limite_libros_prestamo', '3'))
        except (ValueError, TypeError):
            max_prestamos = 3

        activos_count = conn.execute(
            'SELECT COUNT(*) FROM prestamos WHERE user_id = ? AND estado = "Activo"',
            (user_id,)
        ).fetchone()[0]
        
        if activos_count >= max_prestamos:
            flash(f'Límite de préstamos alcanzado: Tu cuenta tiene {activos_count} libros en préstamo activo (límite configurado por administración: {max_prestamos}). Por favor devuelve alguno antes de solicitar un nuevo título.', 'error')
        else:
            conn.execute('INSERT INTO prestamos (user_id, libro_id) VALUES (?, ?)', (user_id, id))
            conn.commit()
            flash('¡Libro prestado con éxito! Ya puedes comenzar tu lectura integrada.', 'success')
        
    conn.close()
    destino = request.referrer or url_for('web.index')
    return redirect(destino)

@web_bp.route('/devolver/<int:id>', methods=['POST'])
def devolver_libro(id):
    """Permite al lector registrar la devolución de un libro que tiene en préstamo con opción a dejar una reseña."""
    user_id = session.get('user_id')
    conn = get_db_connection()
    
    # 1. Marcar préstamo como Devuelto
    conn.execute(
        'UPDATE prestamos SET estado = "Devuelto", fecha_devolucion = CURRENT_TIMESTAMP WHERE user_id = ? AND libro_id = ? AND estado = "Activo"',
        (user_id, id)
    )
    
    # 2. Guardar reseña opcional (si se proporcionó calificación 1 a 5)
    calificacion_raw = request.form.get('calificacion')
    comentario = request.form.get('comentario', '').strip()
    
    if calificacion_raw:
        try:
            calificacion = int(calificacion_raw)
            if 1 <= calificacion <= 5:
                conn.execute(
                    'INSERT INTO resenas (user_id, libro_id, calificacion, comentario) VALUES (?, ?, ?, ?)',
                    (user_id, id, calificacion, comentario)
                )
                flash('¡Libro devuelto con éxito y muchas gracias por compartir tu reseña!', 'success')
            else:
                flash('¡Libro devuelto a la biblioteca con éxito!', 'success')
        except ValueError:
            flash('¡Libro devuelto a la biblioteca con éxito!', 'success')
    else:
        flash('¡Libro devuelto a la biblioteca con éxito!', 'success')
        
    conn.commit()
    conn.close()
    
    destino = request.referrer or url_for('web.mi_estanteria')
    return redirect(destino)

# =========================================================================
# LECTOR DE PDF INTEGRADO (Visualización interna sin descarga)
# =========================================================================

@web_bp.route('/pdf/<path:filename>')
def servir_pdf(filename):
    """Sirve el archivo PDF con cabeceras de visualización inline protegida."""
    response = make_response(send_from_directory(UPLOAD_FOLDER, filename))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response

@web_bp.route('/leer/<int:id>')
def visor_lectura(id):
    """Pantalla con lector de PDF integrado en la aplicación."""
    user_id = session.get('user_id')
    is_admin = session.get('user_role') == 'admin'
    
    conn = get_db_connection()
    query = '''
        SELECT b.id, b.titulo, b.anio, b.edicion, b.resumen, b.portada_path, b.pdf_path, 
               g.nombre AS genero, GROUP_CONCAT(a.nombre, ', ') AS autor,
               (SELECT COUNT(*) FROM prestamos p WHERE p.libro_id = b.id AND p.user_id = ? AND p.estado = 'Activo') AS is_borrowed
        FROM books b
        LEFT JOIN generos g ON b.genero_id = g.id
        LEFT JOIN autores_libros al ON b.id = al.libro_id
        LEFT JOIN autores a ON al.autor_id = a.id
        WHERE b.id = ?
        GROUP BY b.id
    '''
    book = conn.execute(query, (user_id, id)).fetchone()
    conn.close()
    
    if not book:
        flash('El libro solicitado no existe.', 'error')
        return redirect(url_for('web.index'))
        
    if not book['pdf_path']:
        flash('Este libro no cuenta con copia digital en PDF para lectura en línea.', 'error')
        return redirect(url_for('web.book_detail', id=id))
        
    # Verificar que el usuario tenga el préstamo activo antes de leer
    if book['is_borrowed'] == 0:
        flash('Debes solicitar este libro en préstamo antes de poder abrirlo en el lector integrado.', 'error')
        return redirect(url_for('web.book_detail', id=id))
        
    return render_template('visor_pdf.html', book=book)

# =========================================================================
# RUTAS DE ADMINISTRACIÓN (Exclusivas para rol 'admin')
# =========================================================================

@web_bp.route('/admin')
@admin_required
def admin_dashboard():
    """Panel de control del Administrador con métricas, gestión de libros, préstamos y usuarios."""
    conn = get_db_connection()
    
    # 1. Métricas globales del sistema
    total_libros = conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    total_prestamos_activos = conn.execute("SELECT COUNT(*) FROM prestamos WHERE estado = 'Activo'").fetchone()[0]
    total_prestamos_historico = conn.execute('SELECT COUNT(*) FROM prestamos').fetchone()[0]
    total_usuarios = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_admins = conn.execute("SELECT COUNT(*) FROM users WHERE rol = 'admin'").fetchone()[0]
    total_lectores = total_usuarios - total_admins
    
    # 2. Catálogo completo de libros con métrica de préstamos
    books_query = '''
        SELECT b.id, b.titulo, b.anio, b.edicion, b.resumen, b.portada_path, b.pdf_path, 
               g.nombre AS genero, GROUP_CONCAT(a.nombre, ', ') AS autor,
               (SELECT COUNT(*) FROM prestamos p WHERE p.libro_id = b.id AND p.estado = 'Activo') AS prestamos_activos,
               (SELECT COUNT(*) FROM prestamos p WHERE p.libro_id = b.id) AS prestamos_totales
        FROM books b
        LEFT JOIN generos g ON b.genero_id = g.id
        LEFT JOIN autores_libros al ON b.id = al.libro_id
        LEFT JOIN autores a ON al.autor_id = a.id
        GROUP BY b.id
        ORDER BY b.id DESC
    '''
    books = conn.execute(books_query).fetchall()
    
    # 3. Todos los préstamos del sistema
    prestamos_query = '''
        SELECT p.id, p.fecha_prestamo, p.fecha_devolucion, p.estado,
               b.id AS libro_id, b.titulo AS libro_titulo, b.portada_path,
               u.id AS usuario_id, u.username, u.nombres, u.apellidos, u.cedula, u.email
        FROM prestamos p
        JOIN books b ON p.libro_id = b.id
        JOIN users u ON p.user_id = u.id
        ORDER BY p.fecha_prestamo DESC
    '''
    prestamos = conn.execute(prestamos_query).fetchall()
    
    # 4. Todos los usuarios registrados
    users_query = '''
        SELECT u.id, u.username, u.email, u.nombres, u.apellidos, u.cedula, u.rol, u.fecha_registro,
               (SELECT COUNT(*) FROM prestamos p WHERE p.user_id = u.id AND p.estado = 'Activo') AS prestamos_activos,
               (SELECT COUNT(*) FROM prestamos p WHERE p.user_id = u.id) AS prestamos_totales
        FROM users u
        ORDER BY u.id ASC
    '''
    users = conn.execute(users_query).fetchall()

    # 5. Opciones para autocompletado inteligente con datalists (Géneros, Autores, Ediciones)
    generos_disponibles = [row['nombre'] for row in conn.execute('SELECT DISTINCT nombre FROM generos ORDER BY nombre ASC').fetchall()]
    autores_disponibles = [row['nombre'] for row in conn.execute('SELECT DISTINCT nombre FROM autores ORDER BY nombre ASC').fetchall()]
    ediciones_disponibles = [row['edicion'] for row in conn.execute('SELECT DISTINCT edicion FROM books WHERE edicion IS NOT NULL AND TRIM(edicion) != "" ORDER BY edicion ASC').fetchall()]

    # 6. Monitoreo: Usuarios con mayor cantidad de libros en préstamo activo actualmente
    usuarios_top_prestamos_query = '''
        SELECT u.id, u.username, u.nombres, u.apellidos, u.email, u.cedula,
               COUNT(p.id) AS libros_prestados
        FROM users u
        JOIN prestamos p ON u.id = p.user_id
        WHERE p.estado = 'Activo'
        GROUP BY u.id
        ORDER BY libros_prestados DESC, u.id ASC
        LIMIT 6
    '''
    usuarios_top_prestamos = conn.execute(usuarios_top_prestamos_query).fetchall()

    # Parámetros operativos configurables
    try:
        dias_plazo = int(get_config('dias_plazo_devolucion', '14'))
    except (ValueError, TypeError):
        dias_plazo = 14
    try:
        limite_libros = int(get_config('limite_libros_prestamo', '3'))
    except (ValueError, TypeError):
        limite_libros = 3

    # 7. Monitoreo: Préstamos con mayor tiempo transcurrido sin devolver (Alerta de Mora)
    prestamos_mora_query = f'''
        SELECT p.id, p.fecha_prestamo,
               CAST(MAX(0, ROUND(JULIANDAY('now', 'localtime') - JULIANDAY(p.fecha_prestamo))) AS INTEGER) AS dias_transcurridos,
               b.id AS libro_id, b.titulo AS libro_titulo, b.portada_path,
               u.id AS usuario_id, u.username, u.nombres, u.apellidos, u.email, u.cedula,
               {dias_plazo} AS dias_limite,
               CASE WHEN (JULIANDAY('now', 'localtime') - JULIANDAY(p.fecha_prestamo)) > {dias_plazo} THEN 1 ELSE 0 END AS es_mora
        FROM prestamos p
        JOIN books b ON p.libro_id = b.id
        JOIN users u ON p.user_id = u.id
        WHERE p.estado = 'Activo'
        ORDER BY p.fecha_prestamo ASC
        LIMIT 8
    '''
    prestamos_mora = conn.execute(prestamos_mora_query).fetchall()
    
    total_prestamos_mora = conn.execute(
        f"SELECT COUNT(*) FROM prestamos WHERE estado = 'Activo' AND (JULIANDAY('now', 'localtime') - JULIANDAY(fecha_prestamo)) > {dias_plazo}"
    ).fetchone()[0]
    
    conn.close()
    
    metricas = {
        'total_libros': total_libros,
        'total_prestamos_activos': total_prestamos_activos,
        'total_prestamos_historico': total_prestamos_historico,
        'total_usuarios': total_usuarios,
        'total_admins': total_admins,
        'total_lectores': total_lectores,
        'total_prestamos_mora': total_prestamos_mora
    }
    
    return render_template(
        'admin_panel.html',
        metricas=metricas,
        books=books,
        prestamos=prestamos,
        users=users,
        generos_disponibles=generos_disponibles,
        autores_disponibles=autores_disponibles,
        ediciones_disponibles=ediciones_disponibles,
        usuarios_top_prestamos=usuarios_top_prestamos,
        prestamos_mora=prestamos_mora,
        dias_plazo=dias_plazo,
        limite_libros=limite_libros
    )

@web_bp.route('/admin/configuracion', methods=['POST'])
@admin_required
def actualizar_configuracion():
    """Actualiza los parámetros operativos globales: límite de libros simultáneos y plazo de devolución."""
    nuevo_limite = request.form.get('limite_libros_prestamo', '').strip()
    nuevos_dias = request.form.get('dias_plazo_devolucion', '').strip()
    
    try:
        limite_val = int(nuevo_limite)
        if limite_val < 1 or limite_val > 50:
            raise ValueError("Límite fuera de rango.")
    except (ValueError, TypeError):
        flash('El límite de libros simultáneos debe ser un número entero entre 1 y 50.', 'error')
        return redirect(url_for('web.admin_dashboard') + '#tab-configuracion')
        
    try:
        dias_val = int(nuevos_dias)
        if dias_val < 1 or dias_val > 365:
            raise ValueError("Días fuera de rango.")
    except (ValueError, TypeError):
        flash('El plazo de devolución debe ser un número entero entre 1 y 365 días.', 'error')
        return redirect(url_for('web.admin_dashboard') + '#tab-configuracion')
        
    set_config('limite_libros_prestamo', limite_val)
    set_config('dias_plazo_devolucion', dias_val)
    
    flash(f'¡Parámetros actualizados con éxito! Límite de libros por usuario: {limite_val} | Plazo de devolución: {dias_val} días.', 'success')
    return redirect(url_for('web.admin_dashboard') + '#tab-configuracion')

@web_bp.route('/add', methods=['POST'])
@admin_required
def add_book():
    """Crea un nuevo libro en la base de datos (Exclusivo Administrador)."""
    titulo = request.form['titulo'].strip()
    autor_str = request.form['autor'].strip()
    genero_str = request.form['genero'].strip()
    anio = request.form['anio'].strip()
    edicion = request.form.get('edicion', '').strip()
    resumen = request.form.get('resumen', '').strip()
    
    pdf_path = None
    if 'pdf_file' in request.files:
        file = request.files['pdf_file']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            pdf_path = filename

    portada_path = None
    if 'portada_file' in request.files:
        file = request.files['portada_file']
        if file and file.filename != '' and allowed_image_file(file.filename):
            filename = secure_filename(file.filename)
            os.makedirs(PORTADAS_FOLDER, exist_ok=True)
            file.save(os.path.join(PORTADAS_FOLDER, filename))
            portada_path = filename

    if titulo and autor_str and genero_str and anio:
        conn = get_db_connection()
        genero_id = get_or_create_genero(conn, genero_str)
        
        cursor = conn.execute(
            'INSERT INTO books (titulo, genero_id, anio, edicion, resumen, portada_path, pdf_path) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (titulo, genero_id, anio, edicion, resumen, portada_path, pdf_path)
        )
        libro_id = cursor.lastrowid
        
        autores = [a.strip() for a in autor_str.split(',')]
        for a_nombre in autores:
            if a_nombre:
                autor_id = get_or_create_autor(conn, a_nombre)
                conn.execute('INSERT INTO autores_libros (libro_id, autor_id) VALUES (?, ?)', (libro_id, autor_id))
                
        conn.commit()
        conn.close()
        flash('¡Libro registrado exitosamente en el catálogo!', 'success')
    else:
        flash('Faltan campos obligatorios para registrar el libro.', 'error')
        
    destino = request.referrer or url_for('web.admin_dashboard')
    return redirect(destino)

@web_bp.route('/update/<int:id>', methods=['POST'])
@admin_required
def update_book(id):
    """Modifica la información de un libro existente (Exclusivo Administrador)."""
    titulo = request.form['titulo'].strip()
    autor_str = request.form['autor'].strip()
    genero_str = request.form['genero'].strip()
    anio = request.form['anio'].strip()
    edicion = request.form.get('edicion', '').strip()
    resumen = request.form.get('resumen', '').strip()
    
    if titulo and autor_str and genero_str and anio:
        conn = get_db_connection()
        
        pdf_path = request.form.get('current_pdf')
        if 'pdf_file' in request.files:
            file = request.files['pdf_file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                pdf_path = filename
                
        portada_path = request.form.get('current_portada')
        if 'portada_file' in request.files:
            file = request.files['portada_file']
            if file and file.filename != '' and allowed_image_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(PORTADAS_FOLDER, exist_ok=True)
                file.save(os.path.join(PORTADAS_FOLDER, filename))
                portada_path = filename
                
        genero_id = get_or_create_genero(conn, genero_str)
        
        conn.execute(
            'UPDATE books SET titulo = ?, genero_id = ?, anio = ?, edicion = ?, resumen = ?, portada_path = ?, pdf_path = ? WHERE id = ?',
            (titulo, genero_id, anio, edicion, resumen, portada_path, pdf_path, id)
        )
        
        conn.execute('DELETE FROM autores_libros WHERE libro_id = ?', (id,))
        autores = [a.strip() for a in autor_str.split(',')]
        for a_nombre in autores:
            if a_nombre:
                autor_id = get_or_create_autor(conn, a_nombre)
                conn.execute('INSERT INTO autores_libros (libro_id, autor_id) VALUES (?, ?)', (id, autor_id))
                
        conn.commit()
        conn.close()
        flash('¡Libro modificado exitosamente!', 'success')
    else:
        flash('Faltan datos obligatorios para actualizar.', 'error')
        
    destino = request.referrer or url_for('web.admin_dashboard')
    return redirect(destino)

@web_bp.route('/delete/<int:id>', methods=['POST'])
@admin_required
def delete_book(id):
    """Elimina un libro y sus registros asociados (Exclusivo Administrador)."""
    conn = get_db_connection()
    conn.execute('DELETE FROM prestamos WHERE libro_id = ?', (id,))
    conn.execute('DELETE FROM autores_libros WHERE libro_id = ?', (id,))
    conn.execute('DELETE FROM books WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    
    flash('¡Libro eliminado del sistema!', 'success')
    destino = request.referrer or url_for('web.admin_dashboard')
    return redirect(destino)

@web_bp.route('/admin/prestamo/<int:id>/devolver', methods=['POST'])
@admin_required
def admin_devolver_prestamo(id):
    """Permite al Administrador registrar la entrega/devolución física de un libro."""
    conn = get_db_connection()
    conn.execute(
        'UPDATE prestamos SET estado = "Devuelto", fecha_devolucion = CURRENT_TIMESTAMP WHERE id = ?',
        (id,)
    )
    conn.commit()
    conn.close()
    flash('Préstamo marcado como Devuelto con éxito.', 'success')
    return redirect(url_for('web.admin_dashboard'))

# =========================================================================
# GESTIÓN AVANZADA DE USUARIOS / PERFILES (Exclusivo Administrador)
# =========================================================================

@web_bp.route('/admin/usuario/crear', methods=['POST'])
@admin_required
def admin_crear_usuario():
    """Permite al Administrador crear perfiles de usuario directamente."""
    username = request.form['username'].strip()
    password = request.form['password'].strip()
    nombres = request.form.get('nombres', '').strip()
    apellidos = request.form.get('apellidos', '').strip()
    cedula = ''.join(c for c in request.form.get('cedula', '') if c.isdigit())
    email = request.form.get('email', '').strip()
    rol = request.form.get('rol', 'usuario').strip()
    pregunta = request.form.get('pregunta_seguridad', '¿En qué ciudad naciste?')
    respuesta = request.form.get('respuesta_seguridad', 'quito').lower().strip()
    
    if not username or not password:
        flash('El nombre de usuario y la contraseña son obligatorios.', 'error')
        return redirect(url_for('web.admin_dashboard'))
        
    if cedula and not validar_cedula_ecuatoriana(cedula):
        flash('La cédula ingresada no es válida según el algoritmo de dígito verificador ecuatoriano.', 'error')
        return redirect(url_for('web.admin_dashboard'))
        
    conn = get_db_connection()
    existe = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
    if existe:
        conn.close()
        flash(f'El nombre de usuario @{username} ya existe en el sistema.', 'error')
        return redirect(url_for('web.admin_dashboard'))
        
    hashed = generate_password_hash(password)
    conn.execute('''
        INSERT INTO users (username, password, email, nombres, apellidos, cedula, pregunta_seguridad, respuesta_seguridad, rol)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (username, hashed, email, nombres, apellidos, cedula, pregunta, respuesta, rol))
    conn.commit()
    conn.close()
    
    flash(f'¡Perfil de usuario @{username} creado exitosamente con rol {rol.upper()}!', 'success')
    return redirect(url_for('web.admin_dashboard'))

@web_bp.route('/admin/usuario/<int:id>/editar', methods=['POST'])
@admin_required
def admin_editar_usuario(id):
    """Permite al Administrador modificar los datos de perfil de cualquier usuario."""
    nombres = request.form.get('nombres', '').strip()
    apellidos = request.form.get('apellidos', '').strip()
    cedula = ''.join(c for c in request.form.get('cedula', '') if c.isdigit())
    email = request.form.get('email', '').strip()
    nuevo_rol = request.form.get('rol', 'usuario').strip()
    
    if cedula and not validar_cedula_ecuatoriana(cedula):
        flash('La cédula ingresada no es válida según el algoritmo de dígito verificador ecuatoriano.', 'error')
        return redirect(url_for('web.admin_dashboard'))
        
    # Prevenir que el admin en sesión se auto-degrade a lector
    if id == session.get('user_id') and nuevo_rol != 'admin':
        flash('Por seguridad no puedes retirar tus propios permisos de administrador.', 'error')
        return redirect(url_for('web.admin_dashboard'))
        
    conn = get_db_connection()
    conn.execute('''
        UPDATE users SET nombres = ?, apellidos = ?, cedula = ?, email = ?, rol = ?
        WHERE id = ?
    ''', (nombres, apellidos, cedula, email, nuevo_rol, id))
    conn.commit()
    conn.close()
    
    flash('Información del perfil actualizada exitosamente.', 'success')
    return redirect(url_for('web.admin_dashboard'))

@web_bp.route('/admin/usuario/<int:id>/reset-password', methods=['POST'])
@admin_required
def admin_reset_password(id):
    """Soluciona problemas de acceso asignando una nueva contraseña a un usuario."""
    nueva_clave = request.form.get('nueva_password', '').strip()
    if not nueva_clave:
        flash('Debes especificar la nueva contraseña para el usuario.', 'error')
        return redirect(url_for('web.admin_dashboard'))
        
    conn = get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE id = ?', (id,)).fetchone()
    if not user:
        conn.close()
        flash('El usuario indicado no existe.', 'error')
        return redirect(url_for('web.admin_dashboard'))
        
    hashed = generate_password_hash(nueva_clave)
    conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, id))
    conn.commit()
    conn.close()
    
    flash(f'¡Acceso solucionado! La contraseña para @{user["username"]} fue restablecida con éxito.', 'success')
    return redirect(url_for('web.admin_dashboard'))

@web_bp.route('/admin/usuario/<int:id>/eliminar', methods=['POST'])
@admin_required
def admin_eliminar_usuario(id):
    """Elimina permanentemente una cuenta de usuario y sus préstamos."""
    if id == session.get('user_id'):
        flash('Por seguridad no puedes eliminar tu propia cuenta en sesión.', 'error')
        return redirect(url_for('web.admin_dashboard'))
        
    conn = get_db_connection()
    user = conn.execute('SELECT username FROM users WHERE id = ?', (id,)).fetchone()
    if user:
        username = user['username']
        conn.execute('DELETE FROM prestamos WHERE user_id = ?', (id,))
        conn.execute('DELETE FROM users WHERE id = ?', (id,))
        conn.commit()
        flash(f'El perfil del usuario @{username} fue eliminado permanentemente.', 'success')
    else:
        flash('El usuario no existe.', 'error')
        
    conn.close()
    return redirect(url_for('web.admin_dashboard'))

@web_bp.route('/admin/usuario/<int:id>/cambiar-rol', methods=['POST'])
@web_bp.route('/admin/usuario/<int:id>/toggle-rol', methods=['POST'])
@admin_required
def admin_toggle_rol(id):
    """Permite al Administrador cambiar o seleccionar el rol de un usuario ('admin' o 'usuario')."""
    if id == session.get('user_id'):
        flash('Por seguridad no puedes modificar tu propio rol de administrador.', 'error')
        return redirect(url_for('web.admin_dashboard'))
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (id,)).fetchone()
    
    if not user:
        flash('El usuario no existe.', 'error')
    else:
        rol_solicitado = request.form.get('rol', '').strip()
        if rol_solicitado in ['admin', 'usuario']:
            nuevo_rol = rol_solicitado
        else:
            nuevo_rol = 'admin' if user['rol'] == 'usuario' else 'usuario'
            
        conn.execute('UPDATE users SET rol = ? WHERE id = ?', (nuevo_rol, id))
        conn.commit()
        nombre_rol = 'ADMINISTRADOR' if nuevo_rol == 'admin' else 'LECTOR'
        flash(f'Rol del usuario @{user["username"]} actualizado exitosamente a: {nombre_rol}.', 'success')
        
    conn.close()
    return redirect(url_for('web.admin_dashboard'))

# =========================================================================
# RUTAS DE "MI ESTANTERÍA" (Libros en préstamo activo e historial de lecturas)
# =========================================================================

@web_bp.route('/estanteria')
def mi_estanteria():
    """Pantalla 'Mi Estantería': agrupa exclusivamente 'Mis Libros en préstamo' y 'Historial de lecturas'."""
    user_id = session.get('user_id')
    conn = get_db_connection()
    
    # 1. Libros que el usuario tiene prestados actualmente (Activos)
    prestamos_activos_query = '''
        SELECT p.id AS prestamo_id, p.fecha_prestamo, p.estado,
               b.id AS libro_id, b.titulo, b.portada_path, b.pdf_path, b.edicion, b.anio,
               g.nombre AS genero, GROUP_CONCAT(DISTINCT a.nombre) AS autor
        FROM prestamos p
        JOIN books b ON p.libro_id = b.id
        LEFT JOIN generos g ON b.genero_id = g.id
        LEFT JOIN autores_libros al ON b.id = al.libro_id
        LEFT JOIN autores a ON al.autor_id = a.id
        WHERE p.user_id = ? AND p.estado = 'Activo'
        GROUP BY p.id
        ORDER BY p.fecha_prestamo DESC
    '''
    prestamos_activos = conn.execute(prestamos_activos_query, (user_id,)).fetchall()
    
    # 2. Historial completo de préstamos del usuario con reseñas dejadas
    prestamos_historial_query = '''
        SELECT p.id AS prestamo_id, p.fecha_prestamo, p.fecha_devolucion, p.estado,
               b.id AS libro_id, b.titulo, b.portada_path,
               g.nombre AS genero,
               r.calificacion, r.comentario AS resena_comentario
        FROM prestamos p
        JOIN books b ON p.libro_id = b.id
        LEFT JOIN generos g ON b.genero_id = g.id
        LEFT JOIN resenas r ON r.user_id = p.user_id AND r.libro_id = p.libro_id
        WHERE p.user_id = ?
        GROUP BY p.id
        ORDER BY p.fecha_prestamo DESC
    '''
    prestamos_historial = conn.execute(prestamos_historial_query, (user_id,)).fetchall()
    
    # Estadísticas para el encabezado de la estantería
    stats = {
        'activos': len(prestamos_activos),
        'devueltos': sum(1 for p in prestamos_historial if p['estado'] == 'Devuelto'),
        'total': len(prestamos_historial)
    }
    
    conn.close()
    
    return render_template(
        'mi_estanteria.html',
        prestamos_activos=prestamos_activos,
        prestamos_historial=prestamos_historial,
        stats=stats
    )

# =========================================================================
# RUTAS DE PERFIL DE USUARIO (Datos personales, cuenta y seguridad)
# =========================================================================

@web_bp.route('/profile')
def profile():
    """Pantalla de perfil de usuario enfocada en sus datos personales, información de cuenta y seguridad."""
    user_id = session.get('user_id')
    conn = get_db_connection()
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    # Estadísticas resumidas del lector con enlace directo a Mi Estantería
    total_activos = conn.execute("SELECT COUNT(*) FROM prestamos WHERE user_id = ? AND estado = 'Activo'", (user_id,)).fetchone()[0]
    total_devueltos = conn.execute("SELECT COUNT(*) FROM prestamos WHERE user_id = ? AND estado = 'Devuelto'", (user_id,)).fetchone()[0]
    total_solicitudes = conn.execute("SELECT COUNT(*) FROM prestamos WHERE user_id = ?", (user_id,)).fetchone()[0]
    total_resenas = conn.execute("SELECT COUNT(*) FROM resenas WHERE user_id = ?", (user_id,)).fetchone()[0]
    
    conn.close()
    
    stats = {
        'activos': total_activos,
        'devueltos': total_devueltos,
        'total': total_solicitudes,
        'resenas': total_resenas
    }
    
    return render_template(
        'perfil.html',
        user=user,
        stats=stats
    )

@web_bp.route('/profile/update', methods=['POST'])
def profile_update():
    """Actualiza los datos personales del usuario logueado con validación de cédula ecuatoriana."""
    user_id = session.get('user_id')
    nombres = request.form.get('nombres', '').strip()
    apellidos = request.form.get('apellidos', '').strip()
    email = request.form.get('email', '').strip().lower()
    cedula = ''.join(c for c in request.form.get('cedula', '') if c.isdigit())
    
    if cedula and not validar_cedula_ecuatoriana(cedula):
        flash('La cédula ingresada no es válida según el algoritmo de dígito verificador ecuatoriano.', 'error')
        return redirect(url_for('web.profile'))
        
    conn = get_db_connection()
    # Verificar si el correo ya está registrado en otra cuenta
    if email:
        email_ocupado = conn.execute('SELECT id FROM users WHERE LOWER(email) = ? AND id != ?', (email, user_id)).fetchone()
        if email_ocupado:
            conn.close()
            flash('El correo electrónico ingresado ya pertenece a otro usuario.', 'error')
            return redirect(url_for('web.profile'))
            
    conn.execute(
        'UPDATE users SET nombres = ?, apellidos = ?, email = ?, cedula = ? WHERE id = ?',
        (nombres, apellidos, email, cedula, user_id)
    )
    conn.commit()
    conn.close()
    
    nombre_display = f"{nombres} {apellidos}".strip()
    if nombre_display:
        session['user_nombre'] = nombre_display
        
    flash('¡Tus datos personales fueron actualizados correctamente!', 'success')
    return redirect(url_for('web.profile'))

@web_bp.route('/profile/change-password', methods=['POST'])
def profile_change_password():
    """Permite al usuario cambiar su contraseña actual desde su perfil."""
    user_id = session.get('user_id')
    clave_actual = request.form.get('clave_actual', '')
    nueva_clave = request.form.get('nueva_clave', '')
    confirmar_clave = request.form.get('confirmar_clave', '')
    
    if not nueva_clave or nueva_clave != confirmar_clave:
        flash('Las nuevas contraseñas no coinciden o están vacías.', 'error')
        return redirect(url_for('web.profile'))
        
    conn = get_db_connection()
    user = conn.execute('SELECT password FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if not user or not check_password_hash(user['password'], clave_actual):
        conn.close()
        flash('La contraseña actual es incorrecta.', 'error')
        return redirect(url_for('web.profile'))
        
    nueva_hash = generate_password_hash(nueva_clave)
    conn.execute('UPDATE users SET password = ? WHERE id = ?', (nueva_hash, user_id))
    conn.commit()
    conn.close()
    
    flash('¡Tu contraseña ha sido cambiada exitosamente!', 'success')
    return redirect(url_for('web.profile'))
