function bloques_sensores(mdl, u)
%BLOQUES_SENSORES  Subsistema Sensores de robot_segway_bloques: IMU y encoders con bloques nativos.
%   medidas = [giroscopo; acel_x; acel_y; encoder_izq; encoder_der], muestreadas a Ts y retardadas.
  s = [mdl '/Sensores'];
  u.in(s, 'estados'); u.in(s, 'salidas');
  u.buss(s, 'del robot', 'd_inclinacion,ang_rueda_izq,ang_rueda_der'); u.buss(s, 'de la IMU', 'imu_fx,imu_fy');
  u.L(s, 'estados/1', 'del robot/1', ''); u.L(s, 'salidas/1', 'de la IMU/1', '');
  u.zoh(s, 'muestreo del giro'); u.zoh(s, 'muestreo rueda izq'); u.zoh(s, 'muestreo rueda der'); u.zoh(s, 'muestreo f_x'); u.zoh(s, 'muestreo f_y');
  u.L(s, 'del robot/1', 'muestreo del giro/1', ''); u.L(s, 'del robot/2', 'muestreo rueda izq/1', ''); u.L(s, 'del robot/3', 'muestreo rueda der/1', '');
  u.L(s, 'de la IMU/1', 'muestreo f_x/1', ''); u.L(s, 'de la IMU/2', 'muestreo f_y/1', '');
  giroscopio(s, u); acelerometro(s, u); encoders(s, u);
  u.L(s, 'muestreo del giro/1', 'Giroscopio/1', 'vel_cabeceo');
  u.L(s, 'muestreo f_x/1', 'Acelerometro/1', 'f_x'); u.L(s, 'muestreo f_y/1', 'Acelerometro/2', 'f_y');
  u.L(s, 'muestreo rueda izq/1', 'Encoders/1', 'ang_izq'); u.L(s, 'muestreo rueda der/1', 'Encoders/2', 'ang_der');
  u.mux(s, 'medidas (5)', '5');
  u.L(s, 'Giroscopio/1', 'medidas (5)/1', 'giroscopo'); u.L(s, 'Acelerometro/1', 'medidas (5)/2', 'acel_x'); u.L(s, 'Acelerometro/2', 'medidas (5)/3', 'acel_y');
  u.L(s, 'Encoders/1', 'medidas (5)/4', 'encoder_izq'); u.L(s, 'Encoders/2', 'medidas (5)/5', 'encoder_der');
  u.ab('simulink/Discrete/Delay', s, 'retardo del bus de sensores', 'DelayLength', 'retardo_muestras', 'InitialCondition', 'medidas_iniciales', 'SampleTime', 'Ts');
  u.out(s, 'medidas');
  u.L(s, 'medidas (5)/1', 'retardo del bus de sensores/1', 'medidas_sin_retardo'); u.L(s, 'retardo del bus de sensores/1', 'medidas/1', 'medidas');
end

function giroscopio(s0, u)
% giroscopo = sat(vel de cabeceo + sesgo + ruido, +-saturacion)
  s = u.sub(s0, 'Giroscopio');
  u.in(s, 'vel_cabeceo');
  u.const(s, 'sesgo', 'par.sensores.gyro_sesgo'); u.rand(s, 'ruido blanco', 'semilla'); u.gain(s, 'rms del ruido', 'par.sensores.gyro_ruido');
  u.sum(s, 'giro + sesgo + ruido', '+++'); u.sat(s, 'saturacion del giroscopo', '-par.sensores.gyro_sat', 'par.sensores.gyro_sat');
  u.L(s, 'ruido blanco/1', 'rms del ruido/1', '');
  u.L(s, 'vel_cabeceo/1', 'giro + sesgo + ruido/1', ''); u.L(s, 'sesgo/1', 'giro + sesgo + ruido/2', ''); u.L(s, 'rms del ruido/1', 'giro + sesgo + ruido/3', 'ruido');
  u.L(s, 'giro + sesgo + ruido/1', 'saturacion del giroscopo/1', '');
  u.out(s, 'giroscopo'); u.L(s, 'saturacion del giroscopo/1', 'giroscopo/1', '');
end

function acelerometro(s0, u)
% acel = fuerza especifica + ruido (por eje)
  s = u.sub(s0, 'Acelerometro');
  u.in(s, 'f_x'); u.in(s, 'f_y');
  u.rand(s, 'ruido eje x', 'semilla+1'); u.rand(s, 'ruido eje y', 'semilla+2');
  u.gain(s, 'rms del ruido x', 'par.sensores.acel_ruido'); u.gain(s, 'rms del ruido y', 'par.sensores.acel_ruido');
  u.sum(s, 'f_x + ruido', '++'); u.sum(s, 'f_y + ruido', '++');
  u.L(s, 'ruido eje x/1', 'rms del ruido x/1', ''); u.L(s, 'ruido eje y/1', 'rms del ruido y/1', '');
  u.L(s, 'f_x/1', 'f_x + ruido/1', ''); u.L(s, 'rms del ruido x/1', 'f_x + ruido/2', '');
  u.L(s, 'f_y/1', 'f_y + ruido/1', ''); u.L(s, 'rms del ruido y/1', 'f_y + ruido/2', '');
  u.out(s, 'acel_x'); u.out(s, 'acel_y'); u.L(s, 'f_x + ruido/1', 'acel_x/1', ''); u.L(s, 'f_y + ruido/1', 'acel_y/1', '');
end

function encoders(s0, u)
% cuentas = floor(angulo CPR / 2 pi) ; NaN si el robot no tiene encoder
  s = u.sub(s0, 'Encoders');
  u.in(s, 'ang_izq'); u.in(s, 'ang_der');
  u.const(s, 'encoder habilitado', 'par.sensores.encoder'); u.const(s, 'sin encoder (NaN)', 'NaN');
  for lado = {'izq', 'der'}
    d = lado{1};
    u.gain(s, ['cuentas por radian ' d], 'par.sensores.CPR/(2*pi)'); u.round(s, ['cuenta entera ' d], 'floor'); u.sw(s, ['si hay encoder ' d], 'u2 > Threshold', '0.5');
    u.L(s, ['ang_' d '/1'], ['cuentas por radian ' d '/1'], ''); u.L(s, ['cuentas por radian ' d '/1'], ['cuenta entera ' d '/1'], '');
    u.L(s, ['cuenta entera ' d '/1'], ['si hay encoder ' d '/1'], ''); u.L(s, 'encoder habilitado/1', ['si hay encoder ' d '/2'], ''); u.L(s, 'sin encoder (NaN)/1', ['si hay encoder ' d '/3'], '');
    u.out(s, ['encoder_' d]); u.L(s, ['si hay encoder ' d '/1'], ['encoder_' d '/1'], '');
  end
end
