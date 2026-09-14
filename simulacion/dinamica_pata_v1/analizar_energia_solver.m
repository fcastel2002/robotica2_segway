function A = analizar_energia_solver()
%ANALIZAR_ENERGIA_SOLVER Conservación, disipación y sensibilidad numérica.
%   Usa SimulationInput para no alterar la configuración guardada del modelo.
  carpeta = fileparts(mfilename('fullpath'));
  raiz = fileparts(fileparts(carpeta));
  addpath(carpeta);
  addpath(fullfile(raiz, 'modelado', 'dinamica'));
  archivo = fullfile(carpeta, 'dinamica_pata_simulink.slx');
  if ~isfile(archivo), construir_dinamica_pata(); end

  [par_base, p_base] = parametros_simulink_dinamica_pata();
  t_entrada = (0:0.002:0.4)';
  theta0 = deg2rad(25);
  dtheta0 = 0.4;
  configuraciones = struct( ...
    'nombre', {'ode45_ref','ode45_nominal','ode23_nominal'}, ...
    'solver', {'ode45','ode45','ode23'}, ...
    'max_step', {1e-4,1e-3,5e-4}, ...
    'rel_tol', {1e-10,1e-9,1e-8}, ...
    'abs_tol', {1e-12,1e-11,1e-10});

  previo = cd(carpeta);
  limpieza = onCleanup(@() cd(previo));
  corridas_celda = cell(numel(configuraciones), 1);
  for i = 1:numel(configuraciones)
    corridas_celda{i} = correr(configuraciones(i), par_base, p_base, ...
      t_entrada, theta0, dtheta0, 0);
  end
  corridas = vertcat(corridas_celda{:});
  estado_ref = [corridas(1).theta(end), corridas(1).dtheta(end)];
  for i = 1:numel(corridas)
    corridas(i).delta_estado_ref = norm( ...
      [corridas(i).theta(end), corridas(i).dtheta(end)]-estado_ref, inf);
  end

  b_ensayo = 0.02;
  disipada = correr(configuraciones(1), par_base, p_base, ...
    t_entrada, theta0, dtheta0, b_ensayo);
  potencia_disipada = b_ensayo*disipada.dtheta.^2;
  balance_disipativo = disipada.energia.total-disipada.energia.total(1) ...
    + cumtrapz(disipada.t, potencia_disipada);
  disipada.residuo_balance_rel = max(abs(balance_disipativo)) ...
    / max(abs(disipada.energia.total(1)), 1e-12);

  A.configuraciones = configuraciones;
  A.corridas_conservativas = corridas;
  A.corrida_disipativa = disipada;
  A.metricas.deriva_energia_rel_ref = corridas(1).deriva_energia_rel;
  A.metricas.residuo_disipativo_rel = disipada.residuo_balance_rel;
  A.metricas.delta_estado_ode45 = corridas(2).delta_estado_ref;
  A.metricas.delta_estado_ode23 = corridas(3).delta_estado_ref;
  A.metricas.theta_min = min(corridas(1).theta);
  A.metricas.theta_max = max(corridas(1).theta);
end

function R = correr(C, par_pata, p, t_entrada, theta0, dtheta0, b)
  par_pata.Kp = 0;
  par_pata.Kd = 0;
  par_pata.b = b;
  par_pata.k_tope = 0;
  par_pata.c_tope = 0;
  p.Kp = 0;
  p.Kd = 0;
  p.b = b;
  p.tope.habilitado = false;
  sim_pata = struct('theta0', theta0, 'dtheta0', dtheta0, ...
    't_final', t_entrada(end));
  cero = zeros(size(t_entrada));
  theta_ref_ext = timeseries(theta0*ones(size(t_entrada)), t_entrada);
  tau_pert_ext = timeseries(cero, t_entrada);
  normal_ext = timeseries(cero, t_entrada);
  caso_ext = timeseries(3*ones(size(t_entrada)), t_entrada);

  in = Simulink.SimulationInput('dinamica_pata_simulink');
  in = in.setModelParameter('StopTime', num2str(t_entrada(end), 17), ...
    'Solver', C.solver, 'MaxStep', num2str(C.max_step, 17), ...
    'RelTol', num2str(C.rel_tol, 17), 'AbsTol', num2str(C.abs_tol, 17));
  in = in.setVariable('par_pata', par_pata);
  in = in.setVariable('sim_pata', sim_pata);
  in = in.setVariable('theta_ref_ext', theta_ref_ext);
  in = in.setVariable('tau_pert_ext', tau_pert_ext);
  in = in.setVariable('normal_ext', normal_ext);
  in = in.setVariable('caso_ext', caso_ext);
  out = sim(in);

  R.nombre = C.nombre;
  R.t = out.theta_slx.Time;
  R.theta = out.theta_slx.Data;
  R.dtheta = out.dtheta_slx.Data;
  R.energia = energia_dinamica_pata(R.theta, R.dtheta, p, 'aire');
  R.deriva_energia_rel = max(abs(R.energia.total-R.energia.total(1))) ...
    / max(abs(R.energia.total(1)), 1e-12);
end
