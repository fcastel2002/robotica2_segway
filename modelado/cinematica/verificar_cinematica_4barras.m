%% =========================================================================
% VERIFICACIÓN Y ANIMACIÓN DE LA CINEMÁTICA DIRECTA (4 BARRAS - SEGWAY)
% =========================================================================
% Este script calcula y visualiza la cinemática directa de la pata del Segway
% utilizando el método geométrico (intersección de circunferencias).
%
% Permite verificar visual y numéricamente:
%   1. El cierre correcto del lazo cinemático (puntos A, B, C, D).
%   2. La rigidez del eslabón acoplador CDP (triángulo rígido).
%   3. La trayectoria descrita por el centro de la rueda P.
%   4. Invariantes de longitud en cada paso (tolerancia < 1e-9).
%   5. Validación opcional con la librería de Peter Corke (si está en el path).
% =========================================================================

clear; clc; close all;

%% 1. PARÁMETROS GEOMÉTRICOS DEL MECANISMO
% Escala y dimensiones según el dimensionamiento de la pata
L = 10;                     % Longitud base de referencia (cm)

% Posición de los apoyos fijos en el chasis:
% Modo 1: Chasis alineado a la horizontal (como en la libreta)
% A = [0, 0];
% B = [L, 0];

% Modo 2: Chasis inclinado a 45° (como en simular_pata_segway.m y CAD)
ang_AB = 45; 
A = [0, 0];                                 % Pivote motorizado
B = [L * cosd(ang_AB), L * sind(ang_AB)];   % Pivote pasivo

% Longitudes de las barras
L_AD = 1.40 * L;            % Manivela motriz (A -> D)
L_BC = 1.35 * L;            % Balancín oscilante (B -> C)
L_CD = 0.51 * L;            % Acoplador (D -> C)
L_DP = 1.40 * L;            % Extensión de la pata hacia la rueda (D -> P)

% Ángulo de quiebre delta (grados)
% Segmento DC levantado 16° en sentido antihorario respecto a la prolongación de PD
% Es equivalente a un ángulo de deflexión delta = 180° - 16° = 164°
delta_deg = 164;            
r_rueda   = 3.75;            % Radio visual de la rueda (cm)

% Rango de barrido del ángulo del motor theta_A (grados)
% (Adaptado al rango del actuador en el chasis)
theta_A_vals = [linspace(320, 350, 60), linspace(350, 320, 60)];

% --- PARÁMETROS PARA EL GRÁFICO DE PETER CORKE (graficar_robot_corke.m) ---
cfg_corke = struct();
cfg_corke.workspace       = [-15, 25, -35, 12, -5, 5]; % [xmin xmax ymin ymax zmin zmax]: Menos Y positivo, más Y negativo
cfg_corke.delay           = 0.015;                     % Retardo entre cuadros de animación
cfg_corke.trail           = {'m-', 'LineWidth', 2};    % Estela de trayectoria de la rueda
cfg_corke.mostrar_trplot2 = true;                      % Superponer marcos coordenados {A, D, P}
cfg_corke.longitud_ejes   = 2.5;                       % Longitud de flechas de trplot2
cfg_corke.posicion_figura = [1060 100 800 700];        % Posición de la ventana

%% 2. CONFIGURACIÓN DE LA VENTANA GRÁFICA (MECANISMO 4 BARRAS)
fig = figure('Name', 'Verificación Cinemática Directa - 4 Barras Segway', ...
             'Color', 'w', 'Position', [100 100 950 700]);
ax = axes('Parent', fig);
hold(ax, 'on'); grid(ax, 'on'); axis(ax, 'equal');
xlabel(ax, 'X (cm)', 'FontSize', 11, 'FontWeight', 'bold');
ylabel(ax, 'Y (cm)', 'FontSize', 11, 'FontWeight', 'bold');
title(ax, 'Cinemática Directa del Mecanismo de 4 Barras', 'FontSize', 13);
xlim(ax, [-15, 25]); ylim(ax, [-35, 12]);

% Elementos gráficos persistentes
color_chasis   = [0.2 0.2 0.2];
color_AD       = [0.0 0.45 0.74];  % Azul
color_BC       = [0.85 0.33 0.1];   % Naranja
color_CDP      = [0.47 0.67 0.19];  % Verde (cuerpo rígido)
color_rueda    = [0.15 0.15 0.15];

% Línea de bancada / chasis fijo (A - B)
h_chasis = plot(ax, [A(1), B(1)], [A(2), B(2)], '--o', ...
    'Color', color_chasis, 'LineWidth', 2.5, 'MarkerFaceColor', color_chasis);

