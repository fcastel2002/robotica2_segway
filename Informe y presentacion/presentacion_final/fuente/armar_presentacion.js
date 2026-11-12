// Arma Segway_presentacion.pptx (16:9). Necesita pptxgenjs:  npm install pptxgenjs
//   node armar_presentacion.js
// Las imágenes salen de img/ (las genera figuras.py; las capturas tele_* son de ../telemetria/).
// El archivo queda editable en PowerPoint: lo normal es retocarlo ahí y no volver a correr esto.
const path = require("path");
const pptxgen = require("pptxgenjs");

const IMG = path.join(__dirname, "img");
const SALIDA = path.join(__dirname, "..", "Segway_presentacion.pptx");

// colores (hex sin #)
const TINTA = "22262B", OSCURO = "1F2A2E", GRIS = "6B7078", SUAVE = "B9BEC6", TENUE = "F3F4F6", LINEA = "DADDE2";
const NARANJA = "D9531E", BLANCO = "FFFFFF", HUESO = "F4F1EA";
const TEMA = {
  name: "Segway", headFontFace: "Calibri", bodyFontFace: "Calibri",
  colors: { dk1: TINTA, lt1: BLANCO, dk2: OSCURO, lt2: TENUE, accent1: NARANJA, accent2: "2B5FA8", accent3: "4F8F2A",
            accent4: "7B2D8E", accent5: GRIS, accent6: SUAVE, hlink: "2B5FA8", folHlink: "7B2D8E" },
};
// ancho / alto de una imagen PNG, leído de su encabezado
const fs = require("fs");
function proporcion(nombre) {
  const b = Buffer.alloc(24), f = fs.openSync(path.join(IMG, nombre + ".png"), "r");
  fs.readSync(f, b, 0, 24, 0); fs.closeSync(f);
  return b.readUInt32BE(16) / b.readUInt32BE(20);
}

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13,33 x 7,5 pulgadas
pres.theme = { headFontFace: TEMA.headFontFace, bodyFontFace: TEMA.bodyFontFace };
pres.title = "Segway con patas extensibles";
pres.author = "Grupo 4 - Robótica II - UNCUYO";

pres.defineSlideMaster({
  title: "CONTENIDO", background: { color: BLANCO },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.42, w: 12.1, h: 0.85, fontSize: 30, bold: true, color: TINTA, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "Segway con patas extensibles · Robótica II", options: { x: 0.6, y: 7.02, w: 6, h: 0.3, fontSize: 10, color: SUAVE, margin: 0 } } },
  ],
  slideNumber: { x: 12.1, y: 7.02, w: 0.63, h: 0.3, fontSize: 10, color: GRIS, align: "right" },
});
pres.defineSlideMaster({
  title: "OSCURA", background: { color: OSCURO },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.1, w: 7.4, h: 1.9, fontSize: 48, bold: true, color: BLANCO, align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
});

// ---------------------------------------------------------------- ayudas
let seccion = "";
function nueva(titulo, notas, oscura = false) {
  const s = pres.addSlide({ masterName: oscura ? "OSCURA" : "CONTENIDO", sectionTitle: seccion });
  s.addText(titulo, { placeholder: "title" });
  if (notas) s.addNotes(notas);
  return s;
}
function texto(s, t, x, y, w, h, o = {}) {
  s.addText(t, Object.assign({ x, y, w, h, fontSize: 16, color: TINTA, margin: 0, valign: "top", isTextBox: true, paraSpaceAfter: 6 }, o));
}
const FOTOS = { robot_portada: 630 / 1030, robot_parado: 640 / 850, robot_agachado: 640 / 850 };
function imagen(s, nombre, x, y, w, alt) {
  const foto = FOTOS[nombre];
  const h = w / (foto || proporcion(nombre));
  s.addImage({ path: path.join(IMG, nombre + (foto ? ".jpg" : ".png")), x, y, w, h, altText: alt || nombre });
  return h;
}
const neg = (t, extra = {}) => ({ text: t, options: Object.assign({ bold: true }, extra) });
const nor = (t, extra = {}) => ({ text: t, options: extra });

