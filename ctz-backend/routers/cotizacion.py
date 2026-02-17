from datetime import date, timedelta
import json
import os
from urllib import error as urllib_error
from urllib import request as urllib_request

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from database.session import get_db
from models.cotizacion import Cotizacion
from models.usuario import Usuario
from schemas.cotizacion import (
    CotizacionCreate,
    CotizacionResponse,
    CotizacionUpdate,
    CotizacionJasperPayload,
    CotizacionJasperItem,
)
from models.cotizacion_detalle import CotizacionDetalle

router = APIRouter(tags=["Cotizaciones"])


def attach_user_names(cotizaciones: list[Cotizacion], db: Session):
    user_ids = {cot.id_usuario for cot in cotizaciones if cot.id_usuario is not None}
    if not user_ids:
        return cotizaciones

    usuarios = (
        db.query(Usuario.id_usuario, Usuario.nombre)
        .filter(Usuario.id_usuario.in_(user_ids))
        .all()
    )
    nombres_por_id = {id_usuario: nombre for id_usuario, nombre in usuarios}

    for cot in cotizaciones:
        cot.nombre_usuario = nombres_por_id.get(cot.id_usuario)

    return cotizaciones


def _to_float(value, default=0.0):
    if value is None:
        return float(default)
    return float(value)


def _build_jasper_payload(cotizacion: Cotizacion, db: Session) -> CotizacionJasperPayload:
    detalles = (
        db.query(CotizacionDetalle)
        .filter(CotizacionDetalle.id_cotizacion == cotizacion.id_cotizacion)
        .all()
    )

    usuario = None
    if cotizacion.id_usuario is not None:
        usuario = db.query(Usuario).get(cotizacion.id_usuario)

    items = []
    for detalle in detalles:
        cantidad = detalle.cantidad or 0
        valor_unitario = _to_float(detalle.valor_unitario)
        descuento = _to_float(detalle.descuento)
        total = _to_float(detalle.total)
        if total == 0:
            total = max(0.0, (cantidad * valor_unitario) - descuento)

        items.append(
            CotizacionJasperItem(
                cantidad=cantidad,
                descripcion=detalle.descripcion or "Servicio",
                precio_unitario=valor_unitario,
                descuento=descuento,
                total=total,
            )
        )

    subtotal = _to_float(cotizacion.subtotal)
    if subtotal == 0:
        subtotal = sum(item.total for item in items)

    iva = _to_float(cotizacion.iva_monto)
    if iva == 0:
        iva = subtotal * 0.19

    total_mensual = _to_float(cotizacion.total)
    if total_mensual == 0:
        total_mensual = subtotal + iva

    meses = cotizacion.meses or 1
    total_periodo = total_mensual * meses

    condiciones_texto = (cotizacion.condiciones_adicionales or "").strip()
    condiciones_generales = []
    if condiciones_texto:
        condiciones_generales = [
            linea.strip("• ").strip()
            for linea in condiciones_texto.splitlines()
            if linea.strip()
        ]

    if not condiciones_generales:
        condiciones_generales = [
            "Los valores indicados son mensuales y deben pagarse desde la fecha que se acepten los términos.",
            "El cobro se realiza para garantizar la disponibilidad del servicio, no por su nivel de uso.",
        ]

    return CotizacionJasperPayload(
        cliente=cotizacion.nombre_cliente or "Cliente",
        rut=cotizacion.rut_cliente or "",
        ejecutivo=usuario.nombre if usuario else "",
        fecha_emision=cotizacion.fecha_emision,
        fecha_vencimiento=cotizacion.fecha_vencimiento,
        conexiones_simultaneas=cotizacion.conexiones,
        usuarios="Ilimitados",
        subtotal=subtotal,
        iva=iva,
        total_mensual=total_mensual,
        total_periodo=total_periodo,
        condiciones_generales=condiciones_generales,
        capacitacion=[
            "Este presupuesto incluye 2 horas de configuración remota para asistir en el uso de la plataforma.",
        ],
        cobros_adicionales=[
            "La activación de SMS/WhatsApp puede generar costos adicionales según uso.",
            "El presupuesto incluye 10 GB de almacenamiento en disco.",
        ],
        items=items,
    )


