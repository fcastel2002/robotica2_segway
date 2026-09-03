function tests = test_control_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_sensores(tc)
  P = parametros_v1('corregido'); pv = empaquetar_v1(P);
  X = zeros(16,1); X(5) = 0.3; X(7) = 2*pi; X(9) = pi;
  y = zeros(16,1); y(15) = 0; y(16) = P.g;
  m = sensores_sl(X, y, [0;0;0], pv);
  tc.verifyEqual(m(1), 0.3 + P.sens.gyro_bias, 'AbsTol', 1e-12);
  tc.verifyEqual(m(4), floor(P.sens.CPR)); tc.verifyEqual(m(5), floor(P.sens.CPR/2));   % CPR no entero con N = 21.3
  P2 = parametros_v1('cad', 'encoder', false); m2 = sensores_sl(X, y, [0;0;0], empaquetar_v1(P2));
  tc.verifyTrue(all(isnan(m2(4:5))));
  m3 = sensores_sl(X, y, [1;0;0], pv);
  tc.verifyEqual(m3(1) - m(1), P.sens.gyro_rms, 'AbsTol', 1e-12);
end
function test_filtro_complementario(tc)
  P = parametros_v1('corregido'); pv = empaquetar_v1(P); pv(51:60) = 0;
  phi = 5*pi/180; meas = [0; -P.g*sin(phi); P.g*cos(phi); 0; 0];
  control_v1(meas, [0; P.din.l0], pv, 1);
  est = zeros(6,1);
  for k = 1:3000, [~, est] = control_v1(meas, [0; P.din.l0], pv, 0); end   % 15 s >> Ts/k_comp = 1 s
  tc.verifyEqual(est(1), phi, 'AbsTol', 0.1*pi/180);
end
function test_lqr_y_tension(tc)
  P = parametros_v1('corregido'); pv = empaquetar_v1(P);
  pv(51:54) = [-0.3 -3 -0.4 -0.5]; pv(55:58) = 0; pv(59) = P.din.l_min; pv(60) = P.din.l_max;
  meas0 = [0; 0; P.g; 0; 0];
  control_v1(meas0, [0; P.din.l0], pv, 1);
  [u, est] = control_v1([0; -P.g*sin(0.1); P.g*cos(0.1); 0; 0], [0; P.din.l0], pv, 0);
  tc.verifyGreaterThan(est(5), 0);                          % inclinado adelante -> par positivo
  tc.verifyGreaterThan(u(1), 0); tc.verifyEqual(u(1), u(2), 'AbsTol', 1e-12);
  tc.verifyLessThanOrEqual(abs(u(1)), P.bat.V);
end
function test_servo_limitado(tc)
  P = parametros_v1('corregido'); pv = empaquetar_v1(P);
  meas0 = [0; 0; P.g; 0; 0];
  control_v1(meas0, [0; P.din.l_max], pv, 1);
  th_max_l = interp_lin(P.tab.l, P.tab.th, P.din.l_max);
  u1 = control_v1(meas0, [0; P.din.l_min], pv, 0);
  tc.verifyEqual(abs(u1(3) - th_max_l), 0.8*P.servo.w_nl*P.sens.Ts, 'RelTol', 1e-9);   % un paso limitado
  u = u1;
  for k = 1:2000, u = control_v1(meas0, [0; P.din.l_min], pv, 0); end
  tc.verifyEqual(u(3), interp_lin(P.tab.l, P.tab.th, P.din.l_min), 'AbsTol', 1e-9);
  tc.verifyGreaterThanOrEqual(u(3), P.servo.th_min); tc.verifyLessThanOrEqual(u(3), P.servo.th_max);
end
function test_encoder_estima_x(tc)
  P = parametros_v1('corregido'); pv = empaquetar_v1(P); pv(51:60) = 0;
  meas = [0; 0; P.g; 0; 0]; control_v1(meas, [0; P.din.l0], pv, 1);
  cnt = P.sens.CPR;                      % una vuelta por muestra en las dos ruedas
  est = zeros(6,1);
  for k = 1:50, [~, est] = control_v1([0; 0; P.g; k*cnt; k*cnt], [0; P.din.l0], pv, 0); end
  tc.verifyEqual(est(2), 50*2*pi*P.Rw, 'RelTol', 1e-9);
  tc.verifyEqual(est(3), 2*pi*P.Rw/P.sens.Ts, 'RelTol', 0.01);
end