// ================================================================ 1. portada
seccion = "Presentación"; pres.addSection({ title: seccion });
{
  const s = nueva("Segway con\npatas extensibles",
    "Presentarse. Una frase: armamos desde cero un robot de dos ruedas que se equilibra solo, cambia de altura y baja un escalón. El robot está acá: al final lo mostramos andando.", true);
  texto(s, "Un robot de dos ruedas que se equilibra solo, cambia de altura y baja un escalón", 0.8, 4.05, 6.6, 0.9, { fontSize: 20, color: SUAVE });
  texto(s, "Joaquín Calderón · Francisco Castel · Matías Armani\nIgnacio Bartolini · Mariano Gimenez", 0.8, 5.55, 7.4, 0.7, { fontSize: 15, color: HUESO });
  texto(s, "Grupo 4 · Robótica II · Universidad Nacional de Cuyo · 2026", 0.8, 6.38, 7.4, 0.35, { fontSize: 13, color: SUAVE });
  const w = 7.5 * FOTOS.robot_portada;
  imagen(s, "robot_portada", 13.333 - w, 0, w, "El robot parado sobre sus dos ruedas");
}

// ================================================================ 2. para qué sirve
seccion = "El robot"; pres.addSection({ title: seccion });
{
  const s = nueva("Para qué sirve un robot así",
    "El problema que viene a resolver. Mover carga dentro de un depósito o una fábrica lo hacen hoy robots de cuatro ruedas: andan bien en piso liso y con lugar. " +
    "Uno de dos ruedas ocupa menos piso y gira sobre su eje, así que entra y maniobra donde el otro no. Las patas le suman lo que a las ruedas les falta: cambiar de altura, mantener derecha la carga y pasar un desnivel. " +
    "Ejemplos reales: Handle, de Boston Dynamics, para mover cajas; Ascento, de ETH Zúrich, para vigilancia.");
  const bloques = [
    ["Llevar carga de un lugar a otro", "En depósitos y fábricas ya lo hacen robots con ruedas. Son rápidos y gastan poco, mientras el piso sea liso y haya lugar."],
    ["Entrar donde uno de cuatro ruedas no entra", "Con dos ruedas ocupa menos piso y gira sobre su propio eje, sin maniobrar."],
    ["Pisos que no son parejos", "Las patas cambian la altura, mantienen derecha la carga y absorben un escalón."],
  ];
  bloques.forEach(([t, d], i) => {
    texto(s, t, 0.6, 1.55 + i * 1.5, 6.1, 0.4, { fontSize: 20, bold: true });
    texto(s, d, 0.6, 2.0 + i * 1.5, 6.1, 0.9, { fontSize: 16, color: GRIS });
  });
  imagen(s, "giro", 7.3, 1.5, 5.4, "Vista de arriba: un carro de cuatro ruedas necesita lugar para doblar; uno de dos ruedas gira en el lugar");
  texto(s, "Ya hay robots de este tipo trabajando: Handle (Boston Dynamics) mueve cajas en depósitos; Ascento (ETH Zúrich) hace rondas de vigilancia.",
    0.6, 6.25, 12.1, 0.5, { fontSize: 14, color: GRIS, italic: true });
}

// ================================================================ 3. el robot
{
  const s = nueva("El robot",
    "ACÁ SE MUESTRA EL ROBOT DE VERDAD, en la mano. Las dos fotos son el mismo robot, agachado y parado, a la misma escala. " +
    "La caja roja es la cabina: lleva la batería, las dos placas y los servos. De cada lado cuelga una pata, y en la punta de cada pata va una rueda con su motor. Señalar en el robot cada cosa mientras se nombra.");
  const h = imagen(s, "robot_agachado", 0.6, 1.45, 3.7, "Foto del robot agachado");
  imagen(s, "robot_parado", 4.5, 1.45, 3.7, "Foto del robot parado");
  texto(s, "agachado", 0.6, 1.45 + h + 0.1, 3.7, 0.35, { fontSize: 16, color: GRIS, align: "center" });
  texto(s, "parado", 4.5, 1.45 + h + 0.1, 3.7, 0.35, { fontSize: 16, color: GRIS, align: "center" });
  const datos = [["2 ruedas", "cada una con su motor y su encoder"], ["2 patas", "de cuatro barras, con un servo cada una"],
                 ["1,3 kg", "con la batería y las placas"], ["10 cm", "sube la cabina al estirar las patas"]];
  datos.forEach(([n, d], i) => {
    texto(s, n, 8.8, 1.75 + i * 1.22, 3.9, 0.5, { fontSize: 28, bold: true, color: NARANJA });
    texto(s, d, 8.8, 2.25 + i * 1.22, 3.9, 0.6, { fontSize: 15, color: GRIS });
  });
}

