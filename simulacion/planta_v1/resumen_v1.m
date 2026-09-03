function S = resumen_v1(S)
%RESUMEN_V1  Metricas estandar de una corrida. Espera S.t, S.X, S.u, S.y, S.P.
  P = S.P; r2d = 180/pi; t = S.t; phi = S.X(:,2);
  R.phi_max_deg = max(abs(phi))*r2d;
  R.phi_fin_deg = phi(end)*r2d;
  R.cayo = any(abs(phi) > 45*pi/180);
  fuera = abs(phi) >= 1*pi/180; idx = find(fuera, 1, 'last');
  if isempty(idx), R.t_asent = 0; elseif idx == numel(t), R.t_asent = Inf; else, R.t_asent = t(idx+1); end
  R.uso_V = max(max(abs(S.u(:,1:2))))/P.bat.V;
  R.uso_servo = max(abs(S.y(:,10)))/P.servo.tau_max;
  R.pct_desliza = 100*mean(S.y(:,7) > 0.5);
  i_tot = abs(S.y(:,12)) + abs(S.y(:,13));
  R.i_pico = max(i_tot);
  R.mAh = trapz(t, i_tot)/3600*1000;
  R.x_fin = S.X(end,1); R.l_fin = S.X(end,3);
  S.altura = P.Rw + S.X(:,3) - P.din.r_com(2) + P.din.h_tapa_sobre_A;
  S.resumen = R;
end
