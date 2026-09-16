function salida = generar_figuras_dinamica_pata(datos, varargin)
%GENERAR_FIGURAS_DINAMICA_PATA Exporta dashboards de simulación.
%   Sin argumentos toma las señales To Workspace del último Run manual.
  if nargin < 1 || isempty(datos), datos = capturar_desde_base(); end
  ip = inputParser;
  addParameter(ip, 'mostrar', true, @islogical);
  parse(ip, varargin{:});

  carpeta_banco = fileparts(fileparts(mfilename('fullpath')));
  carpeta_figuras = fullfile(carpeta_banco, 'resultados', 'figuras');
  if ~isfolder(carpeta_figuras), mkdir(carpeta_figuras); end

  if isstruct(datos) && isfield(datos, 'corridas_conservativas')
    salida = graficar_energia(datos, carpeta_figuras, ip.Results.mostrar);
  elseif isstruct(datos) && isfield(datos, 'corridas')
    corridas = datos.corridas;
    salida = graficar_barrido(corridas, carpeta_figuras, ip.Results.mostrar);
  elseif iscell(datos)
    salida = graficar_barrido(datos, carpeta_figuras, ip.Results.mostrar);
  else
    salida = graficar_escenario(datos, carpeta_figuras, ip.Results.mostrar);
  end
end