// ================================================================ 3b. la pata
{
  const s = nueva("La pata: un mecanismo de cuatro barras",
    "Con el dibujo y con el robot en la mano. La cabina es la barra fija: ahí están los dos pivotes, el del servo (A) y el del balancín (B). " +
    "El servo mueve la manivela; el balancín y el acoplador obligan a la rueda a subir y bajar casi en línea recta, justo debajo del servo. " +
    "Por eso alcanza con un solo servo por pata y el robot puede cambiar de altura sin moverse del lugar. Mover una pata a mano para que se vea.");
  const hg = imagen(s, "geometria", 0.45, 1.75, 9.0, "Perfil del robot agachado y parado, con los nombres de las barras");
  texto(s, "Todas las piezas están impresas en 3D.", 0.6, 1.75 + hg + 0.35, 8.4, 0.4, { fontSize: 16, color: GRIS });
  texto(s, "Un solo servo por pata.", 9.75, 1.85, 3.0, 0.5, { fontSize: 20, bold: true });
  texto(s, "El servo mueve la manivela. El balancín y el acoplador guían la rueda, que sube y baja casi en línea recta.", 9.75, 2.6, 3.0, 1.9, { fontSize: 16 });
  texto(s, "Por eso puede cambiar de altura parado en el lugar.", 9.75, 4.6, 3.0, 1.0, { fontSize: 16 });
}

// ================================================================ 4. versiones del diseño
{
  const s = nueva("Tres versiones del diseño",
    "Cómo fue cambiando el CAD y por qué (lo cuenta quien lo diseñó). 1.ª: barras largas para la cabina que teníamos; la rueda no bajaba derecha. " +
    "2.ª: todas las barras a escala 80; ahí la rueda sube y baja casi en línea recta. 3.ª, la que está armada: acoplador nuevo y cabina rediseñada para que entren las dos placas, con tapa. " +
    "Las imágenes salen de los archivos del CAD; se pueden cambiar por capturas de SolidWorks.");
  const X = [0.6, 4.77, 8.93], W = 3.8;
  ["1.ª iteración", "2.ª iteración", "3.ª iteración: la que está armada"].forEach((t, i) => texto(s, t, X[i], 1.5, W, 0.4, { fontSize: 18, bold: true }));
  imagen(s, "cad_1ra_iteracion", X[0] + 0.55, 2.05, 2.65, "Ensamble completo de la primera iteración");
  imagen(s, "cad_cabina_v31", X[1] + 0.6, 2.05, 2.6, "Cabina de la segunda iteración");
  imagen(s, "cad_acoplador_v2", X[1] + 0.4, 4.45, 3.0, "Acoplador de la segunda iteración");
  imagen(s, "cad_cabina_v4", X[2] + 0.6, 2.05, 2.6, "Cabina de la tercera iteración");
  imagen(s, "cad_acoplador_v4", X[2] + 0.4, 4.4, 3.0, "Acoplador de la tercera iteración");
  ["Barras largas para la cabina que había: la rueda no bajaba derecha.",
   "Barras a escala 80: la rueda sube y baja casi en línea recta.",
   "Acoplador nuevo y cabina rediseñada, con lugar para las dos placas y tapa."]
    .forEach((t, i) => texto(s, t, X[i], 5.85, W - 0.2, 0.9, { fontSize: 15, color: GRIS }));
}

