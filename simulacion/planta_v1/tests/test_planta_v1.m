function tests = test_planta_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_tamanos(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P);
  X = zeros(16,1); X(3) = P.din.l0;
  [Xdot, y] = planta_sl(X, [0;0;interp_lin(P.tab.l,P.tab.th,P.din.l0)], [0;0;0;0.7;0], pv);
  tc.verifyEqual(size(Xdot), [16 1]); tc.verifyEqual(size(y), [16 1]);
  tc.verifyTrue(all(isfinite(Xdot)));
end
function test_servo_sostiene_el_peso(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P);
  l = P.din.l0; th = interp_lin(P.tab.l, P.tab.th, l); dthdl = interp_lin(P.tab.l, P.tab.dthdl, l);
  tau_nec = P.din.m_b*P.g/(P.servo.n*abs(dthdl));       % par por servo para sostener el cuerpo
  tc.verifyLessThan(tau_nec, P.servo.tau_max);
  X = zeros(16,1); X(3) = l;
  % tau_s necesario (con signo) = m_b g /(n dthdl); el error de posicion que lo produce es tau_s/Kp
  th_ref = th + sign(dthdl)*tau_nec/P.servo.Kp;
  [Xdot, y] = planta_sl(X, [0;0;th_ref], [0;0;0;0.7;0], pv);
  tc.verifyEqual(Xdot(6), 0, 'AbsTol', 1e-6);
  tc.verifyEqual(abs(y(10)), tau_nec, 'RelTol', 1e-6);
  Xdot2 = planta_sl(X, [0;0;th], [0;0;0;0.7;0], pv);
  tc.verifyLessThan(Xdot2(6), 0);                         % sin error de servo, el cuerpo baja
end
function test_imu_en_reposo(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P);
  phi = 0.2; l = P.din.l0; th = interp_lin(P.tab.l, P.tab.th, l); dthdl = interp_lin(P.tab.l, P.tab.dthdl, l);
  tau_nec = P.din.m_b*P.g*cos(phi)/(P.servo.n*abs(dthdl));
  th_ref = th + sign(dthdl)*tau_nec/P.servo.Kp;
  X = zeros(16,1); X(2) = phi; X(3) = l;
  M_p = -P.din.m_b*P.g*l*sin(phi);                        % cancela el vuelco por gravedad (Q = Gv)
  [Xdot, y] = planta_sl(X, [0;0;th_ref], [0;M_p;0;0.7;0], pv);
  tc.verifyEqual(Xdot(4:6), zeros(3,1), 'AbsTol', 1e-6);
  tc.verifyEqual(atan2(-y(15), y(16)), phi, 'AbsTol', 1e-6);
  tc.verifyEqual(hypot(y(15), y(16)), P.g, 'RelTol', 1e-9);
end
function test_rodadura_vs_modelo_base(tc)
  % Reductor rigido, J_r = 0, L = 0, sin friccion, contacto muy rigido y servo casi rigido:
  % la planta debe reproducir la dinamica de modelo_base con el mismo par de rueda en lazo abierto.
  P = parametros_v1('cad', 'J_r', 0, 'L_m', 0, 'tau_c', 0, 'b_m', 0, 'b_w', 0, 'mu', 5, 'v_s', 1e-4, 'c_v', 0, ...
                    'Kp_s', 4500, 'Kd_s', 100, 'tau_s_max', 100);
  pv = empaquetar_v1(P);
  Pz = params_robot('s', 80, 'Dw', 66);
  Pz.din.m_b = P.din.m_b; Pz.din.m_w = P.din.m_w; Pz.din.J_b = P.din.J_b; Pz.din.J_w = P.din.J_w;
  Pz.b.rueda = 0; Pz.b.pitch = P.cuerpo.b_pitch; Pz.b.pata = P.cuerpo.b_pata;
  Pz.din.l_min = P.din.l_min; Pz.din.l_max = P.din.l_max;
  pvz = empaquetar(Pz);
  V = 2; N = P.motor.N; Kt = P.motor.Kt; Ke = P.motor.Ke; R = P.motor.R; Rw = P.Rw;
  l = P.din.l0; th = interp_lin(P.tab.l, P.tab.th, l); dthdl = interp_lin(P.tab.l, P.tab.dthdl, l);
  tau_nec = P.din.m_b*P.g/(P.servo.n*abs(dthdl)); th_ref = th + sign(dthdl)*tau_nec/P.servo.Kp;
  X0 = zeros(16,1); X0(2) = 0.05; X0(3) = l;
  opts = odeset('RelTol',1e-7,'AbsTol',1e-9,'MaxStep',1e-3);
  [~, Xa] = ode15s(@(t,X) planta_sl(X, [V;V;th_ref], [0;0;0;5;0], pv), [0 0.2], X0, opts);
  f = @(t,Z) campo_z(Z, V, N, Kt, Ke, R, Rw, P, pvz);
  [~, Za] = ode15s(f, [0 0.2], [0; 0.05; l; 0; 0; 0], opts);
  tc.verifyEqual(Xa(end,1:2), Za(end,1:2), 'RelTol', 0.02, 'AbsTol', 1e-3);
end
function dZ = campo_z(Z, V, N, Kt, Ke, R, Rw, P, pvz)
  % modelo_base con el mismo par de rueda (dos motores) y una fuerza de servo que sostiene el peso
  q = Z(1:3); qd = Z(4:6);
  tau = 2*N*Kt*(V - Ke*N*qd(1)/Rw)/R;
  G = pvz(7) + pvz(8)*q(3);
  F_l = P.din.m_b*P.g;
  qdd = dinamica_sl(q, qd, [tau; F_l*G], pvz);
  dZ = [qd; qdd];
end
