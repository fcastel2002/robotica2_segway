function [resumen, corridas, archivo] = correr_escenarios_dinamica_pata()
%CORRER_ESCENARIOS_DINAMICA_PATA Ejecuta y guarda el primer barrido baseline.
  nombres = {'estatico_25','banco_nominal','parado_nominal','aire_nominal', ...
    'banco_validacion','parado_validacion','aire_validacion'};
  corridas = cell(size(nombres));
  filas = cell(numel(nombres), 9);
  for i = 1:numel(nombres)
    R = simular_dinamica_pata(nombres{i});
    corridas{i} = R;
    filas(i,:) = {R.nombre, rad2deg(R.metricas.theta_min), rad2deg(R.metricas.theta_max), ...
      R.metricas.tau_pico, R.metricas.tau_pico/0.0981, R.metricas.normal_min, ...
      R.metricas.normal_max, R.error.theta_max, R.error.dtheta_max};
  end
  resumen = cell2table(filas, 'VariableNames', {'escenario','theta_min_deg','theta_max_deg', ...
    'tau_pico_Nm','tau_pico_kgcm','normal_min_N','normal_max_N','error_theta_rad','error_dtheta_rad_s'});
  carpeta = fullfile(fileparts(mfilename('fullpath')), 'resultados');
  if ~isfolder(carpeta), mkdir(carpeta); end
  archivo = fullfile(carpeta, 'corridas_baseline_2026-09-14.mat');
  metadata = struct('fecha', '2026-09-14', 'matlab', version, ...
    'modelo', 'dinamica_pata_simulink.slx', 'variante', 'corregido');
  save(archivo, 'resumen', 'corridas', 'metadata');
  disp(resumen);
end
