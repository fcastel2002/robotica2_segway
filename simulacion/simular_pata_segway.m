function simular_pata_segway()
    % --- PARÁMETROS FIJOS ---
    R = 10;
    ang_AB = 45; 
    A = [0, 0];
    B = [R*cosd(ang_AB), R*sind(ang_AB)]; 

    % --- CONFIGURACIÓN DE LA INTERFAZ GRÁFICA ---
    fig = uifigure('Name', 'Analizador Avanzado de Pierna Segway', 'Position', [100 50 1000 800], 'Color', '#F5F5F5');
    
    % Panel de gráfico
    ax = uiaxes(fig, 'Position', [350 50 600 700]);
    
    % Panel de controles laterales
    pnl = uipanel(fig, 'Position', [20 50 310 700], 'Title', 'Parámetros Cinemáticos', 'FontSize', 14, 'FontWeight', 'bold', 'BackgroundColor', 'w');
    
    % --- CREACIÓN DE CONTROLES: Slider + Campo Numérico Editable Sincronizados ---
    [sld_AD, num_AD] = crear_control(pnl, 'k_{AD} (Manivela):', 0.5, 2.5, 1.4, 640, '%.3f');
    [sld_BC, num_BC] = crear_control(pnl, 'k_{BC} (Balancín):', 0.5, 2.5, 1.35, 570, '%.3f');
    [sld_CD, num_CD] = crear_control(pnl, 'k_{CD} (Acoplad.):', 0.1, 1.5, 0.51, 500, '%.3f');
    [sld_DP, num_DP] = crear_control(pnl, 'k_{DP} (Pierna):', 0.5, 3.0, 1.4, 430, '%.3f');
    [sld_delta, num_delta] = crear_control(pnl, '\delta (Desv. º):', 90, 270, 164, 360, '%.1f');
    [sld_Rueda, num_Rueda] = crear_control(pnl, 'Radio Rueda (cm):', 1, 15, 4, 290, '%.1f');
    
    % Control del Motor (Independiente con color distintivo)
    [sld_theta, num_theta] = crear_control(pnl, 'Ángulo Motor \theta (º):', 320, 350, 320, 220, '%.1f', '#0072BD');

    % Botón de Exportación al Workspace
    btn_exportar = uibutton(pnl, 'push', 'Position', [55 50 200 42], 'Text', 'Exportar a Workspace', ...
        'FontSize', 14, 'FontWeight', 'bold', 'BackgroundColor', '#77AC30', 'FontColor', 'w');

    % Agrupar controles para callbacks y exportación (mantiene compatibilidad val_* y num_*)
    controles = struct(...
        'sld_AD', sld_AD, 'num_AD', num_AD, 'val_AD', num_AD, ...
        'sld_BC', sld_BC, 'num_BC', num_BC, 'val_BC', num_BC, ...
        'sld_CD', sld_CD, 'num_CD', num_CD, 'val_CD', num_CD, ...
        'sld_DP', sld_DP, 'num_DP', num_DP, 'val_DP', num_DP, ...
        'sld_delta', sld_delta, 'num_delta', num_delta, 'val_delta', num_delta, ...
        'sld_Rueda', sld_Rueda, 'num_Rueda', num_Rueda, 'val_Rueda', num_Rueda, ...
        'sld_theta', sld_theta, 'num_theta', num_theta, 'val_theta', num_theta);

    % Inicialización de handles gráficos persistentes y caché cinemático
    gh = inicializar_graficos(ax);
    cache = struct('geom', [], 'Px_full', [], 'Py_full', [], 'desviacion_x', NaN);
    ax.UserData = struct('gh', gh, 'cache', cache);

    % Función de actualización global del gráfico
    update_fcn = @() actualizar_grafico(ax, controles, A, B, R);
    
    % Conectar sincronización bidireccional y actualización en tiempo real
    conectar_control(sld_AD, num_AD, 0.5, 2.5, update_fcn);
    conectar_control(sld_BC, num_BC, 0.5, 2.5, update_fcn);
    conectar_control(sld_CD, num_CD, 0.1, 1.5, update_fcn);
    conectar_control(sld_DP, num_DP, 0.5, 3.0, update_fcn);
    conectar_control(sld_delta, num_delta, 90, 270, update_fcn);
    conectar_control(sld_Rueda, num_Rueda, 1, 15, update_fcn);
    conectar_control(sld_theta, num_theta, 320, 350, update_fcn);
    
    % Callback del botón exportar
    btn_exportar.ButtonPushedFcn = @(src, event) exportar_datos(controles, A, B, R);

    % Dibujo inicial
    update_fcn();
