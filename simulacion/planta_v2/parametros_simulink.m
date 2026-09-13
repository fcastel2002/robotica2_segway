function par = parametros_simulink(P, C)
%PARAMETROS_SIMULINK  Estructura numerica con nombres legibles para las funciones de la planta
%   y para los bloques MATLAB Function de Simulink (que no admiten strings ni handles).
%   par = parametros_simulink(P)        sin ganancias de control (K = 0)
%   par = parametros_simulink(P, C)     con el LQR de disenar_lqr_robot
  if nargin < 2 || isempty(C), C = struct('Kfit', zeros(2,4), 'l_lim', [P.din.l_min P.din.l_max]); end
  par.g = P.g;
  par.cuerpo = struct('masa', P.din.m_b, 'inercia', P.din.J_b, 'com_x', P.din.r_com(1), 'com_y', P.din.r_com(2), ...
                      'amort_cabeceo', P.cuerpo.b_pitch, 'amort_pata', P.cuerpo.b_pata, ...
                      'k_tope', P.cuerpo.k_tope, 'c_tope', P.cuerpo.c_tope, 'h_tapa_sobre_A', P.din.h_tapa_sobre_A);
  par.rueda = struct('radio', P.Rw, 'inercia', P.din.J_w, 'masa_eje', P.din.m_w, 'amort', P.rueda.b_w, ...
                     'mu', P.rueda.mu, 'v0', P.rueda.v_s, 'c_v', P.rueda.c_v);
  par.contacto = struct('k', P.contacto.k, 'c', P.contacto.c);
  par.piso = struct('x0', P.piso.x0, 'alto', P.piso.alto, 'ancho', P.piso.ancho, 'n', P.piso.n);
  % tramos del piso como vectores (descansos horizontales y contrahuellas verticales), para el modelo por bloques
  [par.piso.seg_xmin, par.piso.seg_xmax, par.piso.seg_ymin, par.piso.seg_ymax] = tramos_piso(P.piso);
  par.motor = struct('R', P.motor.R, 'L', P.motor.L, 'Kt', P.motor.Kt, 'Ke', P.motor.Ke, 'relacion', P.motor.N, ...
                     'J_rotor', P.motor.J_r, 'b_rotor', P.motor.b_m, 'tau_coulomb', P.motor.tau_c, ...
                     'rigido', double(P.motor.gear_rigido), 'k_eje', P.motor.k_g, 'c_eje', P.motor.c_g, ...
                     'juego', P.motor.juego, 'eta', P.motor.eta);
  par.bateria = struct('V', P.bat.V, 'R', P.bat.R);
  par.servo = struct('tau_max', P.servo.tau_max, 'w_vacio', P.servo.w_nl, 'Kp', P.servo.Kp, 'Kd', P.servo.Kd, ...
                     'cantidad', P.servo.n, 'theta_min', P.servo.th_min, 'theta_max', P.servo.th_max);
  par.pata = struct('l_min', P.din.l_min, 'l_max', P.din.l_max, 'l0', P.din.l0, ...
                    'tabla_l', P.tab.l(:), 'tabla_theta', P.tab.th(:), 'tabla_dtheta_dl', P.tab.dthdl(:), ...
                    'flexor_activo', double(P.flexor.activo), 'k_flexor', P.flexor.k, 'c_flexor', P.flexor.c, ...
                    'carrera_flexor', P.flexor.carrera, 'masa_mecanismo', P.din.m_mec);
  par.pata.tabla_theta_inv = flipud(P.tab.th(:)); par.pata.tabla_l_inv = flipud(P.tab.l(:));   % theta creciente, para invertir
  par.sensores = struct('Ts', P.sens.Ts, 'encoder', double(P.sens.encoder), 'CPR', P.sens.CPR, ...
                        'gyro_sesgo', P.sens.gyro_bias, 'gyro_sat', P.sens.gyro_sat, 'gyro_ruido', P.sens.gyro_rms, ...
                        'acel_ruido', P.sens.acc_rms, 'imu_dx', P.sens.d_imu(1), 'imu_dy', P.sens.d_imu(2), ...
                        'retardo', P.sens.n_delay);
  par.control = struct('k_comp', P.ctrl.k_comp, 'fc_vel', P.ctrl.fc_vel, 'fc_acel', 5, 'umbral_vuelo', P.ctrl.umbral_vuelo, ...
                       'K1', C.Kfit(1,:), 'K2', C.Kfit(2,:), 'l_min', C.l_lim(1), 'l_max', C.l_lim(2));
  % coeficientes de los pasabajos discretos del controlador: y = a y_prev + (1 - a) u
  par.control.a_vel = exp(-2*pi*par.control.fc_vel*P.sens.Ts);
  par.control.a_acel = exp(-2*pi*par.control.fc_acel*P.sens.Ts);
end

function [xmin, xmax, ymin, ymax] = tramos_piso(piso)
% Mismos tramos que recorre perfil_piso: descansos k = 0..n (altura -k*alto) y contrahuellas k = 1..n.
  n = round(piso.n); x0 = piso.x0; H = piso.alto; W = piso.ancho;
  xmin = zeros(1, 2*n + 1); xmax = xmin; ymin = xmin; ymax = xmin;
  for k = 0:n
    if k == 0, xa = -1e6; else, xa = x0 + (k-1)*W; end
    if k == n, xb = 1e6;  else, xb = x0 + k*W;     end
    xmin(k+1) = xa; xmax(k+1) = xb; ymin(k+1) = -k*H; ymax(k+1) = -k*H;
  end
  for k = 1:n
    xk = x0 + (k-1)*W;
    xmin(n+1+k) = xk; xmax(n+1+k) = xk; ymin(n+1+k) = -k*H; ymax(n+1+k) = -(k-1)*H;
  end
end
