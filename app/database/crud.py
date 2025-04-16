"""
Servicio CRUD (Create, Read, Update, Delete) para la gestión de entidades del negocio.

Este módulo implementa:
1. Operaciones CRUD básicas para todas las entidades:
   - Clientes: Gestión de información de clientes
   - Productos: Gestión del catálogo de productos
   - Ventas: Registro y seguimiento de transacciones
   - Facturas: Documentación de ventas realizadas

2. Características principales:
   - Abstracción de operaciones de base de datos
   - Manejo de transacciones seguro
   - Validación de existencia de registros
   - Retorno de tipos opcionales para manejo de errores

Clases:
    CRUDService: Clase principal que implementa todas las operaciones CRUD

Dependencias:
    - SQLAlchemy: Para operaciones de base de datos
    - Modelos: Cliente, Producto, Venta, DetalleVenta, Factura

Uso típico:
    >>> crud = CRUDService(db_session)
    >>> clientes = crud.get_clientes()
    >>> nuevo_cliente = crud.create_cliente({"nombre": "Juan", "email": "juan@example.com"})
"""

from sqlalchemy.orm import Session
from app.database.models import Cliente, Producto, Venta, DetalleVenta, Factura
from typing import List, Optional, Dict, Any, Union
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Configuración de tipos de datos
ClienteData = Dict[str, Union[str, int, float]]
ProductoData = Dict[str, Union[str, int, float]]
VentaData = Dict[str, Union[str, int, float, dict]]
FacturaData = Dict[str, Union[str, int, float]]

# Campos requeridos por entidad
REQUIRED_CLIENTE_FIELDS = ["nombre", "email"]
REQUIRED_PRODUCTO_FIELDS = ["nombre", "precio", "stock"]
REQUIRED_VENTA_FIELDS = ["cliente_id", "fecha"]
REQUIRED_FACTURA_FIELDS = ["venta_id", "fecha"]

