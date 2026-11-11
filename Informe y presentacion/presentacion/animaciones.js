// Motor de animaciones interactivas para público general (cero ecuaciones en pantalla)
(function () {
  "use strict";

  const Rw = 40; // mm
  const AB = 80, AD = 112, BC = 108, CD = 40.8, DP = 112;
  const ANG_AB = (45 * Math.PI) / 180;
  const DELTA = (164 * Math.PI) / 180;

  function cinematicaPata(thetaDeg) {
    const t = (thetaDeg * Math.PI) / 180;
    const BD = Math.sqrt(AB * AB + AD * AD - 2 * AB * AD * Math.cos(t + ANG_AB));
    const a1 = Math.acos((AD * AD + BD * BD - AB * AB) / (2 * AD * BD));
    const a2 = Math.acos((CD * CD + BD * BD - BC * BC) / (2 * CD * BD));
    const psi = Math.PI - t - a1 - a2;
    const A = { x: 0, y: 0 };
    const B = { x: AB * Math.cos(ANG_AB), y: AB * Math.sin(ANG_AB) };
    const D = { x: AD * Math.cos(t), y: -AD * Math.sin(t) };
    const C = { x: D.x + CD * Math.cos(psi), y: D.y + CD * Math.sin(psi) };
    const P = { x: D.x + DP * Math.cos(psi + DELTA), y: D.y + DP * Math.sin(psi + DELTA) };
    return { A, B, C, D, P, alturaCabinaCm: (-P.y + Rw) / 10 };
  }

  // -------------------- 1. ESCOBA (94 ms) --------------------
  const escoba = {
    phi: (2 * Math.PI) / 180,
    omega: 0,
    t: 0,
    corriendo: false,
    lento: false,
    marcas: []
  };

  function resetEscoba() {
    escoba.phi = (2 * Math.PI) / 180;
    escoba.omega = 0;
    escoba.t = 0;
    escoba.corriendo = false;
    escoba.marcas = [{ t: 0, deg: 2 }];
    actualizarTextoEscoba();
  }

  function actualizarTextoEscoba() {
    const elT = document.getElementById("escoba-tiempo");
    const elA = document.getElementById("escoba-angulo");
    if (elT) elT.textContent = escoba.t.toFixed(2).replace(".", ",") + " s";
    if (elA) {
      const deg = Math.min(90, (escoba.phi * 180) / Math.PI);
      elA.textContent = "inclinación: " + deg.toFixed(1).replace(".", ",") + "°";
    }
  }

  function stepEscoba(dt) {
    const cv = document.getElementById("cv-escoba");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;

    if (escoba.corriendo) {
      const factor = escoba.lento ? 0.22 : 1.0;
      const dts = dt * factor;
      const p = 7.35; // polo inestable real 7,35 1/s (duplica cada ~94 ms)
      escoba.t += dts;
      escoba.phi = ((2 * Math.PI) / 180) * Math.cosh(p * escoba.t);
      const deg = (escoba.phi * 180) / Math.PI;
      const umbrales = [4, 8, 16, 32, 64];
      for (const u of umbrales) {
        if (deg >= u && !escoba.marcas.some((m) => m.deg === u)) {
          escoba.marcas.push({ t: escoba.t, deg: u });
        }
      }
      if (escoba.phi >= Math.PI / 2) {
        escoba.phi = Math.PI / 2;
        escoba.corriendo = false;
      }
      actualizarTextoEscoba();
    }

    ctx.clearRect(0, 0, W, H);
    const cx = W * 0.36, cy = H * 0.82;
    const L = 310;

    // Piso
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(40, cy + 28);
    ctx.lineTo(W - 40, cy + 28);
    ctx.stroke();

    // Fantasmas en cada duplicación (cada ~94 ms)
    for (const m of escoba.marcas) {
      const ang = (m.deg * Math.PI) / 180;
      const tx = cx + L * Math.sin(ang);
      const ty = cy - L * Math.cos(ang);
      ctx.strokeStyle = "rgba(56, 189, 248, 0.22)";
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(tx, ty);
      ctx.stroke();
      ctx.fillStyle = "#94a3b8";
      ctx.font = "600 15px Segoe UI, sans-serif";
      ctx.fillText(m.deg + "° (" + Math.round(m.t * 1000) + " ms)", tx + 10, ty);
    }

    // Vara actual
    const x2 = cx + L * Math.sin(escoba.phi);
    const y2 = cy - L * Math.cos(escoba.phi);
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 10;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(x2, y2);
    ctx.stroke();

    // Masa superior
    ctx.fillStyle = "#38bdf8";
    ctx.beginPath();
    ctx.arc(x2, y2, 24, 0, Math.PI * 2);
    ctx.fill();

    // Rueda/mano en la base
    ctx.fillStyle = "#e2e8f0";
    ctx.beginPath();
    ctx.arc(cx, cy, 26, 0, Math.PI * 2);
    ctx.fill();
  }

  // -------------------- 2. BALANCEO CON EMPUJÓN --------------------
  const bal = { x: 0, v: 0, phi: 0.04, omega: 0, control: true, empujonT: 0 };

  function resetBalanceo() {
    bal.x = 0;
    bal.v = 0;
    bal.phi = 0.04;
    bal.omega = 0;
    bal.empujonT = 0;
  }

  function stepBalanceo(dt) {
    const cv = document.getElementById("cv-balanceo");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;

    const sub = 4;
    const h = Math.min(0.03, dt) / sub;
    for (let i = 0; i < sub; i++) {
      let u = 0;
      if (bal.control && Math.abs(bal.phi) < 1.1) {
        u = 2.2 * bal.x + 2.8 * bal.v + 24.0 * bal.phi + 4.8 * bal.omega;
        u = Math.max(-12, Math.min(12, u));
      }
      const aCarro = u - 0.6 * bal.v;
      const alpha = 54 * Math.sin(bal.phi) - 1.35 * aCarro * Math.cos(bal.phi) - 0.4 * bal.omega;
      bal.v += aCarro * h;
      bal.x += bal.v * h;
      bal.omega += alpha * h;
      bal.phi += bal.omega * h;
      if (Math.abs(bal.phi) > Math.PI / 2) {
        bal.phi = Math.sign(bal.phi) * (Math.PI / 2);
        bal.omega = 0;
        bal.v = 0;
      }
    }
    if (bal.empujonT > 0) bal.empujonT = Math.max(0, bal.empujonT - dt);

    dibujarSegwayLateral(ctx, W, H, bal.x * 260, bal.phi, 0, bal.empujonT > 0);
  }

  // -------------------- 3. AVANCE (FASE NO MÍNIMA) --------------------
  const av = { t: 0, corriendo: false, rastro: [] };

  function resetAvance() {
    av.t = 0;
    av.corriendo = false;
    av.rastro = [];
  }

  function stepAvance(dt) {
    const cv = document.getElementById("cv-avance");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;

    if (av.corriendo) {
      av.t = Math.min(2.4, av.t + dt);
      if (av.t >= 2.4) av.corriendo = false;
    }

    // Curva fiel al cero de fase no mínima: retrocede primero y luego avanza a 30 cm
    const tau = av.t;
    const dip = -0.055 * tau * Math.exp(-tau / 0.16) / 0.058; // pico negativo ~ -0.055 (escala visual para los -14 mm)
    const subida = 1 / (1 + Math.exp(-(tau - 0.95) * 4.2)) - 1 / (1 + Math.exp(0.95 * 4.2));
    const norm = 1 / (1 - 1 / (1 + Math.exp(0.95 * 4.2)));
    const xNorm = dip + Math.max(0, subida * norm);
    const phi = 0.22 * Math.sin((tau / 1.7) * Math.PI) * (tau < 1.7 ? 1 : 0);

    const xPx = -220 + xNorm * 460;
    const origenPx = W / 2 - 220;

    dibujarSegwayLateral(ctx, W, H, xPx, phi, -220, false);

    // Marcador de partida y de retroceso inicial
    ctx.strokeStyle = "rgba(148, 163, 184, 0.5)";
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.moveTo(origenPx, H * 0.25);
    ctx.lineTo(origenPx, H * 0.85);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = "#94a3b8";
    ctx.font = "600 16px Segoe UI, sans-serif";
    ctx.fillText("Salida (0 cm)", origenPx - 45, H * 0.22);
    ctx.fillStyle = "#34d399";
    ctx.fillText("Meta (+30 cm)", origenPx + 460 - 52, H * 0.22);

    if (av.t > 0.08) {
      ctx.fillStyle = "#f87171";
      ctx.font = "700 18px Segoe UI, sans-serif";
      ctx.fillText("1.° Las ruedas patean 14 mm hacia atrás para inclinar el cuerpo", 48, 46);
    }
  }

  function dibujarSegwayLateral(ctx, W, H, offsetPx, phi, refMarkPx, mostrarEmpujon) {
    ctx.clearRect(0, 0, W, H);
    const pisoY = H * 0.82;
    const rRueda = 38;
    const cx = W / 2 + offsetPx;
    const cy = pisoY - rRueda;

    // Piso
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(40, pisoY);
    ctx.lineTo(W - 40, pisoY);
    ctx.stroke();

    // Marca de referencia en el suelo
    const rx = W / 2 + refMarkPx;
    ctx.fillStyle = "#38bdf8";
    ctx.beginPath();
    ctx.arc(rx, pisoY, 6, 0, Math.PI * 2);
    ctx.fill();

    // Cuerpo + pata simplificada
    const L = 190;
    const bx = cx + L * Math.sin(phi);
    const by = cy - L * Math.cos(phi);

    ctx.strokeStyle = "#f87171";
    ctx.lineWidth = 12;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(bx, by);
    ctx.stroke();

    // Cabina
    ctx.save();
    ctx.translate(bx, by);
    ctx.rotate(phi);
    ctx.fillStyle = "#1e293b";
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.roundRect(-52, -36, 104, 72, 14);
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    // Rueda
    ctx.fillStyle = "#0f172a";
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 8;
    ctx.beginPath();
    ctx.arc(cx, cy, rRueda, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    if (mostrarEmpujon) {
      ctx.fillStyle = "#fbbf24";
      ctx.font = "800 22px Segoe UI, sans-serif";
      ctx.fillText("¡EMPUJÓN! →", bx - 190, by);
    }
  }

  // -------------------- 4. PATA DE CUATRO BARRAS --------------------
  const trazaP = [];
  for (let th = 10; th <= 40; th += 1) {
    trazaP.push(cinematicaPata(th).P);
  }

  function stepPata() {
    const cv = document.getElementById("cv-pata");
    const slider = document.getElementById("pata-slider");
    if (!cv || !slider) return;
    const theta = parseFloat(slider.value);
    const g = cinematicaPata(theta);
    const elAlt = document.getElementById("pata-altura");
    if (elAlt) elAlt.textContent = g.alturaCabinaCm.toFixed(1).replace(".", ",") + " cm";

    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;
    ctx.clearRect(0, 0, W, H);

    const s = 2.1; // px por mm
    const pisoY = H - 55;
    // El contacto de la rueda (P.y - Rw) apoya siempre sobre pisoY
    const ox = W * 0.42 - g.P.x * s;
    const oy = pisoY - (-g.P.y + Rw) * s;
    const toCanvas = (pt) => ({ x: ox + pt.x * s, y: oy - pt.y * s });

    // Piso
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(40, pisoY);
    ctx.lineTo(W - 40, pisoY);
    ctx.stroke();

    // Cabina alrededor de A y B
    const pA = toCanvas(g.A);
    const pB = toCanvas(g.B);
    const pC = toCanvas(g.C);
    const pD = toCanvas(g.D);
    const pP = toCanvas(g.P);

    ctx.fillStyle = "rgba(30, 41, 59, 0.9)";
    ctx.strokeStyle = "#64748b";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.roundRect(pA.x - 95, pB.y - 55, 240, 115, 16);
    ctx.fill();
    ctx.stroke();

    // Acoplador CDP
    ctx.fillStyle = "rgba(52, 211, 153, 0.18)";
    ctx.strokeStyle = "#34d399";
    ctx.lineWidth = 8;
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(pD.x, pD.y);
    ctx.lineTo(pC.x, pC.y);
    ctx.lineTo(pP.x, pP.y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Barra AD (manivela del servo)
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 9;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(pA.x, pA.y);
    ctx.lineTo(pD.x, pD.y);
    ctx.stroke();

    // Barra BC (balancín)
    ctx.strokeStyle = "#a78bfa";
    ctx.lineWidth = 9;
    ctx.beginPath();
    ctx.moveTo(pB.x, pB.y);
    ctx.lineTo(pC.x, pC.y);
    ctx.stroke();

    // Rueda en P
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.arc(pP.x, pP.y, Rw * s, 0, Math.PI * 2);
    ctx.stroke();

    // Articulaciones
    for (const [pt, nom] of [[pA, "A (servo)"], [pB, "B"], [pC, "C"], [pD, "D"], [pP, "P (rueda)"]]) {
      ctx.fillStyle = "#f8fafc";
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#cbd5e1";
      ctx.font = "600 14px Segoe UI, sans-serif";
      ctx.fillText(nom, pt.x + 10, pt.y - 8);
    }
  }

  // -------------------- 5. ESCALERA (3 MODOS) --------------------
  const esc = { modo: "corrido", t: 0 };

  function setModoEscalera(m) {
    esc.modo = m;
    esc.t = 0;
    const msg = document.getElementById("esc-mensaje");
    if (!msg) return;
    if (m === "despacio") {
      msg.textContent = "Despacio (< 0,45 m/s): cuando la rueda cae, la esquina de abajo de la cabina todavía está sobre el borde y golpea.";
    } else if (m === "frenando") {
      msg.textContent = "Frenando en cada escalón: aterriza a 14 cm de la pared y en los 15 cm que quedan no llega a frenar.";
    } else {
      msg.textContent = "De corrido (0,77 m/s, hallada por el algoritmo genético): baja los 7 escalones en ciclo estable y frena abajo.";
    }
  }

  function stepEscalera(dt) {
    const cv = document.getElementById("cv-escalera");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;
    esc.t += dt;

    ctx.clearRect(0, 0, W, H);
    const nEsc = 6;
    const dx = 135, dy = 56;
    const x0 = 160, y0 = 90;

    // Dibujar escalera
    ctx.fillStyle = "#1e293b";
    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(40, y0);
    for (let i = 0; i < nEsc; i++) {
      const xi = x0 + i * dx;
      const yi = y0 + i * dy;
      ctx.lineTo(xi, yi);
      ctx.lineTo(xi, yi + dy);
    }
    ctx.lineTo(W - 40, y0 + nEsc * dy);
    ctx.lineTo(W - 40, H - 20);
    ctx.lineTo(40, H - 20);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Posición del robot según modo
    const prog = Math.min(1, esc.t / 3.6);
    let rx = x0 - 40, ry = y0, phi = 0, choca = false;

    if (esc.modo === "despacio") {
      const p = Math.min(1, esc.t / 1.4);
      rx = x0 - 50 + p * 85;
      ry = y0 + (p > 0.55 ? Math.pow((p - 0.55) / 0.45, 2) * dy : 0);
      phi = p > 0.55 ? -0.35 : 0.05;
      if (p >= 0.85) choca = true;
    } else if (esc.modo === "frenando") {
      const p = Math.min(1, esc.t / 2.0);
      rx = x0 - 50 + p * (dx * 1.45);
      const idx = Math.floor(Math.max(0, rx - x0) / dx);
      ry = y0 + Math.min(nEsc, idx + (rx > x0 ? 1 : 0)) * dy;
      phi = p > 0.7 ? 0.55 : -0.1;
      if (p >= 0.92) choca = true;
    } else {
      const totalX = nEsc * dx + 220;
      rx = x0 - 40 + prog * totalX;
      const s = Math.max(0, rx - x0);
      const escIdx = Math.min(nEsc, Math.floor(s / dx) + (s > 0 ? 1 : 0));
      const frac = (s % dx) / dx;
      const yPrev = y0 + Math.max(0, escIdx - 1) * dy;
      const yTarget = y0 + escIdx * dy;
      ry = s <= 0 || escIdx > nEsc ? yTarget : yPrev + Math.min(1, frac * 2.1) * (yTarget - yPrev);
      phi = prog < 0.92 ? -0.12 * Math.sin(s * 0.05) : 0;
    }

    // Rueda y cabina
    const rW = 22;
    const cy = ry - rW;
    const L = 74;
    const bx = rx + L * Math.sin(phi);
    const by = cy - L * Math.cos(phi);

    ctx.strokeStyle = choca ? "#f87171" : "#fbbf24";
    ctx.lineWidth = 7;
    ctx.beginPath();
    ctx.moveTo(rx, cy);
    ctx.lineTo(bx, by);
    ctx.stroke();

    ctx.save();
    ctx.translate(bx, by);
    ctx.rotate(phi);
    ctx.fillStyle = choca ? "#7f1d1d" : "#0f172a";
    ctx.strokeStyle = choca ? "#f87171" : "#38bdf8";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.roundRect(-36, -24, 72, 48, 8);
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    ctx.fillStyle = "#e2e8f0";
    ctx.beginPath();
    ctx.arc(rx, cy, rW, 0, Math.PI * 2);
    ctx.fill();

    if (choca) {
      ctx.fillStyle = "#f87171";
      ctx.font = "800 24px Segoe UI, sans-serif";
      ctx.fillText("✕ ¡CHOCA / NO FRENA A TIEMPO!", rx - 40, cy - 110);
    } else if (esc.modo === "corrido" && prog >= 0.98) {
      ctx.fillStyle = "#34d399";
      ctx.font = "800 24px Segoe UI, sans-serif";
      ctx.fillText("✓ 7 de 7 escalones bajados y detenido", rx - 150, cy - 110);
    }
  }

  // -------------------- 6. EVOLUCIÓN (5.300 CORRIDAS) --------------------
  const evo = { n: 0, puntos: [] };

  function resetEvolucion() {
    evo.n = 0;
    evo.puntos = [];
  }

  function stepEvolucion() {
    const cv = document.getElementById("cv-evolucion");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;

    if (evo.n < 5300) {
      for (let k = 0; k < 45 && evo.n < 5300; k++) {
        evo.n++;
        const p = evo.n / 5300;
        const base = Math.min(0.95, Math.pow(p, 0.65) * 0.85);
        const score = Math.max(0.04, Math.min(1, base + (Math.random() - 0.42) * 0.45));
        evo.puntos.push({ x: p * (W - 70) + 45, y: H - 35 - score * (H - 70), ok: score > 0.84 });
      }
      const el = document.getElementById("evo-contador");
      if (el) el.textContent = evo.n.toLocaleString("es-AR");
    }

    ctx.clearRect(0, 0, W, H);
    // Umbral de éxito
    const yOk = H - 35 - 0.84 * (H - 70);
    ctx.strokeStyle = "rgba(52, 211, 153, 0.4)";
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.moveTo(35, yOk);
    ctx.lineTo(W - 20, yOk);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#34d399";
    ctx.font = "600 14px Segoe UI, sans-serif";
    ctx.fillText("Baja los 7 escalones en las 24 variaciones", 45, yOk - 8);

    for (let i = 0; i < evo.puntos.length; i += 3) {
      const pt = evo.puntos[i];
      ctx.fillStyle = pt.ok ? "#34d399" : "rgba(248, 113, 113, 0.42)";
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, pt.ok ? 3.5 : 2.2, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // -------------------- 7. MEZCLADOR INTERACTIVO LQR (segway_v02) --------------------
  function setLqrSliders(phiDeg, omDeg, xCm, vMs) {
    const sPhi = document.getElementById("lqr-phi");
    const sOm = document.getElementById("lqr-om");
    const sX = document.getElementById("lqr-x");
    const sV = document.getElementById("lqr-v");
    if (sPhi) sPhi.value = String(phiDeg);
    if (sOm) sOm.value = String(omDeg);
    if (sX) sX.value = String(xCm);
    if (sV) sV.value = String(vMs);
  }

  function stepLqr() {
    const cv = document.getElementById("cv-lqr");
    const sPhi = document.getElementById("lqr-phi");
    const sOm = document.getElementById("lqr-om");
    const sX = document.getElementById("lqr-x");
    const sV = document.getElementById("lqr-v");
    if (!cv || !sPhi || !sOm || !sX || !sV) return;

    const phiDeg = parseFloat(sPhi.value);
    const omDeg = parseFloat(sOm.value);
    const xCm = parseFloat(sX.value);
    const vMs = parseFloat(sV.value);

    const elPhi = document.getElementById("lqr-val-phi");
    const elOm = document.getElementById("lqr-val-om");
    const elX = document.getElementById("lqr-val-x");
    const elV = document.getElementById("lqr-val-v");
    if (elPhi) elPhi.textContent = phiDeg.toFixed(1).replace(".", ",") + "°";
    if (elOm) elOm.textContent = Math.round(omDeg) + " °/s";
    if (elX) elX.textContent = Math.round(xCm) + " cm";
    if (elV) elV.textContent = vMs.toFixed(2).replace(".", ",") + " m/s";

    // Ganancias reales en segway_v02 (pata en 15°, con lqrfac=0,87 y lqrfacx=0,86)
    const kx = 1.075;
    const kv = 1.815;
    const kphi = 3.210;
    const kom = 0.378;

    const uPhi = kphi * ((phiDeg * Math.PI) / 180);
    const uOm = kom * ((omDeg * Math.PI) / 180);
    const uX = kx * (xCm / 100);
    const uV = kv * vMs;
    const uTotal = Math.max(-1, Math.min(1, uPhi + uOm + uX + uV));

    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;
    ctx.clearRect(0, 0, W, H);

    const filas = [
      { nom: "Inclinación (kφ·φ)", val: uPhi, col: "#fbbf24" },
      { nom: "Giro (kω·ω)", val: uOm, col: "#f87171" },
      { nom: "Posición (kx·x)", val: uX, col: "#38bdf8" },
      { nom: "Velocidad (kv·v)", val: uV, col: "#34d399" },
      { nom: "TOTAL MOTOR (u)", val: uTotal, col: "#f8fafc", total: true }
    ];

    const cx = W * 0.56;
    const escala = W * 0.36;

    // Línea central (0 % de motor)
    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, 18);
    ctx.lineTo(cx, H - 18);
    ctx.stroke();

    filas.forEach((f, idx) => {
      const y = 34 + idx * 54;
      const alto = f.total ? 28 : 20;
      const w = Math.max(-1, Math.min(1, f.val)) * escala;

      if (f.total) {
        ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
        ctx.beginPath();
        ctx.moveTo(20, y - 14);
        ctx.lineTo(W - 20, y - 14);
        ctx.stroke();
      }

      ctx.fillStyle = f.total ? "#f8fafc" : "#cbd5e1";
      ctx.font = (f.total ? "800 16px " : "600 15px ") + "Segoe UI, sans-serif";
      ctx.fillText(f.nom, 20, y + alto * 0.72);

      // Fondo de barra
      ctx.fillStyle = "rgba(255, 255, 255, 0.06)";
      ctx.beginPath();
      ctx.roundRect(cx - escala, y, escala * 2, alto, 8);
      ctx.fill();

      // Barra activa desde el centro
      ctx.fillStyle = f.col;
      ctx.beginPath();
      if (w >= 0) {
        ctx.roundRect(cx, y, Math.max(3, w), alto, 6);
      } else {
        ctx.roundRect(cx + w, y, Math.max(3, -w), alto, 6);
      }
      ctx.fill();

      // Porcentaje numérico
      const pct = Math.round(f.val * 100);
      const txt = (pct > 0 ? "+" : "") + pct + " %";
      ctx.fillStyle = f.col;
      ctx.font = "700 15px Segoe UI, sans-serif";
      ctx.fillText(txt, W - 66, y + alto * 0.74);
    });
  }

  // -------------------- BUCLE Y EVENTOS --------------------
  let animActiva = null;
  let tPrev = performance.now();

  function loop(now) {
    const dt = Math.min(0.05, (now - tPrev) / 1000);
    tPrev = now;
    if (animActiva === "escoba") stepEscoba(dt);
    else if (animActiva === "lqr") stepLqr();
    else if (animActiva === "balanceo") stepBalanceo(dt);
    else if (animActiva === "avance") stepAvance(dt);
    else if (animActiva === "pata") stepPata();
    else if (animActiva === "escalera") stepEscalera(dt);
    else if (animActiva === "evolucion") stepEvolucion();
    requestAnimationFrame(loop);
  }

  document.addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-accion]");
    if (!btn) return;
    const acc = btn.dataset.accion;
    if (acc === "escoba-soltar") {
      resetEscoba();
      escoba.corriendo = true;
    } else if (acc === "escoba-lento") {
      escoba.lento = !escoba.lento;
      btn.textContent = "Cámara lenta: " + (escoba.lento ? "sí" : "no");
    } else if (acc === "lqr-inclinado") {
      setLqrSliders(5, 15, 0, 0);
    } else if (acc === "lqr-corrido") {
      setLqrSliders(0, 0, 12, 0.15);
    } else if (acc === "lqr-reset") {
      setLqrSliders(0, 0, 0, 0);
    } else if (acc === "bal-empujar") {
      bal.omega += 1.45;
      bal.empujonT = 0.45;
    } else if (acc === "bal-control") {
      bal.control = !bal.control;
      btn.textContent = "Control: " + (bal.control ? "encendido" : "apagado");
    } else if (acc === "bal-reiniciar") {
      resetBalanceo();
    } else if (acc === "av-ir") {
      resetAvance();
      av.corriendo = true;
    } else if (acc === "av-reiniciar") {
      resetAvance();
    } else if (acc === "esc-despacio") {
      setModoEscalera("despacio");
    } else if (acc === "esc-frenando") {
      setModoEscalera("frenando");
    } else if (acc === "esc-corrido") {
      setModoEscalera("corrido");
    }
  });

  window.activarAnimacionSlide = function (nombre) {
    animActiva = nombre || null;
    if (nombre === "escoba") resetEscoba();
    else if (nombre === "lqr") stepLqr();
    else if (nombre === "balanceo") resetBalanceo();
    else if (nombre === "avance") resetAvance();
    else if (nombre === "pata") stepPata();
    else if (nombre === "escalera") setModoEscalera("corrido");
    else if (nombre === "evolucion") resetEvolucion();
  };

  requestAnimationFrame(loop);
})();
