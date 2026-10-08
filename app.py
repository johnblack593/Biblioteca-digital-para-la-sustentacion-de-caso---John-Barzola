from flask import Flask
from flask_restful import Api


from modulos.configuracion import SECRET_KEY
from modulos.rutas_web import web_bp
from modulos.rutas_auth import auth_bp
from modulos.rutas_api import BookListAPI, BookResourceAPI

# Inicializar la aplicación Flask
app = Flask(__name__, template_folder='vistas', static_folder='vistas/data')

# Aplicar configuraciones
app.secret_key = SECRET_KEY

# Registrar Blueprints (Rutas web y autenticación)
app.register_blueprint(web_bp)
app.register_blueprint(auth_bp)

# Inicializar y configurar la API RESTful
api = Api(app)
api.add_resource(BookListAPI, '/api/books')
api.add_resource(BookResourceAPI, '/api/books/<int:id>')

if __name__ == '__main__':
    # activa la recarga automática cuando cambias el código
    app.run(debug=True)