// ================================================================ 5. motores y servos
function ficha(s, filas, x, y, w, parte = 0.42) {
  s.addTable(filas.map(([a, b]) => [
    { text: a, options: { color: GRIS, fontSize: 14 } }, { text: b, options: { color: TINTA, fontSize: 14, bold: true } }]),
    { x, y, w, colW: [w * parte, w * (1 - parte)], rowH: 0.45, margin: [0, 0.05, 0, 0], valign: "middle",
      border: [{ type: "none" }, { type: "none" }, { type: "solid", pt: 0.75, color: LINEA }, { type: "none" }] });
}
{
  const s = nueva("Motores y servos",
    "Motor de rueda: GA25-370 de 12 V con reductor y encoder. Sin carga da unas 300 vueltas por minuto; medimos 312. El par máximo, unos 4 kg·cm, está calculado con la resistencia que medimos, porque la ficha del vendedor se contradice. " +
    "Por qué con encoder: sin saber cuánto giró cada rueda no se puede avanzar ni frenar en un lugar. " +
    "Servo: DS3240 de 40 kg·cm, a 6 V. Por qué tan grande: al caer de un escalón la pata le pide unos 20 kg·cm de golpe; uno de 25 quedaba justo.");
  texto(s, "Motor de las ruedas: GA25-370 con encoder", 0.6, 1.5, 5.9, 0.4, { fontSize: 19, bold: true });
  imagen(s, "motor_foto", 0.5, 2.15, 2.05, "Foto del motorreductor GA25-370 con encoder");
  ficha(s, [["Tensión", "12 V"], ["Velocidad sin carga", "300 rpm"], ["Reducción", "1 : 20"], ["Par máximo", "≈ 4 kg·cm"],
            ["Encoder", "899 cuentas por vuelta"], ["Peso", "96 g"]], 2.7, 2.1, 3.8, 0.45);
  texto(s, [neg("Por qué: "), nor("con encoder, porque para avanzar y frenar hay que saber cuánto giró cada rueda.")], 0.6, 5.1, 5.85, 0.8, { fontSize: 15 });
  texto(s, "El par está calculado con lo que medimos en el robot (7,8 Ω): la ficha del vendedor no cierra.", 0.6, 6.0, 5.85, 0.6, { fontSize: 12, color: GRIS });

  texto(s, "Servo de las patas: DS3240 MG", 6.95, 1.5, 5.8, 0.4, { fontSize: 19, bold: true });
  imagen(s, "servo_foto", 6.95, 2.2, 2.1, "Foto del servo DS3240 de 40 kg");
  ficha(s, [["Tensión", "4,8 a 6,8 V (va a 6 V)"], ["Par a 5 V", "36 kg·cm"], ["Par a 6,8 V", "45 kg·cm"], ["Velocidad", "60° en 0,2 s"],
            ["Engranajes", "metálicos"], ["Peso", "60 g"]], 9.3, 2.1, 3.45);
  texto(s, [neg("Por qué: "), nor("al caer de un escalón la pata le pide unos 20 kg·cm de golpe. Uno de 25 quedaba justo.")], 6.95, 5.1, 5.8, 0.8, { fontSize: 15 });
}

// ================================================================ 6. electrónica
{
  const s = nueva("La electrónica: dos placas hechas por nosotros",
    "Dos placas diseñadas en KiCad y fabricadas con el método de la plancha. La de potencia lleva lo que mueve corriente: los dos drivers de los motores, las fuentes de los servos, los fusibles y tres medidores de corriente. " +
    "La de lógica lleva el microcontrolador (ESP32-S3), la IMU y los conectores de encoders y sensores. Por qué separadas: para que el ruido de los motores no llegue al micro ni a la IMU. " +
    "Por qué placas y no cables: con la primera versión, cableada, el ESP32 se reiniciaba con cada golpe.");
  const w = 5.55;
  const h = imagen(s, "placa_potencia_3d", 0.6, 1.5, w, "Placa de potencia, vista 3D de KiCad");
  imagen(s, "placa_logica_3d", 7.18, 1.5, w, "Placa de lógica, vista 3D de KiCad");
  texto(s, [neg("Potencia. "), nor("Los dos drivers de los motores, las fuentes de 6 V de los servos, tres medidores de corriente y cinco fusibles.")], 0.6, 1.5 + h + 0.15, w, 0.9, { fontSize: 15 });
  texto(s, [neg("Lógica. "), nor("El microcontrolador (ESP32-S3), la IMU y los conectores de los encoders y los sensores.")], 7.18, 1.5 + h + 0.15, w, 0.9, { fontSize: 15 });
  texto(s, "Fabricadas con el método de la plancha. Batería LiPo de 3 celdas. Con la versión cableada, el ESP32 se reiniciaba en cada golpe.",
    0.6, 6.42, 12.1, 0.4, { fontSize: 14, color: GRIS });
}