end

% --- INICIALIZACIÓN PERSISTENTE DE ELEMENTOS GRÁFICOS (SIN CLA) ---
function gh = inicializar_graficos(ax)
    hold(ax, 'on');
    axis(ax, 'equal');
    axis(ax, [-15 25 -5 50]);
    ax.XGrid = 'on'; ax.YGrid = 'on';
    ax.XMinorGrid = 'on'; ax.YMinorGrid = 'on';
    
    color_barra = [0.8500, 0.3250, 0.0980];
    
    % 1. Suelo fijo (y=0)
    gh.h_ground = plot(ax, [-50 50], [0 0], 'Color', [0.3 0.3 0.3], 'LineWidth', 3);
    
    % 2. Chasis
    gh.h_chasis = rectangle(ax, 'Position', [-7, -3, 14, 10], 'EdgeColor', '#0072BD', 'LineWidth', 2);
    
    % 3. Trayectoria de referencia
    gh.h_traj = plot(ax, NaN, NaN, 'k--', 'LineWidth', 1.5);
    
    % 4. Barras del mecanismo y patch triangular
    gh.h_patch_CDP = fill(ax, [0 0 0], [0 0 0], color_barra, 'FaceAlpha', 0.2, 'EdgeColor', 'none');
    gh.h_bar_AD = plot(ax, [0 0], [0 0], '-o', 'Color', color_barra, 'LineWidth', 3, 'MarkerFaceColor', 'k');
    gh.h_bar_BC = plot(ax, [0 0], [0 0], '-o', 'Color', color_barra, 'LineWidth', 3, 'MarkerFaceColor', 'k');
    gh.h_bar_CD = plot(ax, [0 0], [0 0], '-o', 'Color', color_barra, 'LineWidth', 3, 'MarkerFaceColor', 'k');
    gh.h_bar_DP = plot(ax, [0 0], [0 0], '-o', 'Color', color_barra, 'LineWidth', 3, 'MarkerFaceColor', 'k');
    
    % 5. Motor y Rueda
    gh.h_motor = plot(ax, 0, 0, 'ks', 'MarkerFaceColor', 'k', 'MarkerSize', 10);
    gh.h_rueda_circ = plot(ax, NaN, NaN, 'k-', 'LineWidth', 2.5);
    gh.h_rueda_centro = plot(ax, 0, 0, 'ko', 'MarkerFaceColor', '#EDB120', 'MarkerSize', 10, 'LineWidth', 2);
    
    % Precalcular constantes trigonométricas de la rueda y muestreo
    angulos_rueda = linspace(0, 2*pi, 50);
    gh.cos_rueda = cos(angulos_rueda);
    gh.sin_rueda = sin(angulos_rueda);
    gh.theta_full = linspace(320, 350, 150);
    
    % Agrupar objetos móviles para gestión eficiente de visibilidad
    gh.mecanismo_objs = [gh.h_chasis, gh.h_traj, gh.h_bar_AD, gh.h_bar_BC, ...
                         gh.h_bar_CD, gh.h_bar_DP, gh.h_patch_CDP, gh.h_motor, ...
                         gh.h_rueda_circ, gh.h_rueda_centro];
    
    hold(ax, 'off');
end

