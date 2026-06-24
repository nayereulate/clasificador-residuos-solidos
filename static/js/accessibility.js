/**
 * EcoTrack Accesibilidad v4
 * - TTS persistente entre páginas
 * - Micrófono persistente entre páginas (no se apaga al navegar)
 * - Ayuda contextual: solo dice los comandos de la página actual
 */

/* ══════════════════════════════════════════════════════════════
   HELPERS GLOBALES
══════════════════════════════════════════════════════════════ */

function _ind(msg, ms = 2800) {
    const el = document.getElementById('ecoVozIndicator');
    const tx = document.getElementById('ecoVozTexto');
    if (!el || !tx) return;
    tx.textContent = msg;
    el.classList.add('visible');
    clearTimeout(_ind._t);
    _ind._t = setTimeout(() => el.classList.remove('visible'), ms);
}
_ind._t = null;

function _deshBtn(id, titulo) {
    const b = document.getElementById(id);
    if (!b) return;
    b.disabled = true; b.title = titulo;
    b.style.opacity = '0.4'; b.style.cursor = 'not-allowed';
}

function _clic(id) {
    const el = document.getElementById(id);
    if (el && !el.disabled) { el.click(); return true; }
    return false;
}

function _clicSel(sel) {
    const el = document.querySelector(sel);
    if (el) { el.click(); return true; } return false;
}

function _ir(url) { window.location.href = url; }

function _tab(target) {
    const b = document.querySelector(`[data-bs-target="${target}"]`);
    if (b) { b.click(); return true; } return false;
}

function _ruta() { return window.location.pathname; }

function _enRuta(frag) { return _ruta().includes(frag); }

function _scrollA(sel) {
    const el = document.querySelector(sel);
    if (el) { el.scrollIntoView({ behavior: 'smooth', block: 'start' }); return true; } return false;
}

function _cerrarModal() {
    const m = document.querySelector('.modal.show');
    if (m) { bootstrap.Modal.getInstance(m)?.hide(); return true; } return false;
}

function _enviarForm(sel = 'form') {
    const f = document.querySelector(sel);
    if (f) { f.requestSubmit ? f.requestSubmit() : f.submit(); return true; } return false;
}

function _norm(t) {
    return t.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}


/* ══════════════════════════════════════════════════════════════
   TTS
══════════════════════════════════════════════════════════════ */
const EcoVoz = {
    activo: false, voz: null, velocidad: 1.0, volumen: 1.0, disponible: false,

    init() {
        if (!('speechSynthesis' in window)) { _deshBtn('btnTTS', 'Lector no disponible'); return; }
        this.disponible = true;
        this.activo = localStorage.getItem('ecotrack-tts') === 'true';
        const cv = () => {
            const vs = window.speechSynthesis.getVoices();
            this.voz = vs.find(v => v.lang.startsWith('es')) || vs[0] || null;
        };
        cv();
        if (window.speechSynthesis.onvoiceschanged !== undefined)
            window.speechSynthesis.onvoiceschanged = cv;
        this._actualizarBoton();
        if (this.activo) setTimeout(() => this._leerTitulo(), 800);
    },

    hablar(texto, interrumpir = true) {
        if (!this.disponible || !this.activo || !texto?.trim()) return;
        const s = texto.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
        if (interrumpir) window.speechSynthesis.cancel();
        const u = new SpeechSynthesisUtterance(s);
        u.lang = 'es-ES'; u.rate = this.velocidad; u.volume = this.volumen;
        if (this.voz) u.voice = this.voz;
        window.speechSynthesis.speak(u);
    },

    _leerTitulo() {
        const h = document.querySelector('h1,.topbar-title');
        if (h) this.hablar('Página: ' + h.innerText);
    },

    leerPagina() {
        if (!this.disponible) { _ind('TTS no disponible'); return; }
        if (!this.activo) { _ind('Activa el lector primero (Alt+V)'); return; }
        window.speechSynthesis.cancel();
        const partes = [];
        const t = document.querySelector('.topbar-title,h1');
        if (t) partes.push('Página: ' + t.innerText.trim());
        const main = document.getElementById('main-content') || document.querySelector('main');
        if (main) {
            const txt = Array.from(main.querySelectorAll(
                'h1,h2,h3,h4,p,td,th,label,.stat-value,.stat-label,.alert,li'
            )).map(el => el.innerText.trim()).filter(Boolean).join('. ');
            if (txt) partes.push(txt);
        }
        this.hablar(partes.join('. ') || 'Sin contenido.', true);
        _ind('Leyendo página...');
    },

    toggle() {
        if (!this.disponible) return;
        this.activo = !this.activo;
        localStorage.setItem('ecotrack-tts', String(this.activo));
        this._actualizarBoton();
        if (this.activo) this.hablar('Lector activado.');
        else { window.speechSynthesis.cancel(); _ind('Lector desactivado'); }
    },

    _actualizarBoton() {
        const b = document.getElementById('btnTTS');
        if (!b) return;
        b.classList.toggle('activo', this.activo);
        b.setAttribute('aria-pressed', String(this.activo));
        b.title = this.activo ? 'Desactivar lector (Alt+V)' : 'Activar lector (Alt+V)';
    },
};