// ================================================================ 6b. batería y corriente
{
  const s = nueva("Batería y corriente",
    "Para qué sirvieron los medidores de corriente de la placa de potencia. " +
    "AUTONOMÍA: la batería es una LiPo de 3 celdas y 2200 mAh. El robot mide su tensión, calcula la carga y estima los minutos que quedan. En las pruebas del 9/11, equilibrando en el lugar, marcó entre 2 y 3 horas; en una hora y cuarto de pruebas la carga bajó de 79 a 66 %. Es una estimación: manejándolo dura menos, y el consumo de los servos no se mide. " +
    "RESISTENCIA: con la rueda frenada y el medidor de corriente se midió cada motor: 8,1 ohm el izquierdo y 7,6 el derecho. De la ficha del vendedor salían 10,3. Con el valor medido se corrigió el modelo. " +
    "PROTECCIÓN: un fusible en cada rama (4 A por motor), la protección propia del driver, y por programa los motores se apagan si quedan un segundo a fondo o si el robot se cae.");
  const filas = [
    ["2 a 3 horas", "Autonomía",
     "La batería es una LiPo de 2200 mAh. El robot mide su tensión, calcula cuánta carga le queda y estima los minutos de autonomía. Equilibrando en el lugar marcó entre 2 y 3 horas."],
    ["7,8 Ω", "La resistencia real de los motores",
     "Con la rueda frenada y los medidores de corriente de la placa se midió cada motor. De la ficha salían 10,3 Ω. Con el valor medido se corrigió el modelo."],
    ["3 protecciones", "La corriente tiene límite",
     "Un fusible en cada rama; el driver, que se corta solo si la corriente se pasa; y el programa, que apaga los motores si quedan un segundo a fondo o si el robot se cae."],
  ];
  filas.forEach(([valor, titulo, detalle], i) => {
    const y = 1.65 + i * 1.72;
    texto(s, valor, 0.6, y, 3.4, 0.7, { fontSize: 30, bold: true, color: NARANJA });
    texto(s, titulo, 4.3, y + 0.03, 8.4, 0.45, { fontSize: 20, bold: true });
    texto(s, detalle, 4.3, y + 0.55, 8.4, 1.0, { fontSize: 16, color: GRIS });
  });
}

// ================================================================ 7. cómo no se cae
seccion = "El control"; pres.addSection({ title: seccion });
{
  const s = nueva("Cómo hace para no caerse",
    "Es un péndulo invertido: como sostener una escoba parada en la mano. Si se inclina para adelante, las ruedas avanzan hasta quedar otra vez debajo del cuerpo. " +
    "Eso lo decide 200 veces por segundo, mirando cuatro cosas: la inclinación y qué tan rápido cambia (las da la IMU), y dónde está y a qué velocidad va (las dan los encoders).");
  const h = imagen(s, "equilibrio", 0.6, 1.5, 7.7, "Si el robot se inclina, las ruedas avanzan y quedan debajo del cuerpo");
  texto(s, "La IMU da las dos primeras; los encoders de las ruedas, las otras dos.", 0.6, 1.5 + h + 0.3, 7.7, 0.4, { fontSize: 15, color: GRIS });
  texto(s, "Es un péndulo invertido: si nadie lo corrige, se cae.", 8.8, 1.6, 3.95, 0.9, { fontSize: 19, bold: true });
  texto(s, "200 veces por segundo mide cuatro cosas:", 8.8, 2.8, 3.95, 0.4, { fontSize: 16 });
  texto(s, ["cuánto está inclinado", "qué tan rápido se inclina", "dónde está", "a qué velocidad va"].map((t, i, a) =>
    ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } })), 8.8, 3.3, 3.95, 1.8, { fontSize: 16, paraSpaceAfter: 8 });
  texto(s, "Con eso decide cuánto empujar con las ruedas.", 8.8, 5.2, 3.95, 0.7, { fontSize: 16 });
}

// ================================================================ 8. por qué LQR
{
  const s = nueva("Por qué un LQR y no un PID",
    "Lo probamos en la simulación. Un PID que mira solo la inclinación lo sostiene un rato, pero el robot se va corriendo y termina cayéndose. Si además mira la velocidad, queda parado, pero donde quedó. " +
    "Nosotros queremos que se quede en el lugar que le decimos: para eso hay que mirar las cuatro variables a la vez, y las cuatro están atadas entre sí con un solo actuador. " +
    "El LQR es la forma de calcular las cuatro ganancias de una sola vez: le decimos cuánto error aceptamos en cada una y resuelve. Y cuando las patas cambian de altura, se recalcula con las mismas reglas. " +
    "OJO con las preguntas: no decir que es 'óptimo' ni que es 'mejor que un PID' en general.");
  const fila = (a, b, fuerte) => [
    { text: a, options: { fontSize: 17, bold: fuerte, color: TINTA, fill: { color: fuerte ? TENUE : BLANCO } } },
    { text: b, options: { fontSize: 17, bold: fuerte, color: fuerte ? NARANJA : TINTA, fill: { color: fuerte ? TENUE : BLANCO } } }];
  s.addTable([
    [{ text: "Si el control mira…", options: { fontSize: 14, color: GRIS } }, { text: "…el robot", options: { fontSize: 14, color: GRIS } }],
    fila("solo la inclinación (un PID)", "se sostiene un rato, se va corriendo y termina en el piso"),
    fila("la inclinación y la velocidad", "queda parado, pero donde quedó: nada lo trae de vuelta"),
    fila("las cuatro: inclinación, su velocidad, posición y velocidad", "vuelve a su lugar y va adonde se le pide", true),
  ], { x: 0.6, y: 1.55, w: 12.1, colW: [5.4, 6.7], rowH: [0.4, 0.7, 0.7, 0.7], margin: [0, 0.1, 0, 0.1], valign: "middle",
       border: [{ type: "none" }, { type: "none" }, { type: "solid", pt: 0.75, color: LINEA }, { type: "none" }] });
  texto(s, "Las cuatro dependen una de otra y hay un solo actuador: no se pueden ajustar por separado.", 0.6, 4.45, 5.6, 1.0, { fontSize: 17 });
  texto(s, "El LQR calcula las cuatro ganancias juntas. Le decimos cuánto error aceptamos (10 cm de posición, 8° de inclinación) y resuelve el resto. Para cada altura de las patas, las recalcula.",
    6.75, 4.45, 5.95, 1.5, { fontSize: 17 });
  texto(s, "motor = kx · posición + kv · velocidad + kφ · inclinación + kω · velocidad de inclinación", 0.6, 6.3, 12.1, 0.4, { fontSize: 15, color: GRIS, italic: true });
}

