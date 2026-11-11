// Navegación del mazo de diapositivas, notas de orador (N), reloj de exposición (T) y pantalla completa (F)
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

  // Reloj de 25-30 min (se activa/oculta con la tecla T)
  setInterval(() => {
    if (!inicioCharla || !elReloj || elReloj.classList.contains("oculto")) return;
    const seg = Math.floor((Date.now() - inicioCharla) / 1000);
    const mm = String(Math.floor(seg / 60)).padStart(2, "0");
    const ss = String(seg % 60).padStart(2, "0");
    elReloj.textContent = "⏱ " + mm + ":" + ss + " / 25:00";
  }, 500);

  document.addEventListener("keydown", (ev) => {
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
