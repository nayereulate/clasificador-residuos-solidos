/**
 * EcoTrack Accesibilidad — TTS + Comandos de Voz
 * Usa Web Speech API nativa del navegador (sin dependencias externas).
 * Degrada silenciosamente si el navegador no soporta las APIs.
 */

/* ══════════════════════════════════════════════════════════════
   MÓDULO TTS  (Text-To-Speech)
══════════════════════════════════════════════════════════════ */
const EcoVoz = {
    activo: false,
    voz: null,
    velocidad: 1.0,
    volumen: 1.0,
    disponible: false,

    init() {
        if (!('speechSynthesis' in window)) {
            // API no disponible: deshabilitar botón silenciosamente
            const btn = document.getElementById('btnTTS');
            if (btn) {
                btn.disabled = true;
                btn.title = 'Lector de pantalla no disponible en este navegador';
                btn.style.opacity = '0.4';
                btn.style.cursor = 'not-allowed';
            }
            return;
        }

        this.disponible = true;

        // Recuperar preferencia guardada
        this.activo = localStorage.getItem('ecotrack-tts') === 'true';

        // Cargar voces (puede ser asíncrono en algunos navegadores)
        const cargarVoces = () => {
            const voces = window.speechSynthesis.getVoices();
            // Preferir voz en español
            this.voz = voces.find(v => v.lang.startsWith('es')) || voces[0] || null;
        };

        cargarVoces();
        if (window.speechSynthesis.onvoiceschanged !== undefined) {
            window.speechSynthesis.onvoiceschanged = cargarVoces;
        }

        // Actualizar UI según preferencia guardada
        this._actualizarBoton();

        // Si estaba activo, anunciar bienvenida
        if (this.activo) {
            setTimeout(() => this._leerTituloPagina(), 800);
        }
    },

    /**
     * Limpia etiquetas HTML y lee el texto con SpeechSynthesis.
     * @param {string} texto - Texto a leer (puede contener HTML).
     * @param {boolean} interrumpir - Si true, cancela la locución actual antes de hablar.
     */
    hablar(texto, interrumpir = true) {
        if (!this.disponible || !this.activo) return;
        if (!texto || texto.trim() === '') return;

        // Eliminar etiquetas HTML
        const sinHtml = texto.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

        if (interrumpir) window.speechSynthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(sinHtml);
        utterance.lang = 'es-ES';
        utterance.rate = this.velocidad;
        utterance.volume = this.volumen;
        if (this.voz) utterance.voice = this.voz;

        window.speechSynthesis.speak(utterance);
    },

    /** Lee el h1 principal de la página */
    _leerTituloPagina() {
        if (!this.disponible || !this.activo) return;
        const h1 = document.querySelector('h1, .topbar-title');
        if (h1) this.hablar('Página: ' + h1.innerText);
    },

    /** Lee título + contenido principal */
    leerPagina() {
        if (!this.disponible) {
            this._mostrarIndicador('TTS no disponible en este navegador');
            return;
        }
        if (!this.activo) {
            this._mostrarIndicador('Activa el lector de pantalla primero (Alt+V)');
            return;
        }

        window.speechSynthesis.cancel();

        const partes = [];

        // Título de la página (topbar o h1)
        const titulo = document.querySelector('.topbar-title, h1');
        if (titulo) partes.push('Página: ' + titulo.innerText.trim());

        // Contenido principal
        const main = document.getElementById('main-content') || document.querySelector('main');
        if (main) {
            // Obtener texto visible ignorando scripts/styles
            const textoMain = Array.from(main.querySelectorAll(
                'h1, h2, h3, h4, p, td, th, label, .stat-value, .stat-label, .alert, li'
            ))
                .map(el => el.innerText.trim())
                .filter(t => t.length > 0)
                .join('. ');
            if (textoMain) partes.push(textoMain);
        }

        if (partes.length === 0) {
            partes.push('No se encontró contenido para leer en esta página.');
        }

        this.hablar(partes.join('. '), true);
        this._mostrarIndicador('Leyendo página...');
    },

    /** Activa o desactiva el TTS */
    toggle() {
        if (!this.disponible) return;

        this.activo = !this.activo;
        localStorage.setItem('ecotrack-tts', String(this.activo));
        this._actualizarBoton();

        if (this.activo) {
            this.hablar('Lector de pantalla activado. ' +
                'Usa Alt+R para leer la página completa, Alt+S para silenciar.');
        } else {
            window.speechSynthesis.cancel();
            this._mostrarIndicador('Lector desactivado');
        }
    },

    /** Sincroniza el aspecto visual del botón con el estado activo/inactivo */
    _actualizarBoton() {
        const btn = document.getElementById('btnTTS');
        if (!btn) return;
        if (this.activo) {
            btn.classList.add('activo');
            btn.setAttribute('aria-pressed', 'true');
            btn.title = 'Desactivar lector de pantalla (Alt+V)';
        } else {
            btn.classList.remove('activo');
            btn.setAttribute('aria-pressed', 'false');
            btn.title = 'Activar lector de pantalla (Alt+V)';
        }
    },

    /** Muestra brevemente el indicador flotante con un mensaje */
    _mostrarIndicador(msg) {
        const indicator = document.getElementById('ecoVozIndicator');
        const textoEl   = document.getElementById('ecoVozTexto');
        if (!indicator || !textoEl) return;
        textoEl.textContent = msg;
        indicator.classList.add('visible');
        clearTimeout(EcoVoz._indicatorTimer);
        EcoVoz._indicatorTimer = setTimeout(() => {
            indicator.classList.remove('visible');
        }, 2800);
    },

    _indicatorTimer: null,
};