// ================================================================ 9. diseñado en la computadora
{
  const s = nueva("El control se diseñó en la computadora",
    "Lo más importante de esta parte: el control no se ajustó a prueba y error sobre el robot. Armamos el modelo en Simulink (batería, motores, agarre de las ruedas, mecánica), calculamos el LQR ahí y lo probamos ahí. " +
    "Las ganancias que tiene cargadas el robot son las de ese cálculo. Eso muestra que se puede diseñar en simulación algo que después anda en la realidad. " +
    "Para que valga, las señales que se miden tienen que ser buenas: de ahí salen los filtros de la diapositiva que sigue. " +
    "En el robot se ajustó un factor de escala de las ganancias (quedó en 87 %) y los filtros.");
  const h = imagen(s, "simulink_modelo", 0.6, 1.5, 12.1, "Modelo del robot en Simulink: consigna, control LQR, batería y motores, mecánica");
  texto(s, "El modelo en Simulink: adónde se le pide ir, el control, la batería con los motores y la mecánica del robot.", 0.6, 1.5 + h + 0.08, 12.1, 0.3, { fontSize: 13, color: GRIS });
  const h2 = imagen(s, "simulink_respuesta", 0.6, 4.72, 7.6, "Simulación: el robot avanza 30 cm y se queda");
  texto(s, "Simulación: se le pide avanzar 30 cm. Retrocede apenas, va y se queda.", 0.6, 4.72 + h2 + 0.06, 7.6, 0.3, { fontSize: 13, color: GRIS });
  texto(s, "Las ganancias que usa el robot salieron de acá.", 8.65, 4.7, 4.05, 1.1, { fontSize: 22, bold: true, color: NARANJA });
  texto(s, "En el robot se ajustó solo un factor de escala (87 %) y los filtros.", 8.65, 5.85, 4.05, 0.8, { fontSize: 15, color: GRIS });
}

// ================================================================ 10. lo que no anduvo
{
  const s = nueva("Lo que no anduvo a la primera",
    "Tres problemas reales. 1) Vibraba solo: el robot tiene una vibración propia de 7 a 8 Hz y el control la agrandaba; se resolvió con un filtro que saca esa frecuencia. " +
    "2) Cuando pusimos las placas nuevas, los drivers nuevos le dieron más fuerza a los motores (un 44 % más con el mismo comando): hubo que medir los motores, actualizar el modelo y recalcular el LQR y los filtros. " +
    "3) Se nos quemó un driver, pero a medias: para un lado andaba y para el otro entregaba menos tensión. Lo difícil fue darse cuenta; apareció probando el módulo solo en la mesa.");
  const X = [0.6, 4.77, 8.93], W = 3.75;
  const casos = [
    ["Vibraba solo", "El robot tiene una vibración propia, de 7 a 8 veces por segundo. El control la agrandaba hasta llevar los motores de tope a tope.",
     "Un filtro que saca justo esa frecuencia de lo que se le manda a los motores."],
    ["Las placas nuevas le dieron más fuerza", "Con los drivers nuevos, el mismo comando empuja un 44 % más. El control quedó pasado y el robot se balanceaba.",
     "Medimos los motores, actualizamos el modelo y recalculamos las ganancias y los filtros."],
    ["Un driver quemado a medias", "Hacia adelante andaba bien. Hacia atrás entregaba 3,8 V donde tenían que salir 9.",
     "Lo probamos solo, en la mesa, con el osciloscopio. Ahí apareció, y lo cambiamos."],
  ];
  casos.forEach(([t, pasaba, hicimos], i) => {
    texto(s, String(i + 1), X[i], 1.45, 1, 0.7, { fontSize: 40, bold: true, color: NARANJA });
    texto(s, t, X[i], 2.25, W, 0.85, { fontSize: 20, bold: true });
    texto(s, pasaba, X[i], 3.2, W, 1.5, { fontSize: 15, color: GRIS });
    texto(s, [neg("Qué hicimos. ", { color: NARANJA }), nor(hicimos)], X[i], 4.85, W, 1.5, { fontSize: 15 });
  });
}

