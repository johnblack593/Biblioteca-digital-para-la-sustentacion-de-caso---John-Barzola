from flask import Blueprint, jsonify, request
from flask_restful import Resource
from modulos.base_datos import get_db_connection
from modulos.rutas_web import get_or_create_genero, get_or_create_autor

class BookListAPI(Resource):
    def get(self):
        """GET /api/books: Devuelve listado de todos los libros."""
        conn = get_db_connection()
        query = '''
            SELECT b.id, b.titulo, b.anio, b.edicion, b.resumen, b.portada_path, b.pdf_path, 
                   g.nombre AS genero, GROUP_CONCAT(a.nombre, ', ') AS autor
            FROM books b
            LEFT JOIN generos g ON b.genero_id = g.id
            LEFT JOIN autores_libros al ON b.id = al.libro_id
            LEFT JOIN autores a ON al.autor_id = a.id
            GROUP BY b.id
        '''
        books_raw = conn.execute(query).fetchall()
        conn.close()
        books = [dict(b) for b in books_raw]
        return books, 200

    def post(self):
        data = request.get_json()
        if not data or not all(k in data for k in ("titulo", "autor", "genero", "anio")):
            return {'message': 'Faltan datos requeridos (titulo, autor, genero, anio)'}, 400
            
        conn = get_db_connection()
        genero_id = get_or_create_genero(conn, data['genero'])
        
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO books (titulo, genero_id, anio) VALUES (?, ?, ?)',
            (data['titulo'], genero_id, data['anio'])
        )
        new_id = cursor.lastrowid
        
        autores = [a.strip() for a in data['autor'].split(',')]
        for a_nombre in autores:
            if a_nombre:
                autor_id = get_or_create_autor(conn, a_nombre)
                conn.execute('INSERT INTO autores_libros (libro_id, autor_id) VALUES (?, ?)', (new_id, autor_id))

        conn.commit()
        conn.close()
        
        return {'message': 'Libro agregado', 'id': new_id}, 201

class BookResourceAPI(Resource):
    def get(self, id):
        conn = get_db_connection()
        query = '''
            SELECT b.id, b.titulo, b.anio, b.edicion, b.resumen, b.portada_path, b.pdf_path, 
                   g.nombre AS genero, GROUP_CONCAT(a.nombre, ', ') AS autor
            FROM books b
            LEFT JOIN generos g ON b.genero_id = g.id
            LEFT JOIN autores_libros al ON b.id = al.libro_id
            LEFT JOIN autores a ON al.autor_id = a.id
            WHERE b.id = ?
            GROUP BY b.id
        '''
        book = conn.execute(query, (id,)).fetchone()
        conn.close()
        
        if book is None:
            return {'message': 'Libro no encontrado'}, 404
        return dict(book), 200

    def put(self, id):
        data = request.get_json()
        if not data or not all(k in data for k in ("titulo", "autor", "genero", "anio")):
            return {'message': 'Faltan datos requeridos'}, 400
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar si existe
        if not conn.execute('SELECT id FROM books WHERE id = ?', (id,)).fetchone():
            conn.close()
            return {'message': 'Libro no encontrado'}, 404
            
        genero_id = get_or_create_genero(conn, data['genero'])
        
        cursor.execute(
            'UPDATE books SET titulo = ?, genero_id = ?, anio = ? WHERE id = ?',
            (data['titulo'], genero_id, data['anio'], id)
        )
        
        conn.execute('DELETE FROM autores_libros WHERE libro_id = ?', (id,))
        autores = [a.strip() for a in data['autor'].split(',')]
        for a_nombre in autores:
            if a_nombre:
                autor_id = get_or_create_autor(conn, a_nombre)
                conn.execute('INSERT INTO autores_libros (libro_id, autor_id) VALUES (?, ?)', (id, autor_id))
                
        conn.commit()
        conn.close()
        return {'message': 'Libro actualizado'}, 200

    def delete(self, id):
        conn = get_db_connection()
        cursor = conn.cursor()
        if not conn.execute('SELECT id FROM books WHERE id = ?', (id,)).fetchone():
            conn.close()
            return {'message': 'Libro no encontrado'}, 404
            
        cursor.execute('DELETE FROM prestamos WHERE libro_id = ?', (id,))
        cursor.execute('DELETE FROM autores_libros WHERE libro_id = ?', (id,))
        cursor.execute('DELETE FROM books WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return {'message': 'Libro eliminado'}, 200
