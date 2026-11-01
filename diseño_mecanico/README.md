# diseño_mecanico

CAD del robot (SolidWorks 2026). Responsable: Francisco.

| Carpeta | Qué es |
|---|---|
| `3er_iteracion/` | **El CAD vigente** de la pata: acoplador `eslabon_cdp` (v3 y v4, idea 1, con STEP), manivela `eslabon_AD_v2` + `eslabon_AD_tapa`, balancín `eslabon_BC` (interno y externo, v4), cabina `cabeza_v4` y abrazadera del motor JGA25 |
| `chasis nuevo/` | Ensamble `chasis_cuasiFinal.SLDASM` con la cabina `cabeza_v4` / `cabeza_v4_v2`, el servo DS3225MG y `pcb_max_size` (el lugar disponible para la PCB) |
| `utilidades/` | Piezas compradas y de terceros: servo DS3225MG y su horn, motores (JGB37-520, JGA25-370, N20 y su soporte), sensor HC-SR04, rueda, `grua`, tuercas, tornillos y arandelas |

## Lo que se borró el 1/11/2026

Por pedido de Francisco quedaron solo esas tres carpetas. Se borraron `primera_iteracion/`,
`segunda_iteracion/`, `soporte_mesa/`, `step_printing/`, `medir_step/`, `outputs/` y la pieza suelta
`asml_eslabon_BC_externav4_local.SLDPRT` de la raíz. Todo sigue en git:

```bash
git checkout 2867761 -- "diseño_mecanico/segunda_iteracion"
```

recupera una carpeta entera, y `git show 2867761:"diseño_mecanico/<ruta>"` un archivo suelto.
Las cotas, masas e inercias que el modelo tomó de esas iteraciones siguen en
`modelado/parametros/parametros_fisicos.m` y `base_conocimiento/dimensiones_cad_primera_iteracion.md`.

SolidWorks referencia las piezas por ruta: si al abrir `chasis_cuasiFinal.SLDASM` falta alguna, estaba
en una de las carpetas borradas; recuperarla con el comando de arriba y copiarla a `3er_iteracion/`.

Los archivos `~$*.SLDPRT` que crea SolidWorks al abrir una pieza están en el `.gitignore`; no subirlos.