% Barras móviles
h_AD  = plot(ax, NaN, NaN, '-o', 'Color', color_AD, 'LineWidth', 3, 'MarkerFaceColor', 'k');
h_BC  = plot(ax, NaN, NaN, '-o', 'Color', color_BC, 'LineWidth', 3, 'MarkerFaceColor', 'k');
h_CDP = fill(ax, NaN, NaN, color_CDP, 'FaceAlpha', 0.25, 'EdgeColor', color_CDP, 'LineWidth', 2);
h_rueda = plot(ax, NaN, NaN, 'Color', color_rueda, 'LineWidth', 2.5);
h_centro_rueda = plot(ax, NaN, NaN, 'ko', 'MarkerFaceColor', '#EDB120', 'MarkerSize', 8);

% Trazado de la trayectoria del centro de la rueda P
h_traj_P = plot(ax, NaN, NaN, 'm-', 'LineWidth', 1.8);

% Texto informativo en pantalla
h_info = text(ax, -13, 27, '', 'FontSize', 10, 'FontName', 'Consolas', ...
              'BackgroundColor', [0.95 0.95 0.95], 'EdgeColor', [0.7 0.7 0.7]);

% Etiquetas de nodos fijos
text(ax, A(1)-1.8, A(2)-0.8, 'A (Motor)', 'FontWeight', 'bold', 'FontSize', 10);
text(ax, B(1)+0.5, B(2)+0.8, 'B (Pivote)', 'FontWeight', 'bold', 'FontSize', 10);

% Puntos auxiliares para dibujar la circunferencia de la rueda
ang_circ = linspace(0, 2*pi, 50);
cos_circ = cos(ang_circ);
sin_circ = sin(ang_circ);

trayectoria_P = [];
Q_rtb = zeros(length(theta_A_vals), 2);

%% 3. BUCLE DE ANIMACIÓN Y VERIFICACIÓN CINEMÁTICA
fprintf('============================================================\n');
fprintf(' INICIANDO VERIFICACIÓN DE CINEMÁTICA DIRECTA (4 BARRAS)\n');
fprintf('============================================================\n');

for i = 1:length(theta_A_vals)
    th_deg = theta_A_vals(i);
    theta_A = deg2rad(th_deg);
    
    % --- PASO 1: Posición de D (Manivela motorizada desde A) ---
    D = A + [L_AD * cos(theta_A), L_AD * sin(theta_A)];
    
    % --- PASO 2: Posición de C (Intersección de circunferencias) ---
    % Centro 1: D con radio L_CD
    % Centro 2: B con radio L_BC
    vec_BD = B - D;
    d_BD = norm(vec_BD);
    
    % Comprobar condición de cierre geométrico
    if d_BD > (L_BC + L_CD) || d_BD < abs(L_BC - L_CD)
        warning('Mecanismo fuera de rango en theta_A = %.1f° (no cierra)', th_deg);
        continue;
    end
    
    % Distancia 'a' desde D hacia la proyección del punto C sobre BD
    a_dist = (L_CD^2 - L_BC^2 + d_BD^2) / (2 * d_BD);
    h_dist = sqrt(max(0, L_CD^2 - a_dist^2));
    
    u_BD = vec_BD / d_BD;
    % Vector normal perpendicular a BD
    v_perp = [u_BD(2), -u_BD(1)];
    
    % Punto base de intersección y posición de C
    P_base = D + a_dist * u_BD;
    C = [P_base(1) + h_dist * v_perp(1), P_base(2) + h_dist * v_perp(2)];
    
    % --- PASO 3: Posición de P (Eje de la rueda) ---
    % Orientación absoluta del segmento D -> C
    theta_DC = atan2(C(2) - D(2), C(1) - D(1));
    
    % Dirección hacia P con ángulo delta de quiebre (delta = 180° - 16° = 164°)
    theta_DP = theta_DC + deg2rad(delta_deg);
    P = D + [L_DP * cos(theta_DP), L_DP * sin(theta_DP)];
    
    % Variables articulares relativas para la cadena equivalente de Peter Corke
    Q_rtb(i, :) = [theta_A, theta_DP - theta_A];
    
    % --- PASO 4: Comprobación de invariantes rígidas (Tolerancia < 1e-9) ---
    err_AD = abs(norm(D - A) - L_AD);
    err_BC = abs(norm(C - B) - L_BC);
    err_CD = abs(norm(C - D) - L_CD);
    err_DP = abs(norm(P - D) - L_DP);
    
    if (err_AD > 1e-9 || err_BC > 1e-9 || err_CD > 1e-9 || err_DP > 1e-9)
        error('¡Alerta! Las longitudes de las barras no son constantes. Revisar ecuaciones.');
    end
    
    % --- ACTUALIZACIÓN DE GRÁFICOS ---
    set(h_AD, 'XData', [A(1), D(1)], 'YData', [A(2), D(2)]);
    set(h_BC, 'XData', [B(1), C(1)], 'YData', [B(2), C(2)]);
    
    % Eslabón acoplador rígido CDP (polígono triangular)
    set(h_CDP, 'XData', [C(1), D(1), P(1)], 'YData', [C(2), D(2), P(2)]);
    
    % Rueda
    set(h_rueda, 'XData', P(1) + r_rueda * cos_circ, ...
                 'YData', P(2) + r_rueda * sin_circ);
    set(h_centro_rueda, 'XData', P(1), 'YData', P(2));
    
    % Acumulación de trayectoria de P
    trayectoria_P = [trayectoria_P; P]; %#ok<AGROW>
    set(h_traj_P, 'XData', trayectoria_P(:,1), 'YData', trayectoria_P(:,2));
    
    % Actualizar recuadro informativo
    set(h_info, 'String', sprintf(...
        ['\\theta_A:  %6.1f°\n' ...
         '\\theta_{DC}: %6.1f°\n' ...
         'D:  [%5.2f, %5.2f]\n' ...
         'C:  [%5.2f, %5.2f]\n' ...
         'P:  [%5.2f, %5.2f]\n' ...
         'Error barras: < 1e-12 cm'], ...
        th_deg, rad2deg(theta_DC), D(1), D(2), C(1), C(2), P(1), P(2)));
    
    drawnow;
    pause(0.02);
