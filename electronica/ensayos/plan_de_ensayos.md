# Ensayos de electrónica y puesta en marcha

Fecha: 15/10/2026. Responsable: Matías. **Procedimiento propuesto; ensayos todavía no ejecutados.**

Plan general: [electrónica y PCB](../../docs/gestion/2026-10-15-plan-electronica-pcb.md). Los límites de alimentación y corriente deben fijarse con la [matriz de requisitos](../requisitos_y_decisiones.md) y la placa concreta antes de energizar.

## Preparación

Usar multímetro y fuente regulable con limitación de corriente. Para picos, caídas rápidas, ruido y PWM se necesita osciloscopio; un analizador lógico es útil para I²C y encoder. Verificar que la instrumentación y las masas de las sondas no creen cortocircuitos. Documentar si la fuente puede absorber energía de frenado; si no, definir el montaje adecuado antes de ensayar frenadas.

Sujetar el robot/actuador; mantener ruedas o horn sin carga al comienzo. Probar cargas mecánicas progresivas. La corriente de bloqueo se obtiene de documentación confiable, resistencia medida a baja tensión o un ensayo breve y controlado; no bloquear directamente a plena tensión sin límites definidos. No pasar la corriente de motores/servos por protoboard.

## Secuencia

| Ensayo | Preparación y acción | Registrar | Criterio de avance |
|---|---|---|---|
| E-01 Inspección | Identificar placas, polaridad, puentes, shunts, conexiones y dimensiones; revisar continuidad sin energía | Fotos y pinout del ejemplar; cortocircuitos/puentes encontrados | Alimentaciones, masa y conectores identificados |
| E-02 Reguladores | Salidas sin actuadores; después carga progresiva dentro de límites conocidos | Entrada, salida mínima/máxima, corriente, temperatura y rizado con condiciones de medición | Tensión dentro del rango de cada carga y respuesta térmica aceptable en régimen |
| E-03 ESP32 + IMU | Alimentación verificada; lectura de identidad, acelerómetro/giro, calibración en reposo y orientación | Versión, eje de pitch/signo, muestras con timestamp, errores I²C, sesgo y saturación | Lectura estable y configuración reproducible; tiempo compatible con objetivo de 5 ms |
| E-04 Un motor + encoder | Rueda libre; PWM bajo; aumento progresivo; inversión primero pasando por cero | Corriente en entrada del driver, VM, velocidad, cuentas por vuelta, niveles A/B, temperatura y ruido | Ambos sentidos y conteo coherentes; driver dentro de límites; sin reinicios de ESP32 |
| E-05 Un servo | Horn sin mecanismo; tensión verificada; recorrido acotado y carga representativa después | Pulsos, posición útil, corriente pico/media, tensión mínima y temperatura | Recorrido calibrado sin tocar topes; fuente dentro de límites |
| E-06 Ambos servos | Carga progresiva y simultánea representativa del robot | Tensión en cada servo y consumo total del UBEC; picos/duración y temperatura | Sin caída fuera del rango ni protección térmica; UBEC validado o reemplazo definido |
| E-07 Sensores de consumo | Shunt/ramal previamente dimensionados; comparar con instrumento patrón | Valor real del shunt, calibración, caída, potencia disipada, rango y dirección | Error documentado, sin exceder rango ni introducir caída inaceptable |
| E-08 Conjunto | Dos drivers disponibles; IMU/encoders/servos y telemetría simultáneos con soporte | Duración de ciclo, variación, pérdida de cuentas, errores, reinicios, mínimos de tensión y temperaturas | Interfaces simultáneas confiables; no hay fallas eléctricas pendientes antes de cerrar PCB |
| E-09 Fallas | Reset, arranque, desconexión de sensor, timeout, batería baja simulada y paro | Orden de eventos, tiempo de reacción, estado de cada actuador y recuperación | Respuesta igual a la definida con mecánica/control; no hay movimiento inesperado al habilitar |
| E-10 Placa fabricada | Inspección; continuidad; fuente limitada; energizar por bloques y repetir E-02 a E-09 | Revisión PCB/BOM, reparación, fuente/carga y registros | Esquemático, montaje y comportamiento concordantes |

Los umbrales de error, temperatura y tensión se completan a partir de las placas reales y del presupuesto de diseño. No se declara un ensayo aprobado solo por observar que el motor gira o el servo se mueve.

## Registro por ensayo

Copiar esta ficha en un archivo de resultados nuevo:

- ID, fecha, responsable y objetivo:
- Modelo y unidad física del componente:
- Revisión de cableado/PCB y firmware:
- Instrumentos y configuración, límite de corriente:
- Alimentación real y condiciones de carga:
- Procedimiento, duración y configuración PWM/pulsos/filtros:
- Resultados mínimos/máximos/medios; datos y capturas adjuntos:
- Límite aplicable y fuente:
- Resultado: pendiente / aprobado / requiere corrección:
- Corrección necesaria y repetición prevista:

Los valores obtenidos para el motor y su encoder se entregan al responsable del modelado para PAR-003. Los cambios de simulación se hacen en la fuente única de parámetros, con evidencia y revisión del equipo.
