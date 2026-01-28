from fastapi import FastAPI, Depends
from database.connection import engine
from sqlalchemy.orm import Session
from database.session import get_db
from routers import cliente, usuario, cotizacion, cotizacion_detalle, prestacion, iva, plan
from repositories.cliente_repository import get_clientes


app = FastAPI(title="SACMED Cotizador API")

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
