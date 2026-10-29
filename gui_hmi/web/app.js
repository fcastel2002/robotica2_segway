// Interfaz de telemetría del Segway. Sin bibliotecas: lee líneas "nombre:valor,nombre:valor" o
// CSV con encabezado (el formato de firmware/segway_v01) del puente (Server-Sent Events) o del
// puerto USB (Web Serial), las grafica en <canvas> y manda comandos de texto al robot.
'use strict';

const HISTORIA_S = 60;         // segundos guardados en memoria por variable (= ventana máxima)
const GRAFICOS_INICIALES = 8;  // las primeras variables que aparecen se grafican solas
const MAX_MENSAJES = 300;

// Columnas del CSV de firmware/segway_v01 (CSV_HEADER en main/comms_task.c). Si llega otro
// encabezado, lo reemplaza.
const COLUMNAS_FIRMWARE = 't_ms,estado,theta_deg,theta_dot_dps,u,loop_us_max,overruns,enc_l,enc_r,'
  + 'm_l,m_r,servo_l_deg,servo_r_deg,ax_ms2,ay_ms2,az_ms2,gx_dps,gy_dps,gz_dps,x_mm,v_mms';
const CLAVES_TIEMPO = ['t', 't_ms'];  // milisegundos del robot
// Funciones (muestra, t, textos) llamadas con cada muestra antes de guardarla: pueden agregar
// columnas calculadas a la muestra, que se grafican y graban como las demás (banco.js).
const alRecibir = [];
const alMensaje = [];  // funciones (texto) llamadas con cada mensaje '#' del robot (banco.js)

const series = new Map();      // nombre -> { t: [], v: [], fila, celda, grafico }
const textos = new Map();      // columnas de texto (estado) -> { valor, celda }
let columnas = COLUMNAS_FIRMWARE.split(',');
let tAhora = 0;                // tiempo del último dato recibido, en segundos
let tPausa = 0;
let tRobotPrevio = -Infinity;
let pausado = false;
let grabacion = null;          // [{ pc, m }] mientras se graba
let lineasPorSegundo = 0;
let fuente = null;             // { nombre, cerrar() } de la conexión activa
let textoEstado = 'desconectado';
const mensajes = [];
let mensajesNuevos = false;

const $ = (id) => document.getElementById(id);

// ---------- Entrada de datos ----------

const NUMERO = String.raw`[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|nan|[-+]?inf`;
const PAR = new RegExp(String.raw`^([A-Za-z_][\w.]*):(${NUMERO})$`, 'i');
const ES_NUMERO = new RegExp(`^(?:${NUMERO})$`, 'i');
const ENCABEZADO = /^[A-Za-z_]\w*(?:,[A-Za-z_]\w*)+$/;
const PALABRA = /^[A-Za-z_][\w?]*$/;

// "theta:0.5,u:0.1" -> { numeros, textos }, o null si alguna parte no es un par
function leerPares(linea) {
  const numeros = {};
  for (const token of linea.split(',')) {
    const m = PAR.exec(token.trim());
    if (!m) return null;
    numeros[m[1]] = Number(m[2]); // "nan"/"inf" quedan como NaN y se dibujan como hueco
  }
  return { numeros, textos: {} };
}

// "1234,BALANCING,0.52,..." con las columnas del último encabezado, o null si no encaja
function leerCsv(linea) {
  const campos = linea.split(',').map((c) => c.trim());
  if (campos.length !== columnas.length) return null;
  const numeros = {}, palabras = {};
  for (let i = 0; i < campos.length; i++) {
    if (ES_NUMERO.test(campos[i])) numeros[columnas[i]] = Number(campos[i]);
    else if (PALABRA.test(campos[i])) palabras[columnas[i]] = campos[i];
    else return null;
  }
  return Object.keys(numeros).length ? { numeros, textos: palabras } : null;
}

