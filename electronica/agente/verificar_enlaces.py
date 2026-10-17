"""Verifica los enlaces relativos de la documentación de electrónica.

Uso, desde la raíz del repositorio:
    python -I -X utf8 electronica/agente/verificar_enlaces.py [--json salida.json]

Revisa los .md de electronica/ (incluidas carpetas ocultas como .claude/),
BACKLOG.md, AGENTS.md y .claude/skills/ de la raíz. Ignora enlaces web,
anclas internas y bloques de código. Sale con código 1 si hay enlaces rotos.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

RAIZ = Path(__file__).resolve().parents[2]
ENLACE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODIGO = re.compile(r"```.*?```", re.S)


def archivos():
    yield from sorted((RAIZ / "electronica").rglob("*.md"))
    for nombre in ("BACKLOG.md", "AGENTS.md"):
        if (RAIZ / nombre).exists():
            yield RAIZ / nombre
    skills = RAIZ / ".claude" / "skills"
    if skills.exists():
        yield from sorted(skills.rglob("*.md"))


def revisar(md):
    texto = CODIGO.sub("", md.read_text(encoding="utf-8"))
    for numero, linea in enumerate(texto.splitlines(), 1):
        linea = re.sub(r"`[^`]*`", "", linea)
        for destino in ENLACE.findall(linea):
            if re.match(r"^[a-z]+:", destino) or destino.startswith("#"):
                continue
            ruta = unquote(destino.split("#", 1)[0])
            if not ruta:
                continue
            objetivo = (md.parent / ruta).resolve()
            yield numero, destino, objetivo.exists()


def main():
    total = 0
    rotos = []
    documentos = 0
    for md in archivos():
        documentos += 1
        for numero, destino, existe in revisar(md):
            total += 1
            if not existe:
                rotos.append({"archivo": md.relative_to(RAIZ).as_posix(), "linea": numero, "destino": destino})
    resumen = {"documentos": documentos, "enlaces_locales": total, "rotos": rotos}
    if "--json" in sys.argv:
        salida = Path(sys.argv[sys.argv.index("--json") + 1])
        salida.write_text(json.dumps(resumen, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Documentos: {documentos}. Enlaces locales: {total}. Rotos: {len(rotos)}.")
    for r in rotos:
        print(f"  {r['archivo']}:{r['linea']} -> {r['destino']}")
    return 1 if rotos else 0


if __name__ == "__main__":
    sys.exit(main())
