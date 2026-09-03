function medidas = robot_sensores(X, y, ruido, par)
%ROBOT_SENSORES  Medidas crudas: [giroscopo; acel_x; acel_y; encoder_izq; encoder_der].
%   Giroscopo: velocidad de cabeceo con sesgo, ruido y saturacion. Acelerometro: fuerza especifica
%   en la IMU (marco cuerpo) con ruido. Encoders: cuentas enteras (NaN si no hay encoder).
%   ruido = 3 gaussianas unitarias.
%#codegen
  se = par.sensores;
  giroscopo = X(7) + se.gyro_sesgo + se.gyro_ruido*ruido(1);
  giroscopo = max(min(giroscopo, se.gyro_sat), -se.gyro_sat);
  acel_x = y(16) + se.acel_ruido*ruido(2);
  acel_y = y(17) + se.acel_ruido*ruido(3);
  if se.encoder > 0.5
    encoder_izq = floor(X(9)*se.CPR/(2*pi)); encoder_der = floor(X(11)*se.CPR/(2*pi));
  else
    encoder_izq = NaN; encoder_der = NaN;
  end
  medidas = [giroscopo; acel_x; acel_y; encoder_izq; encoder_der];
end
