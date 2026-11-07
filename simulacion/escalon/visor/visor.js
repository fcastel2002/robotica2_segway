// Visor de la bajada de escalón: parámetros y programa de la maniobra, el robot animado, gráficos,
// comparación de corridas, barridos y robustez. Habla con visor.py, que corre banco_escalon (el
// código del firmware contra la planta plana).
'use strict';

// ---------------------------------------------------------------- definiciones
// [clave, nombre, unidad, paso, ayuda, opciones, botones]; las claves son las de "banco_escalon caso"
const GRUPOS = [
  ['Búsqueda del borde', [
    ['pata_busqueda', 'Patas al buscar', '°', 1, 'Altura de las patas mientras retrocede buscando el borde (el sensor necesita más de 10 cm al piso).'],
    ['v_busqueda', 'Velocidad al buscar', 'm/s', 0.01, 'Retrocede despacio hasta que el sensor ve el desnivel.'],
    ['desnivel', 'Desnivel que cuenta como borde', 'm', 0.01, 'El piso bajo el haz más abajo que esto es el borde. Para un escalón de 5 cm, 0,03.'],
    ['d_min', 'Distancia mínima para largar', 'm', 0.01, 'Si después de frenar quedó más cerca del borde que esto, aborta.'],
    ['avance', 'Avanzar antes de buscar', 'm', 0.01, 'Antes de buscar el borde, avanza esto hacia adelante (lejos del borde), para tener lugar para tomar envión. Sirve frenando en cada escalón.'],
  ]],
  ['Largada', [
    ['pata_largada', 'Patas al largar', '°', 1, 'Altura de las patas al acelerar hacia el borde. 0 = agachado (la cabina pega en el borde).'],
    ['v_salida', 'Velocidad de salida pedida', 'm/s', 0.01, 'Hacia atrás, al pasar el borde. La real depende de la batería; por debajo de ~0,45 m/s la cabina pega en el borde.'],
    ['a_salida_max', 'Aceleración máxima', 'm/s²', 0.1, 'Tope de la aceleración para llegar al borde a la velocidad de salida.'],
    ['ff', 'Comando anticipado (ff)', '1/(m/s)', 0.1, 'Comando a los motores por cada m/s pedido, que se suma al del LQR.'],
    ['kx_largada', 'kx al largar', '×', 0.1, 'Factor de la ganancia de posición mientras larga (0 = sin consigna de posición).'],
  ]],
  ['Borde y vuelo', [
    ['d_salto', 'Estirar las patas a', 'm del borde', 0.01, 'Distancia rueda-borde a la que estira las patas de golpe (el cuerpo sube y la cabina pasa más alta). Negativo: no estira antes de caer.'],
    ['pata_vuelo', 'Patas en el aire', '°', 1, 'Hasta dónde estira las patas en el borde y en el aire.'],
    ['vel_pata', 'Velocidad de las patas en el aire', '°/s', 10, 'Lo que se le pide al servo al estirar (el DS3240 da ~330 °/s).'],
    ['motor_vuelo', 'Motor en el aire', '', 1, 'Qué hacen las ruedas mientras el robot está en el aire.',
      [[0, 'rueda a la velocidad del piso'], [1, 'LQR, como en el piso'], [2, 'comando 0 (el L298N frena)']]],
  ]],
  ['Aterrizaje', [
    ['pata_final', 'Patas al tocar', '°', 1, 'Altura de las patas después de tocar el piso.'],
    ['vel_pata_final', 'Velocidad de las patas al tocar', '°/s', 10, 'Si es muy rápida, levanta la rueda del piso.'],
    ['a_frenado', 'Frenado', 'm/s²', 0.1, 'Al tocar, la velocidad pedida va a 0 con esta rampa.'],
    ['kx_aterrizaje', 'kx al tocar', '×', 0.1, 'Factor de la ganancia de posición al tocar (0 = queda donde frene).'],
    ['t_mantener', 'Rueda sostenida al tocar', 's', 0.01, 'Solo con «rueda a la velocidad del piso»: la sigue sosteniendo este tiempo después de tocar.'],
    ['t_sin_acel', 'Sin acelerómetro al tocar', 's', 0.01, 'El filtro de inclinación sigue solo con el giróscopo este tiempo después de tocar.'],
    ['t_continuo', 'Escalera sin frenar', 's', 0.1, 'Mayor que 0: baja la escalera entera sin frenar en cada escalón y frena cuando pasa este tiempo en el piso sin volver a caer. 0 = un escalón.'],
  ]],
  ['Escenario', [
    ['escalones', 'Escalones', '', 1, '1 = uno solo, con piso de sobra abajo; 0 = piso plano.'],
    ['repetir', 'Frenar en cada escalón', '', 1, 'Con varios escalones: cuando termina uno, la maniobra empieza de nuevo (como apretar △ otra vez, 1 s después de quedar quieto).',
      [[0, 'no: la maniobra una vez'], [1, 'sí: otra vez en cada escalón']]],
    ['alto', 'Alto del escalón', 'm', 0.01, 'La escalera del equipo: 18 cm.'],
    ['pisada', 'Pisada', 'm', 0.01, 'Largo de cada escalón (con más de uno).'],
    ['ultimo', 'Último escalón', 'm', 0.01, 'El alto del último escalón si es distinto (la escalera del equipo: 3 cm). 0 = como los otros.'],
    ['x0', 'Rueda al empezar', 'm del borde', 0.05, 'Dónde arranca el robot, antes de buscar el borde.'],
  ]],
  ['Robot y planta', [
    ['v_motor', 'Tensión al motor', 'V', 0.1, 'Lo que llega al motor con PWM 100 %: con el DRV8871, la LiPo (con el L298N se perdían ~2 V).', null,
      [['LiPo 12,6', 12.6], ['12,2', 12.2], ['11,8', 11.8], ['11,1', 11.1]]],
    ['zona_muerta', 'Zona muerta del motor', 'PWM', 0.01, 'Fracción del PWM que no mueve la rueda (DRV8871, medida el 6/11: 0,026; con el L298N, 0,14-0,19; el firmware compensa 0,05 quieto).'],
    ['mu', 'Fricción rueda-piso', 'μ', 0.05, 'Coulomb entre la goma y el piso.'],
    ['servo', 'Par de los servos', '×', 0.05, 'Factor del par de calado de los DS3240.'],
    ['recorte', 'Cabina recortada adelante', 'm', 0.01, 'Cuánto se acorta la cabina adelante (la parte que pega en el borde al bajar hacia atrás); el equipo puede sacarle hasta ~7 cm. La masa queda igual.'],
    ['f_masa', 'Masa de la caja', '×', 0.05, 'Factor de la masa (y la inercia) de la caja: 0,8 = 20 % más liviana.'],
    ['apoyo', 'La cabina en el escalón', '', 1, 'Si la cabina toca el escalón: choque, o que se pueda apoyar (vale si no golpea más de 150 N).',
      [[0, 'tocar es chocar'], [1, 'se puede apoyar']]],
    ['mu_cabina', 'Fricción de la cabina', 'μ', 0.05, 'Fricción de la cabina contra el escalón (0 = la de la rueda). Plástico contra madera: ~0,4.'],
    ['d_ref', 'Equilibrio corrido', '°', 0.25, 'La referencia del firmware corrida respecto del equilibrio real (como cuando la IMU se movió en una caída). + = hacia adelante.'],
    ['f_rotor', 'Inercia de los rotores', '×', 0.1, 'Factor de la inercia de los rotores de los motores (vista desde la rueda, por el reductor al cuadrado).'],
    ['f_inercia', 'Inercia del cuerpo', '×', 0.1, 'Factor de la inercia del cuerpo alrededor de su centro de masa.'],
    ['semilla', 'Ruido (semilla)', '', 1, 'Otra secuencia del ruido de los sensores.'],
  ]],
];

// Situaciones para probar de una: lo que cambian del escenario
const ESCALERA = { escalones: 7, alto: 0.166, pisada: 0.29, ultimo: 0.03 };     // la del equipo, medida el 3/11
const ESCENAS = [
  ['un escalón', { escalones: 1, alto: 0.166, ultimo: 0, repetir: 0, t_continuo: 0 }],
  ['la escalera, frenando en cada escalón', Object.assign({ repetir: 1, t_continuo: 0 }, ESCALERA)],
  ['la escalera de largo', Object.assign({ repetir: 0, t_continuo: 0.8 }, ESCALERA)],
];

// Las mejores maneras de bajar la escalera del equipo que encontró el algoritmo genético
// (genetico.py; las da el servidor): [nombre, parámetros]
let MEJORES = [];

// Eventos del programa (man_evento_t)
const EVENTOS = [['larga', 'al largar + s'], ['borde', 'a m del borde'], ['despega', 'al despegar + s'], ['toca', 'al tocar + s']];

// Los gráficos de una corrida: [título, unidad, [[columna, nombre, color, discontinua]]]
const GRAFICOS = [
  ['Cabeceo del cuerpo y patas', '°', [['th_deg', 'cabeceo', '#1f77b4'], ['pata_real_deg', 'pata', '#ff7f0e'],
    ['pata_pedida_deg', 'pata pedida', '#ff7f0e', true]]],
  ['Velocidad (+ adelante)', 'm/s', [['vx_ms', 'cuerpo', '#1f77b4'], ['odo_v_ms', 'rueda', '#2ca02c'],
    ['v_ref_ms', 'pedida', '#d62728', true]]],
  ['Comando a los motores', 'PWM', [['u', 'u', '#9467bd']]],
  ['Lo que ve el firmware', '°', [['theta_medido_deg', 'IMU', '#1f77b4'], ['ref_deg', 'referencia', '#d62728', true]]],
  ['Eje de la rueda', 'm', [['eje_x_m', 'x (0 = borde)', '#8c564b'], ['eje_z_m', 'altura', '#17becf']]],
  ['Sensor de distancia', 'm', [['dist_m', 'distancia medida', '#7f7f7f']]],
  ['Fuerza piso-rueda y cabina', 'N', [['n_rueda_N', 'rueda', '#e377c2'], ['n_cuerpo_N', 'cabina', '#d62728']]],
  ['Par de los servos', 'N·m', [['par_servo_Nm', 'los dos', '#bcbd22']]],
];

