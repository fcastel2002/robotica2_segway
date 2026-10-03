%% PENDULO INVERTIDO SOBRE RUEDAS: demostracion del modelo de equilibrio
% Leer primero modelado/planta/pendulo_invertido/desarrollo_matematico.md.
% Abrir este archivo y pulsar Run. No requiere Simulink ni toolboxes.
% Orden de estado: [x; velocidad_x; phi; velocidad_phi], todo en SI.
% Las patas permanecen fijas durante cada corrida. El robot no tiene control.

%% 1. Encontrar las carpetas del proyecto sin depender de la carpeta actual.
carpeta_script = fileparts(mfilename('fullpath'));
raiz_repo = fileparts(fileparts(carpeta_script));
carpeta_modelo = fullfile(raiz_repo, 'modelado', 'planta', 'pendulo_invertido');
addpath(carpeta_modelo);
addpath(fullfile(raiz_repo, 'modelado', 'parametros'));
addpath(fullfile(raiz_repo, 'modelado', 'cinematica'));
carpeta_resultados = fullfile(carpeta_script, 'resultados');
if ~isfolder(carpeta_resultados)
    mkdir(carpeta_resultados);
end

%% 2. PARAMETROS EDITABLES: primero la fisica, despues las condiciones del ensayo.
variante = 'segunda_iteracion';
theta_pata_deg = 25;   % AD bajo la horizontal: 10 plegada, 40 estirada
fisicos = parametros_fisicos(variante);

% Para estudiar una modificacion, descomentar y cambiar ANTES de calcular p:
% fisicos.m_carga = 100;                 % [g], modifica masa, CoM e inercia
% fisicos.r_carga = [-18.5, 50];         % [mm], en la convencion original de A
% fisicos.J_cuerpo = 0.004;              % [kg m^2], medida para ESTA postura
% fisicos.J_rueda = 2e-5;               % [kg m^2], de UNA rueda

p = parametros_pendulo_invertido(fisicos, theta_pata_deg);
% Se puede anular la disipacion para verificar conservacion de energia:
% p.b_eje = 0;
% p.b_phi = 0;
% p.b_x = 0;

tau_total_Nm = 0;        % par TOTAL constante en las ruedas; por motor = tau/2
x_inicial_m = 0;
velocidad_x_inicial = 0;
phi_inicial_deg = 0.5;   % inclinacion de P->G, antihoraria (+ = hacia atras)
velocidad_phi_inicial = 0;
duracion_s = 1;
limite_phi_deg = 20;     % corte de demostracion; NO es un limite medido del CAD
tolerancia_relativa = 1e-9;
tolerancia_absoluta = 1e-11;
paso_maximo_s = 1e-3;
cantidad_muestras = 1001;

% El par es mecanico ideal; no se confunde con tension, PWM ni par del servo.
entrada_par = @(tiempo) tau_total_Nm; % constante para ambos modelos
estado_inicial = [x_inicial_m; velocidad_x_inicial; ...
    deg2rad(phi_inicial_deg); velocidad_phi_inicial];
validateattributes(tau_total_Nm, {'numeric'}, {'scalar', 'real', 'finite'});
validateattributes(duracion_s, {'numeric'}, {'scalar', 'real', 'finite', 'positive'});
assert(all([p.b_eje, p.b_phi, p.b_x] >= 0), 'Los amortiguamientos deben ser no negativos.');
assert(limite_phi_deg > abs(phi_inicial_deg) && limite_phi_deg < 90, ...
    'Elegir un limite de demostracion mayor que el angulo inicial y menor que 90 grados.');
[~, diagnostico_inicial] = ecuaciones_pendulo_invertido(estado_inicial, tau_total_Nm, p);
assert(diagnostico_inicial.contacto_valido, ...
    'La condicion inicial ya exige despegue o deslizamiento: revisar par y estado.');

