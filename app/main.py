"""
Archivo principal de la aplicación FastAPI.
Este módulo configura la aplicación, define los endpoints y gestiona el servicio del agente IA.

Funcionalidades principales:
- Configuración de la aplicación FastAPI y middleware CORS
- Inicialización del servicio del agente y gestor de sesiones
- Definición de endpoints para la interfaz de prueba y procesamiento de mensajes
- Manejo de estados de sesión y respuestas del agente
"""

# Importaciones del framework FastAPI y componentes relacionados
from fastapi import FastAPI, Request, Depends, HTTPException  # Framework principal y componentes básicos
from fastapi.middleware.cors import CORSMiddleware  # Middleware para manejar solicitudes de origen cruzado (CORS)
from fastapi.templating import Jinja2Templates  # Motor de plantillas para renderizar HTML
from fastapi.responses import HTMLResponse  # Clase para respuestas HTML

# Importaciones para manejo de configuración y variables de entorno
from dotenv import load_dotenv  # Carga variables de entorno desde archivo .env

# Importaciones relacionadas con la base de datos
from app.database.base import engine, SessionLocal, get_db  # Configuración y utilidades de base de datos
from app.database import models  # Modelos de datos SQLAlchemy
from sqlalchemy.orm import Session  # Clase para manejar sesiones de base de datos

# Importaciones para validación y tipado de datos
from pydantic import BaseModel  # Clase base para modelos de datos con validación
from typing import Optional, Dict, Any  # Tipos para anotaciones de tipo

# Importaciones para logging y registro de eventos
import logging  # Módulo de logging estándar de Python

# Importaciones de servicios propios de la aplicación
from app.services.agent.agent import AgentService  # Servicio principal del agente IA
from app.services.agent.intentions import Intention  # Clase para manejar intenciones del agente
from app.services.session.session_manager import SessionManager  # Gestor de sesiones de usuario

# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Crear las tablas en la base de datos
models.Base.metadata.create_all(bind=engine)

# Crear la aplicación FastAPI con metadatos
app = FastAPI(
    title="Agente IA Empresarial",  # Título de la API
    description="API para el agente IA empresarial con integración de Twilio y PostgreSQL",  # Descripción
    version="1.0.0"  # Versión de la API
)

# Configuración de CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir solicitudes desde cualquier origen
    allow_credentials=True,  # Permitir credenciales en las solicitudes
    allow_methods=["*"],  # Permitir todos los métodos HTTP
    allow_headers=["*"],  # Permitir todos los headers
)

templates = Jinja2Templates(directory="app/templates")

# Instancia global del servicio del agente y del gestor de sesiones
AGENT_SERVICE: Optional[AgentService] = None
SESSION_MANAGER = SessionManager() # Crear instancia del SessionManager

# Inicializar el servicio del agente en el inicio de la aplicación
@app.on_event("startup")
async def startup_event():
    """
    Evento que se ejecuta al iniciar la aplicación.
    Inicializa el servicio del agente como singleton global.
    """
    logger.info("Iniciando la aplicación FastAPI...")
    global AGENT_SERVICE
    # Solo inicializamos si aún no existe
    if AGENT_SERVICE is None:
        # Usamos una sesión temporal solo para la inicialización
        temp_db = SessionLocal()
        try:
            AGENT_SERVICE = AgentService(temp_db)
            logger.info("Servicio del agente inicializado como singleton global")
        except Exception as e:
             logger.exception("Error fatal al inicializar AgentService durante el startup.")
             # Podríamos decidir detener la app aquí si el agente es crítico
             raise RuntimeError("No se pudo inicializar AgentService") from e
        finally:
            temp_db.close()
    logger.info("Aplicación iniciada y lista.")

class Message(BaseModel):
    """
    Modelo de datos para los mensajes enviados al agente.

    Attributes:
        message (str): Contenido del mensaje.
        session_id (str): Identificador de la sesión del usuario.
    """
    message: str
    session_id: str = "default"

@app.get("/test", response_class=HTMLResponse)
async def test_interface(request: Request):
    """
    Endpoint que muestra la interfaz de prueba del agente.

    Args:
        request (Request): Objeto de solicitud FastAPI.

    Returns:
        TemplateResponse: Renderiza la plantilla HTML de la interfaz de prueba.
    """
    # El AGENT_SERVICE ya está inicializado globalmente en startup
    return templates.TemplateResponse("test.html", {"request": request})