// Las señales que se pueden comparar: [columna, nombre, unidad]
const SENALES = [
  ['th_deg', 'cabeceo', '°'], ['pata_real_deg', 'pata', '°'], ['pata_pedida_deg', 'pata pedida', '°'],
  ['vx_ms', 'velocidad del cuerpo', 'm/s'], ['odo_v_ms', 'velocidad de la rueda', 'm/s'],
  ['v_ref_ms', 'velocidad pedida', 'm/s'], ['vz_ms', 'velocidad vertical', 'm/s'],
  ['u', 'comando a los motores', 'PWM'], ['theta_medido_deg', 'ángulo de la IMU', '°'], ['ref_deg', 'referencia', '°'],
  ['eje_x_m', 'x del eje (0 = borde)', 'm'], ['eje_z_m', 'altura del eje', 'm'], ['cm_z_m', 'altura del cuerpo', 'm'],
  ['n_rueda_N', 'fuerza piso-rueda', 'N'], ['n_cuerpo_N', 'fuerza en la cabina', 'N'],
  ['par_servo_Nm', 'par de los servos', 'N·m'], ['dist_m', 'sensor de distancia', 'm'],
];

// Lo que resume una corrida: [clave, nombre, unidad, decimales, factor, la mejor es la menor]
const METRICAS = [
  ['bajados', 'bajó', 'escalones', 0, 1, false],
  ['sale', 'velocidad al borde', 'm/s', 2, 1, false],
  ['toca', 'toca a', 'cm', 0, -0.1, false],
  ['fin', 'termina a', 'cm', 0, -0.1, false],
  ['min', 'lo más lejos', 'cm', 0, -0.1, false],
  ['desvio', 'desvío máximo', '°', 1, 1, true],
  ['pata_min', 'pata mínima', '°', 1, 1, false],
  ['servo', 'par de los servos', 'N·m', 1, 1, true],
  ['rueda', 'fuerza en la rueda', 'N', 0, 1, true],
  ['golpe', 'golpe en la IMU', 'g', 1, 1, true],
  ['borde_error', 'error del borde visto', 'mm', 0, 1, false],
  ['holgura', 'cabina a la escalera (lo más cerca)', 'mm', 0, 1, false],
];
const BARRAS = ['bajados', 'desvio', 'fin', 'sale', 'servo', 'rueda'];

// Rangos de barrido que tienen sentido (si no, ±30 % del valor); el tercero, los pasos
const RANGOS = {
  v_salida: [0.4, 0.7], pata_largada: [0, 30], pata_vuelo: [15, 30], pata_final: [10, 30], d_salto: [-0.05, 0.1],
  v_motor: [11.1, 12.6], d_ref: [-1.5, 1.5], a_frenado: [0.3, 2], vel_pata_final: [50, 1000], alto: [0.05, 0.2],
  x0: [0.3, 0.8], mu: [0.3, 1], zona_muerta: [0.01, 0.1], ff: [0.6, 1.4], a_salida_max: [0.3, 2],
  vel_pata: [100, 1000], pata_busqueda: [10, 30], t_mantener: [0, 0.1], kx_aterrizaje: [0, 1],
  kx_largada: [0, 1], servo: [0.5, 1.2], motor_vuelo: [0, 2, 3], escalones: [1, 4, 4], semilla: [0, 9, 10],
};

const COLOR_ESTADO = {
  inactiva: '#c9ced4', agachar: '#b9a7f0', avanzar: '#d4b9f0', buscar: '#9ecae1', preparar: '#6baed6', largar: '#fdae6b',
  vuelo: '#e6550d', aterrizar: '#74c476', fin: '#31a354', abortada: '#de2d26',
};
const EXES = { ajustada: 'banco_escalon_ajustada.exe', original: 'banco_escalon.exe' };
const NOMBRE_CLASE = ['queda parado', 'la cabina pega en el borde', 'se cae', 'no termina'];
const NOMBRE_CORTO = ['parado', 'choca', 'se cae', 'no termina'];
const PALETA = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#17becf', '#bcbd22', '#7f7f7f'];

// ---------------------------------------------------------------- estado
const E = {
  planta: 'ajustada', plantas: {}, defectos: {}, geoms: {},
  corridas: new Map(), historial: [], actual: null, comparar: new Set(),
  colores: new Map(), etiquetas: new Map(), nColores: 0,
  t: 0, reproduciendo: false, ultimo: null, ventana: 'largada', vista: 'corrida',
  alinear: 'largada', compVentana: 'corta', senales: ['th_deg', 'vx_ms', 'pata_real_deg', 'u', 'eje_z_m', 'n_rueda_N'],
  robusteces: [], nRobustez: 0, barrido: null,
};
let escena, graficos, estados, graficosComp = [], puntosBarrido = [];

// ---------------------------------------------------------------- utilidades
const $ = (id) => document.getElementById(id);
const css = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

function num(v, d = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  if (Math.abs(v) < 0.5 * Math.pow(10, -d)) v = 0;
  return v.toFixed(d).replace('.', ',').replace('-', '−');
}

// Un número para el banco: sin exponentes ni ceros de más
const textoNum = (x) => String(Number(Number(x).toFixed(4)));

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function aviso(texto, error = false) {
  const a = $('aviso');
  a.textContent = texto;
  a.classList.toggle('error', error);
}

async function api(ruta, cuerpo) {
  const opciones = cuerpo ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cuerpo) } : {};
  const r = await fetch(ruta, opciones);
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}

