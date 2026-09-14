function [dx, salida] = estado_dinamica_pata(~, x, tau, N, p, caso)
%ESTADO_DINAMICA_PATA Ecuación de estado del modelo reducido.
%   x = [theta; dtheta]. N es la fuerza normal por rueda; en el caso
%   'parado' su trabajo virtual es cero, pero la normal estimada se informa.
  theta = x(1);
  dtheta = x(2);
  T = terminos_dinamica_pata(theta, p, caso);
  tau_tope = par_tope(theta, dtheta, p);
  ddtheta = (tau + tau_tope - p.b*dtheta + N*T.wP ...
             - 0.5*T.dIeq*dtheta^2 - T.dV)/T.Ieq;
  dx = [dtheta; ddtheta];
  normal_estimada = NaN;
  if strcmpi(caso, 'parado')
    normal_estimada = normal_dinamica_pata(theta, dtheta, ddtheta, p);
  end
  salida = struct('ddtheta', ddtheta, 'tau_tope', tau_tope, ...
    'normal_estimada', normal_estimada, ...
    'contacto_valido', ~isnan(normal_estimada) && normal_estimada > 0, ...
    'en_carrera', theta >= p.theta_min && theta <= p.theta_max);
end

function tau = par_tope(theta, dtheta, p)
  tau = 0;
  if ~p.tope.habilitado, return; end
  if theta < p.theta_min
    tau = p.tope.k*(p.theta_min - theta) - p.tope.c*min(dtheta, 0);
  elseif theta > p.theta_max
    tau = -p.tope.k*(theta - p.theta_max) - p.tope.c*max(dtheta, 0);
  end
end
