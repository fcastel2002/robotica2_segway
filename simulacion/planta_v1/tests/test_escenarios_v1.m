function tests = test_escenarios_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_barrido_ode_corregido(tc)
  R = correr_escenarios('corregido', {'equilibrio_3','empujon_3N','pendiente_5'}, 'ode');
  tc.verifyEqual(numel(R.S), 3);
  tc.verifyEqual(height(R.T), 3);
  tc.verifyTrue(contains(R.tabla, 'equilibrio_3'));
  for i = 1:3, tc.verifyFalse(R.S{i}.resumen.cayo); end
  tc.verifyTrue(isfile(fullfile(fileparts(which('correr_escenarios')), 'resultados', 'resultados_corregido_ode.md')));
end
function test_overrides_se_aplican(tc)
  R = correr_escenarios('cad', {'bateria_baja','sin_encoder'}, 'ode');
  tc.verifyEqual(R.S{1}.P.bat.V, 9.6);
  tc.verifyFalse(R.S{2}.P.sens.encoder);
end