/* ══════════════════════════════════════════════════════════════
   MÓDULO COMANDOS DE VOZ  (SpeechRecognition)
══════════════════════════════════════════════════════════════ */
const EcoComandos = {
    reconocimiento: null,
    activo: false,
    disponible: false,

    /** Mapa de frases → acciones */
    COMANDOS: {
        'inicio':          () => { window.location.href = '/'; },
        'inicio detección':() => { window.location.href = '/'; },
        'administración':  () => { window.location.href = '/administracion/'; },
        'administracion':  () => { window.location.href = '/administracion/'; },
        'reportes':        () => { window.location.href = '/reportes/'; },
        'historial':       () => { window.location.href = '/historial/'; },
        'rutas':           () => { window.location.href = '/recoleccion/'; },
        'recolección':     () => { window.location.href = '/recoleccion/'; },
        'recoleccion':     () => { window.location.href = '/recoleccion/'; },
        'contabilidad':    () => { window.location.href = '/contabilidad/'; },
        'leer página':     () => { EcoVoz.leerPagina(); },
        'leer pagina':     () => { EcoVoz.leerPagina(); },
        'leer':            () => { EcoVoz.leerPagina(); },
        'silencio':        () => { window.speechSynthesis.cancel(); },
        'silenciar':       () => { window.speechSynthesis.cancel(); },
        'parar':           () => { window.speechSynthesis.cancel(); },
        'detener':         () => { window.speechSynthesis.cancel(); },
        'activar lector':  () => { if (!EcoVoz.activo) EcoVoz.toggle(); },
        'desactivar lector': () => { if (EcoVoz.activo) EcoVoz.toggle(); },
        'subir':           () => { window.scrollBy({ top: -200, behavior: 'smooth' }); },
        'bajar':           () => { window.scrollBy({ top: 200, behavior: 'smooth' }); },
        'arriba':          () => { window.scrollTo({ top: 0, behavior: 'smooth' }); },
        'abajo':           () => { window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); },
        'ayuda':           () => { EcoComandos._leerAyuda(); },
    },

    init() {
        const SpeechRecognition =
            window.SpeechRecognition || window.webkitSpeechRecognition || null;

        if (!SpeechRecognition) {
            // API no disponible: deshabilitar botón silenciosamente
            const btn = document.getElementById('btnMicrofono');
            if (btn) {
                btn.disabled = true;
                btn.title = 'Comandos de voz no disponibles en este navegador';
                btn.style.opacity = '0.4';
                btn.style.cursor = 'not-allowed';
            }
            return;
        }

        this.disponible = true;
        this.reconocimiento = new SpeechRecognition();
        this.reconocimiento.lang = 'es-ES';
        this.reconocimiento.interimResults = false;
        this.reconocimiento.maxAlternatives = 3;
        this.reconocimiento.continuous = false; // Se reinicia manualmente tras cada resultado

        this.reconocimiento.onresult = (event) => {
            const alternativas = Array.from(event.results[0])
                .map(alt => alt.transcript.toLowerCase().trim());
            // Intentar con cada alternativa hasta encontrar un comando
            for (const texto of alternativas) {
                if (this.procesar(texto)) break;
            }
        };

        this.reconocimiento.onerror = (event) => {
            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                this._desactivar();
                EcoVoz._mostrarIndicador('Permiso de micrófono denegado');
            } else if (event.error !== 'no-speech') {
                // Reiniciar tras error no crítico si sigue activo
                if (this.activo) setTimeout(() => this._iniciarEscucha(), 500);
            }
        };

        this.reconocimiento.onend = () => {
            // Reiniciar escucha si sigue activo (modo continuo manual)
            if (this.activo) setTimeout(() => this._iniciarEscucha(), 250);
        };
    },

    toggle() {
        if (!this.disponible) return;

        if (this.activo) {
            this._desactivar();
        } else {
            this._activar();
        }
    },

    _activar() {
        this.activo = true;
        this._actualizarBoton();
        this._iniciarEscucha();

        const indicator = document.getElementById('ecoVozIndicator');
        const textoEl   = document.getElementById('ecoVozTexto');
        if (indicator && textoEl) {
            textoEl.textContent = 'Escuchando comandos...';
            indicator.classList.add('visible');
        }

        EcoVoz.hablar('Comandos de voz activados. Di "ayuda" para escuchar los comandos disponibles.');
    },

    _desactivar() {
        this.activo = false;
        try { this.reconocimiento.stop(); } catch (_) { /* ignora */ }
        this._actualizarBoton();

        const indicator = document.getElementById('ecoVozIndicator');
        if (indicator) indicator.classList.remove('visible');

        EcoVoz.hablar('Comandos de voz desactivados.');
    },

    _iniciarEscucha() {
        if (!this.activo) return;
        try { this.reconocimiento.start(); } catch (_) { /* ignora si ya estaba iniciado */ }
    },

    /**
     * Busca y ejecuta el comando que mejor coincida con el texto reconocido.
     * @param {string} texto - Texto en minúsculas.
     * @returns {boolean} true si se encontró y ejecutó algún comando.
     */
    procesar(texto) {
        // Buscar coincidencia exacta primero
        if (this.COMANDOS[texto]) {
            this._ejecutar(texto, this.COMANDOS[texto]);
            return true;
        }

        // Buscar si el texto reconocido contiene alguna clave de comando
        for (const [clave, accion] of Object.entries(this.COMANDOS)) {
            if (texto.includes(clave)) {
                this._ejecutar(clave, accion);
                return true;
            }
        }

        // No se reconoció ningún comando — mostrar feedback discreto
        EcoVoz._mostrarIndicador('No reconocido: "' + texto + '"');
        return false;
    },

    _ejecutar(clave, accion) {
        EcoVoz._mostrarIndicador('Comando: ' + clave);
        EcoVoz.hablar('Ejecutando: ' + clave, false);
        try { accion(); } catch (e) { console.warn('EcoComandos: error ejecutando comando', e); }
    },

    _actualizarBoton() {
        const btn = document.getElementById('btnMicrofono');
        if (!btn) return;
        if (this.activo) {
            btn.classList.add('activo');
            btn.setAttribute('aria-pressed', 'true');
            btn.title = 'Desactivar comandos de voz (Alt+M)';
        } else {
            btn.classList.remove('activo');
            btn.setAttribute('aria-pressed', 'false');
            btn.title = 'Activar comandos de voz (Alt+M)';
        }
    },

    _leerAyuda() {
        const ayuda =
            'Comandos disponibles: ' +
            'inicio, administración, reportes, historial, rutas, contabilidad, ' +
            'leer página, silencio, subir, bajar, arriba, abajo, ' +
            'activar lector, desactivar lector.';
        EcoVoz.hablar(ayuda, true);
    },
};


