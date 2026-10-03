# Simulación del péndulo invertido

Leer primero el [desarrollo matemático](../../modelado/planta/pendulo_invertido/desarrollo_matematico.md).
El objetivo de esta demostración es producir una trayectoria de la planta deducida y verificar
su interpretación física. El robot se libera cerca de la vertical, con patas fijas y sin controlador.

## Ejecutar

Abrir **`SIMULAR_PENDULO_INVERTIDO.m`** y pulsar Run. Encuentra las carpetas a partir de su propia
ubicación; puede ejecutarse desde cualquier carpeta. También, desde la raíz del repositorio:

```matlab
run('simulacion/pendulo_invertido/SIMULAR_PENDULO_INVERTIDO.m')
```

Usa MATLAB base y funciones disponibles en R2023b. La ejecución se verifica en la versión registrada
en `resultados/resultado_base.md`; no se afirma haber probado otra versión.

## Parámetros que conviene tocar

En la sección 2 del script:

- `theta_pata_deg`: postura de las patas, 10° plegada a 40° estirada en la variante vigente.
- `fisicos`: viene de `parametros_fisicos.m`. Se puede modificar masa, posición o inercia antes de
  llamar al adaptador, sin cambiar permanentemente la fuente común. Las masas allí están en g,
  posiciones en mm e inercias en kg·m².
- `tau_total_Nm`: par constante total de las dos ruedas. Por motor corresponde la mitad. No es
  par del servo de patas, tensión ni PWM; no incluye un límite de motor aún no identificado.
- Condiciones iniciales: `x_inicial_m`, `velocidad_x_inicial`, `phi_inicial_deg`, `velocidad_phi_inicial`.
- `p.b_eje`, `p.b_phi`, `p.b_x`: pérdidas viscosas en SI. Para conservación, poner las tres en cero.
- Duración, tolerancias, paso máximo y corte angular de demostración.

`phi` mide la inclinación de la línea eje–CoM, positiva antihoraria (hacia atrás) vista desde el lado derecho; `tau_total_Nm` también es positivo antihorario, por lo que un par negativo hace avanzar. El ángulo del chasis es `beta = phi - p.delta_G`.
Las masas e inercias de ruedas y el par son totales de las dos ruedas; la cabina se cuenta una vez.

El script está dividido en pasos, con las ecuaciones visibles en los tres archivos del modelo.
Las funciones al final del script solo integran el trabajo, detectan eventos y presentan los resultados.

## Salidas

Cada Run reemplaza los resultados de esta carpeta de demostración:

| Archivo en `resultados/` | Contenido |
|---|---|
| `resultado_base.md` | Parámetros, condiciones, matrices, autovalores, solver, fecha y commit base |
| `resultado_base.mat` | Parámetros originales y derivados, estados, energía y contacto completos |
| `trayectoria.csv` | Trayectoria y magnitudes principales, con unidades en las columnas |
| `respuesta.png` | No lineal frente a lineal, avance, contacto y energía frente al trabajo neto |
| `esquema_modelo.png` / `.svg` | Cuerpos equivalentes, coordenadas y acción/reacción de los pares |
| `verificacion.json` | Evidencia de las comprobaciones físicas al ejecutar la verificación |

La simulación termina ante el primero de estos eventos: ángulo de demostración alcanzado,
normal nula, margen de adherencia nulo. En los dos últimos casos el modelo de rodadura deja de
ser aplicable; no se continúa con fuerzas recortadas. El primer evento limita la gráfica y no
representa una colisión medida del robot.

La comparación lineal se informa hasta 5° como ventana de referencia, no como garantía universal
de precisión. El residuo `E(t)-E(0)-W(t)` debe ser pequeño frente a la energía característica
`p.m_cuerpo*p.g*p.l`. Un autovalor con parte real positiva muestra la inestabilidad sin control.

## Verificar

Desde esta carpeta:

```matlab
informe = verificar_pendulo_invertido();
```

Desde la raíz:

```matlab
addpath('simulacion/pendulo_invertido')
informe = verificar_pendulo_invertido();
```

Comprueba seis grupos: composición/matriz de masa en tres posturas; equilibrio y signos;
Jacobiano numérico frente a A/B; balances de potencia y Newton; energía conservativa; y actualización
de masa, CoM e inercia al agregar una carga. No modifica la simulación previa de la pata.
