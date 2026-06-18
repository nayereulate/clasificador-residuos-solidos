# EcoTrack – Guía de instalación

## Requisitos previos

- Python 3.10 o superior
- pip
- Git

---

## Instalación desde cero (para compañeros que clonan el repo)

### 1. Clonar el repositorio

```bash
git clone https://github.com/TU_USUARIO/TU_REPOSITORIO.git
cd ClasificadorDeResiduos
```

### 2. Crear y activar el entorno virtual

```bash
# Crear
python -m venv venv

# Activar en Windows
venv\Scripts\activate

# Activar en Linux / Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
pip install python-dotenv openpyxl
```

> Si `requirements.txt` tiene problemas de codificación, instala manualmente
> los paquetes principales:
> ```bash
> pip install django ultralytics torch torchvision opencv-python pillow
> pip install google-generativeai python-dotenv openpyxl
> ```

### 4. Configurar variables de entorno

```bash
# Windows
copy .env.example .env

# Linux / Mac
cp .env.example .env
```

Abre el archivo `.env` y completa:
- `SECRET_KEY` → cualquier cadena larga y aleatoria
- `GEMINI_API_KEY` → tu API key de Google AI Studio

### 5. Crear las migraciones y la base de datos

```bash
python manage.py makemigrations usuarios
python manage.py makemigrations clasificacion
python manage.py makemigrations historial
python manage.py makemigrations recoleccion
python manage.py makemigrations
python manage.py migrate
```

### 6. Crear el superusuario administrador

```bash
python manage.py createsuperuser
```

Sigue las instrucciones: ingresa nombre de usuario, email (opcional) y contraseña.

### 7. Iniciar el servidor

```bash
python manage.py runserver
```

Abre el navegador en: **http://localhost:8000**

---

## ¿Qué NO está en el repositorio?

| Archivo/Carpeta | Por qué no está |
|---|---|
| `db.sqlite3` | Cada PC crea su propia base de datos |
| `.env` | Contiene API keys sensibles |
| `venv/` | El entorno virtual se instala localmente |
| `media/` | Las imágenes subidas son locales |

---

## Nota sobre el modelo YOLO (`best.pt`)

El archivo `apps/clasificacion/models/best.pt` es el modelo entrenado para
detectar residuos. Si GitHub rechaza subirlo por ser muy grande (>100MB),
compártelo por Google Drive / WeTransfer con tus compañeros y pídeles que
lo coloquen en esa misma ruta.

---

## Módulos del sistema

| Módulo | URL | Descripción |
|---|---|---|
| Detección IA | `/` | Subir imágenes / cámara en vivo con YOLOv8 |
| Administración | `/administracion/` | Grammar Engine, cola de prioridad |
| Reportes | `/reportes/` | Gráficas Chart.js, exportar Excel/PDF |
| Historial | `/historial/` | Log de todas las acciones del sistema |
| Recolección | `/recoleccion/` | Rutas y agenda de recogida |
| Usuarios | `/usuarios/` | Gestión de cuentas y roles |
| Perfil | `/perfil/` | Datos personales, cambiar contraseña |

## Roles

- **Administrador** → acceso completo a todos los módulos
- **Operador** → Detección IA, Administración, Historial, Recolección