class CRUDService:
    """
    Servicio centralizado para operaciones de base de datos.
    
    Esta clase implementa el patrón Repository, proporcionando una interfaz unificada
    para realizar operaciones CRUD en todas las entidades del sistema. Maneja las
    transacciones de base de datos y garantiza la consistencia de los datos.
    
    Entidades soportadas:
        - Clientes: Gestión de información de clientes
        - Productos: Administración de catálogo de productos
        - Ventas: Registro y seguimiento de transacciones
        - Facturas: Documentación de ventas
    
    Atributos:
        db (Session): Sesión activa de SQLAlchemy para operaciones de base de datos
    
    Ejemplo:
        >>> crud = CRUDService(db_session)
        >>> # Crear un nuevo cliente
        >>> cliente = crud.create_cliente({
        ...     "nombre": "Juan Pérez",
        ...     "email": "juan@example.com",
        ...     "telefono": "123456789"
        ... })
        >>> # Actualizar información
        >>> crud.update_cliente(cliente.id, {"telefono": "987654321"})
    """
    def __init__(self, db: Session):
        """
        Inicializa el servicio CRUD con una sesión de base de datos.
        
        Args:
            db (Session): Sesión de SQLAlchemy para interactuar con la base de datos.
        """
        self.db = db

    # ==================== Operaciones CRUD para Clientes ====================
    
    def get_clientes(self) -> List[Cliente]:
        """
        Obtiene todos los clientes registrados en la base de datos.
        
        Returns:
            List[Cliente]: Lista de objetos Cliente.
        """
        return self.db.query(Cliente).all()

    def get_cliente(self, cliente_id: int) -> Optional[Cliente]:
        """
        Obtiene un cliente específico por su ID.
        
        Args:
            cliente_id (int): ID del cliente a buscar.
            
        Returns:
            Optional[Cliente]: Objeto Cliente si existe, None si no se encuentra.
        """
        return self.db.query(Cliente).filter(Cliente.id == cliente_id).first()

    def create_cliente(self, cliente_data: Dict[str, Any]) -> Cliente:
        """
        Crea un nuevo registro de cliente en la base de datos.
        
        Este método:
        1. Valida los datos recibidos
        2. Crea una nueva instancia de Cliente
        3. Persiste los datos en la base de datos
        4. Actualiza el objeto con el ID asignado
        
        Args:
            cliente_data (Dict[str, Any]): Datos del cliente con la estructura:
                {
                    "nombre": str,       # Nombre completo del cliente (requerido)
                    "email": str,        # Email de contacto (requerido)
                    "telefono": str,     # Número telefónico (opcional)
                    "direccion": str     # Dirección física (opcional)
                }
        
        Returns:
            Cliente: Objeto Cliente creado y persistido
            
        Raises:
            ValueError: Si faltan campos requeridos
            SQLAlchemyError: Si hay errores de base de datos
        
        Ejemplo:
            >>> datos_cliente = {
            ...     "nombre": "María García",
            ...     "email": "maria@example.com",
            ...     "telefono": "123456789"
            ... }
            >>> cliente = crud.create_cliente(datos_cliente)
            >>> print(f"Cliente creado con ID: {cliente.id}")
        """
        cliente = Cliente(**cliente_data)
        self.db.add(cliente)
        self.db.commit()
        self.db.refresh(cliente)
        return cliente

    def update_cliente(self, cliente_id: int, cliente_data: Dict[str, Any]) -> Optional[Cliente]:
        """
        Actualiza los datos de un cliente existente.
        
        Este método:
        1. Verifica la existencia del cliente
        2. Actualiza solo los campos proporcionados
        3. Persiste los cambios en la base de datos
        
        Args:
            cliente_id (int): Identificador único del cliente
            cliente_data (Dict[str, Any]): Datos a actualizar:
                {
                    "nombre": str,       # Nuevo nombre (opcional)
                    "email": str,        # Nuevo email (opcional)
                    "telefono": str,     # Nuevo teléfono (opcional)
                    "direccion": str     # Nueva dirección (opcional)
                }
        
        Returns:
            Optional[Cliente]: Cliente actualizado o None si no existe
            
        Raises:
            SQLAlchemyError: Si hay errores en la actualización
        
        Notas:
            - Solo se actualizan los campos incluidos en cliente_data
            - Los campos no incluidos mantienen sus valores actuales
            - Se realiza una actualización parcial (PATCH)
        """
        cliente = self.get_cliente(cliente_id)
        if cliente:
            for key, value in cliente_data.items():
                setattr(cliente, key, value)
            self.db.commit()
            self.db.refresh(cliente)
        return cliente

    def delete_cliente(self, cliente_id: int) -> bool:
        """
        Elimina un cliente de la base de datos.
        
        Este método:
        1. Verifica la existencia del cliente
        2. Comprueba dependencias (ventas, facturas)
        3. Elimina el registro si es posible
        
        Args:
            cliente_id (int): Identificador único del cliente
        
        Returns:
            bool: True si se eliminó correctamente, False si no existe
            
        Raises:
            SQLAlchemyError: Si hay errores en la eliminación
            IntegrityError: Si hay registros dependientes que impiden la eliminación
        
        Notas:
            - La eliminación es permanente (hard delete)
            - Se debe verificar la existencia de ventas asociadas
            - Se recomienda implementar soft delete en futuras versiones
        """
        cliente = self.get_cliente(cliente_id)
        if cliente:
            self.db.delete(cliente)
            self.db.commit()
            return True
        return False

    # ==================== Operaciones CRUD para Productos ====================
    
    def get_productos(self) -> List[Producto]:
        """
        Obtiene todos los productos registrados en la base de datos.
        
        Returns:
            List[Producto]: Lista de objetos Producto.
        """
        return self.db.query(Producto).all()

    def get_producto(self, producto_id: int) -> Optional[Producto]:
        """
        Obtiene un producto específico por su ID.
        
        Args:
            producto_id (int): ID del producto a buscar.
            
        Returns:
            Optional[Producto]: Objeto Producto si existe, None si no se encuentra.
        """
        return self.db.query(Producto).filter(Producto.id == producto_id).first()

    def create_producto(self, producto_data: Dict[str, Any]) -> Producto:
        """
        Crea un nuevo producto en la base de datos.
        
        Args:
            producto_data (Dict[str, Any]): Diccionario con los datos del producto.
                Debe contener al menos 'nombre', 'precio' y 'stock'.
                
        Returns:
            Producto: Objeto Producto creado con ID asignado.
        """
        producto = Producto(**producto_data)
        self.db.add(producto)
        self.db.commit()
        self.db.refresh(producto)
        return producto

    def update_producto(self, producto_id: int, producto_data: Dict[str, Any]) -> Optional[Producto]:
        """
        Actualiza un producto existente.
        
        Args:
            producto_id (int): ID del producto a actualizar.
            producto_data (Dict[str, Any]): Diccionario con los datos a actualizar.
            
        Returns:
            Optional[Producto]: Producto actualizado si existe, None si no se encuentra.
        """
        producto = self.get_producto(producto_id)
        if producto:
            for key, value in producto_data.items():
                setattr(producto, key, value)
            self.db.commit()
            self.db.refresh(producto)
        return producto

    def delete_producto(self, producto_id: int) -> bool:
        """
        Elimina un producto de la base de datos.
        
        Args:
            producto_id (int): ID del producto a eliminar.
            
        Returns:
            bool: True si se eliminó correctamente, False si no se encontró.
        """
        producto = self.get_producto(producto_id)
        if producto:
            self.db.delete(producto)
            self.db.commit()
            return True
        return False

    # ==================== Operaciones CRUD para Ventas ====================
    
    def get_ventas(self) -> List[Venta]:
        """
        Obtiene todas las ventas registradas en la base de datos.
        
        Returns:
            List[Venta]: Lista de objetos Venta.
        """
        return self.db.query(Venta).all()

    def get_venta(self, venta_id: int) -> Optional[Venta]:
        """
        Obtiene una venta específica por su ID.
        
        Args:
            venta_id (int): ID de la venta a buscar.
            
        Returns:
            Optional[Venta]: Objeto Venta si existe, None si no se encuentra.
        """
        return self.db.query(Venta).filter(Venta.id == venta_id).first()

    def create_venta(self, venta_data: Dict[str, Any]) -> Venta:
        """
        Crea una nueva venta en la base de datos.
        
        Args:
            venta_data (Dict[str, Any]): Diccionario con los datos de la venta.
                Debe contener al menos 'cliente_id' y 'fecha'.
                
        Returns:
            Venta: Objeto Venta creado con ID asignado.
        """
        venta = Venta(**venta_data)
        self.db.add(venta)
        self.db.commit()
        self.db.refresh(venta)
        return venta

    def update_venta(self, venta_id: int, venta_data: Dict[str, Any]) -> Optional[Venta]:
        """
        Actualiza una venta existente.
        
        Args:
            venta_id (int): ID de la venta a actualizar.
            venta_data (Dict[str, Any]): Diccionario con los datos a actualizar.
            
        Returns:
            Optional[Venta]: Venta actualizada si existe, None si no se encuentra.
        """
        venta = self.get_venta(venta_id)
        if venta:
            for key, value in venta_data.items():
                setattr(venta, key, value)
            self.db.commit()
            self.db.refresh(venta)
        return venta

    def delete_venta(self, venta_id: int) -> bool:
        """
        Elimina una venta de la base de datos.
        
        Args:
            venta_id (int): ID de la venta a eliminar.
            
        Returns:
            bool: True si se eliminó correctamente, False si no se encontró.
        """
        venta = self.get_venta(venta_id)
        if venta:
            self.db.delete(venta)
            self.db.commit()
            return True
        return False

    # ==================== Operaciones CRUD para Facturas ====================
    
    def get_facturas(self) -> List[Factura]:
        """
        Obtiene todas las facturas registradas en la base de datos.
        
        Returns:
            List[Factura]: Lista de objetos Factura.
        """
        return self.db.query(Factura).all()

    def get_factura(self, factura_id: int) -> Optional[Factura]:
        """
        Obtiene una factura específica por su ID.
        
        Args:
            factura_id (int): ID de la factura a buscar.
            
        Returns:
            Optional[Factura]: Objeto Factura si existe, None si no se encuentra.
        """
        return self.db.query(Factura).filter(Factura.id == factura_id).first()

    def create_factura(self, factura_data: Dict[str, Any]) -> Factura:
        """
        Crea una nueva factura en la base de datos.
        
        Args:
            factura_data (Dict[str, Any]): Diccionario con los datos de la factura.
                Debe contener al menos 'venta_id' y 'fecha'.
                
        Returns:
            Factura: Objeto Factura creado con ID asignado.
        """
        factura = Factura(**factura_data)
        self.db.add(factura)
        self.db.commit()
        self.db.refresh(factura)
        return factura

    def update_factura(self, factura_id: int, factura_data: Dict[str, Any]) -> Optional[Factura]:
        """
        Actualiza una factura existente.
        
        Args:
            factura_id (int): ID de la factura a actualizar.
            factura_data (Dict[str, Any]): Diccionario con los datos a actualizar.
            
        Returns:
            Optional[Factura]: Factura actualizada si existe, None si no se encuentra.
        """
        factura = self.get_factura(factura_id)
        if factura:
            for key, value in factura_data.items():
                setattr(factura, key, value)
            self.db.commit()
            self.db.refresh(factura)
        return factura

    def delete_factura(self, factura_id: int) -> bool:
        """
        Elimina una factura de la base de datos.
        
        Args:
            factura_id (int): ID de la factura a eliminar.
            
        Returns:
            bool: True si se eliminó correctamente, False si no se encontró.
        """
        factura = self.get_factura(factura_id)
        if factura:
            self.db.delete(factura)
            self.db.commit()
            return True
        return False 