function viridis(f) {
  const p = [[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]];
  f = Math.min(Math.max(f, 0), 1) * (p.length - 1);
  const i = Math.min(Math.floor(f), p.length - 2), u = f - i;
  const c = p[i].map((a, k) => Math.round(a + (p[i + 1][k] - a) * u));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

// El índice de `a` (creciente) más cerca de t
function indiceEn(a, t) {
  const n = a.length;
  if (!n || t <= a[0]) return 0;
  if (t >= a[n - 1]) return n - 1;
  let lo = 0, hi = n - 1;
  while (hi - lo > 1) {
    const m = (lo + hi) >> 1;
    if (a[m] <= t) lo = m; else hi = m;
  }
  return t - a[lo] < a[hi] - t ? lo : hi;
}

function pasoLindo(rango, n) {
  const bruto = rango / n, p = Math.pow(10, Math.floor(Math.log10(bruto))), f = bruto / p;
  return (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * p;
}

// Prepara un canvas para dibujar en píxeles CSS (con `alto`, le fija la altura)
function lienzo(cv, alto) {
  const d = window.devicePixelRatio || 1;
  if (alto) cv.style.height = alto + 'px';
  const w = cv.clientWidth, h = alto || cv.clientHeight;
  cv.width = Math.round(w * d);
  cv.height = Math.round(h * d);
  const ctx = cv.getContext('2d');
  ctx.setTransform(d, 0, 0, d, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return [ctx, w, h];
}

// El piso hacia -X: arriba hasta el borde en X = 0 y n escalones (el último sigue)
function perfilPiso(p, xmin, xmax) {
  const n = Math.round(p.escalones);
  if (n <= 0) return [[xmax, 0], [xmin, 0]];
  // el último escalón puede ser de otra altura (la escalera del equipo: 3 cm)
  const nivel = (k) => (k < n || !(p.ultimo > 0)) ? -k * p.alto : -(n - 1) * p.alto - p.ultimo;
  const pts = [[xmax, 0], [0, 0]];
  for (let k = 1; k <= n; k++) {
    pts.push([-(k - 1) * p.pisada, nivel(k)], [k === n ? xmin : -k * p.pisada, nivel(k)]);
  }
  return pts;
}

function dibujarPiso(ctx, p, X, Z, xmin, xmax, fondo) {
  const pts = perfilPiso(p, xmin, xmax);
  ctx.beginPath();
  ctx.moveTo(X(pts[0][0]), Z(pts[0][1]));
  for (const [x, z] of pts) ctx.lineTo(X(x), Z(z));
  ctx.lineTo(X(xmin), Z(fondo));
  ctx.lineTo(X(xmax), Z(fondo));
  ctx.closePath();
  ctx.fillStyle = css('--piso');
  ctx.fill();
  ctx.beginPath();
  ctx.moveTo(X(pts[0][0]), Z(pts[0][1]));
  for (const [x, z] of pts) ctx.lineTo(X(x), Z(z));
  ctx.strokeStyle = css('--piso-linea');
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

// ---------------------------------------------------------------- corridas: colores y nombres
function colorDe(id) {
  if (!E.colores.has(id)) E.colores.set(id, PALETA[E.nColores++ % PALETA.length]);
  return E.colores.get(id);
}

function nombreDe(id) {
  const e = E.etiquetas.get(id);
  return e ? `#${id} ${e}` : `#${id}`;
}

function descParams(params, planta, completa = false) {
  const d = planta && planta !== 'ajustada' ? ['planta original'] : [];
  for (const [k, v] of Object.entries(params)) {
    if (k === 'patas' || k === 'vel') {
      const quien = k === 'patas' ? 'patas' : 'velocidad';
      d.push(completa ? `programa de ${quien}: ${v}` : `programa de ${quien} (${v.split('/').length})`);
    } else {
      d.push(`${k} ${String(v).replace('.', ',')}`);
    }
  }
  return d.join(' · ') || 'por defecto';
}

function descripcion(c, completa = false) {
  return (c.origen ? c.origen + ' · ' : '') + descParams(c.params, c.planta, completa);
}

function chip(clase, texto, chico = false) {
  return `<span class="chip c${clase}${chico ? ' chico' : ''}">${esc(texto)}</span>`;
}

// ---------------------------------------------------------------- formulario
function defectos() { return E.defectos[E.planta]; }
function numericos() { return Object.keys(defectos()).filter((k) => k !== 'patas' && k !== 'vel'); }
function valorForm(k) {
  const e = $('p_' + k);
  return e && e.value !== '' ? Number(e.value) : defectos()[k];
}

function cargarMejor(cambiosMejor) {
  for (const k of numericos()) if ($('p_' + k)) $('p_' + k).value = k in cambiosMejor ? cambiosMejor[k] : defectos()[k];
  cargarPrograma('patas', cambiosMejor.patas || '');
  cargarPrograma('vel', cambiosMejor.vel || '');
  alCambiar();
}

function armarFormulario() {
  const f = $('formulario');
  f.innerHTML = '';
  if (MEJORES.length) {
    const fs = document.createElement('fieldset');
    fs.innerHTML = '<legend>Las mejores para la escalera</legend><div class="presets"></div>' +
      '<p class="ayuda">Lo que encontró el algoritmo genético (genetico.py), con el robot como está hoy; cargan todo.</p>';
    for (const [nombre, c] of MEJORES) {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = nombre;
      b.addEventListener('click', () => cargarMejor(c));
      fs.querySelector('.presets').appendChild(b);
    }
    f.appendChild(fs);
  }
  for (const [titulo, params] of GRUPOS) {
    const fs = document.createElement('fieldset');
    fs.innerHTML = `<legend>${titulo}</legend>`;
    for (const [k, nombre, unidad, paso, ayuda, opciones, botones] of params) {
      if (!(k in defectos())) continue;
      const d = document.createElement('div');
      d.className = 'param' + (opciones ? ' ancho' : '');
      d.dataset.k = k;
      const id = 'p_' + k;
      const etiqueta = `<label for="${id}" title="${ayuda}\n(${k})">${nombre}${unidad ? ` <span class="unidad">[${unidad}]</span>` : ''}</label>`;
      if (opciones) {
        d.innerHTML = etiqueta + `<select id="${id}">${opciones.map(([v, t]) => `<option value="${v}">${t}</option>`).join('')}</select>`;
      } else {
        d.innerHTML = etiqueta + `<input id="${id}" type="number" step="${paso}">`;
      }
      d.insertAdjacentHTML('beforeend', `<span class="defecto"></span>`);
      if (botones) {
        d.insertAdjacentHTML('beforeend', `<div class="presets">${botones.map(([t, v]) => `<button type="button" data-v="${v}">${t}</button>`).join('')}</div>`);
        d.querySelectorAll('.presets button').forEach((b) => b.addEventListener('click', () => {
          $(id).value = b.dataset.v;
          alCambiar();
        }));
      }
      fs.appendChild(d);
      if (k === 'escalones') {
        // Botones para las situaciones de escalera
        const b = document.createElement('div');
        b.className = 'presets';
        b.innerHTML = ESCENAS.map(([t], j) => `<button type="button" data-escena="${j}">${t}</button>`).join('');
        b.querySelectorAll('button').forEach((x) => x.addEventListener('click', () => {
          for (const [kk, v] of Object.entries(ESCENAS[Number(x.dataset.escena)][1])) if ($('p_' + kk)) $('p_' + kk).value = v;
          alCambiar();
        }));
        fs.insertBefore(b, d);
      }
      const entrada = d.querySelector('input, select');
      entrada.value = defectos()[k];
      entrada.addEventListener('input', alCambiar);
      entrada.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') simular(); });
    }
    f.appendChild(fs);
  }
  armarTablaPrograma('patas');
  armarTablaPrograma('vel');
  try {
    const g = JSON.parse(localStorage.getItem('visor-escalon:' + E.planta) || '{}');
    const cambiados = g.c || g;                 // antes se guardaban solo los cambios
    for (const [k, v] of Object.entries(cambiados)) if (k !== 'patas' && k !== 'vel' && $('p_' + k)) $('p_' + k).value = v;
    cargarPrograma('patas', g.patas || '');
    cargarPrograma('vel', g.vel || '');
  } catch (e) { /* sin almacenamiento: quedan los de por defecto */ }
  alCambiar();
}

function cambios() {
  const c = {};
  for (const k of numericos()) {
    const e = $('p_' + k);
    if (!e || e.value === '') continue;
    const x = Number(e.value);
    if (Number.isFinite(x) && Math.abs(x - defectos()[k]) > 1e-9) c[k] = x;
  }
  const patas = textoPrograma('patas'), vel = textoPrograma('vel');
  if (patas) c.patas = patas;
  if (vel) c.vel = vel;
  return c;
}

function alCambiar() {
  const c = cambios();
  document.querySelectorAll('.param').forEach((d) => {
    const k = d.dataset.k;
    d.classList.toggle('cambiado', k in c);
    const op = GRUPOS.flatMap((g) => g[1]).find((p) => p[0] === k)[5];
    const v = defectos()[k];
    d.querySelector('.defecto').textContent = 'por defecto: ' + (op ? op.find((o) => o[0] === v)?.[1] ?? v : String(v).replace('.', ','));
  });
  const prog = [];
  if (c.patas) prog.push(`patas: ${c.patas.split('/').length}`);
  if (c.vel) prog.push(`velocidad: ${c.vel.split('/').length}`);
  $('programa-estado').textContent = prog.length ? '· ' + prog.join(' · ') : '';
  // la tensión al motor va siempre: el visor arranca con la LiPo cargada y el banco, con la de la planta
  const todos = Object.assign({ v_motor: defectos().v_motor }, c);
  $('comando').textContent = `simulacion/escalon/${EXES[E.planta]} caso ` +
    Object.entries(todos).map(([k, v]) => (k === 'patas' || k === 'vel') ? `"${k}=${v}"` : `${k}=${v}`).join(' ') + ' csv=prueba';
  try {
    const { patas, vel, ...resto } = c;
    localStorage.setItem('visor-escalon:' + E.planta, JSON.stringify({ c: resto, patas: patas || '', vel: vel || '' }));
  } catch (e) { /* nada */ }
}

// ---------------------------------------------------------------- programa
function armarTablaPrograma(cual) {
  $('prog-' + cual).innerHTML = '<colgroup><col style="width:34%"><col style="width:19%"><col style="width:19%">' +
    '<col style="width:20%"><col style="width:8%"></colgroup>' +
    `<tr><th>cuándo</th><th>s o m</th><th>${cual === 'patas' ? 'patas [°]' : 'v [m/s]'}</th>` +
    `<th>${cual === 'patas' ? 'a [°/s]' : 'con [m/s²]'}</th><th></th></tr>`;
}

function filaPrograma(cual, [ev, valor, objetivo, ritmo]) {
  const tr = document.createElement('tr');
  tr.innerHTML = `<td><select>${EVENTOS.map(([k, n]) => `<option value="${k}">${n}</option>`).join('')}</select></td>
    <td><input type="number" step="0.01" class="valor" title="Segundos después del evento o, con «a (m) del borde», distancia de la rueda al borde (+ antes, − pasado)"></td>
    <td><input type="number" step="${cual === 'patas' ? 1 : 0.01}" class="obj"></td>
    <td><input type="number" step="${cual === 'patas' ? 10 : 0.1}" min="0" class="ritmo"></td>
    <td><button type="button" title="Sacar esta acción">×</button></td>`;
  tr.querySelector('select').value = ev;
  tr.querySelector('.valor').value = valor;
  tr.querySelector('.obj').value = objetivo;
  tr.querySelector('.ritmo').value = ritmo;
  tr.querySelector('select').addEventListener('change', alCambiar);
  tr.querySelectorAll('input').forEach((i) => i.addEventListener('input', alCambiar));
  tr.querySelector('button').addEventListener('click', () => { tr.remove(); alCambiar(); });
  $('prog-' + cual).appendChild(tr);
}

function textoPrograma(cual) {
  const partes = [];
  for (const tr of [...$('prog-' + cual).querySelectorAll('tr')].slice(1)) {
    const entradas = [...tr.querySelectorAll('input')];
    if (entradas.some((i) => i.value === '' || !Number.isFinite(Number(i.value)))) continue;
    const [valor, objetivo, ritmo] = entradas.map((i) => Number(i.value));
    partes.push(`${tr.querySelector('select').value}:${textoNum(valor)}:${textoNum(objetivo)}:${textoNum(Math.abs(ritmo))}`);
  }
  return partes.join('/');
}

function cargarPrograma(cual, texto) {
  armarTablaPrograma(cual);
  if (!texto) return;
  for (const a of texto.split('/')) {
    const [ev, valor, objetivo, ritmo] = a.split(':');
    filaPrograma(cual, [ev, Number(valor), Number(objetivo), Number(ritmo)]);
  }
}

// Las acciones que hace la maniobra con los parámetros del formulario
function programaPorDefecto(cual) {
  if (cual === 'vel') return [['larga', 0, valorForm('v_salida'), 0.6], ['toca', 0, 0, valorForm('a_frenado')]];
  const a = [];
  if (valorForm('d_salto') >= 0) a.push(['borde', valorForm('d_salto'), valorForm('pata_vuelo'), valorForm('vel_pata')]);
  a.push(['despega', 0, valorForm('pata_vuelo'), valorForm('vel_pata')]);
  a.push(['toca', 0, valorForm('pata_final'), valorForm('vel_pata_final')]);
  return a;
}

function hacerPrograma(cual, que) {
  if (que === 'mas') {
    const n = $('prog-' + cual).querySelectorAll('tr').length - 1;
    const ev = ['larga', 'borde', 'despega', 'toca'][Math.min(n, 3)];
    filaPrograma(cual, cual === 'patas' ? [ev, ev === 'borde' ? 0.03 : 0, valorForm('pata_largada'), 300]
      : [ev, ev === 'borde' ? 0.03 : 0, valorForm('v_salida'), 0.6]);
  } else {
    armarTablaPrograma(cual);
    if (que === 'defecto') programaPorDefecto(cual).forEach((a) => filaPrograma(cual, a));
    if (que === 'nunca') filaPrograma('patas', ['larga', 0, valorForm('pata_largada'), 100]);
  }
  alCambiar();
}

function usarParametros(id) {
  const c = E.corridas.get(id);
  if (c.planta !== E.planta) {
    aviso('Esa corrida es de la otra planta: elegila arriba primero.', true);
    return;
  }
  for (const k of numericos()) if ($('p_' + k)) $('p_' + k).value = k in c.params ? c.params[k] : defectos()[k];
  cargarPrograma('patas', c.params.patas || '');
  cargarPrograma('vel', c.params.vel || '');
  if (c.params.patas || c.params.vel) $('programa').open = true;
  alCambiar();
  aviso(`los parámetros de ${nombreDe(id)} quedaron a la izquierda`);
}

// ---------------------------------------------------------------- corridas
function preparar(c) {
  const D = c.datos;
  c.n = D.t_s.length;
  const primero = (est) => { const i = D.estado.indexOf(est); return i >= 0 ? D.t_s[i] : null; };
  c.eventos = { largada: primero('largar'), despegue: primero('vuelo'), toque: primero('aterrizar'), borde: null };
  if (c.eventos.largada !== null) {
    for (let i = 0; i < c.n; i++) {
      if (D.t_s[i] >= c.eventos.largada && D.eje_x_m[i] < 0) { c.eventos.borde = D.t_s[i]; break; }
    }
  }
  c.iLargar = D.estado.indexOf('largar');
  let i0 = c.iLargar >= 0 ? c.iLargar : D.estado.indexOf('buscar');
  if (i0 < 0) i0 = 0;
  c.t0 = D.t_s[i0];
  c.tRel = D.t_s.map((t) => t - c.t0);
  c.p = Object.assign({}, E.defectos[c.planta], c.params);
  for (const k of Object.keys(c.p)) if (k !== 'patas' && k !== 'vel') c.p[k] = Number(c.p[k]);
  c.alineado = {};
  return c;
}

// Los tiempos de una corrida con el cero en un evento (si no pasó, en la largada)
function tiempos(c, modo) {
  if (!c.alineado[modo]) {
    const t0 = c.eventos[modo] ?? c.eventos.largada ?? c.t0;
    c.alineado[modo] = c.datos.t_s.map((t) => t - t0);
  }
  return c.alineado[modo];
}

function actual() { return E.corridas.get(E.actual) || null; }
function indice(c, t) { return indiceEn(c.tRel, t); }
function conjunto() {
  return [...new Set([E.actual, ...E.comparar])].filter((id) => id !== null && E.corridas.has(id)).map((id) => E.corridas.get(id));
}

function ventana(c) {
  if (E.ventana === 'toda' || c.iLargar < 0) return [c.tRel[0], c.tRel[c.n - 1]];
  return [Math.max(c.tRel[0], -1.0), Math.min(c.tRel[c.n - 1], 3.0)];
}

async function traer(id) {
  if (!E.corridas.has(id)) E.corridas.set(id, preparar(await api('/api/corrida?id=' + id)));
  return E.corridas.get(id);
}

function agregarAlHistorial(id, origen) {
  const c = E.corridas.get(id);
  if (origen && !c.origen) c.origen = origen;
  if (!E.historial.includes(id)) E.historial.unshift(id);
  colorDe(id);
}

async function simular() {
  const b = $('simular');
  if (b.disabled) return;
  b.disabled = true;
  aviso('simulando…');
  try {
    const c = preparar(await api('/api/simular', { planta: E.planta, params: cambios() }));
    E.corridas.set(c.id, c);
    agregarAlHistorial(c.id);
    ponerVista('corrida');
    ver(c.id, true);
    aviso(`corrida #${c.id}: ${NOMBRE_CLASE[c.resumen.clase]}`);
  } catch (e) {
    aviso(e.message, true);
  } finally {
    b.disabled = false;
  }
}

async function probarRobustez() {
  const b = $('probar-robustez');
  if (b.disabled) return;
  b.disabled = true;
  aviso('probando la robustez (27 casos)…');
  try {
    const params = cambios();
    const r = await api('/api/robustez', { planta: E.planta, params });
    E.robusteces.unshift(Object.assign(r, { params, planta: E.planta, n: ++E.nRobustez }));
    E.robusteces = E.robusteces.slice(0, 4);
    dibujarRobustez();
    aviso(`robustez R${E.nRobustez}: ${r.bien} de ${r.filas.length} quedan parados`);
  } catch (e) {
    aviso(e.message, true);
  } finally {
    b.disabled = false;
  }
}

async function barrer() {
  const b = $('barrer');
  if (b.disabled) return;
  const param = $('barrer-param').value;
  const barrer = { param, desde: Number($('barrer-desde').value), hasta: Number($('barrer-hasta').value), pasos: Number($('barrer-pasos').value) };
  b.disabled = true;
  aviso(`barriendo ${param} (${barrer.pasos} corridas)…`);
  try {
    const params = cambios();
    delete params[param];
    const r = await api('/api/barrido', { planta: E.planta, params, barrer });
    E.barrido = Object.assign(r, { params, planta: E.planta });
    dibujarBarrido();
    const bien = r.puntos.filter((p) => p.resumen.clase === 0).length;
    aviso(`barrido de ${param}: ${bien} de ${r.puntos.length} quedan parados`);
  } catch (e) {
    aviso(e.message, true);
  } finally {
    b.disabled = false;
  }
}

async function verDeOtroLado(id, origen) {
  try {
    await traer(id);
    agregarAlHistorial(id, origen);
    ponerVista('corrida');
    ver(id);
  } catch (e) {
    aviso(e.message, true);
  }
}

function ver(id, reproducir = false) {
  E.actual = id;
  E.comparar.delete(id);
  const c = actual();
  $('vacio').style.display = 'none';
  $('tiempo').min = c.tRel[0];
  $('tiempo').max = c.tRel[c.n - 1];
  escena.encuadrar(c);
  E.t = c.iLargar >= 0 ? Math.max(c.tRel[0], -0.6) : c.tRel[0];
  dibujarTodo();
  if (reproducir) reproducir_(); else actualizarTiempo();
}

function quitarCorrida(id) {
  E.historial = E.historial.filter((x) => x !== id);
  E.comparar.delete(id);
  if (E.actual === id) {
    if (E.historial.length) {
      ver(E.historial[0]);
      return;
    }
    E.actual = null;
    pausar();
    $('vacio').style.display = '';
    escena.dibujar();
    $('resumen').innerHTML = '';
  }
  dibujarTodo();
}

function alternarComparar(id, si) {
  if (si) E.comparar.add(id); else E.comparar.delete(id);
  dibujarHistorial();
  escena.dibujar();
  if (E.vista === 'comparar') dibujarComparar();
}

function dibujarTodo() {
  dibujarResumen();
  dibujarHistorial();
  dibujarRobustez();
  redibujarGraficos();
  if (E.vista === 'comparar') dibujarComparar();
  if (E.vista === 'barrido') dibujarBarrido();
}

// ---------------------------------------------------------------- vistas
function ponerVista(v) {
  if (E.vista === v) return;
  E.vista = v;
  document.querySelectorAll('.pestanas button').forEach((b) => b.classList.toggle('activa', b.dataset.vista === v));
  for (const n of ['corrida', 'comparar', 'barrido']) $('vista-' + n).hidden = n !== v;
  requestAnimationFrame(redimensionar);
}

// ---------------------------------------------------------------- reproducción
function reproducir_() {
  const c = actual();
  if (!c) return;
  if (E.t >= c.tRel[c.n - 1]) E.t = c.iLargar >= 0 ? Math.max(c.tRel[0], -0.6) : c.tRel[0];
  E.reproduciendo = true;
  E.ultimo = null;
  $('play').textContent = '❚❚';
  requestAnimationFrame(cuadro);
}

function pausar() {
  E.reproduciendo = false;
  $('play').textContent = '▶';
}

function cuadro(ahora) {
  if (!E.reproduciendo) return;
  const c = actual();
  if (!c) return pausar();
  if (E.ultimo !== null) E.t += (ahora - E.ultimo) / 1000 * Number($('velocidad').value);
  E.ultimo = ahora;
  if (E.t >= c.tRel[c.n - 1]) {
    E.t = c.tRel[c.n - 1];
    pausar();
  }
  actualizarTiempo();
  if (E.reproduciendo) requestAnimationFrame(cuadro);
}

function irA(t) {
  const c = actual();
  if (!c) return;
  E.t = Math.min(Math.max(t, c.tRel[0]), c.tRel[c.n - 1]);
  actualizarTiempo();
}

function actualizarTiempo() {
  const c = actual();
  if (!c) return;
  const i = indice(c, E.t);
  $('tiempo').value = E.t;
  $('reloj').textContent = `${num(E.t, 2)} s ${c.iLargar >= 0 ? 'desde que larga' : ''} · ${c.datos.estado[i]}`;
  escena.dibujar();
  for (const g of graficos) g.g.cursor(E.t);
  estados.dibujar();
  if (E.vista === 'comparar' && E.alinear === 'largada') for (const g of graficosComp) g.cursor(E.t);
}

// ---------------------------------------------------------------- escena
class Escena {
  constructor(cv) {
    this.c = cv;
    this.ctx = cv.getContext('2d');
    this.dimensionar();
  }

  dimensionar() {
    const r = this.c.getBoundingClientRect();
    this.d = window.devicePixelRatio || 1;
    this.w = r.width;
    this.h = r.height;
    this.c.width = Math.round(r.width * this.d);
    this.c.height = Math.round(r.height * this.d);
  }

  encuadrar(c) {
    const D = c.datos;
    let x0 = -0.15, x1 = 0.15, z0 = 0, z1 = 0;
    for (let i = 0; i < c.n; i++) {
      x0 = Math.min(x0, D.eje_x_m[i], D.cm_x_m[i]);
      x1 = Math.max(x1, D.eje_x_m[i], D.cm_x_m[i]);
      z0 = Math.min(z0, D.eje_z_m[i]);
      z1 = Math.max(z1, D.cm_z_m[i]);
    }
    x0 -= 0.2; x1 += 0.2; z0 -= 0.1; z1 += 0.17;
    const e = Math.min(this.w / (x1 - x0), this.h / (z1 - z0));
    this.esc = e;
    this.ox = (this.w - e * (x1 - x0)) / 2 - e * x0;
    this.oz = (this.h - e * (z1 - z0)) / 2 + e * z1;
    this.xmin = -this.ox / e;
    this.xmax = (this.w - this.ox) / e;
    this.zmin = (this.oz - this.h) / e;
  }

  X(x) { return this.ox + this.esc * x; }
  Z(z) { return this.oz - this.esc * z; }

  dibujar() {
    const ctx = this.ctx;
    ctx.setTransform(this.d, 0, 0, this.d, 0, 0);
    ctx.clearRect(0, 0, this.w, this.h);
    const c = actual();
    if (!c || !this.esc) return;
    const G = E.geoms[c.planta];
    dibujarPiso(ctx, c.p, (x) => this.X(x), (z) => this.Z(z), this.xmin - 1, this.xmax + 1, this.zmin - 1);
    this.escala();
    const i = indice(c, E.t);
    if ($('estela').checked) {
      const t0 = Math.max(c.iLargar >= 0 ? 0 : c.tRel[0], E.t - 3);
      const tf = Math.max(E.t, t0 + 1e-3);
      for (let t = t0; t < E.t - 0.015; t += 0.03) {
        this.robot(c.datos, indice(c, t), G, { color: viridis((t - t0) / (tf - t0)), alfa: 0.35, recorte: c.p.recorte });
      }
    }
    for (const id of E.comparar) {
      const k = E.corridas.get(id);
      if (k) this.robot(k.datos, indice(k, E.t), E.geoms[k.planta], { color: colorDe(id), alfa: 0.9, ancho: 2, recorte: k.p.recorte });
    }
    this.robot(c.datos, i, G, { color: css('--robot'), alfa: 1, ancho: 2, relleno: true, haz: $('ver-haz').checked, adelante: true, recorte: c.p.recorte });
    this.textos(c, i);
  }

  escala() {
    const ctx = this.ctx, x = this.xmin + 0.04, z = this.zmin + 0.04;
    ctx.strokeStyle = css('--piso-linea');
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(this.X(x), this.Z(z));
    ctx.lineTo(this.X(x + 0.1), this.Z(z));
    ctx.stroke();
    ctx.fillStyle = css('--suave');
    ctx.font = '11px system-ui, sans-serif';
    ctx.fillText('10 cm', this.X(x), this.Z(z) - 5);
  }

  robot(D, i, G, o) {
    const ctx = this.ctx;
    const th = D.th_deg[i] * Math.PI / 180, ct = Math.cos(th), st = Math.sin(th);
    const cx = D.cm_x_m[i], cz = D.cm_z_m[i];
    const rot = (x, z) => [cx + x * ct + z * st, cz - x * st + z * ct];
    const xs = G.puntos.map((p) => p[0]), zs = G.puntos.map((p) => p[1]);
    const bx0 = Math.min(...xs), bx1 = Math.max(...xs) - (o.recorte || 0), bz0 = Math.min(...zs), bz1 = Math.max(...zs);
    ctx.save();
    ctx.globalAlpha = o.alfa;
    ctx.strokeStyle = o.color;
    ctx.lineWidth = o.ancho || 1;
    // cabina
    ctx.beginPath();
    [[bx0, bz0], [bx1, bz0], [bx1, bz1], [bx0, bz1]].forEach(([x, z], k) => {
      const [wx, wz] = rot(x, z);
      if (k === 0) ctx.moveTo(this.X(wx), this.Z(wz)); else ctx.lineTo(this.X(wx), this.Z(wz));
    });
    ctx.closePath();
    if (o.relleno) {
      ctx.fillStyle = o.color;
      ctx.globalAlpha = 0.12;
      ctx.fill();
      ctx.globalAlpha = o.alfa;
    }
    ctx.stroke();
    // pata: del eje del servo al eje de la rueda
    const [ax, az] = rot(G.a_x, G.a_z);
    const ex = D.eje_x_m[i], ez = D.eje_z_m[i];
    ctx.beginPath();
    ctx.moveTo(this.X(ax), this.Z(az));
    ctx.lineTo(this.X(ex), this.Z(ez));
    ctx.stroke();
    // rueda, con dos rayos para verla girar
    const r = G.r_rueda;
    ctx.beginPath();
    ctx.arc(this.X(ex), this.Z(ez), r * this.esc, 0, 2 * Math.PI);
    ctx.stroke();
    if (D.rueda_deg && (o.relleno || o.ancho >= 2)) {
      const f = D.rueda_deg[i] * Math.PI / 180;
      for (const g of [f, f + Math.PI / 2]) {
        const dx = r * Math.cos(g), dz = -r * Math.sin(g);
        ctx.beginPath();
        ctx.moveTo(this.X(ex - dx), this.Z(ez - dz));
        ctx.lineTo(this.X(ex + dx), this.Z(ez + dz));
        ctx.stroke();
      }
    }
    if (o.relleno) {
      ctx.beginPath();
      ctx.arc(this.X(cx), this.Z(cz), 3.5, 0, 2 * Math.PI);
      ctx.fillStyle = o.color;
      ctx.fill();
    }
    if (o.haz) {
      const [sx, sz] = rot(G.sensor_x, G.sensor_z);
      const b = G.sensor_ang + th, ux = -Math.sin(b), uz = -Math.cos(b);
      const d = D.dist_m[i];
      ctx.beginPath();
      ctx.moveTo(this.X(sx), this.Z(sz));
      ctx.strokeStyle = css('--haz');
      ctx.lineWidth = 1.5;
      if (d !== null) {
        ctx.lineTo(this.X(sx + d * ux), this.Z(sz + d * uz));
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(this.X(sx + d * ux), this.Z(sz + d * uz), 3, 0, 2 * Math.PI);
        ctx.fillStyle = css('--haz');
        ctx.fill();
      } else {
        ctx.setLineDash([4, 4]);
        ctx.lineTo(this.X(sx + 0.12 * ux), this.Z(sz + 0.12 * uz));
        ctx.stroke();
        ctx.setLineDash([]);
      }
    }
    if (o.adelante) {
      const [px, pz] = rot(bx1 + 0.015, (bz0 + bz1) / 2), [qx, qz] = rot(bx1 + 0.06, (bz0 + bz1) / 2);
      ctx.strokeStyle = css('--suave');
      ctx.fillStyle = css('--suave');
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(this.X(px), this.Z(pz));
      ctx.lineTo(this.X(qx), this.Z(qz));
      ctx.stroke();
      const a = Math.atan2(this.Z(qz) - this.Z(pz), this.X(qx) - this.X(px));
      ctx.beginPath();
      ctx.moveTo(this.X(qx), this.Z(qz));
      ctx.lineTo(this.X(qx) - 7 * Math.cos(a - 0.4), this.Z(qz) - 7 * Math.sin(a - 0.4));
      ctx.lineTo(this.X(qx) - 7 * Math.cos(a + 0.4), this.Z(qz) - 7 * Math.sin(a + 0.4));
      ctx.closePath();
      ctx.fill();
      ctx.font = '11px system-ui, sans-serif';
      ctx.fillText('frente', this.X(qx) + 4, this.Z(qz) + 4);
    }
    ctx.restore();
  }

  textos(c, i) {
    const ctx = this.ctx, D = c.datos, est = D.estado[i];
    ctx.font = '600 13px system-ui, sans-serif';
    ctx.fillStyle = COLOR_ESTADO[est] || '#999';
    ctx.fillRect(12, 12, 10, 10);
    ctx.fillStyle = css('--texto');
    ctx.fillText(`${nombreDe(c.id)} · ${est}`, 28, 22);
    ctx.font = '12px system-ui, sans-serif';
    ctx.fillStyle = css('--suave');
    const lineas = [
      `velocidad ${num(D.vx_ms[i], 2)} m/s · rueda ${num(D.odo_v_ms[i], 2)} m/s`,
      `cabeceo ${num(D.th_deg[i], 1)}° · pata ${num(D.pata_real_deg[i], 1)}° · u ${num(D.u[i], 2)}`,
      `eje a ${num(D.eje_x_m[i] * 100, 1)} cm del borde, ${num(D.eje_z_m[i] * 100, 1)} cm de alto`,
    ];
    lineas.forEach((l, k) => ctx.fillText(l, 12, 42 + 16 * k));
    let y = 42 + 16 * lineas.length;
    for (const id of E.comparar) {
      if (!E.corridas.has(id)) continue;
      ctx.fillStyle = colorDe(id);
      ctx.fillText(`${nombreDe(id)} (comparada)`, 12, y);
      y += 16;
    }
  }
}

// ---------------------------------------------------------------- gráficos
// Un gráfico de líneas: trazos = [{t, y, color, nombre, discontinua, alfa, ancho}]
class Grafico {
  constructor(cont, titulo, unidad, alClic) {
    this.titulo = titulo;
    this.unidad = unidad;
    this.trazos = [];
    this.v = null;
    this.tCursor = null;
    this.raton = null;
    this.div = document.createElement('div');
    this.div.className = 'grafico';
    this.base = document.createElement('canvas');
    this.capa = document.createElement('canvas');
    this.capa.className = 'capa';
    this.div.append(this.base, this.capa);
    cont.appendChild(this.div);
    this.capa.addEventListener('click', (ev) => { if (this.v && alClic) alClic(this.tDe(ev.offsetX)); });
    this.capa.addEventListener('mousemove', (ev) => { this.raton = ev.offsetX; this.cursor(this.tCursor); });
    this.capa.addEventListener('mouseleave', () => { this.raton = null; this.cursor(this.tCursor); });
  }

  X(t) { return this.L + (t - this.v[0]) / (this.v[1] - this.v[0]) * (this.w - this.L - 8); }
  tDe(px) { return this.v[0] + (px - this.L) / (this.w - this.L - 8) * (this.v[1] - this.v[0]); }
  Y(y) { return 20 + (1 - (y - this.y0) / (this.y1 - this.y0)) * (this.h - 20 - 18); }

  dibujar(trazos, v) {
    this.trazos = trazos;
    this.v = v;
    const r = this.div.getBoundingClientRect();
    this.d = window.devicePixelRatio || 1;
    this.w = r.width;
    this.h = r.height;
    for (const cv of [this.base, this.capa]) {
      cv.width = Math.round(r.width * this.d);
      cv.height = Math.round(r.height * this.d);
    }
    const ctx = this.base.getContext('2d');
    ctx.setTransform(this.d, 0, 0, this.d, 0, 0);
    ctx.clearRect(0, 0, this.w, this.h);
    if (!v || !trazos.length || this.w < 50) { this.v = null; this.cursor(null); return; }
    let y0 = Infinity, y1 = -Infinity;
    for (const tr of trazos) {
      const a = indiceEn(tr.t, v[0]), b = indiceEn(tr.t, v[1]);
      for (let i = a; i <= b; i++) {
        const y = tr.y[i];
        if (y !== null && y !== undefined) { y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
      }
    }
    if (!Number.isFinite(y0)) { y0 = -1; y1 = 1; }
    if (y1 - y0 < 1e-6) { y0 -= 0.5; y1 += 0.5; }
    const m = (y1 - y0) * 0.06;
    this.y0 = y0 - m;
    this.y1 = y1 + m;
    this.L = 44;
    ctx.font = '10px system-ui, sans-serif';
    ctx.strokeStyle = css('--grilla');
    ctx.fillStyle = css('--suave');
    ctx.lineWidth = 1;
    const py = pasoLindo(this.y1 - this.y0, 4), dy = Math.max(0, -Math.floor(Math.log10(py)));
    for (let y = Math.ceil(this.y0 / py) * py; y <= this.y1; y += py) {
      ctx.beginPath(); ctx.moveTo(this.L, this.Y(y)); ctx.lineTo(this.w - 8, this.Y(y)); ctx.stroke();
      ctx.fillText(num(y, dy), 2, this.Y(y) + 3);
    }
    const pt = pasoLindo(v[1] - v[0], 6), dt = Math.max(0, -Math.floor(Math.log10(pt)));
    for (let t = Math.ceil(v[0] / pt) * pt; t <= v[1] + 1e-9; t += pt) {
      ctx.beginPath(); ctx.moveTo(this.X(t), 20); ctx.lineTo(this.X(t), this.h - 18); ctx.stroke();
      ctx.fillText(num(t, dt), this.X(t) - 8, this.h - 5);
    }
    if (this.y0 < 0 && this.y1 > 0) {
      ctx.strokeStyle = css('--suave');
      ctx.globalAlpha = 0.4;
      ctx.beginPath(); ctx.moveTo(this.L, this.Y(0)); ctx.lineTo(this.w - 8, this.Y(0)); ctx.stroke();
      ctx.globalAlpha = 1;
    }
    ctx.save();
    ctx.beginPath();
    ctx.rect(this.L, 18, this.w - this.L - 8, this.h - 36);
    ctx.clip();
    for (const tr of trazos) this.trazo(ctx, tr);
    ctx.restore();
    this.cursor(this.tCursor);
  }

  trazo(ctx, tr) {
    const a = Math.max(0, indiceEn(tr.t, this.v[0]) - 1), b = Math.min(tr.t.length - 1, indiceEn(tr.t, this.v[1]) + 1);
    ctx.strokeStyle = tr.color;
    ctx.globalAlpha = tr.alfa ?? 1;
    ctx.lineWidth = tr.ancho ?? 1.5;
    ctx.setLineDash(tr.discontinua ? [5, 3] : []);
    ctx.beginPath();
    let enLinea = false;
    for (let i = a; i <= b; i++) {
      const y = tr.y[i];
      if (y === null || y === undefined) { enLinea = false; continue; }
      const x = this.X(tr.t[i]), yy = this.Y(y);
      if (enLinea) ctx.lineTo(x, yy); else ctx.moveTo(x, yy);
      enLinea = true;
    }
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
  }

  cursor(t) {
    this.tCursor = t;
    const ctx = this.capa.getContext('2d');
    ctx.setTransform(this.d || 1, 0, 0, this.d || 1, 0, 0);
    ctx.clearRect(0, 0, this.w || 0, this.h || 0);
    if (!this.v) return;
    // los valores de la leyenda: en el instante del mouse si está encima, si no en el cursor
    let tl = t;
    if (this.raton !== null && this.raton > this.L) {
      tl = this.tDe(this.raton);
      ctx.strokeStyle = css('--suave');
      ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(this.raton, 20); ctx.lineTo(this.raton, this.h - 18); ctx.stroke();
      ctx.setLineDash([]);
    }
    ctx.font = '600 11px system-ui, sans-serif';
    ctx.fillStyle = css('--texto');
    const titulo = `${this.titulo} [${this.unidad}]`;
    ctx.fillText(titulo, this.L, 12);
    let x = this.L + ctx.measureText(titulo).width + 10;
    ctx.font = '11px system-ui, sans-serif';
    for (const tr of this.trazos) {
      let texto = tr.nombre;
      if (tl !== null && tl !== undefined) {
        const v = tr.y[indiceEn(tr.t, tl)];
        texto += ' ' + (v === null || v === undefined ? '—' : num(v, Math.abs(v) >= 100 ? 0 : 2));
      }
      const w = ctx.measureText(texto).width;
      if (x + w + 12 > this.w) break;
      ctx.fillStyle = tr.color;
      ctx.fillRect(x, 5, 8, 8);
      ctx.fillStyle = css('--suave');
      ctx.fillText(texto, x + 11, 12);
      x += w + 20;
    }
    if (t !== null && t !== undefined && t >= this.v[0] && t <= this.v[1]) {
      ctx.strokeStyle = css('--texto');
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(this.X(t), 18); ctx.lineTo(this.X(t), this.h - 18); ctx.stroke();
    }
  }
}

// La línea de estados de la maniobra, en la misma ventana que los gráficos
class Estados {
  constructor(cv) {
    this.c = cv;
    cv.addEventListener('click', (ev) => {
      if (!actual() || !this.v) return;
      irA(this.v[0] + (ev.offsetX - 44) / (cv.clientWidth - 52) * (this.v[1] - this.v[0]));
    });
  }

  dibujar() {
    const c = actual();
    const [ctx, w] = lienzo(this.c);
    if (!c) return;
    this.v = ventana(c);
    const X = (t) => 44 + (t - this.v[0]) / (this.v[1] - this.v[0]) * (w - 52);
    const D = c.datos;
    let i0 = indice(c, this.v[0]);
    const i1 = indice(c, this.v[1]);
    ctx.font = '11px system-ui, sans-serif';
    for (let i = i0 + 1; i <= i1 + 1; i++) {
      if (i <= i1 && D.estado[i] === D.estado[i0]) continue;
      const a = X(c.tRel[i0]), b = X(c.tRel[Math.min(i, i1)]);
      ctx.fillStyle = COLOR_ESTADO[D.estado[i0]] || '#999';
      ctx.fillRect(a, 3, Math.max(b - a, 1), 20);
      ctx.fillStyle = '#1d2329';
      if (b - a > ctx.measureText(D.estado[i0]).width + 6) ctx.fillText(D.estado[i0], a + 3, 17);
      i0 = i;
    }
    ctx.fillStyle = css('--texto');
    ctx.fillRect(X(E.t) - 1, 0, 2, 26);
  }
}

function redibujarGraficos() {
  const c = actual();
  for (const { g, series } of graficos) {
    const trazos = c ? series.filter(([col]) => c.datos[col]).map(([col, nombre, color, discontinua]) =>
      ({ t: c.tRel, y: c.datos[col], color, nombre, discontinua })) : [];
    g.dibujar(trazos, c ? ventana(c) : null);
    g.cursor(c ? E.t : null);
  }
  estados.dibujar();
}

// ---------------------------------------------------------------- resumen e historial
function dibujarResumen() {
  const c = actual();
  if (!c) return;
  const r = c.resumen, cm = (mm) => mm === null ? '—' : num(-mm / 10, 0) + ' cm';
  const datos = [
    ...(r.escalones > 1 ? [['bajó', `${r.bajados} de ${r.escalones} escalones`]] : []),
    ['pasa el borde a', r.sale === null ? '—' : num(r.sale, 2) + ' m/s'],
    ['toca a', cm(r.toca)], ['termina a', cm(r.fin)], ['lo más lejos', cm(r.min)],
    ['desvío máx', r.desvio === null ? '—' : num(r.desvio, 1) + '°'],
    ['pata mín', r.pata_min === null ? '—' : num(r.pata_min, 1) + '°'],
    ['par de los servos', r.servo === null ? '—' : num(r.servo, 1) + ' N·m'],
    ['fuerza en la rueda', r.rueda === null ? '—' : num(r.rueda, 0) + ' N'],
    ['error del borde visto', r.borde_error === null ? 'no lo vio' : num(r.borde_error, 0) + ' mm'],
    ['cabina a la escalera, lo más cerca', r.holgura == null ? '—'
      : num(r.holgura, 0) + ' mm' + (r.holgura_en ? ` (${r.holgura_en}, ${num(r.holgura_t, 2)} s)` : '')],
  ];
  $('resumen').innerHTML = `<span style="color:${colorDe(c.id)};font-weight:600">${esc(nombreDe(c.id))}</span>` +
    chip(r.clase, r.final + (r.motivo ? ` (${r.motivo})` : '')) +
    datos.map(([n, v]) => `<span class="dato">${n} <b>${v}</b></span>`).join('') +
    `<span class="ayuda">(distancias desde el borde de arriba) · ${esc(descripcion(c))}</span>`;
}

function dibujarHistorial() {
  const h = $('historial');
  h.innerHTML = '';
  for (const id of E.historial) {
    const c = E.corridas.get(id), r = c.resumen;
    const d = document.createElement('div');
    d.className = 'corrida' + (id === E.actual ? ' actual' : '');
    const extra = r.clase === 0 ? `termina a ${num(-r.fin / 10, 0)} cm` : (r.sale !== null ? `sale a ${num(r.sale, 2)}` : '');
    d.innerHTML = `<span class="color" style="background:${colorDe(id)}"></span>
      <div><span class="num">${esc(nombreDe(id))}</span> ${chip(r.clase, r.final)} <span class="num">${extra}</span>
        <div class="desc" title="${esc(descripcion(c, true))}">${esc(descripcion(c))}</div></div>
      <div class="botones">
        ${id === E.actual ? '' : `<label title="Sumarla a la comparación"><input type="checkbox" ${E.comparar.has(id) ? 'checked' : ''}> comparar</label>`}
        <button data-b="usar" title="Poner sus parámetros a la izquierda">↺</button>
        <button data-b="nombre" title="Ponerle nombre">✎</button>
        <button data-b="quitar" title="Sacarla de la lista">×</button>
      </div>`;
    d.addEventListener('click', (ev) => { if (!ev.target.closest('.botones')) ver(id); });
    const caja = d.querySelector('input');
    if (caja) caja.addEventListener('change', () => alternarComparar(id, caja.checked));
    d.querySelector('[data-b="usar"]').addEventListener('click', () => usarParametros(id));
    d.querySelector('[data-b="nombre"]').addEventListener('click', () => {
      const n = prompt(`Nombre para #${id}:`, E.etiquetas.get(id) || '');
      if (n === null) return;
      if (n.trim()) E.etiquetas.set(id, n.trim().slice(0, 40)); else E.etiquetas.delete(id);
      dibujarTodo();
      escena.dibujar();
    });
    d.querySelector('[data-b="quitar"]').addEventListener('click', () => quitarCorrida(id));
    h.appendChild(d);
  }
  const n = conjunto().length;
  $('n-comparar').textContent = n > 1 ? `(${n})` : '';
}

// ---------------------------------------------------------------- robustez, las últimas lado a lado
function dibujarRobustez() {
  const L = E.robusteces;
  if (!L.length) return;
  const cab = L.map((R) => `<th title="${esc(descParams(R.params, R.planta, true))}">R${R.n}<br>${R.bien}/${R.filas.length}</th>`).join('');
  const filas = L[0].filas.map(({ clave, nombre }) => `<tr><td>${esc(nombre)}</td>` + L.map((R) => {
    const f = R.filas.find((x) => x.clave === clave);
    if (!f) return '<td></td>';
    const r = f.resumen;
    const texto = r.clase === 0 ? `${num(-r.fin / 10, 0)} cm` : NOMBRE_CORTO[r.clase];
    const tip = `${nombre}: ${r.final}, sale a ${num(r.sale, 2)} m/s, desvío ${num(r.desvio, 1)}°`;
    return `<td class="celda${f.id === E.actual ? ' actual' : ''}"><span class="chip chico c${r.clase}" data-id="${f.id}" data-origen="${esc('R' + R.n + ': ' + nombre)}" title="${esc(tip)}">${texto}</span></td>`;
  }).join('') + '</tr>').join('');
  $('tabla-robustez').innerHTML =
    `<div class="total">${L.map((R) => `R${R.n}: ${R.bien} de ${R.filas.length}`).join(' · ')}</div>
    <div class="ayuda">${L.map((R) => `<div><b>R${R.n}</b>: ${esc(descParams(R.params, R.planta))}</div>`).join('')}</div>
    <table class="robustez"><tr><th></th>${cab}</tr>${filas}</table>
    <p class="ayuda">Verde: queda parado, a tantos cm del borde. Clic en una celda para ver esa corrida.</p>`;
  $('tabla-robustez').querySelectorAll('[data-id]').forEach((s) => s.addEventListener('click', () =>
    verDeOtroLado(Number(s.dataset.id), s.dataset.origen)));
}

// ---------------------------------------------------------------- comparar
function ventanaComp(cs) {
  let a = Infinity, b = -Infinity;
  for (const c of cs) {
    const t = tiempos(c, E.alinear);
    a = Math.min(a, t[0]);
    b = Math.max(b, t[t.length - 1]);
  }
  return E.compVentana === 'toda' ? [a, b] : [Math.max(a, -1), Math.min(b, 3)];
}

function armarSenales() {
  $('comp-senales').innerHTML = SENALES.map(([col, nombre]) => {
    const si = E.senales.includes(col);
    return `<label class="${si ? 'si' : ''}"><input type="checkbox" value="${col}" ${si ? 'checked' : ''}>${nombre}</label>`;
  }).join('');
  $('comp-senales').querySelectorAll('input').forEach((i) => i.addEventListener('change', () => {
    const elegidas = new Set(E.senales);
    if (i.checked) elegidas.add(i.value); else elegidas.delete(i.value);
    E.senales = SENALES.map((s) => s[0]).filter((s) => elegidas.has(s));
    armarSenales();
    dibujarComparar();
  }));
}

function dibujarComparar() {
  const cs = conjunto();
  $('comp-chips').innerHTML = cs.length
    ? 'Comparando: ' + cs.map((c) => `<span class="chip-corrida" style="border-color:${colorDe(c.id)};color:${colorDe(c.id)}">${esc(nombreDe(c.id))} ${chip(c.resumen.clase, c.resumen.final, true)}</span>`).join(' ')
    : '<span class="ayuda">Todavía no hay corridas: simulá una.</span>';
  // tabla
  if (cs.length) {
    const cab = cs.map((c) => `<th style="color:${colorDe(c.id)}">${esc(nombreDe(c.id))}</th>`).join('');
    let filas = `<tr><td>cómo termina</td>${cs.map((c) => `<td>${chip(c.resumen.clase, c.resumen.final, true)}</td>`).join('')}</tr>`;
    for (const [k, nombre, unidad, dec, f, menor] of METRICAS) {
      const vals = cs.map((c) => (c.resumen[k] === null || c.resumen[k] === undefined) ? null : c.resumen[k] * f);
      // la mejor, entre las que quedan paradas
      const validos = vals.filter((v, j) => v !== null && cs[j].resumen.clase === 0);
      const mejor = menor && validos.length > 1 && Math.max(...validos) > Math.min(...validos) ? Math.min(...validos) : null;
      filas += `<tr><td>${nombre} [${unidad}]</td>${vals.map((v, j) => `<td class="${v !== null && v === mejor && cs[j].resumen.clase === 0 ? 'mejor' : ''}">${num(v, dec)}</td>`).join('')}</tr>`;
    }
    filas += `<tr><td>qué tiene</td>${cs.map((c) => `<td class="cambios" title="${esc(descripcion(c, true))}">${esc(descripcion(c))}</td>`).join('')}</tr>`;
    $('comp-tabla').innerHTML = `<table class="comp"><tr><th></th>${cab}</tr>${filas}</table>`;
  } else {
    $('comp-tabla').innerHTML = '';
  }
  // barras
  const cont = $('comp-barras');
  cont.innerHTML = '';
  for (const k of BARRAS) {
    const [, nombre, unidad, dec, f] = METRICAS.find((m) => m[0] === k);
    const cv = document.createElement('canvas');
    cont.appendChild(cv);
    barras(cv, `${nombre} [${unidad}]`, cs.map((c) => ({
      nombre: nombreDe(c.id), color: colorDe(c.id), clase: c.resumen.clase,
      valor: (c.resumen[k] === null || c.resumen[k] === undefined) ? null : c.resumen[k] * f,
    })), dec);
  }
  trayectorias(cs);
  // señales
  for (const g of graficosComp) g.div.remove();
  graficosComp = [];
  const v = cs.length ? ventanaComp(cs) : null;
  for (const col of E.senales) {
    const [, nombre, unidad] = SENALES.find((s) => s[0] === col);
    const g = new Grafico($('comp-graficos'), nombre, unidad, (t) => { if (E.alinear === 'largada') irA(t); });
    g.dibujar(cs.filter((c) => c.datos[col]).map((c) => ({
      t: tiempos(c, E.alinear), y: c.datos[col], color: colorDe(c.id), nombre: nombreDe(c.id),
      ancho: c.id === E.actual ? 2 : 1.5,
    })), v);
    g.cursor(E.alinear === 'largada' ? E.t : null);
    graficosComp.push(g);
  }
}

function barras(cv, titulo, items, dec) {
  const [ctx, w] = lienzo(cv, 28 + 20 * Math.max(items.length, 1));
  ctx.font = '600 11px system-ui, sans-serif';
  ctx.fillStyle = css('--texto');
  ctx.fillText(titulo, 0, 12);
  const vals = items.map((it) => it.valor).filter((v) => v !== null);
  const vmax = Math.max(0, ...vals), vmin = Math.min(0, ...vals);
  const L = 74, R = 70, ancho = Math.max(w - L - R, 10);
  const X = (v) => L + (v - vmin) / ((vmax - vmin) || 1) * ancho;
  items.forEach((it, k) => {
    const y = 20 + 20 * k;
    ctx.font = '11px system-ui, sans-serif';
    ctx.fillStyle = it.color;
    ctx.fillText(it.nombre.length > 11 ? it.nombre.slice(0, 10) + '…' : it.nombre, 0, y + 12);
    if (it.valor === null) {
      ctx.fillStyle = css('--suave');
      ctx.fillText('— ' + NOMBRE_CORTO[it.clase], L, y + 12);
      return;
    }
    const x0 = X(0), x1 = X(it.valor);
    ctx.globalAlpha = it.clase === 0 ? 0.85 : 0.35;
    ctx.fillRect(Math.min(x0, x1), y + 3, Math.max(Math.abs(x1 - x0), 1.5), 13);
    ctx.globalAlpha = 1;
    ctx.fillStyle = css('--texto');
    ctx.fillText(num(it.valor, dec) + (it.clase === 0 ? '' : ' · ' + NOMBRE_CORTO[it.clase]), Math.max(x0, x1) + 4, y + 13);
  });
}

function trayectorias(cs) {
  const cv = $('comp-tray');
  const [ctx, w, h] = lienzo(cv);
  if (!cs.length) return;
  const tramos = cs.map((c) => ({ c, i0: indiceEn(tiempos(c, 'largada'), -0.3) }));
  let x0 = -0.15, x1 = 0.15, z0 = 0, z1 = 0;
  for (const { c, i0 } of tramos) {
    const D = c.datos;
    for (let i = i0; i < c.n; i++) {
      x0 = Math.min(x0, D.eje_x_m[i], D.cm_x_m[i]);
      x1 = Math.max(x1, D.eje_x_m[i], D.cm_x_m[i]);
      z0 = Math.min(z0, D.eje_z_m[i]);
      z1 = Math.max(z1, D.cm_z_m[i]);
    }
  }
  x0 -= 0.06; x1 += 0.06; z0 -= 0.06; z1 += 0.05;
  const e = Math.min(w / (x1 - x0), h / (z1 - z0));
  const ox = (w - e * (x1 - x0)) / 2 - e * x0, oz = (h - e * (z1 - z0)) / 2 + e * z1;
  const X = (x) => ox + e * x, Z = (z) => oz - e * z;
  dibujarPiso(ctx, cs[0].p, X, Z, -ox / e - 1, (w - ox) / e + 1, (oz - h) / e - 1);
  // escala de 10 cm
  ctx.strokeStyle = css('--piso-linea');
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(10, h - 10); ctx.lineTo(10 + 0.1 * e, h - 10); ctx.stroke();
  ctx.fillStyle = css('--suave');
  ctx.font = '11px system-ui, sans-serif';
  ctx.fillText('10 cm', 10, h - 15);
  for (const { c, i0 } of tramos) {
    const D = c.datos;
    ctx.strokeStyle = colorDe(c.id);
    for (const [cx, cz, raya, ancho] of [['eje_x_m', 'eje_z_m', [], 2], ['cm_x_m', 'cm_z_m', [4, 3], 1.2]]) {
      ctx.setLineDash(raya);
      ctx.lineWidth = ancho;
      ctx.beginPath();
      for (let i = i0; i < c.n; i++) {
        if (i === i0) ctx.moveTo(X(D[cx][i]), Z(D[cz][i])); else ctx.lineTo(X(D[cx][i]), Z(D[cz][i]));
      }
      ctx.stroke();
    }
    ctx.setLineDash([]);
    if (c.eventos.toque !== null) {
      const i = indiceEn(D.t_s, c.eventos.toque);
      ctx.beginPath();
      ctx.arc(X(D.eje_x_m[i]), Z(D.eje_z_m[i]), 5, 0, 2 * Math.PI);
      ctx.stroke();
    }
    const xf = X(D.eje_x_m[c.n - 1]), zf = Z(D.eje_z_m[c.n - 1]);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(xf - 5, zf - 5); ctx.lineTo(xf + 5, zf + 5);
    ctx.moveTo(xf - 5, zf + 5); ctx.lineTo(xf + 5, zf - 5);
    ctx.stroke();
  }
}

// ---------------------------------------------------------------- barrido
function armarBarrido() {
  const sel = $('barrer-param'), antes = sel.value;
  sel.innerHTML = GRUPOS.flatMap(([, ps]) => ps.filter((p) => p[0] in defectos()))
    .map((p) => `<option value="${p[0]}">${p[1]}</option>`).join('');
  sel.value = antes && [...sel.options].some((o) => o.value === antes) ? antes : 'v_salida';
  $('barrer-metrica').innerHTML = METRICAS.map(([k, nombre, unidad]) => `<option value="${k}">${nombre} [${unidad}]</option>`).join('');
  $('barrer-metrica').value = 'desvio';
  rangoBarrido();
}

function rangoBarrido() {
  const k = $('barrer-param').value, d = valorForm(k);
  const [a, b, n] = RANGOS[k] || (d === 0 ? [-1, 1] : [d * 0.7, d * 1.3]);
  $('barrer-desde').value = textoNum(a);
  $('barrer-hasta').value = textoNum(b);
  if (n) $('barrer-pasos').value = n;
}

function dibujarBarrido() {
  const B = E.barrido, cv = $('barrido-graf');
  const [ctx, w, h] = lienzo(cv);
  puntosBarrido = [];
  if (!B) { $('barrido-tabla').innerHTML = ''; return; }
  const m = METRICAS.find((x) => x[0] === $('barrer-metrica').value);
  const pts = B.puntos.map((p) => ({ x: p.valor, y: p.resumen[m[0]] === null ? null : p.resumen[m[0]] * m[4], p }));
  const xs = pts.map((q) => q.x), ys = pts.map((q) => q.y).filter((y) => y !== null);
  let xa = Math.min(...xs), xb = Math.max(...xs), ya = ys.length ? Math.min(...ys) : 0, yb = ys.length ? Math.max(...ys) : 1;
  if (xb - xa < 1e-9) { xa -= 1; xb += 1; }
  if (yb - ya < 1e-9) { ya -= 1; yb += 1; }
  const my = (yb - ya) * 0.1, mx = (xb - xa) * 0.04;
  ya -= my; yb += my; xa -= mx; xb += mx;
  const L = 52, R = 14, T = 24, Bo = 34;
  const X = (x) => L + (x - xa) / (xb - xa) * (w - L - R), Y = (y) => T + (1 - (y - ya) / (yb - ya)) * (h - T - Bo);
  ctx.font = '10px system-ui, sans-serif';
  ctx.strokeStyle = css('--grilla');
  ctx.fillStyle = css('--suave');
  const py = pasoLindo(yb - ya, 5), dy = Math.max(0, -Math.floor(Math.log10(py)));
  for (let y = Math.ceil(ya / py) * py; y <= yb; y += py) {
    ctx.beginPath(); ctx.moveTo(L, Y(y)); ctx.lineTo(w - R, Y(y)); ctx.stroke();
    ctx.fillText(num(y, dy), 4, Y(y) + 3);
  }
  const px = pasoLindo(xb - xa, 8), dx = Math.max(0, -Math.floor(Math.log10(px)));
  for (let x = Math.ceil(xa / px) * px; x <= xb + 1e-9; x += px) {
    ctx.beginPath(); ctx.moveTo(X(x), T); ctx.lineTo(X(x), h - Bo); ctx.stroke();
    ctx.fillText(num(x, dx), X(x) - 10, h - Bo + 14);
  }
  ctx.font = '600 11px system-ui, sans-serif';
  ctx.fillStyle = css('--texto');
  const nombreParam = [...$('barrer-param').options].find((o) => o.value === B.param)?.textContent || B.param;
  ctx.fillText(`${m[1]} [${m[2]}] según ${nombreParam.toLowerCase()} (${B.param})`, L, 14);
  // línea y puntos
  ctx.strokeStyle = css('--suave');
  ctx.lineWidth = 1;
  ctx.beginPath();
  let en = false;
  for (const q of pts) {
    if (q.y === null) { en = false; continue; }
    if (en) ctx.lineTo(X(q.x), Y(q.y)); else ctx.moveTo(X(q.x), Y(q.y));
    en = true;
  }
  ctx.stroke();
  const colores = [css('--bien'), css('--choca'), css('--cae'), css('--aborta')];
  for (const q of pts) {
    const sx = X(q.x), sy = q.y === null ? h - Bo - 6 : Y(q.y);
    ctx.beginPath();
    ctx.arc(sx, sy, 6, 0, 2 * Math.PI);
    ctx.fillStyle = colores[q.p.resumen.clase];
    ctx.fill();
    if (q.p.id === E.actual) {
      ctx.strokeStyle = css('--texto');
      ctx.lineWidth = 2;
      ctx.stroke();
    }
    puntosBarrido.push({ sx, sy, id: q.p.id, origen: `barrido de ${B.param}` });
  }
  // la leyenda de colores
  ctx.font = '11px system-ui, sans-serif';
  let lx = w - R - 290;
  NOMBRE_CORTO.forEach((n, k) => {
    ctx.fillStyle = colores[k];
    ctx.beginPath(); ctx.arc(lx, 10, 5, 0, 2 * Math.PI); ctx.fill();
    ctx.fillStyle = css('--suave');
    ctx.fillText(n, lx + 8, 14);
    lx += 72;
  });
  // tabla
  $('barrido-tabla').innerHTML = `<table class="robustez"><tr><th>${esc(B.param)}</th><th></th><th>sale a</th><th>termina a</th><th>desvío</th></tr>` +
    B.puntos.map((p) => {
      const r = p.resumen;
      return `<tr data-id="${p.id}" data-origen="${esc(`barrido de ${B.param}`)}" class="${p.id === E.actual ? 'actual' : ''}">
        <td class="n">${num(p.valor, 3)}</td><td>${chip(r.clase, r.final, true)}</td>
        <td class="n">${r.sale === null ? '' : num(r.sale, 2) + ' m/s'}</td>
        <td class="n">${r.clase === 0 ? num(-r.fin / 10, 0) + ' cm' : ''}</td>
        <td class="n">${r.desvio === null ? '' : num(r.desvio, 1) + '°'}</td></tr>`;
    }).join('') + '</table>';
  $('barrido-tabla').querySelectorAll('tr[data-id]').forEach((tr) => tr.addEventListener('click', () =>
    verDeOtroLado(Number(tr.dataset.id), tr.dataset.origen)));
}

async function compararBarrido() {
  const B = E.barrido;
  if (!B) return;
  const n = B.puntos.length, k = Math.min(n, 10);
  const elegidos = [...new Set(Array.from({ length: k }, (_, j) => Math.round(j * (n - 1) / Math.max(k - 1, 1))))].map((j) => B.puntos[j]);
  aviso('trayendo las corridas del barrido…');
  try {
    for (const p of elegidos) {
      await traer(p.id);
      agregarAlHistorial(p.id, `barrido de ${B.param}`);
      E.comparar.add(p.id);
    }
    if (E.actual === null) ver(elegidos[0].id);
    E.comparar.delete(E.actual);
    aviso('');
    ponerVista('comparar');
    dibujarTodo();
  } catch (e) {
    aviso(e.message, true);
  }
}

// ---------------------------------------------------------------- inicio
async function cargarPlanta(planta) {
  aviso('cargando la planta (la primera vez compila el banco)…');
  const j = await api('/api/inicio?planta=' + planta);
  E.planta = planta;
  E.plantas = j.plantas;
  E.defectos[planta] = j.parametros;
  E.geoms[planta] = j.geometria;
  try { MEJORES = await api('/api/mejores'); } catch (e) { MEJORES = []; }
  const s = $('planta');
  if (!s.options.length) s.innerHTML = Object.entries(j.plantas).map(([k, n]) => `<option value="${k}">${n}</option>`).join('');
  s.value = planta;
  armarFormulario();
  armarBarrido();
  aviso('');
}

function redimensionar() {
  escena.dimensionar();
  const c = actual();
  if (c) escena.encuadrar(c);
  escena.dibujar();
  redibujarGraficos();
  if (E.vista === 'comparar') dibujarComparar();
  if (E.vista === 'barrido') dibujarBarrido();
}

async function iniciar() {
  escena = new Escena($('escena'));
  graficos = GRAFICOS.map(([titulo, unidad, series]) => ({ g: new Grafico($('graficos'), titulo, unidad, irA), series }));
  estados = new Estados($('estados'));
  armarSenales();
  $('simular').addEventListener('click', simular);
  $('probar-robustez').addEventListener('click', probarRobustez);
  $('por-defecto').addEventListener('click', () => {
    for (const k of numericos()) if ($('p_' + k)) $('p_' + k).value = defectos()[k];
    armarTablaPrograma('patas');
    armarTablaPrograma('vel');
    alCambiar();
  });
  document.querySelectorAll('[data-prog]').forEach((b) => b.addEventListener('click', () => hacerPrograma(b.dataset.prog, b.dataset.hacer)));
  $('copiar').addEventListener('click', () => navigator.clipboard?.writeText($('comando').textContent));
  $('planta').addEventListener('change', async (ev) => {
    try { await cargarPlanta(ev.target.value); } catch (e) { aviso(e.message, true); }
  });
  document.querySelectorAll('.pestanas button').forEach((b) => b.addEventListener('click', () => ponerVista(b.dataset.vista)));
  $('play').addEventListener('click', () => (E.reproduciendo ? pausar() : reproducir_()));
  $('tiempo').addEventListener('input', (ev) => { pausar(); irA(Number(ev.target.value)); });
  $('estela').addEventListener('change', () => escena.dibujar());
  $('ver-haz').addEventListener('change', () => escena.dibujar());
  document.querySelectorAll('input[name="ventana"]').forEach((r) => r.addEventListener('change', () => {
    E.ventana = r.value;
    redibujarGraficos();
  }));
  $('alinear').addEventListener('change', (ev) => { E.alinear = ev.target.value; dibujarComparar(); });
  $('comp-ventana').addEventListener('change', (ev) => { E.compVentana = ev.target.value; dibujarComparar(); });
  $('barrer').addEventListener('click', barrer);
  $('barrer-param').addEventListener('change', rangoBarrido);
  $('barrer-metrica').addEventListener('change', dibujarBarrido);
  $('barrido-comparar').addEventListener('click', compararBarrido);
  $('barrido-graf').addEventListener('click', (ev) => {
    let mejor = null, dmin = 14;
    for (const p of puntosBarrido) {
      const d = Math.hypot(p.sx - ev.offsetX, p.sy - ev.offsetY);
      if (d < dmin) { dmin = d; mejor = p; }
    }
    if (mejor) verDeOtroLado(mejor.id, mejor.origen);
  });
  document.addEventListener('keydown', (ev) => {
    if (ev.target.closest('input, select, textarea') || E.vista !== 'corrida') return;
    if (ev.key === ' ') { ev.preventDefault(); E.reproduciendo ? pausar() : reproducir_(); }
    if (ev.key === 'ArrowRight' || ev.key === 'ArrowLeft') {
      ev.preventDefault();
      pausar();
      irA(E.t + (ev.key === 'ArrowRight' ? 1 : -1) * (ev.shiftKey ? 0.05 : 0.005));
    }
  });
  let espera;
  window.addEventListener('resize', () => { clearTimeout(espera); espera = setTimeout(redimensionar, 100); });
  redimensionar();
  try {
    await cargarPlanta('ajustada');
  } catch (e) {
    aviso(e.message, true);
  }
}

iniciar();
