// Configuración del Segway: lo que se ajusta una vez, separado del banco de pruebas. Comprobar la
// aplicación puente del joystick y calibrar la IMU. Se apoya en app.js (enviar(), mensajes,
// alRecibir) y en banco.js (ultima, ultimaLlegada, DATO_VIEJO_MS, mostrar()).
// Ni la aplicación puente ni guardar la calibración en la placa existen todavía: la página queda
// preparada con el formato propuesto en gui_hmi/README.md (sección Configuración).
'use strict';

// ---------- Joystick (aplicación puente) ----------
// El joystick de PS4 se conecta por Bluetooth a la laptop y una aplicación puente lo lee y manda
// los comandos de movimiento al robot por WiFi. La página solo comprueba que esa aplicación ande:
// le pide GET <dirección>/estado y espera un JSON como
//   { "joystick": { "conectado": true, "nombre": "Wireless Controller", "bateria": 80 },
//     "robot": { "conectado": true, "destino": "192.168.4.1:4211" },
//     "mando": { "avance": 0.25, "giro": -0.10 } }
// con todos los campos opcionales. La página se sirve desde otro puerto, así que la aplicación
// tiene que responder con Access-Control-Allow-Origin: * (si no, el navegador descarta la respuesta).

const PERIODO_JOY_MS = 2000;  // solo mientras Configuración está a la vista
const PERIODO_JOY_FALLA_MS = 10000;
const ESPERA_JOY_MS = 1500;
let joy = null;               // última respuesta de la aplicación
let joyLlegada = null;        // performance.now() de esa respuesta
let joyError = null;          // por qué falló la última consulta; null si respondió
let consultandoJoy = false;

const direccionJoy = () => $('joy-direccion').value.trim().replace(/\/+$/, '');

async function consultarJoy() {
  if (consultandoJoy) return;
  consultandoJoy = true;
  try {
    const r = await fetch(`${direccionJoy()}/estado`, { signal: AbortSignal.timeout(ESPERA_JOY_MS), cache: 'no-store' });
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
  $('joy-robot').textContent = !viva ? '—' : !r ? 'sin dato' : r.conectado ? `enviando${r.destino ? ` a ${r.destino}` : ''}` : 'sin conexión';
  $('joy-edad').textContent = joyLlegada === null ? '—' : `hace ${Math.round((performance.now() - joyLlegada) / 1000)} s`;
  for (const el of document.querySelectorAll('[data-app]')) mostrar(el, viva ? joy.mando?.[el.dataset.app] : undefined);
  $('joy-aviso').hidden = !joyError;
  $('joy-aviso').textContent = `La aplicación puente ${joyError} en ${direccionJoy()}/estado. Todavía no existe; `
    + 'cuando esté, tiene que contestar ese pedido con Access-Control-Allow-Origin: *.';
}

$('joy-form').onsubmit = (e) => {
  e.preventDefault();
  recordar('segway.joy_direccion', direccionJoy());
  consultarJoy();
};
$('joy-direccion').value = recuperar('segway.joy_direccion') || $('joy-direccion').value;
// Si no responde, se espera más entre consultas: cada intento fallido deja un error en la consola
// del navegador. Comprobar consulta en el momento.
let ultimaConsultaJoy = -Infinity;
setInterval(() => {
  if ($('configuracion').hidden || document.hidden) return;
  if (joyError && performance.now() - ultimaConsultaJoy < PERIODO_JOY_FALLA_MS) return;
  ultimaConsultaJoy = performance.now();
  consultarJoy();
}, PERIODO_JOY_MS);

// ---------- Calibración de la IMU ----------
// Se calcula en la página con la telemetría cruda (ejes del sensor, con sesgo): promedios con el
// robot quieto. La telemetría trae el giróscopo con 0,1 °/s de resolución, pero el ruido del
// sensor hace que el promedio de cientos de muestras resuelva por debajo. Queda en localStorage
// hasta que el firmware pueda guardarla en la memoria no volátil de la placa (NVS).

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

let cal = leerCal();  // { giro: { sesgo, desvio, fecha }, caras: { '+x': [ax, ay, az], … }, fechaCaras, cero: { theta, fecha } }
let medicion = null;  // { tipo, boton, inicio, fin, muestras }
const recientes = []; // últimas muestras del giróscopo, para el indicador de quietud

function leerCal() {
  try { return { caras: {}, ...JSON.parse(recuperar(CLAVE_CAL)) }; } catch { return { caras: {} }; }
}
function guardarCal() { recordar(CLAVE_CAL, JSON.stringify(cal)); }

alRecibir.push((m) => {
  if (!('ax_ms2' in m)) return;
  const s = { a: [m.ax_ms2, m.ay_ms2, m.az_ms2], g: [m.gx_dps, m.gy_dps, m.gz_dps], theta: m.theta_deg };
  recientes.push(s.g);
  if (recientes.length > 25) recientes.shift(); // 0,5 s a 50 Hz
  if (!medicion) return;
  medicion.muestras.push(s);
  if (performance.now() >= medicion.fin) terminarMedicion();
});

// media y desvío estándar de cada componente de una lista de vectores
function estadistica(vectores) {
  const n = vectores.length, k = vectores[0].length;
  const media = Array.from({ length: k }, (_, i) => vectores.reduce((s, v) => s + v[i], 0) / n);
  const desvio = media.map((mi, i) => Math.sqrt(vectores.reduce((s, v) => s + (v[i] - mi) ** 2, 0) / n));
  return { media, desvio };
}

function progreso(texto) { $('cal-progreso').textContent = texto; }

function empezarMedicion(tipo, boton) {
  if (medicion) { // el botón de la medición en curso la cancela
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
  } else { // cara del acelerómetro: el eje que se lleva casi toda la gravedad
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

const conSigno = (v, dec) => { // sin "−0.00"
  const s = Math.abs(v).toFixed(dec);
  return `${v < 0 && Number(s) !== 0 ? '−' : '+'}${s}`;
};
const fechaCorta = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });

// offset y escala de cada eje con sus dos caras: arriba lee offset + escala·g, abajo offset − escala·g
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
  await enviar('get'); // la respuesta llena ref° en la tarjeta Control
};

$('cal-copiar').onclick = async () => {
  const caras = Object.keys(NOMBRE_CARA).filter((c) => cal.caras[c]).map((c) => NOMBRE_CARA[c]);
  const texto = [
    'Calibración de la IMU (ejes del sensor, medida en gui_hmi)',
    `giróscopo, sesgo: ${textoGiro() ?? 'sin medir'}`,
    `acelerómetro: ${textoAcel() ?? 'sin medir'}${caras.length ? ` (caras: ${caras.join(' ')})` : ''}`,
    `cero de inclinación: ${cal.cero ? `${cal.cero.theta.toFixed(2)}°` : 'sin medir'}`,
    `datos: ${JSON.stringify(cal)}`,
  ].join('\n');
  try {
    await navigator.clipboard.writeText(texto);
    progreso('Calibración copiada al portapapeles.');
  } catch { // sin permiso de portapapeles: queda en los mensajes
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

setInterval(() => { // 10 veces por segundo: avance de la medición e indicador de quietud
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
