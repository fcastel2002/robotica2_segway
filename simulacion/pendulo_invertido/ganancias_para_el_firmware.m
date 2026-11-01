%% GANANCIAS_PARA_EL_FIRMWARE  El LQR del modelo, en las unidades del firmware, probado en Simulink.
%
%  El modelo da K en voltios: V = -K z, con z = [x v phi omega] en (m, m/s, rad, rad/s).
%  El firmware no manda voltios sino una fraccion de PWM entre -1 y 1, y lo que llega al
%  motor es esa fraccion por la tension que deja pasar el driver. Por eso
%
%       u_pwm = k * z,     k = -K / V_motor,     V_motor = V_bat - caida del driver.
%
%  En el convenio del firmware (balance.h) todo es positivo hacia ADELANTE: x y v de los
%  encoders, phi de la IMU (menos la referencia) y u. Con ese convenio las cuatro k salen
%  positivas: inclinado hacia adelante, las ruedas avanzan para ponerse debajo.
%
%  Si la tension real no es la supuesta, el lazo ve la ganancia multiplicada por
%  g = V_real/V_motor. La seccion 4 busca entre que g sigue estable con el muestreo de
%  5 ms, un paso de retardo y el filtro de velocidad, y la 5 lo simula en Simulink
%  (pendulo_invertido_lqr.slx) con la bateria llena, nominal y baja.
%
%  Deja el resumen en resultados/ganancias_firmware.md y la figura en
%  resultados/ganancias_firmware.png.

clear; close all; clc

