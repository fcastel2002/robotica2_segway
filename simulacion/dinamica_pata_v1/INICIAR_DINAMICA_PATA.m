function varargout = INICIAR_DINAMICA_PATA(accion, escenario)
%INICIAR_DINAMICA_PATA Punto de entrada único del banco reducido.
%   INICIAR_DINAMICA_PATA abre el modelo con 'parado_nominal' listo para Run.
%   INICIAR_DINAMICA_PATA('simular','parado_nominal') ejecuta un escenario.
%   INICIAR_DINAMICA_PATA('qa') ejecuta las 12 pruebas.
%   Acciones: abrir, simular, qa, barrido, energia, reconstruir, ayuda.
  if nargin < 1 || isempty(accion), accion = 'abrir'; end
  if nargin < 2 || isempty(escenario), escenario = 'parado_nominal'; end

  carpeta_banco = fileparts(mfilename('fullpath'));
  repo = fileparts(fileparts(carpeta_banco));
  carpeta_interna = fullfile(carpeta_banco, 'interno');
  addpath(carpeta_banco);
  addpath(carpeta_interna);
  addpath(fullfile(repo, 'modelado', 'cinematica'));
  addpath(fullfile(repo, 'modelado', 'dinamica'));
  addpath(fullfile(repo, 'simulacion', 'planta_v2'));
  configurar_cache();

  archivo_modelo = fullfile(carpeta_banco, 'dinamica_pata_simulink.slx');
  accion = lower(char(accion));
  resultado = [];
  switch accion
    case 'abrir'
      if ~isfile(archivo_modelo), construir_dinamica_pata(carpeta_banco); end
      preparar_en_base(escenario);
      open_system(archivo_modelo);
      resultado = struct('modelo', archivo_modelo, 'escenario', char(escenario));
      fprintf('Modelo abierto con "%s" listo para ejecutar con Run.\n', char(escenario));

    case 'simular'
      if ~isfile(archivo_modelo), construir_dinamica_pata(carpeta_banco); end
      open_system(archivo_modelo);
      resultado = simular_dinamica_pata(escenario);
      fprintf('Escenario "%s" completado. Revise R.metricas y R.error.\n', char(escenario));

    case 'qa'
      test_core = fullfile(repo, 'modelado', 'dinamica', 'tests', ...
        'test_dinamica_pata.m');
      test_slx = fullfile(carpeta_banco, 'tests', ...
        'test_dinamica_pata_simulink.m');
      r1 = runtests(test_core);
      r2 = runtests(test_slx);
      resultado = [r1(:); r2(:)];
      disp(table(string({resultado.Name})', [resultado.Passed]', ...
        [resultado.Duration]', 'VariableNames', {'Prueba','Paso','Duracion_s'}));
      assert(all([resultado.Passed]), 'INICIAR_DINAMICA_PATA:QA', ...
        'Hay pruebas fallidas en el banco reducido.');
      fprintf('QA completado: %d/%d pruebas aprobadas.\n', ...
        sum([resultado.Passed]), numel(resultado));

    case 'barrido'
      [resumen, corridas, archivo] = correr_escenarios_dinamica_pata();
      resultado = struct('resumen', resumen, 'corridas', {corridas}, ...
        'archivo', archivo);

    case 'energia'
      resultado = analizar_energia_solver();
      disp(resultado.metricas);

    case 'reconstruir'
      archivo_modelo = construir_dinamica_pata(carpeta_banco);
      preparar_en_base(escenario);
      open_system(archivo_modelo);
      resultado = struct('modelo', archivo_modelo, 'escenario', char(escenario));
      fprintf('Modelo reconstruido y abierto con "%s".\n', char(escenario));

    case 'ayuda'
      mostrar_ayuda();

    otherwise
      error('INICIAR_DINAMICA_PATA:Accion', ...
        'Acción "%s" desconocida. Use abrir, simular, qa, barrido, energia, reconstruir o ayuda.', ...
        accion);
  end

  if nargout > 0, varargout{1} = resultado; end
end

function preparar_en_base(nombre)
  [par_pata, p] = parametros_simulink_dinamica_pata();
  E = escenarios_dinamica_pata(nombre, p);
  sim_pata = struct('theta0', E.theta0, 'dtheta0', E.dtheta0, ...
    't_final', E.t_final);
  assignin('base', 'par_pata', par_pata);
  assignin('base', 'sim_pata', sim_pata);
  assignin('base', 'theta_ref_ext', timeseries(E.theta_ref, E.t));
  assignin('base', 'tau_pert_ext', timeseries(E.tau_perturbacion, E.t));
  assignin('base', 'normal_ext', timeseries(E.normal, E.t));
  assignin('base', 'caso_ext', timeseries(E.caso_serie, E.t));
end

function mostrar_ayuda()
  fprintf(['\nBanco reducido de dinamica de pata\n' ...
    '  INICIAR_DINAMICA_PATA                         Abrir parado_nominal\n' ...
    '  R = INICIAR_DINAMICA_PATA(''simular'', caso) Ejecutar un escenario\n' ...
    '  r = INICIAR_DINAMICA_PATA(''qa'')            Ejecutar 12 pruebas\n' ...
    '  B = INICIAR_DINAMICA_PATA(''barrido'')       Ejecutar siete escenarios\n' ...
    '  A = INICIAR_DINAMICA_PATA(''energia'')       Analizar energia y solver\n' ...
    '  INICIAR_DINAMICA_PATA(''reconstruir'')       Regenerar el SLX\n\n']);
end

function configurar_cache()
  raiz_cache = fullfile(tempdir, 'robotica2_segway_simulink');
  carpeta_cache = fullfile(raiz_cache, 'cache');
  carpeta_codegen = fullfile(raiz_cache, 'codegen');
  Simulink.fileGenControl('set', 'CacheFolder', carpeta_cache, ...
    'CodeGenFolder', carpeta_codegen, 'createDir', true);
end