% --- CÁLCULO PREASIGNADO DE TRAYECTORIA COMPLETA BASE ---
function [Px_full, Py_full, desviacion_x] = calcular_trayectoria_base(AD, BC, CD, DP, delta, A, B, theta_full)
    n_pts = length(theta_full);
    Px_raw = zeros(1, n_pts);
    Py_raw = zeros(1, n_pts);
    valido = false(1, n_pts);
    
    bc_plus_cd = BC + CD;
    bc_minus_cd_abs = abs(BC - CD);
    cd_sq_minus_bc_sq = CD^2 - BC^2;
    cd_sq = CD^2;
    
    for i = 1:n_pts
        th = theta_full(i);
        D_t = A + [AD*cosd(th), AD*sind(th)];
        vec_BD = B - D_t;
        d_BD_t = hypot(vec_BD(1), vec_BD(2));
        
        if d_BD_t > bc_plus_cd || d_BD_t < bc_minus_cd_abs
            continue;
        end
        
        a_t = (cd_sq_minus_bc_sq + d_BD_t^2) / (2*d_BD_t);
        h_t = sqrt(max(0, cd_sq - a_t^2));
        
        inv_d = 1 / d_BD_t;
        P2_t = D_t + a_t * vec_BD * inv_d;
        C_t = [P2_t(1) + h_t*vec_BD(2)*inv_d, P2_t(2) - h_t*vec_BD(1)*inv_d];
        
        ang_DC_t = atan2d(C_t(2)-D_t(2), C_t(1)-D_t(1));
        P_t = D_t + [DP*cosd(ang_DC_t + delta), DP*sind(ang_DC_t + delta)];
        
        Px_raw(i) = P_t(1);
        Py_raw(i) = P_t(2);
        valido(i) = true;
    end
    
    Px_full = Px_raw(valido);
    Py_full = Py_raw(valido);
    
    if ~isempty(Px_full)
        desviacion_x = max(Px_full) - min(Px_full);
    else
        desviacion_x = NaN;
    end
end

% --- FUNCIÓN PARA CREAR SLIDER + CAMPO NUMÉRICO EDITABLE ---
function [sld, num_field] = crear_control(parent, label_text, min_val, max_val, start_val, y_pos, fmt, color_label)
    if nargin < 7 || isempty(fmt)
        fmt = '%.3f';
    end
    if nargin < 8 || isempty(color_label)
        color_label = 'k';
    end

    % Etiqueta del parámetro
    uilabel(parent, 'Position', [20 y_pos 160 22], 'Text', label_text, ...
        'FontWeight', 'bold', 'FontColor', color_label);
    
    % Campo numérico editable con formato y límites configurados
    num_field = uieditfield(parent, 'numeric', ...
        'Position', [185 y_pos 100 24], ...
        'Limits', [min_val max_val], ...
        'Value', start_val, ...
        'ValueDisplayFormat', fmt, ...
        'FontWeight', 'bold', ...
        'FontColor', color_label);
    
    % Slider
    sld = uislider(parent, ...
        'Position', [20 y_pos-22 265 3], ...
        'Limits', [min_val max_val], ...
        'Value', start_val);
end

% --- CONEXIÓN BIDIRECCIONAL SLIDER <-> CAMPO NUMÉRICO ---
function conectar_control(sld, num_field, min_val, max_val, update_fcn)
    % 1. Arrastre en tiempo real del slider (ValueChanging)
    sld.ValueChangingFcn = @(src, event) on_slider_changing(event.Value, sld, num_field, min_val, max_val, update_fcn);
    
    % 2. Cambio final del slider al soltar (ValueChanged)
    sld.ValueChangedFcn = @(src, event) on_slider_changed(src.Value, sld, num_field, min_val, max_val, update_fcn);
    
    % 3. Edición directa del campo numérico con Enter / desenfoque (ValueChanged)
    num_field.ValueChangedFcn = @(src, event) on_field_changed(src.Value, sld, num_field, min_val, max_val, update_fcn);
end

function on_slider_changing(raw_val, ~, num_field, min_val, max_val, update_fcn)
    val = validar_y_acotar(raw_val, min_val, max_val, num_field.Value);
    num_field.Value = val;
    update_fcn();
end

function on_slider_changed(raw_val, sld, num_field, min_val, max_val, update_fcn)
    val = validar_y_acotar(raw_val, min_val, max_val, sld.Value);
    sld.Value = val;
    num_field.Value = val;
    update_fcn();
end

function on_field_changed(raw_val, sld, num_field, min_val, max_val, update_fcn)
    val = validar_y_acotar(raw_val, min_val, max_val, sld.Value);
    num_field.Value = val;
    sld.Value = val;
    update_fcn();
end

% --- VALIDACIÓN ROBUSTA DE ENTRADA (Límites, NaN, no-escalares) ---
function val = validar_y_acotar(val, min_val, max_val, fallback)
    if isempty(val) || ~isnumeric(val) || ~isscalar(val) || ~isreal(val) || isnan(val) || isinf(val)
        val = fallback;
    else
        val = max(min_val, min(max_val, double(val)));
    end
end

