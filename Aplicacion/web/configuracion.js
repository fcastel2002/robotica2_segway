// Configuración del Segway y comunicación con la aplicación puente del joystick (:8001).
// Se apoya en app.js (enviar(), mensajes, alRecibir) y en banco.js (ultima, ultimaLlegada, DATO_VIEJO_MS, mostrar()).
'use strict';

// ---------- Joystick (aplicación puente) ----------
const PERIODO_JOY_VIVO_MS = 60;  // 16-20 Hz para respuesta instantánea de botones y sticks
const PERIODO_JOY_MS = 1500;     // antes de la primera respuesta
const PERIODO_JOY_FALLA_MS = 5000;
const ESPERA_JOY_MS = 1200;
let joy = null;               // última respuesta de la aplicación
let joyLlegada = null;        // performance.now() de esa respuesta
let joyError = null;          // por qué falló la última consulta; null si respondió
let consultandoJoy = false;

const direccionJoy = () => $('joy-direccion').value.trim().replace(/\/+$/, '');

function mayorMag(...vals) {
  let m = 0;
  for (const v of vals) if (Number.isFinite(v) && Math.abs(v) > Math.abs(m)) m = v;
  return m;
}

function leerGamepadNavegador() {
  if (!('getGamepads' in navigator)) return null;
  const gps = navigator.getGamepads?.() || [];
  const gp = gps.find((g) => g && g.connected);
  if (!gp) return null;

  const esStandard = gp.mapping === 'standard';
  const lx = gp.axes[0] ?? 0;
  const ly = -(gp.axes[1] ?? 0);
  const rx = gp.axes[2] ?? 0;
  const ry = esStandard
    ? -(gp.axes[3] ?? 0)
    : (gp.axes.length > 5 && Math.abs(gp.axes[5] ?? 0) > 0.08 ? -(gp.axes[5] ?? 0) : -(gp.axes[3] ?? 0));

  const btn = (i) => Boolean(gp.buttons[i]?.pressed || (gp.buttons[i]?.value ?? 0) > 0.5);
  let up = btn(12), down = btn(13), left = btn(14), right = btn(15);
  let dpadY = (up ? 1 : 0) - (down ? 1 : 0);
  let dpadX = (right ? 1 : 0) - (left ? 1 : 0);

  // Respaldo para cruceta en axes[9] (POV hat en mapeo DirectInput sin 'standard')
  if (dpadY === 0 && dpadX === 0 && gp.axes.length > 9) {
    const pov = gp.axes[9];
    if (Number.isFinite(pov) && pov >= -1.05 && pov <= 1.05) {
      const rad = ((pov + 1) * 315 / 2) * (Math.PI / 180);
      const c = Math.cos(rad), s = Math.sin(rad);
      dpadY = c > 0.3 ? 1 : c < -0.3 ? -1 : 0;
      dpadX = s > 0.3 ? 1 : s < -0.3 ? -1 : 0;
      up = dpadY > 0; down = dpadY < 0; left = dpadX < 0; right = dpadX > 0;
    }
  }

  // En mapeo 'standard': 0=X(Equis), 1=O(Círculo), 2=Cuadrado, 3=Triángulo, 4=L1, 5=R1, 6=L2, 7=R2, 8=Share, 9=Options
  // En DirectInput crudo Sony: 0=Cuadrado, 1=X(Equis), 2=O(Círculo), 3=Triángulo, 4=L1, 5=R1, 6=L2, 7=R2, 8=Share, 9=Options
  const botones = esStandard
    ? {
        x: btn(0),
        o: btn(1),
        cuadrado: btn(2),
        triangulo: btn(3),
        l1: btn(4),
        r1: btn(5),
        l2: btn(6),
        r2: btn(7),
        share: btn(8),
        options: btn(9),
        up, down, left, right,
      }
    : {
        cuadrado: btn(0),
        x: btn(1),
        o: btn(2),
        triangulo: btn(3),
        l1: btn(4),
        r1: btn(5),
        l2: btn(6),
        r2: btn(7),
        share: btn(8),
        options: btn(9),
        up, down, left, right,
      };

  return {
    conectado: true,
    nombre: gp.id.replace(/\s*\(.*\)\s*$/, '').trim() || gp.id,
    ejes: {
      lx,
      ly,
      rx,
      ry,
      dpad_x: dpadX,
      dpad_y: dpadY,
    },
    botones,
    avance: mayorMag(ly, dpadY),
    giro: mayorMag(lx, rx, dpadX),
  };
}

