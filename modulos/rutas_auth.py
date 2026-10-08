from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from modulos.base_datos import get_db_connection
from modulos.validadores import validar_cedula_ecuatoriana

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form['username'].strip().lower()
        password = request.form['password']
        
        conn = get_db_connection()
        # Permite iniciar sesión indistintamente con correo electrónico o nombre de usuario
        user = conn.execute(
            'SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?',
            (identifier, identifier)
        ).fetchone()
        conn.close()
        
        # Verificamos si el usuario existe y si la contraseña coincide con el hash
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_role'] = user['rol'] if 'rol' in user.keys() else 'usuario'
            nombre_display = f"{user['nombres'] or ''} {user['apellidos'] or ''}".strip()
            session['user_nombre'] = nombre_display if nombre_display else user['username']
            
            if session['user_role'] == 'admin':
                flash(f'¡Bienvenido al Panel de Administración, {user["username"]}!', 'success')
                return redirect(url_for('web.admin_dashboard'))
            else:
                flash('¡Inicio de sesión exitoso! Bienvenido a la biblioteca.', 'success')
                return redirect(url_for('web.index'))
        else:
            flash('Usuario/correo o contraseña incorrectos', 'error')
            
    return render_template('acceso.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Ruta para registrar un nuevo usuario con correo como usuario, validación de cédula y doble contraseña."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        nombres = request.form.get('nombres', '').strip()
        apellidos = request.form.get('apellidos', '').strip()
        cedula = ''.join(c for c in request.form.get('cedula', '') if c.isdigit())
        pregunta_seguridad = request.form.get('pregunta_seguridad', '')
        respuesta_seguridad = request.form.get('respuesta_seguridad', '').lower().strip()
        
        # 1. Validación de correo obligatorio y con formato básico
        if not email or '@' not in email:
            flash('Por favor ingresa un correo electrónico válido.', 'error')
            return render_template('registro.html')

        # 2. Validación de doble contraseña (confirmación)
        if not password or not confirm_password:
            flash('Debes ingresar y confirmar tu contraseña.', 'error')
            return render_template('registro.html')
            
        if password != confirm_password:
            flash('Las contraseñas ingresadas no coinciden. Por favor verifícalas.', 'error')
            return render_template('registro.html')

        # 3. Validación de cédula ecuatoriana con algoritmo oficial del dígito verificador
        if not validar_cedula_ecuatoriana(cedula):
            flash('La cédula ingresada no es válida según el algoritmo de dígito verificador ecuatoriano.', 'error')
            return render_template('registro.html')

        conn = get_db_connection()
        # 4. El correo actúa como usuario y se verifica que no esté duplicado en la base de datos
        user_existente = conn.execute(
            'SELECT id FROM users WHERE LOWER(email) = ? OR LOWER(username) = ?',
            (email, email)
        ).fetchone()
        
        if user_existente:
            conn.close()
            flash('El correo electrónico ya se encuentra registrado. Utiliza otro o inicia sesión.', 'error')
            return render_template('registro.html')
            
        hashed_password = generate_password_hash(password)
        # Se guarda el email tanto en username como en email para compatibilidad total
        conn.execute(
            'INSERT INTO users (username, password, email, nombres, apellidos, cedula, pregunta_seguridad, respuesta_seguridad, rol) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (email, hashed_password, email, nombres, apellidos, cedula, pregunta_seguridad, respuesta_seguridad, 'usuario')
        )
        conn.commit()
        conn.close()
        flash('¡Registro exitoso! Ya puedes iniciar sesión con tu correo electrónico.', 'success')
        return redirect(url_for('auth.login'))
            
    return render_template('registro.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    """Paso 1: Identificación con correo o usuario y cédula."""
    if request.method == 'POST':
        identifier = request.form['username'].strip().lower()
        cedula = ''.join(c for c in request.form['cedula'] if c.isdigit())
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE (LOWER(username) = ? OR LOWER(email) = ?) AND cedula = ?',
            (identifier, identifier, cedula)
        ).fetchone()
        conn.close()
        
        if user:
            session['recovery_user_id'] = user['id']
            return redirect(url_for('auth.recuperar_paso2'))
        else:
            flash('Usuario/correo o cédula incorrectos', 'error')
            
    return render_template('recuperar_paso1.html')

@auth_bp.route('/recuperar_paso2', methods=['GET', 'POST'])
def recuperar_paso2():
    """Paso 2: Pregunta de seguridad y nueva contraseña."""
    user_id = session.get('recovery_user_id')
    if not user_id:
        return redirect(url_for('auth.recuperar'))
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if request.method == 'POST':
        respuesta = request.form['respuesta_seguridad'].lower().strip()
        nueva_password = request.form['nueva_password']
        
        if respuesta == user['respuesta_seguridad']:
            hashed_password = generate_password_hash(nueva_password)
            conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))
            conn.commit()
            conn.close()
            session.pop('recovery_user_id', None)
            flash('¡Contraseña actualizada correctamente! Inicia sesión con tu nueva clave.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('La respuesta de seguridad es incorrecta', 'error')
            
    conn.close()
    return render_template('recuperar_paso2.html', pregunta=user['pregunta_seguridad'])
