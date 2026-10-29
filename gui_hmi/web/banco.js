// Banco de pruebas del Segway: leer cada sensor y mover cada actuador por separado, sin el lazo
// de control. Se apoya en app.js (conexión, enviar(), motores a mano, mensajes) y le agrega a
// cada muestra columnas calculadas (rpm_l, rpm_r, a_ms2) que se grafican y graban como las demás.
'use strict';

const VENTANA_RPM_S = 0.2;      // ventana de la derivada de los encoders: 10 muestras a 50 Hz
const DATO_VIEJO_MS = 1000;     // sin datos por más tiempo, los valores se apagan
const PERIODO_SERVO_MS = 100;   // como mucho 10 comandos por segundo mientras se arrastra

let ultima = {};                // última muestra, números y textos
let ultimaLlegada = -Infinity;  // performance.now() de la última muestra
let muestrasPorSegundo = 0;
const historiaEnc = [];         // [{ t, l, r }] que cubren VENTANA_RPM_S
let escalon = null;             // prueba de escalón en curso

const LADOS = { l: 'izq', r: 'der' };
const acotar = (v, min, max) => Math.min(Math.max(v, min), max);
const cuentasPorVuelta = () => Number($('cpr').value) || 880;

// ---------- Columnas calculadas ----------

alRecibir.push((m, t, textosMuestra) => {
  if ('enc_l' in m && 'enc_r' in m) {
    const previa = historiaEnc[historiaEnc.length - 1];
    if (previa && t <= previa.t) historiaEnc.length = 0; // el ESP32 se reinició
    historiaEnc.push({ t, l: m.enc_l, r: m.enc_r });
    while (historiaEnc.length > 2 && t - historiaEnc[1].t >= VENTANA_RPM_S) historiaEnc.shift();
    const a = historiaEnc[0], dt = t - a.t;
    for (const lado in LADOS) {
      m[`rpm_${lado}`] = dt > 0 ? ((m[`enc_${lado}`] - a[lado]) / cuentasPorVuelta() / dt) * 60 : 0;
    }
    if (escalon && performance.now() >= escalon.mitad) {
      escalon.suma.l += m.rpm_l;
      escalon.suma.r += m.rpm_r;
      escalon.n++;
    }
  }
  if ('ax_ms2' in m) m.a_ms2 = Math.hypot(m.ax_ms2, m.ay_ms2, m.az_ms2); // NaN sin IMU
  ultima = { ...m, ...textosMuestra };
  ultimaLlegada = performance.now();
  muestrasPorSegundo++;
});

// "Encoders a cero" hace saltar la cuenta: sin esto, la derivada daría un pico
for (const b of document.querySelectorAll('[data-comando="enc reset"]')) {
  b.addEventListener('click', () => { historiaEnc.length = 0; });
}

// ---------- Mostrar valores ----------

// <div class="medidor" data-col=… data-min data-max>x</div> -> nombre, barra y valor
for (const el of document.querySelectorAll('.medidor')) {
  const nombre = el.textContent;
  el.innerHTML = '<span></span><span class="barra"><i></i></span><output>—</output>';
  el.firstChild.textContent = nombre;
}
const celdas = [...document.querySelectorAll('#banco [data-col]')];

function texto(el, v) {
  if (v === undefined) return '—';
  if (typeof v === 'string') return v;
  if (Number.isNaN(v)) return el.dataset.nan ?? 'nan';
  const s = (v * (Number(el.dataset.factor) || 1)).toFixed(Number(el.dataset.dec ?? 2));
  return s.replace(/^-(0\.?0*)$/, '$1') + (el.dataset.unidad ?? ''); // sin "-0"
}

function mostrar(el, v) {
  if (!el.classList.contains('medidor')) {
    el.textContent = texto(el, v);
    return;
  }
  el.querySelector('output').textContent = texto(el, v);
  const min = Number(el.dataset.min), max = Number(el.dataset.max);
  const pos = (x) => ((acotar(x, min, max) - min) / (max - min)) * 100;
  const barra = el.querySelector('i');
  if (!Number.isFinite(v)) { barra.style.width = '0'; return; }
  const cero = pos(0), p = pos(v); // la barra crece desde el cero (o desde el mínimo)
  barra.style.left = `${Math.min(cero, p)}%`;
  barra.style.width = `${Math.abs(p - cero)}%`;
}

function duracion(ms) {
  const s = Math.floor(ms / 1000);
  const dos = (n) => String(n).padStart(2, '0');
  return s >= 3600 ? `${Math.floor(s / 3600)} h ${dos(Math.floor(s / 60) % 60)} min` : `${Math.floor(s / 60)}:${dos(s % 60)}`;
}