@router.post("/cotizaciones", response_model=CotizacionResponse)
def crear_cotizacion(data: CotizacionCreate, db: Session = Depends(get_db)):
    cotizacion = Cotizacion(**data.dict())
    cotizacion.fecha_emision = date.today()
    cotizacion.fecha_vencimiento = date.today() + timedelta(days=30)
    db.add(cotizacion)
    db.commit()
    db.refresh(cotizacion)
    return cotizacion


@router.get("/cotizaciones", response_model=list[CotizacionResponse])
def listar_cotizaciones(
    id_usuario: int | None = Query(default=None),
    db: Session = Depends(get_db)
):
    query = db.query(Cotizacion)
    if id_usuario is not None:
        query = query.filter(Cotizacion.id_usuario == id_usuario)

    cotizaciones = query.all()
    return attach_user_names(cotizaciones, db)


@router.get("/cotizaciones/{id_cotizacion}", response_model=CotizacionResponse)
def obtener_cotizacion(id_cotizacion: int, db: Session = Depends(get_db)):
    cotizacion = db.query(Cotizacion).get(id_cotizacion)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    attach_user_names([cotizacion], db)
    return cotizacion


@router.get("/cotizaciones/{id_cotizacion}/jasper", response_model=CotizacionJasperPayload)
def obtener_cotizacion_para_jasper(id_cotizacion: int, db: Session = Depends(get_db)):
    cotizacion = db.query(Cotizacion).get(id_cotizacion)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    return _build_jasper_payload(cotizacion, db)


@router.get("/cotizaciones/{id_cotizacion}/jasper/pdf")
def generar_pdf_jasper(id_cotizacion: int, db: Session = Depends(get_db)):
    cotizacion = db.query(Cotizacion).get(id_cotizacion)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    jasper_render_url = os.getenv("JASPER_RENDER_URL")
    if not jasper_render_url:
        raise HTTPException(
            status_code=503,
            detail="El servicio Jasper no está configurado. Define JASPER_RENDER_URL en el backend.",
        )

    payload = _build_jasper_payload(cotizacion, db).dict()
    body = json.dumps(payload).encode("utf-8")
    request = urllib_request.Request(
        jasper_render_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/pdf",
        },
        method="POST",
    )

    jasper_token = os.getenv("JASPER_API_TOKEN")
    if jasper_token:
        request.add_header("Authorization", f"Bearer {jasper_token}")

    try:
        with urllib_request.urlopen(request, timeout=45) as response:
            pdf_content = response.read()
            content_type = response.headers.get("Content-Type", "application/pdf")
    except urllib_error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="ignore")
        detail = error_text.strip() or "Jasper respondió con un error al generar el PDF."
        raise HTTPException(status_code=502, detail=detail) from exc
    except urllib_error.URLError as exc:
        raise HTTPException(
            status_code=502,
            detail="No fue posible conectar con el servicio Jasper.",
        ) from exc

    file_name = f"cotizacion-{id_cotizacion}.pdf"
    return StreamingResponse(
        iter([pdf_content]),
        media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="{file_name}"'},
    )


@router.put("/cotizaciones/{id_cotizacion}", response_model=CotizacionResponse)
def actualizar_cotizacion(id_cotizacion: int, data: CotizacionUpdate, db: Session = Depends(get_db)):
    cotizacion = db.query(Cotizacion).get(id_cotizacion)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    for campo, valor in data.dict(exclude_unset=True).items():
        setattr(cotizacion, campo, valor)
    db.commit()
    db.refresh(cotizacion)
    return cotizacion


@router.delete("/cotizaciones/{id_cotizacion}")
def eliminar_cotizacion(id_cotizacion: int, db: Session = Depends(get_db)):
    cotizacion = db.query(Cotizacion).get(id_cotizacion)

    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    if cotizacion.estado == "CONFIRMADA":
        raise HTTPException(status_code=400, detail="Las cotizaciones confirmadas no se pueden eliminar")

    db.query(CotizacionDetalle)\
        .filter(CotizacionDetalle.id_cotizacion == id_cotizacion)\
        .delete()

    db.delete(cotizacion)

    db.commit()
    return {"ok": True}
