"""
Módulo de gestión de estados de sesión para el Agente IA.

Este módulo proporciona funcionalidad para:
- Persistencia de estados de sesión en archivos JSON
- Serialización y deserialización de objetos complejos
- Reconstrucción de objetos Intention desde datos serializados

Clases principales:
    SessionManager: Gestor principal de estados de sesión

Constantes:
    SESSION_DIR: Directorio donde se almacenan los archivos de sesión

Dependencias:
    - json: Para serialización/deserialización de datos
    - app.services.agent.intentions: Para manejo de objetos Intention
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from app.services.agent.intentions import Intention, INTENTIONS # Importar Intention e INTENTIONS

# Configurar logging
logger = logging.getLogger(__name__)

# Constantes de configuración
SESSION_DIR = "session_data"  # Directorio para archivos de sesión
SESSION_FILE_EXTENSION = ".json"  # Extensión de archivos de sesión
INDENT_SPACES = 2  # Espacios para formato JSON

# Asegurar existencia del directorio de sesiones
os.makedirs(SESSION_DIR, exist_ok=True)

class SessionManager:
    """
    Gestor de estados de sesión para el Agente IA.
    
    Esta clase maneja:
    - Persistencia de estados de conversación
    - Serialización de objetos complejos (como Intention)
    - Reconstrucción de estados desde archivos
    - Manejo de errores en operaciones de I/O
    
    La estructura del estado incluye:
        - pending_action: Acción pendiente (Intention)
        - pending_data: Datos asociados a la acción
        - current_purpose: Propósito actual de la conversación
    
    Ejemplo de uso:
        >>> manager = SessionManager()
        >>> state = {"pending_action": some_intention, "pending_data": {}}
        >>> manager.save_session("user123", state)
        >>> loaded_state = manager.load_session("user123")
    """
    def save_session(self, session_id: str, state: Dict[str, Any]) -> None:
        """
        Persiste el estado de una sesión en archivo JSON.
        
        Este método:
        1. Serializa objetos complejos (especialmente Intention)
        2. Convierte enumeraciones a sus valores string
        3. Guarda el estado en un archivo JSON con formato legible
        
        Args:
            session_id (str): Identificador único de la sesión
            state (Dict[str, Any]): Estado a persistir, que puede contener:
                - pending_action (Optional[Intention]): Acción pendiente
                - pending_data (Optional[Dict]): Datos de la acción
                - current_purpose (Optional[str]): Propósito actual
        
        Raises:
            IOError: Si hay problemas escribiendo el archivo
            Exception: Para otros errores de serialización
        
        Ejemplo:
            >>> state = {
            ...     "pending_action": Intention(...),
            ...     "pending_data": {"cliente": {"id": 1}},
            ...     "current_purpose": "consultar cliente"
            ... }
            >>> manager.save_session("user123", state)
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("session_id debe ser un string no vacío")
        if not isinstance(state, dict):
            raise ValueError("state debe ser un diccionario")

        try:
            file_path = os.path.join(SESSION_DIR, f"{session_id}.json")
            serializable_state = {}

            # Serializar pending_action si es un objeto Intention
            pending_action = state.get("pending_action")
            if isinstance(pending_action, Intention):
                serializable_state["pending_action"] = {
                    "type": pending_action.type.value, # Usar .value para Enums
                    "entities": [e.value for e in pending_action.entities], # Usar .value
                    "action": pending_action.action.value, # Usar .value
                    # No es necesario guardar fields/template aquí si se pueden buscar
                }
            elif isinstance(pending_action, dict): # Si ya es un dict (e.g., desde carga fallida)
                 serializable_state["pending_action"] = pending_action
            else:
                serializable_state["pending_action"] = None

            # Copiar otros datos directamente (asumiendo que son serializables)
            serializable_state["pending_data"] = state.get("pending_data")
            serializable_state["current_purpose"] = state.get("current_purpose")

            with open(file_path, 'w') as f:
                json.dump(serializable_state, f, indent=2) # Usar indent para legibilidad
            logger.info(f"Estado guardado para sesión {session_id}")

        except Exception as e:
            logger.error(f"Error al guardar el estado de la sesión {session_id}: {str(e)}")

    def load_session(self, session_id: str) -> Dict[str, Any]:
        """
        Recupera y reconstruye el estado de una sesión desde archivo.
        
        Este método:
        1. Lee el archivo JSON de la sesión
        2. Reconstruye objetos complejos (Intention)
        3. Valida la integridad de los datos cargados
        
        Args:
            session_id (str): Identificador único de la sesión
        
        Returns:
            Dict[str, Any]: Estado reconstruido con la estructura:
                {
                    "pending_action": Optional[Intention],
                    "pending_data": Optional[Dict],
                    "current_purpose": Optional[str]
                }
                Retorna diccionario vacío si no existe la sesión o hay error.
        
        Notas:
            - Si la reconstrucción de Intention falla, se mantienen los datos crudos
            - Los errores son manejados silenciosamente (logging + retorno vacío)
        
        Ejemplo:
            >>> state = manager.load_session("user123")
            >>> if state.get("pending_action"):
            ...     # Procesar acción pendiente
        """
        if not isinstance(session_id, str) or not session_id.strip():
            logger.error("ID de sesión inválido")
            return {}

        try:
            file_path = os.path.join(SESSION_DIR, f"{session_id}.json")
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                logger.info(f"Estado bruto cargado para sesión {session_id}")

                # Reconstruir objeto Intention si existe en el estado cargado
                if data.get("pending_action"):
                    reconstructed_intention = self.reconstruct_intention(data["pending_action"])
                    if reconstructed_intention:
                        data["pending_action"] = reconstructed_intention
                        logger.info(f"Intención reconstruida para sesión {session_id}")
                    else:
                        logger.warning(f"No se pudo reconstruir la intención para {session_id}, usando datos brutos.")
                
                logger.info(f"Estado completo cargado y procesado para sesión {session_id}")
                return data
            else:
                 logger.info(f"No se encontró archivo de sesión para {session_id}")

        except json.JSONDecodeError as e:
             logger.error(f"Error al decodificar JSON para sesión {session_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Error general al cargar el estado de la sesión {session_id}: {str(e)}")

        return {} # Devuelve diccionario vacío en caso de error o si no existe

    def reconstruct_intention(self, intention_data: Dict[str, Any]) -> Optional[Intention]:
        """
        Reconstruye un objeto Intention desde datos serializados.
        
        Este método:
        1. Valida los datos de entrada
        2. Busca una coincidencia en el catálogo INTENTIONS
        3. Reconstruye la intención si encuentra coincidencia
        
        Args:
            intention_data (Dict[str, Any]): Datos serializados con la estructura:
                {
                    "type": str,      # Tipo de intención
                    "action": str,    # Acción a realizar
                    "entities": List[str]  # Entidades involucradas
                }
        
        Returns:
            Optional[Intention]: Objeto Intention reconstruido, o None si:
                - Los datos de entrada son inválidos
                - Faltan campos requeridos
                - No se encuentra coincidencia en el catálogo
        
        Notas:
            - La comparación se realiza usando valores de enumeración
            - El orden de las entidades no importa en la comparación
            - Se usa el catálogo INTENTIONS como fuente de verdad
        """
        if not isinstance(intention_data, dict):
             logger.warning("Intentando reconstruir intención desde datos no válidos.")
             return None
             
        type_val = intention_data.get("type")
        action_val = intention_data.get("action")
        entities_val = intention_data.get("entities")

        if not all([type_val, action_val, entities_val]):
             logger.warning("Faltan datos clave para reconstruir la intención.")
             return None

        try:
            # Buscar la intención correspondiente en el catálogo INTENTIONS
            for intention_key, intention_obj in INTENTIONS.items():
                # Comparar usando .value para Enums y convirtiendo listas a sets para comparar sin orden
                if (intention_obj.type.value == type_val and
                    intention_obj.action.value == action_val and
                    set(e.value for e in intention_obj.entities) == set(entities_val)):
                    logger.debug(f"Intención encontrada para reconstrucción: {intention_key}")
                    return intention_obj # Devolver la instancia completa del catálogo
        except Exception as e:
            logger.error(f"Error durante la búsqueda de intención para reconstrucción: {str(e)}")

        logger.warning(f"No se encontró ninguna intención coincidente en el catálogo para: {intention_data}")
        return None # No se encontró coincidencia 