function tests = test_motor_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_bloqueo(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P); pv(15) = 0;   % L = 0 -> corriente algebraica
  [tau_g, dwm, di, i, J_add] = motor_lado(12, 0, 0, 0, 0, 0, pv);
  tc.verifyEqual(i, 12/P.motor.R, 'RelTol', 1e-9);
  tc.verifyEqual(tau_g, P.motor.N*P.motor.Kt*12/P.motor.R, 'RelTol', 1e-9);
  tc.verifyEqual(dwm, 0); tc.verifyEqual(di, 0);
  tc.verifyEqual(J_add, P.motor.N^2*P.motor.J_r, 'RelTol', 1e-12);
end
function test_vacio(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P); pv(15) = 0;
  J_eq = P.din.J_w + P.motor.N^2*P.motor.J_r;
  f = @(~, z) dz_vacio(z, pv, J_eq, P.rueda.b_w);
  [~, Z] = ode15s(f, [0 3], 0, odeset('RelTol',1e-6));
  w_fin = Z(end);
  tc.verifyGreaterThan(w_fin, 0.90*P.motor.w_nl_out);
  tc.verifyLessThan(w_fin, 1.00*P.motor.w_nl_out);
end
function test_elastico_transmite(tc)
  P = parametros_v1('cad', 'gear_rigido', false); pv = empaquetar_v1(P);
  e = 2*P.motor.juego;
  [tau_g, dwm, ~, ~, J_add] = motor_lado(0, 0, 0, e*P.motor.N, 0, 0, pv);
  tc.verifyEqual(tau_g, P.motor.k_g*(e - P.motor.juego/2), 'RelTol', 1e-9);
  tc.verifyLessThan(dwm, 0);
  tc.verifyEqual(J_add, 0);
  tau_g0 = motor_lado(0, 0, 0, 0.2*P.motor.juego*P.motor.N, 0, 0, pv);
  tc.verifyEqual(tau_g0, 0, 'AbsTol', 1e-12);
end
function dz = dz_vacio(z, pv, J_eq, b_w)
  ww = z(1);
  tau_g = motor_lado(12, 0, pv(18)*ww, 0, ww, 0, pv);
  dz = (tau_g - b_w*ww)/J_eq;
end
