from django.http import HttpRequest


def _get_ip(request: HttpRequest) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def registrar(request_or_user, accion: str, modulo: str, descripcion: str, objeto=None):
    """
    Registra una entrada en el historial.

    Parámetros:
        request_or_user  – HttpRequest o instancia de Usuario
        accion           – código de acción (ver EntradaHistorial.ACCIONES)
        modulo           – código del módulo (ver EntradaHistorial.MODULOS)
        descripcion      – texto libre
        objeto           – instancia del modelo afectado (opcional)
    """
    from .models import EntradaHistorial

    if isinstance(request_or_user, HttpRequest):
        request = request_or_user
        usuario = request.user if request.user.is_authenticated else None
        ip = _get_ip(request)
    else:
        usuario = request_or_user
        ip = None

    entry = EntradaHistorial(
        usuario=usuario,
        accion=accion,
        modulo=modulo,
        descripcion=descripcion,
        ip_address=ip,
    )

    if objeto is not None:
        entry.objeto_id   = getattr(objeto, 'pk', None)
        entry.objeto_tipo = type(objeto).__name__

    entry.save()
    return entry
