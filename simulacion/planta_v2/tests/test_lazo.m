function tests = test_lazo
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_lista_y_estructura(tc)
  P = parametros_robot('cad');
  lista = escenarios_robot('lista'); tc.verifyEqual(numel(lista), 19);
  for i = 1:numel(lista)
    E = escenarios_robot(lista{i}, P);
    tc.verifyEqual(size(E.X0), [20 1]);
    tc.verifyEqual(size(E.ref.signals.values, 2), 2); tc.verifyEqual(size(E.pert.signals.values, 2), 5);
    tc.verifyEqual(E.ref.time(end), E.tf, 'AbsTol', 1e-9);
  end
  E = escenarios_robot('escalera', P); tc.verifyEqual(E.overrides, {'piso_n', 3}); tc.verifyGreaterThan(E.tf, 10);
end
function test_equilibrio_8_recupera(tc)
  for v = {'corregido','cad'}
    P = parametros_robot(v{1}); C = disenar_lqr_robot(P);
    E = escenarios_robot('equilibrio_8', P); E.tf = 4;
    S = simular_ode(P, C, E);
    tc.verifyFalse(S.resumen.cayo, ['se cae en ' v{1}]);
    fin = S.t > 3;
    tc.verifyLessThan(max(abs(S.X(fin,3)))*180/pi, 1.5, ['no asienta en ' v{1}]);
    tc.verifyEqual(S.resumen.t_vuelo, 0);                                   % en piso plano nunca despega
    tc.verifyEqual(S.resumen.N_max_g, 1, 'AbsTol', 0.3);                    % la normal se queda cerca del peso
  end
end
function test_escalon_corre(tc)
  P = parametros_robot('corregido', 'piso_n', 1); C = disenar_lqr_robot(P);
  E = escenarios_robot('escalon_1', P);
  S = simular_ode(P, C, E);
  tc.verifyGreaterThan(S.resumen.t_vuelo, 0.05);                            % hubo caida libre
  tc.verifyGreaterThan(S.resumen.N_max_g, 2);                               % y un impacto
  tc.verifyTrue(isfield(S.resumen, 'escalones_bajados'));
end
