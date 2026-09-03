function [comandos, estimaciones] = robot_controlador(medidas, referencias, par, reset)
%ROBOT_CONTROLADOR  Ley de control discreta a Ts.
%   medidas      = [giroscopo; acel_x; acel_y; encoder_izq; encoder_der]
%   referencias  = [x_ref; l_ref]
%   comandos     = [V_izq; V_der; theta_servo_ref]
%   estimaciones = [phi_est; x_est; dx_est; l_est; tau_rueda; saturado_V; en_vuelo]
%   Estados persistentes: filtro complementario, integracion de encoders, consigna de servo.
%   reset = 1 inicializa los estados (primera muestra).
%   En vuelo (|fuerza especifica| lejos de g) el filtro usa solo el giroscopo.
%#codegen
  persistent phi_est x_est w_est enc_prev th_cmd listo dx_prev a_est
  if isempty(listo), listo = false; phi_est = 0; x_est = 0; w_est = [0 0]; enc_prev = [0 0]; th_cmd = 0; dx_prev = 0; a_est = 0; end
  co = par.control; se = par.sensores; mo = par.motor; sv = par.servo; pa = par.pata;
  R = par.rueda.radio; Ts = se.Ts; V_bat = par.bateria.V; g = par.g;
  th_inv = flipud(pa.tabla_theta(:)); l_inv = flipud(pa.tabla_l(:));   % theta creciente para invertir

  giro = medidas(1); fbx = medidas(2); fby = medidas(3); enc = [medidas(4) medidas(5)];
  x_ref = referencias(1); l_ref = max(min(referencias(2), pa.l_max), pa.l_min);
  th_objetivo = interp_lin(pa.tabla_l, pa.tabla_theta, l_ref);
  if ~listo || reset > 0.5
    listo = true; phi_est = atan2(-fbx, fby); x_est = 0; w_est = [0 0]; th_cmd = th_objetivo; dx_prev = 0; a_est = 0;
    if any(isnan(enc)), enc_prev = [0 0]; else, enc_prev = enc; end
  end
  % --- posicion, velocidad y aceleracion de la base desde encoders ---
  if se.encoder > 0.5 && ~any(isnan(enc))
    dth = (enc - enc_prev)*2*pi/se.CPR; enc_prev = enc;
    a = exp(-2*pi*co.fc_vel*Ts);
    w_est = a*w_est + (1 - a)*dth/Ts;
    x_est = x_est + R*mean(dth);
    dx_est = R*mean(w_est);
    b = exp(-2*pi*5*Ts);
    a_est = b*a_est + (1 - b)*(dx_est - dx_prev)/Ts; dx_prev = dx_est;
  else
    w_est = [0 0]; dx_est = 0; a_est = 0;
  end
  % --- angulo: filtro complementario, acelerometro corregido por la aceleracion de la base ---
  en_vuelo = double(abs(hypot(fbx, fby) - g) > co.umbral_vuelo);
  k = co.k_comp; if en_vuelo > 0.5, k = 0; end           % sin piso el acelerometro no mide gravedad
  fbx_c = fbx - cos(phi_est)*a_est;  fby_c = fby - sin(phi_est)*a_est;
  phi_acel = atan2(-fbx_c, fby_c);
  phi_est = (1 - k)*(phi_est + giro*Ts) + k*phi_acel;
  dphi_est = giro;
  % --- LQR programado por largo de pata ---
  l_est = interp_lin(th_inv, l_inv, th_cmd);
  lk = max(min(l_est, co.l_max), co.l_min);
  K = co.K1 + co.K2*lk;
  tau_rueda = -(K(1)*(x_est - x_ref) + K(2)*phi_est + K(3)*dx_est + K(4)*dphi_est);
  % --- par -> tension por motor con compensacion de fcem ---
  V = zeros(2,1); saturado = 0;
  for k2 = 1:2
    Vk = mo.R*(tau_rueda/2)/(mo.Kt*mo.relacion*mo.eta) + mo.Ke*mo.relacion*w_est(k2);
    if abs(Vk) > V_bat, saturado = 1; end
    V(k2) = max(min(Vk, V_bat), -V_bat);
  end
  % --- consigna de servo con limitador de velocidad ---
  paso = 0.8*sv.w_vacio*Ts;
  th_cmd = th_cmd + max(min(th_objetivo - th_cmd, paso), -paso);
  th_cmd = max(min(th_cmd, sv.theta_max), sv.theta_min);
  comandos = [V(1); V(2); th_cmd];
  estimaciones = [phi_est; x_est; dx_est; l_est; tau_rueda; saturado; en_vuelo];
end
