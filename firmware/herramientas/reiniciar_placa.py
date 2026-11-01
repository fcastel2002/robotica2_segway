"""Reinicia la ESP32 por la línea EN (RTS del CH343), como hace esptool al terminar de grabar.

Sale de FAULT, pero los servos se sueltan hasta el próximo "servo": colgar o agarrar el robot antes.
    python reiniciar_placa.py COM7
"""
import sys, time, serial
s = serial.Serial()
s.port, s.baudrate = sys.argv[1], 115200
s.dtr = False
s.rts = False
s.open()
s.rts = True       # EN a 0
time.sleep(0.2)
s.rts = False      # EN a 1: arranca
time.sleep(0.1)
s.close()
print('reiniciada')
