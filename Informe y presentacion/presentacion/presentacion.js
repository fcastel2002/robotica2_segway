// Navegación del mazo de diapositivas, notas de orador (N), reloj de exposición (T),
// pantalla completa (F), selector interactivo de las 5 pantallas de Aplicacion/ y zoom Lightbox.
(function () {
  "use strict";

  const slides = Array.from(document.querySelectorAll(".slide"));
  const elProgreso = document.getElementById("progreso");
  const elActo = document.getElementById("acto-actual");
  const elContador = document.getElementById("contador");
  const elNotas = document.getElementById("panel-notas");
  const elReloj = document.getElementById("reloj");

  let idx = 0;
  let inicioCharla = null;

  function irA(nuevoIdx) {
    idx = Math.max(0, Math.min(slides.length - 1, nuevoIdx));
    slides.forEach((s, i) => s.classList.toggle("activa", i === idx));

    const actual = slides[idx];
    const pct = ((idx + 1) / slides.length) * 100;
    if (elProgreso) elProgreso.style.width = pct.toFixed(1) + "%";
    if (elActo) elActo.textContent = actual.dataset.acto || "";
    if (elContador) elContador.textContent = (idx + 1) + " / " + slides.length;

    const nota = actual.querySelector("aside.notas");
    if (elNotas) {
      elNotas.innerHTML = nota ? nota.innerHTML : "<i>Sin notas en esta diapositiva.</i>";
    }

    if (typeof window.activarAnimacionSlide === "function") {
      window.activarAnimacionSlide(actual.dataset.anim || null);
    }

    history.replaceState(null, "", "#" + (idx + 1));
  }

  // Selector interactivo de las 5 pantallas de Aplicacion/
  const INFO_PANTALLAS = {
    mando: {
      img: "assets/app_mando.png",
      titulo: "1. Mando / Conducción (DualShock 4 por HID nativo)",
      p1: "<b>Mapa interactivo en vivo del mando PS4:</b> leído por <code>joystick.py</code> directo sobre <code>hid.dll</code> a <b>25&nbsp;Hz por UDP</b> (funciona incluso con la pestaña en segundo plano). Con <b>OPTIONS</b> alterna entre <i>Opción 1</i> (1 stick + cruceta) y <i>Opción 2</i> (2 sticks separados).",
      p2: "<b>Control de patas y seguridad:</b> <b>R1/L1</b> suben y bajan las patas de a <b>±2°</b> (acotadas estrictamente entre <b>0° y 30°</b>), <b>✕</b> arma el LQR, <b>◯</b> ejecuta corte de emergencia, <b>△</b> lanza la bajada de escalón, <b>□</b> la parada controlada y <b>SHARE</b> graba 8&nbsp;s a 200&nbsp;Hz.",
      badge: "HUD en tiempo real: inclinación θ vs. θ<sub>ref</sub>, velocidad real vs. consigna flotante (<code>xlibre=1</code>) y esfuerzo de cada puente H."
    },
    banco: {
      img: "assets/app_banco.png",
      titulo: "2. Banco de Pruebas (Sensores, Actuadores y 21 Parámetros LQR)",
      p1: "<b>Tres columnas fijas (Sensores · Actuadores · Control):</b> muestra la IMU cruda y relativa (θ − θ<sub>ref</sub> con indicador de ventana de armado ±5°), cuentas/vueltas/RPM de encoders (<b>899 cuentas/vuelta</b>) y deslizador de motores con ensayo automático de escalón.",
      p2: "<b>Sintonía en caliente del firmware:</b> permite leer (<code>get</code>) y cargar (<code>set</code>) las ganancias <code>kx, kv, kphi, kw</code>, tabla por altura (<code>lqrpata 2</code>), doble Notch (<code>11,6</code> y <code>7,7 Hz</code>), zonas muertas (<code>deadband</code> / <code>dbmov</code>) y rampas de manejo.",
      badge: "Seguridad de servos: casilla «juntos» sincronizada y regla del firmware que exige ambas patas fijas e iguales para permitir el primer armado."
    },
    energia: {
      img: "assets/app_energia.png",
      titulo: "3. Energía (Monitoreo I²C con 2× INA219 + 1× INA226)",
      p1: "<b>Batería LiPo 3S y autonomía en vivo:</b> tensión calibrada (<code>INA226_V_GANANCIA = 0,951</code>), estado de carga (SoC&nbsp;%), curva de descarga de toda la sesión y estimación de minutos restantes según el ritmo de los últimos 5&nbsp;min.",
      p2: "<b>Corriente y potencia por rueda:</b> los dos <b>INA219</b> (<code>0x40</code> y <code>0x41</code>) miden tensión y corriente de entrada a cada driver MOSFET DRV8871 (con signo negativo en frenado regenerativo), más el consumo de la lógica (<b>49&nbsp;mA · 0,6&nbsp;W</b>).",
      badge: "Diagnóstico en vivo: detecta fusibles abiertos (F2/F3) si cae la tensión de un driver y monitorea el tiempo de ciclo (< 2,4 ms de 5.000 µs)."
    },
    graficos: {
      img: "assets/app_graficos.png",
      titulo: "4. Gráficos (Osciloscopio Multicanal a 50 Hz y Ráfagas a 200 Hz)",
      p1: "<b>39 variables disponibles en tiempo real:</b> renderizado fluido a 60&nbsp;fps en <code>&lt;canvas&gt;</code> con retención de 60&nbsp;s en memoria, selector de ventana temporal (5, 10, 30 y 60&nbsp;s) y botón de pausa sin perder muestras entrantes.",
      p2: "<b>Inspección muestra a muestra y exportación CSV:</b> cursor interactivo que informa el valor exacto y su instante relativo, y grabación con un clic a archivos <code>segway_YYYY-MM-DD.csv</code> compatibles con MATLAB y Python.",
      badge: "Sincronizado con el reloj interno del ESP32 (<code>t_ms</code>) para que el jitter de WiFi UDP no deforme las derivadas ni la fase."
    },
    config: {
      img: "assets/app_configuracion.png",
      titulo: "5. Configuración (Puente HID y Calibración Guiada de IMU)",
      p1: "<b>Diagnóstico del puente del mando PS4 (<code>:8001/estado</code>):</b> verifica en tiempo real la conexión Bluetooth/USB del DualShock 4, su nivel de batería, el modo activo de sticks y el enlace UDP hacia el robot (<code>:4211</code>).",
      p2: "<b>Asistente de calibración de IMU en 3 pasos:</b> 1) sesgo y ruido del giróscopo en reposo (3&nbsp;s), 2) offset y factor de escala del acelerómetro en las <b>6 caras ortogonales</b> (±x, ±y, ±z), y 3) cero de inclinación θ<sub>0</sub> con envío directo a <code>set ref</code>.",
      badge: "Rechazo automático de vibraciones: descarta la toma si detecta movimiento (> 1 °/s o > 0,15 m/s²) durante la captura."
    }
  };

  const tabBtns = document.querySelectorAll("#app-tabs .app-tab");
  const imgApp = document.getElementById("app-screen-img");
  const tTitulo = document.getElementById("app-info-titulo");
  const tP1 = document.getElementById("app-info-p1");
  const tP2 = document.getElementById("app-info-p2");
  const tBadge = document.getElementById("app-info-badge");

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.dataset.tab;
      const d = INFO_PANTALLAS[key];
      if (!d) return;
      tabBtns.forEach((b) => b.classList.toggle("activo", b === btn));
      if (imgApp) imgApp.src = d.img;
      if (tTitulo) tTitulo.innerHTML = d.titulo;
      if (tP1) tP1.innerHTML = d.p1;
      if (tP2) tP2.innerHTML = d.p2;
      if (tBadge) tBadge.innerHTML = d.badge;
    });
  });

  // Visor Lightbox al hacer clic sobre cualquier imagen CAD, PCB o captura
  const modal = document.createElement("div");
  modal.id = "lightbox-modal";
  modal.className = "oculto";
  modal.innerHTML = '<img id="lightbox-img" src="" alt="Vista ampliada"><span>Clic en cualquier lugar o Esc para cerrar</span>';
  document.body.appendChild(modal);
  const modalImg = document.getElementById("lightbox-img");

  modal.addEventListener("click", () => modal.classList.add("oculto"));
  document.querySelectorAll(".tarjeta-cad img, .captura, .mini-cad-us img").forEach((img) => {
    img.style.cursor = "zoom-in";
    img.addEventListener("click", (e) => {
      e.stopPropagation();
      modalImg.src = img.src;
      modal.classList.remove("oculto");
    });
  });

  // Reloj de 25-30 min (se activa/oculta con la tecla T)
  setInterval(() => {
    if (!inicioCharla || !elReloj || elReloj.classList.contains("oculto")) return;
    const seg = Math.floor((Date.now() - inicioCharla) / 1000);
    const mm = String(Math.floor(seg / 60)).padStart(2, "0");
    const ss = String(seg % 60).padStart(2, "0");
    elReloj.textContent = "⏱ " + mm + ":" + ss + " / 25:00";
  }, 500);

  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !modal.classList.contains("oculto")) {
      modal.classList.add("oculto");
      return;
    }
    if (ev.target.tagName === "INPUT") return;
    if (ev.key === "ArrowRight" || ev.key === "PageDown" || ev.key === " ") {
      ev.preventDefault();
      irA(idx + 1);
    } else if (ev.key === "ArrowLeft" || ev.key === "PageUp") {
      ev.preventDefault();
      irA(idx - 1);
    } else if (ev.key === "Home") {
      irA(0);
    } else if (ev.key === "End") {
      irA(slides.length - 1);
    } else if (ev.key === "n" || ev.key === "N") {
      if (elNotas) elNotas.classList.toggle("oculto");
    } else if (ev.key === "t" || ev.key === "T") {
      if (!inicioCharla) inicioCharla = Date.now();
      if (elReloj) elReloj.classList.toggle("oculto");
    } else if (ev.key === "f" || ev.key === "F") {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen().catch(() => {});
      }
    }
  });

  const hashNum = parseInt(location.hash.replace("#", ""), 10);
  irA(Number.isFinite(hashNum) && hashNum >= 1 ? hashNum - 1 : 0);
})();
