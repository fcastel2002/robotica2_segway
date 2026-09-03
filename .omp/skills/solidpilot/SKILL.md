---
name: solidpilot
description: Usa SolidPilot mediante el MCP de SolidWorks para crear, editar, reconstruir, ensamblar, verificar, documentar o exportar piezas, chapas, assemblies y dibujos. Impone recetas y esquemas vigentes, ejecución CAD secuencial, unidades correctas, Feature Graph como ruta principal y compuertas estrictas contra piezas vacías, assemblies vacíos, componentes omitidos y mates físicamente incoherentes.
---

# SolidPilot riguroso

Usar esta skill para operar el servidor de [SolidPilot](https://github.com/eyfel/mcp-server-solidworks). La prioridad es la validez geométrica y mecánica, no producir un archivo que solamente abra en SolidWorks.

## Condición de terminado

No declarar terminado un trabajo hasta que se cumplan todas las condiciones aplicables:

- Cada operación requerida devolvió `COMPLETED`; una respuesta parcial, ambigua o `FAILED` no cuenta.
- La pieza tiene al menos un cuerpo sólido cuando el encargo exige un sólido, volumen positivo y el árbol esperado.
- El assembly contiene exactamente el inventario previsto; nunca aceptar un `.SLDASM` sólo porque fue guardado.
- Cada mate corresponde a una relación física identificable, usa geometría compatible y conserva o elimina exactamente los grados de libertad previstos.
- No hay componentes, features, cotas, bends ni contornos omitidos en silencio.
- Se ejecutaron las lecturas de verificación aplicables y se compararon con resultados esperados calculados antes de modelar.
- El documento final se guardó en la ruta solicitada y se volvió a verificar después del guardado.
- Toda limitación no verificable se informa como tal. No afirmar ausencia de interferencias: el MCP actual no expone un analizador objetivo de interferencias.

Si falta una decisión que cambia la geometría, el montaje, la función cinemática o la fabricación, agotar primero archivos, selección de SolidWorks, árbol, recetas, esquemas y análisis. Si la ambigüedad persiste, formular una pregunta concreta antes de inventar geometría o mates.

## Fuentes autoritativas y preflight obligatorio

Las recetas y esquemas servidos por el MCP son más autoritativos y actuales que esta skill. Al iniciar cada trabajo:

1. Consultar `recipe://usage/index` y registrar la versión indicada.
2. Leer `recipe://usage/forward` antes de crear un Feature Graph desde intención de diseño.
3. Leer `schema://feature-graph` antes de escribir cualquier `ir.graph`; el esquema es el registro real de capacidades. Lo que no aparece allí no se puede construir mediante IR.
4. Para reproducir una pieza o assembly existente, leer `recipe://usage/contract`, `recipe://usage/canonicalization`, `recipe://usage/mapping`, la sección específica (`recipe://usage/mapping_part`, `recipe://usage/mapping_sheet_metal` o `recipe://usage/mapping_assembly`) y `recipe://usage/verification`. Leer también `schema://analysis-artifact`.
5. Para reconstruir desde DXF/DWG, leer `recipe://usage/reverse` antes de interpretar el payload completo.
6. Para trabajos por lote o carpeta, leer `recipe://usage/coverage` y emitir su resumen de cobertura; no contar un archivo fallido como verificado.
7. Volver a consultar el índice si el servidor se reconectó, cambió de versión o contradice una regla recordada.
8. Ejecutar `ensure_ready`. Confirmar servidor, COM, versión de SolidWorks, documento activo y `state_version`.
9. Definir el tipo de documento esperado, las entradas, la ruta final y los invariantes verificables antes de mutar CAD.

Nunca reemplazar estas lecturas con conocimiento memorizado ni con el README del repositorio.

## Serialización y estado

- Todas las llamadas del MCP SolidPilot, de lectura o escritura, se hacen secuencialmente. Nunca lanzar herramientas CAD en paralelo ni solapar operaciones sobre la sesión GUI.
- Respetar el `state_version` devuelto por cada llamada. El adaptador lo gestiona y reintenta una vez ante `INVALID_STATE_VERSION`; no inventarlo ni reutilizar una respuesta anterior.
- No ejecutar más de dos mutaciones CAD sin un checkpoint. Para cambios topológicos, preferir un checkpoint después de cada feature.
- `submit_feature_graph` es una única operación orquestada y constituye la excepción al límite anterior: el compilador ejecuta los nodos secuencialmente y devuelve un reporte por nodo. Verificar inmediatamente al terminar.
- Las operaciones CAD no son transaccionales. Si un Feature Graph falla, abandonar el documento parcial y reenviar el grafo corregido con `fresh_document=true`. No parchear una construcción parcial como si fuera íntegra.
- Ante errores de conexión o COM, ejecutar `ensure_ready` y reintentar una vez. Ante otro error, corregir su causa; no repetir a ciegas.
- No usar `close_document(close_all=true)` salvo que sea seguro descartar todos los documentos sin guardar de la sesión.

## Unidades: distinguir cada frontera

| Frontera | Longitudes | Ángulos |
|---|---:|---:|
| Herramientas MCP de bajo nivel | metros | grados |
| `modify_dimension` | metros | radianes para cotas angulares |
| Feature Graph IR | metros | radianes, salvo campos explícitos como `angle_deg` |
| `analyze_model` / `analyze_assembly` | SI; metros y radianes donde corresponda | según contrato del campo |
| Payload completo de `analyze_drawing` | milímetros reales ya escalados | grados; no aplicar escala a ángulos |

Reglas:

- Convertir milímetros a metros exactamente una vez antes de autorar herramientas o IR: `mm / 1000`.
- Redondear IR a la precisión que ordene la receta vigente; no redondear antes los cálculos de comprobación.
- Nunca enviar grados en un campo IR que exige radianes. Ejemplo: `90° = 1.57079632679 rad`.
- En `circular_pattern`, `angle_deg` permanece en grados porque el propio campo lo declara.
- No suponer que todas las APIs usan la misma unidad sólo porque SolidWorks internamente usa SI.

## Arrays y strings JSON

En el límite MCP, respetar la firma exacta:

- Los parámetros declarados como strings JSON se envían serializados, por ejemplo `points: "[x1,y1,x2,y2]"`, `segments: "[{...}]"`, `near: "[x,y,z]"`, `axis: "[x,y,z]"`, `edge_indices: "[3,5]"`, `edges_json`, `profiles`, `features_json`, `formats_json` y `transform_json`.
- `submit_feature_graph.graph` es un string que contiene el objeto JSON completo.
- Dentro de ese objeto Feature Graph, `nodes`, `profile`, `points`, `transform`, `sides` y demás colecciones son arrays JSON nativos. No convertir cada array interno en otro string.
- Validar localmente sintaxis, cantidad de elementos, números finitos, ids únicos y referencias hacia nodos anteriores antes de enviar.

## Elegir la ruta correcta

### Creación desde intención

Ruta principal: `submit_feature_graph` con el grafo completo y `fresh_document=true`.

- Construir el mayor grafo coherente posible y enviarlo una vez.
- Usar herramientas de bajo nivel sólo para recuperación de un nodo, una edición genuinamente puntual o una feature fuera del vocabulario IR.
- No hand-build feature por feature cuando el esquema puede representarlo.
- No improvisar un sustituto parecido para una feature ausente del esquema. Registrar `VOCABULARY_GAP` y explicar la diferencia funcional.

### Reproducción de una pieza o assembly existente

1. `save_analysis` sobre el archivo fuente.
2. Generar IR en orden de árbol según las recetas vigentes, sin omisiones.
3. `rebuild_from_ir(..., fresh_document=true)`.
4. `compare_parts` o `compare_assemblies` contra el original.
5. Sólo tratar como reproducible un resultado cuyo veredicto objetivo sea `PASS`/`verified` según el contrato vigente.

### Edición de un documento existente

1. `open_document` o `activate_document`.
2. `analyze_model(analysis_type='features')` o `analyze_assembly` según el documento.
3. Usar `modify_dimension` para cambios paramétricos; comprobar el valor efectivo devuelto.
4. Usar `edit_feature` para suppress, unsuppress, delete o rename.
5. Después de cualquier cambio topológico, volver a leer features y referencias; los índices y anchors previos quedan invalidados.

### DXF/DWG a pieza

1. Leer `recipe://usage/reverse`.
2. Ejecutar `analyze_drawing(mode='auto')`.
3. Si responde `DIRECT_BUILDABLE`, revisar resumen, SHA, espesor, blank, bends, volumen esperado y `SKIPPED`; después usar `mode='build'`.
4. Si responde `NOT_DIRECT`, aceptar el veredicto, leer el análisis completo y construir mediante `submit_feature_graph`. No cerrar contornos abiertos ni resolver signos por plausibilidad.
5. Consumir cada dimensión y primitiva en una feature nombrada, clasificarla como duplicado/silueta o registrar un gap.
6. Verificar masa/volumen, coordenadas de features definidas desde vistas secundarias y sentido de cada bend. Volumen, área y topología no detectan espejados ni bends omitidos.

### Modelo a dibujo

1. Guardar primero la pieza o assembly fuente.
2. `create_drawing` y añadir las vistas necesarias con `add_drawing_view`.
3. Para chapa, usar `add_flat_pattern_view`; no sustituirla por una vista plegada cuando se necesita fabricación.
4. Preferir `auto_dimension_drawing` y `auto_center_marks` sobre selecciones por coordenadas.
5. Usar `add_section_view` para profundidades o features internas, y `add_hole_callout`/`add_drawing_dimension` sólo donde aporten información no cubierta.
6. Verificar el `.SLDDRW` generado con `analyze_slddrw_test`: vistas no vacías, cotas esperadas, valores y secciones.
7. Guardar y exportar mediante `export_document` o `batch_export`.

## Contrato previo de pieza

Antes de modelar una pieza, producir internamente una tabla de intención:

- datum y sistema de ejes;
- dimensiones fuente convertidas a SI;
- material y densidad cuando se conozcan;
- orden de features;
- dirección positiva/negativa de cada boss, cut, bend y patrón;
- condición final de extrusión;
- referencias topológicas requeridas en el estado exacto donde se resolverán;
- cuerpo, volumen, área, centro de masa, límites y conteos topológicos esperados cuando puedan calcularse.

Para cada corte comprobar que intersecta material. Para cada boss comprobar que crea o une el cuerpo previsto. Preferir `through_all`, `up_to_surface` o `mid_plane` cuando expresen la intención mejor que una profundidad adivinada.

## Feature Graph: invariantes no negociables

- `graph.nodes` debe ser no vacío.
- IDs deterministas `n1..nN`, únicos y en orden de construcción.
- No mezclar vocabulario de pieza y assembly en un mismo grafo.
- Los nodos que consumen el sketch activo deben seguir inmediatamente a su sketch según el esquema vigente.
- Loft profiles, sweep path, seeds de patterns y features de mirror sólo referencian nodos anteriores válidos.
- Los perfiles cerrados cierran por endpoints numéricamente idénticos y ordenados. No agregar constraints redundantes a geometría congelada.
- Los anchors se calculan para la geometría existente justo antes del nodo consumidor, no para la pieza terminada.
- Para fillets/chamfers de reproducción, usar `feature_map` o geometría pre-feature; la arista consumida ya no existe en el sólido final.
- Los puntos `near` deben ser interiores o midpoints inequívocos, nunca intersecciones compartidas por varias caras/aristas.
- La dirección de extrusión se deriva de la normal del datum. Front→`+Z`, Top→`+Y`, Right→`+X`; una base flange tiene una convención de espesor distinta. Verificar el signo con readback, no por intuición.
- Los patterns lineales del IR son de una dirección. Formar una grilla como pattern de otro pattern cuando el esquema vigente mantenga esa restricción.
- Sólo declarar material si el nombre exacto existe en la biblioteca indicada.

## Selección topológica robusta

- Antes de crear un sketch sobre cara, consultar `analyze_model('faces')` y usar `face_index`.
- Antes de fillet/chamfer, consultar `analyze_model('edges')` o `feature_map` y usar `edge_indices`.
- Preferir lecturas dirigidas con `near`, `k` y `axis` cuando se conoce la zona aproximada.
- Después de cualquier cambio topológico, descartar todos los índices previos y volver a analizar.
- Para una selección indicada por el usuario en la GUI, llamar `get_selection` antes de cualquier herramienta que limpie la selección.
- En assemblies, obtener índices mediante `analyze_assembly('faces'|'edges', component=...)`; nunca usar coordenadas de pantalla ni asumir que dos instancias comparten índices después de cambiar su geometría.

## Checkpoints para herramientas de bajo nivel

- Tras abrir o crear: `verify_state`; comprobar documento y tipo correctos.
- Tras crear/editar sketch: comprobar `ActiveSketch`. Para perfiles complejos, `analyze_model('sketch', name=...)` antes de consumirlos.
- Tras boss, cut, revolve, sweep, loft o rib: exigir `COMPLETED`, revisar `result_geometry` y comprobar el árbol con `verify_state` o `analyze_model('features')`.
- Tras pattern: comprobar feature creada, conteo de instancias efectivo y `result_geometry`; detectar wraps/duplicados.
- Tras fillet/chamfer: analizar primero edges válidos y después confirmar feature y topología.
- Tras base flange, edge flange o sketched bend: confirmar feature, caras de referencia, espesor y sentido plegado. Un volumen correcto no demuestra que el bend exista ni que su signo sea correcto.
- Tras `modify_dimension` o `edit_feature`: comprobar valor efectivo, rebuild y árbol; volver a adquirir topología.
- Tras cada mate de bajo nivel: revisar los transforms devueltos de ambos componentes antes de agregar el siguiente. No continuar si el mate mueve un componente fuera de la pose prevista.

## Assemblies: contrato mecánico antes de CAD

Un mate no es una herramienta para arrastrar una pieza a una pose conveniente. El `transform` define la pose inicial/final prevista; el mate expresa una restricción física del mecanismo.

Antes de crear el grafo, cerrar dos tablas internas.

### Inventario de componentes

Por cada ocurrencia:

- id de nodo;
- ruta absoluta y hash de la fuente cuando esté disponible;
- configuración;
- función mecánica;
- `fixed` explícito;
- transform de 13 números: matriz 3×3 row-major, traslación en metros y escala;
- masa/volumen/bounds esperados;
- interfaces y componentes con los que realmente se relaciona.

Validaciones previas:

- Abrir secuencialmente cada archivo físico y comprobar que es legible, tiene cuerpos sólidos y volumen positivo, salvo excepción explícita del encargo.
- Guardar todas las piezas nuevas antes de referenciarlas.
- No insertar placeholders, documentos vacíos ni rutas dudosas.
- Fijar normalmente una única referencia estructural. Más componentes fijos sólo son válidos si el diseño exige placements rígidos independientes; nunca fijar todo para ocultar mates ausentes.
- Una ocurrencia suprimida o una jerarquía que el esquema no pueda representar es un gap, no un componente silenciosamente descartado.
- El grafo de conectividad debe incluir toda ocurrencia no fija. Un componente aislado sólo es válido si el encargo lo define explícitamente como cuerpo libre.

### Plan de mates y grados de libertad

Por cada mate:

- intención de la unión: apoyo, eje, guía, contacto, separación, orientación o bloqueo;
- componentes A/B distintos;
- superficie o arista física en cada lado;
- anchor component-local, kind, direction/radius si corresponde;
- tipo, alignment, flip y valor;
- grados de libertad eliminados;
- grados de libertad que deben permanecer;
- comprobación posterior esperada.

Antes de materializar cada anchor, leer la geometría de la ocurrencia con `analyze_assembly('faces'|'edges', component=...)` o derivarla de una pieza ya verificada. Registrar point/normal/axis/radius/índice que demuestra que la entidad es la interfaz prevista. El nombre o cercanía visual no bastan.

Reglas de coherencia:

- `coincident`/`distance` entre planos representa apoyo o separación; `parallel`/`perpendicular` sólo orientación.
- `concentric` requiere cilindros/círculos coaxiales geométricamente compatibles; no demuestra contacto axial.
- `tangent` exige superficies que realmente deban tocarse.
- `angle` exige una relación angular funcional y un valor explícito.
- `lock` sólo se usa cuando la intención es rigidizar por completo esa relación. Nunca como comodín para salvar selección o cinemática mal definidas.
- Usar `closest` únicamente si ambas soluciones son físicamente equivalentes. Si el signo importa, elegir `aligned` o `anti_aligned` a partir de normals/axes y pose objetivo.
- Nunca agregar un mate duplicado, contradictorio o que no reduzca un grado de libertad previsto.
- No añadir mates sólo para aumentar el conteo. Un conjunto sin mates puede ser correcto para una referencia importada con todos los componentes deliberadamente fijos; un mecanismo con componentes flotantes no puede aceptarse así.
- En un apoyo plano, comprobar normals y pose: las piezas deben quedar en los lados físicos previstos de la interfaz, no coplanares pero solapadas.
- En un ajuste concéntrico, comprobar axis, radio/diámetro y holgura o interferencia prevista; compartir eje por azar no constituye una unión válida.
- Toda ocurrencia flotante debe quedar conectada al mecanismo por una cadena de mates con intención, salvo que se haya especificado como cuerpo libre.

Patrones mecánicos típicos:

- Articulación revoluta: concentricidad del eje más apoyo/separación axial; conservar una rotación. No agregar lock ni clocking si debe girar.
- Unión coaxial rígida: concentricidad, posición axial y una referencia de clocking sólo si la orientación alrededor del eje importa.
- Junta prismática: restringir orientación y desplazamientos transversales; conservar la traslación del eje. No fijar su posición axial sin requisito.
- Apoyo plano: coincident o distance para la normal; añadir orientación lateral sólo si el diseño la exige.
- Componente atornillado: alinear ejes y caras de asiento; bloquear clocking sólo cuando la interfaz o patrón de agujeros lo determine.

Antes de enviar, hacer un balance analítico de grados de libertad por componente. Una assembly subrestringida puede ser correcta si es un mecanismo; registrarlo. Una assembly sobre-restringida, contradictoria o rígida por accidente no es aceptable.

## Construcción y compuerta final de assembly

1. Leer `recipe://usage/forward`, `recipe://usage/mapping_assembly` y `schema://feature-graph`.
2. Confirmar inventario y plan de mates.
3. Crear un Feature Graph que contenga sólo nodos `component` y `mate`: todos los componentes primero, todos los mates después. Cada side de mate referencia un componente anterior.
4. Enviar el grafo completo con `submit_feature_graph(..., fresh_document=true)`.
5. Exigir `COMPLETED N/N`; cualquier nodo fallido invalida el documento completo.
6. Ejecutar una sola lectura estructural final con `analyze_assembly('components')` y `analyze_assembly('mates')`, según la disciplina de la receta. Usar `components_flat` sólo para inspeccionar hojas de jerarquías existentes y declarar la pérdida de jerarquía si se aplana.
7. Ejecutar `verify_state` y `analyze_model('mass_properties')` sobre el assembly.
8. Comprobar objetivamente:
   - `component_count` igual al inventario y mayor que cero;
   - cada ocurrencia con source/config correctos, path no vacío, transform presente y estado fixed/floating previsto;
   - ningún componente inesperadamente suppressed;
   - `mate_count`, multiconjunto de tipos, valores y alignments iguales al plan;
   - cada mate con exactamente dos entidades y los propietarios previstos;
   - transforms finales dentro de la tolerancia del diseño; para reproducción, posición ≤ 1 µm y rotación ≤ `1e-6`;
   - volumen/área/masa coherentes con las propiedades verificadas de las piezas y el inventario; no inferir ausencia de interferencias a partir de estas magnitudes;
   - interfaces de asiento, ejes y distancias coincidentes con la geometría verificada de cada componente;
   - grafo de conectividad sin ocurrencias aisladas no justificadas;
   - grados de libertad conservados/eliminados según el plan.
9. Si existe assembly de referencia, ejecutar `compare_assemblies`. Sólo aceptar `verified_criteria=PASS`: set exacto de componentes, transforms, cantidad/tipos de mates y propiedades de masa dentro del contrato.
10. Si no existe referencia, declarar “verificado contra la especificación”, no “idéntico” ni “interference-free”.
11. Guardar con `save_document`, comprobar la ruta y repetir `verify_state` más las lecturas de components/mates si el guardado o una reactivación cambió el documento activo.
12. Cuando el cliente permita acceso al sistema de archivos, confirmar que el `.SLDASM` existe en la ruta final y tiene tamaño no nulo. Esto complementa, pero nunca reemplaza, las comprobaciones internas de componentes y mates.

Rechazar la entrega si el assembly quedó vacío, falta una sola ocurrencia, un mate carece de intención física, una selección resolvió otra cara/arista, un transform se desplazó sin explicación o el árbol presenta errores.

## Verificación final de piezas

### Con referencia

- `compare_parts` debe confirmar topología exacta y tolerancias de volumen/área de la receta vigente.
- Comparar además posición de features cuando un espejo podría conservar topología, volumen y área.

### Sin referencia

- Calcular antes de construir el volumen y centro de masa esperados siempre que la geometría lo permita.
- Leer `analyze_model('geometry')`, `analyze_model('mass_properties')` y `analyze_model('features')`.
- Verificar cuerpos, caras, aristas, vértices, volumen, área, centro de masa y feature order contra la intención.
- Para features asimétricas, agujeros, pockets, bends y flanges, leer faces/edges objetivo y comprobar sus coordenadas/signos.
- Una coincidencia parcial no autoriza a omitir diferencias.

## Cobertura completa de herramientas

Elegir por intención, no por familiaridad:

- Ciclo de documento: `ensure_ready`, `open_new_part`, `open_new_assembly`, `open_document`, `activate_document`, `save_document`, `close_document`.
- Sketch: `create_sketch`, `edit_sketch`, `add_sketch_entity`, `add_sketch_entities`, `add_sketch_constraint`, `add_dimension`.
- Sólidos y chapa: `extrude_feature`, `create_rib`, `add_edge_feature`, `add_reference_geometry`, `create_pattern`, `sheet_metal_feature`.
- Edición/material: `modify_dimension`, `edit_feature`, `set_part_material`.
- Análisis/selección: `verify_state`, `analyze_model`, `get_selection`, `analyze_assembly`.
- Assembly: `insert_component`, `add_mate`, `save_body_as_part`, `compare_assemblies`.
- Pipeline e IR: `save_analysis`, `rebuild_from_ir`, `submit_feature_graph`, `compare_parts`.
- Dibujo: `create_drawing`, `add_drawing_view`, `add_flat_pattern_view`, `auto_dimension_drawing`, `auto_center_marks`, `add_hole_callout`, `add_drawing_dimension`, `add_section_view`, `analyze_drawing`, `analyze_slddrw_test`.
- Exportación: `export_document`, `batch_export`.

Usar `save_body_as_part` sólo para extraer cuerpos distintos de una pieza multibody importada; deduplicar por fingerprint y reconstruir transforms. No fingir que una importación STEP aplanada preserva estructura, jerarquía o mates.

## Manejo de fallos

- `REFERENCE_UNRESOLVED` o `REFERENCE_AMBIGUOUS`: volver a analizar la geometría en el estado correcto y corregir el anchor una vez. No ampliar tolerancias ni iterar puntos al azar.
- `EXTRUSION_FAILED` o corte que no elimina material: revisar la normal y cambiar el signo una vez cuando la evidencia indique dirección inversa.
- `ENTITY_NOT_FOUND`: volver a adquirir índices; cambiaron con la topología.
- `ADD_MATE_FAILED`: revisar compatibilidad geométrica, kind, índices, alignment y grados de libertad. No reemplazar por `lock`.
- `INVALID_STATE_VERSION`: permitir el resync del adaptador y continuar desde el estado leído.
- Fallo parcial de `add_sketch_entities`: los segmentos anteriores permanecen. Descartar/recrear el sketch o documento; no duplicarlos al reenviar el lote completo.
- `source_stale`: recalcular el análisis/hash; nunca reconstruir desde un artefacto obsoleto.
- Gap de vocabulario o resolver: informarlo con tipo/referencia exactos y detener la construcción dependiente.

## Informe de entrega

Reportar de forma compacta pero auditable:

- archivos creados/actualizados y rutas;
- versión de receta/esquema usada;
- features principales y material;
- verificaciones numéricas ejecutadas y sus resultados;
- para assemblies: componentes esperados/reales, fixed/floating, mates esperados/reales por tipo, intención y DOF de cada unión, máximo error de transform y resultado de `compare_assemblies` si aplica;
- para dibujos: vistas, secciones, cotas/center marks y formatos exportados;
- gaps, skips, ambigüedades y capacidades no verificadas.

Nunca ocultar un fallo tras frases como “archivo generado”, “assembly creado” o “visualmente correcto”. El entregable es el modelo validado, no la existencia del archivo.