%% 3. Mostrar que robot equivalente estamos simulando.
fprintf('\nPENDULO INVERTIDO: postura fija de %.1f grados\n', theta_pata_deg);
fprintf('Masa cuerpo = %.6f kg; ruedas = %.6f kg; total = %.6f kg\n', ...
    p.m_cuerpo, p.m_ruedas, p.m_total);
fprintf('Radio = %.6f m; distancia P-G = %.6f m\n', p.r, p.l);
fprintf('J_G = %.9f kg m^2; J_ruedas total = %.9f kg m^2\n', p.J_cuerpo, p.J_ruedas);
fprintf('Chasis en equilibrio: beta = %.3f grados\n', rad2deg(p.beta_equilibrio));
fprintf('Inercia del cuerpo: %s\n', p.fuente_inercia);
disp(p.piezas);

%% 4. Obtener el modelo lineal cerca de phi = 0.
L = linealizar_pendulo_invertido(p);
fprintf('A, con estado [x; velocidad_x; phi; velocidad_phi]:\n');
disp(L.A);
fprintf('B, con entrada tau TOTAL [N m]:\n');
disp(L.B);
fprintf('Autovalores de A [1/s]:\n');
disp(L.autovalores);
fprintf('Rango de controlabilidad: %d de 4\n', L.rango_controlabilidad);

%% 5. Integrar la dinamica NO lineal y la contabilidad de trabajo.
% Las primeras cuatro variables son estados mecanicos. La quinta integra
% la potencia neta para contrastarla con E(t)-E(0); no agrega fisica al robot.
estado_ampliado_inicial = [estado_inicial; 0];
limite_phi_rad = deg2rad(limite_phi_deg);
opciones = odeset('RelTol', tolerancia_relativa, ...
    'AbsTol', tolerancia_absoluta, 'MaxStep', paso_maximo_s, ...
    'Events', @(t, y) eventos_modelo(t, y, entrada_par, p, limite_phi_rad));
solucion = ode45(@(t, y) dinamica_con_trabajo(t, y, entrada_par, p), ...
    [0, duracion_s], estado_ampliado_inicial, opciones);

tiempo_final = solucion.x(end);
tiempo = linspace(0, tiempo_final, cantidad_muestras).';
estado_ampliado = deval(solucion, tiempo).';
estado_no_lineal = estado_ampliado(:, 1:4);
trabajo_neto = estado_ampliado(:, 5);

motivo_fin = 'Se alcanzo la duracion solicitada';
if isfield(solucion, 'ie') && ~isempty(solucion.ie)
    motivos = {'Limite angular de demostracion', 'Normal nula: comienza despegue', ...
        'Limite de adherencia: comienza deslizamiento'};
    motivo_fin = motivos{solucion.ie(end)};
end

%% 6. Integrar el modelo lineal en el mismo intervalo, con la misma entrada.
% Comparar ambos fuera de pequenos angulos solo muestra el error de Taylor.
opciones_lineales = odeset('RelTol', tolerancia_relativa, ...
    'AbsTol', tolerancia_absoluta, 'MaxStep', paso_maximo_s);
solucion_lineal = ode45(@(t, z) L.A * z + L.B * entrada_par(t), ...
    [0, tiempo_final], estado_inicial, opciones_lineales);
estado_lineal = deval(solucion_lineal, tiempo).';

%% 7. Recuperar energia y reacciones en cada instante de salida.
energia = zeros(cantidad_muestras, 1);
normal = zeros(cantidad_muestras, 1);
fuerza_tangencial = zeros(cantidad_muestras, 1);
margen_adherencia = zeros(cantidad_muestras, 1);
for i = 1:cantidad_muestras
    estado_i = estado_no_lineal(i, :).';
    [~, R] = ecuaciones_pendulo_invertido(estado_i, entrada_par(tiempo(i)), p);
    energia(i) = R.energia;
    normal(i) = R.normal;
    fuerza_tangencial(i) = R.fuerza_tangencial;
    margen_adherencia(i) = R.margen_adherencia;
