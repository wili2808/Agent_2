"""
Esquemas de validación para mensajes del Agente IA.

Este módulo define los modelos Pydantic para:
1. Validación de mensajes entrantes (requests)
2. Estructuración de respuestas del agente (responses)

Los esquemas garantizan:
- Tipado fuerte de datos
- Validación automática de campos
- Serialización/deserialización consistente

Clases:
    MessageRequest: Esquema para mensajes entrantes
    MessageResponse: Esquema para respuestas del agente

Uso típico:
    >>> request = MessageRequest(message="listar clientes", user_id="user123")
    >>> response = MessageResponse(
    ...     status="success",
    ...     data={"clientes": [...]},
    ...     message="Operación exitosa"
    ... )
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, Literal

class MessageRequest(BaseModel):
    """
    Esquema para validación de mensajes entrantes al agente.
    
    Este modelo valida y estructura los mensajes que los usuarios
    envían al agente para su procesamiento. Garantiza que los
    mensajes contengan toda la información necesaria.
    
    Attributes:
        message (str): Texto del mensaje del usuario
            Debe ser una cadena no vacía que contenga la instrucción
            o consulta para el agente.
            
        user_id (Optional[str]): Identificador único del usuario
            Permite mantener el contexto de la conversación y
            estado entre mensajes del mismo usuario.
    
    Ejemplo:
        >>> # Mensaje simple sin ID de usuario
        >>> msg1 = MessageRequest(message="listar clientes")
        >>> 
        >>> # Mensaje con ID de usuario para seguimiento
        >>> msg2 = MessageRequest(
        ...     message="crear cliente",
        ...     user_id="user123"
        ... )
    
    Raises:
        ValidationError: Si el mensaje está vacío o los tipos no coinciden
    """
    message: str = Field(
        ...,  # Campo requerido
        min_length=1,
        description="Mensaje o instrucción del usuario para el agente"
    )
    user_id: Optional[str] = Field(
        None,
        description="Identificador único del usuario para mantener contexto"
    )
    
    @validator("message")
    def validate_message_content(cls, v: str) -> str:
        """Valida que el mensaje no esté vacío o solo contenga espacios"""
        if not v.strip():
            raise ValueError("El mensaje no puede estar vacío")
        return v.strip()
    
    class Config:
        """Configuración del modelo Pydantic"""
        json_schema_extra = {
            "example": {
                "message": "listar todos los clientes",
                "user_id": "user123"
            }
        }

class MessageResponse(BaseModel):
    """
    Esquema para estructurar las respuestas del agente.
    
    Este modelo define el formato estándar para todas las respuestas
    del agente, incluyendo tanto casos de éxito como de error.
    
    Attributes:
        status (Literal["success", "error", "confirmation_required"]):
            Estado de la operación:
            - "success": Operación completada exitosamente
            - "error": Ocurrió un error durante el procesamiento
            - "confirmation_required": Se requiere confirmación del usuario
            
        data (Optional[Dict[str, Any]]): Datos de la respuesta
            Contiene la información solicitada en caso de éxito.
            Puede incluir:
            - Resultados de consultas
            - Datos de entidades creadas/actualizadas
            - Información de confirmación pendiente
            
        message (Optional[str]): Mensaje descriptivo
            - En caso de éxito: Descripción de la operación realizada
            - En caso de error: Descripción del error ocurrido
            - En caso de confirmación: Instrucciones para el usuario
    
    Ejemplo:
        >>> # Respuesta exitosa
        >>> response1 = MessageResponse(
        ...     status="success",
        ...     data={"clientes": [{"id": 1, "nombre": "Juan"}]},
        ...     message="Clientes listados exitosamente"
        ... )
        >>> 
        >>> # Respuesta de error
        >>> response2 = MessageResponse(
        ...     status="error",
        ...     message="Cliente no encontrado"
        ... )
        >>> 
        >>> # Respuesta que requiere confirmación
        >>> response3 = MessageResponse(
        ...     status="confirmation_required",
        ...     data={"action": "delete_cliente", "id": 1},
        ...     message="¿Confirma la eliminación del cliente?"
        ... )
    """
    status: Literal["success", "error", "confirmation_required"] = Field(
        ...,
        description="Estado de la operación realizada"
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Datos de la respuesta en caso de éxito"
    )
    message: Optional[str] = Field(
        None,
        description="Mensaje descriptivo de la operación o error"
    )
    
    @validator("data", always=True)
    def validate_data_for_success(cls, v: Optional[Dict[str, Any]], values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Valida que haya datos cuando el status es success"""
        if values.get("status") == "success" and not v:
            raise ValueError("Se requieren datos para respuestas exitosas")
        return v
    
    @validator("message", always=True)
    def validate_message_presence(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Valida que haya mensaje cuando el status es error"""
        if values.get("status") == "error" and not v:
            raise ValueError("Se requiere mensaje de error para respuestas de error")
        return v
    
    class Config:
        """Configuración del modelo Pydantic"""
        json_schema_extra = {
            "examples": [
                {
                    "status": "success",
                    "data": {"clientes": [{"id": 1, "nombre": "Juan"}]},
                    "message": "Operación completada exitosamente"
                },
                {
                    "status": "error",
                    "message": "Error al procesar la solicitud"
                },
                {
                    "status": "confirmation_required",
                    "data": {"action": "delete", "entity": "cliente", "id": 1},
                    "message": "¿Desea proceder con la eliminación?"
                }
            ]
        } 