function meas = sensores_sl(X, y, ruido, pv)
%SENSORES_SL  Medidas crudas: [gyro; fb_x; fb_y; enc_L; enc_R]. ruido = 3 gaussianas unitarias.
%   Giroscopo con sesgo, ruido y saturacion; acelerometro (fuerza especifica en la IMU) con ruido;
%   encoders en cuentas enteras (NaN si la variante no tiene encoder).
%#codegen
  encoder = pv(41) > 0.5; CPR = pv(42); gyro_bias = pv(43); gyro_sat = pv(44); gyro_rms = pv(45); acc_rms = pv(46);
  gyro = X(5) + gyro_bias + gyro_rms*ruido(1);
  gyro = max(min(gyro, gyro_sat), -gyro_sat);
  fbx = y(15) + acc_rms*ruido(2);
  fby = y(16) + acc_rms*ruido(3);
  if encoder
    encL = floor(X(7)*CPR/(2*pi)); encR = floor(X(9)*CPR/(2*pi));
  else
    encL = NaN; encR = NaN;
  end
  meas = [gyro; fbx; fby; encL; encR];
end