// ================================================================ 11 a 14. la aplicación
seccion = "La aplicación y el joystick"; pres.addSection({ title: seccion });
function pantalla(titulo, img, puntos, notas) {
  const s = nueva(titulo, notas + " (La misma pantalla está en la carpeta telemetria, para abrirla en el navegador a pantalla completa.)");
  const h = imagen(s, img, 0.6, 1.5, 8.45, "Pantalla de la aplicación");
  texto(s, "Pantalla rehecha para que se lea al proyectarla.", 0.6, 1.5 + h + 0.1, 8.45, 0.3, { fontSize: 12, color: SUAVE });
  texto(s, puntos.map((t, i) => ({ text: t, options: { breakLine: i < puntos.length - 1 } })), 9.4, 1.55, 3.3, 4.7, { fontSize: 16, paraSpaceAfter: 16 });
}
pantalla("La aplicación: manejarlo con un joystick", "tele_1_mando",
  ["Se maneja con un joystick de PS4.", "La notebook lee el joystick y le manda las órdenes al robot por WiFi.", "En la pantalla se ve lo que se le pide y lo que el robot hace de verdad."],
  "La aplicación es una página web hecha por nosotros; corre en la notebook. Primera pantalla: manejo. El joystick va por Bluetooth a la notebook y de ahí al robot por WiFi, 25 veces por segundo.");
pantalla("La aplicación: probar cada parte por separado", "tele_2_banco_de_pruebas",
  ["Cada sensor y cada motor, uno por uno.", "Sirve para revisar el robot antes de pararlo.", "Las ganancias del control se cambian desde acá, sin volver a grabar el programa."],
  "Banco de pruebas: la IMU, los encoders, los motores y los servos por separado. Es lo primero que se mira cuando algo no anda.");
pantalla("La aplicación: batería y consumo", "tele_3_energia",
  ["La placa de potencia mide la corriente de cada motor y la tensión de la batería.", "Con la tensión calcula la carga y estima los minutos de autonomía; avisa cuando está baja.", "El gráfico es de una bajada real del escalón: el pico es la frenada."],
  "Energía: tensión y carga de la batería y corriente de cada motor. El gráfico es de una bajada de escalón grabada el 11/11.");
pantalla("La aplicación: ver qué pasó en cada prueba", "tele_4_graficos",
  ["Todo lo que mide el robot, en el momento.", "Además graba 8 segundos con 200 datos por segundo.", "Con esas grabaciones comparamos el robot contra la simulación."],
  "Gráficos: lo que se ve acá es una bajada real del escalón de 12 cm: inclinación, velocidad, lo que se manda a los motores y las patas. La franja es el vuelo.");

// ================================================================ 16. el escalón
seccion = "El escalón"; pres.addSection({ title: seccion });
{
  const s = nueva("Bajar un escalón de 12 cm",
    "Lo baja de espaldas, con un botón. Toma carrera hacia atrás, pasa el borde a 0,65 m/s, en el aire estira las patas, toca y frena. Queda parado a medio metro. " +
    "El dibujo está hecho con los datos de la simulación.");
  const h = imagen(s, "escalon_secuencia", 0.6, 1.45, 12.1, "Cinco momentos de la bajada del escalón");
  const pasos = ["De espaldas al escalón, quieto, con las patas a media altura.", "Retrocede acelerando hasta pasar el borde a 0,65 m/s.",
                 "En el aire estira las patas. El vuelo dura 0,12 segundos.", "Toca el piso y empieza a frenar.", "Queda parado, a medio metro del escalón."];
  pasos.forEach((t, i) => texto(s, [neg(String(i + 1) + "  ", { color: NARANJA }), nor(t)], 0.6 + i * 2.45, 1.45 + h + 0.2, 2.25, 1.2, { fontSize: 14 }));
}

