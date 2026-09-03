function mostrar_params(P, K)
%MOSTRAR_PARAMS  Imprime la geometria y los resultados en mm / grados / kg-cm.
  if nargin < 2, K = barrido_pata(P); end
  mm = 1e3; r2d = 180/pi;
  fprintf('\n=========== GEOMETRIA  (escala s = |AB| = %.1f mm) ===========\n', P.s*mm);
  fprintf('  ejes: -x = adelante, +x = atras, suelo en y = 0.\n');
  fprintf('        A (hombro) adelante, B detras y arriba, la pata se pliega hacia atras.\n');
  fprintf('  familia de relaciones : %s\n', P.geom);
  fprintf('  %-26s %8s %10s\n', 'barra', 'k (adim)', 'largo [mm]');
  fprintf('  %-26s %8.3f %10.1f\n', 'AB  bancada (= escala)', 1.000, P.AB*mm);
  fprintf('  %-26s %8.3f %10.1f\n', 'AD  manivela (motor)',   P.k.AD, P.AD*mm);
  fprintf('  %-26s %8.3f %10.1f\n', 'BC  balancin',           P.k.BC, P.BC*mm);
  fprintf('  %-26s %8.3f %10.1f\n', 'CD  acoplador',          P.k.CD, P.CD*mm);
  fprintf('  %-26s %8.3f %10.1f\n', 'DP  pata',               P.k.DP, P.DP*mm);
  fprintf('  delta (D->C hacia D->P) : %6.1f deg   |   en el plano, entre DC y la\n', P.delta*r2d);
  fprintf('                                            prolongacion de PD : %.1f deg\n', P.delta_plano*r2d);
  fprintf('  orientacion de la bancada : %.1f deg\n', P.ang_AB*r2d);
  fprintf('  B respecto de A : (%+.1f , %+.1f) mm\n', P.B(1)*mm, P.B(2)*mm);
  fprintf('  recorrido del motor : %.0f a %.0f deg  (%.0f deg de giro)\n', ...
          P.th(1)*r2d, P.th(2)*r2d, (P.th(2)-P.th(1))*r2d);

  fprintf('\n=========== RUEDA Y CHASIS ===========\n');
  fprintf('  rueda  : diametro %.0f mm, ancho de nucleo %.0f mm\n', P.Dw*mm, P.ancho_rueda*mm);
  fprintf('  placa lateral (lleva A y B) : %.0f x %.0f mm, espesor %.0f mm\n', ...
          P.placa.largo*mm, P.placa.alto*mm, P.placa.espesor*mm);
  fprintf('     sobre  x [%+.0f  %+.0f]   y [%+.0f  %+.0f] mm respecto de A\n', ...
          P.placa.x(1)*mm, P.placa.x(2)*mm, P.placa.y(1)*mm, P.placa.y(2)*mm);
  fprintf('  cabina : %.0f (largo) x %.0f (alto) x %.0f (ancho entre placas) mm\n', ...
          P.chasis.largo*mm, P.chasis.alto*mm, P.chasis.ancho*mm);
  fprintf('     centro en (%+.1f , %+.1f) mm respecto de A\n', P.chasis.xc*mm, P.chasis.yc*mm);

  fprintf('\n=========== MASAS ===========\n');
  c = {'servos de hombro',P.m.servo; 'motores de rueda',P.m.motorw; 'ruedas',P.m.rueda; ...
       'barras',P.m.barras; 'placas laterales',P.m.placas; 'tornilleria',P.m.torn; ...
       'caja (bat + elec + estr)',P.m.caja};
  for i=1:size(c,1), fprintf('  %-26s %6.0f g\n', c{i,1}, c{i,2}*1000); end
  fprintf('  %-26s %6.0f g\n', 'TOTAL', P.m.total*1000);
  fprintf('  bateria ubicada en x = %+.0f mm  (puede ir de %+.0f a %+.0f dentro de la caja)\n', ...
          P.x_bat*mm, P.x_bat_lim(1)*mm, P.x_bat_lim(2)*mm);
  fprintf('  centro de masa a %+.1f mm del punto de contacto  ->  inclinacion permanente %.1f deg\n', ...
          P.balance.x_com*mm, P.balance.inclinacion*r2d);

  fprintf('\n=========== COMPORTAMIENTO ===========\n');
  if ~K.ok
    fprintf('  *** el mecanismo NO cierra en todo el rango del motor ***\n');
  end
  v = K.valido;
  fprintf('  altura del tope del chasis : %.0f a %.0f mm\n', min(K.h_total(v))*mm, max(K.h_total(v))*mm);
  fprintf('  carrera (agachado a de pie): %.1f mm\n', K.carrera*mm);
  fprintf('  desvio horizontal del eje  : %.2f mm  (%.2f %% de la carrera)\n', ...
          K.desvio*mm, 100*K.desvio/K.carrera);
  fprintf('  offset del eje respecto A  : %.2f mm\n', K.offset*mm);
  fprintf('  angulo de transmision      : %.0f a %.0f deg\n', K.mu_min*r2d, K.mu_max*r2d);
  fprintf('  ganancia dz/dtheta         : %.1f mm/rad\n', K.dzdth*mm);
  fprintf('  PAR EN EL HOMBRO           : %.2f N.m = %.1f kg.cm   (por pata, estatico)\n', ...
          K.tau_hombro, K.tau_hombro*10.1972);
  fprintf('  par por rueda (traccion)   : %.2f N.m = %.1f kg.cm\n', ...
          K.tau_rueda, K.tau_rueda*10.1972);
  fprintf('\n');
end