end
residuo_energia = energia - energia(1) - trabajo_neto;
error_angular = estado_no_lineal(:, 3) - estado_lineal(:, 3);
ventana_local = abs(estado_no_lineal(:, 3)) <= deg2rad(5);
if any(ventana_local)
    error_local_deg = max(abs(rad2deg(error_angular(ventana_local))));
else
    error_local_deg = NaN; % no hubo muestras dentro de la ventana de 5 grados
end

fprintf('Fin en %.6f s: %s\n', tiempo_final, motivo_fin);
fprintf('Error angular lineal/no lineal hasta 5 grados: %.6g grados\n', error_local_deg);
fprintf('Residuo maximo del balance de energia: %.6g J\n', max(abs(residuo_energia)));
fprintf('Normal minima: %.6f N; margen de adherencia minimo: %.6f N\n', ...
    min(normal), min(margen_adherencia));

%% 8. Graficar la respuesta, el contacto y la verificacion de energia.
fig_respuesta = figure('Name', 'Pendulo invertido: respuesta', ...
    'Color', 'w', 'Position', [80, 80, 1200, 850]);
azul = [0.05, 0.30, 0.60];
naranja = [0.80, 0.30, 0.05];
tiledlayout(2, 2, 'TileSpacing', 'compact', 'Padding', 'compact');

nexttile;
plot(tiempo, rad2deg(estado_no_lineal(:, 3)), 'Color', azul, 'LineWidth', 2);
hold on;
plot(tiempo, rad2deg(estado_lineal(:, 3)), '--', 'Color', naranja, 'LineWidth', 1.5);
yline(5, ':', 'Ventana local: 5 grados');
grid on;
xlabel('Tiempo [s]'); ylabel('Inclinacion de P-G [grados]');
title('La vertical es un equilibrio inestable');
legend('No lineal', 'Lineal', 'Location', 'northwest');

nexttile;
plot(tiempo, estado_no_lineal(:, 1) * 1000, 'Color', azul, 'LineWidth', 2);
hold on;
plot(tiempo, estado_lineal(:, 1) * 1000, '--', 'Color', naranja, 'LineWidth', 1.5);
grid on;
xlabel('Tiempo [s]'); ylabel('Posicion del eje [mm]');
title('Las ruedas tambien se desplazan');
legend('No lineal', 'Lineal', 'Location', 'best');

nexttile;
plot(tiempo, normal, 'Color', azul, 'LineWidth', 2);
hold on;
plot(tiempo, margen_adherencia, 'Color', naranja, 'LineWidth', 1.5);
yline(0, 'k:');
grid on;
xlabel('Tiempo [s]'); ylabel('Fuerza total [N]');
title('Validez del apoyo y de la rodadura');
legend('Normal N', 'Margen: mu N - |F|', 'Location', 'best');

nexttile;
plot(tiempo, energia - energia(1), 'Color', azul, 'LineWidth', 2);
hold on;
plot(tiempo, trabajo_neto, '--', 'Color', naranja, 'LineWidth', 1.5);
grid on;
xlabel('Tiempo [s]'); ylabel('Energia y trabajo [J]');
title(sprintf('Balance de energia: residuo maximo %.1e J', max(abs(residuo_energia))));
legend('E(t) - E(0)', 'Trabajo neto W(t)', 'Location', 'best');
sgtitle(sprintf('Patas fijas: %.1f grados | par total: %.3f N m', theta_pata_deg, tau_total_Nm));
exportgraphics(fig_respuesta, fullfile(carpeta_resultados, 'respuesta.png'), 'Resolution', 200);

%% 9. Guardar resultados trazables para volver a leerlos sin correr MATLAB.
[estado_git, commit_base] = system(sprintf('git -C "%s" rev-parse HEAD', raiz_repo));
if estado_git ~= 0
    commit_base = 'No disponible';
