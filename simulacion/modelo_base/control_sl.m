function [u, sat_w, sat_s] = control_sl(X, ref, pv)
%CONTROL_SL  Ley de control, version numerica pura (apta para Simulink).
%   X = [x; phi; l; dx; dphi; dl]    ref = [x_ref; l_ref]    pv = empaquetar(P,C)
%#codegen
  m_b=pv(1); g=pv(6); ga=pv(7); gb=pv(8);
  l_min=pv(9); l_max=pv(10);
  tw_max=pv(14); ts_max=pv(15); kp=pv(16);
  K1 = pv(22:25).'; K2 = pv(26:29).'; lA = pv(30); lB = pv(31);

  x=X(1); phi=X(2); l=X(3); dx=X(4); dphi=X(5); dl=X(6);
  l_ref = ref(2);
  if l_ref < l_min, l_ref = l_min; end
  if l_ref > l_max, l_ref = l_max; end

  lk = l; if lk < lA, lk = lA; end; if lk > lB, lk = lB; end
  K = K1 + K2*lk;                        % ganancia programada por altura de pata

  tau_w = -(K(1)*(x-ref(1)) + K(2)*phi + K(3)*dx + K(4)*dphi);
  sat_w = double(abs(tau_w) > tw_max);
  if tau_w >  tw_max, tau_w =  tw_max; end
  if tau_w < -tw_max, tau_w = -tw_max; end

  G = ga + gb*l;  if abs(G) < 1e-4, G = 1e-4; end
  tau_s = m_b*g*G + (kp*(l_ref - l) - 0.10*kp*dl) * G;
  sat_s = double(abs(tau_s) > ts_max);
  if tau_s >  ts_max, tau_s =  ts_max; end
  if tau_s < -ts_max, tau_s = -ts_max; end

  u = [tau_w; tau_s];
end
