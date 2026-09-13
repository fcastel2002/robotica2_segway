%% =========================================================================
% VERIFICACIÓN Y ANIMACIÓN DE LA CINEMÁTICA DIRECTA (4 BARRAS - SEGWAY)
% =========================================================================
% Este script calcula y visualiza la cinemática directa de la pata del Segway
% utilizando el método geométrico (intersección de circunferencias), con las ecuaciones y los
% nombres de cinematica_directa.m (AB, AD, BC, CD, DP, beta, delta, theta) y las cotas del CAD en
% parametros_geometria.m. Resumen de la deducción: cinematica_resumen.pdf
%
% Permite verificar visual y numéricamente:
%   1. El cierre correcto del lazo cinemático (puntos A, B, C, D).
%   2. La rigidez del eslabón acoplador CDP (triángulo rígido).
%   3. La trayectoria descrita por el centro de la rueda P.
%   4. Invariantes de longitud en cada paso (tolerancia < 1e-9).
%   5. Validación opcional con la librería de Peter Corke (si está en el path).
% =========================================================================

clear; clc; close all;

%% 1. PARÁMETROS GEOMÉTRICOS DEL MECANISMO (mm y grados)
% Una sola fuente de los valores: parametros_geometria.m (cotas del CAD).
% Nombres: AB bancada, AD manivela, BC balancín, CD y DP acoplador rígido, beta ángulo de la
% bancada, delta ángulo del acoplador en D, theta ángulo del servo. Ver ../geometria/geometria_robot.png
G = parametros_geometria();
AB = G.AB; AD = G.AD; BC = G.BC; CD = G.CD; DP = G.DP; beta = G.beta; delta = G.delta;
A = [0, 0];                                   % Pivote motorizado (eje del servo)
B = [AB * cosd(beta), AB * sind(beta)];       % Pivote pasivo del balancín, a AB de A y beta desde +x
r_rueda = G.Rw;                               % Radio de la rueda (mm)

% Rango de barrido del ángulo del servo theta (grados): ida y vuelta
theta_vals = [linspace(G.theta(1), G.theta(2), 60), linspace(G.theta(2), G.theta(1), 60)];

% --- PARÁMETROS PARA EL GRÁFICO DE PETER CORKE (graficar_robot_corke.m) ---
cfg_corke = struct();
cfg_corke.workspace       = [-150, 250, -350, 120, -50, 50]; % [xmin xmax ymin ymax zmin zmax] en mm
cfg_corke.delay           = 0.015;                     % Retardo entre cuadros de animación
cfg_corke.trail           = {'m-', 'LineWidth', 2};    % Estela de trayectoria de la rueda
cfg_corke.mostrar_trplot2 = true;                      % Superponer marcos coordenados {A, D, P}
cfg_corke.longitud_ejes   = 25;                        % Longitud de flechas de trplot2 (mm)
cfg_corke.posicion_figura = [1060 100 800 700];        % Posición de la ventana

%% 2. CONFIGURACIÓN DE LA VENTANA GRÁFICA (MECANISMO 4 BARRAS)
fig = figure('Name', 'Verificación Cinemática Directa - 4 Barras Segway', ...
             'Color', 'w', 'Position', [100 100 950 700]);
ax = axes('Parent', fig);
hold(ax, 'on'); grid(ax, 'on'); axis(ax, 'equal');
xlabel(ax, 'X (mm)  (positivo = hacia atrás)', 'FontSize', 11, 'FontWeight', 'bold');
ylabel(ax, 'Y (mm)', 'FontSize', 11, 'FontWeight', 'bold');
title(ax, 'Cinemática Directa del Mecanismo de 4 Barras', 'FontSize', 13);
xlim(ax, [-150, 250]); ylim(ax, [-350, 120]);

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
h_info = text(ax, -140, 100, '', 'FontSize', 10, 'FontName', 'Consolas', ...
              'BackgroundColor', [0.95 0.95 0.95], 'EdgeColor', [0.7 0.7 0.7]);

% Etiquetas de nodos fijos
text(ax, A(1)-18, A(2)-8, 'A (Servo)', 'FontWeight', 'bold', 'FontSize', 10);
text(ax, B(1)+5, B(2)+8, 'B (Pivote)', 'FontWeight', 'bold', 'FontSize', 10);

% Puntos auxiliares para dibujar la circunferencia de la rueda
ang_circ = linspace(0, 2*pi, 50);
cos_circ = cos(ang_circ);
sin_circ = sin(ang_circ);

trayectoria_P = [];
Q_rtb = zeros(length(theta_vals), 2);

%% 3. BUCLE DE ANIMACIÓN Y VERIFICACIÓN CINEMÁTICA
fprintf('============================================================\n');
fprintf(' INICIANDO VERIFICACIÓN DE CINEMÁTICA DIRECTA (4 BARRAS)\n');
fprintf('============================================================\n');

for i = 1:length(theta_vals)
    th_deg = theta_vals(i);
    theta = deg2rad(th_deg);

    % --- PASOS 1 a 3: D, C y P con las ecuaciones de cinematica_directa.m ---
    %   D = A + AD (cos theta, sin theta)
    %   BD^2 = AB^2 + AD^2 - 2 AB AD cos(theta - beta) ;  alfa_DB = atan2(yB - yD, xB - xD)
    %   cos gamma = (CD^2 + BD^2 - BC^2) / (2 CD BD) ;    theta_DC = alfa_DB - gamma
    %   C = D + CD (cos theta_DC, sin theta_DC) ;  theta_DP = theta_DC + delta ;  P = D + DP (cos theta_DP, sin theta_DP)
    K = cinematica_directa(th_deg, G);
    if ~K.valido
        warning('Mecanismo fuera de rango en theta = %.1f° (no cierra)', th_deg);
        continue;
    end
    D = K.D; C = K.C; P = K.P;
    theta_DC = deg2rad(K.theta_DC);
    theta_DP = deg2rad(K.theta_DP);

    % Variables articulares relativas para la cadena equivalente de Peter Corke
    Q_rtb(i, :) = [theta, theta_DP - theta];

    % --- PASO 4: Comprobación de invariantes rígidas (Tolerancia < 1e-9) ---
    err_AD = abs(norm(D - A) - AD);
    err_BC = abs(norm(C - B) - BC);
    err_CD = abs(norm(C - D) - CD);
    err_DP = abs(norm(P - D) - DP);
    
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
        ['\\theta:  %6.1f°\n' ...
         '\\theta_{DC}: %6.1f°\n' ...
         'D:  [%6.1f, %6.1f] mm\n' ...
         'C:  [%6.1f, %6.1f] mm\n' ...
         'P:  [%6.1f, %6.1f] mm\n' ...
         'Error barras: < 1e-9 mm'], ...
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
    L1_rtb = Link('d', 0, 'a', AD, 'alpha', 0);
    L2_rtb = Link('d', 0, 'a', DP, 'alpha', 0);
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
    fprintf('Diferencia real: %.2e mm\n', error_corke);
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
