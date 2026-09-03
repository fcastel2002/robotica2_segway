function medidas0 = medida_inicial(X0, alpha0, par)
%MEDIDA_INICIAL  Medida "en reposo" para inicializar el filtro y la cola del retardo: solo gravedad.
  g = par.g; phi0 = X0(3);
  y0 = zeros(18,1);
  y0(16) = g*sin(alpha0 - phi0);      % acel_x
  y0(17) = g*cos(alpha0 - phi0);      % acel_y
  medidas0 = robot_sensores(X0, y0, zeros(3,1), par);
end
