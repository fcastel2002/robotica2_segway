function mostrar_parametros(P)
%MOSTRAR_PARAMETROS  Imprime lo que quedo en P en unidades de ingenieria (mm, g, kg cm, grados).
%   Sirve para verificar despues de cambiar algo en parametros_editables.m.
  mm = 1e3; r2d = 180/pi; o = P.opciones;
  fprintf('\n================ ROBOT: variante %s ================\n', P.variante);
  fprintf('Motor: %s\n', P.motor.nombre);
  fprintf('\n--- Geometria del cuatro barras [mm] ---\n');
  fprintf('  AB (bancada) %.1f a %.1f deg | AD %.1f | BC %.1f | CD %.1f | DP %.1f | delta %.0f deg | servo %.0f..%.0f deg\n', ...
      P.AB*mm, P.ang_AB*r2d, P.AD*mm, P.BC*mm, P.CD*mm, P.DP*mm, P.delta*r2d, P.th(1)*r2d, P.th(2)*r2d);
  K = P.cinematica; v = K.valido;
  fprintf('  carrera del eje de rueda %.1f mm | desvio horizontal %.1f mm | angulo de transmision %.0f..%.0f deg\n', ...
      (max(K.P(v,2))-min(K.P(v,2)))*mm, (max(K.P(v,1))-min(K.P(v,1)))*mm, K.mu_min*r2d, K.mu_max*r2d);
  fprintf('  rueda R = %.0f mm | altura del tope de la tapa de pie / agachado: %.0f / %.0f mm\n', P.Rw*mm, ...
      (P.Rw - min(K.P(v,2)) + P.din.h_tapa_sobre_A)*mm, (P.Rw - max(K.P(v,2)) + P.din.h_tapa_sobre_A)*mm);
  fprintf('\n--- Masas [g] ---\n');
  fprintf('  cabina %.0f | tapa %.0f | servos 2 x %.0f | bateria %.0f | electronica %.0f | tornilleria %.0f | carga %.0f\n', ...
      o.m_cabina, o.m_tapa, o.m_servo, o.m_bateria, o.m_electronica, o.m_tornilleria, o.m_carga);
  fprintf('  barras por pata: AD %.1f | BC %.1f | CDP %.1f   (x2 patas) | ruedas 2 x %.0f | motores 2 x %.0f\n', o.m_AD, o.m_BC, o.m_CDP, o.m_rueda, o.m_motor);
  fprintf('  => cuerpo suspendido m_b = %.0f g | en el eje m_w = %.0f g | total %.0f g\n', P.din.m_b*1e3, P.din.m_w*1e3, P.m.total*1e3);
  fprintf('  => CoM del cuerpo respecto de A: %.1f mm atras, %.1f mm arriba | J_b = %.2e kg m2 (%s)\n', ...
      P.din.r_com(1)*mm, P.din.r_com(2)*mm, P.din.J_b, ternario(isempty(o.J_cuerpo), 'calculada de las piezas', 'IMPUESTA'));
  fprintf('  => largo de pendulo l = %.0f..%.0f mm | ganancia G = |dl/dtheta| = %.0f mm/rad\n', P.din.l_min*mm, P.din.l_max*mm, P.din.G*mm);
  fprintf('  => par de servo para sostener el cuerpo: %.2f N m = %.1f kg cm por servo (maximo %.1f)\n', ...
      P.din.m_b*P.g*P.din.G/P.servo.n, P.din.m_b*P.g*P.din.G/P.servo.n*10.197, P.servo.tau_max*10.197);
  fprintf('\n--- Rueda, contacto y piso ---\n');
  fprintf('  J_w = %.2e kg m2 (%s) | mu = %.2f | neumatico k = %.0f N/m, c = %.0f N s/m (hundimiento estatico %.2f mm)\n', ...
      P.din.J_w, ternario(isempty(o.J_rueda), 'disco', 'IMPUESTA'), P.rueda.mu, P.contacto.k, P.contacto.c, P.m.total*P.g/(2*P.contacto.k)*mm);
  fprintf('  limite de adherencia por rueda: %.3f N m = %.2f kg cm | escalones: %d de %.0f x %.0f cm desde x = %.2f m\n', ...
      P.rueda.mu*P.m.total*P.g/2*P.Rw, P.rueda.mu*P.m.total*P.g/2*P.Rw*10.197, P.piso.n, P.piso.alto*100, P.piso.ancho*100, P.piso.x0);
  fprintf('\n--- Motor + reductor ---\n');
  J_ref = P.motor.N^2*P.motor.J_r;
  fprintf('  R = %.2f ohm | L = %.1f mH | Ke = Kt = %.4f V s/rad | 1:%.1f | vacio en la rueda %.0f rpm = %.2f m/s\n', ...
      P.motor.R, P.motor.L*1e3, P.motor.Ke, P.motor.N, P.motor.w_nl_out*60/(2*pi), P.motor.w_nl_out*P.Rw);
  fprintf('  par de bloqueo en la rueda %.2f N m = %.1f kg cm | rotor reflejado N^2 J_r = %.2e kg m2 = %.1f kg aparentes en la base\n', ...
      P.motor.N*P.motor.Kt*P.bat.V/P.motor.R, P.motor.N*P.motor.Kt*P.bat.V/P.motor.R*10.197, J_ref, 2*(P.din.J_w + J_ref)/P.Rw^2);
  fprintf('  reductor %s | juego %.1f deg | bateria %.1f V, %.2f ohm\n', ternario(P.motor.gear_rigido, 'rigido', 'elastico con juego'), P.motor.juego*r2d, P.bat.V, P.bat.R);
  fprintf('\n--- Servo y flexor ---\n');
  fprintf('  servo: %.1f kg cm, %.1f rad/s en vacio, Kp %.0f N m/rad, Kd %.1f | flexor %s (k %.0f N/m, carrera %.0f mm)\n', ...
      P.servo.tau_max*10.197, P.servo.w_nl, P.servo.Kp, P.servo.Kd, ternario(P.flexor.activo, 'ACTIVO', 'apagado'), P.flexor.k, P.flexor.carrera*mm);
  fprintf('\n--- Sensores y control ---\n');
  fprintf('  Ts = %.0f ms | retardo %d muestras | encoder %s (%.0f cuentas/vuelta de rueda) | IMU a (%.1f, %.1f) mm de A | gyro sesgo %.1f deg/s\n', ...
      P.sens.Ts*1e3, P.sens.n_delay, ternario(P.sens.encoder, 'si', 'NO'), P.sens.CPR, o.d_imu(1), o.d_imu(2), o.gyro_bias_dps);
  fprintf('\n');
end
function y = ternario(c, a, b)
  if c, y = a; else, y = b; end
end
