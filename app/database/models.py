"""
Módulo de modelos para la base de datos del sistema de gestión empresarial.

Este módulo define todas las entidades del modelo de datos utilizando SQLAlchemy ORM.
Incluye las clases para gestionar clientes, productos, ventas, detalles de venta y facturas,
así como sus relaciones entre sí.

Clases principales:
    - Cliente: Información de clientes registrados en el sistema.
    - Producto: Catálogo de productos disponibles para la venta.
    - Venta: Registro de transacciones de venta.
    - DetalleVenta: Productos incluidos en cada venta con sus cantidades y precios.
    - Factura: Documentos de facturación asociados a las ventas.

Todas las clases heredan de Base, que establece la conexión con SQLAlchemy.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Cliente(Base):
    """
    Modelo para la tabla de clientes.
    
    Almacena la información de los clientes registrados en el sistema.
    
    Attributes:
        id (int): Identificador único del cliente, clave primaria.
        nombre (str): Nombre completo del cliente. Campo obligatorio.
        email (str): Correo electrónico del cliente. Debe ser único.
        telefono (str): Número de teléfono del cliente.
        direccion (Text): Dirección física del cliente.
        fecha_registro (datetime): Fecha y hora de registro del cliente en el sistema.
        
    Relationships:
        ventas (Venta): Relación uno a muchos con la tabla de ventas.
                        Un cliente puede tener múltiples ventas asociadas.
    """
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), unique=True)
    telefono = Column(String(20))
    direccion = Column(Text)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    # Relación con ventas
    ventas = relationship("Venta", back_populates="cliente")

class Producto(Base):
    """
    Modelo para la tabla de productos.
    
    Almacena la información de los productos disponibles para la venta.
    
    Attributes:
        id (int): Identificador único del producto, clave primaria.
        nombre (str): Nombre del producto. Campo obligatorio.
        descripcion (Text): Descripción detallada del producto.
        precio (float): Precio unitario del producto. Campo obligatorio.
        stock (int): Cantidad disponible en inventario. Valor predeterminado: 0.
        fecha_creacion (datetime): Fecha y hora de creación del registro del producto.
        
    Relationships:
        detalles_venta (DetalleVenta): Relación uno a muchos con la tabla de detalles de venta.
                                       Un producto puede estar en múltiples detalles de venta.
    """
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    precio = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    # Relación con detalles de venta
    detalles_venta = relationship("DetalleVenta", back_populates="producto")

class Venta(Base):
    """
    Modelo para la tabla de ventas.
    
    Almacena la información de las transacciones de venta realizadas.
    
    Attributes:
        id (int): Identificador único de la venta, clave primaria.
        cliente_id (int): Clave foránea que relaciona con la tabla de clientes.
        fecha_venta (datetime): Fecha y hora en que se realizó la venta.
        total (float): Monto total de la venta. Campo obligatorio.
        estado (str): Estado actual de la venta ('pendiente', 'completada', 'cancelada', etc.).
                      Valor predeterminado: 'pendiente'.
        
    Relationships:
        cliente (Cliente): Relación muchos a uno con la tabla de clientes.
                          Cada venta pertenece a un único cliente.
        detalles (DetalleVenta): Relación uno a muchos con la tabla de detalles de venta.
                                Una venta puede tener múltiples detalles (productos).
        factura (Factura): Relación uno a uno con la tabla de facturas.
                          Una venta puede tener asociada una única factura.
    """
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    fecha_venta = Column(DateTime, default=datetime.utcnow)
    total = Column(Float, nullable=False)
    estado = Column(String(20), default='pendiente')

    # Relaciones
    cliente = relationship("Cliente", back_populates="ventas")
    detalles = relationship("DetalleVenta", back_populates="venta")
    factura = relationship("Factura", back_populates="venta", uselist=False)

class DetalleVenta(Base):
    """
    Modelo para la tabla de detalles de venta.
    
    Almacena la información detallada de los productos incluidos en cada venta.
    Representa la relación muchos a muchos entre Ventas y Productos.
    
    Attributes:
        id (int): Identificador único del detalle de venta, clave primaria.
        venta_id (int): Clave foránea que relaciona con la tabla de ventas.
        producto_id (int): Clave foránea que relaciona con la tabla de productos.
        cantidad (int): Cantidad del producto incluido en la venta. Campo obligatorio.
        precio_unitario (float): Precio unitario del producto al momento de la venta.
                               Campo obligatorio.
        subtotal (float): Monto subtotal (cantidad * precio_unitario). Campo obligatorio.
        
    Relationships:
        venta (Venta): Relación muchos a uno con la tabla de ventas.
                      Cada detalle pertenece a una única venta.
        producto (Producto): Relación muchos a uno con la tabla de productos.
                           Cada detalle está asociado a un único producto.
    """
    __tablename__ = "detalles_venta"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"))
    producto_id = Column(Integer, ForeignKey("productos.id"))
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    # Relaciones
    venta = relationship("Venta", back_populates="detalles")
    producto = relationship("Producto", back_populates="detalles_venta")

class Factura(Base):
    """
    Modelo para la tabla de facturas.
    
    Almacena la información de las facturas generadas para las ventas.
    
    Attributes:
        id (int): Identificador único de la factura, clave primaria.
        venta_id (int): Clave foránea que relaciona con la tabla de ventas.
        numero_factura (str): Número único de la factura. Campo obligatorio.
        fecha_emision (datetime): Fecha y hora de emisión de la factura.
        estado (str): Estado actual de la factura ('pendiente', 'pagada', 'anulada', etc.).
                     Valor predeterminado: 'pendiente'.
        total (float): Monto total de la factura. Campo obligatorio.
        
    Relationships:
        venta (Venta): Relación uno a uno con la tabla de ventas.
                      Cada factura está asociada a una única venta.
    """
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"))
    numero_factura = Column(String(20), unique=True, nullable=False)
    fecha_emision = Column(DateTime, default=datetime.utcnow)
    estado = Column(String(20), default='pendiente')
    total = Column(Float, nullable=False)

    # Relación con venta
    venta = relationship("Venta", back_populates="factura") 