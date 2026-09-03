function S = resumen_corrida(S)
%RESUMEN_CORRIDA  Metricas estandar de una corrida (ode15s o Simulink). Espera S.t, S.X, S.u, S.y, S.P.
  P = S.P; r2d = 180/pi; t = S.t; phi = S.X(:,3);
  peso = P.m.total*P.g;
  R.phi_max_deg = max(abs(phi))*r2d;
  R.phi_fin_deg = phi(end)*r2d;
  R.cayo = any(abs(phi) > 45*pi/180);
  fuera = abs(phi) >= 1*pi/180; idx = find(fuera, 1, 'last');
  if isempty(idx), R.t_asent = 0; elseif idx == numel(t), R.t_asent = Inf; else, R.t_asent = t(idx+1); end
  R.uso_V = max(max(abs(S.u(:,1:2))))/P.bat.V;
  R.uso_servo = max(abs(S.y(:,11)))/P.servo.tau_max;
  R.pct_desliza = 100*mean(S.y(:,8) > 0.5);
  i_tot = abs(S.y(:,13)) + abs(S.y(:,14));
  R.i_pico = max(i_tot);
  R.mAh = trapz(t, i_tot)/3600*1000;
  R.x_fin = S.X(end,1); R.l_fin = S.X(end,4);
  R.N_max_g = max(S.y(:,5))/peso;                         % normal maxima en "pesos del robot"
  l = S.X(:,4); c = cos(S.X(:,3)); s = sin(S.X(:,3)); dl = S.X(:,8); dphi = S.X(:,7);
  ay_cuerpo = S.y(:,2) + S.y(:,4).*c - 2*dl.*dphi.*s - l.*S.y(:,3).*s - l.*dphi.^2.*c;   % aceleracion vertical del CoM
  R.a_cuerpo_max_g = max(abs(ay_cuerpo))/P.g;              % pico que siente la cabina, en g
  en_vuelo = S.y(:,18) <= 0;
  R.t_vuelo = sum(en_vuelo)*P.sens.Ts;
  R.y_min = min(S.X(:,2));
  if P.flexor.activo, R.flexor_max_mm = max(S.X(:,19) - S.X(:,4))*1e3; else, R.flexor_max_mm = 0; end
  if P.piso.n > 0
    R.escalones_bajados = min(P.piso.n, max(0, floor((R.x_fin - P.piso.x0)/P.piso.ancho) + 1));
  else
    R.escalones_bajados = 0;
  end
  yg = altura_piso(S.X(:,1), P.piso);
  S.altura = (S.X(:,2) - yg) + S.X(:,4) - P.din.r_com(2) + P.din.h_tapa_sobre_A;   % tope de la tapa sobre el piso local
  S.piso_bajo_rueda = yg;
  S.resumen = R;
end