async function enviarAccionJoy(accion, valor = null) {
  try {
    const r = await fetch(`${direccionJoy()}/accion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accion, valor }),
      signal: AbortSignal.timeout(ESPERA_JOY_MS),
      cache: 'no-store',
    });
    if (r.ok) {
      joy = await r.json();
      joyLlegada = performance.now();
      joyError = null;
      dibujarJoy();
    }
  } catch {
    // Si el servidor puente aún no respondió, la consulta periódica actualizará el estado
  }
}
window.enviarAccionJoy = enviarAccionJoy;

async function consultarJoy() {
  if (consultandoJoy) return;
  consultandoJoy = true;
  try {
    const gpWeb = leerGamepadNavegador();
    const r = gpWeb
      ? await fetch(`${direccionJoy()}/mando`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(gpWeb),
          signal: AbortSignal.timeout(ESPERA_JOY_MS),
          cache: 'no-store',
        })
      : await fetch(`${direccionJoy()}/estado`, {
          signal: AbortSignal.timeout(ESPERA_JOY_MS),
          cache: 'no-store',
        });
    if (!r.ok) throw new Error(`respondió ${r.status}`);
    joy = await r.json();
    joyLlegada = performance.now();
    joyError = null;
  } catch (err) {
    joyError = err.name === 'TimeoutError' ? 'no contestó a tiempo'
      : err instanceof SyntaxError ? 'la respuesta no es JSON'
      : err.message.startsWith('respondió') ? err.message : 'no responde';
  } finally {
    consultandoJoy = false;
    dibujarJoy();
  }
}

function dibujarJoy() {
  const viva = joyLlegada !== null && !joyError;
  const chip = $('joy-estado');
  chip.textContent = viva ? 'aplicación conectada' : joyError ? 'sin aplicación' : '';
  chip.className = `etiqueta ${viva ? 'activo' : 'alerta'}`;
  $('joy-app').textContent = viva ? 'responde' : joyError ?? '—';
  const j = viva ? joy.joystick : null, r = viva ? joy.robot : null;
  $('joy-mando').textContent = !viva ? '—' : !j ? 'sin dato' : !j.conectado ? 'desconectado'
    : ['conectado', j.nombre, Number.isFinite(j.bateria) ? `batería ${j.bateria} %` : null].filter(Boolean).join(' · ');
  if ($('joy-modo')) {
    $('joy-modo').textContent = !viva ? '—' : (joy.config?.modo_descripcion || joy.config?.modo || '—');
  }
  if ($('joy-servo')) {
    $('joy-servo').textContent = !viva || !joy.servo ? '—' : `${joy.servo.grados}° (rango ${joy.servo.min}°–${joy.servo.max}°)`;
  }
  $('joy-robot').textContent = !viva ? '—' : !r ? 'sin dato' : r.conectado ? `enviando${r.destino ? ` a ${r.destino}` : ''}` : 'sin conexión';
  $('joy-edad').textContent = joyLlegada === null ? '—' : `hace ${Math.round((performance.now() - joyLlegada) / 1000)} s`;
  for (const el of document.querySelectorAll('[data-app]')) mostrar(el, viva ? joy.mando?.[el.dataset.app] : undefined);
  $('joy-aviso').hidden = !joyError;
  $('joy-aviso').textContent = `La aplicación puente ${joyError} en ${direccionJoy()}/estado. `
    + 'Se inicia sola con Aplicacion/puente.py (o con python Aplicacion/joystick.py).';

  window.actualizarVistaMando?.(joy, viva, joyError);
}

$('joy-form').onsubmit = (e) => {
  e.preventDefault();
  recordar('segway.joy_direccion', direccionJoy());
  consultarJoy();
};
$('joy-direccion').value = recuperar('segway.joy_direccion') || $('joy-direccion').value;

let ultimaConsultaJoy = -Infinity;
setInterval(() => {
  if (document.hidden) return;
  const viva = joyLlegada !== null && !joyError;
  const vistaConJoy = !$('configuracion').hidden || ($('mando') && !$('mando').hidden);
  if (!vistaConJoy && (!viva || !leerGamepadNavegador())) return;
  const espera = joyError ? PERIODO_JOY_FALLA_MS : viva ? PERIODO_JOY_VIVO_MS : PERIODO_JOY_MS;
  if (performance.now() - ultimaConsultaJoy < espera) return;
  ultimaConsultaJoy = performance.now();
  consultarJoy();
}, PERIODO_JOY_VIVO_MS);

// ---------- Calibración de la IMU ----------
const G = 9.80665;
const CLAVE_CAL = 'segway.calibracion_imu';
const DURACION_S = { giro: 3, cara: 2, cero: 3 };
const MAX_DESVIO_GIRO = 1.0;  // °/s: más es que se movió (quieto, el MPU-6050 da ~0,1)
const MAX_DESVIO_ACEL = 0.15; // m/s²
const MAX_DESVIO_CERO = 1.0;  // ° de inclinación: se sostiene a mano, con algo de temblor
const ALINEADO = 0.97;        // fracción de |a| sobre un eje para aceptar la cara (≤14° de inclinación)
const EJES = ['x', 'y', 'z'];
const NOMBRE_CARA = { '+x': '+x', '-x': '−x', '+y': '+y', '-y': '−y', '+z': '+z', '-z': '−z' };
const NOMBRE_MEDICION = { giro: 'sesgo del giróscopo', cara: 'posición del acelerómetro', cero: 'cero de inclinación' };

let cal = leerCal();
let medicion = null;
const recientes = [];

function leerCal() {
  try { return { caras: {}, ...JSON.parse(recuperar(CLAVE_CAL)) }; } catch { return { caras: {} }; }
}
function guardarCal() { recordar(CLAVE_CAL, JSON.stringify(cal)); }

alRecibir.push((m) => {
  if (!('ax_ms2' in m)) return;
  const s = { a: [m.ax_ms2, m.ay_ms2, m.az_ms2], g: [m.gx_dps, m.gy_dps, m.gz_dps], theta: m.theta_deg };
  recientes.push(s.g);
  if (recientes.length > 25) recientes.shift();
  if (!medicion) return;
  medicion.muestras.push(s);
  if (performance.now() >= medicion.fin) terminarMedicion();
});

function estadistica(vectores) {
  const n = vectores.length, k = vectores[0].length;
  const media = Array.from({ length: k }, (_, i) => vectores.reduce((s, v) => s + v[i], 0) / n);
  const desvio = media.map((mi, i) => Math.sqrt(vectores.reduce((s, v) => s + (v[i] - mi) ** 2, 0) / n));
  return { media, desvio };
}

function progreso(texto) { $('cal-progreso').textContent = texto; }

function empezarMedicion(tipo, boton) {
  if (medicion) {
    const cancelada = medicion.tipo;
    cortarMedicion();
    if (cancelada === tipo) { progreso('Medición cancelada.'); return; }
  }
  if (performance.now() - ultimaLlegada > DATO_VIEJO_MS) { progreso('No llegan datos del robot.'); return; }
  const ahora = performance.now();
  medicion = { tipo, boton, texto: boton.textContent, inicio: ahora, fin: ahora + DURACION_S[tipo] * 1000, muestras: [] };
  boton.textContent = 'Cancelar';
}

function cortarMedicion() {
  medicion.boton.textContent = medicion.texto;
  medicion = null;
}

function terminarMedicion() {
  const { tipo, muestras } = medicion;
  cortarMedicion();
  if (muestras.length < 10) { progreso('Muy pocas muestras: ¿llega la telemetría?'); return; }
  if (muestras.some((s) => [...s.a, ...s.g].some((v) => !Number.isFinite(v)))) {
    progreso('La IMU no respondió durante la medición (lecturas nan): revisar el I²C y repetir.');
    return;
  }
  const a = estadistica(muestras.map((s) => s.a));
  const g = estadistica(muestras.map((s) => s.g));
  const fecha = new Date().toISOString();

  if (tipo === 'cero') {
    const t = estadistica(muestras.map((s) => [s.theta]));
    if (t.desvio[0] > MAX_DESVIO_CERO) { progreso(`Se movió demasiado (±${t.desvio[0].toFixed(1)}°): repetir más quieto.`); return; }
    cal.cero = { theta: t.media[0], fecha };
    progreso(`Cero de inclinación medido con ${muestras.length} muestras.`);
  } else if (Math.max(...g.desvio) > MAX_DESVIO_GIRO || Math.max(...a.desvio) > MAX_DESVIO_ACEL) {
    progreso('Se movió durante la medición: repetir con el robot quieto y apoyado.');
    return;
  } else if (tipo === 'giro') {
    cal.giro = { sesgo: g.media, desvio: Math.max(...g.desvio), fecha };
    progreso(`Sesgo del giróscopo medido con ${muestras.length} muestras.`);
  } else {
    const modulo = Math.hypot(...a.media);
    const i = a.media.reduce((mejor, v, j) => (Math.abs(v) > Math.abs(a.media[mejor]) ? j : mejor), 0);
    if (modulo < 0.8 * G || modulo > 1.2 * G) {
      progreso(`|a| = ${modulo.toFixed(2)} m/s² no parece la gravedad: revisar la IMU.`);
      return;
    }
    if (Math.abs(a.media[i]) / modulo < ALINEADO) {
      const grados = Math.acos(Math.abs(a.media[i]) / modulo) * 180 / Math.PI;
      progreso(`No está apoyado sobre una cara: el eje más vertical (${EJES[i]}) está inclinado ${grados.toFixed(0)}°. Enderezarlo y repetir.`);
      return;
    }
    const cara = `${a.media[i] > 0 ? '+' : '-'}${EJES[i]}`;
    cal.caras[cara] = a.media;
    cal.fechaCaras = fecha;
    const faltan = Object.keys(NOMBRE_CARA).filter((c) => !cal.caras[c]);
    progreso(`Cara ${NOMBRE_CARA[cara]} hacia arriba medida.${faltan.length ? ` Faltan: ${faltan.map((c) => NOMBRE_CARA[c]).join(', ')}.` : ' Están las seis.'}`);
  }
  guardarCal();
  dibujarCal();
}

const conSigno = (v, dec) => {
  const s = Math.abs(v).toFixed(dec);
  return `${v < 0 && Number(s) !== 0 ? '−' : '+'}${s}`;
};
const fechaCorta = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });

function acelerometro() {
  return EJES.map((eje, i) => {
    const arriba = cal.caras[`+${eje}`], abajo = cal.caras[`-${eje}`];
    if (!arriba || !abajo) return null;
    return { offset: (arriba[i] + abajo[i]) / 2, escala: (arriba[i] - abajo[i]) / (2 * G) };
  });
}

function textoGiro() {
  if (!cal.giro) return null;
  return `${EJES.map((e, i) => `${e} ${conSigno(cal.giro.sesgo[i], 2)}`).join('  ')} °/s · ruido ${cal.giro.desvio.toFixed(2)}`;
}
function textoAcel() {
  const ejes = acelerometro();
  if (!ejes.some(Boolean)) return null;
  return ejes.map((r, i) => (r ? `${EJES[i]} ${conSigno(r.offset, 2)} m/s² ×${r.escala.toFixed(3)}` : `${EJES[i]} —`)).join('  ');
}

function dibujarCal() {
  const giro = textoGiro(), acel = textoAcel();
  $('cal-giro').textContent = giro ? `${giro} · ${fechaCorta(cal.giro.fecha)}` : '—';
  $('cal-acel').textContent = acel ? `offset y escala: ${acel}`
    : Object.keys(cal.caras).length ? 'Falta la cara opuesta: cada eje se calcula con sus dos caras.' : '—';
  for (const el of document.querySelectorAll('[data-cara]')) el.classList.toggle('hecha', Boolean(cal.caras[el.dataset.cara]));
  $('cal-cero').textContent = cal.cero ? `θ₀ = ${conSigno(cal.cero.theta, 2)}° · ${fechaCorta(cal.cero.fecha)}` : '—';
  $('cal-usar-ref').disabled = !cal.cero;
}

for (const boton of document.querySelectorAll('[data-medir]')) {
  boton.onclick = () => empezarMedicion(boton.dataset.medir, boton);
}

$('cal-usar-ref').onclick = async () => {
  await enviar(`set ref ${cal.cero.theta.toFixed(2)}`);
  await enviar('get');
};

$('cal-copiar').onclick = async () => {
  const caras = Object.keys(NOMBRE_CARA).filter((c) => cal.caras[c]).map((c) => NOMBRE_CARA[c]);
  const texto = [
    'Calibración de la IMU (ejes del sensor, medida en Aplicacion)',
    `giróscopo, sesgo: ${textoGiro() ?? 'sin medir'}`,
    `acelerómetro: ${textoAcel() ?? 'sin medir'}${caras.length ? ` (caras: ${caras.join(' ')})` : ''}`,
    `cero de inclinación: ${cal.cero ? `${cal.cero.theta.toFixed(2)}°` : 'sin medir'}`,
    `datos: ${JSON.stringify(cal)}`,
  ].join('\n');
  try {
    await navigator.clipboard.writeText(texto);
    progreso('Calibración copiada al portapapeles.');
  } catch {
    texto.split('\n').forEach(mensaje);
    verMensajes(true);
    progreso('No se pudo copiar: quedó en Mensajes del robot.');
  }
};

$('cal-borrar').onclick = () => {
  if (!confirm('¿Borrar la calibración guardada en este navegador?')) return;
  cal = { caras: {} };
  guardarCal();
  dibujarCal();
  progreso('Calibración borrada.');
};

setInterval(() => {
  const fresco = performance.now() - ultimaLlegada < DATO_VIEJO_MS;
  if (medicion) {
    if (!fresco) { cortarMedicion(); progreso('Medición cortada: dejaron de llegar datos.'); }
    else {
      const s = Math.min((performance.now() - medicion.inicio) / 1000, DURACION_S[medicion.tipo]);
      progreso(`Midiendo ${NOMBRE_MEDICION[medicion.tipo]}… ${s.toFixed(1)} de ${DURACION_S[medicion.tipo]} s, no moverlo.`);
    }
  }
  const chip = $('cal-quieto');
  if (!fresco || recientes.length < 10 || recientes.some((g) => g.some((v) => !Number.isFinite(v)))) {
    chip.textContent = '';
    return;
  }
  const quieto = Math.max(...estadistica(recientes).desvio) <= MAX_DESVIO_GIRO;
  chip.textContent = quieto ? 'quieto' : 'en movimiento';
  chip.className = `etiqueta ${quieto ? 'activo' : 'alerta'}`;
}, 100);

dibujarJoy();
dibujarCal();