/* ══════════════════════════════════════════════════════════════
   COMANDOS DE VOZ
══════════════════════════════════════════════════════════════ */
const EcoComandos = {
    reconocimiento: null,
    activo:         false,
    disponible:     false,

    /**
     * Comandos agrupados por contexto de página.
     * Cada entrada: { frases: [...], accion: fn, paginas: ['*'] | ['/ruta'] }
     * paginas: ['*']   → disponible en todas las páginas
     *         ['/administracion'] → solo en esa ruta (usa includes)
     */
    COMANDOS: [

        // ── CÁMARA (solo en /) ──────────────────────────────────────────────
        { paginas: ['/'],
          frases: ['iniciar camara','iniciar cámara','encender camara','encender cámara','abrir camara'],
          accion: () => _clic('btn-iniciar-camara') },
        { paginas: ['/'],
          frases: ['detener camara','detener cámara','apagar camara','apagar cámara','parar camara'],
          accion: () => _clic('btn-detener-camara') },
        { paginas: ['/'],
          frases: ['guardar analisis','guardar análisis','guardar frame','guardar foto','guardar captura'],
          accion: () => _clic('btn-guardar-analisis') },
        { paginas: ['/'],
          frases: ['auto guardado','auto-guardado','guardado automatico','guardado automático'],
          accion: () => _clic('btn-autosave-toggle') },
        { paginas: ['/'],
          frases: ['metricas','métricas','debug','panel debug'],
          accion: () => _clic('btn-debug-toggle') },
        { paginas: ['/'],
          frases: ['tab camara','tab cámara','pestaña camara','pestaña cámara','ir a camara','modo camara'],
          accion: () => _tab('#tab-cam') },
        { paginas: ['/'],
          frases: ['tab imagen','pestaña imagen','ir a imagen','modo imagen'],
          accion: () => _tab('#tab-img') },
        { paginas: ['/'],
          frases: ['tab video','pestaña video','ir a video','modo video'],
          accion: () => _tab('#tab-video') },
        { paginas: ['/'],
          frases: ['analizar','analizar imagen','detectar','detectar residuos'],
          accion: () => { const b = document.querySelector('#form-img [type="submit"]'); b?.click(); } },

        // ── ADMINISTRACIÓN ──────────────────────────────────────────────────
        { paginas: ['/administracion'],
          frases: ['procesar pendientes','procesar todos','procesar residuos'],
          accion: () => _clic('btn-proc-todos') || _clicSel('button.btn-warning') },
        { paginas: ['/administracion'],
          frases: ['ver aceptados','residuos aceptados','base de datos'],
          accion: () => _ir('/administracion/aceptados/') },
        { paginas: ['/administracion'],
          frases: ['exportar json'], accion: () => _clicSel('a[href*="exportar/json"]') },
        { paginas: ['/administracion'],
          frases: ['exportar xml'],  accion: () => _clicSel('a[href*="exportar/xml"]') },
        { paginas: ['/administracion'],
          frases: ['exportar txt'],  accion: () => _clicSel('a[href*="exportar/txt"]') },
        { paginas: ['/administracion'],
          frases: ['exportar','descargar'], accion: () => _clicSel('.dropdown-toggle') },
        { paginas: ['/administracion'],
          frases: ['eliminar sin clasificar'],
          accion: () => _clicSel('button.btn-outline-danger') },

        // ── CONTABILIDAD – DASHBOARD ────────────────────────────────────────
        { paginas: ['/contabilidad/'],
          frases: ['nuevo ingreso','crear ingreso','agregar ingreso'],
          accion: () => _ir('/contabilidad/ingresos/crear/') },
        { paginas: ['/contabilidad/'],
          frases: ['nuevo egreso','crear egreso','agregar egreso'],
          accion: () => _ir('/contabilidad/egresos/crear/') },
        { paginas: ['/contabilidad/'],
          frases: ['ver ingresos','lista ingresos'],
          accion: () => _ir('/contabilidad/ingresos/') },
        { paginas: ['/contabilidad/'],
          frases: ['ver egresos','lista egresos'],
          accion: () => _ir('/contabilidad/egresos/') },
        { paginas: ['/contabilidad/'],
          frases: ['proyeccion','proyección','ver proyeccion'],
          accion: () => _ir('/contabilidad/proyeccion/') },
        { paginas: ['/contabilidad/'],
          frases: ['precios','precios por material','gestionar precios'],
          accion: () => _ir('/contabilidad/precios/') },

        // ── CONTABILIDAD – PROYECCIÓN ───────────────────────────────────────
        { paginas: ['/contabilidad/proyeccion'],
          frases: ['calcular tanda','calcular','calcular proyeccion'],
          accion: () => _clicSel('button.btn-success[type="submit"]') },
        { paginas: ['/contabilidad/proyeccion'],
          frases: ['total historico','ver todo','quitar fechas','limpiar fechas'],
          accion: () => _ir('/contabilidad/proyeccion/') },

        // ── CONTABILIDAD – PRECIOS ──────────────────────────────────────────
        { paginas: ['/contabilidad/precios'],
          frases: ['guardar precio','agregar precio','nuevo precio'],
          accion: () => _clicSel('button.btn-success[type="submit"]') },

        // ── REPORTES ────────────────────────────────────────────────────────
        { paginas: ['/reportes'],
          frases: ['exportar excel','descargar excel'],
          accion: () => _ir('/reportes/excel/') },
        { paginas: ['/reportes'],
          frases: ['imprimir reporte','imprimir'],
          accion: () => _ir('/reportes/imprimir/') },

        // ── PERFIL ──────────────────────────────────────────────────────────
        { paginas: ['/perfil'],
          frases: ['cambiar contrasena','cambiar contraseña','cambiar password'],
          accion: () => _ir('/perfil/password/') },
        { paginas: ['/perfil'],
          frases: ['guardar cambios','guardar perfil'],
          accion: () => _enviarForm('form') },

        // ── USUARIOS ────────────────────────────────────────────────────────
        { paginas: ['/usuarios'],
          frases: ['nuevo usuario','crear usuario','agregar usuario'],
          accion: () => _ir('/usuarios/crear/') },

        // ── ACCIONES GENÉRICAS (filtros, formularios, modales) ──────────────
        { paginas: ['*'],
          frases: ['aplicar filtro','filtrar','buscar'],
          accion: () => _clicSel('button.btn-success[type="submit"],button.btn-primary[type="submit"]') },
        { paginas: ['*'],
          frases: ['limpiar filtros','limpiar filtro','quitar filtros','sin filtro'],
          accion: () => _clicSel('a.btn-outline-secondary[href*="?"]') || _clicSel('a.btn-outline-secondary') },
        { paginas: ['*'],
          frases: ['guardar','guardar cambios','confirmar'],
          accion: () => _clicSel('button.btn-success[type="submit"]') },
        { paginas: ['*'],
          frases: ['cancelar','volver','atras','atrás'],
          accion: () => history.back() },
        { paginas: ['*'],
          frases: ['cerrar modal','cerrar ventana','cerrar dialogo','cerrar'],
          accion: () => _cerrarModal() },
        { paginas: ['*'],
          frases: ['cerrar sesion','cerrar sesión','salir','logout'],
          accion: () => _clicSel('button[type="submit"].text-danger,form[action*="logout"] button') },

        // ── NAVEGACIÓN ───────────────────────────────────────────────────────
        { paginas: ['*'],
          frases: ['inicio','deteccion ia','detección ia','ir al inicio','volver al inicio'],
          accion: () => _ir('/') },
        { paginas: ['*'],
          frases: ['administracion','administración'],
          accion: () => _ir('/administracion/') },
        { paginas: ['*'],
          frases: ['reportes'],
          accion: () => _ir('/reportes/') },
        { paginas: ['*'],
          frases: ['historial'],
          accion: () => _ir('/historial/') },
        { paginas: ['*'],
          frases: ['contabilidad'],
          accion: () => _ir('/contabilidad/') },
        { paginas: ['*'],
          frases: ['perfil','mi perfil'],
          accion: () => _ir('/perfil/') },
        { paginas: ['*'],
          frases: ['usuarios','gestionar usuarios'],
          accion: () => _ir('/usuarios/') },

        // ── SCROLL ───────────────────────────────────────────────────────────
        { paginas: ['*'], frases: ['subir'],
          accion: () => window.scrollBy({ top: -300, behavior: 'smooth' }) },
        { paginas: ['*'], frases: ['bajar'],
          accion: () => window.scrollBy({ top: 300, behavior: 'smooth' }) },
        { paginas: ['*'], frases: ['ir arriba','arriba','inicio de pagina'],
          accion: () => window.scrollTo({ top: 0, behavior: 'smooth' }) },
        { paginas: ['*'], frases: ['ir abajo','abajo','final de pagina'],
          accion: () => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }) },
        { paginas: ['*'], frases: ['ir a la tabla','ver tabla'],
          accion: () => _scrollA('table,.table-responsive') },
        { paginas: ['*'], frases: ['ir al grafico','ver grafico'],
          accion: () => _scrollA('canvas,.chart-wrap') },
        { paginas: ['*'], frases: ['ir al formulario','ver formulario'],
          accion: () => _scrollA('form') },

        // ── TEMA ─────────────────────────────────────────────────────────────
        { paginas: ['*'], frases: ['modo oscuro','tema oscuro'],
          accion: () => { if (document.documentElement.getAttribute('data-theme') !== 'dark') _clic('theme-toggle'); } },
        { paginas: ['*'], frases: ['modo claro','tema claro'],
          accion: () => { if (document.documentElement.getAttribute('data-theme') !== 'light') _clic('theme-toggle'); } },
        { paginas: ['*'], frases: ['cambiar tema','alternar tema'],
          accion: () => _clic('theme-toggle') },

        // ── LECTOR TTS ────────────────────────────────────────────────────────
        { paginas: ['*'], frases: ['leer pagina','leer página','leer todo','leer'],
          accion: () => EcoVoz.leerPagina() },
        { paginas: ['*'], frases: ['silencio','silenciar','parar audio','para'],
          accion: () => window.speechSynthesis.cancel() },
        { paginas: ['*'], frases: ['activar lector'],
          accion: () => { if (!EcoVoz.activo) EcoVoz.toggle(); } },
        { paginas: ['*'], frases: ['desactivar lector'],
          accion: () => { if (EcoVoz.activo)  EcoVoz.toggle(); } },

        // ── AYUDA ─────────────────────────────────────────────────────────────
        { paginas: ['*'], frases: ['ayuda','comandos','que puedo decir'],
          accion: () => EcoComandos._leerAyuda() },
    ],

    // ── Comandos activos para la ruta actual ─────────────────────────────────
    _comandosActivos() {
        const ruta = _ruta();
        return this.COMANDOS.filter(c =>
            c.paginas.includes('*') ||
            c.paginas.some(p => ruta === p || ruta.startsWith(p))
        );
    },

    // ────────────────────────────────────────────────────────────────────────
    init() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition || null;
        if (!SR) { _deshBtn('btnMicrofono', 'Comandos de voz no disponibles'); return; }

        this.disponible = true;
        this.reconocimiento = new SR();
        this.reconocimiento.lang            = 'es-ES';
        this.reconocimiento.interimResults  = false;
        this.reconocimiento.maxAlternatives = 5;
        this.reconocimiento.continuous      = false;

        this.reconocimiento.onresult = (event) => {
            const alts = Array.from(event.results[0]).map(a => a.transcript.toLowerCase().trim());
            for (const t of alts) { if (this.procesar(t)) break; }
        };
        this.reconocimiento.onerror = (event) => {
            if (['not-allowed','service-not-allowed'].includes(event.error)) {
                this._desactivar(); _ind('Permiso de micrófono denegado');
            } else if (event.error !== 'no-speech' && this.activo) {
                setTimeout(() => this._iniciarEscucha(), 500);
            }
        };
        this.reconocimiento.onend = () => {
            if (this.activo) setTimeout(() => this._iniciarEscucha(), 250);
        };

        // ── Persistencia entre páginas ────────────────────────────────────
        if (localStorage.getItem('ecotrack-mic') === 'true') {
            // Reactivar tras recarga sin molestar al usuario con TTS
            setTimeout(() => {
                this.activo = true;
                this._actualizarBoton();
                this._iniciarEscucha();
                _ind('Micrófono activo', 1500);
            }, 600);
        }
    },

    toggle() { if (this.disponible) this.activo ? this._desactivar() : this._activar(); },

    _activar() {
        this.activo = true;
        localStorage.setItem('ecotrack-mic', 'true');
        this._actualizarBoton();
        this._iniciarEscucha();
        _ind('Escuchando comandos…', 99999);
        EcoVoz.hablar('Comandos activados. Di ayuda para ver los disponibles.');
    },

    _desactivar() {
        this.activo = false;
        localStorage.setItem('ecotrack-mic', 'false');
        try { this.reconocimiento.stop(); } catch (_) {}
        this._actualizarBoton();
        const el = document.getElementById('ecoVozIndicator');
        if (el) el.classList.remove('visible');
        EcoVoz.hablar('Comandos desactivados.');
    },

    _iniciarEscucha() {
        if (!this.activo) return;
        try { this.reconocimiento.start(); } catch (_) {}
    },

    /**
     * Matching: exacto primero, luego inclusión.
     * Solo evalúa comandos activos para la ruta actual.
     */
    procesar(texto) {
        const tn = _norm(texto);
        const activos = this._comandosActivos();

        for (const cmd of activos)
            for (const f of cmd.frases)
                if (tn === _norm(f)) { this._ejecutar(f, cmd.accion); return true; }

        for (const cmd of activos)
            for (const f of cmd.frases)
                if (tn.includes(_norm(f))) { this._ejecutar(f, cmd.accion); return true; }

        _ind('"' + texto + '" — no reconocido');
        return false;
    },

    _ejecutar(clave, accion) {
        _ind('▶ ' + clave);
        EcoVoz.hablar(clave, false);
        try { accion(); } catch (e) { console.warn('EcoComandos:', e); }
    },

    _actualizarBoton() {
        const b = document.getElementById('btnMicrofono');
        if (!b) return;
        b.classList.toggle('activo', this.activo);
        b.setAttribute('aria-pressed', String(this.activo));
        b.title = this.activo ? 'Desactivar comandos (Alt+M)' : 'Activar comandos (Alt+M)';
    },

    /** Lee SOLO los comandos disponibles en la página actual */
    _leerAyuda() {
        const ruta  = _ruta();
        const activos = this._comandosActivos();

        // Separar comandos de página específica de los genéricos
        const especificos = activos.filter(c => !c.paginas.includes('*'));
        const genericos   = activos.filter(c =>  c.paginas.includes('*'));

        const lista = (cmds) => cmds.map(c => c.frases[0]).join(', ');

        let texto = '';

        if (especificos.length)
            texto += 'En esta página puedes decir: ' + lista(especificos) + '. ';

        // Comandos genéricos siempre disponibles (se resume para no ser largo)
        texto +=
            'Siempre disponibles: ' +
            'inicio, administración, reportes, historial, contabilidad, perfil, ' +
            'subir, bajar, leer página, silencio, cambiar tema, ayuda, cerrar sesión.';

        EcoVoz.hablar(texto, true);
    },
};