function salida = graficar_energia(A, carpeta, mostrar)
  visibilidad = 'off';
  if mostrar, visibilidad = 'on'; end
  corridas = A.corridas_conservativas;
  disipada = A.corrida_disipativa;
  colores = lines(numel(corridas));
  etiqueta = 'DinamicaPataEnergia';
  cerrar_figura_previa(etiqueta);
  fig = figure('Name', 'Validación energética', 'Tag', etiqueta, ...
    'NumberTitle', 'off', 'Color', 'w', 'Position', [80 120 1500 650], ...
    'Visible', visibilidad);
  mosaico = tiledlayout(fig, 1, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

  nexttile(mosaico);
  for i = 1:numel(corridas)
    energia = corridas(i).energia.total;
    deriva = max(abs((energia-energia(1))/max(abs(energia(1)), 1e-12)), eps);
    semilogy(corridas(i).t, deriva, 'LineWidth', 1.5, ...
      'Color', colores(i,:), 'DisplayName', strrep(corridas(i).nombre, '_', ' '));
    hold on
  end
  xlabel('t [s]'); ylabel('|E(t)-E(0)|/|E(0)|');
  title('Conservación de energía'); grid on; legend('Location', 'best');

  nexttile(mosaico);
  energia_d = disipada.energia.total;
  perdida = energia_d-energia_d(1);
  trabajo_disipado = -cumtrapz(disipada.t, 0.02*disipada.dtheta.^2);
  plot(disipada.t, perdida, 'LineWidth', 1.7, 'DisplayName', 'E(t)-E(0)'); hold on
  plot(disipada.t, trabajo_disipado, '--', 'LineWidth', 1.5, ...
    'DisplayName', '-\int b\omega^2 dt');
  xlabel('t [s]'); ylabel('Energía [J]'); title('Balance con amortiguamiento');
  grid on; legend('Location', 'best');

  sensibilidad = max(A.metricas.delta_estado_ode45, A.metricas.delta_estado_ode23);
  titulo = sprintf(['Validación energética | deriva %.2e | residuo %.2e | ' ...
    'sensibilidad solver %.2e'], A.metricas.deriva_energia_rel_ref, ...
    A.metricas.residuo_disipativo_rel, sensibilidad);
  title(mosaico, titulo, ...
    'FontWeight', 'bold', 'FontSize', 16);
  salida = exportar(fig, fullfile(carpeta, 'energia_solver'));
  if ~mostrar, close(fig); end
end

function salida = graficar_escenario(R, carpeta, mostrar)
  visibilidad = 'off';
  if mostrar, visibilidad = 'on'; end
  nombre = char(R.nombre);
  etiqueta = 'DinamicaPataEscenario';
  cerrar_figura_previa(etiqueta);
  fig = figure('Name', ['Dinámica de pata — ' nombre], 'Tag', etiqueta, ...
    'NumberTitle', 'off', ...
    'Color', 'w', 'Position', [80 80 1500 850], 'Visible', visibilidad);
  mosaico = tiledlayout(fig, 2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

  t = R.t(:);
  theta_deg = rad2deg(R.theta(:));
  nexttile(mosaico);
  plot(t, theta_deg, 'LineWidth', 1.8, 'DisplayName', 'Simulink'); hold on
  if isfield(R, 'theta_ref') && ~isempty(R.theta_ref)
    plot(t, rad2deg(R.theta_ref(:)), '--', 'LineWidth', 1.3, 'DisplayName', 'Referencia');
  end
  if isfield(R, 'ode') && isstruct(R.ode) && isfield(R.ode, 'theta')
    plot(t, rad2deg(R.ode.theta(:)), ':', 'LineWidth', 1.5, 'DisplayName', 'ODE');
  end
  if isfield(R, 'limites')
    yline(rad2deg(R.limites.theta_min), '--', 'Tope inferior', 'HandleVisibility', 'off');
    yline(rad2deg(R.limites.theta_max), '--', 'Tope superior', 'HandleVisibility', 'off');
  end
  ylabel('\theta [deg]'); xlabel('t [s]'); title('Seguimiento angular');
  grid on; legend('Location', 'best');

  nexttile(mosaico);
  plot(t, R.tau(:)/0.0981, 'LineWidth', 1.7, 'DisplayName', 'Servo'); hold on
  plot(t, R.tau_tope(:)/0.0981, '--', 'LineWidth', 1.2, 'DisplayName', 'Topes');
  if isfield(R, 'limites')
    limite_kgcm = R.limites.tau_max/0.0981;
    yline(limite_kgcm, '--r', 'Límite servo', 'HandleVisibility', 'off');
    yline(-limite_kgcm, '--r', 'HandleVisibility', 'off');
  end
  ylabel('\tau [kg cm]'); xlabel('t [s]'); title('Esfuerzo del actuador');
  grid on; legend('Location', 'best');

  nexttile(mosaico);
  normal = R.normal(:);
  if any(isfinite(normal))
    yyaxis left
    plot(t, normal, 'LineWidth', 1.6); ylabel('Normal [N]');
    yyaxis right
    stairs(t, double(R.contacto_valido(:)), 'LineWidth', 1.1);
    ylabel('Contacto válido'); ylim([-0.05 1.05]);
    title('Contacto con el suelo'); xlabel('t [s]'); grid on
  else
    axis off
    text(0.5, 0.58, 'Normal no aplicable', 'HorizontalAlignment', 'center', ...
      'FontSize', 14, 'FontWeight', 'bold');
    text(0.5, 0.42, 'El caso seleccionado no impone apoyo en el suelo', ...
      'HorizontalAlignment', 'center', 'FontSize', 11);
  end

  nexttile(mosaico);
  tau_pico = max(abs(R.tau))/0.0981;
  normal_valida = normal(isfinite(normal));
  normal_texto = 'N/A';
  if ~isempty(normal_valida), normal_texto = sprintf('%.3f N', min(normal_valida)); end
  uso_servo = 'N/A';
  if isfield(R, 'limites')
    uso_servo = sprintf('%.1f %%', 100*max(abs(R.tau))/R.limites.tau_max);
  end
  error_texto = 'No calculado en Run manual';
  if isfield(R, 'error')
    error_texto = sprintf('e_theta %.2e rad | e_dtheta %.2e rad/s', ...
      R.error.theta_max, R.error.dtheta_max);
  end
  axis off
  title('Indicadores útiles');
  texto = sprintf(['Par pico: %.2f kg cm\nUso del servo: %s\n' ...
    'Rango angular: %.2f a %.2f deg\nNormal mínima: %s\n' ...
    'Simulink vs ODE: %s'], tau_pico, uso_servo, min(theta_deg), ...
    max(theta_deg), normal_texto, error_texto);
  text(0.05, 0.8, texto, 'Units', 'normalized', 'FontSize', 13, ...
    'VerticalAlignment', 'top', 'Interpreter', 'none');

  title(mosaico, strrep(nombre, '_', ' '), 'FontWeight', 'bold', 'FontSize', 16);
  salida = exportar(fig, fullfile(carpeta, 'ultimo_run'));
  if ~mostrar, close(fig); end
end

function salida = graficar_barrido(corridas, carpeta, mostrar)
  n = numel(corridas);
  nombres = cellfun(@(R) strrep(R.nombre, '_', ' '), corridas, 'UniformOutput', false);
  tau_pico = cellfun(@(R) max(abs(R.tau))/0.0981, corridas);
  theta_min = cellfun(@(R) rad2deg(min(R.theta)), corridas);
  theta_max = cellfun(@(R) rad2deg(max(R.theta)), corridas);
  normal_min = nan(1, n); normal_max = nan(1, n);
  for i = 1:n
    normal = corridas{i}.normal(isfinite(corridas{i}.normal));
    if ~isempty(normal)
      normal_min(i) = min(normal);
      normal_max(i) = max(normal);
    end
  end

  visibilidad = 'off';
  if mostrar, visibilidad = 'on'; end
  etiqueta = 'DinamicaPataBarrido';
  cerrar_figura_previa(etiqueta);
  fig = figure('Name', 'Resumen comparativo — dinámica de pata', 'Tag', etiqueta, ...
    'NumberTitle', 'off', 'Color', 'w', 'Position', [40 140 1750 620], ...
    'Visible', visibilidad);
  mosaico = tiledlayout(fig, 1, 3, 'TileSpacing', 'compact', 'Padding', 'compact');
  x = 1:n;

  nexttile(mosaico);
  bar(x, tau_pico, 'FaceColor', [0.15 0.45 0.75]); hold on
  limite = corridas{1}.limites.tau_max/0.0981;
  yline(limite, '--r', sprintf('Límite %.1f kg cm', limite), 'LineWidth', 1.3);
  configurar_eje_categorico(x, nombres); ylabel('Par pico [kg cm]');
  title('Uso del servo'); grid on

  nexttile(mosaico);
  centro = (theta_min+theta_max)/2;
  errorbar(x, centro, centro-theta_min, theta_max-centro, 'o', ...
    'LineWidth', 1.7, 'MarkerFaceColor', [0.2 0.6 0.35]); hold on
  yline(10, '--r', 'Tope inferior'); yline(40, '--r', 'Tope superior');
  configurar_eje_categorico(x, nombres); ylabel('Rango de \theta [deg]');
  title('Carrera angular utilizada'); grid on

  nexttile(mosaico);
  bar(x, [normal_min(:) normal_max(:)], 'grouped');
  yline(0, '--r', 'Pérdida de contacto');
  configurar_eje_categorico(x, nombres); ylabel('Normal [N]');
  title('Margen de contacto (solo casos aplicables)'); grid on
  legend('Mínima', 'Máxima', 'Location', 'best');

  title(mosaico, 'Banco reducido — resumen para revisión del equipo', ...
    'FontWeight', 'bold', 'FontSize', 16);
  salida.resumen = exportar(fig, fullfile(carpeta, 'resumen_equipo'));
  if ~mostrar, close(fig); end
end

function configurar_eje_categorico(x, nombres)
  set(gca, 'XTick', x, 'XTickLabel', nombres, 'XTickLabelRotation', 24);
  xlim([0.4 numel(x)+0.6]);
end

function cerrar_figura_previa(etiqueta)
  previas = findall(groot, 'Type', 'figure', 'Tag', etiqueta);
  if ~isempty(previas), delete(previas); end
end

function salida = exportar(fig, base)
  salida.png = [base '.png'];
  ejes = findall(fig, 'Type', 'axes');
  for i = 1:numel(ejes)
    ejes(i).Toolbar.Visible = 'off';
  end
  exportgraphics(fig, salida.png, 'Resolution', 220);
end

function R = capturar_desde_base()
  requeridas = {'theta_slx','dtheta_slx','ddtheta_slx','tau_slx','Ieq_slx', ...
    'Vprima_slx','normal_estimada_slx','contacto_valido_slx','tau_tope_slx'};
  for i = 1:numel(requeridas)
    if ~salida_disponible(requeridas{i})
      error('generar_figuras_dinamica_pata:SinDatos', ...
        'No existe %s. Ejecute primero el modelo mediante INICIAR_DINAMICA_PATA.', requeridas{i});
    end
  end
  theta = leer_salida('theta_slx');
  dtheta = leer_salida('dtheta_slx');
  ddtheta = leer_salida('ddtheta_slx');
  tau = leer_salida('tau_slx');
  Ieq = leer_salida('Ieq_slx');
  Vprima = leer_salida('Vprima_slx');
  normal = leer_salida('normal_estimada_slx');
  contacto = leer_salida('contacto_valido_slx');
  tau_tope = leer_salida('tau_tope_slx');
  R.t = theta.Time;
  R.theta = theta.Data;
  R.dtheta = dtheta.Data;
  R.ddtheta = ddtheta.Data;
  R.tau = tau.Data;
  R.Ieq = Ieq.Data;
  R.Vprima = Vprima.Data;
  R.normal = normal.Data;
  R.contacto_valido = logical(contacto.Data);
  R.tau_tope = tau_tope.Data;
  R.nombre = 'run_manual';
  if evalin('base', 'exist(''escenario_pata_actual'',''var'')') == 1
    R.nombre = evalin('base', 'escenario_pata_actual');
  end
  if evalin('base', 'exist(''theta_ref_ext'',''var'')') == 1
    ref = evalin('base', 'theta_ref_ext');
    R.theta_ref = interp1(ref.Time, ref.Data, R.t, 'linear', 'extrap');
  end
  par_pata = evalin('base', 'par_pata');
  R.limites = struct('theta_min', par_pata.theta_min, ...
    'theta_max', par_pata.theta_max, 'tau_max', par_pata.tau_max);
end

function disponible = salida_disponible(nombre)
  disponible = evalin('base', sprintf('exist(''%s'',''var'')', nombre)) == 1;
  if disponible, return; end
  if evalin('base', 'exist(''out'',''var'')') ~= 1, return; end
  out = evalin('base', 'out');
  disponible = isa(out, 'Simulink.SimulationOutput') && any(strcmp(who(out), nombre));
end

function valor = leer_salida(nombre)
  if evalin('base', sprintf('exist(''%s'',''var'')', nombre)) == 1
    valor = evalin('base', nombre);
    return
  end
  out = evalin('base', 'out');
  valor = out.get(nombre);
end
