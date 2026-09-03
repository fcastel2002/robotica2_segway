function tests = test_simulink_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_construye_y_coincide_con_ode(tc)
  P = parametros_v1('corregido'); C = disenar_control_v1(P);
  E = escenarios_v1('equilibrio_8', P); E.tf = 3;
  mdl = construir_planta(P, C, E);
  tc.verifyTrue(bdIsLoaded(mdl));
  tc.verifyTrue(isfile(fullfile(fileparts(which('construir_planta')), [mdl '.slx'])));
  Ss = simular_slx_v1(P, C, E);
  So = simular_ode_v1(P, C, E);
  tc.verifyFalse(Ss.resumen.cayo);
  tc.verifyEqual(Ss.resumen.phi_max_deg, So.resumen.phi_max_deg, 'RelTol', 0.05);
  tc.verifyEqual(Ss.X(end,2), So.X(end,2), 'AbsTol', 0.5*pi/180);
  tc.verifyEqual(size(Ss.X, 2), 16); tc.verifyEqual(size(Ss.y, 2), 16);
end
function test_variante_cad_en_simulink(tc)
  P = parametros_v1('cad'); C = disenar_control_v1(P);
  E = escenarios_v1('empujon_3N', P); E.tf = 4;
  S = simular_slx_v1(P, C, E);
  tc.verifyFalse(S.resumen.cayo);
end
