"""Lee la placa por el puerto serie sin reiniciarla (DTR y RTS en reposo): telemetría unos segundos y "get" e "ina".
Solo lectura: no manda arm, motor ni servo."""
import sys, time, serial

puerto = sys.argv[1] if len(sys.argv) > 1 else 'COM5'
segundos = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
salida = sys.argv[3] if len(sys.argv) > 3 else None

s = serial.Serial()
s.port = puerto
s.baudrate = 115200
s.timeout = 0.1
s.dtr = False
s.rts = False
s.open()

lineas = []
def leer(t):
    fin = time.time() + t
    buf = b''
    while time.time() < fin:
        buf += s.read(4096)
        while b'\n' in buf:
            l, buf = buf.split(b'\n', 1)
            lineas.append((time.time(), l.decode('utf-8', 'replace').rstrip('\r')))

leer(segundos)
s.write(b'get\n'); s.flush()
leer(1.5)
s.write(b'ina\n'); s.flush()
leer(1.0)
s.close()

if salida:
    with open(salida, 'w', encoding='utf-8') as f:
        for t, l in lineas:
            f.write('%.3f|%s\n' % (t, l))
for t, l in lineas:
    if l.startswith('#'):
        print(l)
datos = [l for _, l in lineas if l and l[0].isdigit()]
print('--- %d lineas de telemetria' % len(datos))
for l in datos[:3] + datos[-3:]:
    print(l[:200])
