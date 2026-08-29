function optimizar_barrido_objetivo()
    % --- 1. PARÁMETROS BASE Y LIMITES (±10%) ---
    R = 10;
    A = [0, 0]; 
    B = [R*cosd(45), R*sind(45)];
    theta_vec = linspace(320, 350, 50); 
    
    p_base = [1.4, 1.4, 0.51, 1.4, 170]; 
    
    % NUEVO: Coordenada X (en cm) donde quieres alinear la vertical
    x_objetivo = 0; 
    
    N = 7; % Puntos por variable (16,807 iteraciones en total)
    
    fprintf('Generando espacio de búsqueda... \n');
    rango = @(val) linspace(val*0.9, val*1.1, N);
    [AD_g, BC_g, CD_g, DP_g, delta_g] = ndgrid(...
        rango(p_base(1)), rango(p_base(2)), rango(p_base(3)), ...
        rango(p_base(4)), rango(p_base(5)));
    
    combinaciones = [AD_g(:), BC_g(:), CD_g(:), DP_g(:), delta_g(:)];
    total_iter = size(combinaciones, 1);
    
    % --- 2. BUCLE CON PENALIZACIÓN DE OFFSET ---
    mejor_costo = inf;
    mejor_delta_x = inf;
    mejor_error_cm = inf;
    mejor_parametros = p_base;
    
    % PESO DE ALINEACIÓN: Multiplicador para forzar el mecanismo hacia x_objetivo
    peso_centrado = 3.0; 
    
    fprintf('Evaluando %d combinaciones con objetivo en X = %.2f...\n', total_iter, x_objetivo);
    tic; 
    
    for i = 1:total_iter
        p_actual = combinaciones(i, :);
        AD = p_actual(1)*R; BC = p_actual(2)*R; 
        CD = p_actual(3)*R; DP = p_actual(4)*R; delta = p_actual(5);
        
        valido = true;
        Px_min = inf; Px_max = -inf;
        
        for th = theta_vec
            D = A + [AD*cosd(th), AD*sind(th)];
            d_BD = norm(B - D);
            
            if d_BD > (BC + CD) || d_BD < abs(BC - CD)
                valido = false; break; 
            end
            
            a = (CD^2 - BC^2 + d_BD^2) / (2*d_BD);
            h = sqrt(max(0, CD^2 - a^2));
            P2 = D + a * (B - D) / d_BD;
            C = [P2(1) + h*(B(2)-D(2))/d_BD, P2(2) - h*(B(1)-D(1))/d_BD];
            ang_DC = atan2d(C(2)-D(2), C(1)-D(1));
            
            Px = D(1) + DP*cosd(ang_DC + delta);
            
            if Px < Px_min, Px_min = Px; end
            if Px > Px_max, Px_max = Px; end
        end
        
        if valido
            delta_x = Px_max - Px_min;
            
            % AHORA: Calcula la distancia máxima respecto a tu x_objetivo
            error_cm = max(abs(Px_max - x_objetivo), abs(Px_min - x_objetivo));
            
            % Criterio: Minimizar suma ponderada
            costo = delta_x + (peso_centrado * error_cm);
            
            if costo < mejor_costo
                mejor_costo = costo;
                mejor_delta_x = delta_x;
                mejor_error_cm = error_cm;
                mejor_parametros = p_actual;
            end
        end
    end
    
    tiempo = toc;
    fprintf('¡Optimización completada en %.2f segundos!\n\n', tiempo);
    
    % --- 3. RESULTADOS ---
    fprintf('=== RESULTADOS CENTRADOS EN X = %.2f ===\n', x_objetivo);
    fprintf('k_AD:    %.4f\n', mejor_parametros(1));
    fprintf('k_BC:    %.4f\n', mejor_parametros(2));
    fprintf('k_CD:    %.4f\n', mejor_parametros(3));
    fprintf('k_DP:    %.4f\n', mejor_parametros(4));
    fprintf('Delta:   %.2fº\n', mejor_parametros(5));
    fprintf('-------------------------------------\n');
    fprintf('Linealidad (Delta x): %.4f cm\n', mejor_delta_x);
    fprintf('Desvío Máx respecto a X=%.2f: %.4f cm\n', x_objetivo, mejor_error_cm);
    fprintf('=====================================\n');
    
    % --- 4. GRÁFICA ---
    graficar_comparativa(p_base, mejor_parametros, theta_vec, R, A, B, x_objetivo);
end

function graficar_comparativa(p_base, p_opt, theta_vec, R, A, B, x_objetivo)
    [Px_base, Py_base] = calcular_trayectoria(p_base, theta_vec, R, A, B);
    [Px_opt, Py_opt] = calcular_trayectoria(p_opt, theta_vec, R, A, B);
    
    figure('Name', 'Comparativa Diseño Base vs Desplazado', 'Color', 'w', 'Position', [200 200 600 500]);
    plot(Px_base, Py_base, 'r--', 'LineWidth', 2, 'DisplayName', 'Diseño Base'); hold on;
    plot(Px_opt, Py_opt, 'b-', 'LineWidth', 2.5, 'DisplayName', 'Diseño Optimizado');
    
    % AHORA: Dibujar la línea en la coordenada x_objetivo
    plot([x_objetivo x_objetivo], [-40 10], 'k:', 'LineWidth', 1.5, 'DisplayName', sprintf('Eje Objetivo (x=%.1f)', x_objetivo));
    
    grid on; axis equal;
    xlabel('Posición X (cm)', 'FontWeight', 'bold');
    ylabel('Posición Y (cm)', 'FontWeight', 'bold');
    title(sprintf('Optimización con Objetivo en X = %.1f cm', x_objetivo), 'FontSize', 12);
    legend('Location', 'best', 'FontSize', 11);
end

function [Px, Py] = calcular_trayectoria(p, theta_vec, R, A, B)
    AD = p(1)*R; BC = p(2)*R; CD = p(3)*R; DP = p(4)*R; delta = p(5);
    Px = zeros(1, length(theta_vec)); Py = zeros(1, length(theta_vec));
    for i = 1:length(theta_vec)
        th = theta_vec(i);
        D = A + [AD*cosd(th), AD*sind(th)];
        d_BD = norm(B - D);
        a = (CD^2 - BC^2 + d_BD^2) / (2*d_BD);
        h = sqrt(max(0, CD^2 - a^2));
        P2 = D + a * (B - D) / d_BD;
        C = [P2(1) + h*(B(2)-D(2))/d_BD, P2(2) - h*(B(1)-D(1))/d_BD];
        ang_DC = atan2d(C(2)-D(2), C(1)-D(1));
        Px(i) = D(1) + DP*cosd(ang_DC + delta);
        Py(i) = D(2) + DP*sind(ang_DC + delta);
    end
end