// ================================================================ 17. simulación contra robot
{
  const s = nueva("Primero en la simulación, después en el robot",
    "Clave: la bajada no se probó tirando el robot. Se armó un simulador que corre el mismo programa que lleva el robot, y ahí se eligió la velocidad y se probó contra 32 variantes: batería más baja, más peso, piso resbaloso, escalones de 10 a 15 cm. " +
    "Recién después se hizo en el robot: 3 de 3. El gráfico compara la misma bajada: en azul lo que dijo la simulación, en naranja lo que midió el robot.");
  const h = imagen(s, "escalon_robot_vs_simulacion", 0.5, 1.5, 8.9, "La misma bajada en la simulación y en el robot: avance y velocidad");
  [["0,65 y 0,66 m/s", "velocidad al pasar el borde: simulación y robot"], ["0,115 y 0,120 s", "tiempo en el aire: simulación y robot"]].forEach(([n, d], i) => {
    texto(s, n, 9.75, 1.65 + i * 1.45, 3, 0.5, { fontSize: 26, bold: true, color: NARANJA });
    texto(s, d, 9.75, 2.15 + i * 1.45, 3, 0.7, { fontSize: 14, color: GRIS });
  });
  const y = 1.5 + h + 0.35;
  [["El mismo programa", "El simulador corre el mismo código que lleva el robot."],
   ["32 de 32", "variantes simuladas bajan bien: otra batería, más peso, piso resbaloso, escalón de 10 a 15 cm."],
   ["3 de 3", "bajadas en el robot, a esa velocidad."]].forEach(([n, d], i) => {
    texto(s, n, 0.6 + i * 4.17, y, 3.8, 0.45, { fontSize: 20, bold: true });
    texto(s, d, 0.6 + i * 4.17, y + 0.5, 3.8, 0.9, { fontSize: 15, color: GRIS });
  });
}

// ================================================================ 18. qué le agregaríamos
seccion = "Cierre"; pres.addSection({ title: seccion });
{
  const s = nueva("Lo que le agregaríamos",
    "Tres cosas que quedan para una próxima versión. Cerrar acá, pedir preguntas y después pasar a la demostración.");
  const X = [0.6, 4.77, 8.93], W = 3.75;
  const ideas = [
    ["Que salte escalones", "Ya los baja. El paso que sigue es subirlos."],
    ["Sensores para andar solo", "Detectar y esquivar obstáculos, y adaptarse a la forma del piso sin que nadie lo maneje."],
    ["Otro material", "Más resistente que el plástico impreso, para poder llevar carga."],
  ];
  ideas.forEach(([t, d], i) => {
    texto(s, String(i + 1), X[i], 1.75, 1, 0.8, { fontSize: 40, bold: true, color: NARANJA });
    texto(s, t, X[i], 2.65, W, 0.5, { fontSize: 22, bold: true });
    texto(s, d, X[i], 3.3, W, 1.6, { fontSize: 16, color: GRIS });
  });
}

// ================================================================ 19 y 20. preguntas y demostración
{
  const s = nueva("¿Preguntas?", "Preguntas del público y de los profesores, antes de prender el robot.", true);
  imagen(s, "portada_robot", 8.55, 1.55, 4.1, "Dibujo de perfil del robot");
}
{
  const s = nueva("Demostración\nen vivo", "Orden sugerido en la guía: equilibrio, empujón, subir y bajar las patas, manejarlo, girar en el lugar y, al final, el escalón.", true);
  texto(s, ["Se equilibra en su lugar", "Aguanta un empujón", "Sube y baja de altura", "Se maneja con el joystick", "Baja el escalón"].map((t, i, a) =>
    ({ text: t, options: { bullet: true, breakLine: i < a.length - 1 } })), 0.8, 4.2, 6.5, 2.4, { fontSize: 19, color: HUESO, paraSpaceAfter: 8 });
  imagen(s, "portada_robot", 8.55, 1.55, 4.1, "Dibujo de perfil del robot");
}

(async () => {
  await pres.writeFile({ fileName: SALIDA });
  // opcional: dejar la paleta del tema en el archivo, si está a mano la herramienta que lo hace
  if (process.env.APLICAR_TEMA) {
    const { applyTheme } = require(process.env.APLICAR_TEMA);
    await applyTheme(SALIDA, TEMA);
  }
  console.log("listo:", SALIDA);
})();
