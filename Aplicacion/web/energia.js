// Vista de energía: batería, motores y lógica, de los INA de la placa de potencia. Se apoya en
// app.js (datos, dibujar()) y en banco.js, que llena todo lo que tenga data-col. Va antes que
// banco.js: las potencias que calcula acá tienen que estar en la muestra cuando banco.js la copia.
'use strict';

const TENDENCIA_CADA_S = 5;
const SIN_TENSION_V = 6;        // BAT_V_PRESENTE de board_config.h
const NIVELES = {
  NORMAL: ['bien', 'activo'],
  BAJA: ['baja: cargarla pronto', 'alerta'],
  CRITICA: ['crítica: dejar de usarla', 'alerta'],
  SIN: ['sin batería', ''],
};

const tendencia = { t: [], v: [], grafico: { canvas: $('bat-tendencia'), cursorX: null } };
let energia = {};               // última muestra con datos de energía

alRecibir.push((m, t, textosMuestra) => {
  if (!('v_bat' in m)) return;
  m.p_l_w = (m.v_l * m.i_l_ma) / 1000;
  m.p_r_w = (m.v_r * m.i_r_ma) / 1000;
  m.p_log_w = (m.v_bat * m.i_log_ma) / 1000;
  const medidas = [m.p_l_w, m.p_r_w, m.p_log_w].filter(Number.isFinite);
  m.p_w = medidas.length ? medidas.reduce((a, b) => a + b) : NaN;
  energia = { ...m, ...textosMuestra };

  const ultimoT = tendencia.t[tendencia.t.length - 1];
  if (ultimoT !== undefined && t < ultimoT) { // el ESP32 se reinició
    tendencia.t.length = 0;
    tendencia.v.length = 0;
  }
  if (Number.isFinite(m.v_bat) && m.v_bat >= SIN_TENSION_V
      && (ultimoT === undefined || t < ultimoT || t - ultimoT >= TENDENCIA_CADA_S)) {
    tendencia.t.push(t);
    tendencia.v.push(m.v_bat);
  }
});

function textoAutonomia(e) {
  if (e.bateria === undefined || e.bateria === 'SIN') return '—';
  if (!Number.isFinite(e.autonomia_min)) return 'calculando…';
  const min = Math.round(e.autonomia_min);
  return min >= 60 ? `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')} min` : `${min} min`;
}

// Un motor sin tensión con batería presente es un fusible (F2, F3) o un conector: se dice acá,
// porque armado sin tensión el robot se cae sin aviso.
function avisoMotores(e) {
  if (!(e.v_bat >= SIN_TENSION_V)) return '';
  const sin = [['izq', e.v_l], ['der', e.v_r]].filter(([, v]) => v < SIN_TENSION_V).map(([lado]) => lado);
  return sin.length ? `sin tensión: ${sin.join(' y ')}` : '';
}

function avisoMedidores(e) {
  if (e.v_bat === undefined) return ['', ''];
  const faltan = [['batería', e.v_bat], ['motor izq', e.i_l_ma], ['motor der', e.i_r_ma]]
    .filter(([, v]) => !Number.isFinite(v)).map(([nombre]) => nombre);
  return faltan.length ? [`sin dato: ${faltan.join(', ')}`, 'alerta'] : ['todos leen', 'activo'];
}

setInterval(() => { // 2 veces por segundo: son valores lentos
  if ($('energia').hidden) return;
  const [nivel, claseNivel] = NIVELES[energia.bateria] ?? ['', ''];
  $('bat-nivel').textContent = nivel;
  $('bat-nivel').className = `etiqueta ${claseNivel}`;
  $('bat-autonomia').textContent = textoAutonomia(energia);
  $('mot-aviso').textContent = avisoMotores(energia);
  const [medidores, claseMedidores] = avisoMedidores(energia);
  $('ina-estado').textContent = medidores;
  $('ina-estado').className = `etiqueta ${claseMedidores}`;
  // Toda la sesión, con al menos un minuto a la vista
  const desde = tendencia.t.length ? tendencia.t[0] : tAhora;
  dibujar(tendencia, tAhora, Math.max(60, tAhora - desde));
}, 500);
