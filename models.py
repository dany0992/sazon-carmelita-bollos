from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Date

# Inicializar instancia de SQLAlchemy
db = SQLAlchemy()

# -----------------------------
# 📦 Inventario de bollos por vendedora
# -----------------------------
class InventarioBollos(db.Model):
    __tablename__ = 'inventario_bollos'

    id = Column(Integer, primary_key=True)
    vendedora = Column(String(100), nullable=False)        # Nombre de la vendedora
    sabor = Column(String(50), nullable=False)              # Sabor del bollo
    cantidad_actual = Column(Integer, default=0)            # Cantidad disponible
    fecha_asignacion = Column(Date, nullable=False)         # Fecha en que se asignó el inventario

# -----------------------------
# 🧾 Registro individual de ventas por bollo
# -----------------------------
class VentasBollos(db.Model):
    __tablename__ = 'ventas_bollos'

    id = Column(Integer, primary_key=True)
    sabor = Column(String(50), nullable=False)              # Sabor vendido
    vendedora = Column(String(50), nullable=False)          # Vendedora responsable
    fecha_venta = Column(DateTime, nullable=False)          # Fecha y hora exacta
    grupo_venta = Column(String(100), nullable=True)        # ID que agrupa múltiples ventas de una misma transacción

# -----------------------------
# 📊 Cierre diario por sabor y vendedora
# -----------------------------
class CorteDia(db.Model):
    __tablename__ = 'corte_dia'

    id = Column(Integer, primary_key=True)
    vendedora = Column(String(100), nullable=False)         # Nombre de la vendedora
    fecha = Column(Date, nullable=False)                    # Día del corte
    sabor = Column(String(50), nullable=False)              # Sabor de bollo
    cantidad_vendida = Column(Integer, nullable=False)      # Total vendido
    cantidad_restante = Column(Integer, nullable=False)     # Inventario restante al cierre