// Lo común de las cinco pantallas: el menú, pasar de una a otra con las flechas y dibujar los gráficos.
const PANTALLAS = [
  ["1_mando.html", "Mando / Conducción"],
  ["2_banco_de_pruebas.html", "Banco de pruebas"],
  ["3_energia.html", "Energía"],
  ["4_graficos.html", "Gráficos"],
  ["5_configuracion.html", "Configuración"],
];

(function armarMarco() {
  const aca = location.pathname.split("/").pop() || PANTALLAS[0][0];
  const i = Math.max(0, PANTALLAS.findIndex((p) => p[0] === aca));
  document.querySelector(".lateral").innerHTML =
    "<h1>Segway</h1><p>control y telemetría</p>" +
    PANTALLAS.map((p, k) => `<a href="${p[0]}"${k === i ? ' class="activa"' : ""}>${p[1]}</a>`).join("");
  document.querySelector(".barra").innerHTML =
    '<span class="boton">Robot por WiFi</span><span class="conexion">conectado · 50 datos por segundo</span>' +
    '<span class="hueco"></span><span class="estado">EQUILIBRANDO</span>' +
    '<span class="boton">Armar</span><span class="boton peligro">Desarmar</span>';
  // flechas del teclado: pantalla anterior / siguiente
  document.addEventListener("keydown", (e) => {
    const paso = { ArrowRight: 1, PageDown: 1, " ": 1, ArrowLeft: -1, PageUp: -1 }[e.key];
    if (paso && PANTALLAS[i + paso]) location.href = PANTALLAS[i + paso][0];
  });
})();

// Gráfico de líneas contra el tiempo del registro. series = [[datos, color], ...]
function grafico(id, series, o = {}) {
  const W = 1000, H = o.alto || 150, L = o.letra || 13, mi = 50, md = 10, ms = 8, mb = o.ejeT ? L + 11 : 8;
  const t = REGISTRO.t, t0 = t[0], t1 = t[t.length - 1];
  let lo = o.min, hi = o.max;
  if (lo === undefined) {
    const todos = series.flatMap((s) => s[0]);
    lo = Math.min(...todos); hi = Math.max(...todos);
    const m = (hi - lo) * 0.1 || 1; lo -= m; hi += m;
  }
  const X = (v) => mi + ((v - t0) / (t1 - t0)) * (W - mi - md);
  const Y = (v) => ms + ((hi - v) / (hi - lo)) * (H - ms - mb);
  let s = "";
  // la franja del vuelo (entre que pasa el borde y que toca)
  const f = Object.fromEntries(REGISTRO.fases);
  if (f.vuelo !== undefined && f.aterrizar !== undefined)
    s += `<rect x="${X(f.vuelo)}" y="${ms}" width="${X(f.aterrizar) - X(f.vuelo)}" height="${H - ms - mb}" fill="#e0a437" opacity="0.28"/>`;
  const paso = o.paso || (hi - lo) / 3;
  for (let v = Math.ceil(lo / paso) * paso; v <= hi + 1e-9; v += paso) {
    s += `<line x1="${mi}" x2="${W - md}" y1="${Y(v)}" y2="${Y(v)}" stroke="#2a2a28"/>`;
    s += `<text x="${mi - 8}" y="${Y(v) + L / 3}" text-anchor="end" style="font-size:${L}px">${(+v.toFixed(2)).toString().replace(".", ",")}</text>`;
  }
  if (o.ejeT)
    for (let v = Math.ceil(t0); v <= t1; v += 1)
      s += `<text x="${X(v)}" y="${H - 5}" text-anchor="middle" style="font-size:${L}px">${v === 0 ? "pasa el borde" : v + " s"}</text>`;
  for (const [datos, color, ancho] of series) {
    const p = datos.map((v, k) => `${X(t[k]).toFixed(1)},${Y(Math.max(lo, Math.min(hi, v))).toFixed(1)}`).join(" ");
    s += `<polyline points="${p}" fill="none" stroke="${color}" stroke-width="${ancho || 2}" stroke-linejoin="round"/>`;
  }
  const svg = document.getElementById(id);
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.innerHTML = s;
}
