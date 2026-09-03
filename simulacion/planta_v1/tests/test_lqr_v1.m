function tests = test_lqr_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_polo_inestable(tc)
  for v = {'cad','corregido'}
    P = parametros_v1(v{1});
    for l0 = [P.din.l_min P.din.l0 P.din.l_max]
      [A, B] = modelo_lineal_v1(P, l0);
      p = max(real(eig(A)));
      tc.verifyGreaterThan(p, 5); tc.verifyLessThan(p, 13);
      tc.verifyEqual(rank(ctrb(A, B)), 4);
    end
  end
end
function test_lqr_estable_y_signo(tc)
  for v = {'cad','corregido'}
    P = parametros_v1(v{1}); C = disenar_control_v1(P);
    for i = 1:numel(C.polos_lc), tc.verifyLessThan(max(real(C.polos_lc{i})), 0); end
    K0 = C.Kf(P.din.l0);
    tc.verifyLessThan(K0(2), 0);                 % phi positivo -> tau_w = -K*X positivo
    tc.verifyLessThan(C.Kerr, 0.5*max(abs(K0)));
  end
end
function test_inercia_reflejada(tc)
  P = parametros_v1('cad'); [~, ~, M2] = modelo_lineal_v1(P, P.din.l0);
  tc.verifyGreaterThan(M2(1,1), 5);              % N=100: el rotor reflejado equivale a varios kg
  P2 = parametros_v1('corregido'); [~, ~, M2b] = modelo_lineal_v1(P2, P2.din.l0);
  tc.verifyLessThan(M2b(1,1), 2);
end
