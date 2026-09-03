function K = barrido_pata(P, n)
%BARRIDO_PATA  Recorre el rango del motor y calcula todas las metricas.
%
%   K = barrido_pata(P)      usa 361 puntos
%   K = barrido_pata(P, n)
%
%   Agrega a la salida de cinematica_pata (todo en SI):
%     K.z          altura del pivote A sobre el suelo, por pose   [m]
%     K.h_total    altura del tope del chasis sobre el suelo      [m]
%     K.carrera    z_max - z_min                                  [m]
%     K.desvio     desviacion horizontal maxima del eje de rueda  [m]
%     K.offset     |x| medio del eje de rueda respecto de A       [m]
%     K.mu_min     angulo de transmision minimo                   [rad]
%     K.dzdth      ganancia del mecanismo, dz/dtheta              [m/rad]
%     K.tau_hombro par estatico en el hombro por pata             [N.m]

  if nargin < 2, n = 361; end
  th = linspace(P.th(1), P.th(2), n);
  K = cinematica_pata(P, th);
  if ~any(K.valido)
    K.ok = false; K.carrera = NaN; K.desvio = NaN; K.mu_min = NaN;
    K.dzdth = NaN; K.tau_hombro = NaN; K.offset = NaN;
    K.z = nan(n,1); K.h_total = nan(n,1);
    return;
  end

  v = K.valido;
  % el suelo esta a Rw por debajo del eje de rueda -> altura de A sobre el suelo
  K.z = nan(numel(th),1);
  K.z(v) = P.Rw - K.P(v,2);
  K.h_total = K.z + P.chasis.yc + P.chasis.alto/2;

  K.carrera = max(K.z(v)) - min(K.z(v));
  K.desvio  = max(K.P(v,1)) - min(K.P(v,1));
  K.offset  = abs(mean(K.P(v,1)));
  K.mu_min  = min(K.mu(v));
  K.mu_max  = max(K.mu(v));

  dth = abs(th(find(v,1,'last')) - th(find(v,1,'first')));
  K.dzdth = K.carrera / dth;
  K.giro  = dth;

  % par estatico: la mitad del peso por pata, multiplicada por la ganancia
  F = P.m.total * 9.81 / 2;
  K.tau_hombro = F * K.dzdth;                 % [N.m]
  K.tau_rueda  = 0.7 * F * P.Rw;              % limite de traccion, mu = 0.7
end
