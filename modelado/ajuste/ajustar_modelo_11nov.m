%% AJUSTAR_MODELO_11NOV  El modelo contra lo medido el 10-11/11 con el robot de 1327 g (MED-008).
%
%  1. Estático: el centro de masa de la caja (corr_caja) y la inclinación de la IMU, para que el modelo dé
%     el equilibrio medido en las tres alturas (la ref del firmware con refauto, barridos del 11/11) y la altura
%     del centro de masa medida en 30° con las caídas y la prueba de inclinación (ajustar_caidas.py, 140 mm).
%  2. La inercia que les falta a las piezas (J_extra) para dar la medida en 30° (0,0124 kg m²).
%  3. Dinámico: con eso fijo, el rendimiento de la reductora (eta), un roce viscoso de la rueda contra el piso
%     (b_x), uno más en el eje rueda-cuerpo (b_extra) y un retardo puro, para que la planta del modelo siga a la
%     medida con los barridos (frf_barridos.py: cabeceo y avance por unidad de PWM, de 2 a 9,5 Hz, las tres
%     alturas a la vez).
%
%  Imprime las líneas para la variante 'ajustada' de parametros_fisicos.m y deja fig_modelo_11nov.png.

aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
raiz = fileparts(fileparts(aqui));
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));

%% Lo medido
M_TOTAL = 1.327;  L30 = 0.1403;  J30 = 0.0124;           % ajustar_caidas.py (cuerpo sin las ruedas)
T = readtable(fullfile(aqui, 'barridos_2026-11-11_frf.csv'));
patas = unique(T.pata)';
eq_medido = arrayfun(@(p) T.ref(find(T.pata == p, 1)), patas);   % [°] la IMU en el equilibrio
v_bat = arrayfun(@(p) T.v_bat(find(T.pata == p, 1)), patas);

f0 = parametros_fisicos('ajustada');
f0.m_carga = f0.m_carga + (1e3 * M_TOTAL - masa_total(f0));    % lo que falta para pesar 1327 g, en la cabina

%% 1. Estático: x = [imu_delta_deg, corr_x_mm, corr_z_mm] (corr_caja: x hacia atrás, z arriba, como en parametros_fisicos)
res_est = @(x) [arrayfun(@(p) equilibrio(f_con(f0, x), p), patas) - eq_medido, ...
                (largo(f_con(f0, x), 30) - L30) * 1e3 / 2];      % 2 mm pesan como 1°
op = optimoptions('lsqnonlin', 'Display', 'off', 'FunctionTolerance', 1e-12, 'StepTolerance', 1e-10);
x_est = lsqnonlin(res_est, [f0.imu_delta_deg, f0.corr_caja], [], [], op);
f1 = f_con(f0, x_est);
e = res_est(x_est);
fprintf('1. Equilibrio: medido %s°, modelo %s° | l(30) = %.1f mm (medido %.1f)\n', mat2str(round(eq_medido, 2)), ...
    mat2str(round(eq_medido + e(1:end-1), 2)), 1e3 * largo(f1, 30), 1e3 * L30);
fprintf('   imu_delta_deg = %.2f; corr_caja = [%.1f %.1f]; m_carga = %.0f\n', x_est, f1.m_carga);
for p = patas
    q = parametros_pendulo_invertido(f1, p + f1.pata_cero);
    fprintf('   patas %2d: l = %.1f mm, J propia (piezas) = %.4f kg m2\n', p, 1e3 * q.l, q.J_cuerpo);
end

%% 2. La inercia que falta
q = parametros_pendulo_invertido(f1, 30 + f1.pata_cero);
f1.J_extra = J30 - q.J_cuerpo;
fprintf('2. J_extra = %.4f kg m2 (las piezas dan %.4f en 30°; medido %.4f)\n', f1.J_extra, q.J_cuerpo, J30);

