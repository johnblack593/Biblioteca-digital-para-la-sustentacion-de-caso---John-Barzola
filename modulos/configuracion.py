import os

# Ruta base del proyecto (un nivel arriba de modulos)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

# Configuración de Base de Datos
DATABASE = os.path.join(BASE_DIR, 'biblioteca.db')

# Configuración de Archivos Subidos (vistas/data)
UPLOAD_FOLDER = os.path.join(ROOT_DIR, 'vistas', 'data', 'pdfs')
PORTADAS_FOLDER = os.path.join(ROOT_DIR, 'vistas', 'data', 'portadas')

# Extensiones permitidas
ALLOWED_EXTENSIONS = {'pdf'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Crear las carpetas si no existen
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PORTADAS_FOLDER, exist_ok=True)

# Secret Key para la aplicación
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or os.urandom(24)
