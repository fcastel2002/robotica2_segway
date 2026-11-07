%% GANANCIAS_AJUSTADAS  El LQR recalculado con el modelo AJUSTADO, para cada altura de pata.
%
%  Mismo criterio que simulacion/pendulo_invertido/ganancias_para_el_firmware.m (Bryson con
%  max_phi 8 grados y R x64, el "suave" que equilibró el robot el 29/10), pero con la variante
%  'ajustada' de parametros_fisicos.m y en cada altura de pata del firmware (0 a 30). En unidades
%  del firmware: k = -K / V_motor, con V_motor = V_bat - caida_driver.
%
%  También evalúa las tablas que tiene hoy el firmware (LQR_TABLA y LQR_TABLA_DRV de
%  segway_v02/main/board_config.h) sobre el modelo ajustado: polos del lazo muestreado (5 ms, un
%  paso de retardo, velocidad filtrada a 20 Hz) y margen de ganancia. Escribe ganancias_ajustadas.csv
%  (el modelo de hoy: 3/11 con el L298N, 7/11 con el DRV8871) e imprime la tabla para board_config.h.

clear; clc
aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
raiz = fileparts(fileparts(aqui));
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));

f = parametros_fisicos('ajustada');
V_motor = f.V_bat - f.caida_driver;
config = fileread(fullfile(raiz, 'firmware', 'segway_v02', 'main', 'board_config.h'));
patas_fw = numeros(config, 'LQR_TABLA_PATAS_DEG');
tablas = {'LQR_TABLA', 'LQR_TABLA_DRV'};
k_fw = cell(size(tablas));
for j = 1:numel(tablas)
    v = numeros(config, tablas{j});
    if ~isempty(v), k_fw{j} = reshape(v, 4, [])'; end
end
patas = (0:5:30)';
Ts = f.Ts;  wf = 2*pi*f.fc_vel;

fprintf('Modelo ajustado: %.0f g, V_motor %.1f V; pata del firmware = postura del modelo - %.1f\n\n', ...
    f.m_carga + 962, V_motor, f.pata_cero);
fprintf('pata   l [mm]  polo inest. | LQR ajustado k = [kx kv kphi kw]   g_max |');
for j = 1:numel(tablas)
    if ~isempty(k_fw{j}), fprintf(' %s: g_max (z min) |', tablas{j}); end
end
fprintf('\n');
T = zeros(numel(patas), 9);
for i = 1:numel(patas)
    p = parametros_pendulo_invertido(f, patas(i) + f.pata_cero);
    [p, ~] = motor_pendulo_invertido(p, f);
    C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8, 'factor_R', 64);
    k = -C.K/V_motor;
    [~, ~, gmax_aj] = lazo_muestreado(C.A, C.B, k, V_motor, Ts, wf);
    T(i, 1:8) = [patas(i), k, 1e3*p.l, max(real(eig(C.A))), gmax_aj];
    fprintf('%4.0f   %5.1f   %6.2f 1/s | [%5.2f %5.2f %5.2f %5.3f]   %5.2f |', ...
        patas(i), 1e3*p.l, max(real(eig(C.A))), k, gmax_aj);
    for j = 1:numel(tablas)
        if isempty(k_fw{j}), continue, end
        kj = interp1(patas_fw(:), k_fw{j}, patas(i));
        [~, ~, gmax_j] = lazo_muestreado(C.A, C.B, kj, V_motor, Ts, wf);
        cl = eig(C.A + C.B*(kj*V_motor));
        if j == 1, T(i, 9) = gmax_j; end
        fprintf('   %5.2f  (%.2f)          |', gmax_j, min(-real(cl)./abs(cl)));
    end
    fprintf('\n');
end
writetable(array2table(T, 'VariableNames', {'pata', 'kx', 'kv', 'kphi', 'kw', 'l_mm', 'polo', ...
    'gmax_ajustado', 'gmax_hoy'}), fullfile(aqui, 'ganancias_ajustadas.csv'));
fprintf('\ng_max: cuántas veces más ganancia aguanta el lazo muestreado antes de oscilar\n');
fprintf('z min: el amortiguamiento más bajo del lazo continuo con esa tabla\n');
fprintf('-> ganancias_ajustadas.csv\n\nPara board_config.h (filas de la pata 0 a la 30 de a 5):\n{ ');
for i = 1:numel(patas)
    fprintf('{ %.2ff, %.2ff, %.2ff, %.3ff }', T(i, 2:5));
    if i < numel(patas), fprintf(', '); end
    if mod(i, 2) == 0 && i < numel(patas), fprintf('\\\n  '); end
end
fprintf(' }\n');

function v = numeros(texto, nombre)
    % Los números de un #define de board_config.h (puede seguir en varias líneas con \)
    m = regexp(texto, ['#define\s+' nombre '\s+(\{(?:[^\n]*\\\s*\n)*[^\n]*)'], 'tokens', 'once');
    if isempty(m), v = []; return, end
    v = str2double(regexp(m{1}, '-?\d+(\.\d+)?(?=f)', 'match'));
end

function [rho, gmin, gmax] = lazo_muestreado(A, B, k, V_motor, Ts, wf)
    % u = k z en PWM, el motor recibe V_motor*u; velocidad filtrada; un paso de retardo
    K = -k*V_motor;
    Af = [A, zeros(4, 1); wf*[0 1 0 0], -wf];  Bf = [B; 0];
    Kf = [K(1), 0, K(3), K(4), K(2)];
    d = c2d(ss(Af, Bf, eye(5), 0), Ts, 'zoh');
    radio = @(g) max(abs(eig([d.A, d.B; -g*Kf, 0])));
    rho = radio(1);
    lo = 0.01; hi = 1;  for it = 1:40, m = (lo + hi)/2; if radio(m) < 1, hi = m; else, lo = m; end, end
    gmin = hi;
    lo = 1; hi = 20;    for it = 1:40, m = (lo + hi)/2; if radio(m) < 1, lo = m; else, hi = m; end, end
    gmax = lo;
end
