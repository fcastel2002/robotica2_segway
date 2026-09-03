function [qdd, s] = dinamica_robot(q, qd, u, P)
%DINAMICA_ROBOT  Envoltorio comodo de DINAMICA_SL con el struct de parametros.
%   Toda la fisica esta en dinamica_sl.m, que es la version que usa Simulink.
%   Asi hay una sola fuente de verdad para las ecuaciones.
%
%   q  = [x; phi; l]     x hacia ADELANTE, phi desde la vertical, l = eje->CoM
%   qd = [dx; dphi; dl]
%   u  = [tau_w; tau_s]  las dos ruedas juntas / los dos hombros juntos
  persistent pv_cache clave
  cl = [P.din.m_b P.din.m_w P.Rw P.din.Gfit(:).' P.act.tau_w_max];
  if isempty(clave) || numel(clave) ~= numel(cl) || any(clave ~= cl)
    pv_cache = empaquetar(P); clave = cl;
  end
  [qdd, N, f_roce, desliza, theta_m, G] = dinamica_sl(q, qd, u, pv_cache);
  if nargout > 1
    s.N = N; s.f_roce = f_roce; s.desliza = desliza;
    s.theta = theta_m; s.G = G; s.f_pata = u(2)/G;
    s.phi_chasis = q(2) - atan2(P.din.r_com(1), max(q(3),1e-3));
  end
end
