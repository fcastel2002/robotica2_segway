# Sharp GP2Y0A60SZ (Pololu #2474)

Hoja de datos completa: [GP2Y0A60SZ_hoja_datos_OP13005EN-A.pdf](GP2Y0A60SZ_hoja_datos_OP13005EN-A.pdf) (Sharp, hoja OP13005EN-A, 10 págs.) [D], descargada el 11/11/2026 de la [copia de Northwestern](https://hades.mech.northwestern.edu/images/7/70/GP2YA60SZ.pdf). Matías envió antes capturas de las págs. 4 y 6.

| Archivo | Contenido |
|---|---|
| [2026-11-11_hoja_datos_tablas.png](2026-11-11_hoja_datos_tablas.png) | Máximos absolutos, condiciones recomendadas y características a 3 V y 5 V |
| [2026-11-11_hoja_datos_curva.png](2026-11-11_hoja_datos_curva.png) | Salida en función de la distancia, modos 3 V y 5 V (papel blanco, 90 %) |

Datos que usa el diseño (SUP-82):

- Modo 5 V (el del #2474): alimentación recomendada de 4,5 a 5,5 V. Modo 3 V: 2,7 a 3,6 V.
- Modo 5 V: Vo a 150 cm de 0,15 a 1,15 V (típ. 0,65); ΔVo de 10 a 150 cm de 2,75 a 3,25 V (típ. 3,00). Curva típica: 3,6 V a 10 cm.
- Modo 3 V: Vo a 150 cm típ. 0,35 V; ΔVo típ. 1,60 V. Curva típica: 1,9 V a 10 cm.
- Máximos absolutos: Vcc de −0,3 a 5,5 V; Vo de −0,3 a Vcc + 0,3 V.
- Consumo medio 33 mA típ., 50 mA máx.; en reposo (CTRL a 0 V) 5 µA máx.

Ficha del carrier: [Pololu #2474](https://www.pololu.com/product/2474) [V], consultada el 11/11/2026. El #2474 trae el modo 5 V; el #2476 es el mismo carrier en modo 3 V, y se cambia de uno a otro con una resistencia de 0 Ω.

Datos de la hoja completa que afectan el uso (11/11/2026):

- **Salida escalonada:** el sensor mide cada 16,5 ± 3,7 ms y mantiene la salida fija hasta la medida siguiente; la transición tarda hasta 5,0 ms. La primera medida después de encender o de activar CTRL es inestable (pág. 5). No hay filtro externo en Vo en el circuito de conexión de Sharp (pág. 3).
- **Pulsos del LED de más de 300 mA:** Sharp pide una fuente de 400 mA o más (pág. 2). El consumo medio sigue siendo de 33 mA.
- Notas de montaje (pág. 7): mantener limpia la lente, evitar luz solar directa en el detector y orientar la línea emisor-detector en paralelo a los bordes que se quieren detectar.

