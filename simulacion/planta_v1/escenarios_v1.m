function E = escenarios_v1(nombre, P)
%ESCENARIOS_V1  Estado inicial, referencias, perturbaciones y overrides de cada escenario.
%   E = escenarios_v1('equilibrio_8', P)      lista = escenarios_v1('lista')
%   E.ref / E.pert son estructuras para From Workspace: .time (n x 1), .signals.values (n x k).
%   ref = [x_ref l_ref] ; pert = [F_x M_p alpha mu F_esc]
  lista = {'equilibrio_3','equilibrio_8','equilibrio_15','empujon_3N','empujon_6N','agachar','avanzar', ...
           'velocidad','pendiente_5','pendiente_10','escalon_5mm','escalon_10mm','resbaloso','bateria_baja', ...
           'sensor_retardo_10','sin_encoder'};
  if strcmp(nombre, 'lista'), E = lista; return; end
  d2r = pi/180; dt = 1e-3;
  E.nombre = nombre; E.tf = 6; E.overrides = {}; E.n_delay = P.sens.n_delay; E.semilla = P.sens.semilla;
  X0 = zeros(16,1); X0(3) = P.din.l0;
  t = (0:dt:E.tf)';
  x_ref = zeros(size(t)); l_ref = P.din.l0*ones(size(t));
  F_x = zeros(size(t)); M_p = zeros(size(t)); alpha = zeros(size(t)); mu = P.rueda.mu*ones(size(t)); F_esc = zeros(size(t));
  pulso = @(t0, dur) double(t >= t0 & t < t0 + dur);
  m_tot = P.din.m_b + P.din.m_w;
  switch nombre
    case 'equilibrio_3',  X0(2) = 3*d2r;
    case 'equilibrio_8',  X0(2) = 8*d2r;
    case 'equilibrio_15', X0(2) = 15*d2r;
    case 'empujon_3N',    F_x = 3*pulso(2, 0.05);
    case 'empujon_6N',    F_x = 6*pulso(2, 0.05);
    case 'agachar',       l_ref(t > 1 & t <= 3) = P.din.l_min*1.05; l_ref(t > 3) = P.din.l_max*0.97;
    case 'avanzar',       x_ref(t > 1 & t <= 4) = 0.5;
    case 'velocidad',     x_ref = 0.2*max(t - 1, 0);
    case 'pendiente_5',   alpha(:) = 5*d2r;
    case 'pendiente_10',  alpha(:) = 10*d2r;
    case 'escalon_5mm',   F_esc = -m_tot*sqrt(2*P.g*0.005)/0.02*pulso(3, 0.02);
    case 'escalon_10mm',  F_esc = -m_tot*sqrt(2*P.g*0.010)/0.02*pulso(3, 0.02);
    case 'resbaloso',     mu(:) = 0.3; F_x = 3*pulso(2, 0.05); E.overrides = {'mu', 0.3};
    case 'bateria_baja',  F_x = 6*pulso(2, 0.05); E.overrides = {'V_bat', 9.6};
    case 'sensor_retardo_10', F_x = 6*pulso(2, 0.05); E.n_delay = 2; E.overrides = {'n_delay', 2};
    case 'sin_encoder',   x_ref(t > 1 & t <= 4) = 0.5; E.overrides = {'encoder', false};
    otherwise, error('escenarios_v1: escenario "%s" no definido', nombre);
  end
  E.X0 = X0;
  E.ref.time = t;  E.ref.signals.values = [x_ref l_ref];                E.ref.signals.dimensions = 2;
  E.pert.time = t; E.pert.signals.values = [F_x M_p alpha mu F_esc];    E.pert.signals.dimensions = 5;
end