end
commit_base = strtrim(commit_base);
metadatos.fecha = char(datetime('now', 'TimeZone', 'America/Argentina/Buenos_Aires', ...
    'Format', 'yyyy-MM-dd HH:mm:ss Z'));
metadatos.matlab = version;
metadatos.commit_base = commit_base;
metadatos.variante = variante;
metadatos.solver = 'ode45';
metadatos.RelTol = tolerancia_relativa;
metadatos.AbsTol = tolerancia_absoluta;
metadatos.MaxStep = paso_maximo_s;
metadatos.motivo_fin = motivo_fin;
metadatos.duracion_solicitada = duracion_s;
metadatos.limite_phi_deg = limite_phi_deg;

save(fullfile(carpeta_resultados, 'resultado_base.mat'), 'p', 'fisicos', 'L', ...
    'metadatos', 'tau_total_Nm', 'estado_inicial', 'tiempo', 'estado_no_lineal', ...
    'estado_lineal', 'energia', 'trabajo_neto', 'residuo_energia', 'normal', ...
    'fuerza_tangencial', 'margen_adherencia');
tabla_salida = table(tiempo, estado_no_lineal(:, 1), estado_no_lineal(:, 2), ...
    rad2deg(estado_no_lineal(:, 3)), estado_no_lineal(:, 4), ...
    rad2deg(estado_lineal(:, 3)), normal, fuerza_tangencial, energia, residuo_energia, ...
    'VariableNames', {'t_s', 'x_m', 'v_ms', 'phi_deg', 'omega_rads', ...
    'phi_lineal_deg', 'normal_N', 'tangencial_N', 'energia_J', 'residuo_J'});
writetable(tabla_salida, fullfile(carpeta_resultados, 'trayectoria.csv'));
escribir_resumen(carpeta_resultados, p, L, metadatos, estado_inicial, ...
    tau_total_Nm, tiempo_final, error_local_deg, normal, margen_adherencia, residuo_energia);
dibujar_esquema(p, carpeta_resultados);
fprintf('Resultados guardados en: %s\n', carpeta_resultados);

%% Funciones locales: lectura directa de cada operacion auxiliar.
function dy = dinamica_con_trabajo(t, y, entrada, p)
    [dz, R] = ecuaciones_pendulo_invertido(y(1:4), entrada(t), p);
    dy = [dz; R.potencia_neta];
end

function [valor, terminal, direccion] = eventos_modelo(t, y, entrada, p, limite)
    [~, R] = ecuaciones_pendulo_invertido(y(1:4), entrada(t), p);
    valor = [limite - abs(y(3)); R.normal; R.margen_adherencia];
    terminal = [1; 1; 1];
    direccion = [-1; -1; -1];
end

