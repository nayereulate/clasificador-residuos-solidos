<div align="center">

# ♻️ EcoTrack
### Sistema de Control y Manejo de Residuos Sólidos

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.0.6-092E20?style=for-the-badge&logo=django&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-FF6B6B?style=for-the-badge&logo=python&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

*Detección inteligente de residuos mediante visión por computadora y clasificación automática con un motor de reglas personalizado.*

</div>

---

## 📋 Tabla de contenidos

- [🎯 ¿Qué es EcoTrack?](#-qué-es-ecotrack)
- [✨ Características principales](#-características-principales)
- [🏗️ Arquitectura del sistema](#️-arquitectura-del-sistema)
- [🧩 Módulos](#-módulos)
- [🛠️ Tecnologías utilizadas](#️-tecnologías-utilizadas)
- [🎨 Patrones de diseño](#-patrones-de-diseño)
- [🚀 Instalación](#-instalación)
- [📁 Estructura del proyecto](#-estructura-del-proyecto)
- [👥 Roles del sistema](#-roles-del-sistema)

---

## 🎯 ¿Qué es EcoTrack?

**EcoTrack** es una aplicación web desarrollada en Django que permite **detectar, clasificar y gestionar residuos sólidos** mediante inteligencia artificial. El sistema utiliza **YOLOv8** para detectar objetos en imágenes y un **Grammar Engine personalizado** para clasificarlos por material, asignarles prioridad de recolección y generar alertas automáticas.

> Proyecto académico — Clasificador de Residuos Sólidos MTP2

---

## ✨ Características principales

| Característica | Descripción |
|---|---|
| 🤖 **Detección IA** | YOLOv8 detecta residuos en imágenes estáticas y cámara en vivo |
| ⚙️ **Grammar Engine** | Motor de reglas IF→THEN con 111 reglas de clasificación |
| 📊 **Reportes** | Gráficas interactivas con Chart.js, exportar a Excel y PDF |
| 📋 **Historial** | Log automático de todas las acciones del sistema |
| 🚛 **Recolección** | Gestión de rutas y agenda de recolección |
| 👥 **Usuarios** | Autenticación con roles (Administrador / Operador) |
| 🌙 **Dark mode** | Tema claro/oscuro con persistencia en localStorage |
| 📱 **Responsive** | Sidebar adaptable, funciona en móvil y escritorio |

---

## 🏗️ Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        ECOTRACK - FLUJO                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   📷 MÓDULO 1 — Detección IA                                    │
│   ─────────────────────────────                                  │
│   Imagen / Cámara                                                │
│        │                                                         │
│        ▼                                                         │
│   YOLOv8 (best.pt)  ──►  JSON con objetos detectados           │
│        │                  {"Lata": 3, "Botella": 5}             │
│        ▼                                                         │
│   Base de datos (Residuo)                                        │
│                                                                  │
│   ⚙️  MÓDULO 2 — Administración                                 │
│   ─────────────────────────────                                  │
│   resultado_json                                                 │
│        │                                                         │
│        ▼                                                         │
│   MaterialClassifierFactory  (Patrón Factory)                   │
│        │                                                         │
│        ▼                                                         │
│   GrammarEngine.process()   (Pipeline)                          │
│   ├── Parser.parse()                                             │
│   ├── Validator.validate()                                       │
│   └── Interpreter.interpret() ──► RuleEngine (111 reglas)       │
│        │                                                         │
│        ▼                                                         │
│   PriorityQueue  ──►  Alertas  ──►  ExportStrategy             │
│        │                                  │                      │
│        ▼                                  ▼                      │
│   ResultadoAdministracion          JSON / XML / TXT             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Módulos

<details>
<summary><b>📷 Módulo 1 — Detección IA</b></summary>

- Sube una imagen o usa la **cámara en vivo** del dispositivo
- **YOLOv8** (`best.pt`) detecta residuos con bounding boxes
- Muestra imagen original vs imagen anotada lado a lado
- La cámara analiza frames en tiempo real cada 900ms con **tracking suavizado**
- Guarda resultados en `Residuo.resultado_json`

**Tecnologías:** Ultralytics YOLOv8, OpenCV, PyTorch, JavaScript (WebRTC)

</details>

<details>
<summary><b>⚙️ Módulo 2 — Administración (Grammar Engine)</b></summary>

Procesa el JSON del Módulo 1 sin volver a ejecutar la IA:

1. **Grammar Engine** valida y aplica 111 reglas `IF → THEN`
2. Clasifica cada objeto en: Metal, Vidrio, Plástico, Papel/Cartón, Orgánico, Espuma/EPS, Otro
3. Determina el **material predominante** y **nivel de prioridad** (1-6)
4. Genera **alertas automáticas** según umbrales configurables
5. **Cola de prioridad** con `queue.PriorityQueue` (Metal=1 → Otro=6)
6. **Procesamiento en hilo** para no bloquear la interfaz
7. **Exportación** en JSON, XML y TXT

</details>

<details>
<summary><b>📊 Módulo 3 — Reportes</b></summary>

- Dashboard con **4 KPIs** en tiempo real
- **Gráfica doughnut** — distribución por material
- **Gráfica de línea** — detecciones por mes
- **Gráfica de barras horizontal** — por prioridad de recolección
- **Gráfica de barras** — distribución de confianza de IA
- Exportar a **Excel** (con estilos y múltiples hojas)
- **Imprimir a PDF** vía página de impresión del navegador

</details>

<details>
<summary><b>📋 Módulo 4 — Historial</b></summary>

- Registro automático de **todas las acciones** del sistema
- Filtra por: acción, módulo, usuario, rango de fechas
- Muestra: usuario, IP, fecha/hora, descripción
- Estadísticas: acciones hoy / esta semana / total

</details>

<details>
<summary><b>🚛 Módulo 5 — Recolección</b></summary>

- Crea y gestiona **rutas de recolección** con zonas y operadores
- Estados: Pendiente → En proceso → Completada / Cancelada
- Asigna residuos a rutas mediante **AJAX** (sin recargar página)
- Cambio de estado en tiempo real
- Filtros por estado, prioridad y zona

</details>

<details>
<summary><b>👥 Módulo 6 — Usuarios</b></summary>

- Login / Logout con autenticación Django
- Modelo `Usuario` extendiendo `AbstractUser`
- **Roles:** Administrador (acceso total) / Operador (acceso limitado)
- Perfil editable: nombre, email, departamento, teléfono
- Cambio de contraseña desde el perfil
- CRUD completo de usuarios (solo administradores)

</details>

---

## 🛠️ Tecnologías utilizadas

### Backend
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=flat-square&logo=django&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)

### Inteligencia Artificial
![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-5C3EE8?style=flat-square&logo=opencv&logoColor=white)
![Ultralytics](https://img.shields.io/badge/YOLOv8-FF6B6B?style=flat-square&logo=python&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google_Gemini-4285F4?style=flat-square&logo=google&logoColor=white)

### Frontend
![Bootstrap](https://img.shields.io/badge/Bootstrap_5.3-7952B3?style=flat-square&logo=bootstrap&logoColor=white)
![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?style=flat-square&logo=chartdotjs&logoColor=white)
![Font Awesome](https://img.shields.io/badge/Font_Awesome_6-528DD7?style=flat-square&logo=fontawesome&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)

### Exportación
![openpyxl](https://img.shields.io/badge/openpyxl-Excel-217346?style=flat-square&logo=microsoftexcel&logoColor=white)
![XML](https://img.shields.io/badge/XML-ElementTree-orange?style=flat-square)

---

## 🎨 Patrones de diseño

```
┌─────────────────┬────────────────────────────────────────────────┐
│ Patrón          │ Dónde se aplica                                │
├─────────────────┼────────────────────────────────────────────────┤
│ 🏭 Factory      │ MaterialClassifierFactory → crea clasificadores │
│ 🔄 Strategy     │ ExportContext → JSON / XML / TXT               │
│ 🔗 Pipeline     │ GrammarEngine → parse → validate → interpret   │
│ 📋 Template     │ Django MTV (Models, Templates, Views)          │
│ 🎯 Observer     │ Threading + AJAX polling para estado en vivo   │
│ 🏗️ Service Layer│ AdministracionService encapsula lógica de negocio│
└─────────────────┴────────────────────────────────────────────────┘
```

---

## 🚀 Instalación

### Prerrequisitos
- Python 3.10+
- Git

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/nayereulate/clasificador-residuos-solidos.git
cd clasificador-residuos-solidos

# 2. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / Mac

# 3. Instalar dependencias
pip install django pillow python-dotenv openpyxl google-generativeai
pip install ultralytics torch torchvision opencv-python

# 4. Configurar variables de entorno
copy .env.example .env         # Windows
# cp .env.example .env         # Linux / Mac
# → Editar .env y completar SECRET_KEY y GEMINI_API_KEY

# 5. Crear la base de datos
python manage.py makemigrations usuarios
python manage.py makemigrations clasificacion
python manage.py makemigrations historial
python manage.py makemigrations recoleccion
python manage.py makemigrations
python manage.py migrate

# 6. Crear superusuario
python manage.py createsuperuser

# 7. Iniciar el servidor
python manage.py runserver
```

Abrir en el navegador: **http://localhost:8000**

---

## 📁 Estructura del proyecto

```
ClasificadorDeResiduos/
│
├── 📁 apps/
│   ├── 📁 usuarios/          # Autenticación, roles, perfiles
│   ├── 📁 clasificacion/     # Módulo 1 (YOLO) + Módulo 2 (Grammar Engine)
│   │   ├── 📁 models/        # best.pt — modelo YOLOv8 entrenado
│   │   ├── 📁 services/      # yolo_service.py, gemini_service.py
│   │   ├── models.py         # Residuo, ResultadoAdministracion
│   │   ├── views.py          # Detección IA + API cámara
│   │   ├── views_admin.py    # Dashboard administración
│   │   └── administracion_service.py  # Grammar Engine + patrones
│   ├── 📁 historial/         # Log de acciones
│   ├── 📁 reportes/          # Gráficas + exportación Excel
│   └── 📁 recoleccion/       # Rutas de recolección
│
├── 📁 grammar_engine/        # Motor de reglas personalizado
│   ├── engine.py             # Orquestador principal
│   ├── parser.py             # Validación de entrada
│   ├── validator.py          # Validación con esquema
│   ├── rules.py              # Motor IF → THEN
│   ├── interpreter.py        # Capa de interpretación
│   └── transformer.py        # Conversión JSON / XML
│
├── 📁 templates/             # HTML con Django Template Language
│   ├── base.html             # Sidebar + Dark mode + Topbar
│   ├── 📁 auth/              # Login
│   ├── 📁 clasificacion/     # Detección + Administración
│   ├── 📁 usuarios/          # Gestión de usuarios
│   ├── 📁 historial/         # Timeline de actividad
│   ├── 📁 reportes/          # Dashboard de gráficas
│   └── 📁 recoleccion/       # Rutas
│
├── 📁 config/
│   ├── settings.py           # Configuración Django
│   └── urls.py               # Enrutamiento principal
│
├── .env.example              # Plantilla de variables de entorno
├── .gitignore                # Archivos excluidos de Git
└── SETUP.md                  # Guía de instalación detallada
```

---

## 👥 Roles del sistema

| Rol | Detección IA | Administración | Reportes | Historial | Recolección | Usuarios |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Administrador** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Operador** | ✅ | ✅ | ❌ | ✅ | ✅ | ❌ |

---

## 🔒 Seguridad

- ✅ Variables de entorno para API keys y `SECRET_KEY`
- ✅ Todas las vistas protegidas con `@login_required`
- ✅ Control de acceso por rol en vistas sensibles
- ✅ Protección CSRF en todos los formularios
- ✅ Log automático de acciones en el Historial

---

<div align="center">

**EcoTrack** — Proyecto académico de clasificación de residuos sólidos

![Made with Python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)
![Made with Django](https://img.shields.io/badge/Made%20with-Django-092E20.svg)

</div>