% --- FUNCIÓN DE ACTUALIZACIÓN Y RENDERIZADO OPTIMIZADO (XData/YData/Position) ---
function actualizar_grafico(ax, ctrl, A, B, R)
    % Recuperar handles gráficos persistentes y caché de trayectoria
    state = ax.UserData;
    if isempty(state) || ~isfield(state, 'gh') || ~isvalid(state.gh.h_ground)
        gh = inicializar_graficos(ax);
        cache = struct('geom', [], 'Px_full', [], 'Py_full', [], 'desviacion_x', NaN);
        state = struct('gh', gh, 'cache', cache);
        ax.UserData = state;
    else
        gh = state.gh;
        cache = state.cache;
    end

    % 1. Extraer valores actuales de los campos sincronizados
    theta = ctrl.num_theta.Value;
    k_AD = ctrl.num_AD.Value;
    k_BC = ctrl.num_BC.Value;
    k_CD = ctrl.num_CD.Value;
    k_DP = ctrl.num_DP.Value;
    delta = ctrl.num_delta.Value;
    r_rueda = ctrl.num_Rueda.Value;
    
    AD = k_AD * R; 
    BC = k_BC * R; 
    CD = k_CD * R; 
    DP = k_DP * R;

    % 2. CACHÉ DE TRAYECTORIA: Recalcular solo si la geometría relevante cambió
    geom_actual = [k_AD, k_BC, k_CD, k_DP, delta];
    if isempty(cache.geom) || ~isequal(cache.geom, geom_actual)
        [cache.Px_full, cache.Py_full, cache.desviacion_x] = ...
            calcular_trayectoria_base(AD, BC, CD, DP, delta, A, B, gh.theta_full);
        cache.geom = geom_actual;
        state.cache = cache;
        ax.UserData = state;
    end

    % 3. Cinemática de la posición actual (theta)
    D = A + [AD*cosd(theta), AD*sind(theta)];
    vec_BD = B - D;
    d_BD = hypot(vec_BD(1), vec_BD(2));
    
    if d_BD > (BC + CD) || d_BD < abs(BC - CD)
        title(ax, 'ERROR CINEMÁTICO: Mecanismo fuera de alcance', 'Color', 'r', 'FontSize', 14);
        set(gh.mecanismo_objs, 'Visible', 'off');
        drawnow limitrate nocallbacks;
        return;
    end
    
    % Restaurar visibilidad si estaba oculta
    set(gh.mecanismo_objs, 'Visible', 'on');
    
    a = (CD^2 - BC^2 + d_BD^2) / (2*d_BD);
    h = sqrt(max(0, CD^2 - a^2));
    inv_d = 1 / d_BD;
    P2 = D + a * vec_BD * inv_d;
    C = [P2(1) + h*vec_BD(2)*inv_d, P2(2) - h*vec_BD(1)*inv_d];
    ang_DC = atan2d(C(2)-D(2), C(1)-D(1));
    P = D + [DP*cosd(ang_DC + delta), DP*sind(ang_DC + delta)];
    
    % --- TRASLACIÓN DE COORDENADAS (Suelo en Y = 0) ---
    punto_mas_bajo = P(2) - r_rueda;
    dy = -punto_mas_bajo; 
    
    A_pl = A + [0, dy];
    B_pl = B + [0, dy];
    C_pl = C + [0, dy];
    D_pl = D + [0, dy];
    P_pl = P + [0, dy];
    
    % --- ACTUALIZACIÓN DE PROPIEDADES EN OBJETOS PERSISTENTES ---
    % 1. Chasis
    gh.h_chasis.Position = [-7, -3 + dy, 14, 10];
    
    % 2. Trayectoria de referencia trasladada
    if ~isempty(cache.Px_full)
        gh.h_traj.XData = cache.Px_full;
        gh.h_traj.YData = cache.Py_full + dy;
        gh.h_traj.Visible = 'on';
    else
        gh.h_traj.Visible = 'off';
    end
    
    % 3. Barras del mecanismo
    gh.h_bar_AD.XData = [A_pl(1), D_pl(1)];
    gh.h_bar_AD.YData = [A_pl(2), D_pl(2)];
    
    gh.h_bar_BC.XData = [B_pl(1), C_pl(1)];
    gh.h_bar_BC.YData = [B_pl(2), C_pl(2)];
    
    gh.h_bar_CD.XData = [C_pl(1), D_pl(1)];
    gh.h_bar_CD.YData = [C_pl(2), D_pl(2)];
    
    gh.h_bar_DP.XData = [D_pl(1), P_pl(1)];
    gh.h_bar_DP.YData = [D_pl(2), P_pl(2)];
    
    % 4. Patch triangular CDP
    gh.h_patch_CDP.XData = [C_pl(1), D_pl(1), P_pl(1)];
    gh.h_patch_CDP.YData = [C_pl(2), D_pl(2), P_pl(2)];
    
    % 5. Motor y Rueda
    gh.h_motor.XData = A_pl(1);
    gh.h_motor.YData = A_pl(2);
    
    gh.h_rueda_circ.XData = P_pl(1) + r_rueda * gh.cos_rueda;
    gh.h_rueda_circ.YData = P_pl(2) + r_rueda * gh.sin_rueda;
    
    gh.h_rueda_centro.XData = P_pl(1);
    gh.h_rueda_centro.YData = P_pl(2);
    
    % 6. Cálculo de Altura Total y Título
    tope_chasis_relativo = 7;
    altura_total = tope_chasis_relativo + dy;
    
    title_str = sprintf('\\theta_{Motor}: %.1f^\\circ | \\Delta x_{Max}: %.2f cm | Altura Total: %.2f cm', ...
        theta, cache.desviacion_x, altura_total);
    title(ax, title_str, 'FontSize', 14, 'Interpreter', 'tex', 'Color', 'k');
    
    % Forzar refresco eficiente sin saturar callbacks
    drawnow limitrate nocallbacks;
