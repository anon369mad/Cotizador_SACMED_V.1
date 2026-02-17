from datetime import date, timedelta
from html import escape
import base64
from pathlib import Path

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


def _format_currency(value: float) -> str:
    return f"{round(_to_float(value)):,.0f}".replace(",", ".")


def _format_date(value: date | None) -> str:
    if not value:
        return "-"
    return value.strftime("%d-%m-%Y")


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
        descuento = max(0.0, min(100.0, _to_float(detalle.descuento)))
        total = _to_float(detalle.total)
        if total == 0:
            total = max(0.0, (cantidad * valor_unitario) * (1 - (descuento / 100)))

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

    meses = max(1, int(cotizacion.meses or 1))
    total_periodo = total_mensual if (cotizacion.tipo or '').strip() == 'Única' else (total_mensual * meses)

    condiciones_texto = (cotizacion.condiciones_adicionales or "").strip()
    condiciones_generales = []
    if condiciones_texto:
        condiciones_generales = [
            linea.strip("• ").strip()
            for linea in condiciones_texto.splitlines()
            if linea.strip()
        ]

    tipo_cotizacion = (cotizacion.tipo or "").strip() or "-"
    modalidad_pago = "Pago único" if tipo_cotizacion == "Única" else f"Cada {meses} mes" + ("" if meses == 1 else "es")

    return CotizacionJasperPayload(
        cliente=cotizacion.nombre_cliente or "Cliente",
        rut=cotizacion.rut_cliente or "",
        ejecutivo=usuario.nombre if usuario else "",
        tipo_cotizacion=tipo_cotizacion,
        modalidad_pago=modalidad_pago,
        meses=meses,
        fecha_emision=cotizacion.fecha_emision,
        fecha_vencimiento=cotizacion.fecha_vencimiento,
        conexiones_simultaneas=cotizacion.conexiones,
        usuarios="Ilimitados",
        subtotal=subtotal,
        iva=iva,
        total_mensual=total_mensual,
        total_periodo=total_periodo,
        condiciones_generales=condiciones_generales,
        capacitacion=[],
        cobros_adicionales=[],
        items=items,
    )


