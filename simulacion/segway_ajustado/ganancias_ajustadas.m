%% GANANCIAS_AJUSTADAS  El LQR recalculado con el modelo AJUSTADO (3/11), para cada altura de pata.
%
%  Mismo criterio que simulacion/pendulo_invertido/ganancias_para_el_firmware.m (Bryson con
%  max_phi 8 grados y R x64, el "suave" que equilibró el robot el 29/10), pero con la variante
%  'ajustada' de parametros_fisicos.m y en cada altura de pata del firmware (0 a 30). En unidades
%  del firmware: k = -K / V_motor, con V_motor = V_bat - caida_driver.
%
%  También evalúa las ganancias que tiene hoy el firmware (las del modelo viejo en la pata 15) sobre
%  el modelo ajustado: polos del lazo muestreado (5 ms, un paso de retardo, velocidad filtrada a
%  20 Hz) y margen de ganancia. Escribe ganancias_ajustadas.csv.

clear; clc
aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
raiz = fileparts(fileparts(aqui));
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));

f = parametros_fisicos('ajustada');
V_motor = f.V_bat - f.caida_driver;
k_hoy = [1.52 2.73 4.14 0.478];             % board_config.h (modelo viejo, pata 15, factor_R 64)
patas = (0:5:30)';
Ts = f.Ts;  wf = 2*pi*f.fc_vel;

fprintf('Modelo ajustado: V_motor %.1f V; pata del firmware = postura del modelo - %.1f\n\n', V_motor, f.pata_cero);
fprintf('pata   l [mm]  polo inest. | LQR ajustado k = [kx kv kphi kw]   g_max | ganancias de hoy: radio  g_max  (z min)\n');
T = zeros(numel(patas), 9);
for i = 1:numel(patas)
    p = parametros_pendulo_invertido(f, patas(i) + f.pata_cero);
    [p, ~] = motor_pendulo_invertido(p, f);
    C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8, 'factor_R', 64);
    k = -C.K/V_motor;
    [~, ~, gmax_aj] = lazo_muestreado(C.A, C.B, k, V_motor, Ts, wf);
    [rho_hoy, ~, gmax_hoy] = lazo_muestreado(C.A, C.B, k_hoy, V_motor, Ts, wf);
    cl = eig(C.A + C.B*(k_hoy*V_motor));
    zeta = min(-real(cl)./abs(cl));
    T(i, :) = [patas(i), k, 1e3*p.l, max(real(eig(C.A))), gmax_aj, gmax_hoy];
    fprintf('%4.0f   %5.1f   %6.2f 1/s | [%5.2f %5.2f %5.2f %5.3f]   %5.2f | %6.3f  %5.2f  (%.2f)\n', ...
        patas(i), 1e3*p.l, max(real(eig(C.A))), k, gmax_aj, rho_hoy, gmax_hoy, zeta);
end
writetable(array2table(T, 'VariableNames', {'pata', 'kx', 'kv', 'kphi', 'kw', 'l_mm', 'polo', ...
    'gmax_ajustado', 'gmax_hoy'}), fullfile(aqui, 'ganancias_ajustadas.csv'));
fprintf('\ng_max: cuántas veces más ganancia aguanta el lazo muestreado antes de oscilar\n');
fprintf('-> ganancias_ajustadas.csv\n');

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
