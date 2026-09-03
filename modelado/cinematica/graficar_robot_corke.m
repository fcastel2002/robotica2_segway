function fig = graficar_robot_corke(robot_rtb, Q_rtb, A, B, poses_finales, cfg)
% GRAFICAR_ROBOT_CORKE Visualiza y anima la cadena equivalente en Peter Corke RTB
%
% Entradas:
%   robot_rtb     - Objeto SerialLink de Peter Corke
%   Q_rtb         - Matriz (N x 2) de ángulos articulares [q1, q2] de la trayectoria
%   A             - Coordenadas [x, y] del punto A (base motorizada)
%   B             - Coordenadas [x, y] del punto B (pivote pasivo)
%   poses_finales - Struct con los puntos [D, P] o transformaciones finales:
%                     .D  - Coordenadas [xD, yD]
%                     .P  - Coordenadas [xP, yP]
%                     .q1 - Ángulo de la junta 1 en la pose final (rad)
%                     .q2 - Ángulo de la junta 2 en la pose final (rad)
%   cfg           - Struct opcional de configuración gráfica:
%                     .workspace       - Vector de límites [xmin xmax ymin ymax zmin zmax]
%                     .delay           - Retardo entre cuadros de animación (segundos)
%                     .trail           - Estilo de estela del efector final
%                     .mostrar_trplot2 - Booleano para superponer marcos {A, D, P}
%                     .longitud_ejes   - Longitud de las flechas de trplot2
%                     .posicion_figura - Posición [left bottom width height] de la ventana

%% 1. Configuración de parámetros por defecto si no se especifican
if nargin < 6 || isempty(cfg)
    cfg = struct();
end

% Límites del espacio de trabajo 3D (X, Y, Z)
% Mostramos menos Y positivo y más Y negativo para no cortar la pata estirada
if ~isfield(cfg, 'workspace') || isempty(cfg.workspace)
    cfg.workspace = [-15, 25, -32, 10, -5, 5];
end

if ~isfield(cfg, 'delay') || isempty(cfg.delay)
    cfg.delay = 0.015;
end

if ~isfield(cfg, 'trail') || isempty(cfg.trail)
    cfg.trail = {'m-', 'LineWidth', 2};
end

if ~isfield(cfg, 'mostrar_trplot2') || isempty(cfg.mostrar_trplot2)
    cfg.mostrar_trplot2 = true;
end

if ~isfield(cfg, 'longitud_ejes') || isempty(cfg.longitud_ejes)
    cfg.longitud_ejes = 2.5;
end

if ~isfield(cfg, 'posicion_figura') || isempty(cfg.posicion_figura)
    cfg.posicion_figura = [1060 100 800 700];
end

%% 2. Creación de la ventana gráfica
fig = figure('Name', 'Visualizador Peter Corke (robot.plot y trplot2)', ...
             'Color', 'w', 'Position', cfg.posicion_figura);

fprintf('\nAnimando cadena equivalente en Peter Corke (robot.plot)...\n');

%% 3. Animación con robot.plot (SerialLink de RTB)
% Dibuja los eslabones cilíndricos, las juntas y la trayectoria de la punta
robot_rtb.plot(Q_rtb, ...
    'workspace', cfg.workspace, ...
    'view', 'top', ...
    'trail', cfg.trail, ...
    'delay', cfg.delay, ...
    'nobase', ...
    'noshadow');

hold on;

%% 4. Superposición de marcos de referencia con trplot2 (SMTB)
if cfg.mostrar_trplot2
    % Matrices de transformación homogénea SE(2) de 3x3
    T_A = transl2(A(1), A(2));
    T_D = transl2(poses_finales.D(1), poses_finales.D(2)) * trot2(poses_finales.q1);
    T_P = transl2(poses_finales.P(1), poses_finales.P(2)) * trot2(poses_finales.q1 + poses_finales.q2);

    trplot2(T_A, 'frame', 'A', 'color', 'k', 'length', cfg.longitud_ejes, 'thick', 2);
    trplot2(T_D, 'frame', 'D', 'color', 'b', 'length', cfg.longitud_ejes, 'thick', 2);
    trplot2(T_P, 'frame', 'P', 'color', 'r', 'length', cfg.longitud_ejes, 'thick', 2);
end

%% 5. Elementos de referencia del mecanismo de 4 barras
% Dibuja la bancada fija A-B y el pivote B
plot([A(1), B(1)], [A(2), B(2)], 'k--', 'LineWidth', 2);
plot(B(1), B(2), 'ks', 'MarkerFaceColor', 'k', 'MarkerSize', 8);
text(B(1) + 0.5, B(2) + 0.8, 'B (Pivote pasivo)', 'FontWeight', 'bold', 'FontSize', 10);

title(sprintf('Peter Corke: robot.plot (Cadena A \\rightarrow D \\rightarrow P) | Y \\in [%d, %d] cm', ...
      cfg.workspace(3), cfg.workspace(4)), 'FontSize', 12, 'FontWeight', 'bold');

fprintf('Figura 2 (Peter Corke) lista y centrada.\n');

end
