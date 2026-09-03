function [u, y] = controlador(X, ref, C, P)
%CONTROLADOR  Envoltorio comodo de CONTROL_SL con los structs.
%   Toda la ley esta en control_sl.m, que es la version que usa Simulink.
  persistent pv_cache clave
  cl = [C.Kfit(:).' P.act.tau_w_max P.act.tau_s_max P.act.kp_servo];
  if isempty(clave) || numel(clave) ~= numel(cl) || any(clave ~= cl)
    pv_cache = empaquetar(P, C); clave = cl;
  end
  [u, sw, ss] = control_sl(X, ref, pv_cache);
  if nargout > 1, y.sat_w = sw; y.sat_s = ss; end
end
