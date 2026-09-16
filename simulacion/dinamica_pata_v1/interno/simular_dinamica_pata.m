function R = simular_dinamica_pata(nombre, varargin)
%SIMULAR_DINAMICA_PATA Ejecuta Simulink y el oráculo ODE con las mismas entradas.
  ip = inputParser;
  addRequired(ip, 'nombre', @(x) ischar(x) || isstring(x));
  addParameter(ip, 'variante', 'corregido', @(x) ischar(x) || isstring(x));
  addParameter(ip, 'reconstruir', false, @islogical);
  parse(ip, nombre, varargin{:});

  carpeta_interna = fileparts(mfilename('fullpath'));
  carpeta = fileparts(carpeta_interna);
  raiz = fileparts(fileparts(carpeta));
  addpath(carpeta_interna);
  addpath(fullfile(raiz, 'modelado', 'dinamica'));
  [par_pata, p] = parametros_simulink_dinamica_pata(ip.Results.variante);
  E = escenarios_dinamica_pata(nombre, p);
  archivo = fullfile(carpeta, 'dinamica_pata_simulink.slx');
  if ip.Results.reconstruir || ~isfile(archivo), construir_dinamica_pata(carpeta); end

  theta_ref_ext = timeseries(E.theta_ref, E.t);
  tau_pert_ext = timeseries(E.tau_perturbacion, E.t);
  normal_ext = timeseries(E.normal, E.t);
  caso_ext = timeseries(E.caso_serie, E.t);
  sim_pata = struct('theta0', E.theta0, 'dtheta0', E.dtheta0, 't_final', E.t_final);
  in = Simulink.SimulationInput('dinamica_pata_simulink');
  in = in.setModelParameter('StopTime', num2str(E.t_final, 17), ...
    'ReturnWorkspaceOutputs', 'on');
  in = in.setVariable('par_pata', par_pata);
  in = in.setVariable('sim_pata', sim_pata);
  in = in.setVariable('theta_ref_ext', theta_ref_ext);
  in = in.setVariable('tau_pert_ext', tau_pert_ext);
  in = in.setVariable('normal_ext', normal_ext);
  in = in.setVariable('caso_ext', caso_ext);
  previo = cd(carpeta);
  limpieza = onCleanup(@() cd(previo));
  out = sim(in);

  R.nombre = E.nombre;
  R.variante = p.variante;
  R.t = out.theta_slx.Time;
  R.theta = out.theta_slx.Data;
  R.dtheta = out.dtheta_slx.Data;
  R.ddtheta = out.ddtheta_slx.Data;
  R.tau = out.tau_slx.Data;
  R.Ieq = out.Ieq_slx.Data;
  R.Vprima = out.Vprima_slx.Data;
  R.normal = out.normal_estimada_slx.Data;
  R.contacto_valido = logical(out.contacto_valido_slx.Data);
  R.tau_tope = out.tau_tope_slx.Data;
  R.theta_ref = interp1(E.t, E.theta_ref, R.t, 'linear', 'extrap');
  R.caso = E.caso;
  R.limites = struct('theta_min', p.theta_min, 'theta_max', p.theta_max, ...
    'tau_max', p.tau_max);
  R.ode = referencia_ode(E, p, R.t);
  R.error.theta_max = max(abs(R.theta-R.ode.theta));
  R.error.dtheta_max = max(abs(R.dtheta-R.ode.dtheta));
  normal_valida = R.normal(isfinite(R.normal));
  if isempty(normal_valida), normal_valida = NaN; end
  R.metricas = struct('tau_pico', max(abs(R.tau)), ...
    'normal_min', min(normal_valida), 'normal_max', max(normal_valida), ...
    'theta_min', min(R.theta), 'theta_max', max(R.theta));
end

function O = referencia_ode(E, p, tiempos)
  casos = {'banco','parado','aire'};
  caso = casos{E.caso};
  f = @(t,x) rhs(t, x, E, p, caso);
  opciones = odeset('RelTol', 1e-10, 'AbsTol', 1e-12, 'MaxStep', 0.001);
  [~, x] = ode45(f, tiempos, [E.theta0; E.dtheta0], opciones);
  O.theta = x(:,1);
  O.dtheta = x(:,2);
end

function dx = rhs(t, x, E, p, caso)
  ref = interp1(E.t, E.theta_ref, t, 'linear', 'extrap');
  perturbacion = interp1(E.t, E.tau_perturbacion, t, 'linear', 'extrap');
  N = interp1(E.t, E.normal, t, 'linear', 'extrap');
  tau_pd = p.Kp*(ref-x(1))-p.Kd*x(2);
  limite = p.tau_max;
  if tau_pd*x(2) > 0
    limite = p.tau_max*max(0, 1-abs(x(2))/p.w_nl);
  end
  tau = min(max(tau_pd, -limite), limite) + perturbacion;
  dx = estado_dinamica_pata(t, x, tau, N, p, caso);
end