/* ══════════════════════════════════════════════════════════════
   TECLAS DE ACCESO RÁPIDO
══════════════════════════════════════════════════════════════ */
document.addEventListener('keydown', (e) => {
    if (!e.altKey) return;
    switch (e.key.toLowerCase()) {
        case 'v': e.preventDefault(); EcoVoz.toggle();       break;
        case 'm': e.preventDefault(); EcoComandos.toggle();  break;
        case 'r': e.preventDefault(); EcoVoz.leerPagina();   break;
        case 's':
            e.preventDefault();
            if ('speechSynthesis' in window) window.speechSynthesis.cancel();
            _ind('Audio silenciado');
            break;
    }
});


/* ══════════════════════════════════════════════════════════════
   AUTO-LECTURA
══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.sb-link').forEach(link => {
        link.addEventListener('mouseenter', () => {
            if (EcoVoz.activo) EcoVoz.hablar(link.innerText.trim(), false);
        });
    });

    document.querySelectorAll('.toast-body,.alert').forEach(el => {
        if (EcoVoz.activo) EcoVoz.hablar(el.innerText.trim());
    });

    // Leer cambios del estado de cámara automáticamente
    const camStatus = document.getElementById('camera-status');
    if (camStatus) {
        new MutationObserver(() => {
            if (EcoVoz.activo) EcoVoz.hablar(camStatus.textContent.trim(), false);
        }).observe(camStatus, { childList: true, characterData: true, subtree: true });
    }
});
