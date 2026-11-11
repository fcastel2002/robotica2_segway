# Informe y presentación — Segway con patas extensibles

Carpeta central con los dos entregables finales del proyecto (**Robótica II, UNCUYO — Grupo 4**: Joaquín Calderón, Francisco Castel, Matías Armani):
1. **El Informe Técnico Final** (riguroso, matemático y experimental, dirigido al profesor/cátedra).
2. **La Presentación Web Interactiva** (atractiva, visual y sin fórmulas, pensada para 25–30 minutos ante público general).

---

## 1. Presentación Interactiva (Público general — 25 a 30 min)

- **Archivo principal:** [`presentacion/index.html`](presentacion/index.html) (también se abre con doble clic en [`abrir_presentacion.bat`](abrir_presentacion.bat)).
- **100 % autocontenida y sin dependencias externas:** funciona sin internet en cualquier navegador moderno.
- **Atajos de teclado durante la exposición:**
  - `→`, `Espacio` o `AvPág`: siguiente diapositiva.
  - `←` o `RePág`: diapositiva anterior.
  - `N`: mostrar / ocultar **notas de orador** con el guion y el tiempo sugerido de cada pantalla.
  - `T`: iniciar / mostrar el **reloj de exposición** (cuenta hacia los 25:00 min).
  - `F`: activar / salir de **pantalla completa**.
- **Simulaciones interactivas incluidas en las diapositivas:**
  - *La regla de los 94 ms (escoba):* botón para soltar y cámara lenta con marcas en 2°, 4°, 8°, 16°, 32° y 64°.
  - *Equilibrio ante empujones:* botón para darle un empujón al robot con el control encendido o apagado.
  - *La paradoja de avanzar (cero de fase no mínima):* muestra cómo las ruedas patean 14 mm hacia atrás para inclinar el cuerpo antes de ir 30 cm hacia adelante.
  - *Mecanismo de cuatro barras en vivo:* deslizador de 10° a 40° que muestra cómo el eje de la rueda sube y baja casi en línea recta duplicando la altura de la cabina.
  - *La escalera de 7 escalones:* comparador animado de los tres modos (*Despacio*, *Frenando en cada escalón* y *De corrido*) y visualización de las +5.300 corridas del algoritmo genético.

---

## 2. Informe Técnico Final (Profesor)

- **Fuente LaTeX completa:** [`informe_tecnico_final.tex`](informe_tecnico_final.tex) (sincronizada con [`docs/modelo/modelo_del_segway.tex`](../docs/modelo/modelo_del_segway.tex)).
- **Estructura (16 capítulos + 5 apéndices):**
  - **Capítulos 1 a 10:** Mapa del modelo, geometría y masas medidas (962 g), cinemática y dinámica por Lagrange de la pata, péndulo invertido ($x, \varphi$), motor GA25-370 y límite de tracción ($\mu$), diseño y justificación del LQR, banco Simulink nativo, acoplamiento con patas móviles ($\delta_G(\theta)$) y plan de ensayos.
  - **Capítulo 11:** Diseño mecánico e iteración constructiva (evolución Hoeken $\to$ cuatro barras escala 80 $\to$ 3.ª iteración, elasticidad en serie del PLA que reduce el impacto en el eje del servo de 421 N a ~193 N, y soporte de mesa con trinquete).
  - **Capítulo 12:** Arquitectura electrónica y diseño de PCB (Placa de Potencia v0.7 y Placa de Lógica v0.6 por transferencia térmica, puentes MOSFET DRV8871, doble UBEC de 6 V, protecciones F1–F5/TVS/divisores y sensores de corriente INA219/INA226).
  - **Capítulo 13:** Firmware en tiempo real sobre ESP-IDF (FreeRTOS a 200 Hz en C puro, odometría compensada por cabeceo, filtro *notch* a 7,5 Hz, doble zona muerta `deadband`/`dbmov`, consigna flotante `xlibre`, inmunidad a caída libre e interfaz web + mando PS4 por HID).
  - **Capítulo 14:** Identificación experimental y ajuste del modelo (48 mediciones estáticas por WiFi en 13 alturas y onda cuadrada en 4 posturas; reducción del error RMS de equilibrio de $1{,}52^\circ$ a $0{,}08^\circ$ y rediseño de `LQR_TABLA` por altura).
  - **Capítulo 15:** Maniobra de descenso de escalón y escalera con algoritmo genético (LQR en vuelo para un escalón, imposibilidad física de frenar en 29 cm de pisada, optimización evolutiva en >5.300 corridas frente a 24 variaciones y recorte frontal de 2 cm en la cabina).
  - **Capítulo 16:** Conclusiones técnicas y lecciones de ingeniería.
  - **Apéndices A–E:** Deducciones algebraicas completas (cinemática, DCL, Lagrange de la pata en el aire y apoyada) y documentación constructiva de las placas electrónicas ([`placas_v0.7_completo.pdf`](../docs/placas_v0.7_completo.pdf)).

### Cómo compilar el PDF en una PC con MiKTeX / TeX Live

Desde esta carpeta (`Informe y presentacion/`), ejecutar dos pasadas de `pdflatex` para actualizar el índice y las referencias cruzadas:

```powershell
pdflatex -interaction=nonstopmode informe_tecnico_final.tex
pdflatex -interaction=nonstopmode informe_tecnico_final.tex
```
