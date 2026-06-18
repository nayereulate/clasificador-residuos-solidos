from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import render, redirect, get_object_or_404

from .forms import UsuarioCrearForm, UsuarioEditarForm, PerfilForm
from .models import Usuario


# ─── Decorador simple para admins ────────────────────────────────────────────

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.es_admin):
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('inicio')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ─── Auth ────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            # Registrar en historial
            try:
                from apps.historial.utils import registrar
                registrar(request, 'LOGIN', 'usuarios', f'El usuario {user.username} inició sesión.')
            except Exception:
                pass
            next_url = request.GET.get('next', 'inicio')
            return redirect(next_url)
        else:
            return render(request, 'auth/login.html', {'error': True})

    return render(request, 'auth/login.html')


def logout_view(request):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            from apps.historial.utils import registrar
            registrar(request, 'LOGOUT', 'usuarios', f'El usuario {request.user.username} cerró sesión.')
        except Exception:
            pass
    logout(request)
    return redirect('login')


# ─── Perfil ──────────────────────────────────────────────────────────────────

@login_required
def perfil_view(request):
    if request.method == 'POST':
        form = PerfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('perfil')
    else:
        form = PerfilForm(instance=request.user)

    pwd_form = PasswordChangeForm(request.user)
    return render(request, 'usuarios/perfil.html', {'form': form, 'pwd_form': pwd_form})


@login_required
def cambiar_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Contraseña actualizada correctamente.')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    return redirect('perfil')


# ─── Gestión de usuarios (admin) ─────────────────────────────────────────────

@admin_required
def lista_usuarios(request):
    q    = request.GET.get('q', '').strip()
    rol  = request.GET.get('rol', '')
    qs   = Usuario.objects.all()

    if q:
        qs = qs.filter(username__icontains=q) | qs.filter(first_name__icontains=q) | \
             qs.filter(last_name__icontains=q) | qs.filter(email__icontains=q)
    if rol:
        qs = qs.filter(rol=rol)

    return render(request, 'usuarios/lista.html', {
        'usuarios': qs,
        'q': q,
        'rol': rol,
    })


@admin_required
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioCrearForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            try:
                from apps.historial.utils import registrar
                registrar(request, 'CREAR', 'usuarios',
                          f'Usuario {usuario.username} creado.', usuario)
            except Exception:
                pass
            messages.success(request, f'Usuario "{usuario.username}" creado correctamente.')
            return redirect('usuarios_lista')
    else:
        form = UsuarioCrearForm()

    return render(request, 'usuarios/form.html', {'form': form, 'modo': 'crear'})


@admin_required
def editar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)

    if request.method == 'POST':
        form = UsuarioEditarForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            try:
                from apps.historial.utils import registrar
                registrar(request, 'EDITAR', 'usuarios',
                          f'Usuario {usuario.username} editado.', usuario)
            except Exception:
                pass
            messages.success(request, f'Usuario "{usuario.username}" actualizado.')
            return redirect('usuarios_lista')
    else:
        form = UsuarioEditarForm(instance=usuario)

    return render(request, 'usuarios/form.html', {'form': form, 'modo': 'editar', 'usuario': usuario})


@admin_required
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.user.pk == usuario.pk:
        messages.error(request, 'No puedes eliminar tu propio usuario.')
        return redirect('usuarios_lista')
    if request.method == 'POST':
        nombre = str(usuario)
        usuario.delete()
        try:
            from apps.historial.utils import registrar
            registrar(request, 'ELIMINAR', 'usuarios', f'Usuario {nombre} eliminado.')
        except Exception:
            pass
        messages.success(request, f'Usuario "{nombre}" eliminado.')
    return redirect('usuarios_lista')