/* ══════════════════════════════════════════════════════════════
   TECLAS DE ACCESO RÁPIDO
══════════════════════════════════════════════════════════════ */
document.addEventListener('keydown', (e) => {
    if (!e.altKey) return;

    switch (e.key.toLowerCase()) {
        case 'v':
            e.preventDefault();
            EcoVoz.toggle();
            break;
        case 'm':
            e.preventDefault();
            EcoComandos.toggle();
            break;
        case 'r':
            e.preventDefault();
            EcoVoz.leerPagina();
            break;
        case 's':
            e.preventDefault();
            if ('speechSynthesis' in window) window.speechSynthesis.cancel();
            EcoVoz._mostrarIndicador('Audio silenciado');
            break;
    }
});


/* ══════════════════════════════════════════════════════════════
   AUTO-LECTURA: hover en links del sidebar
══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
    // Leer links del sidebar al hacer hover cuando TTS está activo
    document.querySelectorAll('.sb-link').forEach(link => {
        link.addEventListener('mouseenter', () => {
            if (EcoVoz.activo && EcoVoz.disponible) {
                EcoVoz.hablar(link.innerText.trim(), false);
            }
        });
    });

    // Leer alerts/mensajes Django automáticamente si TTS activo
    // (esto también se invoca desde el inline script en base.html)
    document.querySelectorAll('.toast-body').forEach(el => {
        if (EcoVoz.activo) EcoVoz.hablar(el.innerText.trim());
    });

    // Auto-leer resultados de análisis si existen en la página
    const resultadoAnalisis = document.querySelector(
        '[data-accessibility-announce], .resultado-clasificacion, #resultado-ia'
    );
    if (resultadoAnalisis && EcoVoz.activo) {
        setTimeout(() => EcoVoz.hablar(resultadoAnalisis.innerText.trim()), 1200);
    }
});