%% 1. Rutas =================================================================
aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
raiz = fileparts(fileparts(aqui));
addpath(fullfile(raiz, 'modelado', 'parametros'));
addpath(fullfile(raiz, 'modelado', 'cinematica'));
addpath(fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
addpath(aqui);

%% 2. Lo que conviene tocar =================================================
postura_deg  = 25;        % la misma postura de diseno que INICIAR_PENDULO_SIMULINK
max_phi_deg  = 8;
caida_driver = 2.0;       % [V] L298N del prototipo (firmware/docs/arquitectura_v0_1.md, sec. 10);
                          %     con el DRV8871 de la version final poner ~0
V_llena      = 12.6;      % [V] LiPo 3S: llena, nominal y baja
V_baja       = 9.6;
k_21_10      = [5.00 4.76 8.17 1.04];   % lo que se calculo el 21/10 (CTL-308), sin caida del driver

%% 3. K del modelo y ganancias del firmware =================================
fisicos = parametros_fisicos('segunda_iteracion');
p = parametros_pendulo_invertido(fisicos, postura_deg);
[p, motor] = motor_pendulo_invertido(p, fisicos);
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', max_phi_deg);

V_nominal = motor.V_bat;                    % 11,1 V
V_motor   = V_nominal - caida_driver;       % lo que supone el firmware
k_sin_caida = -C.K/V_nominal;
k_firmware  = -C.K/V_motor;

nombres = {'x [1/m]', 'v [1/(m/s)]', 'phi [1/rad]', 'omega [1/(rad/s)]'};
fprintf('K del modelo = [%.2f %.2f %.2f %.2f] V por (m, m/s, rad, rad/s)\n\n', C.K);
fprintf('%-18s %10s %12s %14s\n', 'ganancia', '21/10', 'hoy, sin', sprintf('hoy, %.1f V', V_motor));
fprintf('%-18s %10s %12s %14s\n', '', '(11,1 V)', 'caida', '(L298N)');
for i = 1:4
    fprintf('%-18s %10.3f %12.3f %14.3f\n', nombres{i}, k_21_10(i), k_sin_caida(i), k_firmware(i));
end
cambio = 100*(k_sin_caida./k_21_10 - 1);
fprintf('\nCambio del modelo desde el 21/10: %+.1f %% %+.1f %% %+.1f %% %+.1f %%\n', cambio);
fprintf('Por la caida del L298N las ganancias suben un %.0f %%\n\n', 100*(V_nominal/V_motor - 1));

%% 4. Robustez del lazo muestreado frente a la tension real ==================
% Mismo lazo que test_sobrevive_a_la_implementacion_real: muestreo de 5 ms con retencion,
% un paso de retardo de computo y la velocidad filtrada a 20 Hz.
Ts = fisicos.Ts;  wf = 2*pi*fisicos.fc_vel;
Af = [C.A, zeros(4,1); wf*[0 1 0 0], -wf];   Bf = [C.B; 0];
Kf = [C.K(1), 0, C.K(3), C.K(4), C.K(2)];
df = c2d(ss(Af, Bf, eye(5), 0), Ts, 'zoh');
radio = @(g) max(abs(eig([df.A, df.B; -g*Kf, 0])));
lo = 0.01;  hi = 1;
for it = 1:50, m = (lo + hi)/2; if radio(m) < 1, hi = m; else, lo = m; end, end
g_min = hi;
lo = 1;  hi = 10;
for it = 1:50, m = (lo + hi)/2; if radio(m) < 1, lo = m; else, hi = m; end, end
g_max = lo;
fprintf('Lazo muestreado estable si V_real/V_supuesta esta entre %.2f y %.2f\n', g_min, g_max);

escenarios = struct( ...
    'nombre', {'bateria llena', 'bateria nominal', 'bateria baja', 'DRV8871 sin actualizar'}, ...
    'V_real', {V_llena - caida_driver, V_motor, V_baja - caida_driver, V_nominal});
for e = 1:numel(escenarios)
    escenarios(e).g = escenarios(e).V_real/V_motor;
    escenarios(e).radio = radio(escenarios(e).g);
    fprintf('  %-24s V_real %5.1f V  g = %.2f  radio %.4f\n', escenarios(e).nombre, ...
        escenarios(e).V_real, escenarios(e).g, escenarios(e).radio);
end
fprintf('\n');

%% 5. Simulink: recuperacion y escalon de 30 cm en cada escenario ===========
modelo = 'pendulo_invertido_lqr';
archivo = fullfile(aqui, [modelo '.slx']);
if ~exist(archivo, 'file'), construir_pendulo_simulink(aqui, modelo); end
load_system(archivo);
tau_traccion = limite_de_traccion(p);

for e = 1:numel(escenarios)
    % El firmware aplica V_real * sat(k z) = sat(g * (-K z), V_real): en Simulink eso es
    % K multiplicada por g y la bateria en V_real.
    simular = @(phi0, x_dest, t_c, T) correr(modelo, escenarios(e).g*C.K, ...
        escenarios(e).V_real, motor, p, tau_traccion, phi0, x_dest, t_c, T);

    % (a) mayor inclinacion inicial de la que se recupera, de a 1 grado
    limite = 0;  tope = 45;
    for phi0 = 1:tope
        [~, z] = simular(phi0, 0, 0, 6);
        if abs(rad2deg(z(end,3))) < 0.5 && max(abs(z(:,3))) < pi/2
            limite = phi0;
        else
            break
        end
    end
    escenarios(e).recupera_txt = sprintf('%d grados', limite);
    if limite == tope, escenarios(e).recupera_txt = sprintf('%d grados o mas', tope); end

    % (b) arranca inclinado 5 grados, y en t = 2 s se le pide ir 30 cm adelante
    [t, z, U] = simular(5, 0.30, 2.0, 8);
    escenarios(e).t = t;  escenarios(e).z = z;  escenarios(e).U = U;
    escenarios(e).error_final_mm = 1e3*abs(z(end,1) - 0.30);
    fuera = find(abs(z(:,1) - 0.30) > 0.01 & t >= 2.0, 1, 'last');
    escenarios(e).llega_s = t(min(fuera + 1, numel(t))) - 2.0;
    escenarios(e).satura = 100*mean(abs(U(:,1)) >= escenarios(e).V_real - 1e-6);
    fprintf('  %-24s se recupera hasta %s | 30 cm: llega en %.2f s, error %.2f mm\n', ...
        escenarios(e).nombre, escenarios(e).recupera_txt, escenarios(e).llega_s, escenarios(e).error_final_mm);
end
close_system(modelo, 0);

%% 6. Figura y resumen ======================================================
carpeta = fullfile(aqui, 'resultados');
figure('Name', 'Ganancias para el firmware', 'Position', [60 60 1100 720], 'Color', 'w');
colores = lines(numel(escenarios));
for e = 1:numel(escenarios)
    s = escenarios(e);
    etiqueta = sprintf('%s (%.1f V)', s.nombre, s.V_real);
    subplot(3,1,1); hold on; plot(s.t, rad2deg(s.z(:,3)), 'LineWidth', 1.5, 'Color', colores(e,:), 'DisplayName', etiqueta);
    subplot(3,1,2); hold on; plot(s.t, 100*s.z(:,1), 'LineWidth', 1.5, 'Color', colores(e,:), 'DisplayName', etiqueta);
    subplot(3,1,3); hold on; plot(s.t, s.U(:,1)/s.V_real, 'LineWidth', 1.5, 'Color', colores(e,:), 'DisplayName', etiqueta);
end
subplot(3,1,1); grid on; ylabel('\phi [\circ]'); legend('Location', 'northeast');
title('Arranca inclinado 5\circ y en t = 2 s se le piden 30 cm: misma k en el firmware, distinta tension real');
subplot(3,1,2); grid on; ylabel('x [cm]'); yline(30, ':k', 'HandleVisibility', 'off');
subplot(3,1,3); grid on; ylabel('PWM'); xlabel('t [s]'); ylim([-1.1 1.1]);
yline([-1 1], '--r', 'HandleVisibility', 'off');
exportgraphics(gcf, fullfile(carpeta, 'ganancias_firmware.png'), 'Resolution', 150);

fid = fopen(fullfile(carpeta, 'ganancias_firmware.md'), 'w', 'n', 'UTF-8');
fprintf(fid, '# Ganancias del LQR para el firmware\n\n');
fprintf(fid, 'Generado por [`ganancias_para_el_firmware.m`](../ganancias_para_el_firmware.m) el %s, MATLAB %s.\n\n', ...
    char(datetime('now', 'Format', 'yyyy-MM-dd HH:mm')), version);
fprintf(fid, 'Ley del firmware: `u = kx*x + kv*v + kphi*phi + komega*omega`, con u en fraccion de PWM (-1 a 1), ');
fprintf(fid, 'todo positivo hacia adelante y phi = inclinacion de la IMU menos `ref`.\n\n');
fprintf(fid, 'K del modelo: [%.2f %.2f %.2f %.2f] V por (m, m/s, rad, rad/s), postura %g grados.\n\n', C.K, postura_deg);
fprintf(fid, '| Ganancia | 21/10 (11,1 V) | Hoy, sin caida (11,1 V) | **Hoy, L298N (%.1f V)** |\n|---|---|---|---|\n', V_motor);
claves = {'kx [1/m]', 'kv [1/(m/s)]', 'kphi [1/rad]', 'komega [1/(rad/s)]'};
for i = 1:4
    fprintf(fid, '| %s | %.3f | %.3f | **%.3f** |\n', claves{i}, k_21_10(i), k_sin_caida(i), k_firmware(i));
end
fprintf(fid, '\nCambio del modelo desde el 21/10: %+.1f %%, %+.1f %%, %+.1f %% y %+.1f %%. ', cambio);
fprintf(fid, 'La caida de %.1f V del L298N sube las cuatro un %.0f %%.\n\n', caida_driver, 100*(V_nominal/V_motor - 1));
fprintf(fid, 'Lazo muestreado (5 ms, un paso de retardo, velocidad filtrada a %g Hz): estable si la tension real ', fisicos.fc_vel);
fprintf(fid, 'dividida la supuesta esta entre **%.2f y %.2f**.\n\n', g_min, g_max);
fprintf(fid, '| Escenario en Simulink | V real | g | Radio espectral | Se recupera hasta | 30 cm: llega en | Error final |\n|---|---|---|---|---|---|---|\n');
for e = 1:numel(escenarios)
    s = escenarios(e);
    fprintf(fid, '| %s | %.1f V | %.2f | %.4f | %s | %.2f s | %.2f mm |\n', ...
        s.nombre, s.V_real, s.g, s.radio, s.recupera_txt, s.llega_s, s.error_final_mm);
end
fprintf(fid, '\nEl firmware corta a 30 grados (`TILT_LIMIT_DEG`): lo que pase de ahi es margen.\n');
fprintf(fid, '\n![Respuesta en cada escenario](ganancias_firmware.png)\n\n');
fprintf(fid, 'Alcance: planta no lineal con motor, bateria y agarre (pendulo_invertido_lqr.slx), control continuo con ');
fprintf(fid, 'el estado exacto. El muestreo, el retardo y el filtro entran solo en el radio espectral (lineal). ');
fprintf(fid, 'No estan la zona muerta del motor, el filtro complementario ni la cuantizacion del encoder: eso lo ');
fprintf(fid, 'prueba el banco del codigo C del firmware.\n');
fclose(fid);
fprintf('\nresumen -> %s\nfigura  -> %s\n', fullfile(carpeta, 'ganancias_firmware.md'), ...
    fullfile(carpeta, 'ganancias_firmware.png'));

%% ==========================================================================
function [t, z, U] = correr(modelo, K, V_bat, motor, p, tau_traccion, phi0_deg, x_destino, t_consigna, duracion)
    entrada = Simulink.SimulationInput(modelo);
    valores = {'K', K; 'V_bat', V_bat; 'beta_V', motor.beta_V; 'b_m', motor.b_m; ...
        'tau_traccion', tau_traccion; 'a', p.a; 'h', p.h; 'j', p.j; 'k', p.k; ...
        'e_acople', p.e_acople; 'r', p.r; 'b_eje', p.b_eje_mecanico; 'b_x', p.b_x; ...
        'b_phi', p.b_phi; 'q0', [0; deg2rad(phi0_deg)]; 'q_punto0', [0; 0]; ...
        'x_destino', x_destino; 't_consigna', t_consigna; 'duracion', duracion};
    for i = 1:size(valores, 1)
        entrada = entrada.setVariable(valores{i,1}, valores{i,2});
    end
    entrada = entrada.setModelParameter('StopTime', num2str(duracion));
    salida = sim(entrada);
    t = salida.sl_z.time;
    z = salida.sl_z.signals.values;
    U = salida.sl_tension.signals.values;
end
