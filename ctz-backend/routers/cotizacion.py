from datetime import date, datetime, timedelta, timezone
from html import escape
import base64
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from database.session import get_db
from models.cotizacion import Cotizacion
from models.capacitacion_plataforma import CapacitacionPlataforma
from models.plan import Plan
from models.prestacion import Prestacion
from models.usuario import Usuario
from models.iva import Iva
from schemas.cotizacion import (
    CotizacionCreate,
    CotizacionResponse,
    CotizacionUpdate,
    CotizacionJasperPayload,
    CotizacionJasperItem,
)
from models.cotizacion_detalle import CotizacionDetalle

router = APIRouter(tags=["Cotizaciones"])

ANNEX_STORAGE_DIR = Path(__file__).resolve().parents[1] / "storage"
ANNEX_PDF_PATH = ANNEX_STORAGE_DIR / "servicios-adicionales.pdf"
ANNEX_META_PATH = ANNEX_STORAGE_DIR / "servicios-adicionales.meta"
def _today_in_chile() -> date:
    try:
        chile_tz = ZoneInfo("America/Santiago")
        return datetime.now(chile_tz).date()
    except ZoneInfoNotFoundError:
        # Fallback para entornos sin base tzdata (común en Windows/Python embebido).
        # Mantiene la app operativa y aproxima la fecha local de Chile.
        chile_fixed_offset = timezone(timedelta(hours=-3))
        return datetime.now(chile_fixed_offset).date()



def _ensure_annex_storage():
    ANNEX_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _get_annex_metadata() -> dict:
    if not ANNEX_META_PATH.exists():
        return {}

    try:
        raw = ANNEX_META_PATH.read_text(encoding="utf-8").split("|", maxsplit=1)
        return {
            "filename": raw[0] or ANNEX_PDF_PATH.name,
            "uploaded_at": raw[1] if len(raw) > 1 else None,
        }
    except Exception:
        return {"filename": ANNEX_PDF_PATH.name, "uploaded_at": None}


def _merge_pdfs(main_pdf: bytes, annex_pdf_path: Path) -> bytes:
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Falta la dependencia pypdf para anexar el documento adicional.",
        ) from exc

    writer = PdfWriter()
    for page in PdfReader(BytesIO(main_pdf)).pages:
        writer.add_page(page)
    for page in PdfReader(str(annex_pdf_path)).pages:
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def attach_user_names(cotizaciones: list[Cotizacion], db: Session):
    user_ids = {cot.id_usuario for cot in cotizaciones if cot.id_usuario is not None}
    if not user_ids:
        return cotizaciones

    usuarios = (
        db.query(Usuario.id_usuario, Usuario.nombre, Usuario.activo)
        .filter(Usuario.id_usuario.in_(user_ids))
        .all()
    )
    usuarios_por_id = {
        id_usuario: {
            "nombre": nombre,
            "activo": activo,
        }
        for id_usuario, nombre, activo in usuarios
    }

    for cot in cotizaciones:
        usuario = usuarios_por_id.get(cot.id_usuario)
        cot.nombre_usuario = usuario["nombre"] if usuario else None
        cot.usuario_eliminado = cot.id_usuario is not None and (not usuario or not usuario["activo"])

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


def _normalize_quote_type(raw_type: str | None) -> tuple[str, bool]:
    normalized = (raw_type or "").strip().upper()
    is_unique = normalized in {"UNICA", "ÚNICA"}
    if is_unique:
        return "Única", True
    return "Período", False


def _split_conditions_and_observations(raw_conditions: str | None) -> tuple[list[str], list[str]]:
    if not raw_conditions:
        return [], []

    conditions: list[str] = []
    observations: list[str] = []
    for line in raw_conditions.splitlines():
        normalized = line.strip("• ").strip()
        if not normalized:
            continue

        if normalized.upper().startswith("__OBS__"):
            observation_text = normalized[7:].strip(" :-")
            if observation_text:
                observations.append(observation_text)
            continue

        conditions.append(normalized)

    return conditions, observations


