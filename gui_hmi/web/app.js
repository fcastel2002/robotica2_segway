// Interfaz de telemetría del Segway. Sin bibliotecas: lee líneas "nombre:valor,nombre:valor"
// del puente (Server-Sent Events) o del puerto USB (Web Serial) y las grafica en <canvas>.
'use strict';

const HISTORIA_S = 60;         // segundos guardados en memoria por variable (= ventana máxima)
const GRAFICOS_INICIALES = 6;  // las primeras variables que aparecen se grafican solas
const MAX_MENSAJES = 300;

const series = new Map();      // nombre -> { t: [], v: [], fila, celda, grafico }
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

const PAR = /^([A-Za-z_][\w.]*):([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?|nan|[-+]?inf)$/i;

function procesarLinea(linea) {
  linea = linea.trim();
  if (!linea) return;
  const muestra = {};
  for (const token of linea.split(',')) {
    const m = PAR.exec(token.trim());
    if (!m) { // no es telemetría: es un mensaje de texto del robot
      mensaje(linea);
      return;
    }
    muestra[m[1]] = Number(m[2]); // "nan"/"inf" quedan como NaN y se dibujan como hueco
  }

  let t;
  if ('t' in muestra) {
    t = muestra.t / 1000;
    if (t < tRobotPrevio - 1) borrarHistoria(); // el ESP32 se reinició
    tRobotPrevio = t;
  } else {
    t = performance.now() / 1000;
  }
  for (const [nombre, v] of Object.entries(muestra)) {
    if (nombre === 't') continue;
    const s = series.get(nombre) || nuevaSerie(nombre);
    s.t.push(t);
    s.v.push(v);
  }
  tAhora = t;
  lineasPorSegundo++;
  if (grabacion) grabacion.push({ pc: Date.now(), m: muestra });
}

function mensaje(texto) {
  mensajes.push(`${new Date().toLocaleTimeString()}  ${texto}`);
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
  return { nombre: 'puente', cerrar: () => es.close() };
}

async function conectarUsb() {
  const puerto = await navigator.serial.requestPort();
  await puerto.open({ baudRate: Number($('baudios').value) });
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
  return {
    nombre: 'usb',
    cerrar: () => { seguir = false; lector?.cancel(); },
  };
}

async function conectar() {
  const tipo = $('fuente').value;
  borrarHistoria();
  try {
    fuente = tipo === 'usb' ? await conectarUsb() : conectarPuente();
    $('conectar').textContent = 'Desconectar';
  } catch (err) {
    if (err.name !== 'NotFoundError') estado(`error: ${err.message}`, 'error'); // NotFound = canceló el diálogo
  }
}

function desconectado(texto = 'desconectado', clase = '') {
  fuente = null;
  $('conectar').textContent = 'Conectar';
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

// ---------- Botones ----------

$('conectar').onclick = () => {
  if (fuente) { fuente.cerrar(); desconectado(); } else conectar();
};
$('fuente').onchange = () => {
  $('baudios').hidden = $('fuente').value !== 'usb';
  if (fuente) { fuente.cerrar(); desconectado(); }
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
}

leerColores();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', leerColores);
requestAnimationFrame(cuadro);
if (location.protocol.startsWith('http')) conectar(); // abierta desde el puente: conectar sola