setInterval(() => { // 10 veces por segundo, como la tabla de app.js
  const viejo = performance.now() - ultimaLlegada > DATO_VIEJO_MS;
  $('banco').classList.toggle('viejo', viejo);
  $('banco-aviso').hidden = !viejo;
  if (viejo) {
    $('banco-aviso').textContent = fuente
      ? 'Conectado, pero no llegan datos: ¿velocidad equivocada, tlm off o el robot se reinició sin encabezado? Probar «tlm on».'
      : 'Sin conexión: conectar por USB, o correr puente.py --simular para probar la página sin robot.';
  }

  const cpr = cuentasPorVuelta(), radio = Number($('radio').value) || 40;
  const valores = { ...ultima };
  for (const lado in LADOS) {
    const c = ultima[`enc_${lado}`];
    if (c === undefined) continue;
    valores[`vueltas_${lado}`] = c / cpr;
    valores[`dist_${lado}_mm`] = (c / cpr) * 2 * Math.PI * radio;
  }
  for (const el of celdas) mostrar(el, valores[el.dataset.col]);

  const theta = ultima.theta_deg;
  $('robot-dibujo').setAttribute('transform', `rotate(${Number.isFinite(theta) ? acotar(theta, -90, 90) : 0})`);
  const imu = $('imu-estado');
  imu.textContent = ultima.ax_ms2 === undefined ? '' : Number.isNaN(ultima.ax_ms2) ? 'sin lectura' : 'ok';
  imu.className = `etiqueta ${imu.textContent === 'ok' ? 'activo' : 'alerta'}`;
  $('encendido').textContent = ultima.t_ms === undefined ? '—' : duracion(ultima.t_ms);

  for (const el of document.querySelectorAll('[data-requiere-conexion]')) el.disabled = !fuente;
  if (!fuente) servoEnviado.l = servoEnviado.r = null;
  // Suelto: los pasos no tienen desde dónde contar. Agarrado y sin tocar (p. ej. al conectar),
  // el deslizador sigue al servo.
  for (const lado in LADOS) {
    const suelto = !agarrado(lado);
    for (const b of document.querySelectorAll(`[data-paso^="${lado} "]`)) b.disabled = suelto;
    if (suelto) {
      servoEnviado[lado] = null;
    } else if (servoEnviado[lado] === null && servoPendiente[lado] === null
               && document.activeElement !== $(`servo-${lado}`)) {
      ponerServo(lado, Math.round(ultima[`servo_${lado}_deg`]));
    }
  }
  if (escalon && !fuente) terminarEscalon('cortado: se desconectó');
  if (escalon && $('motores').disabled) terminarEscalon('cortado: el robot salió de DISARMED/FAULT');
}, 100);

setInterval(() => {
  $('tasa').textContent = `${muestrasPorSegundo} Hz`;
  muestrasPorSegundo = 0;
}, 1000);

// ---------- Escalón de motores ----------
// Pone los deslizadores en el valor pedido, espera y frena. Las RPM se promedian en la segunda
// mitad, cuando la rueda ya terminó de acelerar. Sirve para la zona muerta y para el ensayo E-04.

$('escalon').onsubmit = (e) => {
  e.preventDefault();
  if (escalon) { terminarEscalon('cancelado'); return; }
  const pct = acotar(Math.round(Number($('escalon-pct').value)) || 0, -100, 100);
  const s = acotar(Number($('escalon-s').value) || 2, 0.2, 10);
  const rueda = $('escalon-rueda').value;
  const lados = rueda === 'ambas' ? ['l', 'r'] : [rueda];
  for (const lado in LADOS) {
    const v = lados.includes(lado) ? pct : 0;
    $(`motor-${lado}`).value = v;
    $(`valor-${lado}`).textContent = `${v} %`;
  }
  mandarMotores();
  escalon = {
    pct, s, lados,
    mitad: performance.now() + s * 500,
    suma: { l: 0, r: 0 },
    n: 0,
    temporizador: setTimeout(() => terminarEscalon(), s * 1000),
  };
  $('escalon-boton').textContent = 'Cancelar';
  $('escalon-resultado').textContent = `en curso: ${pct} % durante ${s} s…`;
};

// motivo: sin motivo terminó bien; 'tomado' = se movió un deslizador y él manda desde ahí
function terminarEscalon(motivo) {
  if (!escalon) return;
  const e = escalon;
  escalon = null;
  clearTimeout(e.temporizador);
  $('escalon-boton').textContent = 'Probar';
  if (motivo !== 'tomado') frenarMotores();
  let resultado;
  if (motivo) resultado = `escalón ${motivo === 'tomado' ? 'cancelado: se movió un deslizador' : motivo}`;
  else if (!e.n) resultado = 'escalón sin datos de los encoders';
  else {
    resultado = `escalón ${e.pct} % · ${e.s} s: `
      + e.lados.map((l) => `${LADOS[l]} ${Math.round(e.suma[l] / e.n)} RPM`).join(', ');
  }
  $('escalon-resultado').textContent = resultado;
  mensaje(resultado);
}

