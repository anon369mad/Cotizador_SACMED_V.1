from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from database.connection import engine
from sqlalchemy.orm import Session
from sqlalchemy import inspect, text
from database.session import get_db
from routers import cliente, usuario, cotizacion, cotizacion_detalle, prestacion, iva, plan
from repositories.cliente_repository import get_clientes


app = FastAPI(title="SACMED Cotizador API")


def ensure_dynamic_attributes_columns():
    inspector = inspect(engine)

    required = {
        "planes": "atributos_adicionales",
        "prestaciones": "atributos_adicionales",
    }

    with engine.begin() as connection:
        for table_name, column_name in required.items():
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            if column_name in columns:
                continue
            connection.execute(
                text(
                    f"ALTER TABLE {table_name} "
                    f"ADD COLUMN {column_name} JSON NOT NULL "
                    "DEFAULT (JSON_OBJECT())"
                )
            )


ensure_dynamic_attributes_columns()

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
