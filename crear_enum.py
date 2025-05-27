import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///basededatos.db")
engine = create_engine(DATABASE_URL)

# Ejecutar solo si estás usando PostgreSQL
if "postgresql" in DATABASE_URL:
    with engine.connect() as connection:
        connection.execute(text("CREATE TYPE sabor_enum AS ENUM ('Plátano', 'Fresa', 'Mango', 'Coco', 'Chocolate', 'Nuez', 'Pay de Limón', 'Mangonada');"))
        print("ENUM creado correctamente en PostgreSQL.")
else:
    print("Estás en SQLite. No es necesario crear ENUM.")