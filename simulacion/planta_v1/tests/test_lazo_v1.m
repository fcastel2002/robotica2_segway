function tests = test_lazo_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_lista_y_estructura(tc)
  P = parametros_v1('cad');
  lista = escenarios_v1('lista'); tc.verifyEqual(numel(lista), 16);
  for i = 1:numel(lista)
    E = escenarios_v1(lista{i}, P);
    tc.verifyEqual(size(E.X0), [16 1]);
    tc.verifyEqual(size(E.ref.signals.values, 2), 2);
    tc.verifyEqual(size(E.pert.signals.values, 2), 5);
    tc.verifyEqual(E.ref.time(end), E.tf, 'AbsTol', 1e-9);
  end
  E = escenarios_v1('escalon_10mm', P);
  tc.verifyLessThan(min(E.pert.signals.values(:,5)), -10);
end
function test_equilibrio_8_recupera(tc)
  for v = {'corregido','cad'}
    P = parametros_v1(v{1}); C = disenar_control_v1(P);
    E = escenarios_v1('equilibrio_8', P); E.tf = 4;
    S = simular_ode_v1(P, C, E);
    tc.verifyFalse(S.resumen.cayo, ['se cae en ' v{1}]);
    fin = S.t > 3;
    tc.verifyLessThan(max(abs(S.X(fin,2)))*180/pi, 1.0, ['no asienta en ' v{1}]);
  end
end
function test_agachar_llega(tc)
  P = parametros_v1('corregido'); C = disenar_control_v1(P);
  E = escenarios_v1('agachar', P);
  S = simular_ode_v1(P, C, E);
  tc.verifyFalse(S.resumen.cayo);
  i = find(S.t > 2.9, 1); tc.verifyEqual(S.X(i,3), P.din.l_min*1.05, 'AbsTol', 0.005);
  tc.verifyEqual(S.X(end,3), P.din.l_max*0.97, 'AbsTol', 0.005);
end
