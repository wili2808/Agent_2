"""
Sistema de reconocimiento y gestión de intenciones del Agente IA.

Este módulo implementa:
1. Sistema de clasificación de intenciones:
   - Tipos de intenciones (consulta, registro, etc.)
   - Entidades del negocio (cliente, producto, etc.)
   - Acciones posibles sobre las entidades

2. Catálogo de intenciones predefinidas:
   - Definición de campos requeridos y opcionales
   - Plantillas de respuesta
   - Mapeo de patrones de reconocimiento

3. Motor de reconocimiento de intenciones:
   - Normalización de texto
   - Coincidencia de patrones
   - Fallback inteligente basado en palabras clave

Clases principales:
    IntentionType: Enumeración de tipos de intención
    EntityType: Enumeración de entidades del negocio
    ActionType: Enumeración de acciones posibles
    Intention: Modelo de datos para intenciones

Constantes:
    INTENTIONS: Catálogo de intenciones predefinidas

Funciones:
    match_intention: Función principal de reconocimiento de intenciones
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel
import unicodedata

# Configuración de normalización de texto
NORMALIZE_ACCENTS = True
NORMALIZE_CASE = True
STRIP_SPACES = True

# Listas de palabras clave para confirmación/negación
CONFIRMATION_KEYWORDS = [
    "sí", "si", "s", "yes", "confirmo", "confirmar", 
    "ok", "dale", "adelante"
]

NEGATION_KEYWORDS = [
    "no", "n", "cancel", "cancelar", "cancelado", 
    "nope", "negativo"
]

# Palabras clave para fallback de intenciones
ENTITY_KEYWORDS = {
    "cliente": ["cliente", "clientes", "usuario", "usuarios"],
    "producto": ["producto", "productos", "artículo", "artículos"],
    "venta": ["venta", "ventas", "pedido", "pedidos"],
    "factura": ["factura", "facturas", "comprobante"]
}

class IntentionType(str, Enum):
    """
    Clasificación de alto nivel para las intenciones del usuario.
    
    Esta enumeración define las categorías principales de intenciones que el
    agente puede reconocer y procesar. Cada tipo representa un propósito
    general distinto en la interacción con el sistema.
    
    Valores:
        CONSULTA: Solicitudes de información o lectura de datos
            Ejemplo: "mostrar todos los clientes", "ver productos"
            
        REGISTRO: Creación de nuevos registros
            Ejemplo: "crear nuevo cliente", "agregar producto"
            
        MODIFICACION: Actualización de registros existentes
            Ejemplo: "actualizar datos del cliente", "modificar precio"
            
        ELIMINACION: Eliminación de registros
            Ejemplo: "eliminar cliente", "borrar producto"
            
        VENTA: Operaciones relacionadas con ventas
            Ejemplo: "registrar venta", "procesar pedido"
            
        FACTURACION: Gestión de facturación
            Ejemplo: "generar factura", "emitir comprobante"
            
        INVENTARIO: Control de inventario
            Ejemplo: "actualizar stock", "ajustar inventario"
            
        CONVERSACION: Interacción conversacional general
            Ejemplo: "hola", "cómo estás", "qué puedes hacer"
    """
    CONSULTA = "consulta"         # Consultar información
    REGISTRO = "registro"         # Registrar nueva información
    MODIFICACION = "modificacion" # Modificar información existente
    ELIMINACION = "eliminacion"   # Eliminar información
    VENTA = "venta"               # Operaciones de venta
    FACTURACION = "facturacion"   # Operaciones de facturación
    INVENTARIO = "inventario"     # Gestión de inventario
    CONVERSACION = "conversacion" # Conversación general

class EntityType(str, Enum):
    """
    Entidades del dominio sobre las que el agente puede operar.
    
    Esta enumeración define los objetos principales del modelo de negocio
    que pueden ser afectados por las acciones del agente. Cada entidad
    representa una tabla o concepto en la base de datos.
    
    Valores:
        CLIENTE: Representa a los clientes del negocio
            Campos principales: id, nombre, email, telefono, direccion
            
        PRODUCTO: Representa los productos o servicios
            Campos principales: id, nombre, precio, stock
            
        VENTA: Representa una transacción de venta
            Campos principales: id, fecha, cliente_id, total
            
        FACTURA: Representa un documento de facturación
            Campos principales: id, venta_id, fecha, monto
            
        DETALLE_VENTA: Representa los items de una venta
            Campos principales: id, venta_id, producto_id, cantidad, precio
        
        ASISTENTE: Representa al asistente virtual
            Se utiliza para conversaciones generales no relacionadas con CRUD
    
    Notas:
        - Cada entidad debe corresponder a un modelo en la base de datos
        - Las operaciones CRUD están disponibles para todas las entidades
        - Algunas entidades pueden tener relaciones específicas entre sí
    """
    CLIENTE = "cliente"                 # Entidad cliente
    PRODUCTO = "producto"               # Entidad producto
    VENTA = "venta"                     # Entidad venta
    FACTURA = "factura"                 # Entidad factura
    DETALLE_VENTA = "detalle_venta"     # Entidad detalle de venta
    ASISTENTE = "asistente"             # Entidad asistente para conversaciones

class ActionType(str, Enum):
    """
    Tipos de acciones que el agente puede realizar.
    
    Valores:
        LISTAR: Obtener todos los registros de una entidad
        BUSCAR: Encontrar registros específicos según criterios
        CREAR: Registrar nueva información en la base de datos
        ACTUALIZAR: Modificar registros existentes
        ELIMINAR: Remover registros de la base de datos
        PROCESAR_VENTA: Gestionar una nueva transacción de venta
        GENERAR_FACTURA: Crear documento de facturación
        ACTUALIZAR_STOCK: Modificar niveles de inventario
        CONVERSAR: Mantener una conversación general no relacionada con CRUD
    """
    LISTAR = "listar"
    BUSCAR = "buscar"
    CREAR = "crear"
    ACTUALIZAR = "actualizar"
    ELIMINAR = "eliminar"
    PROCESAR_VENTA = "procesar_venta"
    GENERAR_FACTURA = "generar_factura"
    ACTUALIZAR_STOCK = "actualizar_stock"
    CONVERSAR = "conversar"  # Acción para conversaciones generales

class Intention(BaseModel):
    """
    Modelo que representa una intención específica del usuario.
    
    Esta clase define la estructura completa de una intención, incluyendo
    su tipo, las entidades involucradas, la acción a realizar y los
    campos necesarios para ejecutar la acción.
    
    Attributes:
        type (IntentionType): Categoría general de la intención
            Ejemplo: CONSULTA, REGISTRO, etc.
            
        entities (List[EntityType]): Lista de entidades involucradas
            Ejemplo: [EntityType.CLIENTE] para operaciones sobre clientes
            
        action (ActionType): Acción específica a realizar
            Ejemplo: LISTAR, CREAR, ACTUALIZAR, etc.
            
        required_fields (Dict[EntityType, List[str]]): Campos obligatorios
            Mapeo de entidad a lista de campos requeridos
            Ejemplo: {EntityType.CLIENTE: ["nombre", "email"]}
            
        optional_fields (Dict[EntityType, List[str]]): Campos opcionales
            Mapeo de entidad a lista de campos adicionales
            Ejemplo: {EntityType.CLIENTE: ["telefono", "direccion"]}
            
        response_template (str): Plantilla para la respuesta
            Mensaje base para comunicar el resultado de la acción
    
    Ejemplo:
        >>> intention = Intention(
        ...     type=IntentionType.REGISTRO,
        ...     entities=[EntityType.CLIENTE],
        ...     action=ActionType.CREAR,
        ...     required_fields={EntityType.CLIENTE: ["nombre", "email"]},
        ...     optional_fields={EntityType.CLIENTE: ["telefono"]},
        ...     response_template="Cliente creado exitosamente."
        ... )
    """
    type: IntentionType
    entities: List[EntityType]
    action: ActionType
    required_fields: Dict[EntityType, List[str]]
    optional_fields: Dict[EntityType, List[str]]
    response_template: str

# Definición de intenciones disponibles en el sistema
# Cada intención mapea un propósito específico a un conjunto de entidades y acciones
INTENTIONS = {
    # === Operaciones de Cliente ===
    
    "listar_clientes": Intention(
        type=IntentionType.CONSULTA,
        entities=[EntityType.CLIENTE],
        action=ActionType.LISTAR,
        required_fields={},  
        optional_fields={},  
        response_template="Listando todos los clientes registrados."
    ),
    
    # Intención para buscar un cliente específico
    "buscar_cliente": Intention(
        type=IntentionType.CONSULTA,
        entities=[EntityType.CLIENTE],
        action=ActionType.BUSCAR,
        required_fields={EntityType.CLIENTE: ["nombre", "email"]},  # Requiere al menos nombre o email
        optional_fields={},
        response_template="Buscando cliente con los criterios proporcionados."
    ),
    
    # Intención para crear un nuevo cliente
    "crear_cliente": Intention(
        type=IntentionType.REGISTRO,
        entities=[EntityType.CLIENTE],
        action=ActionType.CREAR,
        required_fields={EntityType.CLIENTE: ["nombre", "email"]},  # Campos obligatorios
        optional_fields={EntityType.CLIENTE: ["telefono", "direccion"]},  # Campos opcionales
        response_template="Creando nuevo cliente con los datos proporcionados."
    ),
    
    # Intención para listar todos los productos
    "listar_productos": Intention(
        type=IntentionType.CONSULTA,
        entities=[EntityType.PRODUCTO],
        action=ActionType.LISTAR,
        required_fields={},
        optional_fields={},
        response_template="Listando todos los productos disponibles."
    ),
    
    # Intención para crear una nueva venta
    "crear_venta": Intention(
        type=IntentionType.VENTA,
        entities=[EntityType.VENTA, EntityType.CLIENTE, EntityType.PRODUCTO],
        action=ActionType.PROCESAR_VENTA,
        required_fields={
            EntityType.CLIENTE: ["id"],
            EntityType.PRODUCTO: ["id", "cantidad"]
        },
        optional_fields={},
        response_template="Procesando nueva venta."
    ),
    
    # Intención para generar una factura
    "generar_factura": Intention(
        type=IntentionType.FACTURACION,
        entities=[EntityType.FACTURA, EntityType.VENTA],
        action=ActionType.GENERAR_FACTURA,
        required_fields={EntityType.VENTA: ["id"]},
        optional_fields={},
        response_template="Generando factura para la venta especificada."
    ),
    
    # Intención para conversación general
    "conversacion_general": Intention(
        type=IntentionType.CONVERSACION,
        entities=[EntityType.ASISTENTE],
        action=ActionType.CONVERSAR,
        required_fields={},
        optional_fields={},
        response_template="Conversación general con el asistente."
    )
}

# Patrones de reconocimiento
patterns = {
    "listar_clientes": [
        # Patrones directos
        "listar clientes", "mostrar clientes", "ver clientes",
        # Patrones con variaciones
        "dame los clientes", "quiero ver los clientes",
        # Patrones con sinónimos
        "clientes registrados", "todos los clientes",
        # Patrones de consulta
        "consultar clientes", "buscar todos los clientes",
        # Variaciones singulares
        "listar cliente", "ver cliente"
    ],
    "buscar_cliente": [
        "buscar cliente", "encontrar cliente", "cliente específico", "datos del cliente",
        "información de cliente", "buscar un cliente", "cliente por nombre", "cliente por email",
        "buscar un cliente por", "información de un cliente", "datos de cliente", "cliente con nombre"
    ],
    "crear_cliente": [
        "crear cliente", "nuevo cliente", "añadir cliente", "registrar cliente",
        "dar de alta cliente", "agregar cliente", "insertar cliente", "cliente nuevo",
        "crear un cliente", "registrar un nuevo cliente", "añadir un cliente nuevo"
    ],
    "listar_productos": [
        "listar productos", "mostrar productos", "ver productos", "dame los productos",
        "quiero ver los productos", "productos disponibles", "todos los productos",
        "lista de productos", "catálogo de productos", "inventario", "qué productos hay"
    ],
    "crear_venta": [
        "crear venta", "nueva venta", "registrar venta", "hacer una venta",
        "procesar venta", "vender producto", "registrar una venta", "añadir venta",
        "generar venta", "realizar venta", "vender", "procesar una venta"
    ],
    "generar_factura": [
        "generar factura", "crear factura", "nueva factura", "emitir factura",
        "facturar venta", "factura para venta", "facturación", "generar la factura",
        "necesito una factura", "crear una factura", "emitir una factura"
    ],
    "conversacion_general": [
        # Saludos
        "hola", "buenos días", "buenas tardes", "buenas noches", "saludos", 
        "qué tal", "cómo estás", "cómo va", "qué hay",
        
        # Ayuda y preguntas sobre funcionalidades
        "ayuda", "ayúdame", "qué puedes hacer", "cómo funciona", "cuáles son tus funciones",
        "qué sabes hacer", "cómo te uso", "instrucciones", "manual", "guía",
        
        # Identidad del asistente
        "quién eres", "cómo te llamas", "tu nombre", "qué eres", "qué tipo de asistente",
        
        # Agradecimientos
        "gracias", "muchas gracias", "te agradezco", "excelente", "genial",
        
        # Despedidas
        "adiós", "hasta luego", "nos vemos", "chao", "bye", "hasta pronto"
    ]
}

def match_intention(message: str) -> Optional[Intention]:
    """
    Analiza el mensaje del usuario y determina la intención correspondiente.
    
    Proceso de análisis:
    1. Verifica si es un mensaje de confirmación/negación
    2. Normaliza el texto (elimina acentos, convierte a minúsculas)
    3. Busca coincidencias en patrones predefinidos
    4. Realiza búsqueda por palabras clave si no hay coincidencia exacta
    
    Args:
        message (str): Texto del mensaje del usuario
        
    Returns:
        Optional[Intention]: Intención identificada o None si es confirmación/negación
        
    Notas:
        - Los patrones están organizados por tipo de intención
        - Se incluye un fallback a intenciones comunes si no hay coincidencia exacta
        - Por defecto retorna la intención de listar clientes si no hay coincidencia
    """
    # Verificar si es un mensaje de confirmación
    confirmation_messages = ["sí", "si", "s", "yes", "confirmo", "confirmar", "ok", "dale", "adelante"]
    negation_messages = ["no", "n", "cancel", "cancelar", "cancelado", "nope", "negativo"]
    
    # Normalizar el mensaje eliminando acentos y convirtiendo a minúscula
    def normalize_text(text):
        # Normalizar a NFD y eliminar diacríticos (acentos)
        text = unicodedata.normalize('NFD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        # Convertir a minúscula y eliminar espacios extras
        return text.lower().strip()
    
    normalized_message = normalize_text(message)
    
    # Si es una confirmación o negación, devolvemos None para manejarlo en el proceso principal
    if normalized_message in confirmation_messages or normalized_message in negation_messages:
        print(f"Detectada confirmación/negación: '{message}' -> '{normalized_message}'")
        return None
    
    # Verificar coincidencias en patrones
    for intention_key, pattern_list in patterns.items():
        for pattern in pattern_list:
            if pattern in normalized_message:
                print(f"Coincidencia encontrada para '{intention_key}' con patrón '{pattern}'")
                return INTENTIONS.get(intention_key)
    
    # Comprobar si parece una pregunta (comienza con qué, cómo, dónde, etc.)
    question_starters = ["que ", "qué ", "como ", "cómo ", "donde ", "dónde ", "cuando ", "cuándo ", 
                         "por qué ", "porque ", "cual ", "cuál ", "quien ", "quién "]
    if any(normalized_message.startswith(starter) for starter in question_starters):
        print(f"Detectada pregunta conversacional: '{message}'")
        return INTENTIONS.get("conversacion_general")
    
    # Comprobar si es un mensaje corto (menos de 4 palabras) y no contiene palabras clave de negocio
    business_keywords = (ENTITY_KEYWORDS["cliente"] + ENTITY_KEYWORDS["producto"] + 
                         ENTITY_KEYWORDS["venta"] + ENTITY_KEYWORDS["factura"])
    if len(normalized_message.split()) < 4 and not any(keyword in normalized_message for keyword in business_keywords):
        print(f"Mensaje corto sin palabras clave de negocio: '{message}'")
        return INTENTIONS.get("conversacion_general")
    
    # Si no hay coincidencia específica pero el mensaje menciona clientes
    if any(word in normalized_message for word in ["cliente", "clientes"]):
        return INTENTIONS.get("listar_clientes")
    
    # Si no hay coincidencia específica pero el mensaje menciona productos
    if any(word in normalized_message for word in ["producto", "productos", "inventario"]):
        return INTENTIONS.get("listar_productos")
    
    # Si no hay coincidencia específica pero el mensaje menciona ventas
    if any(word in normalized_message for word in ["venta", "ventas", "vender"]):
        return INTENTIONS.get("crear_venta")
    
    # Si no hay coincidencia específica pero el mensaje menciona facturas
    if any(word in normalized_message for word in ["factura", "facturas", "facturación"]):
        return INTENTIONS.get("generar_factura")
        
    # Por defecto, si no se encuentra una intención específica, considérala conversacional
    print(f"No se encontró coincidencia específica para el mensaje: '{message}', tratando como conversación general")
    return INTENTIONS.get("conversacion_general") 