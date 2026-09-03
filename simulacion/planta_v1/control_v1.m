function [u, est] = control_v1(meas, ref, pv, reset)
%CONTROL_V1  Ley de control discreta a Ts. meas = [gyro fb_x fb_y enc_L enc_R], ref = [x_ref l_ref].
%   u = [V_L; V_R; th_cmd]      est = [phi_hat; x_hat; dx_hat; l_hat; tau_w; sat_V]
%   Estados persistentes: filtro complementario, integracion de encoders, consigna de servo.
%   reset = 1 inicializa los estados (se usa en la primera muestra).
%#codegen
  persistent phi_hat x_hat w_hat enc_prev th_cmd listo dx_prev a_hat
  if isempty(listo), listo = false; phi_hat = 0; x_hat = 0; w_hat = [0 0]; enc_prev = [0 0]; th_cmd = 0; dx_prev = 0; a_hat = 0; end
  Rw=pv(5); l_min=pv(7); l_max=pv(8); R_m=pv(14); Kt=pv(16); Ke=pv(17); N=pv(18); V_bat=pv(29);
  w_nl_s=pv(32); th_min=pv(36); th_max=pv(37); Ts=pv(40); encoder=pv(41)>0.5; CPR=pv(42);
  k_comp=pv(47); fc_vel=pv(48); eta=pv(49);
  K1=pv(51:54); K2=pv(55:58); lA=pv(59); lB=pv(60);
  n=round(pv(61)); l_tab=pv(62:62+n-1); th_tab=pv(83:83+n-1);
  th_inv = flipud(th_tab(:)); l_inv = flipud(l_tab(:));      % theta creciente para invertir el mapa

  gyro=meas(1); fbx=meas(2); fby=meas(3); enc=[meas(4) meas(5)];
  x_ref=ref(1); l_ref=max(min(ref(2), l_max), l_min);
  th_target = interp_lin(l_tab, th_tab, l_ref);
  if ~listo || reset > 0.5
    listo = true; phi_hat = atan2(-fbx, fby); x_hat = 0; w_hat = [0 0]; th_cmd = th_target; dx_prev = 0; a_hat = 0;
    if any(isnan(enc)), enc_prev = [0 0]; else, enc_prev = enc; end
  end
  % --- posicion, velocidad y aceleracion de la base desde encoders ---
  if encoder && ~any(isnan(enc))
    dth = (enc - enc_prev)*2*pi/CPR; enc_prev = enc;
    a = exp(-2*pi*fc_vel*Ts);
    w_hat = a*w_hat + (1 - a)*dth/Ts;
    x_hat = x_hat + Rw*mean(dth);
    dx_hat = Rw*mean(w_hat);
    b = exp(-2*pi*5*Ts);
    a_hat = b*a_hat + (1 - b)*(dx_hat - dx_prev)/Ts; dx_prev = dx_hat;
  else
    w_hat = [0 0]; dx_hat = 0; a_hat = 0;   % modo degradado: sin medida de rueda
  end
  % --- angulo: filtro complementario con el acelerometro corregido por la aceleracion de la base ---
  % (sin esta correccion, acelerar hacia adelante se lee como inclinarse hacia atras y el lazo se escapa)
  fbx_c = fbx - cos(phi_hat)*a_hat;  fby_c = fby - sin(phi_hat)*a_hat;
  phi_acc = atan2(-fbx_c, fby_c);
  phi_hat = (1 - k_comp)*(phi_hat + gyro*Ts) + k_comp*phi_acc;
  dphi_hat = gyro;
  % --- LQR programado por altura de pata (l estimado desde la consigna de servo) ---
  l_hat = interp_lin(th_inv, l_inv, th_cmd);
  lk = max(min(l_hat, lB), lA);
  K = K1 + K2*lk;
  tau_w = -(K(1)*(x_hat - x_ref) + K(2)*phi_hat + K(3)*dx_hat + K(4)*dphi_hat);
  % --- par -> tension por motor con compensacion de fcem ---
  V = zeros(2,1); sat_V = 0;
  for k = 1:2
    Vk = R_m*(tau_w/2)/(Kt*N*eta) + Ke*N*w_hat(k);
    if abs(Vk) > V_bat, sat_V = 1; end
    V(k) = max(min(Vk, V_bat), -V_bat);
  end
  % --- consigna de servo con limitador de velocidad ---
  paso = 0.8*w_nl_s*Ts;
  th_cmd = th_cmd + max(min(th_target - th_cmd, paso), -paso);
  th_cmd = max(min(th_cmd, th_max), th_min);
  u = [V(1); V(2); th_cmd];
  est = [phi_hat; x_hat; dx_hat; l_hat; tau_w; sat_V];
end