function escribir_resumen(carpeta, p, L, meta, z0, tau, tf, error_local, N, margen, residuo)
    archivo = fullfile(carpeta, 'resultado_base.md');
    fid = fopen(archivo, 'w', 'n', 'UTF-8');
    assert(fid >= 0, 'No se pudo abrir el resumen de resultados.');
    cerrar_archivo = onCleanup(@() fclose(fid));
    fprintf(fid, '# Resultado del pendulo invertido\n\n');
    fprintf(fid, '- Corrida: %s (Buenos Aires).\n- MATLAB: %s.\n', meta.fecha, meta.matlab);
    fprintf(fid, '- Commit base: `%s`; incorpora archivos locales del modelo nuevo.\n', meta.commit_base);
    fprintf(fid, '- Variante: `%s`; postura fija: %.1f grados.\n', meta.variante, p.theta_pata_deg);
    fprintf(fid, '- Fuente: `%s`. Masas/CoM/inercias estimados; rotor y electricidad omitidos.\n', p.fuente);
    fprintf(fid, '- Solver: %s; RelTol %.1e; AbsTol %.1e; MaxStep %.1e s.\n\n', ...
        meta.solver, meta.RelTol, meta.AbsTol, meta.MaxStep);
    fprintf(fid, '| Parametro | Valor SI |\n|---|---:|\n');
    fprintf(fid, '| Masa cuerpo [kg] | %.9f |\n| Masa ruedas [kg] | %.9f |\n', p.m_cuerpo, p.m_ruedas);
    fprintf(fid, '| Radio [m] | %.9f |\n| Distancia P-G [m] | %.9f |\n', p.r, p.l);
    fprintf(fid, '| J_G [kg m2] | %.9g |\n| J_ruedas [kg m2] | %.9g |\n', p.J_cuerpo, p.J_ruedas);
    fprintf(fid, '| Chasis en equilibrio [grados] | %.6f |\n', rad2deg(p.beta_equilibrio));
    fprintf(fid, '| b_eje [N m s/rad] | %.6g |\n| b_phi [N m s/rad] | %.6g |\n', p.b_eje, p.b_phi);
    fprintf(fid, '| b_x [N s/m] | %.6g |\n| mu | %.6g |\n\n', p.b_x, p.mu);
    fprintf(fid, 'Estado inicial `[x, v, phi, omega]`: `%s` (SI). Par total: %.6f N m.\n\n', ...
        mat2str(z0.', 8), tau);
    fprintf(fid, 'Duracion solicitada %.6f s; limite angular %.1f grados.\n\n', ...
        meta.duracion_solicitada, meta.limite_phi_deg);
    fprintf(fid, 'Fin en **%.6f s**: %s.\n\n', tf, meta.motivo_fin);
    fprintf(fid, '- Error angular hasta 5 grados: %.9g grados.\n', error_local);
    fprintf(fid, '- Normal minima: %.9f N; margen minimo de adherencia: %.9f N.\n', min(N), min(margen));
    fprintf(fid, '- Residuo maximo del balance de energia: %.9g J.\n', max(abs(residuo)));
    fprintf(fid, '- Rango de controlabilidad: %d de 4.\n\n', L.rango_controlabilidad);
    fprintf(fid, 'Orden de estado: `[x; v; phi; omega]`. Entrada: par total de las ruedas.\n\n');
    fprintf(fid, '```text\nA =\n%s\nB =\n%s\nAutovalores =\n%s\n```\n\n', ...
        mat2str(L.A, 9), mat2str(L.B, 9), mat2str(L.autovalores, 9));
    fprintf(fid, 'El equilibrio superior es inestable. El lineal aproxima la dinamica local;\n');
    fprintf(fid, 'esta corrida no identifica parametros ni valida un controlador fisico.\n\n');
    fprintf(fid, '![Respuesta](respuesta.png)\n\n[Datos](trayectoria.csv) | [MATLAB](resultado_base.mat)\n');
end

function dibujar_esquema(p, carpeta)
    % Es un esquema del cuerpo equivalente, no un dibujo a escala del CAD.
    fig = figure('Name', 'Pendulo invertido: convenciones', ...
        'Color', 'w', 'Position', [100, 100, 1050, 650]);
    ax = axes(fig);
    hold(ax, 'on'); axis(ax, 'equal'); axis(ax, 'off');
    azul = [0.05, 0.30, 0.60];
    naranja = [0.80, 0.30, 0.05];
    phi = deg2rad(15); % inclinacion ilustrativa, distinta de la condicion inicial
    P = [0, p.r];
    G = P + p.l * [-sin(phi), cos(phi)];
    plot(ax, [-0.11, 0.17], [0, 0], 'k-', 'LineWidth', 1.5);
    angulos = linspace(0, 2*pi, 150);
    plot(ax, p.r * cos(angulos), p.r + p.r * sin(angulos), ...
        'Color', naranja, 'LineWidth', 3);
    plot(ax, [P(1), G(1)], [P(2), G(2)], 'Color', azul, 'LineWidth', 9);
    plot(ax, [0, 0], [p.r, p.r + 1.17*p.l], 'k--', 'LineWidth', 1);
    plot(ax, P(1), P(2), 'ko', 'MarkerFaceColor', 'k', 'MarkerSize', 6);
    plot(ax, [-p.r, 0], [p.r, p.r], ':', 'Color', naranja, 'LineWidth', 1.2);
    plot(ax, G(1), G(2), 'o', 'Color', azul, 'MarkerFaceColor', azul, 'MarkerSize', 15);
    arco = linspace(pi/2, pi/2+phi, 30);
    plot(ax, 0.55*p.l*cos(arco), p.r+0.55*p.l*sin(arco), 'k-', 'LineWidth', 1.5);
    text(ax, 0.004, p.r+0.73*p.l, '$\varphi > 0$', 'Interpreter', 'latex', 'FontSize', 15);
    text(ax, G(1)-0.075, G(2)+0.012, 'G: masa m, inercia J_G', 'FontSize', 14, 'Color', azul);
    text(ax, -0.020, p.r+0.004, 'P', 'FontSize', 14);
    text(ax, 0.002, p.r+0.35*p.l, '$\ell$', 'Interpreter', 'latex', 'FontSize', 17);
    text(ax, -0.021, p.r-0.009, 'r', 'FontSize', 15);
    quiver(ax, G(1), G(2)-0.012, 0, -0.037, 0, 'Color', azul, 'LineWidth', 1.5);
    text(ax, G(1)-0.020, G(2)-0.043, 'mg', 'FontSize', 14, 'Color', azul);
    quiver(ax, 0.068, p.r, 0.065, 0, 0, 'k', 'LineWidth', 1.5);
    text(ax, 0.065, p.r+0.010, 'x positivo: avance', 'FontSize', 14);
    dibujar_par(ax, [-0.055, p.r+0.015], 0.015, -100, 160, naranja, '+\tau');
    dibujar_par(ax, [0.065, p.r+0.37*p.l], 0.015, 220, -30, azul, '-\tau');
    text(ax, -0.10, -0.024, 'Dos ruedas equivalentes: m_w, J_w | rodadura: x = -r\psi | angulos y pares + antihorarios', 'FontSize', 13);
    text(ax, -0.10, p.r+1.30*p.l, 'Patas bloqueadas en una postura \theta_0', 'FontSize', 17, 'FontWeight', 'bold');
    xlim(ax, [-0.12, 0.20]); ylim(ax, [-0.04, p.r+1.48*p.l]);
    exportgraphics(fig, fullfile(carpeta, 'esquema_modelo.png'), 'Resolution', 200);
    print(fig, fullfile(carpeta, 'esquema_modelo.svg'), '-dsvg');
end

function dibujar_par(ax, centro, radio, inicio_deg, fin_deg, color, etiqueta)
    angulo = deg2rad(linspace(inicio_deg, fin_deg, 60));
    puntos_x = centro(1) + radio*cos(angulo);
    puntos_y = centro(2) + radio*sin(angulo);
    plot(ax, puntos_x, puntos_y, 'Color', color, 'LineWidth', 1.8);
    tangente = sign(fin_deg-inicio_deg) * [-sin(angulo(end)), cos(angulo(end))];
    largo_flecha = 0.007;
    inicio_flecha = [puntos_x(end), puntos_y(end)] - largo_flecha*tangente;
    quiver(ax, inicio_flecha(1), inicio_flecha(2), ...
        largo_flecha*tangente(1), largo_flecha*tangente(2), 0, ...
        'Color', color, 'LineWidth', 2, 'MaxHeadSize', 0.9);
    text(ax, centro(1)-0.008, centro(2)+1.4*radio, etiqueta, 'Color', color, 'FontSize', 17);
end
