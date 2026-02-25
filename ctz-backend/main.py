from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.connection import engine
from sqlalchemy import inspect, text
from routers import cliente, usuario, cotizacion, cotizacion_detalle, prestacion, iva, plan
from models.conexion_capacitacion import ConexionCapacitacion
from models.capacitacion_plataforma import CapacitacionPlataforma
from routers import conexion_capacitacion, capacitacion_plataforma


app = FastAPI(title="SACMED Cotizador API")


def ensure_plan_whatsapp_column():
    inspector = inspect(engine)

    with engine.begin() as connection:
        columns = {column["name"] for column in inspector.get_columns("planes")}
        if "mensajes_whatsapp" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE planes "
                    "ADD COLUMN mensajes_whatsapp INTEGER NOT NULL DEFAULT 0"
                )
            )


def ensure_conexiones_almacenamiento_table():
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if "conexiones_almacenamiento" not in table_names and "conexiones_capacitacion" in table_names:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE conexiones_capacitacion RENAME TO conexiones_almacenamiento")
            )
        return

    if "conexiones_almacenamiento" not in table_names:
        ConexionCapacitacion.__table__.create(bind=engine)






def ensure_cotizacion_detalle_observaciones_column():
    inspector = inspect(engine)
    if "cotizacion_detalle" not in inspector.get_table_names():
        return

    with engine.begin() as connection:
        columns = {column["name"] for column in inspector.get_columns("cotizacion_detalle")}
        if "observaciones" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE cotizacion_detalle "
                    "ADD COLUMN observaciones VARCHAR(1000) NULL"
                )
            )

def ensure_capacitaciones_plataforma_table():
    inspector = inspect(engine)
    if "capacitaciones_plataforma" not in inspector.get_table_names():
        CapacitacionPlataforma.__table__.create(bind=engine)

def ensure_conexiones_almacenamiento_storage_column():
    inspector = inspect(engine)
    if "conexiones_almacenamiento" not in inspector.get_table_names():
        return

    with engine.begin() as connection:
        columns = {column["name"] for column in inspector.get_columns("conexiones_almacenamiento")}

        if "gigabytes_almacenamiento" not in columns:
            connection.execute(
                text(
                    "ALTER TABLE conexiones_almacenamiento "
                    "ADD COLUMN gigabytes_almacenamiento INTEGER NOT NULL DEFAULT 0"
                )
            )

        if "horas_capacitacion" in columns:
            connection.execute(text("ALTER TABLE conexiones_almacenamiento DROP COLUMN horas_capacitacion"))


ensure_plan_whatsapp_column()
ensure_conexiones_almacenamiento_table()
ensure_capacitaciones_plataforma_table()
ensure_conexiones_almacenamiento_storage_column()
ensure_cotizacion_detalle_observaciones_column()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    try:
        engine.connect()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}

app.include_router(cliente.router)
app.include_router(usuario.router)
app.include_router(cotizacion.router)   
app.include_router(cotizacion_detalle.router)
app.include_router(prestacion.router)
app.include_router(iva.router)
app.include_router(plan.router)
app.include_router(conexion_capacitacion.router)
app.include_router(capacitacion_plataforma.router)