function procesarLinea(linea) {
  linea = linea.trim();
  if (!linea) return;
  if (linea.startsWith('#')) { // el firmware marca con '#' todo lo que no es dato
    const texto = linea.replace(/^#\s*/, '');
    if (ENCABEZADO.test(texto)) columnas = texto.split(',');
    mensaje(texto);
    return;
  }
  if (ENCABEZADO.test(linea)) { columnas = linea.split(','); return; } // encabezado sin '#'
  const leida = leerPares(linea) ?? leerCsv(linea);
  if (!leida) { // no es telemetría: es un mensaje de texto del robot
    mensaje(linea);
    return;
  }
  const muestra = leida.numeros;

  let t;
  const claveT = CLAVES_TIEMPO.find((k) => k in muestra);
  if (claveT) {
    t = muestra[claveT] / 1000;
    if (t < tRobotPrevio - 1) borrarHistoria(); // el ESP32 se reinició
    tRobotPrevio = t;
  } else {
    t = performance.now() / 1000;
  }
  for (const f of alRecibir) f(muestra, t, leida.textos);
  for (const [nombre, v] of Object.entries(muestra)) {
    if (nombre === claveT) continue;
    const s = series.get(nombre) || nuevaSerie(nombre);
    s.t.push(t);
    s.v.push(v);
  }
  tAhora = t;
  lineasPorSegundo++;
  for (const [nombre, v] of Object.entries(leida.textos)) {
    (textos.get(nombre) || nuevoTexto(nombre)).valor = v;
  }
  if (grabacion) grabacion.push({ pc: Date.now(), m: { ...muestra, ...leida.textos } });
}

let ultimoMensaje = '', repeticiones = 0;
function mensaje(texto) {
  leerParametros(texto);
  for (const f of alMensaje) f(texto);
  const linea = `${new Date().toLocaleTimeString()}  ${texto}`;
  if (texto === ultimoMensaje && mensajes.length) { // p. ej. "ok: motor" al mover un deslizador
    mensajes[mensajes.length - 1] = `${linea}  (×${++repeticiones})`;
  } else {
    mensajes.push(linea);
    repeticiones = 1;
  }
  ultimoMensaje = texto;
  if (mensajes.length > MAX_MENSAJES) mensajes.shift();
  mensajesNuevos = true;
}

function borrarHistoria() {
  for (const s of series.values()) { s.t.length = 0; s.v.length = 0; }
  tRobotPrevio = -Infinity;
}

// ---------- Fuentes ----------

function conectarPuente() {
  const es = new EventSource('eventos');
  es.onopen = () => estado('puente conectado', 'ok');
  es.onerror = () => estado('sin puente, reintentando… (¿está corriendo puente.py?)', 'error');
  es.onmessage = (e) => e.data.split('\n').forEach(procesarLinea);
  const enviar = async (texto) => {
    const r = await fetch('comando', { method: 'POST', body: texto });
    if (!r.ok) throw new Error(`el puente respondió ${r.status}`);
  };
  return { nombre: 'puente', enviar, cerrar: () => es.close() };
}

// puerto: uno ya autorizado (reconexión automática); sin él, el navegador pide elegir
async function conectarUsb(puerto) {
  puerto ??= await navigator.serial.requestPort();
  try {
    await puerto.open({ baudRate: Number($('baudios').value) });
  } catch (err) {
    throw new Error(`${err.message} ¿Lo tiene otro programa? Cerrar el monitor de ESP-IDF.`);
  }
  estado('USB conectado', 'ok');
  let seguir = true;
  let lector;
  (async () => {
    const decodificador = new TextDecoder();
    let resto = '';
    while (seguir && puerto.readable) {
      lector = puerto.readable.getReader();
      try {
        for (;;) {
          const { value, done } = await lector.read();
          if (done) break;
          resto += decodificador.decode(value, { stream: true });
          const lineas = resto.split('\n');
          resto = lineas.pop();
          lineas.forEach(procesarLinea);
        }
      } catch (err) { // errores de trama o desbordes: se avisa y se sigue leyendo
        mensaje(`[USB] ${err.message}`);
      } finally {
        lector.releaseLock();
      }
    }
    await puerto.close().catch(() => {});
    if (seguir) desconectado('USB desconectado (¿se desenchufó?)', 'error');
  })();
  const codificador = new TextEncoder();
  const enviar = async (texto) => {
    const escritor = puerto.writable.getWriter();
    try { await escritor.write(codificador.encode(texto + '\n')); } finally { escritor.releaseLock(); }
  };
  // Si el robot ya había arrancado, el encabezado CSV se perdió: "tlm on" lo vuelve a imprimir.
  setTimeout(() => { if (seguir) enviar('tlm on').catch(() => {}); }, 300);
  return {
    nombre: 'usb',
    enviar,
    cerrar: () => { seguir = false; lector?.cancel(); },
  };
}

async function conectar(puerto) {
  const tipo = $('fuente').value;
  borrarHistoria();
  try {
    fuente = tipo === 'usb' ? await conectarUsb(puerto) : conectarPuente();
    $('conectar').textContent = 'Desconectar';
    $('comandos').hidden = false;
  } catch (err) {
    if (err.name !== 'NotFoundError') estado(`error: ${err.message}`, 'error'); // NotFound = canceló el diálogo
  }
}

function desconectado(texto = 'desconectado', clase = '') {
  fuente = null;
  ponerDeslizadores(0); // ya no se puede mandar nada: el próximo conectar arranca en cero
  enviado.l = enviado.r = 0;
  $('conectar').textContent = 'Conectar';
  $('comandos').hidden = true;
  estado(texto, clase);
}

function estado(texto, clase = '') {
  textoEstado = texto;
  $('estado').textContent = texto;
  $('estado').className = `estado ${clase}`;
}

// ---------- Panel de variables y gráficos ----------

function nuevaSerie(nombre) {
  const fila = document.createElement('tr');
  fila.innerHTML = '<td><input type="checkbox"></td><td></td><td></td>';
  fila.cells[1].textContent = nombre;
  const casilla = fila.querySelector('input');
  const s = { t: [], v: [], fila, celda: fila.cells[2], grafico: null };
  series.set(nombre, s);
  $('variables').tBodies[0].append(fila);
  $('sin-datos').hidden = true;

  casilla.checked = [...series.values()].filter((x) => x.grafico).length < GRAFICOS_INICIALES;
  fila.addEventListener('click', (e) => {
    if (e.target !== casilla) casilla.checked = !casilla.checked;
    mostrarGrafico(nombre, casilla.checked);
  });
  mostrarGrafico(nombre, casilla.checked);
  return s;
}

function nuevoTexto(nombre) { // columna de texto (el estado del supervisor): se lee, no se grafica
  const fila = document.createElement('tr');
  fila.className = 'texto';
  fila.innerHTML = '<td></td><td></td><td></td>';
  fila.cells[1].textContent = nombre;
  const x = { valor: '', celda: fila.cells[2] };
  textos.set(nombre, x);
  $('variables').tBodies[0].prepend(fila);
  $('sin-datos').hidden = true;
  return x;
}

function mostrarGrafico(nombre, visible) {
  const s = series.get(nombre);
  if (visible && !s.grafico) {
    const div = document.createElement('div');
    div.className = 'grafico';
    div.innerHTML = '<h3><b></b><span></span></h3><canvas></canvas>';
    div.querySelector('b').textContent = nombre;
    const canvas = div.querySelector('canvas');
    s.grafico = { div, canvas, valor: div.querySelector('span'), cursorX: null };
    canvas.addEventListener('mousemove', (e) => { s.grafico.cursorX = e.offsetX; });
    canvas.addEventListener('mouseleave', () => { s.grafico.cursorX = null; });
  } else if (!visible && s.grafico) {
    s.grafico.div.remove();
    s.grafico = null;
  }
  // los gráficos siguen el orden de la tabla
  for (const x of series.values()) if (x.grafico) $('graficos').append(x.grafico.div);
}

// ---------- Dibujo ----------

let colores;
function leerColores() {
  const css = getComputedStyle(document.documentElement);
  const c = (n) => css.getPropertyValue(n).trim();
  colores = {
    texto: c('--tenue'), rejilla: c('--rejilla'), linea: c('--linea'), cursor: c('--texto'), fondo: c('--superficie'),
  };
}

function formato(v) {
  if (!Number.isFinite(v)) return String(v);
  const a = Math.abs(v);
  if (a !== 0 && (a >= 1e5 || a < 1e-3)) return v.toExponential(2);
  return String(Number(v.toPrecision(4)));
}

function marcas(min, max, cantidad) {
  const bruto = (max - min) / cantidad;
  const base = 10 ** Math.floor(Math.log10(bruto));
  const paso = [1, 2, 5, 10].map((k) => k * base).find((p) => p >= bruto);
  const lista = [];
  for (let v = Math.ceil(min / paso) * paso; v <= max; v += paso) lista.push(v);
  return lista;
}

function primerIndice(t, desde) { // búsqueda binaria del primer t >= desde
  let a = 0, b = t.length;
  while (a < b) { const m = (a + b) >> 1; if (t[m] < desde) a = m + 1; else b = m; }
  return a;
}

function dibujar(s, t1, ventana) {
  const { canvas, cursorX } = s.grafico;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  const t0 = t1 - ventana;
  const i0 = Math.max(0, primerIndice(s.t, t0) - 1);
  let min = Infinity, max = -Infinity;
  for (let i = i0; i < s.v.length; i++) {
    const v = s.v[i];
    if (v < min) min = v;
    if (v > max) max = v;
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) { min = -1; max = 1; }
  if (max - min < 1e-9) { const m = Math.abs(min) * 0.05 || 1; min -= m; max += m; }
  const margen = (max - min) * 0.08;
  min -= margen; max += margen;

  const izq = 52, der = 6, arr = 6, abj = 18;
  const X = (t) => izq + ((t - t0) / ventana) * (w - izq - der);
  const Y = (v) => arr + ((max - v) / (max - min)) * (h - arr - abj);

  ctx.font = '11px system-ui, sans-serif';
  ctx.lineWidth = 1;
  ctx.strokeStyle = colores.rejilla;
  ctx.fillStyle = colores.texto;
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  for (const v of marcas(min, max, 4)) {
    const y = Math.round(Y(v)) + 0.5;
    ctx.beginPath(); ctx.moveTo(izq, y); ctx.lineTo(w - der, y); ctx.stroke();
    ctx.fillText(formato(v), izq - 6, y);
  }
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (const d of marcas(-ventana, 0, 5)) { // tiempo relativo al último dato: -10 s … 0
    const x = Math.round(X(t1 + d)) + 0.5;
    ctx.beginPath(); ctx.moveTo(x, arr); ctx.lineTo(x, h - abj); ctx.stroke();
    ctx.fillText(d === 0 ? '0 s' : `${formato(d)}`, x, h - abj + 4);
  }

  ctx.save();
  ctx.beginPath();
  ctx.rect(izq, 0, w - izq - der, h);
  ctx.clip();
  ctx.strokeStyle = colores.linea;
  ctx.lineWidth = 2;
  ctx.lineJoin = 'round';
  ctx.beginPath();
  let trazando = false;
  for (let i = i0; i < s.v.length; i++) {
    const v = s.v[i];
    if (Number.isNaN(v)) { trazando = false; continue; }
    const x = X(s.t[i]), y = Y(v);
    if (trazando) ctx.lineTo(x, y); else ctx.moveTo(x, y);
    trazando = true;
  }
  ctx.stroke();
  ctx.restore();

  // cursor: valor de la variable en el instante bajo el mouse
  if (cursorX !== null && cursorX > izq && s.t.length) {
    const tc = t0 + ((cursorX - izq) / (w - izq - der)) * ventana;
    let i = Math.min(primerIndice(s.t, tc), s.t.length - 1);
    if (i > 0 && tc - s.t[i - 1] < s.t[i] - tc) i--;
    const x = X(s.t[i]), y = Y(s.v[i]);
    ctx.strokeStyle = colores.cursor;
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(x, arr); ctx.lineTo(x, h - abj); ctx.stroke();
    ctx.fillStyle = colores.linea;
    ctx.beginPath(); ctx.arc(x, y, 4, 0, 2 * Math.PI); ctx.fill();
    const texto = `${formato(s.v[i])}  @ ${formato(s.t[i] - t1)} s`;
    ctx.font = '12px system-ui, sans-serif';
    const ancho = ctx.measureText(texto).width + 8;
    const xt = x > w / 2 ? x - 6 - ancho : x + 6;
    ctx.fillStyle = colores.fondo;
    ctx.fillRect(xt, arr, ancho, 18);
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillStyle = colores.cursor;
    ctx.fillText(texto, xt + 4, arr + 3);
  }
}

function cuadro() {
  const t1 = pausado ? tPausa : tAhora;
  const ventana = Number($('ventana').value);
  for (const s of series.values()) {
    const corte = primerIndice(s.t, t1 - HISTORIA_S);
    if (corte > 500) { s.t.splice(0, corte); s.v.splice(0, corte); } // recorta en bloques, no en cada dato
    if (s.grafico) dibujar(s, t1, ventana);
  }
  requestAnimationFrame(cuadro);
}

// ---------- Actualizaciones lentas (texto) ----------

setInterval(() => { // 10 veces por segundo: los números se pueden leer
  for (const s of series.values()) {
    const texto = s.v.length ? formato(s.v[s.v.length - 1]) : '—';
    s.celda.textContent = texto;
    if (s.grafico) s.grafico.valor.textContent = texto;
  }
  for (const x of textos.values()) x.celda.textContent = x.valor;
  const estadoRobot = textos.get('estado')?.valor;
  $('estado-robot').hidden = !estadoRobot;
  if (estadoRobot) {
    $('estado-robot').textContent = estadoRobot;
    $('estado-robot').className = `estado-robot ${CLASE_ESTADO[estadoRobot] ?? ''}`;
  }
  // El firmware ignora "motor" fuera de DISARMED y FAULT: los deslizadores lo reflejan
  const motoresHabilitados = !estadoRobot || ESTADOS_MOTOR_A_MANO.includes(estadoRobot);
  if ($('motores').disabled === motoresHabilitados) {
    $('motores').disabled = !motoresHabilitados;
    $('motores-aviso').textContent = motoresHabilitados ? '' : `solo en ${ESTADOS_MOTOR_A_MANO.join(' o ')}`;
    if (!motoresHabilitados) ponerDeslizadores(0);
  }
  if (grabacion) $('grabar').textContent = `Detener y guardar (${grabacion.length})`;
  if (mensajesNuevos) {
    const consola = $('consola');
    const alFondo = consola.scrollTop + consola.clientHeight >= consola.scrollHeight - 4;
    consola.textContent = mensajes.join('\n');
    if (alFondo) consola.scrollTop = consola.scrollHeight;
    $('n-mensajes').textContent = `(${mensajes.length})`;
    mensajesNuevos = false;
  }
}, 100);

setInterval(() => { // frecuencia de llegada de datos
  if (fuente) {
    const tasa = lineasPorSegundo ? `${lineasPorSegundo} Hz` : 'sin datos del robot';
    $('estado').textContent = `${textoEstado} · ${tasa}`;
  }
  lineasPorSegundo = 0;
}, 1000);

// ---------- Grabación CSV ----------

function descargarCsv(filas) {
  const columnas = [...new Set(filas.flatMap((f) => Object.keys(f.m)))];
  const lineas = [['pc_ms', ...columnas].join(',')];
  for (const f of filas) lineas.push([f.pc, ...columnas.map((c) => f.m[c] ?? '')].join(','));
  const enlace = document.createElement('a');
  enlace.href = URL.createObjectURL(new Blob([lineas.join('\n') + '\n'], { type: 'text/csv' }));
  const d = new Date();
  const dos = (n) => String(n).padStart(2, '0');
  enlace.download = `segway_${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}_`
    + `${dos(d.getHours())}-${dos(d.getMinutes())}-${dos(d.getSeconds())}.csv`;
  enlace.click();
  URL.revokeObjectURL(enlace.href);
}

// ---------- Comandos al robot ----------

const CLASE_ESTADO = { BALANCING: 'activo', FALLEN: 'alerta', FAULT: 'alerta' };

// Los comandos salen de a uno y en orden: por USB, un segundo write mientras el primero no
// terminó falla (el puerto queda tomado), y se perdería p. ej. el "motor stop" al soltar.
let colaEnvio = Promise.resolve();

// silencioso: no se anota en la consola (los deslizadores mandan muchos comandos seguidos)
function enviar(texto, silencioso = false) {
  texto = texto.trim();
  if (!texto) return colaEnvio;
  if (!fuente?.enviar) { mensaje(`[sin conexión] no se mandó: ${texto}`); return colaEnvio; }
  if (!silencioso) {
    mensaje(`> ${texto}`);
    $('mensajes').open = true;
  }
  const destino = fuente;
  colaEnvio = colaEnvio.then(() => destino.enviar(texto))
    .catch((err) => mensaje(`[error al mandar] ${err.message}`));
  return colaEnvio;
}

// ---------- Motores a mano ----------
// El firmware deja el último "motor" aplicado hasta que llega otro: no tiene tiempo de espera.
// Por eso la página frena por su cuenta al soltar el deslizador (salvo "mantener"), al
// desconectar y al ocultar o cerrar la pestaña. Si se corta el cable, no hay quien frene.

const ESTADOS_MOTOR_A_MANO = ['DISARMED', 'FAULT'];
const PERIODO_MOTOR_MS = 100;    // como mucho 10 comandos por segundo mientras se arrastra
const enviado = { l: 0, r: 0 };  // último porcentaje mandado a cada motor
let envioPendiente = null;

function ponerDeslizadores(pct) {
  for (const lado of ['l', 'r']) {
    $(`motor-${lado}`).value = pct;
    $(`valor-${lado}`).textContent = `${pct} %`;
  }
}

function mandarMotores() {
  clearTimeout(envioPendiente);
  envioPendiente = null;
  const l = Number($('motor-l').value), r = Number($('motor-r').value);
  const antes = { ...enviado };
  if (l === antes.l && r === antes.r) return colaEnvio;
  enviado.l = l; // se anota antes de mandar: la cola respeta el orden de las llamadas
  enviado.r = r;
  if (l === 0 && r === 0) return enviar('motor stop', true);
  if (l === r) return enviar(`motor ${l}`, true);
  if (l !== antes.l) enviar(`motor l ${l}`, true);
  return r !== antes.r ? enviar(`motor r ${r}`, true) : colaEnvio;
}

function frenarMotores() {
  ponerDeslizadores(0);
  return mandarMotores();
}

for (const lado of ['l', 'r']) {
  const deslizador = $(`motor-${lado}`);
  deslizador.addEventListener('input', () => {
    if ($('motores-juntos').checked) ponerDeslizadores(deslizador.value);
    else $(`valor-${lado}`).textContent = `${deslizador.value} %`;
    envioPendiente ??= setTimeout(mandarMotores, PERIODO_MOTOR_MS);
  });
  deslizador.addEventListener('change', () => { // se soltó
    if (!$('motores-mantener').checked) ponerDeslizadores(0);
    mandarMotores();
  });
}
$('motores-mantener').addEventListener('change', (e) => { if (!e.target.checked) frenarMotores(); });
document.addEventListener('visibilitychange', () => { if (document.hidden) frenarMotores(); });
addEventListener('pagehide', () => frenarMotores());

// La respuesta de "get" (# kp=0.8 ki=0 ...) llena las casillas de ganancias y las que tengan
// data-param (umax en el banco de pruebas).
function leerParametros(texto) {
  if (!texto.startsWith('kp=')) return;
  for (const [, nombre, valor] of texto.matchAll(/(\w+)=([-+\d.eE]+)/g)) {
    const casilla = $('ganancias').elements[nombre] ?? document.querySelector(`[data-param="${nombre}"]`);
    if (casilla && document.activeElement !== casilla) casilla.value = Number(valor);
  }
}

for (const boton of document.querySelectorAll('[data-comando]')) {
  boton.onclick = () => {
    // "motor stop", "disarm" y "arm" ponen en cero el motor a mano del firmware
    if (['motor stop', 'disarm', 'arm'].includes(boton.dataset.comando)) {
      ponerDeslizadores(0);
      enviado.l = enviado.r = 0;
    }
    enviar(boton.dataset.comando);
  };
}
$('linea-comando').onsubmit = (e) => {
  e.preventDefault();
  enviar($('texto-comando').value);
  $('texto-comando').select();
};
$('ganancias').onsubmit = async (e) => {
  e.preventDefault();
  for (const casilla of $('ganancias').querySelectorAll('input')) {
    if (casilla.value !== '') await enviar(`set ${casilla.name} ${casilla.value}`);
  }
  await enviar('get');
};
document.addEventListener('keydown', (e) => { // Esc desarma desde cualquier lado de la página
  if (e.key === 'Escape' && fuente) {
    ponerDeslizadores(0);
    enviado.l = enviado.r = 0;
    enviar('disarm');
  }
});

// ---------- Botones ----------

async function cerrarFuente() { // frena antes de soltar el puerto: después ya no se puede
  await frenarMotores();
  fuente.cerrar();
  desconectado();
}

$('conectar').onclick = () => {
  if (fuente) cerrarFuente(); else conectar();
};

// Un puerto que ya se eligió una vez queda autorizado: al abrir la página o al enchufar la placa
// se conecta solo, sin el diálogo. Con más de uno autorizado no adivina: hay que tocar Conectar.
async function conectarUsbAutorizado() {
  if (fuente || $('fuente').value !== 'usb' || !('serial' in navigator)) return;
  const puertos = await navigator.serial.getPorts();
  if (puertos.length === 1) conectar(puertos[0]);
  else if (puertos.length > 1) estado('varios puertos autorizados: tocar Conectar y elegir uno');
}
if ('serial' in navigator) navigator.serial.addEventListener('connect', conectarUsbAutorizado);
function recordar(clave, valor) { try { localStorage.setItem(clave, valor); } catch { /* sin almacenamiento */ } }
function recuperar(clave) { try { return localStorage.getItem(clave); } catch { return null; } }
for (const id of ['fuente', 'baudios']) { // la última fuente y velocidad elegidas
  const guardado = recuperar(`segway.${id}`);
  if (guardado && [...$(id).options].some((o) => o.value === guardado)) $(id).value = guardado;
  $(id).addEventListener('change', () => recordar(`segway.${id}`, $(id).value));
}
// puente.py abre la página con ?fuente=usb (robot real) o ?fuente=puente (--simular)
const fuentePedida = new URLSearchParams(location.search).get('fuente');
if (['usb', 'puente'].includes(fuentePedida)) {
  $('fuente').value = fuentePedida;
  recordar('segway.fuente', fuentePedida);
}

$('fuente').onchange = async () => {
  $('baudios').hidden = $('fuente').value !== 'usb';
  if (fuente) await cerrarFuente();
  conectarUsbAutorizado();
};
$('pausa').onclick = () => {
  pausado = !pausado;
  tPausa = tAhora;
  $('pausa').textContent = pausado ? 'Reanudar' : 'Pausar';
};
$('grabar').onclick = () => {
  if (!grabacion) {
    grabacion = [];
    $('grabar').classList.add('grabando');
  } else {
    if (grabacion.length) descargarCsv(grabacion);
    grabacion = null;
    $('grabar').classList.remove('grabando');
    $('grabar').textContent = 'Grabar CSV';
  }
};

if (!('serial' in navigator)) {
  const opcion = $('fuente').querySelector('[value=usb]');
  opcion.disabled = true;
  opcion.textContent += ' (requiere Chrome o Edge)';
  if ($('fuente').value === 'usb') $('fuente').value = 'puente';
}
$('baudios').hidden = $('fuente').value !== 'usb';

leerColores();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', leerColores);
requestAnimationFrame(cuadro);
// Abierta desde el puente: conectar sola. El USB, solo si el puerto ya se eligió alguna vez
// (la primera vez el navegador exige un clic en Conectar para mostrar el diálogo).
if (location.protocol.startsWith('http') && $('fuente').value === 'puente') conectar();
else conectarUsbAutorizado();