def _parse_conditions_text(raw_conditions: str | None) -> list[str]:
    conditions, _ = _split_conditions_and_observations(raw_conditions)
    return conditions


def _parse_observations_text(raw_conditions: str | None) -> list[str]:
    _, observations = _split_conditions_and_observations(raw_conditions)
    return observations

def _is_quote_on_request_condition(condition: str) -> bool:
    normalized = (condition or "").strip().lower()
    return "valor a cotizar" in normalized


def _is_sacmed_signature_service(service_name: str | None) -> bool:
    normalized = (service_name or "").strip().lower()
    return "firma" in normalized and "electr" in normalized and "sacmed" in normalized


def _merge_conditions(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for condition in group:
            key = condition.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(condition.strip())
    return merged


def _quote_has_plan_item(detalles: list[CotizacionDetalle], db: Session) -> bool:
    if not detalles:
        return False

    plan_names = {
        (plan_name or "").strip().lower()
        for (plan_name,) in db.query(Plan.nombre).filter(Plan.activo.is_(True)).all()
        if (plan_name or "").strip()
    }
    if not plan_names:
        return False

    for detalle in detalles:
        descripcion = (detalle.descripcion or "").strip().lower()
        if not descripcion:
            continue

        if any(plan_name in descripcion for plan_name in plan_names):
            return True

    return False


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
    # Determine IVA percentage from the database (use cotizacion.id_iva if provided,
    # otherwise use the first active IVA). The DB stores percentage like 19 or 19.9
    porcentaje = None
    try:
        if getattr(cotizacion, 'id_iva', None):
            iva_obj = db.query(Iva).get(cotizacion.id_iva)
            if iva_obj:
                porcentaje = float(iva_obj.porcentaje)
        if porcentaje is None:
            iva_obj = db.query(Iva).filter(Iva.activo == True).first()
            if iva_obj:
                porcentaje = float(iva_obj.porcentaje)
    except Exception:
        porcentaje = None

    if porcentaje is None:
        porcentaje = 19.0

    if iva == 0:
        iva = subtotal * (porcentaje / 100.0)

    total_mensual = _to_float(cotizacion.total)
    if total_mensual == 0:
        total_mensual = subtotal + iva

    tipo_cotizacion, es_cotizacion_unica = _normalize_quote_type(cotizacion.tipo)
    incluye_plan = _quote_has_plan_item(detalles, db)

    meses = max(1, int(cotizacion.meses or 1))
    conexiones = int(cotizacion.conexiones or 0)
    es_pago_trimestral = (not es_cotizacion_unica) and conexiones in (1, 2)
    meses_cobro = 3 if es_pago_trimestral else meses

    descuento_periodo_pct = 0.0
    if not es_cotizacion_unica:
        if meses == 12:
            descuento_periodo_pct = 10.0
        elif meses == 6:
            descuento_periodo_pct = 5.0

    total_periodo_base = total_mensual if es_cotizacion_unica else (total_mensual * meses_cobro)
    descuento_periodo_monto = total_periodo_base * (descuento_periodo_pct / 100.0)
    total_periodo = total_periodo_base - descuento_periodo_monto

    condiciones_manual = _parse_conditions_text(cotizacion.condiciones_adicionales)
    observaciones_manual = _parse_observations_text(cotizacion.condiciones_adicionales)

    condiciones_servicios: list[str] = []
    ids_prestaciones = {
        detalle.id_prestacion
        for detalle in detalles
        if detalle.id_prestacion is not None
    }
    if ids_prestaciones:
        prestaciones = (
            db.query(Prestacion.id_prestacion, Prestacion.nombre, Prestacion.condiciones)
            .filter(Prestacion.id_prestacion.in_(ids_prestaciones))
            .all()
        )

        condiciones_por_prestacion = {}
        omitir_valor_a_cotizar = False
        if len(ids_prestaciones) == 1 and prestaciones:
            _, nombre_servicio, _ = prestaciones[0]
            omitir_valor_a_cotizar = _is_sacmed_signature_service(nombre_servicio)

        for id_prestacion, _, condiciones in prestaciones:
            condiciones_por_prestacion[id_prestacion] = condiciones

        for detalle in detalles:
            if detalle.id_prestacion is None:
                continue
            condiciones = _parse_conditions_text(
                condiciones_por_prestacion.get(detalle.id_prestacion)
            )
            if omitir_valor_a_cotizar:
                condiciones = [
                    condition
                    for condition in condiciones
                    if not _is_quote_on_request_condition(condition)
                ]
            condiciones_servicios.extend(condiciones)

    condiciones_generales = _merge_conditions(condiciones_manual, condiciones_servicios)

    condiciones_base_pdf = [
        "Los valores indicados son mensuales y deberán ser pagados desde la fecha que se acepten los términos y condiciones. https://beta-sacmed.movacaribe.com/TdToS.v2.0.2.pdf",
        "El cobro se realiza por garantizar la disponibilidad 24/7 del servicio, no por su nivel de uso.",
        "En caso de que la cantidad de conexiones a contratar sea de una o dos, el primer pago debe ser trimestral (Total Mensual * 3) luego de pasar los 3 meses se genera facturación mensual.",
    ]

    if conexiones <= 5:
        gigabytes_incluidos = 10
    else:
        gigabytes_incluidos = conexiones + 5

    mensajes_incluidos = 0
    plan_referencia = (
        db.query(Plan)
        .filter(Plan.activo.is_(True), Plan.conexiones_incluidas <= conexiones)
        .order_by(Plan.conexiones_incluidas.desc())
        .first()
    )
    if not plan_referencia:
        plan_referencia = (
            db.query(Plan)
            .filter(Plan.activo.is_(True))
            .order_by(Plan.conexiones_incluidas.asc())
            .first()
        )
    if plan_referencia:
        mensajes_incluidos = int(plan_referencia.mensajes_whatsapp or 0)

    horas_capacitacion = 0
    regla_capacitacion = (
        db.query(CapacitacionPlataforma)
        .filter(
            CapacitacionPlataforma.activo.is_(True),
            CapacitacionPlataforma.conexiones_desde <= conexiones,
            (CapacitacionPlataforma.conexiones_hasta.is_(None))
            | (CapacitacionPlataforma.conexiones_hasta >= conexiones),
        )
        .order_by(CapacitacionPlataforma.conexiones_desde.desc())
        .first()
    )
    if regla_capacitacion:
        horas_capacitacion = int(regla_capacitacion.horas_capacitacion or 0)

    if conexiones in (1, 2):
        capacitacion_base_pdf = [
            "Configuración inicial: aproximadamente 2 horas según la cantidad de conexiones contratadas.",
        ]
    else:
        capacitacion_base_pdf = [
            f"Capacitación de plataforma: {horas_capacitacion} horas según el intervalo de conexiones contratado.",
        ]

    cobros_adicionales_base_pdf = [
        "La activación de SMS/WhatsApp, pueden generar costos adicionales, que se facturarán según su uso.",
        f"El presupuesto incluye una bolsa mensual de {mensajes_incluidos} mensajes de WhatsApp para confirmación de citas. En caso de exceder esta cantidad, los mensajes adicionales tendrán un costo de $50 + IVA mensual.",
        f"El presupuesto incluye {gigabytes_incluidos} GB de almacenamiento en disco. Cualquier uso que exceda este límite se cobrará automáticamente a un valor de $5.000 más IVA por cada 5 GB adicionales.",
    ]

    if es_cotizacion_unica:
        condiciones_pdf = condiciones_generales
        capacitacion_base_pdf = []
        cobros_adicionales_base_pdf = []
    else:
        condiciones_pdf = condiciones_generales + (condiciones_base_pdf if incluye_plan else [])
        if not incluye_plan:
            capacitacion_base_pdf = []
            cobros_adicionales_base_pdf = []

    modalidad_pago = "Pago único" if es_cotizacion_unica else f"Cada {meses} mes" + ("" if meses == 1 else "es")

    return CotizacionJasperPayload(
        cliente=(cotizacion.nombre_cliente or "").strip() or "-",
        rut=(cotizacion.rut_cliente or "").strip() or "-",
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
        iva_porcentaje=porcentaje,
        total_mensual=total_mensual,
        total_periodo=total_periodo,
        descuento_periodo_pct=descuento_periodo_pct,
        descuento_periodo_monto=descuento_periodo_monto,
        condiciones_generales=condiciones_pdf,
        capacitacion=capacitacion_base_pdf,
        cobros_adicionales=cobros_adicionales_base_pdf,
        observaciones=observaciones_manual,
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
          <td colspan=\"5\" class=\"empty-row\">No hay servicios agregados</td>
        </tr>
        """

    def _render_section(title: str, items: list[str]) -> str:
        if not items:
            return ""
        item_list = "".join(f"<li>{escape(text)}</li>" for text in items if text)
        if not item_list:
            return ""
        return f'<div class="section-title">{escape(title)}</div><ul>{item_list}</ul>'

    is_unique_quote = (payload.tipo_cotizacion or "").strip().lower() == "única"
    condiciones_section = _render_section("Condiciones Generales:", payload.condiciones_generales)
    capacitacion_section = "" if is_unique_quote else _render_section("Capacitación plataforma:", payload.capacitacion)
    cobros_adicionales_section = "" if is_unique_quote else _render_section("Cobros adicionales:", payload.cobros_adicionales)
    observacion_items = []
    for observation in getattr(payload, "observaciones", []) or []:
        normalized_observation = str(observation or "").strip()
        if normalized_observation:
            observacion_items.append(normalized_observation)

    if not is_unique_quote and any((item.descripcion or "").strip() for item in payload.items):
        observacion_items.insert(0, "Todos los planes contratados llevan como servicio agenda médica, ficha clínica multiespecialista, telemedicina y herramientas administrativas.")

    observacion_section = _render_section("Observaciones:", observacion_items)

    total_label = "Total"
    if not is_unique_quote:
        total_label = "Total período"
        if (payload.conexiones_simultaneas or 0) in (1, 2):
            total_label = "Total trimestral"
        else:
            total_label = f"Total ({payload.meses} mes" + ("" if payload.meses == 1 else "es") + ")"

    period_discount_pct = max(0.0, float(getattr(payload, 'descuento_periodo_pct', 0.0) or 0.0))
    period_discount_amount = max(0.0, float(getattr(payload, 'descuento_periodo_monto', 0.0) or 0.0))
    discount_summary_row = ""
    if (not is_unique_quote) and period_discount_pct > 0 and period_discount_amount > 0:
        discount_summary_row = (
            f'<tr><td>Descuento período ({_format_currency(period_discount_pct)}% sobre total del período)</td>'
            f'<td class="money">- $ {_format_currency(period_discount_amount)}</td></tr>'
        )

    logo_html = (
        f'<img src="{img_data_uri}" alt="SACMED" style="height: 90px; vertical-align: middle;" />'
        if img_data_uri
        else "SACMED"
    )

    # Prepare IVA percentage display (always compute so the template can use it)
    iva_pct_value = getattr(payload, 'iva_porcentaje', None) or 19.0
    try:
        iva_pct_num = float(iva_pct_value)
        if iva_pct_num.is_integer():
            iva_pct_text = f"{int(iva_pct_num)}%"
        else:
            iva_pct_text = f"{round(iva_pct_num, 1)}%"
    except Exception:
        iva_pct_text = "19%"

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
        .title {{ font-size:24px; color:#666; font-weight:700; margin: 8px 0 16px; }}
        .dates {{ width: 55%; margin-left:auto; border-collapse: collapse; font-size:12px; margin-bottom:26px; }}
        .dates td {{ border:1px solid #4f78a4; padding:5px 8px; background:#dce9f8; }}
        .dates td:first-child {{ font-weight:700; width:60%; }}
        .client {{ margin: 16px 0 18px; }}
        .client strong {{ margin-right:8px; }}
        table.main {{ width:100%; border-collapse: collapse; font-size:12px; table-layout: fixed; }}
        table.main th {{ background:#b7d1eb; border:1px solid #787878; padding:6px; text-align:center; }}
        table.main td {{ border:1px solid #909090; padding:5px 7px; }}
        table.main col.col-cantidad {{ width:10%; }}
        table.main col.col-servicio {{ width:44%; }}
        table.main col.col-unitario {{ width:16%; }}
        table.main col.col-descuento {{ width:15%; }}
        table.main col.col-total {{ width:15%; }}
        .empty-row {{ text-align:center; color:#5f6b74; font-style:italic; }}
        .money {{ text-align:right; white-space:nowrap; }}
        .summary-left-cell {{ border:none !important; font-weight:600; line-height:1.7; text-align:center; padding:10px 6px 2px; }}
        .summary-right-cell {{ border:none !important; padding:0 !important; }}
        .summary-right {{ width:100%; border-collapse: collapse; table-layout: fixed; }}
        .summary-right td {{ border:1px solid #909090; padding:4px 6px; }}
        .summary-right tr:last-child td {{ background:#9ec3e8; font-weight:700; }}
        .section-title {{ margin:16px 0 7px; font-weight:700; text-decoration:underline; color:#325f8d; }}
        ul {{ margin: 4px 0 8px 18px; padding:0; line-height:1.45; }}
        li {{ margin: 0 0 6px; }}
        .observacion-list li {{ font-weight: 700; }}
        .footer {{ margin-top:24px; display:flex; justify-content:space-between; }}
        .additional-page {{ page-break-before: always; border:1px solid #b6ab7a; padding:24px; min-height: 255mm; box-sizing:border-box; }}
        .additional-logo {{ text-align:center; margin: 8px 0 18px; }}
        .additional-logo img {{ height: 58px; }}
        .additional-logo .text-logo {{ font-size: 56px; font-weight:700; color:#1f76d0; letter-spacing:1px; }}
        .additional-title {{ font-size:20px; color:#2a5f97; margin: 8px 0 12px; font-weight:700; }}
        .additional-subtitle {{ font-size:14px; color:#2a5f97; margin: 14px 0 8px; font-weight:700; }}
        .additional-list {{ margin-left: 18px; line-height:1.45; }}
        .additional-list > li {{ margin-bottom: 12px; }}
        .additional-list ul {{ margin-top: 4px; }}
        .nota-iva {{ margin-top: 10px; font-weight:700; }}
        .fea-table {{ width:100%; border-collapse: collapse; margin-top: 8px; }}
        .fea-table th, .fea-table td {{ border:1px solid #777; padding:6px; font-size:11px; }}
        .footer-address {{ margin-top: 18px; text-align:center; color:#3d76ae; font-size:10px; font-weight:700; }}
      </style>
    </head>
    <body>
      <div class=\"sheet\">
        <div class=\"logo\">
            {logo_html}
        </div>
        <div class=\"title\">Cotización</div>

        <table class=\"dates\">
          <tr><td>Fecha de emisión</td><td>{_format_date(payload.fecha_emision)}</td></tr>
          <tr><td>Fecha de vencimiento</td><td>{_format_date(payload.fecha_vencimiento)}</td></tr>
        </table>

        <div class="client">
          <div><strong>Cliente:</strong> {escape(payload.cliente)}</div>
          <div><strong>RUT:</strong> {escape(payload.rut)}</div>
        </div>

        <table class="main">
          <colgroup>
            <col class="col-cantidad" />
            <col class="col-servicio" />
            <col class="col-unitario" />
            <col class="col-descuento" />
            <col class="col-total" />
          </colgroup>
          <thead>
            <tr>
              <th>Cantidad</th><th>Descripción</th><th>Precio unitario</th><th>Descuento</th><th>Total</th>
            </tr>
          </thead>
          <tbody>
            {item_rows}
            <tr>
              <td>&nbsp;</td><td></td><td></td><td></td><td></td>
            </tr>
            <tr>
              <td class="summary-left-cell" colspan="3">
                <div>Total de conexiones simultáneas: {payload.conexiones_simultaneas or 0}</div>
                <div>Usuarios: {escape(payload.usuarios or 'Ilimitados')}</div>
              </td>
              <td class="summary-right-cell" colspan="2">
                <table class="summary-right">
                  <tr><td>Subtotal</td><td class="money">$ {_format_currency(payload.subtotal)}</td></tr>
                  <tr><td>IVA ({iva_pct_text})</td><td class="money">$ {_format_currency(payload.iva)}</td></tr>
                  <tr><td>Total mensual</td><td class="money">$ {_format_currency(payload.total_mensual)}</td></tr>
                  {discount_summary_row}
                  <tr><td>{total_label}</td><td class="money">$ {_format_currency(payload.total_periodo)}</td></tr>
                </table>
              </td>
            </tr>
          </tbody>
        </table>

        {observacion_section}
        {condiciones_section}
        {capacitacion_section}
        {cobros_adicionales_section}

        <div class="footer">Documento generado por: {escape(payload.ejecutivo or 'Usuario')}</div>
      </div>

    </body>
    </html>
    """


@router.get("/configuraciones/servicios-adicionales/pdf")
def obtener_pdf_servicios_adicionales():
    if not ANNEX_PDF_PATH.exists():
        raise HTTPException(status_code=404, detail="No hay un PDF configurado")

    metadata = _get_annex_metadata()
    download_name = metadata.get("filename") or ANNEX_PDF_PATH.name
    return FileResponse(
        ANNEX_PDF_PATH,
        media_type="application/pdf",
        filename=download_name,
    )


@router.get("/configuraciones/servicios-adicionales")
def obtener_configuracion_servicios_adicionales():
    if not ANNEX_PDF_PATH.exists():
        return {"has_file": False, "filename": None, "uploaded_at": None}

    metadata = _get_annex_metadata()
    return {
        "has_file": True,
        "filename": metadata.get("filename") or ANNEX_PDF_PATH.name,
        "uploaded_at": metadata.get("uploaded_at"),
    }


@router.post("/configuraciones/servicios-adicionales")
async def subir_pdf_servicios_adicionales(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    if not filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo se permite subir archivos PDF")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="El archivo no tiene un formato PDF válido")

    _ensure_annex_storage()
    ANNEX_PDF_PATH.write_bytes(content)

    uploaded_at = datetime.utcnow().isoformat()
    original_name = file.filename or ANNEX_PDF_PATH.name
    ANNEX_META_PATH.write_text(f"{original_name}|{uploaded_at}", encoding="utf-8")

    return {
        "ok": True,
        "filename": original_name,
        "uploaded_at": uploaded_at,
    }


@router.post("/cotizaciones", response_model=CotizacionResponse)
def crear_cotizacion(data: CotizacionCreate, db: Session = Depends(get_db)):
    cotizacion = Cotizacion(**data.dict())
    fecha_emision = _today_in_chile()
    cotizacion.fecha_emision = fecha_emision
    cotizacion.fecha_vencimiento = fecha_emision + timedelta(days=15)
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

    if ANNEX_PDF_PATH.exists():
        pdf_content = _merge_pdfs(pdf_content, ANNEX_PDF_PATH)

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

    db.query(CotizacionDetalle)\
        .filter(CotizacionDetalle.id_cotizacion == id_cotizacion)\
        .delete()

    db.delete(cotizacion)

    db.commit()
    return {"ok": True}