end

% --- FUNCIÓN PARA EXPORTAR VARIABLES AL WORKSPACE ---
function exportar_datos(ctrl, A, B, R)
    parametros.k_AD = ctrl.num_AD.Value;
    parametros.k_BC = ctrl.num_BC.Value;
    parametros.k_CD = ctrl.num_CD.Value;
    parametros.k_DP = ctrl.num_DP.Value;
    parametros.delta = ctrl.num_delta.Value;
    parametros.r_rueda = ctrl.num_Rueda.Value;
    parametros.R = R;
    
    theta_eval = linspace(320, 350, 500); 
    n_eval = length(theta_eval);
    Px = zeros(1, n_eval);
    Py = zeros(1, n_eval);
    valido = false(1, n_eval);
    
    AD = parametros.k_AD * R; 
    BC = parametros.k_BC * R; 
    CD = parametros.k_CD * R; 
    DP = parametros.k_DP * R; 
    delta = parametros.delta;
    
    bc_plus_cd = BC + CD;
    bc_minus_cd_abs = abs(BC - CD);
    cd_sq_minus_bc_sq = CD^2 - BC^2;
    cd_sq = CD^2;
    
    for i = 1:n_eval
        th = theta_eval(i);
        D_t = A + [AD*cosd(th), AD*sind(th)];
        vec_BD = B - D_t;
        d_BD_t = hypot(vec_BD(1), vec_BD(2));
        
        if d_BD_t > bc_plus_cd || d_BD_t < bc_minus_cd_abs
            continue; 
        end
        
        a_t = (cd_sq_minus_bc_sq + d_BD_t^2) / (2*d_BD_t);
        h_t = sqrt(max(0, cd_sq - a_t^2));
        inv_d = 1 / d_BD_t;
        P2_t = D_t + a_t * vec_BD * inv_d;
        C_t = [P2_t(1) + h_t*vec_BD(2)*inv_d, P2_t(2) - h_t*vec_BD(1)*inv_d];
        ang_DC_t = atan2d(C_t(2)-D_t(2), C_t(1)-D_t(1));
        P_t = D_t + [DP*cosd(ang_DC_t + delta), DP*sind(ang_DC_t + delta)];
        
        Px(i) = P_t(1); 
        Py(i) = P_t(2);
        valido(i) = true;
    end
    
    Px = Px(valido); 
    Py = Py(valido); 
    theta_eval = theta_eval(valido);
    
    assignin('base', 'cinematica_parametros', parametros);
    assignin('base', 'trayectoria_Px', Px);
    assignin('base', 'trayectoria_Py', Py);
    assignin('base', 'trayectoria_theta', theta_eval);
    
    parent_fig = ancestor(ctrl.sld_AD, 'figure');
    if isempty(parent_fig)
        parent_fig = ctrl.sld_AD.Parent.Parent;
    end
    uialert(parent_fig, 'Datos exportados correctamente al Workspace (sistema relativo al motor A).', 'Exportación Exitosa', 'Icon', 'success');
end
