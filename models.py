from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, DateTime, Date, Enum
from datetime import datetime

# Inicializar instancia de SQLAlchemy
db = SQLAlchemy()

# -----------------------------
# 📦 Inventario actual por vendedora y sabor
# -----------------------------
class InventarioBollos(db.Model):
    __tablename__ = 'inventario_bollos'

    id = Column(Integer, primary_key=True)
    vendedora = Column(String(100), nullable=False)        # Nombre de la vendedora
    sabor = Column(String(50), nullable=False)              # Sabor del bollo
    cantidad_actual = Column(Integer, default=0)            # Cantidad actual en inventario
    fecha_asignacion = Column(Date, nullable=False)         # Última actualización o asignación

# -----------------------------
# 🧾 Registro individual de ventas por bollo
# -----------------------------
class VentasBollos(db.Model):
    __tablename__ = 'ventas_bollos'

    id = Column(Integer, primary_key=True)
    sabor = Column(String(50), nullable=False)              # Sabor vendido
    vendedora = Column(String(50), nullable=False)          # Vendedora que realizó la venta
    fecha_venta = Column(DateTime, nullable=False)          # Fecha y hora exacta de la venta
    grupo_venta = Column(String(100), nullable=True)        # ID que agrupa múltiples ventas por transacción

# -----------------------------
# 📋 Historial completo de movimientos de inventario
# -----------------------------
# 📋 Historial completo de movimientos de inventario
class MovimientoInventario(db.Model):
    __tablename__ = 'movimientos_inventario'

    id = Column(Integer, primary_key=True)
    vendedora = Column(String(100), nullable=False)
    sabor = Column(String(50), nullable=False)
    tipo = Column(Enum('entrada', 'salida', 'ajuste', name='tipo_movimiento'), nullable=False)
    cantidad = Column(Integer, nullable=False)
    motivo = Column(String(200), nullable=True)
    fecha_movimiento = Column(DateTime, default=datetime.utcnow)
