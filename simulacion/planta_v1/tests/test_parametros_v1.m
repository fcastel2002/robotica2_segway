function tests = test_parametros_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_cad_cierra_y_masas(tc)
  P = parametros_v1('cad');
  tc.verifyTrue(P.cinematica.ok);
  tc.verifyEqual(P.AD, 0.140, 'AbsTol', 1e-9); tc.verifyEqual(P.AB, 0.080, 'AbsTol', 1e-9);
  tc.verifyGreaterThan(P.din.m_b, 0.70); tc.verifyLessThan(P.din.m_b, 0.80);
  tc.verifyEqual(P.din.m_w, 0.250, 'AbsTol', 1e-6);
  tc.verifyGreaterThan(P.din.l_max - P.din.l_min, 0.095); tc.verifyLessThan(P.din.l_max - P.din.l_min, 0.110);
  tc.verifyEqual(P.din.G, 0.198, 'AbsTol', 0.012);
  tc.verifyTrue(all(P.tab.dthdl < 0));
  tc.verifyTrue(issorted(P.tab.l));
end
function test_corregido_recta(tc)
  P = parametros_v1('corregido');
  tc.verifyLessThan(P.cinematica.desvio, 1.5e-3);
  P2 = parametros_v1('cad'); tc.verifyGreaterThan(P2.cinematica.desvio, 5e-3);
  tc.verifyEqual(P.motor.N, 21.3); tc.verifyTrue(P.sens.encoder);
end
function test_empaquetar(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P);
  tc.verifyEqual(numel(pv), 124); tc.verifyEqual(pv(18), 100); tc.verifyEqual(pv(61), 21);
  tc.verifyEqual(pv(62), P.din.l_min, 'AbsTol', 1e-12);
  tc.verifyEqual(pv(51:60), zeros(10,1));
end
function test_overrides(tc)
  P = parametros_v1('cad', 'V_bat', 9.6, 'gear_rigido', false);
  tc.verifyEqual(P.bat.V, 9.6); tc.verifyFalse(P.motor.gear_rigido);
  tc.verifyError(@() parametros_v1('cad','no_existe',1), ?MException);
end
function test_interp_lin(tc)
  xt = [0 1 2]'; yt = [0 10 40]';
  tc.verifyEqual(interp_lin(xt, yt, 0.5), 5, 'AbsTol', 1e-12);
  tc.verifyEqual(interp_lin(xt, yt, 1.5), 25, 'AbsTol', 1e-12);
  tc.verifyEqual(interp_lin(xt, yt, 3), 70, 'AbsTol', 1e-12);
  tc.verifyEqual(interp_lin(xt, yt, -1), -10, 'AbsTol', 1e-12);
end