@app.post("/test/message")
async def process_test_message(message: Message, db: Session = Depends(get_db)):
    """
    Endpoint unificado que procesa los mensajes enviados por el usuario al agente.
    
    Flujo de procesamiento:
    1. Carga el estado de la sesión actual
    2. Restaura el estado del agente si existe una acción pendiente
    3. Procesa el mensaje con el agente
    4. Guarda el nuevo estado de la sesión
    
    Args:
        message (Message): Mensaje del usuario con session_id
        db (Session): Sesión de base de datos inyectada por FastAPI
    
    Returns:
        dict: Respuesta del agente con el resultado del procesamiento
    
    Raises:
        HTTPException: Si hay errores en el procesamiento o el servicio no está disponible
    """
    global AGENT_SERVICE # Necesitamos acceder al singleton global
    global SESSION_MANAGER # Acceder al SessionManager global

    # Asegurar que el agente esté inicializado (aunque startup debería haberlo hecho)
    if AGENT_SERVICE is None:
         logger.error("AGENT_SERVICE no está inicializado al procesar mensaje.")
         raise HTTPException(status_code=500, detail="Error interno del servidor: Servicio del agente no disponible.")

    try:
        session_id = message.session_id
        logger.info(f"Procesando mensaje para sesión: {session_id}")

        # Actualizar la sesión de BD del agente para esta solicitud específica
        AGENT_SERVICE.update_db_session(db)

        # Cargar el estado de la sesión usando SessionManager
        session_state = SESSION_MANAGER.load_session(session_id)
        logger.debug(f"Estado cargado para sesión {session_id}: {session_state}")

        # Restaurar el estado del agente desde la sesión cargada
        # Verificar si pending_action es una instancia de Intention después de cargar
        pending_action_loaded = session_state.get("pending_action")
        if isinstance(pending_action_loaded, Intention):
             AGENT_SERVICE.pending_action = pending_action_loaded
             AGENT_SERVICE.pending_data = session_state.get("pending_data", {})
             AGENT_SERVICE.current_purpose = session_state.get("current_purpose")
             logger.info(f"Estado del agente restaurado para sesión {session_id} desde el estado cargado.")
        elif pending_action_loaded: # Si existe pero no es Intention (error en carga/reconstrucción)
             logger.warning(f"pending_action cargado para {session_id} no es un objeto Intention válido. Reiniciando estado.")
             AGENT_SERVICE.pending_action = None
             AGENT_SERVICE.pending_data = None
             AGENT_SERVICE.current_purpose = None
        else: # Si no había pending_action en el estado
             AGENT_SERVICE.pending_action = None
             AGENT_SERVICE.pending_data = None
             AGENT_SERVICE.current_purpose = None
             logger.info(f"No había acción pendiente en el estado cargado para {session_id}. Estado del agente reiniciado.")


        # Procesar el mensaje con el agente (ahora con el estado restaurado)
        response = await AGENT_SERVICE.process_message(message.message)
        logger.debug(f"Respuesta del agente para sesión {session_id}: {response}")

        # Guardar el estado actualizado del agente usando SessionManager
        current_agent_state = {
            "pending_action": AGENT_SERVICE.pending_action,
            "pending_data": AGENT_SERVICE.pending_data,
            "current_purpose": AGENT_SERVICE.current_purpose
        }
        SESSION_MANAGER.save_session(session_id, current_agent_state)
        logger.info(f"Estado actualizado guardado para sesión {session_id}")

        return response

    except HTTPException as http_exc:
         # Re-lanzar excepciones HTTP para que FastAPI las maneje
         raise http_exc
    except Exception as e:
        # Log detallado del error para depuración
        logger.exception(f"Error inesperado procesando mensaje para sesión {session_id}: {str(e)}") # Usar logger.exception para incluir traceback
        # Devolver un error genérico al cliente
        raise HTTPException(status_code=500, detail=f"Error interno al procesar el mensaje.")

@app.get("/")
async def root():
    """
    Endpoint raíz de la API.

    Returns:
        dict: Mensaje de bienvenida
    """
    logger.info("Acceso al endpoint raíz '/'")
    return {"message": "Bienvenido al Agente IA Empresarial"}

# Punto de entrada para ejecutar la aplicación (si se corre directamente)
if __name__ == "__main__":
    import uvicorn  # Servidor ASGI
    logger.info("Iniciando servidor Uvicorn directamente...")
    # Iniciar el servidor en todas las interfaces (0.0.0.0) en el puerto 8000
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) # Usar reload para desarrollo