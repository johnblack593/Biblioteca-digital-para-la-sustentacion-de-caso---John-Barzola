# Proyecto de Caso Práctico: Sistema Web de Biblioteca Virtual y Lectura Digital

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?logo=flask&logoColor=white)
![SQLite3](https://img.shields.io/badge/SQLite3-Normalizado%203FN-003B57?logo=sqlite&logoColor=white)
![CSS3](https://img.shields.io/badge/Frontend-Vanilla%20CSS-1572B6?logo=css3&logoColor=white)
![Estado](https://img.shields.io/badge/Estado-Completado%20100%25-22C55E)

> **Institución:** Instituto Superior Universitario Espíritu Santo (TES)  
> **Carrera:** Tecnología Superior en Desarrollo de Aplicaciones Web  
> **Asignatura / Módulo:** Caso Práctico – Desarrollo de una Aplicación Web con Base de Datos y API  
> **Estudiante / Autor:** Barzola Villamar John Christopher  
> **Docente Evaluador:** Ing. Juan Carlos Ramos  
> **Semestre:** Módulo 2 – Semestre 4 (2026) 

---

## 📖 1. Presentación del Proyecto

Hola profesor, bienvenido a la documentación de mi proyecto de titulación técnica. Este sistema consiste en una **Biblioteca Virtual y Plataforma de Lectura Digital en Línea**, desarrollada desde cero con **Python (Flask)** en el backend, una base de datos relacional en **SQLite3** completamente normalizada en **Tercera Forma Normal (3FN)**, y una interfaz de usuario limpia y moderna desarrollada con **HTML5 y Vanilla CSS** (sin librerías pesadas), optimizada para pantallas de escritorio y teléfonos móviles.

El objetivo principal del proyecto es brindar una solución completa a los problemas habituales de las bibliotecas físicas y digitales:
- Evitar que los usuarios se vean obligados a descargar archivos PDF pesados en sus dispositivos, ofreciendo un **visor de lectura integrado dentro del navegador**.
- Administrar el ciclo de préstamos y devoluciones con reglas de negocio claras (solo se puede leer un libro si se ha solicitado previamente su préstamo).
- Proteger el acceso al sistema mediante **control de acceso basado en roles (RBAC)** y validaciones de seguridad estrictas (cédula ecuatoriana, unicidad de correo y contraseñas cifradas con hash PBKDF2).

---

## 🚀 2. Características y Requisitos Implementados

A continuación, detallo las funciones incorporadas en la versión final del sistema:

### A. Registro y Seguridad de Usuarios
1. **Validación de Cédula de Identidad Ecuatoriana:**
   - Se implementó en el backend el algoritmo oficial del **módulo 10 (dígito verificador)** para cédulas de Ecuador (código de provincia entre 1 y 24 o 30, tercer dígito menor a 6, coeficientes alternados 2-1-2-1...). No permite el registro con números inventados o inválidos.
2. **El Correo Electrónico como Nombre de Usuario:**
   - Se eliminó el campo redundante de "usuario" en el formulario de registro. Ahora el **correo electrónico** es el identificador único para iniciar sesión.
   - El sistema comprueba en la base de datos que el correo no esté duplicado antes de crear la cuenta.
3. **Confirmación de Contraseña:**
   - El formulario solicita ingresar la contraseña dos veces para prevenir equivocaciones al escribirla.
4. **Cifrado de Credenciales:**
   - Ninguna contraseña se guarda en texto plano; se utiliza la función criptográfica `generate_password_hash` de Werkzeug (**PBKDF2-HMAC-SHA256 con sal aleatoria**).
5. **Autoservicio de Recuperación:**
   - Si el usuario olvida su clave, puede restablecerla respondiendo a una pregunta de seguridad preestablecida en su perfil.

### B. Catálogo General y Experiencia de Lectura
1. **Top 5 Libros Más Solicitados:**
   - Sección superior destacada en tarjetas visuales que calcula en tiempo real los 5 libros con mayor número de préstamos históricos.
2. **Últimos 5 Libros Añadidos:**
   - Vitrina superior que expone las 5 obras más recientes añadidas al acervo bibliográfico.
3. **Paginación Dinámica (10 libros por página):**
   - El catálogo principal muestra un máximo de 10 libros por página con botones interactivos de paginación (`Anterior`, selector numérico de páginas y `Siguiente`), evitando listas infinitas y optimizando la velocidad de carga.
4. **Acervo Completo de 46 Obras de la Literatura Universal:**
   - La base de datos incluye 46 libros clásicos universales (*Cien Años de Soledad*, *Don Quijote*, *1984*, *El Hobbit*, *Crimen y Castigo*, *Rayuela*, *Fahrenheit 451*, etc.).
   - Todas las 46 obras cuentan con sus **carátulas reales** descargadas y vinculadas en el sistema.
   - Todas las obras poseen **sinopsis literarias amplias, profundas y detalladas** (contexto histórico, trama central y valor temático).
5. **PDF de Muestra Didáctica Transversal:**
   - Todos los libros que no disponían de archivo digital propio tienen vinculado el PDF de muestra didáctica subido al sistema, garantizando que el docente o evaluador pueda abrir y probar el visor interactivo en cualquiera de las 46 obras.
6. **Flujo de Negocio en Detalle de Libro:**
   - Para acceder al libro digital, el lector debe **solicitar el préstamo primero**. Una vez aprobado el préstamo en el sistema, se desbloquea el botón **«Abrir Lector Integrado»** y el botón para devolverlo.
7. **Reseñas y Calificaciones Comunitarias (Mínimo 4 por Libro):**
   - Cada una de las 46 obras cuenta con al menos 4 reseñas analíticas y calificaciones en estrellas registradas por lectores de la comunidad, calculando en tiempo real el promedio de puntuación y exhibiendo insignias de «Lector Verificado» en la ficha técnica.

### C. Lector Digital Integrado en Navegador
1. **Sin Descargas Forzadas (RFC 6266):**
   - El servidor despacha el PDF inyectando la cabecera HTTP `Content-Disposition: inline; filename="..."` y `Content-Type: application/pdf`.
2. **Visor Inmersivo:**
   - Se muestra dentro de un marco `<iframe>` a pantalla completa con controles de navegación (`← Volver`) y botón para alternar el modo **Pantalla Completa** mediante la API nativa de JavaScript (`requestFullscreen()`).
   - Se removió cualquier botón innecesario para brindar una experiencia de lectura despejada y cómoda.

### D. Panel de Administración y Gestión
1. **Gestión de Catálogo:**
   - Permite crear, editar y eliminar libros.
   - Al registrar o modificar libros, los campos de **Género**, **Autor** y **Edición** cuentan con sugerencias automáticas mediante elementos `<datalist>` basados en los registros ya existentes en la base de datos, permitiendo también ingresar nuevos libremente.
2. **Paginación en el Panel de Administración:**
   - Tanto la sección de Gestión de Catálogo como el Control de Préstamos disponen de paginación de 10 elementos por página.
3. **Modales Interactivos:**
   - Al hacer clic en «Rol» de un usuario, se abre un cuadro modal para seleccionar el nuevo rol (`usuario` o `admin`).
   - Al eliminar un libro o usuario, se despliega un cuadro de confirmación para evitar borrados accidentales.
4. **Diseño Responsivo Móvil:**
   - Navegación móvil con menú hamburguesa desplegable.
   - Columnas de tablas adaptadas para pantallas pequeñas (ocultando columnas secundarias y mostrando metadatos integrados bajo el título).
   - Métricas y tarjetas rediseñadas para visualización ergonómica en teléfonos inteligentes y tabletas.
5. **Configuración Dinámica de Políticas de Préstamo (Sin Valores Harcodeados):**
   - Se eliminaron los límites fijos del código fuente. Desde la pestaña **«⚙️ Políticas de Préstamo»**, el administrador puede configurar en caliente:
     - **Límite máximo de libros simultáneos por lector** (parámetro configurable entre 1 y 50 libros).
     - **Plazo de devolución en días antes de incurrir en Mora** (parámetro configurable entre 1 y 365 días).
   - Los cambios se guardan en la tabla `configuracion` y se reflejan al instante en todo el sistema (validaciones de préstamo, cálculo de préstamos vencidos/mora y avisos al lector).

---

## 🔑 3. Credenciales de Prueba para la Evaluación

Para que el profesor o jurado evaluador pueda verificar tanto el rol de administrador como el de lector, se han dejado preparadas las siguientes cuentas oficiales configuradas en la base de datos:

| Rol de Usuario | Identificador (Login) | Contraseña | Nombre Registrado | ¿Qué permite hacer en el sistema? |
| :--- | :--- | :--- | :--- | :--- |
| **Administrador** | `admin` *(o `admin@biblioteca.com`)* | `admin` | Administrador del Sistema | Control total del catálogo (crear/editar/eliminar), visualización de métricas KPI, gestión de roles de usuarios, configuración dinámica de políticas de préstamo y supervisión de todos los préstamos. |
| **Lector / Usuario** | `user` *(o `lector@biblioteca.com`)* | `user` | Juan Carlos Pérez | Explorar el catálogo de 46 obras, solicitar préstamos, abrir el lector integrado en pantalla completa, devolver libros, calificar con estrellas y ver su estantería personal. |

> *Nota:* El sistema permite iniciar sesión indistintamente ingresando el **nombre de usuario** (`admin`, `user`) o el **correo electrónico** (`admin@biblioteca.com`, `lector@biblioteca.com`). También es posible registrar una cuenta nueva en la pantalla `/register` utilizando cualquier cédula ecuatoriana válida de 10 dígitos.

---

## 🗄️ 4. Estructura de la Base de Datos y Claves

La base de datos relacional está implementada en **SQLite3** (`modulos/biblioteca.db`) y consta de 8 tablas normalizadas (incluyendo valoraciones comunitarias y configuración dinámica del sistema):

```text
                  +---------------+
                  |    GENEROS    |
                  +---------------+
                  | id (PK)       |
                  | nombre        |
                  +-------+-------+
                          | 1:N
                          v
+-------------+   +---------------+   +------------------+   +-------------+
|    USERS    |   |     BOOKS     |   |  AUTORES_LIBROS  |   |   AUTORES   |
+-------------+   +---------------+   +------------------+   +-------------+
| id (PK)     |   | id (PK)       |   | libro_id (PK,FK) |   | id (PK)     |
| username    |   | titulo        |<--| autor_id (PK,FK) |--->| nombre      |
| email (UQ)  |   | genero_id(FK) |   +------------------+   +-------------+
| password    |   | anio          |
| nombres     |   | edicion       |
| apellidos   |   | resumen       |
| cedula      |   | portada_path  |
| rol         |   | pdf_path      |
+------+------+   +-------+-------+
       |                  |
       | 1:N              | 1:N
       +--------+ +-------+
                | |
                v v
         +---------------+         +---------------+         +-----------------+
         |   PRESTAMOS   |         |    RESENAS    |         |  CONFIGURACION  |
         +---------------+         +---------------+         +-----------------+
         | id (PK)       |         | id (PK)       |         | clave (PK, TEXT)|
         | user_id (FK)  |         | user_id (FK)  |         | valor (TEXT)    |
         | libro_id (FK) |         | libro_id (FK) |         | descripcion(TXT)|
         | fecha_prestamo|         | calificacion  |         +-----------------+
         | fecha_devoluc |         | comentario    |
         | estado        |         | fecha         |
         +---------------+         +---------------+
```

- **`configuracion`:** Almacena parámetros dinámicos de administración (`limite_libros_prestamo`, `dias_plazo_devolucion`).
- **`resenas`:** Almacena opiniones y puntuaciones (1 a 5 estrellas) con integridad referencial hacia `users` y `books`.

### ❓ ¿Cuál es la Clave Primaria de los Usuarios? (Explicación para el Examen)
- **A nivel de Base de Datos (Técnico):** La clave primaria formal (`PRIMARY KEY`) es el campo **`id`** (`INTEGER PRIMARY KEY AUTOINCREMENT`). Se utiliza un entero autoincremental porque es mucho más eficiente para indexar y actúa como clave foránea (`FOREIGN KEY`) en la tabla `prestamos(user_id)`.
- **A nivel de Negocio / Formulario:** El **correo electrónico (`email`)** es una **clave candidata única (`UNIQUE`)**. Aunque la clave primaria interna es el `id`, el usuario no necesita saber su número de ID para ingresar; utiliza su correo electrónico como credencial identificadora irrepetible.

---

## 🛠️ 5. Pasos para Instalar y Ejecutar el Proyecto en Local

### Paso 1: Clonar o descargar el proyecto
Abrir la terminal y clonar el repositorio del proyecto:
```bash
git clone https://github.com/johnblack593/Biblioteca-digital-para-la-sustentacion-de-caso---John-Barzola.git
cd Biblioteca-digital-para-la-sustentacion-de-caso---John-Barzola
```

### Paso 2: Crear y activar el entorno virtual (`venv`)
Se utiliza un entorno virtual para que las librerías no interfieran con el sistema operativo:
- **En Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
  *(Si PowerShell muestra error de permisos de ejecución, se puede habilitar con: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` o usar CMD con: `.\venv\Scripts\activate.bat`)*
- **En Linux / macOS:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Paso 3: Instalar las dependencias
Con el entorno virtual activado (verás `(venv)` al inicio de la línea de comandos), ejecuta:
```powershell
pip install -r requirements.txt
```

### Paso 4: Ejecutar el servidor web
Inicia la aplicación con Python:
```powershell
python app.py
```
El servidor arrancará en modo de desarrollo en la dirección local:
```text
http://127.0.0.1:5000
```

### Paso 5: Abrir en el navegador
Abre Google Chrome, Microsoft Edge o Firefox e ingresa a `http://127.0.0.1:5000` para comenzar a interactuar con la biblioteca.

---

## 📁 6. Organización de Archivos del Proyecto

```text
EXA-PRACTICO-JCBV/
│
├── app.py                      # Archivo principal de arranque y configuración de Flask
├── requirements.txt            # Lista de dependencias del proyecto (Flask, Werkzeug, etc.)
├── README.md                   # Esta guía general del proyecto
├── .gitignore                  # Exclusión del entorno virtual venv y archivos temporales
│
├── modulos/                    # Lógica de programación del servidor (Backend)
│   ├── __init__.py             # Inicializador del paquete de módulos
│   ├── base_datos.py           # Conexión centralizada a SQLite3 y utilidades de configuración
│   ├── biblioteca.db           # Base de datos relacional con 46 obras, usuarios y préstamos
│   ├── configuracion.py        # Claves secretas, rutas y tipos de archivos permitidos
│   ├── iniciar_bd.py           # Script de inicialización y migración del esquema de base de datos
│   ├── rutas_auth.py           # Login, registro con cédula y correo, recuperación de clave
│   ├── rutas_web.py            # Rutas del catálogo, préstamos, administración y visor PDF
│   ├── validadores.py          # Algoritmo de validación de cédula de identidad ecuatoriana
│   └── rutas_api.py            # API RESTful en JSON para integración externa (/api/books)
│
└── vistas/                     # Archivos visuales que ve el usuario (Frontend Jinja2)
    ├── plantilla_base.html     # Barra de navegación superior, pie de página y estructura
    ├── inicio.html             # Catálogo principal, Top 5 solicitados, últimos 5 y paginación
    ├── detalle_libro.html      # Ficha técnica, carátula en alta definición y sinopsis rica
    ├── admin_panel.html        # Panel administrativo con pestañas paginadas y modales
    ├── visor_pdf.html          # Lector digital integrado a pantalla completa
    ├── mi_estanteria.html      # Libros prestados actualmente, historial y métricas
    ├── perfil.html             # Perfil del usuario, datos personales y seguridad
    ├── acceso.html             # Formulario de inicio de sesión (usuario o correo)
    ├── registro.html           # Formulario de registro con cédula ecuatoriana y 2 contraseñas
    ├── recuperar_paso1.html    # Recuperación de contraseña (paso 1: identificación)
    ├── recuperar_paso2.html    # Recuperación de contraseña (paso 2: pregunta de seguridad)
    │
    └── data/                   # Recursos estáticos de la aplicación
        ├── css/
        │   └── estilos.css     # Estilos Vanilla CSS con modo responsivo móvil
        ├── img/
        │   └── fondo_login.jpg # Imagen de fondo ilustrativa para el acceso
        ├── portadas/           # 46 carátulas en formato JPG de las obras clásicas
        └── pdfs/               # Archivos PDF para lectura digital (incluye muestra didáctica)
```

---

## 🌐 7. Endpoints de la API RESTful

Para demostrar la capacidad de integración con otras plataformas o aplicaciones móviles, el sistema expone los siguientes servicios web que responden en formato JSON:

| Método | URL | Descripción |
| :---: | :--- | :--- |
| `GET` | `/api/books` | Retorna la lista de todos los libros con sus autores, géneros y años. |
| `GET` | `/api/books/<id>` | Retorna la información completa de un libro por su identificador. |
| `POST` | `/api/books` | Permite registrar un nuevo libro enviando un objeto JSON. |
| `PUT` | `/api/books/<id>` | Permite actualizar los datos de una obra existente. |
| `DELETE`| `/api/books/<id>` | Permite eliminar un libro del catálogo. |

---

## 🔒 8. Nota sobre Seguridad: ¿Por qué HTTP en local y HTTPS en producción?

Durante el desarrollo académico, la aplicación corre de forma nativa en `http://127.0.0.1:5000`. Esto se hizo a propósito para evitar advertencias molestas de navegadores por certificados autofirmados inválidos y errores de protocolo durante la depuración.

En un entorno de producción real en internet (siguiendo las recomendaciones de *The Twelve-Factor App*), Flask no debe encargarse directamente de los certificados SSL. La forma correcta es colocar un **servidor web frontal como Nginx** que reciba el tráfico HTTPS seguro en el puerto 443 con un certificado gratuito de **Let's Encrypt**, y luego pase las peticiones de forma interna y rápida al servidor de Flask.

---

## 🎓 9. Conclusión del Estudiante

El desarrollo de este caso práctico me ha permitido aplicar de forma práctica los conocimientos adquiridos a lo largo de la carrera en desarrollo web:
1. Diseñar y normalizar bases de datos relacionales sin redundancia.
2. Programar lógica de backend estructurada y limpia con Python y Flask.
3. Aplicar validaciones de seguridad reales (como el dígito verificador ecuatoriano y el hash criptográfico de contraseñas).
4. Diseñar interfaces web intuitivas, responsivas y agradables utilizando Vanilla CSS puro.
5. Desarrollar una API RESTful estándar lista para conectarse con cualquier cliente moderno.

*Desarrollado con dedicación para la obtención del título de Tecnólogo Superior en Desarrollo de Aplicaciones Web.*
