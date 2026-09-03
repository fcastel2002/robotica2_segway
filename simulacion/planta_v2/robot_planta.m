function [Xdot, y] = robot_planta(X, u, d, par)
%ROBOT_PLANTA  Derivada del estado del robot completo (v2: eje libre en vertical, contacto con el piso,
%   escalones, flexor opcional).
%   X (20) = [x y phi l dx dy dphi dl  th_rueda_izq w_rueda_izq th_rueda_der w_rueda_der ...
%             th_rotor_izq w_rotor_izq th_rotor_der w_rotor_der  i_izq i_der  l_mec dl_mec]
%   u (3)  = [V_izq V_der theta_servo_ref]        d (5) = [F_x M_p alpha mu F_esc]
%   y (18) = [ddx ddy ddphi ddl N f_izq f_der desliza tau_g_izq tau_g_der tau_servo theta_servo ...
%             i_izq i_der V_bus fb_x fb_y penetracion]
%   Marco: x a lo largo del piso (+ adelante), y normal al piso (altura del eje de rueda), phi del
%   cuerpo desde la normal (+ adelante), l = distancia eje de rueda -> CoM del cuerpo. Con flexor,
%   l_mec es el largo que impone el cuatro barras y l - l_mec la deformacion del flexor.
%#codegen
  cu = par.cuerpo; ru = par.rueda; sv = par.servo; pa = par.pata; g = par.g;
  x = X(1); yw = X(2); phi = X(3); l = X(4); dx = X(5); dyw = X(6); dphi = X(7); dl = X(8);
  thwL = X(9); wwL = X(10); thwR = X(11); wwR = X(12); thmL = X(13); wmL = X(14); thmR = X(15); wmR = X(16);
  iL = X(17); iR = X(18); lm = X(19); dlm = X(20);
  th_ref = u(3); F_x = d(1); M_p = d(2); alpha = d(3); mu = d(4); F_esc = d(5);
  if mu <= 0, mu = ru.mu; end
  if l < 1e-3, l = 1e-3; end
  c = cos(phi); s = sin(phi);

  % --- bateria y motores ---
  V_bus = max(par.bateria.V - par.bateria.R*(abs(iL) + abs(iR)), 0);
  V_L = max(min(u(1), V_bus), -V_bus); V_R = max(min(u(2), V_bus), -V_bus);
  [tau_gL, dwmL, diL, iL_ef, J_extra] = motor_reductor(V_L, iL, wmL, thmL, wwL, thwL, par);
  [tau_gR, dwmR, diR, iR_ef, ~]       = motor_reductor(V_R, iR, wmR, thmR, wwR, thwR, par);
  J_eq = ru.inercia + J_extra;

  % --- contacto rueda-piso (las dos ruedas) ---
  [Fcx, Fcy, tcL, tcR, N, fL, fR, desliza, delta] = contacto_rueda(x, yw, dx, dyw, wwL, wwR, par, mu);

  % --- servo: actua sobre el largo del mecanismo (l_mec con flexor, l sin flexor) ---
  con_flexor = pa.flexor_activo > 0.5;
  if con_flexor, lq = lm; dlq = dlm; else, lq = l; dlq = dl; end
  th_s = interp_lin(pa.tabla_l, pa.tabla_theta, lq);
  dthdl = interp_lin(pa.tabla_l, pa.tabla_dtheta_dl, lq);
  dth_s = dthdl*dlq;
  tau_cmd = sv.Kp*(th_ref - th_s) - sv.Kd*dth_s;
  if tau_cmd*dth_s > 0, lim = sv.tau_max*max(0, 1 - abs(dth_s)/sv.w_vacio); else, lim = sv.tau_max; end
  tau_s = max(min(tau_cmd, lim), -lim);
  F_servo = sv.cantidad*tau_s*dthdl;
  f_tope = 0;
  if lq < pa.l_min, f_tope = cu.k_tope*(pa.l_min - lq) - cu.c_tope*dlq; end
  if lq > pa.l_max, f_tope = cu.k_tope*(pa.l_max - lq) - cu.c_tope*dlq; end
  if con_flexor
    sc = lm - l; dsc = dlm - dl;                        % compresion del flexor y su velocidad
    F_flex = pa.k_flexor*sc + pa.c_flexor*dsc;          % positiva empuja el cuerpo lejos del eje
    if sc < 0, F_flex = F_flex + cu.k_tope*sc + cu.c_tope*dsc; end
    if sc > pa.carrera_flexor, F_flex = F_flex + cu.k_tope*(sc - pa.carrera_flexor) + cu.c_tope*dsc; end
    Q_l = F_flex + F_x*s;
    ddlm = (F_servo - F_flex + f_tope - cu.amort_pata*dlm)/pa.masa_mecanismo;
    dlm_est = dlm;
  else
    Q_l = F_servo + f_tope + F_x*s - cu.amort_pata*dl;
    ddlm = 0; dlm_est = 0;
  end

  % --- cuerpo ---
  [M, C, Gv] = dinamica_cuerpo_gen(phi, l, dphi, dl, cu.masa, ru.masa_eje, cu.inercia, g, alpha);
  Q = [ Fcx + F_x + F_esc;
        Fcy;
       -(tau_gL + tau_gR) + M_p + F_x*l*c - cu.amort_cabeceo*dphi;
        Q_l ];
  qdd = M \ (Q - C - Gv);

  % --- ruedas ---
  dwwL = (tau_gL + tcL - ru.amort*wwL)/J_eq;
  dwwR = (tau_gR + tcR - ru.amort*wwR)/J_eq;

  % --- fuerza especifica en la IMU (marco cuerpo: x adelante, y hacia arriba de la pata) ---
  ax_com = qdd(1) + qdd(4)*s + 2*dl*dphi*c + l*qdd(3)*c - l*dphi^2*s;
  ay_com = qdd(2) + qdd(4)*c - 2*dl*dphi*s - l*qdd(3)*s - l*dphi^2*c;
  d_ix = par.sensores.imu_dx; d_iy = par.sensores.imu_dy;
  dwx = c*d_ix + s*d_iy;  dwy = -s*d_ix + c*d_iy;
  a_imu = [ax_com; ay_com] + qdd(3)*[dwy; -dwx] - dphi^2*[dwx; dwy];
  gvec = g*[-sin(alpha); -cos(alpha)];
  fw = a_imu - gvec;
  fb_x = c*fw(1) - s*fw(2);
  fb_y = s*fw(1) + c*fw(2);

  Xdot = [dx; dyw; dphi; dl; qdd; wwL; dwwL; wwR; dwwR; wmL; dwmL; wmR; dwmR; diL; diR; dlm_est; ddlm];
  y = [qdd; N; fL; fR; desliza; tau_gL; tau_gR; tau_s; th_s; iL_ef; iR_ef; V_bus; fb_x; fb_y; delta];
end
