function tests = test_planta
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function [th_ref, tau_nec] = servo_que_sostiene(P, l, phi)
  th = interp_lin(P.tab.l, P.tab.th, l); dthdl = interp_lin(P.tab.l, P.tab.dthdl, l);
  tau_nec = P.din.m_b*P.g*cos(phi)/(P.servo.n*abs(dthdl));
  th_ref = th + sign(dthdl)*tau_nec/P.servo.Kp;
end
function test_tamanos(tc)
  P = parametros_robot('cad'); par = parametros_simulink(P); X0 = estado_inicial(P);
  [Xdot, y] = robot_planta(X0, [0;0;interp_lin(P.tab.l,P.tab.th,P.din.l0)], [0;0;0;0;0], par);
  tc.verifyEqual(size(Xdot), [20 1]); tc.verifyEqual(size(y), [18 1]); tc.verifyTrue(all(isfinite(Xdot)));
end
function test_equilibrio_estatico_en_el_piso(tc)
  P = parametros_robot('corregido'); par = parametros_simulink(P); X0 = estado_inicial(P);
  th_ref = servo_que_sostiene(P, P.din.l0, 0);
  [Xdot, y] = robot_planta(X0, [0;0;th_ref], [0;0;0;0;0], par);
  tc.verifyEqual(Xdot(5:8), zeros(4,1), 'AbsTol', 1e-6);          % nada acelera
  tc.verifyEqual(y(5), P.m.total*P.g, 'RelTol', 1e-9);             % la normal sostiene todo el peso
  tc.verifyEqual(y(18), P.m.total*P.g/(2*P.contacto.k), 'RelTol', 1e-9);
  tc.verifyEqual(atan2(-y(16), y(17)), 0, 'AbsTol', 1e-9);         % la IMU lee vertical
end
function test_caida_libre(tc)
  P = parametros_robot('corregido'); par = parametros_simulink(P); X0 = estado_inicial(P);
  X0(2) = P.Rw + 0.1;                                              % 10 cm en el aire
  th_ref = interp_lin(P.tab.l, P.tab.th, P.din.l0);               % servo sin error: en vuelo no sostiene nada
  [Xdot, y] = robot_planta(X0, [0;0;th_ref], [0;0;0;0;0], par);
  tc.verifyEqual(Xdot(6), -P.g, 'RelTol', 1e-9);                   % el eje cae con g
  tc.verifyEqual(Xdot(5), 0, 'AbsTol', 1e-9); tc.verifyEqual(y(5), 0);
  tc.verifyEqual(hypot(y(16), y(17)), 0, 'AbsTol', 1e-6);          % el acelerometro lee cero: ingravidez
end
function test_pendiente_y_servo(tc)
  P = parametros_robot('cad'); par = parametros_simulink(P); X0 = estado_inicial(P, 0.2, P.din.l0);
  [th_ref, tau_nec] = servo_que_sostiene(P, P.din.l0, 0.2);
  M_p = -P.din.m_b*P.g*P.din.l0*sin(0.2);                          % cancela el vuelco
  [Xdot, y] = robot_planta(X0, [0;0;th_ref], [0;M_p;0;0;0], par);
  tc.verifyEqual(Xdot(5:8), zeros(4,1), 'AbsTol', 1e-5);
  tc.verifyEqual(abs(y(11)), tau_nec, 'RelTol', 1e-6);
  tc.verifyEqual(atan2(-y(16), y(17)), 0.2, 'AbsTol', 1e-6);
end
function test_flexor_estatico(tc)
  P = parametros_robot('corregido', 'flexor', true); par = parametros_simulink(P);
  % con el flexor, el cuerpo cuelga del mecanismo: en equilibrio el flexor comprime m_b g / k
  l0 = P.din.l0; sc = P.din.m_b*P.g/P.flexor.k;
  X0 = estado_inicial(P, 0, l0); X0(19) = l0 + sc;                 % l_mec = l + compresion
  th_ref = servo_que_sostiene(P, l0 + sc, 0);
  [Xdot] = robot_planta(X0, [0;0;th_ref], [0;0;0;0;0], par);
  tc.verifyEqual(Xdot(5:8), zeros(4,1), 'AbsTol', 1e-6);
  tc.verifyEqual(Xdot(20), 0, 'AbsTol', 1e-6);                     % el mecanismo tampoco acelera
  tc.verifyLessThan(sc, P.flexor.carrera);
end
function test_controlador_vuelo(tc)
  P = parametros_robot('corregido'); C = disenar_lqr_robot(P); par = parametros_simulink(P, C);
  m0 = [0; 0; P.g; 0; 0]; robot_controlador(m0, [0; P.din.l0], par, 1);
  [~, e1] = robot_controlador([0.5; 0; P.g; 0; 0], [0; P.din.l0], par, 0);      % en el piso, gira a 0.5 rad/s
  tc.verifyEqual(e1(7), 0);
  [~, e2] = robot_controlador([0.5; 0; 0.5; 0; 0], [0; P.din.l0], par, 0);      % acelerometro casi cero: vuelo
  tc.verifyEqual(e2(7), 1);
  tc.verifyEqual(e2(1) - e1(1), 0.5*P.sens.Ts, 'AbsTol', 1e-9);                % solo integra el giroscopo
end
function test_lqr(tc)
  for v = {'cad','corregido'}
    P = parametros_robot(v{1}); C = disenar_lqr_robot(P);
    for i = 1:numel(C.polos_lc), tc.verifyLessThan(max(real(C.polos_lc{i})), 0); end
    tc.verifyLessThan(C.Kf(P.din.l0)*[0;1;0;0], 0);
    par = parametros_simulink(P, C); tc.verifyEqual(par.control.K1, C.Kfit(1,:));
  end
end
