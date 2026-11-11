// Pestaña "Mando / Conducción": mapa interactivo en vivo del joystick PS4 (DualShock 4),
// cambio entre Opción 1 (1 stick) y Opción 2 (2 sticks) con los botones de la página, control de
// servos de las patas (R1/L1 apretado en el mando: suben/bajan hasta soltar; acá, de a 2°) con tope
// 0°..30°, y armado (✕) / desarme (◯). 11/11: OPTIONS se alinea con el borde y baja; R3/L3 giran.
'use strict';

(function iniciarVistaMando() {
  const BOTONES_SVG = [
    'x', 'o', 'cuadrado', 'triangulo',
    'l1', 'r1', 'share', 'options',
    'up', 'down', 'left', 'right',
  ];

  const ETIQUETA_BOTON = {
    x: '✕ (Armar)',
    o: '◯ (Desarmar)',
    cuadrado: '□',
    triangulo: '△',
    l1: 'L1 (bajan las patas)',
    r1: 'R1 (suben las patas)',
    l2: 'L2',
    r2: 'R2',
    share: 'SHARE',
    options: 'OPTIONS (alinear y bajar)',
    up: '↑',
    down: '↓',
    left: '←',
    right: '→',
  };

  function acotarServoEstricto(grados) {
    const n = Math.round(Number(grados) || 0);
    return Math.max(0, Math.min(30, n));   // rango de las patas (joystick.py, SERVO_MAX_DEG)
  }

  window.actualizarVistaMando = function actualizarVistaMando(joyData, viva, errorTexto) {
    const chip = $('mando-estado-chip');
    if (!chip) return;

    const j = viva ? joyData?.joystick : null;
    const conectado = Boolean(viva && j?.conectado);
    chip.textContent = !viva
      ? (errorTexto || 'sin puente')
      : conectado
        ? `conectado · ${j.nombre || 'PS4'}`
        : 'mando desconectado';
    chip.className = `etiqueta ${conectado ? 'activo' : 'alerta'}`;

    $('mando-nombre').textContent = !viva
      ? '—'
      : conectado
        ? [j.nombre, Number.isFinite(j.bateria) ? `${j.bateria} %` : null].filter(Boolean).join(' · ')
        : 'sin mando detectado (conectar por Bluetooth o USB)';

    const r = viva ? joyData?.robot : null;
    $('mando-destino').textContent = !viva || !r
      ? '—'
      : r.conectado
        ? `activo (${r.destino || 'UDP :4211'})`
        : 'esperando robot';

    // Modo de conducción (Opción 1 vs Opción 2)
    const modo = joyData?.config?.modo || 'opcion_1';
    const esModo2 = modo === 'opcion_2';
    $('mando-modo-texto').textContent = esModo2
      ? 'Opción 2: 2 Sticks separados (Izq = Avance · Der = Giro) + Flechitas'
      : 'Opción 1: 1 Stick (Izquierdo = Avance + Giro) + Flechitas';
    $('btn-modo-1').classList.toggle('activo', !esModo2);
    $('btn-modo-2').classList.toggle('activo', esModo2);

    // Roles en el diagrama de los sticks
    $('stick-l-rol').textContent = esModo2 ? 'Izq: Avance' : 'Izq: Avance + Giro';
    $('stick-r-rol').textContent = esModo2 ? 'Der: Giro' : 'Der: (solo en Opción 2)';
    $('svg-stick-r').classList.toggle('inactivo', !esModo2);

    // Posición en vivo de los dos sticks en el SVG
    const ejes = (viva && joyData?.ejes) || { lx: 0, ly: 0, rx: 0, ry: 0 };
    const radioMax = 16;
    const lxPx = 155 + Math.max(-1, Math.min(1, Number(ejes.lx) || 0)) * radioMax;
    const lyPx = 136 - Math.max(-1, Math.min(1, Number(ejes.ly) || 0)) * radioMax;
    const rxPx = 265 + Math.max(-1, Math.min(1, Number(ejes.rx) || 0)) * radioMax;
    const ryPx = 136 - Math.max(-1, Math.min(1, Number(ejes.ry) || 0)) * radioMax;
    $('stick-l-dot').setAttribute('cx', lxPx.toFixed(1));
    $('stick-l-dot').setAttribute('cy', lyPx.toFixed(1));
    $('stick-r-dot').setAttribute('cx', rxPx.toFixed(1));
    $('stick-r-dot').setAttribute('cy', ryPx.toFixed(1));

    // Botones presionados en el SVG y en la tabla
    const bot = (viva && joyData?.botones) || {};
    const activos = [];
    for (const k of BOTONES_SVG) {
      const el = $(`svg-btn-${k}`);
      const pres = Boolean(bot[k]);
      if (el) el.classList.toggle('presionado', pres);
      if (pres && ETIQUETA_BOTON[k]) activos.push(ETIQUETA_BOTON[k]);
    }
    if (bot.l2) activos.push('L2');
    if (bot.r2) activos.push('R2');
    if (bot.l3) activos.push('L3 (gira a la izquierda)');
    if (bot.r3) activos.push('R3 (gira a la derecha)');
    $('mando-botones-activos').textContent = activos.length ? activos.join(' · ') : 'ninguno';

    // Estado de los servos (0° a 30° en pasos de 2°)
    const gradosServo = acotarServoEstricto(joyData?.servo?.grados ?? 0);
    $('mando-servo-obj').textContent = `${gradosServo}° (tope 30°)`;
    for (const b of document.querySelectorAll('[data-servo-fijo]')) {
      b.classList.toggle('activo', Number(b.dataset.servoFijo) === gradosServo);
    }

    // Último evento disparado
    if (joyData?.ultimo_evento) {
      $('mando-evento').textContent = joyData.ultimo_evento;
    }
  };

  // Botones de cambio de modo (Opción 1 / Opción 2). OPTIONS ya no lo cambia (11/11: alinear y bajar),
  // y como △ no se dispara con un clic en el dibujo
  $('btn-modo-1')?.addEventListener('click', () => window.enviarAccionJoy?.('opcion_1'));
  $('btn-modo-2')?.addEventListener('click', () => window.enviarAccionJoy?.('opcion_2'));

  // Botones de servos (L1 -2°, R1 +2° y escalones fijos 0°, 10°, 20°, 30°)
  $('btn-servo-l1')?.addEventListener('click', () => window.enviarAccionJoy?.('servo_bajar'));
  $('btn-servo-r1')?.addEventListener('click', () => window.enviarAccionJoy?.('servo_subir'));
  $('svg-btn-l1')?.addEventListener('click', () => window.enviarAccionJoy?.('servo_bajar'));
  $('svg-btn-r1')?.addEventListener('click', () => window.enviarAccionJoy?.('servo_subir'));

  for (const b of document.querySelectorAll('[data-servo-fijo]')) {
    b.addEventListener('click', () => {
      const ang = acotarServoEstricto(b.dataset.servoFijo);
      window.enviarAccionJoy?.('servo_set', ang);
    });
  }

  // Botones de Armar (✕) y Desarmar de emergencia (◯)
  $('btn-mando-armar')?.addEventListener('click', () => window.enviarAccionJoy?.('armar'));
  $('btn-mando-desarmar')?.addEventListener('click', () => window.enviarAccionJoy?.('desarmar'));
  $('svg-btn-x')?.addEventListener('click', () => window.enviarAccionJoy?.('armar'));
  $('svg-btn-o')?.addEventListener('click', () => window.enviarAccionJoy?.('desarmar'));

  // Indicador de estado del supervisor del robot en la tarjeta de conducción
  setInterval(() => {
    const chipRobot = $('mando-estado-robot');
    if (!chipRobot) return;
    const est = ultima?.estado;
    if (!est) {
      chipRobot.textContent = 'sin telemetría';
      chipRobot.className = 'etiqueta';
      return;
    }
    chipRobot.textContent = est;
    chipRobot.className = `etiqueta ${est === 'BALANCING' ? 'activo' : 'alerta'}`;
  }, 100);
})();