%% 3. Dinámico: y = [eta, b_x (N s/m), b_extra (N m s/rad), retardo (s)]
banda = T.f_hz >= 2 & T.f_hz <= 9.5;
D = T(banda, :);
res_din = @(y) residuo_planta(f1, y, D, patas, v_bat);
lb = [0.2 0 0 0];  ub = [1 60 0.2 0.04];
fprintf('3. Planta (cabeceo y avance por unidad de PWM, 2 a 9,5 Hz, las tres alturas):\n');
ELEGIDO = 3;        % el roce de la reductora como amortiguamiento en el eje (lo que hace el roce seco con poca amplitud)
casos = {'como estaba (eta 0,75, sin roces extra, sin retardo)', [0.75 0 0 0], false(1, 4)
         'rendimiento + retardo',                               [0.75 0 0 0.005], [1 0 0 1]
         'roce en el eje + retardo (eta 0,75)',                 [0.75 0 0.01 0.005], [0 0 1 1]
         'roce con el piso + retardo (eta 0,75)',               [0.75 5 0 0.005], [0 1 0 1]
         'rendimiento + roce en el eje + retardo',              [0.75 0 0.01 0.005], [1 0 1 1]
         'todo',                                                [0.75 5 0.01 0.005], [1 1 1 1]};
y_fin = [];
for k = 1:size(casos, 1)
    y0 = casos{k, 2};  libre = logical(casos{k, 3});
    if any(libre)
        arm = @(z) setfield_vec(y0, libre, z);
        z = lsqnonlin(@(z) res_din(arm(z)), y0(libre), lb(libre), ub(libre), op);
        y = arm(z);
    else
        y = y0;
    end
    r = res_din(y);
    fprintf('   %-50s eta %.2f  b_x %5.2f  b_extra %.4f  retardo %4.1f ms -> error %.3f\n', casos{k, 1}, y(1), ...
        y(2), y(3), 1e3 * y(4), sqrt(mean(r.^2)));
    if k == ELEGIDO, y_fin = y; end
end

%% Lo que queda, para parametros_fisicos.m
fprintf('\nPara la variante ''ajustada'' (11/11):\n');
fprintf('  o.m_carga = %.0f;  o.corr_caja = [%.1f %.1f];  o.imu_delta_deg = %.2f;  o.J_extra = %.4f;\n', ...
    f1.m_carga, f1.corr_caja, f1.imu_delta_deg, f1.J_extra);
fprintf('  o.eta_reductor = %.2f;  o.b_x = %.2f;  o.b_eje_extra = %.4f;  o.retardo_s = %.4f;  (V_bat de los barridos %.2f)\n', ...
    y_fin(1), y_fin(2), y_fin(3), y_fin(4), mean(v_bat));

%% Figura
fig = figure('Visible', 'off', 'Position', [50 50 1500 800], 'Color', 'w');
colores = lines(3);
for ip = 1:numel(patas)
    p = patas(ip);  Dp = T(T.pata == p, :);  w = 2 * pi * Dp.f_hz;
    Pw = Dp.Pw_re + 1i * Dp.Pw_im;
    [Pw0, ~] = planta(f_con_din(f0, [0.75 0 0 0]), p, v_bat(ip), w);
    [Pw1, ~] = planta(f_con_din(f1, y_fin), p, v_bat(ip), w);
    subplot(2, 3, ip); hold on; grid on
    semilogx(Dp.f_hz, abs(Pw), 'o-', 'Color', colores(3, :), 'MarkerSize', 3, 'DisplayName', 'robot');
    semilogx(Dp.f_hz, abs(Pw0), '--', 'Color', [0.5 0.5 0.5], 'DisplayName', 'modelo del 7/11');
    semilogx(Dp.f_hz, abs(Pw1), '-', 'Color', colores(1, :), 'LineWidth', 1.3, 'DisplayName', 'modelo ajustado');
    set(gca, 'XScale', 'log'); xlim([1 20]); title(sprintf('patas %d°: |cabeceo / PWM|', p));
    if ip == 1, ylabel('rad/s'); legend('Location', 'northeast'); end
    subplot(2, 3, 3 + ip); hold on; grid on
    semilogx(Dp.f_hz, rad2deg(unwrap(angle(Pw))), 'o-', 'Color', colores(3, :), 'MarkerSize', 3);
    semilogx(Dp.f_hz, rad2deg(unwrap(angle(Pw0))), '--', 'Color', [0.5 0.5 0.5]);
    semilogx(Dp.f_hz, rad2deg(unwrap(angle(Pw1 .* exp(-1i * w * y_fin(4))))), '-', 'Color', colores(1, :), 'LineWidth', 1.3);
    set(gca, 'XScale', 'log'); xlim([1 20]); xlabel('Hz'); title('fase [°]');
