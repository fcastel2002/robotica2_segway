# Checklist de cierre de sesión

Ejecutar en este orden al terminar una tarea, antes de una pausa larga o antes de compactar el contexto.

1. **Backlog** (`BACKLOG.md` en la raíz): estado, fecha y evidencia enlazada de cada fila tocada. No marcar `HECHO` sin un archivo, resultado o decisión que lo verifique.
2. **Estado actual** (`agente/memoria/estado_actual.md`): fecha de corte, hechos nuevos, próximo paso ejecutable y obstáculos reales.
3. **Decisiones** (`agente/memoria/decisiones.md`): solo si Matías decidió algo o una decisión cambió. Registrar origen, fecha y qué reemplaza. No borrar la anterior.
4. **Cronología** (`agente/memoria/cronologia.md`): una fila por sesión con el formato de [plantillas](plantillas.md).
5. **Datos faltantes**: agregar las preguntas nuevas y tachar las respondidas.
6. **Enlaces**: correr `python -I -X utf8 electronica/agente/verificar_enlaces.py` desde la raíz y corregir los enlaces rotos que introdujo la sesión.
7. **Git**: `git status` limpio de archivos generados que no corresponden. Commit solo si Matías lo pidió.

## Memoria documental y memoria automática

La memoria canónica de electrónica es documental: los archivos de `agente/memoria/` y el backlog, versionados en git y compartidos con el equipo. La memoria automática de Claude Code vive fuera del repositorio, en `~/.claude/projects/<repo>/memory/`, y es local a esta computadora. Solo puede guardar preferencias de trabajo de Matías y punteros a los documentos. Una decisión de diseño, un dato técnico o un estado de tarea guardado solo allí se considera perdido.
