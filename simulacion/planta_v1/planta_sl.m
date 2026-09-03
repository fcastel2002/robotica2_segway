function [Xdot, y] = planta_sl(X, u, d, pv)
%PLANTA_SL  Derivada del estado de la planta completa (cuerpo + ruedas + motores + servo).
%   X (16) = [x phi l dx dphi dl thwL wwL thwR wwR thmL wmL thmR wmR iL iR]
%   u (3)  = [V_L V_R th_ref]      d (5) = [F_x M_p alpha mu F_esc]
%   y (16) = [ddx ddphi ddl N_tot f_L f_R desliza tau_gL tau_gR tau_s th_s i_L i_R V_bus fb_x fb_y]
%   Marco: x a lo largo del piso (+ adelante), phi desde la normal al piso (+ adelante),
%   l = distancia eje de rueda -> CoM del cuerpo. fb = fuerza especifica en la IMU, marco cuerpo
%   (x adelante, y hacia arriba de la pata); el angulo del acelerometro es atan2(-fb_x, fb_y).
%#codegen
  m_b=pv(1); m_w=pv(2); J_b=pv(3); J_w=pv(4); Rw=pv(5); g=pv(6); l_min=pv(7); l_max=pv(8);
  b_pitch=pv(9); b_pata=pv(10); b_w=pv(11); k_tope=pv(12); c_tope=pv(13);
  mu_def=pv(26); v_s=pv(27); c_v=pv(28); V_bat=pv(29); R_bat=pv(30);
  tau_s_max=pv(31); w_nl_s=pv(32); Kp_s=pv(33); Kd_s=pv(34); n_serv=pv(35);
  d_ix=pv(38); d_iy=pv(39);
  n = round(pv(61)); l_tab = pv(62:62+n-1); th_tab = pv(83:83+n-1); dthdl_tab = pv(104:104+n-1);

  phi=X(2); l=X(3); dx=X(4); dphi=X(5); dl=X(6);
  thwL=X(7); wwL=X(8); thwR=X(9); wwR=X(10); thmL=X(11); wmL=X(12); thmR=X(13); wmR=X(14); iL=X(15); iR=X(16);
  th_ref=u(3); F_x=d(1); M_p=d(2); alpha=d(3); mu=d(4); F_esc=d(5);
  if mu <= 0, mu = mu_def; end
  if l < 1e-3, l = 1e-3; end
  c = cos(phi); s = sin(phi);

  % --- bateria y motores ---
  V_bus = max(V_bat - R_bat*(abs(iL) + abs(iR)), 0);
  V_L = max(min(u(1), V_bus), -V_bus); V_R = max(min(u(2), V_bus), -V_bus);
  [tau_gL, dwmL, diL, iL_eff, J_add] = motor_lado(V_L, iL, wmL, thmL, wwL, thwL, pv);
  [tau_gR, dwmR, diR, iR_eff, ~]     = motor_lado(V_R, iR, wmR, thmR, wwR, thwR, pv);
  J_eq = J_w + J_add;

  % --- servo: fuerza sobre l a traves del cuatro barras ---
  th_s = interp_lin(l_tab, th_tab, l);
  dthdl = interp_lin(l_tab, dthdl_tab, l);
  dth_s = dthdl*dl;
  tau_cmd = Kp_s*(th_ref - th_s) - Kd_s*dth_s;
  if tau_cmd*dth_s > 0
    lim = tau_s_max*max(0, 1 - abs(dth_s)/w_nl_s);
  else
    lim = tau_s_max;
  end
  tau_s = max(min(tau_cmd, lim), -lim);
  F_l = n_serv*tau_s*dthdl;
  f_tope = 0;
  if l < l_min, f_tope = k_tope*(l_min - l) - c_tope*dl; end
  if l > l_max, f_tope = k_tope*(l_max - l) - c_tope*dl; end

  % --- cuerpo: dos pasadas para la normal (evita el lazo algebraico) ---
  [M, C, Gv] = dinamica_v1_gen(phi, l, dphi, dl, m_b, m_w, J_b, g, alpha);
  N_tot = (m_w + m_b)*g*cos(alpha);
  qdd = zeros(3,1); f_L = 0; f_R = 0; dwwL = 0; dwwR = 0; ay_com = 0;
  for pasada = 1:2
    N_i = max(N_tot, 0)/2;
    vsL = Rw*wwL - dx; vsR = Rw*wwR - dx;
    f_L = mu*N_i*tanh(vsL/v_s) - c_v*vsL;
    f_R = mu*N_i*tanh(vsR/v_s) - c_v*vsR;
    dwwL = (tau_gL - Rw*f_L - b_w*wwL)/J_eq;
    dwwR = (tau_gR - Rw*f_R - b_w*wwR)/J_eq;
    Q = [ f_L + f_R + F_x + F_esc;
         -(tau_gL + tau_gR) + M_p + F_x*l*c - b_pitch*dphi;
          F_l + F_x*s - b_pata*dl + f_tope ];
    qdd = M \ (Q - C - Gv);
    ay_com = qdd(3)*c - 2*dl*dphi*s - l*qdd(2)*s - l*dphi^2*c;
    N_tot = (m_w + m_b)*g*cos(alpha) + m_b*ay_com;
  end
  desliza = double(abs(Rw*wwL - dx) > 2*v_s || abs(Rw*wwR - dx) > 2*v_s);

  % --- fuerza especifica en la IMU (marco cuerpo) ---
  ax_com = qdd(1) + qdd(3)*s + 2*dl*dphi*c + l*qdd(2)*c - l*dphi^2*s;
  dwx = c*d_ix + s*d_iy;  dwy = -s*d_ix + c*d_iy;
  a_imu = [ax_com; ay_com] + qdd(2)*[dwy; -dwx] - dphi^2*[dwx; dwy];
  gvec = g*[-sin(alpha); -cos(alpha)];
  fw = a_imu - gvec;
  fb_x = c*fw(1) - s*fw(2);
  fb_y = s*fw(1) + c*fw(2);

  Xdot = [dx; dphi; dl; qdd; wwL; dwwL; wwR; dwwR; wmL; dwmL; wmR; dwmR; diL; diR];
  y = [qdd; N_tot; f_L; f_R; desliza; tau_gL; tau_gR; tau_s; th_s; iL_eff; iR_eff; V_bus; fb_x; fb_y];
end
