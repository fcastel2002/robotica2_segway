function [ok, R] = verificar_geometria(P, verbose)
%VERIFICAR_GEOMETRIA  Corre la lista de chequeos y devuelve PASA / NO PASA.
  if nargin < 2, verbose = true; end
  mm = 1e3; r2d = 180/pi;
  K = barrido_pata(P, 601);
  R = {}; ok = true;

  function add(nombre, cond, txt)
    R(end+1,:) = {nombre, cond, txt};
    if ~cond, ok = false; end
  end

  add('cierra el mecanismo', K.ok, ...
      sprintf('%d de %d poses validas', sum(K.valido), numel(K.valido)));
  if ~K.ok
    if verbose, imprimir(R); end
    return;
  end

  add('angulo de transmision >= 40 deg', K.mu_min*r2d >= 40, ...
      sprintf('mu minimo = %.0f deg', K.mu_min*r2d));
  add('desvio de la recta <= 2 %%', 100*K.desvio/K.carrera <= 2, ...
      sprintf('%.2f mm sobre %.0f mm de carrera = %.2f %%', ...
      K.desvio*mm, K.carrera*mm, 100*K.desvio/K.carrera));
  add('eje de rueda sobre el hombro', K.offset*mm <= 5, ...
      sprintf('offset = %.2f mm', K.offset*mm));

  h = K.h_total(K.valido);
  add('altura entre 200 y 300 mm de pie', max(h)*mm >= 200 && max(h)*mm <= 300, ...
      sprintf('%.0f a %.0f mm', min(h)*mm, max(h)*mm));

  % B tiene que quedar DETRAS de A
  add('B queda detras de A', P.B(1) > 0, ...
      sprintf('B en (%+.0f , %+.0f) mm respecto de A', P.B(1)*mm, P.B(2)*mm));

  % la PLACA LATERAL lleva los dos pivotes fijos
  add('la placa lateral aloja A y B', P.placa.largo > 0 && P.placa.alto > 0, ...
      sprintf('placa de %.0f x %.0f mm, espesor %.0f mm', ...
      P.placa.largo*mm, P.placa.alto*mm, P.placa.espesor*mm));

  % ¿entra B dentro de la cabina, con A en el medio?
  bx0 = P.chasis.xc - P.chasis.largo/2; bx1 = P.chasis.xc + P.chasis.largo/2;
  by0 = P.chasis.yc - P.chasis.alto/2;  by1 = P.chasis.yc + P.chasis.alto/2;
  m0 = P.placa.margen;
  dentroB = P.B(1) <= bx1-m0 && P.B(1) >= bx0+m0 && P.B(2) <= by1-m0 && P.B(2) >= by0+m0;
  alto_nec = 2*(abs(P.B(2)-P.chasis.yc) + m0);
  add('B entra en la cabina con material', dentroB, ...
      sprintf('cabina y[%+.0f %+.0f], B_y=%+.0f -> hace falta %.0f mm de alto (hay %.0f)', ...
      by0*mm, by1*mm, P.B(2)*mm, alto_nec*mm, P.chasis.alto*mm));

  % balance
  add('centro de masa a menos de 15 mm del contacto', abs(P.balance.x_com) <= 15e-3, ...
      sprintf('CoM a %+.0f mm -> inclinacion permanente de %.1f deg', ...
      P.balance.x_com*mm, P.balance.inclinacion*r2d));

  v = find(K.valido);
  x0 = P.chasis.xc - P.chasis.largo/2; x1 = P.chasis.xc + P.chasis.largo/2;
  y0 = P.chasis.yc - P.chasis.alto/2;  y1 = P.chasis.yc + P.chasis.alto/2;

  % la cabina no debe tocar el suelo con el robot agachado
  z_min = min(K.z(K.valido));
  add('la cabina no toca el suelo agachado', z_min + y0 >= 20e-3, ...
      sprintf('fondo de cabina a %.0f mm del suelo en la pose mas baja', (z_min+y0)*mm));

  % ningun eslabon debe bajar del suelo
  hC = K.z(v) + K.C(v,2);  hD = K.z(v) + K.D(v,2);
  hmin = min([hC; hD]);
  add('los nudos C y D despegan del suelo >= 15 mm', hmin >= 15e-3, ...
      sprintf('nudo mas bajo a %.0f mm del suelo (pose mas agachada)', hmin*mm));
  % cuanta carrera queda si se exige 15 mm de despeje de los nudos
  buena = (hC >= 15e-3) & (hD >= 15e-3);
  if any(buena)
    zu = K.z(v); zu = zu(buena);
    R(end+1,:) = {'carrera util con 15 mm de despeje', true, ...
        sprintf('%.0f mm de %.0f mm  (alturas %.0f a %.0f mm)', ...
        (max(zu)-min(zu))*mm, K.carrera*mm, ...
        (min(zu)+P.chasis.yc+P.chasis.alto/2)*mm, (max(zu)+P.chasis.yc+P.chasis.alto/2)*mm)};
  end

  % la rueda no debe tocar C ni D
  dmin = min([hypot(K.C(v,1)-K.P(v,1), K.C(v,2)-K.P(v,2)); ...
              hypot(K.D(v,1)-K.P(v,1), K.D(v,2)-K.P(v,2))]);
  add('la rueda no toca C ni D', dmin >= P.Rw + 8e-3, ...
      sprintf('nudo mas cercano al eje: %.0f mm, radio de rueda %.0f mm', dmin*mm, P.Rw*mm));

  % huella sagital
  xs = [K.C(v,1); K.D(v,1); K.P(v,1); P.A(1); P.B(1); x0; x1; P.placa.x(:)];
  R(end+1,:) = {'huella sagital (informativo)', true, ...
      sprintf('%.0f mm  (de %+.0f a %+.0f)', (max(xs)-min(xs))*mm, min(xs)*mm, max(xs)*mm)};
  R(end+1,:) = {'centro de la cabina (informativo)', true, ...
      sprintf('x = %+.0f mm  (para que el CoM caiga sobre la rueda)', P.chasis.xc*mm)};

  if verbose, imprimir(R); end
end

function imprimir(R)
  fprintf('\n=========== VERIFICACION ===========\n');
  for i = 1:size(R,1)
    if R{i,2}, m = 'PASA '; else, m = 'FALLA'; end
    fprintf('  [%s]  %-42s %s\n', m, R{i,1}, R{i,3});
  end
  fprintf('\n');
end