end
sgtitle(sprintf(['Barridos del 11/11 contra el modelo: el del 7/11 y el ajustado (1327 g, l y J de las caídas, ' ...
    'eta %.2f, b_x %.1f N s/m, retardo %.1f ms)'], y_fin(1), y_fin(2), 1e3 * y_fin(4)));
exportgraphics(fig, fullfile(aqui, 'fig_modelo_11nov.png'), 'Resolution', 110);
fprintf('-> fig_modelo_11nov.png\n');

%% ------------------------------------------------------------------ funciones
function m = masa_total(f)
    n = f.n_servos;
    m = f.m_cabina + f.m_tapa + n * f.m_servo + f.m_bateria + f.m_electronica + f.m_tornilleria + f.m_carga + ...
        n * (f.m_AD + f.m_BC + f.m_CDP + f.m_motor + f.m_rueda);
end

function f = f_con(f, x)
    f.imu_delta_deg = x(1);  f.corr_caja = x(2:3);
end

function f = f_con_din(f, y)
    f.eta_reductor = y(1);  f.b_x_extra = y(2);  f.b_eje_extra = y(3);
end

function th = equilibrio(f, pata)
    q = parametros_pendulo_invertido(f, pata + f.pata_cero);
    th = f.imu_delta_deg + rad2deg(q.beta_equilibrio);
end

function l = largo(f, pata)
    q = parametros_pendulo_invertido(f, pata + f.pata_cero);
    l = q.l;
end

function [Pw, Pv] = planta(f, pata, V, w)
    q = parametros_pendulo_invertido(f, pata + f.pata_cero);
    if isfield(f, 'b_x_extra'), q.b_x = f.b_x_extra; end
    if isfield(f, 'b_eje_extra'), q.b_eje = q.b_eje + f.b_eje_extra; end
    [q, m] = motor_pendulo_invertido(q, f);
    L = linealizar_pendulo_invertido(q);
    B = m.beta_V * L.B * V;                    % por unidad de PWM
    s = 1i * w(:);
    Pw = zeros(size(s));  Pv = Pw;
    for k = 1:numel(s)
        X = (s(k) * eye(4) - L.A) \ B;
        Pw(k) = X(4);  Pv(k) = X(2);
    end
end

function r = residuo_planta(f, y, D, patas, v_bat)
    r = [];
    fy = f_con_din(f, y);
    for ip = 1:numel(patas)
        Dp = D(D.pata == patas(ip), :);
        w = 2 * pi * Dp.f_hz;
        [Pw, Pv] = planta(fy, patas(ip), v_bat(ip), w);
        d = exp(-1i * w * y(4));
        ew = log((Dp.Pw_re + 1i * Dp.Pw_im) ./ (Pw .* d));
        ev = log((Dp.Pv_re + 1i * Dp.Pv_im) ./ (Pv .* d));
        cw = sqrt(Dp.coh_w);  cv = sqrt(Dp.coh_v);
        r = [r; cw .* real(ew); cw .* imag(ew); cv .* real(ev); cv .* imag(ev)]; %#ok<AGROW>
    end
end

function v = setfield_vec(v, libre, z)
    v(libre) = z;
end
