function tests = test_simulink
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_construye_y_coincide_con_ode(tc)
  P = parametros_robot('corregido'); C = disenar_lqr_robot(P);
  E = escenarios_robot('equilibrio_8', P); E.tf = 3;
  mdl = construir_robot_slx(P, C, E);
  tc.verifyTrue(bdIsLoaded(mdl));
  bloques = find_system(mdl, 'SearchDepth', 1, 'BlockType', 'SubSystem');
  tc.verifyEqual(numel(bloques), 6);                                    % Escenario, Controlador, Robot, Sensores, Registro, Graficos
  Ss = simular_slx(P, C, E);
  So = simular_ode(P, C, E);
  tc.verifyFalse(Ss.resumen.cayo);
  tc.verifyEqual(Ss.resumen.phi_max_deg, So.resumen.phi_max_deg, 'RelTol', 0.05);
  tc.verifyEqual(Ss.X(end,3), So.X(end,3), 'AbsTol', 0.5*pi/180);
  tc.verifyEqual(size(Ss.X, 2), 20); tc.verifyEqual(size(Ss.y, 2), 18); tc.verifyEqual(size(Ss.est, 2), 7);
end
function test_senales_con_nombre(tc)
  mdl = 'robot_segway';
  if ~bdIsLoaded(mdl), load_system(fullfile(fileparts(which('construir_robot_slx')), [mdl '.slx'])); end
  for nom = {'comandos','medidas','estados','referencias','perturbaciones','estimaciones'}
    h = find_system(mdl, 'FindAll', 'on', 'SearchDepth', 1, 'Type', 'line', 'Name', nom{1});
    tc.verifyNotEmpty(h, ['falta la senal ' nom{1}]);
  end
  h = find_system([mdl '/Robot'], 'FindAll', 'on', 'Type', 'line', 'Name', 'inclinacion');
  tc.verifyNotEmpty(h);
  tc.verifyEmpty(find_system(mdl, 'FindAll', 'on', 'Type', 'line', 'Name', 'pv'));
end
