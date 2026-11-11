// Motor de simulaciones interactivas para la presentación de Robótica II (segway_v02)
(function () {
  "use strict";

  const Rw = 40; // mm (radio de rueda)
  const AB = 80, AD = 112, BC = 108, CD = 40.8, DP = 112;
  const ANG_AB = (45 * Math.PI) / 180;
  const DELTA = (164 * Math.PI) / 180;

  function cinematicaPata(thetaDeg) {
    const t = (thetaDeg * Math.PI) / 180;
    const BD = Math.sqrt(AB * AB + AD * AD - 2 * AB * AD * Math.cos(t + ANG_AB));
    const a1 = Math.acos(Math.max(-1, Math.min(1, (AD * AD + BD * BD - AB * AB) / (2 * AD * BD))));
    const a2 = Math.acos(Math.max(-1, Math.min(1, (CD * CD + BD * BD - BC * BC) / (2 * CD * BD))));
    const psi = Math.PI - t - a1 - a2;
    const A = { x: 0, y: 0 };
    const B = { x: AB * Math.cos(ANG_AB), y: AB * Math.sin(ANG_AB) };
    const D = { x: AD * Math.cos(t), y: -AD * Math.sin(t) };
    const C = { x: D.x + CD * Math.cos(psi), y: D.y + CD * Math.sin(psi) };
    const P = { x: D.x + DP * Math.cos(psi + DELTA), y: D.y + DP * Math.sin(psi + DELTA) };
    return { A, B, C, D, P, alturaCabinaCm: (-P.y + Rw) / 10 };
  }

  // -------------------- 1. ESCOBA / PÉNDULO (94 ms) --------------------
  const escoba = {
    phi: (2 * Math.PI) / 180,
    t: 0,
    pausaFin: 0,
    corriendo: true,
    lento: false,
    marcas: [{ t: 0, deg: 2 }]
  };

  function resetEscoba() {
    escoba.phi = (2 * Math.PI) / 180;
    escoba.t = 0;
    escoba.pausaFin = 0;
    escoba.corriendo = true;
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
        escoba.pausaFin = 1.6;
      }
      actualizarTextoEscoba();
    } else if (escoba.pausaFin > 0) {
      escoba.pausaFin -= dt;
      if (escoba.pausaFin <= 0) {
        resetEscoba();
      }
    }

    ctx.clearRect(0, 0, W, H);
    const cx = W * 0.28, cy = H * 0.82;
    const L = 285;

    // Piso
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(30, cy + 26);
    ctx.lineTo(W - 30, cy + 26);
    ctx.stroke();

    // Vertical de referencia
    ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.moveTo(cx, cy - L - 20);
    ctx.lineTo(cx, cy);
    ctx.stroke();
    ctx.setLineDash([]);

    // Fantasmas en cada duplicación (cada ~94 ms)
    for (const m of escoba.marcas) {
      const ang = (m.deg * Math.PI) / 180;
      const tx = cx + L * Math.sin(ang);
      const ty = cy - L * Math.cos(ang);
      ctx.strokeStyle = "rgba(56, 189, 248, 0.25)";
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(tx, ty);
      ctx.stroke();
      ctx.fillStyle = "#94a3b8";
      ctx.font = "600 14px Segoe UI, sans-serif";
      ctx.fillText(m.deg + "° (" + Math.round(m.t * 1000) + " ms)", tx + 8, ty + 4);
    }

    // Vara actual sin control
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
    ctx.fillStyle = "#f87171";
    ctx.beginPath();
    ctx.arc(x2, y2, 22, 0, Math.PI * 2);
    ctx.fill();

    // Rueda en la base
    ctx.fillStyle = "#e2e8f0";
    ctx.beginPath();
    ctx.arc(cx, cy, 24, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#fbbf24";
    ctx.font = "700 16px Segoe UI, sans-serif";
    ctx.fillText("SIN CONTROL: se duplica cada 94 ms", 36, 36);
  }

  // -------------------- 2. MEZCLADOR INTERACTIVO LQR (segway_v02) --------------------
  function setLqrSliders(phiDeg, omDeg, xCm, vMs) {
    const sPhi = document.getElementById("lqr-phi");
    const sOm = document.getElementById("lqr-om");
    const sX = document.getElementById("lqr-x");
    const sV = document.getElementById("lqr-v");
    if (sPhi) sPhi.value = String(phiDeg);
    if (sOm) sOm.value = String(omDeg);
    if (sX) sX.value = String(xCm);
    if (sV) sV.value = String(vMs);
    stepLqr();
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

    // Mini robot a la izquierda mostrando el estado actual y la flecha de motor u
    const rCx = 105 + xCm * 2.2;
    const rCy = H * 0.76;
    const phiRad = (phiDeg * Math.PI) / 180;
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(20, rCy + 24);
    ctx.lineTo(200, rCy + 24);
    ctx.stroke();

    const bx = rCx + 115 * Math.sin(phiRad);
    const by = rCy - 115 * Math.cos(phiRad);
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 8;
    ctx.beginPath();
    ctx.moveTo(rCx, rCy);
    ctx.lineTo(bx, by);
    ctx.stroke();

    ctx.save();
    ctx.translate(bx, by);
    ctx.rotate(phiRad);
    ctx.fillStyle = "#1e293b";
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.roundRect(-30, -20, 60, 40, 8);
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    ctx.fillStyle = "#e2e8f0";
    ctx.beginPath();
    ctx.arc(rCx, rCy, 22, 0, Math.PI * 2);
    ctx.fill();

    // Flecha de par/comando u en la rueda
    if (Math.abs(uTotal) > 0.02) {
      const fl = uTotal * 70;
      ctx.strokeStyle = "#34d399";
      ctx.lineWidth = 5;
      ctx.beginPath();
      ctx.moveTo(rCx, rCy);
      ctx.lineTo(rCx + fl, rCy);
      ctx.stroke();
    }
    ctx.fillStyle = "#94a3b8";
    ctx.font = "600 13px Segoe UI, sans-serif";
    ctx.fillText("Vista del estado", 58, H - 14);

    // Barras de contribución a la derecha
    const filas = [
      { nom: "Inclinación (kφ·φ)", val: uPhi, col: "#fbbf24" },
      { nom: "Giro (kω·ω)", val: uOm, col: "#f87171" },
      { nom: "Posición (kx·x)", val: uX, col: "#38bdf8" },
      { nom: "Velocidad (kv·v)", val: uV, col: "#34d399" },
      { nom: "COMANDO MOTOR u", val: uTotal, col: "#f8fafc", total: true }
    ];

    const cx = W * 0.67;
    const escala = W * 0.22;

    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(cx, 18);
    ctx.lineTo(cx, H - 18);
    ctx.stroke();

    filas.forEach((f, idx) => {
      const y = 28 + idx * 58;
      const alto = f.total ? 28 : 20;
      const w = Math.max(-1, Math.min(1, f.val)) * escala;

      if (f.total) {
        ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
        ctx.beginPath();
        ctx.moveTo(220, y - 12);
        ctx.lineTo(W - 16, y - 12);
        ctx.stroke();
      }

      ctx.fillStyle = f.total ? "#f8fafc" : "#cbd5e1";
      ctx.font = (f.total ? "800 15px " : "600 14px ") + "Segoe UI, sans-serif";
      ctx.fillText(f.nom, 220, y + alto * 0.74);

      ctx.fillStyle = "rgba(255, 255, 255, 0.06)";
      ctx.beginPath();
      ctx.roundRect(cx - escala, y, escala * 2, alto, 8);
      ctx.fill();

      ctx.fillStyle = f.col;
      ctx.beginPath();
      if (w >= 0) {
        ctx.roundRect(cx, y, Math.max(3, w), alto, 6);
      } else {
        ctx.roundRect(cx + w, y, Math.max(3, -w), alto, 6);
      }
      ctx.fill();

      const pct = Math.round(f.val * 100);
      const txt = (pct > 0 ? "+" : "") + pct + " %";
      ctx.fillStyle = f.col;
      ctx.font = "700 14px Segoe UI, sans-serif";
      ctx.fillText(txt, W - 64, y + alto * 0.74);
    });
  }

  // -------------------- 3. BALANCEO CON EMPUJÓN + OSCILOSCOPIO --------------------
  const bal = {
    x: 0,
    v: 0,
    phi: 0.09,
    omega: 0.4,
    control: true,
    empujonDir: 0,
    empujonT: 0,
    hist: []
  };

  function resetBalanceo() {
    bal.x = 0;
    bal.v = 0;
    bal.phi = 0.08;
    bal.omega = 0.65;
    bal.empujonT = 0.35;
    bal.empujonDir = 1;
    bal.hist = [];
  }

  function stepBalanceo(dt) {
    const cv = document.getElementById("cv-balanceo");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;

    const sub = 4;
    const h = Math.min(0.03, dt) / sub;
    let uCmd = 0;
    for (let i = 0; i < sub; i++) {
      let u = 0;
      if (bal.control && Math.abs(bal.phi) < 1.15) {
        u = 1.08 * bal.x + 1.82 * bal.v + 3.21 * bal.phi + 0.38 * bal.omega;
        u = Math.max(-1, Math.min(1, u));
      }
      uCmd = u;
      const aCarro = 11.5 * u - 0.8 * bal.v;
      const alpha = 54.0 * Math.sin(bal.phi) - 1.45 * aCarro * Math.cos(bal.phi) - 0.45 * bal.omega;
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

    bal.hist.push({
      phiDeg: (bal.phi * 180) / Math.PI,
      xCm: bal.x * 100,
      uPct: uCmd * 100
    });
    if (bal.hist.length > 260) bal.hist.shift();

    ctx.clearRect(0, 0, W, H);

    // Mitad superior: Robot equilibrando
    const pisoY = H * 0.56;
    const rRueda = 30;
    const cx = W / 2 + bal.x * 320;
    const cy = pisoY - rRueda;

    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(40, pisoY);
    ctx.lineTo(W - 40, pisoY);
    ctx.stroke();

    // Marca de origen (x = 0)
    ctx.fillStyle = "#38bdf8";
    ctx.beginPath();
    ctx.arc(W / 2, pisoY, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = "600 13px Segoe UI, sans-serif";
    ctx.fillText("x = 0", W / 2 - 16, pisoY + 18);

    const L = 135;
    const bx = cx + L * Math.sin(bal.phi);
    const by = cy - L * Math.cos(bal.phi);

    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 10;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(bx, by);
    ctx.stroke();

    ctx.save();
    ctx.translate(bx, by);
    ctx.rotate(bal.phi);
    ctx.fillStyle = "#1e293b";
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.roundRect(-44, -28, 88, 56, 12);
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    // Rueda con rayos para ver el giro
    const angRueda = (bal.x * 320) / rRueda;
    ctx.fillStyle = "#0f172a";
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.arc(cx, cy, rRueda, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 2.5;
    for (let k = 0; k < 3; k++) {
      const a = angRueda + (k * Math.PI) / 1.5;
      ctx.beginPath();
      ctx.moveTo(cx - rRueda * 0.75 * Math.cos(a), cy - rRueda * 0.75 * Math.sin(a));
      ctx.lineTo(cx + rRueda * 0.75 * Math.cos(a), cy + rRueda * 0.75 * Math.sin(a));
      ctx.stroke();
    }

    if (bal.empujonT > 0) {
      ctx.fillStyle = "#fbbf24";
      ctx.font = "800 20px Segoe UI, sans-serif";
      const txt = bal.empujonDir >= 0 ? "¡EMPUJÓN! →" : "← ¡EMPUJÓN!";
      ctx.fillText(txt, bx + (bal.empujonDir >= 0 ? -165 : 55), by);
    }

    // Mitad inferior: Osciloscopio en tiempo real
    const oscTop = H * 0.63;
    const oscH = H * 0.32;
    const oscCy = oscTop + oscH / 2;
    ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
    ctx.strokeStyle = "rgba(148, 163, 184, 0.22)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.roundRect(40, oscTop, W - 80, oscH, 12);
    ctx.fill();
    ctx.stroke();

    ctx.strokeStyle = "rgba(148, 163, 184, 0.2)";
    ctx.beginPath();
    ctx.moveTo(40, oscCy);
    ctx.lineTo(W - 40, oscCy);
    ctx.stroke();

    const trazarCanal = (prop, esc, col) => {
      if (bal.hist.length < 2) return;
      ctx.strokeStyle = col;
      ctx.lineWidth = 2.6;
      ctx.beginPath();
      for (let i = 0; i < bal.hist.length; i++) {
        const px = 50 + (i / 260) * (W - 100);
        const py = Math.max(oscTop + 6, Math.min(oscTop + oscH - 6, oscCy - bal.hist[i][prop] * esc));
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();
    };

    trazarCanal("phiDeg", 2.8, "#fbbf24");
    trazarCanal("xCm", 1.6, "#38bdf8");
    trazarCanal("uPct", 0.65, "#34d399");

    // Leyenda del osciloscopio
    ctx.font = "700 14px Segoe UI, sans-serif";
    ctx.fillStyle = "#fbbf24";
    ctx.fillText("● Inclinación φ (°)", 58, oscTop + 22);
    ctx.fillStyle = "#38bdf8";
    ctx.fillText("● Posición x (cm)", 230, oscTop + 22);
    ctx.fillStyle = "#34d399";
    ctx.fillText("● Comando motor u (%)", 400, oscTop + 22);
  }

  // -------------------- 4. AVANCE (FASE NO MÍNIMA) --------------------
  const av = { t: 0, corriendo: true };

  function resetAvance() {
    av.t = 0;
    av.corriendo = true;
  }

  function posFaseNoMinima(tau) {
    const dip = (-0.055 * tau * Math.exp(-tau / 0.16)) / 0.058;
    const subida = 1 / (1 + Math.exp(-(tau - 0.95) * 4.2)) - 1 / (1 + Math.exp(0.95 * 4.2));
    const norm = 1 / (1 - 1 / (1 + Math.exp(0.95 * 4.2)));
    return dip + Math.max(0, subida * norm);
  }

  function stepAvance(dt) {
    const cv = document.getElementById("cv-avance");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;

    if (av.corriendo) {
      av.t = Math.min(2.5, av.t + dt);
      if (av.t >= 2.5) av.corriendo = false;
    }

    const tau = av.t;
    const xNorm = posFaseNoMinima(tau);
    const phi = 0.22 * Math.sin((tau / 1.7) * Math.PI) * (tau < 1.7 ? 1 : 0);

    const origenPx = W * 0.28;
    const escalaAv = 480;
    const cx = origenPx + xNorm * escalaAv;
    const pisoY = H * 0.56;
    const rRueda = 30;
    const cy = pisoY - rRueda;

    ctx.clearRect(0, 0, W, H);

    // Piso
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(40, pisoY);
    ctx.lineTo(W - 40, pisoY);
    ctx.stroke();

    // Línea de salida y meta
    ctx.strokeStyle = "rgba(148, 163, 184, 0.45)";
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.moveTo(origenPx, H * 0.12);
    ctx.lineTo(origenPx, pisoY);
    ctx.moveTo(origenPx + escalaAv, H * 0.12);
    ctx.lineTo(origenPx + escalaAv, pisoY);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = "#94a3b8";
    ctx.font = "700 15px Segoe UI, sans-serif";
    ctx.fillText("Salida (0 cm)", origenPx - 45, H * 0.1);
    ctx.fillStyle = "#34d399";
    ctx.fillText("Meta (+30 cm)", origenPx + escalaAv - 50, H * 0.1);

    // Robot
    const L = 135;
    const bx = cx + L * Math.sin(phi);
    const by = cy - L * Math.cos(phi);
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 10;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(bx, by);
    ctx.stroke();

    ctx.save();
    ctx.translate(bx, by);
    ctx.rotate(phi);
    ctx.fillStyle = "#1e293b";
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.roundRect(-44, -28, 88, 56, 12);
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    ctx.fillStyle = "#e2e8f0";
    ctx.beginPath();
    ctx.arc(cx, cy, rRueda, 0, Math.PI * 2);
    ctx.fill();

    // Curva de posición x(t) abajo mostrando el retroceso de -14 mm
    const gTop = H * 0.64, gH = H * 0.30;
    const gZeroY = gTop + gH * 0.72;
    ctx.fillStyle = "rgba(15, 23, 42, 0.85)";
    ctx.strokeStyle = "rgba(148, 163, 184, 0.22)";
    ctx.beginPath();
    ctx.roundRect(40, gTop, W - 80, gH, 12);
    ctx.fill();
    ctx.stroke();

    ctx.strokeStyle = "rgba(148, 163, 184, 0.25)";
    ctx.beginPath();
    ctx.moveTo(50, gZeroY);
    ctx.lineTo(W - 50, gZeroY);
    ctx.stroke();

    const maxK = Math.floor((tau / 2.5) * 200);
    ctx.lineWidth = 3;
    for (let k = 1; k <= maxK; k++) {
      const t0 = ((k - 1) / 200) * 2.5;
      const t1 = (k / 200) * 2.5;
      const v0 = posFaseNoMinima(t0);
      const v1 = posFaseNoMinima(t1);
      ctx.strokeStyle = v1 < 0 ? "#f87171" : "#38bdf8";
      ctx.beginPath();
      ctx.moveTo(60 + (t0 / 2.5) * (W - 120), gZeroY - v0 * (gH * 0.58));
      ctx.lineTo(60 + (t1 / 2.5) * (W - 120), gZeroY - v1 * (gH * 0.58));
      ctx.stroke();
    }

    ctx.fillStyle = "#f87171";
    ctx.font = "700 15px Segoe UI, sans-serif";
    ctx.fillText("1.° Retroceso inicial (−14 mm) para inclinar el cuerpo", 65, gZeroY + 26);
    ctx.fillStyle = "#38bdf8";
    ctx.fillText("2.° Avance hacia la consigna (+30 cm)", 560, gTop + 26);
  }

  // -------------------- 5. PATA DE CUATRO BARRAS --------------------
  const pataState = { auto: true, fase: 0 };
  const trazaP = [];
  for (let th = 10; th <= 40; th += 1) {
    trazaP.push(cinematicaPata(th).P);
  }

  function stepPata(dt) {
    const cv = document.getElementById("cv-pata");
    const slider = document.getElementById("pata-slider");
    if (!cv || !slider) return;

    if (pataState.auto && dt) {
      pataState.fase += dt * 1.35;
      const thAuto = 24 + 13 * Math.sin(pataState.fase);
      slider.value = thAuto.toFixed(1);
    }

    const theta = parseFloat(slider.value);
    const g = cinematicaPata(theta);
    const elAng = document.getElementById("pata-angulo");
    const elAlt = document.getElementById("pata-altura");
    const elKphi = document.getElementById("pata-kphi");
    if (elAng) elAng.textContent = theta.toFixed(1).replace(".", ",") + "°";
    if (elAlt) elAlt.textContent = g.alturaCabinaCm.toFixed(1).replace(".", ",") + " cm";
    if (elKphi) {
      const kphi = 2.85 + ((theta - 10) / 30) * 0.95;
      elKphi.textContent = kphi.toFixed(2).replace(".", ",") + " rad⁻¹";
    }

    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;
    ctx.clearRect(0, 0, W, H);

    const s = 2.05; // px por mm
    const pisoY = H - 48;
    const ox = W * 0.44 - g.P.x * s;
    const oy = pisoY - (-g.P.y + Rw) * s;
    const toCanvas = (pt) => ({ x: ox + pt.x * s, y: oy - pt.y * s });

    // Piso
    ctx.strokeStyle = "#334155";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(30, pisoY);
    ctx.lineTo(W - 30, pisoY);
    ctx.stroke();

    // Vertical de trayectoria cuasi-rectilínea de P
    const pP = toCanvas(g.P);
    ctx.strokeStyle = "rgba(56, 189, 248, 0.35)";
    ctx.setLineDash([5, 5]);
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(pP.x, 40);
    ctx.lineTo(pP.x, pisoY);
    ctx.stroke();
    ctx.setLineDash([]);

    const pA = toCanvas(g.A);
    const pB = toCanvas(g.B);
    const pC = toCanvas(g.C);
    const pD = toCanvas(g.D);

    // Cabina portante alrededor de A y B
    ctx.fillStyle = "rgba(30, 41, 59, 0.92)";
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.roundRect(pA.x - 90, pB.y - 50, 230, 108, 16);
    ctx.fill();
    ctx.stroke();

    // Acoplador CDP (verde)
    ctx.fillStyle = "rgba(52, 211, 153, 0.2)";
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

    // Manivela AD (amarillo)
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 9;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(pA.x, pA.y);
    ctx.lineTo(pD.x, pD.y);
    ctx.stroke();

    // Balancín BC (violeta)
    ctx.strokeStyle = "#a78bfa";
    ctx.lineWidth = 9;
    ctx.beginPath();
    ctx.moveTo(pB.x, pB.y);
    ctx.lineTo(pC.x, pC.y);
    ctx.stroke();

    // Rueda en P
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.arc(pP.x, pP.y, Rw * s, 0, Math.PI * 2);
    ctx.stroke();

    for (const [pt, nom] of [[pA, "A (servo)"], [pB, "B (chasis)"], [pC, "C"], [pD, "D"], [pP, "P (eje rueda)"]]) {
      ctx.fillStyle = "#f8fafc";
      ctx.beginPath();
      ctx.arc(pt.x, pt.y, 6, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#cbd5e1";
      ctx.font = "600 14px Segoe UI, sans-serif";
      ctx.fillText(nom, pt.x + 10, pt.y - 8);
    }
  }

  // -------------------- 6. PREDICCIÓN DE CAÍDA CON SHARP GP2Y0A60SZLF --------------------
  const caida = { conUs: true, t: 0 };

  function setModoCaida(conUs) {
    caida.conUs = conUs;
    caida.t = 0;
    const el = document.getElementById("caida-estado");
    if (!el) return;
    if (conUs) {
      el.innerHTML = "<b>Con Sharp GP2Y0A60SZLF:</b> el haz óptico infrarrojo detecta el salto de distancia antes de que llegue la rueda, extiende las patas para el vuelo y las flexiona al tocar (~190 N).";
    } else {
      el.innerHTML = "<b>Sin sensor GP2Y0A60SZLF:</b> el robot llega al borde a ciegas con las patas rígidas; recién se entera cuando ya está cayendo, golpea fuerte (421 N) y pierde el equilibrio.";
    }
  }

  function stepCaida(dt) {
    const cv = document.getElementById("cv-caida");
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const W = cv.width, H = cv.height;

    caida.t += dt;
    if (caida.t > 4.2) caida.t = 0;

    ctx.clearRect(0, 0, W, H);

    const xBorde = W * 0.48;
    const yAlto = H * 0.56;
    const yBajo = H * 0.82;
    const rW = 28;

    // Dibujar escalón
    ctx.fillStyle = "#1e293b";
    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(30, yAlto);
    ctx.lineTo(xBorde, yAlto);
    ctx.lineTo(xBorde, yBajo);
    ctx.lineTo(W - 30, yBajo);
    ctx.lineTo(W - 30, H - 15);
    ctx.lineTo(30, H - 15);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Cinemática de avance hacia el escalón
    const p = Math.min(1, caida.t / 3.4);
    const rx = 110 + p * (W - 240);

    // ¿Dónde cae la rueda?
    let ry = yAlto;
    let enVuelo = false;
    let impacto = false;
    if (rx > xBorde) {
      const s = Math.min(1, (rx - xBorde) / 115);
      ry = yAlto + s * s * (yBajo - yAlto);
      enVuelo = s < 1;
      impacto = s >= 1 && rx < xBorde + 185;
    }

    // El haz óptico del Sharp GP2Y0A60SZLF apunta ~78 px delante del eje de rueda
    const xHaz = rx + 78;
    const yPisoHaz = xHaz > xBorde ? yBajo : yAlto;
    const bichoDetectaBorde = caida.conUs && xHaz > xBorde && rx < xBorde + 40;

    // Altura de las patas (amortiguación activa si hay sensor Sharp)
    let L = 98;
    let phi = 0.04;
    let caido = false;
    if (caida.conUs) {
      if (xHaz > xBorde && rx <= xBorde + 40) {
        // Estira las patas preparándose para el escalón
        L = 122;
        phi = -0.06;
      } else if (enVuelo) {
        L = 126;
        phi = -0.04;
      } else if (rx > xBorde) {
        // Flexiona las rodillas absorbiendo el impacto y recupera
        const post = Math.min(1, (rx - (xBorde + 115)) / 180);
        L = 82 + post * 18;
        phi = 0.08 * Math.exp(-post * 3) * Math.cos(post * 8);
      }
    } else {
      // Sin sensor: patas rígidas y vuelco al caer
      L = 100;
      if (rx > xBorde) {
        const post = Math.min(1, (rx - xBorde) / 200);
        phi = 0.15 + post * 0.95;
        if (post > 0.65) caido = true;
      }
    }

    const cy = ry - rW;
    const bx = rx + L * Math.sin(phi);
    const by = cy - L * Math.cos(phi);

    // Dibujar haz óptico infrarrojo Sharp GP2Y0A60SZLF si está activo
    if (caida.conUs) {
      const sx = bx + 32;
      const sy = by + 10;
      ctx.fillStyle = bichoDetectaBorde ? "rgba(251, 191, 36, 0.22)" : "rgba(244, 63, 94, 0.16)";
      ctx.strokeStyle = bichoDetectaBorde ? "#fbbf24" : "#f43f5e";
      ctx.lineWidth = 2.4;
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(xHaz - 9, yPisoHaz);
      ctx.lineTo(xHaz + 9, yPisoHaz);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();

      // Punto focal IR sobre el piso
      ctx.fillStyle = bichoDetectaBorde ? "#fbbf24" : "#f43f5e";
      ctx.beginPath();
      ctx.arc(xHaz, yPisoHaz, 5.5, 0, Math.PI * 2);
      ctx.fill();
    }

    // Pata con rodilla articulada
    const rodX = (rx + bx) / 2 - 18 * Math.cos(phi);
    const rodY = (cy + by) / 2 - 18 * Math.sin(phi);
    ctx.strokeStyle = caido ? "#f87171" : "#34d399";
    ctx.lineWidth = 8;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(rx, cy);
    ctx.lineTo(rodX, rodY);
    ctx.lineTo(bx, by);
    ctx.stroke();

    // Cabina
    ctx.save();
    ctx.translate(bx, by);
    ctx.rotate(phi);
    ctx.fillStyle = caido ? "#7f1d1d" : "#0f172a";
    ctx.strokeStyle = caido ? "#f87171" : "#38bdf8";
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.roundRect(-40, -26, 80, 52, 10);
    ctx.fill();
    ctx.stroke();
    ctx.restore();

    // Rueda
    ctx.fillStyle = "#e2e8f0";
    ctx.beginPath();
    ctx.arc(rx, cy, rW, 0, Math.PI * 2);
    ctx.fill();

    // Indicador de distancia medida por el Sharp GP2Y0A60SZLF arriba a la derecha
    const distCm = xHaz > xBorde && rx < xBorde + 95 ? 36.0 : 18.0;
    const vAdc = xHaz > xBorde && rx < xBorde + 95 ? 0.73 : 1.20;
    ctx.fillStyle = "rgba(15, 23, 42, 0.9)";
    ctx.strokeStyle = bichoDetectaBorde ? "#fbbf24" : "rgba(148, 163, 184, 0.3)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.roundRect(W - 335, 22, 310, 86, 12);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#94a3b8";
    ctx.font = "600 13px Segoe UI, sans-serif";
    ctx.fillText("SHARP GP2Y0A60SZLF (GPIO3 ADC1):", W - 319, 46);
    ctx.fillStyle = caida.conUs ? (bichoDetectaBorde ? "#fbbf24" : "#38bdf8") : "#64748b";
    ctx.font = "800 20px Segoe UI, sans-serif";
    ctx.fillText(
      caida.conUs ? "d = " + distCm.toFixed(1).replace(".", ",") + " cm  (" + vAdc.toFixed(2).replace(".", ",") + " V)" : "APAGADO",
      W - 319,
      74
    );
    ctx.font = "700 13px Segoe UI, sans-serif";
    ctx.fillStyle = bichoDetectaBorde ? "#fbbf24" : "#34d399";
    if (caida.conUs) {
      ctx.fillText(
        bichoDetectaBorde ? "⚠ ¡escalón detectado! Extendiendo patas" : "✓ piso continuo (sensor_piso.c)",
        W - 319,
        96
      );
    }

    if (caido) {
      ctx.fillStyle = "#f87171";
      ctx.font = "800 21px Segoe UI, sans-serif";
      ctx.fillText("✕ Caída sin anticipación: golpe rígido (421 N) y vuelco", 42, 46);
    } else if (caida.conUs && impacto) {
      ctx.fillStyle = "#34d399";
      ctx.font = "800 21px Segoe UI, sans-serif";
      ctx.fillText("✓ Rodillas flexionadas: impacto amortiguado (~190 N)", 42, 46);
    }
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
    else if (animActiva === "pata") stepPata(dt);
    else if (animActiva === "caida") stepCaida(dt);
    requestAnimationFrame(loop);
  }

  // Respuesta inmediata al mover cualquier deslizador (input)
  document.addEventListener("input", (ev) => {
    if (ev.target.id === "pata-slider") {
      pataState.auto = false;
      const btn = document.getElementById("btn-pata-auto");
      if (btn) btn.textContent = "▶ Mover pata sola";
      stepPata(0);
    } else if (ev.target.id && ev.target.id.startsWith("lqr-")) {
      stepLqr();
    }
  });

  document.addEventListener("click", (ev) => {
    const btn = ev.target.closest("button[data-accion]");
    if (!btn) return;
    const acc = btn.dataset.accion;
    if (acc === "escoba-soltar") {
      resetEscoba();
    } else if (acc === "escoba-lento") {
      escoba.lento = !escoba.lento;
      btn.textContent = "Cámara lenta: " + (escoba.lento ? "sí" : "no");
    } else if (acc === "lqr-inclinado") {
      setLqrSliders(5, 15, 0, 0);
    } else if (acc === "lqr-corrido") {
      setLqrSliders(0, 0, 12, 0.15);
    } else if (acc === "lqr-frenando") {
      setLqrSliders(5, -45, 0, 0);
    } else if (acc === "lqr-reset") {
      setLqrSliders(0, 0, 0, 0);
    } else if (acc === "bal-empujar-der") {
      bal.omega += 1.45;
      bal.empujonDir = 1;
      bal.empujonT = 0.45;
    } else if (acc === "bal-empujar-izq") {
      bal.omega -= 1.45;
      bal.empujonDir = -1;
      bal.empujonT = 0.45;
    } else if (acc === "bal-control") {
      bal.control = !bal.control;
      btn.textContent = "Control LQR: " + (bal.control ? "ENCENDIDO" : "APAGADO");
    } else if (acc === "bal-reiniciar") {
      resetBalanceo();
    } else if (acc === "av-ir") {
      resetAvance();
    } else if (acc === "av-reiniciar") {
      resetAvance();
    } else if (acc === "pata-auto") {
      pataState.auto = !pataState.auto;
      btn.textContent = pataState.auto ? "⏸ Pausar movimiento" : "▶ Mover pata sola";
    } else if (acc === "caida-con") {
      setModoCaida(true);
    } else if (acc === "caida-sin") {
      setModoCaida(false);
    }
  });

  window.activarAnimacionSlide = function (nombre) {
    animActiva = nombre || null;
    if (nombre === "escoba") resetEscoba();
    else if (nombre === "lqr") stepLqr();
    else if (nombre === "balanceo") resetBalanceo();
    else if (nombre === "avance") resetAvance();
    else if (nombre === "pata") {
      pataState.auto = true;
      const btn = document.getElementById("btn-pata-auto");
      if (btn) btn.textContent = "⏸ Pausar movimiento";
      stepPata(0);
    } else if (nombre === "caida") setModoCaida(true);
  };

  requestAnimationFrame(loop);
})();