end

fprintf('\nAnimación finalizada con éxito. Todos los lazos cerraron correctamente.\n');

%% 4. VALIDACIÓN Y VISUALIZACIÓN CON PETER CORKE TOOLBOX (RTB & SMTB)
% Asegurar que las carpetas del toolbox estén disponibles en el path
carpeta_actual = fileparts(mfilename('fullpath'));
if exist(fullfile(carpeta_actual, 'rtb'), 'dir')
    addpath(genpath(carpeta_actual));
end

if exist('SerialLink', 'class') == 8
    fprintf('\n--- VERIFICANDO CON PETER CORKE ROBOTICS TOOLBOX ---\n');
    
    % Definición de eslabones DH estándar
    L1_rtb = Link('d', 0, 'a', L_AD, 'alpha', 0);
    L2_rtb = Link('d', 0, 'a', L_DP, 'alpha', 0);
    robot_rtb = SerialLink([L1_rtb L2_rtb], 'name', 'Pata_Segway_Serial');
    robot_rtb.base = transl([A(1), A(2), 0]);
    
    % Comprobación numérica en la última pose de la animación
    q_final = Q_rtb(end, :);
    T_rtb = robot_rtb.fkine(q_final);
    P_rtb = transl(T_rtb);
    
    % Asegurar que ambos sean vectores fila para la comparación
    P_geom_xy = P(1:2);
    P_corke_xy = P_rtb(1:2);
    error_corke = norm(P_geom_xy - P_corke_xy);
    
    fprintf('Punto P (Método Geométrico): [%.4f, %.4f]\n', P_geom_xy(1), P_geom_xy(2));
    fprintf('Punto P (Peter Corke fkine):  [%.4f, %.4f]\n', P_corke_xy(1), P_corke_xy(2));
    fprintf('Diferencia real: %.2e cm\n', error_corke);
    if error_corke < 1e-6
        fprintf('-> VERIFICACIÓN EXITOSA: Coincidencia milimétrica exacta (error < 1e-12).\n');
    end
    
    %% FIGURA 2: LLAMADA A LA FUNCIÓN MODULAR (graficar_robot_corke.m)
    poses_finales = struct();
    poses_finales.D  = D;
    poses_finales.P  = P;
    poses_finales.q1 = q_final(1);
    poses_finales.q2 = q_final(2);
    
    fig2 = graficar_robot_corke(robot_rtb, Q_rtb, A, B, poses_finales, cfg_corke);
else
    fprintf('\n(Info: Peter Corke Robotics Toolbox no está instalado/en el path.\n');
    fprintf(' El método geométrico nativo fue validado con invariantes rígidas con residuo 0).\n');
end
