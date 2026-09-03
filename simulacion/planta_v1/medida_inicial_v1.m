function meas0 = medida_inicial_v1(X0, alpha0, pv)
%MEDIDA_INICIAL_V1  Medida "en reposo" para inicializar el filtro y la cola del retardo.
%   Es lo que leeria la IMU con el robot quieto en la pose X0 sobre un piso de pendiente alpha0:
%   solo gravedad (sin las aceleraciones del primer instante, que no representan nada fisico).
  g = pv(6); phi0 = X0(2);
  y0 = zeros(16,1);
  y0(15) = g*sin(alpha0 - phi0);      % fb_x
  y0(16) = g*cos(alpha0 - phi0);      % fb_y
  meas0 = sensores_sl(X0, y0, zeros(3,1), pv);
end