def _build_weasy_html(payload: CotizacionJasperPayload) -> str:
    # Try to embed the logo as a base64 data URI so WeasyPrint can load it
    img_data_uri = ""
    try:
        logo_path = (
            Path(__file__).resolve().parents[2]
            / "ctz-frontend"
            / "public"
            / "sacmed.png"
        )
        if logo_path.exists():
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
            img_data_uri = f"data:image/png;base64,{encoded}"
    except Exception:
        img_data_uri = ""

    item_rows = ""
    for item in payload.items:
        item_rows += f"""
        <tr>
          <td>{item.cantidad}</td>
          <td>{escape(item.descripcion)}</td>
          <td class=\"money\">$ {_format_currency(item.precio_unitario)}</td>
          <td class=\"money\">{_format_currency(item.descuento)}%</td>
          <td class=\"money\">$ {_format_currency(item.total)}</td>
        </tr>
        """

    if not item_rows:
        item_rows = """
        <tr>
          <td>1</td>
          <td>Suscripción SACMED Plan Starter</td>
          <td class=\"money\">$ 0</td>
          <td class=\"money\">$ 0</td>
          <td class=\"money\">$ 0</td>
        </tr>
        """

    condiciones = "".join(f"<li>{escape(text)}</li>" for text in payload.condiciones_generales)
    condiciones_section = ""
    if condiciones:
        condiciones_section = f'<div class="section-title">Condiciones adicionales:</div><ul>{condiciones}</ul>'
    total_label = "Total (Pago único)"
    if payload.total_periodo != payload.total_mensual:
        total_label = "Total (Período)"
    logo_html = (
        f'<img src="{img_data_uri}" alt="SACMED" style="height: 90px; vertical-align: middle;" />'
        if img_data_uri
        else "SACMED"
    )

    return f"""
    <!doctype html>
    <html lang=\"es\">
    <head>
      <meta charset=\"utf-8\" />
      <style>
        @page {{ size: A4; margin: 14mm; }}
        body {{ font-family: Arial, sans-serif; color:#2f2f2f; font-size:12px; }}
        .sheet {{ border:1px solid #525252; padding:22px; min-height: 255mm; box-sizing:border-box; }}
        .logo {{ font-size:52px; font-weight:700; color:#1f76d0; letter-spacing:1px; margin-bottom:8px; }}
        .title {{ font-size:33px; color:#666; font-weight:700; margin: 8px 0 20px; }}
        .dates {{ width: 55%; margin-left:auto; border-collapse: collapse; font-size:12px; margin-bottom:26px; }}
        .dates td {{ border:1px solid #4f78a4; padding:5px 8px; background:#dce9f8; }}
        .dates td:first-child {{ font-weight:700; width:60%; }}
        .client {{ margin: 16px 0 18px; }}
        .client strong {{ margin-right:8px; }}
        table.main {{ width:100%; border-collapse: collapse; font-size:12px; }}
        table.main th {{ background:#b7d1eb; border:1px solid #787878; padding:6px; text-align:center; }}
        table.main td {{ border:1px solid #909090; padding:5px 7px; }}
        .money {{ text-align:right; white-space:nowrap; }}
        .summary-wrap {{ display:flex; justify-content:space-between; margin-top:8px; }}
        .summary-left {{ width:60%; font-weight:600; line-height:1.7; }}
        .summary-right {{ width:40%; border-collapse: collapse; }}
        .summary-right td {{ border:1px solid #909090; padding:4px 6px; }}
        .summary-right tr:last-child td {{ background:#9ec3e8; font-weight:700; }}
        .section-title {{ margin:16px 0 7px; font-weight:700; text-decoration:underline; color:#325f8d; }}
        ul {{ margin: 4px 0 8px 18px; padding:0; line-height:1.45; }}
        li {{ margin: 0 0 6px; }}
        .footer {{ margin-top:24px; display:flex; justify-content:space-between; }}
        .sign {{ margin-top:40px; font-weight:700; text-align:right; }}
      </style>
    </head>
    <body>
      <div class=\"sheet\">
        <div class=\"logo\">
            {logo_html}
        </div>
        <div class=\"title\">Documento de cotización</div>

        <table class=\"dates\">
          <tr><td>Fecha de emisión</td><td>{_format_date(payload.fecha_emision)}</td></tr>
          <tr><td>Fecha de vencimiento</td><td>{_format_date(payload.fecha_vencimiento)}</td></tr>
        </table>

        <div class="client">
          <div><strong>Cliente:</strong> {escape(payload.cliente)}</div>
          <div><strong>RUT:</strong> {escape(payload.rut)}</div>
          <div><strong>Tipo de cotización:</strong> {escape(payload.tipo_cotizacion or '-')}</div>
          <div><strong>Período (meses):</strong> {payload.meses}</div>
          <div><strong>Modalidad de pago:</strong> {escape(payload.modalidad_pago)}</div>
        </div>

        <table class=\"main\">
          <thead>
            <tr>
              <th>Cantidad</th><th>Servicio</th><th>Unitario</th><th>Desc.</th><th>Total</th>
            </tr>
          </thead>
          <tbody>
            {item_rows}
          </tbody>
        </table>

        <div class=\"summary-wrap\">
          <div class=\"summary-left\">
            <div>Total de conexiones simultáneas: {payload.conexiones_simultaneas or 0}</div>
            <div>Usuarios: {escape(payload.usuarios or 'Ilimitados')}</div>
          </div>
          <table class=\"summary-right\">
            <tr><td>Subtotal mensual</td><td class=\"money\">$ {_format_currency(payload.subtotal)}</td></tr>
            <tr><td>IVA mensual (19%)</td><td class=\"money\">$ {_format_currency(payload.iva)}</td></tr>
            <tr><td>{total_label}</td><td class=\"money\">$ {_format_currency(payload.total_periodo)}</td></tr>
          </table>
        </div>

        {condiciones_section}

        <div class=\"footer\">Documento generado por: {escape(payload.ejecutivo or 'Usuario')}</div>
        <div class=\"sign\">Firma Cliente ________________________</div>
      </div>
    </body>
    </html>
    """


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


@router.get("/cotizaciones/{id_cotizacion}/weasy", response_model=CotizacionJasperPayload)
def obtener_cotizacion_para_weasy(id_cotizacion: int, db: Session = Depends(get_db)):
    return obtener_cotizacion_para_jasper(id_cotizacion, db)


@router.get("/cotizaciones/{id_cotizacion}/jasper/pdf")
def generar_pdf_jasper(id_cotizacion: int, db: Session = Depends(get_db)):
    cotizacion = db.query(Cotizacion).get(id_cotizacion)
    if not cotizacion:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    try:
        from weasyprint import HTML
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="WeasyPrint no está instalado en el backend.",
        ) from exc

    payload = _build_jasper_payload(cotizacion, db)
    html = _build_weasy_html(payload)

    try:
        pdf_content = HTML(string=html).write_pdf()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo generar el PDF con WeasyPrint: {exc}",
        ) from exc

    file_name = f"cotizacion-{id_cotizacion}.pdf"
    return StreamingResponse(
        iter([pdf_content]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{file_name}"'},
    )


@router.get("/cotizaciones/{id_cotizacion}/weasy/pdf")
def generar_pdf_weasy(id_cotizacion: int, db: Session = Depends(get_db)):
    return generar_pdf_jasper(id_cotizacion, db)


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
