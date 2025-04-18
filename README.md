# Agent IA Empresarial

Sistema de agente conversacional inteligente para gestión empresarial que utiliza procesamiento de lenguaje natural para realizar operaciones CRUD y mantener conversaciones con los usuarios.

## 🚀 Características

- **Interfaz conversacional**: Interactúa con el sistema usando lenguaje natural
- **Gestión de clientes**: Crear, listar, buscar, actualizar y eliminar clientes
- **Gestión de productos**: Crear, listar, buscar, actualizar y eliminar productos
- **Gestión de ventas**: Crear ventas y asociar productos y clientes
- **Generación de facturas**: Crear facturas a partir de ventas
- **Chatbot conversacional**: Interacción general con preguntas, saludos y consultas
- **Integración con Twilio**: Servicio para comunicación por mensajes (configurado pero opcional)
- **Persistencia en base de datos**: Almacenamiento en PostgreSQL

## 🛠️ Tecnologías utilizadas

- **FastAPI**: Framework web de alto rendimiento
- **SQLAlchemy**: ORM para interacción con base de datos
- **PostgreSQL**: Base de datos relacional
- **Langchain**: Framework para aplicaciones basadas en LLM
- **Ollama**: Para ejecutar modelos de lenguaje localmente
- **Pydantic**: Validación de datos y configuraciones
- **Alembic**: Migraciones de base de datos
- **Jinja2**: Motor de plantillas para la interfaz web

## 📋 Requisitos previos

- Python 3.9+
- PostgreSQL instalado y en ejecución
- [Ollama](https://ollama.ai/download) instalado (para ejecutar modelos de lenguaje localmente)
- Modelo llama3 o mistral descargado en Ollama (`ollama pull mistral:7b` o `ollama pull llama3`)

## ⚙️ Instalación

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/tu-usuario/Agent_2.git
   cd Agent_2
   ```

2. Crear y activar un entorno virtual:

   ```bash
   # Windows
   python -m venv env
   .\env\Scripts\activate

   # Linux/Mac
   python -m venv env
   source env/bin/activate
   ```

3. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Configurar variables de entorno:
   Copia el archivo `.env.example` a `.env` y ajusta los valores:

   ```
   DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/nombre_db
   OLLAMA_API_URL=http://localhost:11434
   OLLAMA_MODEL=mistral:7b
   OLLAMA_API_KEY=ollama
   SECRET_KEY=tu_clave_secreta
   DEBUG=True
   ```

5. Crear la base de datos en PostgreSQL:

   ```bash
   # Desde la línea de comandos de PostgreSQL
   createdb nombre_db
   ```

6. Inicializar la base de datos:
   ```bash
   # Ejecutar las migraciones
   alembic upgrade head
   ```

## 🚀 Ejecución

Para iniciar la aplicación en modo desarrollo:

```bash
uvicorn app.main:app --reload
```

La aplicación estará disponible en `http://localhost:8000/test`

## 🌐 Despliegue en producción

Para desplegar en un entorno de producción:

1. Configura un servidor web como Nginx o Apache como proxy inverso
2. Utiliza Gunicorn como servidor WSGI para mayor rendimiento:
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app
   ```
3. Configura un servicio systemd para mantener la aplicación en ejecución
4. Ajusta las variables de entorno para producción (DEBUG=False)

## 💬 Uso del Agente

Una vez que la aplicación esté en ejecución, puedes interactuar con el sistema utilizando la interfaz web en `/test`.

Ejemplos de comandos:

- "Listar clientes"
- "Crear un nuevo cliente con nombre Juan Pérez y email juan@example.com"
- "Mostrar productos"
- "Hola, ¿qué puedes hacer?"
- "¿Cómo funcionan las ventas?"

## 🔧 Solución de problemas

### Error de conexión con Ollama

Si aparece el error "Cannot connect to host localhost:11434":

1. Verifica que Ollama esté instalado y en ejecución
2. Asegúrate de que el modelo especificado en `.env` esté descargado
3. Ejecuta `ollama list` para ver tus modelos disponibles
4. Comprueba la configuración de firewall si usas una IP remota

### Error de conexión a base de datos

1. Verifica que PostgreSQL esté en ejecución
2. Comprueba que la cadena de conexión en `.env` sea correcta
3. Asegúrate de que la base de datos exista

## 📝 Estructura del proyecto

```
.
├── app
│   ├── api            # Endpoints de la API
│   ├── database       # Modelos y configuración de BD
│   ├── services       # Servicios del agente y procesamiento
│   ├── schemas        # Esquemas Pydantic
│   ├── templates      # Plantillas HTML
│   └── main.py        # Punto de entrada principal
├── .env               # Variables de entorno
├── alembic            # Configuración de migraciones
├── requirements.txt   # Dependencias
└── README.md          # Este archivo
```

## 🤝 Contribuir

Si deseas contribuir al proyecto:

1. Haz un fork del repositorio
2. Crea una rama para tu funcionalidad (`git checkout -b feature/nueva-funcionalidad`)
3. Realiza tus cambios y haz commit (`git commit -m 'Agrega nueva funcionalidad'`)
4. Sube los cambios a tu rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request
