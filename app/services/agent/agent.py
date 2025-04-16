"""
Servicio del Agente IA para procesamiento de lenguaje natural y gestión de acciones.

Este módulo implementa el servicio principal del agente que:
- Gestiona la interacción con el modelo de lenguaje Ollama
- Procesa mensajes de usuario y detecta intenciones
- Ejecuta acciones CRUD en la base de datos
- Mantiene el estado de la conversación y el flujo de confirmación

Clases principales:
    AgentService: Clase principal que maneja toda la lógica del agente

Dependencias principales:
    - langchain_community.llms.Ollama: Para interacción con el modelo de lenguaje
    - sqlalchemy.orm: Para operaciones de base de datos
    - intentions: Para el sistema de reconocimiento de intenciones
"""

# Importaciones necesarias para el servicio del agente
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnablePassthrough
from .intentions import Intention, match_intention, INTENTIONS, IntentionType, EntityType, ActionType
from ...database.crud import CRUDService
from sqlalchemy.orm import Session
import json
import logging
from dotenv import load_dotenv
import os
import copy
import datetime
import re

# Configurar logging para seguimiento y depuración
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno para configuración
load_dotenv()

class AgentService:
    """
    Servicio principal del agente IA que gestiona el procesamiento de mensajes y acciones.
    
    Esta clase implementa:
    - Inicialización y configuración del modelo de lenguaje Ollama
    - Procesamiento de mensajes y detección de intenciones
    - Sistema de confirmación para acciones críticas
    - Ejecución de operaciones CRUD en la base de datos
    
    Atributos:
        db (Session): Sesión activa de SQLAlchemy
        crud (CRUDService): Servicio para operaciones CRUD
        pending_action (Optional[Intention]): Acción pendiente de confirmación
        pending_data (Optional[dict]): Datos extraídos para la acción pendiente
        current_purpose (Optional[str]): Propósito actual de la conversación
        llm (Ollama): Instancia del modelo de lenguaje
        parser (JsonOutputParser): Parser para salidas en formato JSON
    """
    def __init__(self, db: Session):
        """
        Inicializa el servicio del agente.
        Configura el modelo de lenguaje, analizador de intenciones y estado de la conversación.
        
        Args:
            db (Session): Sesión de base de datos para operaciones CRUD.
        """
        try:
            # Inicializar dependencias y estado
            self.db = db
            self.crud = CRUDService(db)
            
            # Variables de estado para el flujo de confirmación
            self.pending_action = None  # Acción pendiente de confirmación
            self.pending_data = None    # Datos extraídos para la acción pendiente
            self.current_purpose = None # Propósito actual de la conversación
            
            # Configuración de Ollama desde variables de entorno
            base_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")
            model = os.getenv("OLLAMA_MODEL", "mistral:7b")
            temperature = os.getenv("OLLAMA_MODEL_TEMPERATURE", 0.0)

            logger.info(f"Inicializando modelo {model} en {base_url} con temperatura {temperature}")
            
            # Inicializar el modelo de lenguaje con parámetros optimizados
            self.llm = Ollama(
                base_url=base_url,
                model=model,
                temperature=temperature,    # Control de creatividad (0.0-1.0)
                top_p=0.8,          # Muestreo de probabilidad acumulativa
                num_ctx=4096,       # Tamaño del contexto en tokens
                num_thread=4,       # Hilos para inferencia
                repeat_penalty=1.1, # Penalización para repeticiones
                stop=["</s>", "```"] # Tokens de parada
            )
            
            # Configurar el parser para salida en formato JSON
            self.parser = JsonOutputParser()
            
            # Definir la plantilla de prompt para análisis de intención
            self.intention_prompt = PromptTemplate(
                input_variables=["user_message"],
                template="""<s>[INST] Eres un asistente virtual de una empresa. Analiza el siguiente mensaje del usuario y determina:
                1. La intención del usuario (consulta, registro, modificación, eliminación, venta, facturación, otro)
                2. Las entidades mencionadas (cliente, producto, venta, factura, detalle_venta)
                3. La acción requerida (listar, buscar, crear, actualizar, eliminar, procesar_venta, generar_factura, actualizar_stock)
                4. Los datos extraídos del mensaje

                Mensaje del usuario: {user_message}

                IMPORTANTE: Debes responder ÚNICAMENTE con JSON válido, sin texto adicional.
                Usa esta estructura exacta:
                {{
                    "intention": "tipo de intención",
                    "entities": ["entidades mencionadas"],
                    "action": "acción requerida",
                    "extracted_data": {{
                        "entidad1": {{"campo1": "valor1", "campo2": "valor2"}},
                        "entidad2": {{"campo1": "valor1"}}
                    }}
                }}
                
                IMPORTANTE: En caso de que no se pueda determinar la intencion o la intencion no sea alguna de las mencionadas, responde con la intención "otro" y en la entidad "otro" y en la acción "otro".
                
                [/INST]</s>"""
            )
            
            # Crear la cadena de procesamiento para análisis de intención
            self.intention_chain = (
                {"user_message": RunnablePassthrough()}
                | self.intention_prompt
                | self.llm
                | self.parser
            )
            
            logger.info("Servicio del agente inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error al inicializar el servicio del agente: {str(e)}")
            raise
    
    def update_db_session(self, db: Session):
        """
        Actualiza la sesión de base de datos del servicio.
        Este método es importante para mantener una sesión válida en cada solicitud.
        
        Args:
            db (Session): Nueva sesión de base de datos.
        """
        self.db = db
        self.crud = CRUDService(db)

    async def process_message(self, message: str) -> dict:
        """
        Procesa un mensaje del usuario y determina la acción a realizar.
        Implementa un flujo de confirmación para las acciones detectadas.
        
        Args:
            message (str): Mensaje del usuario a procesar.
            
        Returns:
            dict: Respuesta estructurada con el resultado del procesamiento.
                  Incluye status, message y data según el tipo de respuesta.
        """
        try:
            logger.info(f"Procesando mensaje: {message}")
            logger.info(f"Estado actual: pending_action={self.pending_action is not None}, purpose={self.current_purpose}")
            
            # Verificar si es una confirmación o negación
            message_lower = message.lower().strip()
            
            # Comprobar si tenemos una acción pendiente
            if self.pending_action:
                logger.info(f"Hay una acción pendiente: {self.pending_action.type} - {self.pending_action.action}")
                
                # Crear copias profundas para evitar modificaciones no deseadas
                # durante el procesamiento de la acción
                action_to_execute = copy.deepcopy(self.pending_action)
                data_to_use = copy.deepcopy(self.pending_data)
                
                # Guardamos los valores antes de limpiar el estado
                # para incluirlos en la respuesta final
                action_type = self.pending_action.type
                action_entities = self.pending_action.entities
                action_action = self.pending_action.action
                
                # Ejecutar la acción con los datos extraídos previamente
                result = await self.execute_action(action_to_execute, data_to_use)
                
                # Limpiar el estado para nuevas acciones
                self.pending_action = None
                self.pending_data = None
                self.current_purpose = None
                
                logger.info(f"Acción ejecutada con éxito: {result}")
                
                # Respuesta de éxito
                return {
                    "status": "success",
                    "message": f"Tarea completada exitosamente:\n{json.dumps(result, indent=2)}\n\n¿Qué otra tarea desea realizar?",
                    "data": {
                        "intention": action_type,
                        "entities": action_entities,
                        "action": action_action,
                        "result": result
                    }
                }
            else:
                # Si no hay acción pendiente, analizar el mensaje
                # Ya sea un mensaje nuevo o la palabra "sí"/"no" sin contexto
                
                # Detectar si el mensaje parece ser una confirmación o negación sin contexto
                if message_lower in ["sí", "si", "s", "yes", "no", "n", "cancel", "cancelar"]:
                    logger.warning(f"Recibida confirmación/negación sin acción pendiente: {message}")
                    return {
                        "status": "error",
                        "message": "No hay ninguna acción pendiente para confirmar o cancelar. ¿Qué tarea desea realizar?",
                        "data": None
                    }
                
                # Analizar la intención del mensaje (no hay acción pendiente)
                try:
                    # Llamar al modelo para analizar la intención
                    intention_analysis = await self.intention_chain.ainvoke(message)
                    logger.info(f"Análisis de intención: {intention_analysis}")
                    
                    # Validar el resultado del análisis
                    if not intention_analysis or not isinstance(intention_analysis, dict):
                        raise ValueError("El análisis de intención no devolvió un resultado válido")
                    
                    # Obtener la intención correspondiente de la lista predefinida
                    intention = match_intention(message)
                    if not intention:
                        return {
                            "status": "error",
                            "message": "No se pudo determinar la intención del mensaje. ¿Qué tarea desea realizar?",
                            "data": None
                        }
                    
                    # Guardar la acción pendiente para confirmación
                    self.pending_action = intention
                    self.pending_data = intention_analysis.get("extracted_data", {})
                    self.current_purpose = f"Realizar {intention.action} en {', '.join(intention.entities)}"
                    
                    logger.info(f"Nueva acción pendiente: {self.pending_action.action} - {self.current_purpose}")
                    
                    # Preparar mensaje de confirmación con detalles de la acción
                    confirmation_message = f"Detecté que deseas realizar la siguiente acción:\n"
                    confirmation_message += f"Intención: {intention.type}\n"
                    confirmation_message += f"Entidades: {', '.join(intention.entities)}\n"
                    confirmation_message += f"Acción: {intention.action}\n"
                    confirmation_message += f"Datos extraídos: {json.dumps(self.pending_data, indent=2)}\n\n"
                    confirmation_message += "¿Deseas que proceda con esta acción? (Responde 'sí' o 'no')"
                    
                    # Respuesta que requiere confirmación
                    return {
                        "status": "confirmation_required",
                        "message": confirmation_message,
                        "data": {
                            "intention": intention.type,
                            "entities": intention.entities,
                            "action": intention.action,
                            "extracted_data": self.pending_data
                        }
                    }
                    
                except Exception as e:
                    logger.error(f"Error en el análisis de intención: {str(e)}")
                    return {
                        "status": "error",
                        "message": f"Error al analizar la intención: {str(e)}\n¿Qué tarea desea realizar?",
                        "data": None
                    }
            
        except Exception as e:
            logger.error(f"Error al procesar mensaje: {str(e)}")
            return {
                "status": "error",
                "message": f"Error al procesar el mensaje: {str(e)}\n¿Qué tarea desea realizar?",
                "data": None
            }

    async def execute_action(self, intention: Intention, extracted_data: dict) -> dict:
        """
        Ejecuta la acción correspondiente a la intención detectada en la base de datos.
        
        Este método:
        1. Valida la intención y los datos extraídos
        2. Ejecuta la operación CRUD correspondiente
        3. Convierte los resultados a formato JSON serializable
        
        Args:
            intention (Intention): Intención detectada que define la acción a realizar
            extracted_data (dict): Datos extraídos del mensaje del usuario, organizados por entidad
        
        Returns:
            dict: Resultado serializable de la acción ejecutada, con la siguiente estructura:
                {
                    "status": str,  # "success" o "error"
                    "message": str, # Descripción del resultado
                    "data": dict   # Datos resultantes de la operación
                }
        
        Raises:
            ValueError: Si faltan datos requeridos para la operación
            Exception: Si ocurre un error durante la ejecución de la acción
        
        Ejemplo:
            >>> intention = Intention(type=IntentionType.CONSULTA, action=ActionType.LISTAR)
            >>> data = {"cliente": {"id": 1}}
            >>> result = await agent.execute_action(intention, data)
            >>> print(result)
            {"status": "success", "data": {"clientes": [...]}}
        """
        
        # Helper para convertir un objeto SQLAlchemy a un dict serializable
        def model_to_dict(model_instance):
            if model_instance is None:
                return None
            # Excluir el estado interno de SQLAlchemy y convertir tipos no serializables
            data = {}
            for c in model_instance.__table__.columns:
                value = getattr(model_instance, c.key)
                if isinstance(value, datetime.datetime): # Convertir datetime a string ISO
                    data[c.key] = value.isoformat()
                # Se podrían añadir otras conversiones aquí si fuera necesario (ej. Decimal)
                else:
                    data[c.key] = value
            return data

        try:
            logger.info(f"Ejecutando acción: {intention.action.value} para entidades: {[e.value for e in intention.entities]}")
            # Lógica para listar registros
            if intention.action == ActionType.LISTAR:
                if EntityType.CLIENTE in intention.entities:
                    clientes = self.crud.get_clientes()
                    # Convertir cada cliente a un diccionario serializable
                    result_data = [model_to_dict(cliente) for cliente in clientes]
                    return {"clientes": result_data}
                elif EntityType.PRODUCTO in intention.entities:
                    productos = self.crud.get_productos()
                    result_data = [model_to_dict(producto) for producto in productos]
                    return {"productos": result_data}
                elif EntityType.VENTA in intention.entities:
                    ventas = self.crud.get_ventas()
                    result_data = [model_to_dict(venta) for venta in ventas]
                    return {"ventas": result_data}
                elif EntityType.FACTURA in intention.entities:
                    facturas = self.crud.get_facturas()
                    result_data = [model_to_dict(factura) for factura in facturas]
                    return {"facturas": result_data}
            
            # Lógica para crear registros
            elif intention.action == ActionType.CREAR:
                if EntityType.CLIENTE in intention.entities:
                    cliente_data = extracted_data.get(EntityType.CLIENTE.value, {})
                    cliente = self.crud.create_cliente(cliente_data)
                    return {"cliente": model_to_dict(cliente)}
                elif EntityType.PRODUCTO in intention.entities:
                    producto_data = extracted_data.get(EntityType.PRODUCTO.value, {})
                    producto = self.crud.create_producto(producto_data)
                    return {"producto": model_to_dict(producto)}
                # Añadir lógica similar para VENTA y FACTURA si es necesario crear directamente

            # Lógica para actualizar registros
            elif intention.action == ActionType.ACTUALIZAR:
                if EntityType.CLIENTE in intention.entities:
                    cliente_info = extracted_data.get(EntityType.CLIENTE.value, {})
                    cliente_id = cliente_info.get("id")
                    if not cliente_id:
                         raise ValueError("Se requiere 'id' para actualizar cliente.")
                    cliente = self.crud.update_cliente(cliente_id, cliente_info)
                    return {"cliente": model_to_dict(cliente)}
                elif EntityType.PRODUCTO in intention.entities:
                    producto_info = extracted_data.get(EntityType.PRODUCTO.value, {})
                    producto_id = producto_info.get("id")
                    if not producto_id:
                         raise ValueError("Se requiere 'id' para actualizar producto.")
                    producto = self.crud.update_producto(producto_id, producto_info)
                    return {"producto": model_to_dict(producto)}
                # Añadir lógica similar para VENTA y FACTURA

            # Lógica para eliminar registros
            elif intention.action == ActionType.ELIMINAR:
                if EntityType.CLIENTE in intention.entities:
                    cliente_info = extracted_data.get(EntityType.CLIENTE.value, {})
                    cliente_id = cliente_info.get("id")
                    if not cliente_id:
                         raise ValueError("Se requiere 'id' para eliminar cliente.")
                    success = self.crud.delete_cliente(cliente_id)
                    return {"success": success, "message": f"Cliente con ID {cliente_id} {'eliminado' if success else 'no encontrado'}."}
                elif EntityType.PRODUCTO in intention.entities:
                    producto_info = extracted_data.get(EntityType.PRODUCTO.value, {})
                    producto_id = producto_info.get("id")
                    if not producto_id:
                         raise ValueError("Se requiere 'id' para eliminar producto.")
                    success = self.crud.delete_producto(producto_id)
                    return {"success": success, "message": f"Producto con ID {producto_id} {'eliminado' if success else 'no encontrado'}."}
                # Añadir lógica similar para VENTA y FACTURA

            # Acción no implementada o no reconocida aquí
            logger.warning(f"Acción no implementada o no reconocida en execute_action: {intention.action}")
            return {"status": "error", "message": f"Acción '{intention.action.value}' no implementada."}
            
        except ValueError as ve:
             logger.error(f"Error de datos al ejecutar acción {intention.action.value}: {str(ve)}")
             # Devolvemos un diccionario de error serializable
             return {"status": "error", "message": f"Error de datos: {str(ve)}"}
        except Exception as e:
            # Captura otras excepciones (ej. de base de datos)
            logger.exception(f"Error inesperado al ejecutar acción {intention.action.value}: {str(e)}") # Usar exception para traceback
            # Lanzar la excepción para que sea manejada por process_message o el llamador superior
            # Esto asegura que el estado pendiente se limpie correctamente en process_message
            raise # Re-lanza la excepción original

    def setup_index(self):
        """
        Configura el índice vectorial para búsqueda semántica de documentos.
        
        Este método (pendiente de implementar):
        - Cargará documentos desde la base de datos
        - Creará embeddings para búsqueda semántica
        - Configurará el índice vectorial para consultas rápidas
        
        TODO:
        - Implementar carga de documentos
        - Configurar modelo de embeddings
        - Crear estructura de índice
        """
        pass

    async def process_query(self, query: str, context: dict = None):
        """
        Procesa una consulta específica utilizando el índice vectorial.
        
        Este método (pendiente de implementar):
        - Vectorizará la consulta
        - Buscará documentos relevantes en el índice
        - Generará una respuesta contextual
        
        Args:
            query (str): Consulta del usuario
            context (dict, optional): Contexto adicional para la búsqueda
            
        TODO:
        - Implementar vectorización de consulta
        - Agregar búsqueda en índice
        - Generar respuesta con contexto
        """
        pass

    async def handle_database_operation(self, operation: str, data: dict):
        """
        Maneja operaciones de base de datos (a implementar).
        
        Args:
            operation (str): Tipo de operación a realizar
            data (dict): Datos necesarios para la operación
        """
        pass 