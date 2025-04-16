"""
Módulo de configuración de la base de datos utilizando SQLAlchemy.

Este módulo proporciona las funcionalidades básicas para la conexión,
sesión y gestión de la base de datos del sistema utilizando SQLAlchemy ORM.

Components principales:
    - engine: Motor de conexión a la base de datos.
    - SessionLocal: Clase para crear sesiones de base de datos.
    - Base: Clase base declarativa para los modelos ORM.
    - get_db: Función para obtener una sesión de base de datos.

La configuración utiliza variables de entorno para obtener la URL de conexión
a la base de datos, lo que facilita el despliegue en diferentes entornos.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

# Obtener la URL de la base de datos desde las variables de entorno
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Crear el motor de la base de datos
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Crear la sesión local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Crear la clase base para los modelos
Base = declarative_base()

# Dependencia para obtener la sesión de la base de datos
def get_db():
    """
    Función que proporciona una sesión de base de datos.
    
    Esta función se utiliza como dependencia en los endpoints de FastAPI para
    inyectar una sesión de base de datos en cada solicitud. La sesión se cierra
    automáticamente al finalizar la solicitud, incluso si ocurre una excepción.
    
    Yields:
        Session: Una sesión activa de SQLAlchemy para interactuar con la base de datos.
    
    Example:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 