for (const lado in LADOS) $(`motor-${lado}`).addEventListener('input', () => terminarEscalon('tomado'));
for (const b of document.querySelectorAll('[data-comando="motor stop"], [data-comando="disarm"]')) {
  b.addEventListener('click', () => terminarEscalon('cancelado'));
}
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') terminarEscalon('cancelado con Esc'); });
document.addEventListener('visibilitychange', () => { if (document.hidden) terminarEscalon('cortado: pestaña oculta'); });

$('limite').onsubmit = async (e) => {
  e.preventDefault();
  const v = $('limite').elements.umax.value;
  if (v === '') return;
  await enviar(`set umax ${v}`);
  await enviar('get'); // la respuesta confirma el valor que quedó (el firmware lo acota a 0-1)
};

// ---------- Servos ----------
// A diferencia de los motores, quedan donde se los deja: el servo sostiene la pata. Un servo
// suelto no tiene posición conocida (el firmware manda "nan"): su deslizador y sus pasos se
// bloquean y el primer ángulo se escribe en "Ir a", porque el servo va directo hasta ahí.

const servoEnviado = { l: null, r: null };   // último ángulo mandado a cada servo agarrado
const servoPendiente = { l: null, r: null }; // envío demorado mientras se arrastra
const agarrado = (lado) => Number.isFinite(ultima[`servo_${lado}_deg`]);

function ponerServo(lado, grados) {
  $(`servo-${lado}`).value = grados;
  $(`objetivo-${lado}`).textContent = `${$(`servo-${lado}`).value}°`; // ya acotado a los límites
}

function mandarServo(lado) {
  clearTimeout(servoPendiente[lado]);
  servoPendiente[lado] = null;
  const v = Number($(`servo-${lado}`).value);
  if (v !== servoEnviado[lado]) enviar(`servo ${lado} ${v}`, true);
  servoEnviado[lado] = v;
}

for (const lado in LADOS) {
  const deslizador = $(`servo-${lado}`);
  deslizador.addEventListener('input', () => {
    ponerServo(lado, deslizador.value);
    // Suelto no hay rampa: mandar mientras se arrastra lo haría saltar por el camino.
    // Se manda una vez, al soltar.
    if (agarrado(lado)) servoPendiente[lado] ??= setTimeout(() => mandarServo(lado), PERIODO_SERVO_MS);
  });
  deslizador.addEventListener('change', () => mandarServo(lado)); // al soltar: el valor final
}

for (const b of document.querySelectorAll('[data-paso]')) {
  b.onclick = () => { // ±1/±5° desde el objetivo actual; el deslizador lo acota a los límites
    const [lado, paso] = b.dataset.paso.split(' ');
    if (!agarrado(lado)) return;
    ponerServo(lado, Number($(`servo-${lado}`).value) + Number(paso));
    servoEnviado[lado] = Number($(`servo-${lado}`).value);
    enviar(`servo ${lado} ${servoEnviado[lado]}`);
  };
}

for (const form of document.querySelectorAll('.servo .ir-a')) {
  const lado = form.closest('.servo').dataset.lado;
  form.onsubmit = (e) => {
    e.preventDefault();
    const v = Number(form.elements[0].value);
    ponerServo(lado, v);
    servoEnviado[lado] = v;
    enviar(`servo ${lado} ${v}`);
  };
}

for (const b of document.querySelectorAll('[data-servo]')) {
  b.onclick = () => { // soltar: la posición deja de conocerse
    const lado = b.dataset.servo.split(' ')[0];
    for (const l in LADOS) if (lado === l || !(lado in LADOS)) servoEnviado[l] = null;
    enviar(`servo ${b.dataset.servo}`);
  };
}

// Al conectar se piden los parámetros (llena umax)
let estabaConectado = false;
setInterval(() => {
  if (fuente && !estabaConectado) setTimeout(() => enviar('get', true), 600); // después del "tlm on"
  estabaConectado = Boolean(fuente);
}, 200);

// ---------- Pestañas ----------

function mostrarVista(id) {
  for (const b of document.querySelectorAll('[data-vista]')) {
    const activa = b.dataset.vista === id;
    b.setAttribute('aria-selected', String(activa));
    $(b.dataset.vista).hidden = !activa;
  }
  recordar('segway.vista', id);
}
for (const b of document.querySelectorAll('[data-vista]')) b.onclick = () => mostrarVista(b.dataset.vista);
mostrarVista(recuperar('segway.vista') === 'vista-graficos' ? 'vista-graficos' : 'banco');

for (const id of ['cpr', 'radio']) { // dependen del motor y la rueda: se recuerdan
  const guardado = recuperar(`segway.${id}`);
  if (guardado) $(id).value = guardado;
  $(id).addEventListener('change', () => { historiaEnc.length = 0; recordar(`segway.${id}`, $(id).value); });
}
