function tests = test_dinamica_pata_simulink
  tests = functiontests(localfunctions);
end

function setupOnce(tc)
  carpeta = fileparts(mfilename('fullpath'));
  tc.TestData.banco = fileparts(carpeta);
  tc.TestData.repo = fileparts(fileparts(tc.TestData.banco));
  addpath(tc.TestData.banco);
  addpath(fullfile(tc.TestData.banco, 'interno'));
  addpath(fullfile(tc.TestData.repo, 'modelado', 'dinamica'));
end

function teardownOnce(~)
  if bdIsLoaded('dinamica_pata_simulink'), close_system('dinamica_pata_simulink', 0); end
end

function test_construccion_reproducible(tc)
  carpeta_temporal = tempname;
  modelo_qa = 'dinamica_pata_simulink_qa';
  mkdir(carpeta_temporal);
  limpieza_temporal = onCleanup(@() limpiar_temporal(carpeta_temporal, modelo_qa)); %#ok<NASGU>
  archivo = construir_dinamica_pata(carpeta_temporal, modelo_qa);
  tc.verifyTrue(isfile(archivo));
  load_system(archivo);
  luts = find_system(modelo_qa, 'LookUnderMasks', 'all', ...
    'BlockType', 'Lookup_n-D');
  tc.verifyEqual(numel(luts), 6);
  matlabFunctions = find_system(modelo_qa, 'LookUnderMasks', 'all', ...
    'MaskType', 'MATLAB Function');
  tc.verifyEmpty(matlabFunctions);
  [par_pata, p] = parametros_simulink_dinamica_pata();
  E = escenarios_dinamica_pata('estatico_25', p);
  sim_pata = struct('theta0', E.theta0, 'dtheta0', E.dtheta0, 't_final', E.t_final);
  asignar = {'par_pata',par_pata;'sim_pata',sim_pata; ...
    'theta_ref_ext',timeseries(E.theta_ref,E.t); ...
    'tau_pert_ext',timeseries(E.tau_perturbacion,E.t); ...
    'normal_ext',timeseries(E.normal,E.t);'caso_ext',timeseries(E.caso_serie,E.t)};
  for i = 1:size(asignar,1), assignin('base', asignar{i,1}, asignar{i,2}); end
  limpieza = onCleanup(@() evalin('base', ...
    'clear par_pata sim_pata theta_ref_ext tau_pert_ext normal_ext caso_ext'));
  set_param(modelo_qa, 'SimulationCommand', 'update');
  close_system(modelo_qa, 0);
end

function test_tres_casos_contra_ode(tc)
  casos = {'banco_validacion','parado_validacion','aire_validacion'};
  for i = 1:numel(casos)
    R = simular_dinamica_pata(casos{i});
    tc.verifyLessThan(R.error.theta_max, 1e-5, casos{i});
    tc.verifyLessThan(R.error.dtheta_max, 1e-4, casos{i});
    tc.verifyGreaterThanOrEqual(min(R.Ieq), 0);
  end
end

function test_estatico_y_senales(tc)
  R = simular_dinamica_pata('estatico_25');
  p = parametros_dinamica_pata();
  T = terminos_dinamica_pata(R.theta(1), p, 'parado');
  tc.verifyTrue(all(isfinite([R.theta; R.dtheta; R.ddtheta; R.tau; R.normal])));
  tc.verifyLessThanOrEqual(max(abs(R.tau)), 2.4+1e-12);
  tc.verifyEqual(size(R.theta), size(R.t));
  tc.verifyEqual(R.Ieq(1), T.Ieq, 'AbsTol', 1e-9);
  tc.verifyEqual(R.Vprima(1), T.dV, 'AbsTol', 1e-9);
end

function test_energia_y_sensibilidad_solver(tc)
  A = analizar_energia_solver();
  tc.verifyGreaterThan(A.metricas.theta_min, deg2rad(10));
  tc.verifyLessThan(A.metricas.theta_max, deg2rad(40));
  tc.verifyLessThan(A.metricas.deriva_energia_rel_ref, 1e-6);
  tc.verifyLessThan(A.metricas.residuo_disipativo_rel, 1e-5);
  tc.verifyLessThan(A.metricas.delta_estado_ode45, 1e-5);
  tc.verifyLessThan(A.metricas.delta_estado_ode23, 1e-4);
end

function limpiar_temporal(carpeta, modelo)
  if bdIsLoaded(modelo)
    close_system(modelo, 0);
  end
  if isfolder(carpeta), rmdir(carpeta, 's'); end
end
