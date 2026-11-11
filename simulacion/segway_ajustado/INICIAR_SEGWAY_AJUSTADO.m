%% INICIAR_SEGWAY_AJUSTADO  El modelo del Segway AJUSTADO con el robot (3/11/2026) en Simulink.
%
%  Es una copia aparte de simulacion/segway_completo (que queda como estaba): mismos seis bloques,
%  con los numeros de la variante 'ajustada' de parametros_fisicos.m y con lo que el firmware hace
%  de verdad: el LQR en fraccion de PWM cada 5 ms con un ciclo de retardo, el rechaza banda, la
%  zona muerta compensada, el roce seco del motor y la banda muerta del servo. Que se corrigio y
%  por que: modelado/ajuste/ajuste_del_modelo.md.
%
%  Por defecto repite la prueba del 3/11 (sesion_placa.py identificar): el robot quieto con las
%  patas en pata_fw y una onda cuadrada de +-1,5 grados en la ref, y lo compara con lo medido.
%  Abrir y pulsar Run.

clear; close all; clc

%% 1. Rutas ================================================================
aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
raiz = fileparts(fileparts(aqui));
addpath(fullfile(raiz, 'modelado', 'parametros'));
addpath(fullfile(raiz, 'modelado', 'cinematica'));
addpath(fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
addpath(aqui);

%% 2. LO QUE CONVIENE TOCAR ================================================
% --- el robot
pata_fw        = 20;        % [grados] pata del FIRMWARE (0 agachado, 30 estirado; la del joystick)
ganancias      = 'firmware';% 'firmware' = las de board_config.h; 'ajustadas' = LQR del modelo ajustado en esta pata
% 11/11: el control de hoy (segway_v02): LQR_TABLA_DRV según la pata, por lqrfac (kphi, kw) y lqrfacx (kx, kv)
tabla_drv      = [1.25 2.10 3.13 0.329; 1.25 2.10 3.34 0.364; 1.25 2.10 3.52 0.399; 1.25 2.11 3.69 0.435; ...
                  1.25 2.11 3.85 0.470; 1.25 2.12 4.00 0.506; 1.25 2.13 4.15 0.544];   % patas 0:5:30
k_firmware     = interp1((0:5:30)', tabla_drv, pata_fw) .* [0.86 0.86 0.87 0.87];
db_fw          = 0.03;      % zona muerta compensada (DEFAULT_DEADBAND)
notch_hz       = 11.6;      % rechaza banda ancho (Q 0,7; set notch). 0 = sin filtro
notch2_hz      = 7.7;       % rechaza banda angosto (Q 2; set notch2). 0 = sin filtro
vel_pata_dps   = 16;        % velocidad de las patas del firmware (set velpata)

% --- de donde arranca y que se le pide
x0             = 0;  v0 = 0;  omega0 = 0;
phi0           = 0;                 % [rad] arranca en equilibrio
x_destino      = 0;                 % [m] adonde ir (0 = quedarse)
t_consigna     = 1.0;
amp_ref        = deg2rad(1.5);      % onda cuadrada en la inclinacion pedida (la "ref" del firmware)
nivel_ref      = 2.084;             % [s] por nivel, como la prueba
ciclos_ref     = 5;
t_onda         = 2.0;               % [s] cuando empieza
giro_ref       = 0;

% --- las patas
pata_fw_fin    = pata_fw;   % [grados del firmware] a donde van en t_patas (igual = quietas)
t_patas        = 4.0;

% --- los sensores (como el original: ideales; poner un numero para el ruido)
ruido_imu_angulo  = 0;  ruido_imu_giro = 0;  ruido_encoder_x = 0;  ruido_encoder_v = 0;
sesgo_imu         = 0;  Ts_sensores = 0.005;
compensar_delta_G = 1;

duracion       = t_onda + 2*ciclos_ref*nivel_ref + 2;

%% 3. Planta, motor y controlador ==========================================
fisicos = parametros_fisicos('ajustada');
postura_deg = pata_fw + fisicos.pata_cero;          % la postura del modelo
p = parametros_pendulo_invertido(fisicos, postura_deg);
[p, motor] = motor_pendulo_invertido(p, fisicos);
V_motor = fisicos.V_bat - fisicos.caida_driver;     % lo que llega al motor con PWM 1
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8, 'factor_R', 64);
switch ganancias
    case 'firmware',  k_fw = k_firmware;
    case 'ajustadas', k_fw = -C.K/V_motor;
    otherwise, error('ganancias: ''firmware'' o ''ajustadas''');
end
K = -k_fw*V_motor;                  % en voltios, para leer y comparar con el original

%% 4. Variables que lee el modelo ==========================================
Ts = fisicos.Ts;
% rechaza banda del firmware (balance.c: RBJ con Q = 0,7) a 200 Hz
notch_num = 1;  notch_den = 1;
for nq = [notch_hz 0.7; notch2_hz 2]'      % los dos en cascada, como balance.c
    if nq(1) > 0
        w0 = 2*pi*nq(1)*Ts;  alfa = sin(w0)/(2*nq(2));  a0 = 1 + alfa;
        notch_num = conv(notch_num, [1, -2*cos(w0), 1]/a0);
        notch_den = conv(notch_den, [1, -2*cos(w0)/a0, (1 - alfa)/a0]);
    end
end
% 11/11: el retardo de la planta medido con los barridos (parametros_fisicos: retardo_s) se suma al ciclo de
% retardo del firmware, en ciclos enteros de 5 ms
n_retardo = 1 + round(fisicos.retardo_s/Ts);
% motores de rueda: uno por bloque
V_bat        = fisicos.V_bat;
beta_V_motor = motor.beta_V / motor.n_motores;
b_m_motor    = motor.b_m    / motor.n_motores;
tau_seco_motor = beta_V_motor*fisicos.zona_muerta_motor*V_motor;
tau_traccion = limite_de_traccion(p);
% planta
r               = p.r;
b_x             = p.b_x;
b_phi           = p.b_phi;
b_eje_mecanico  = p.b_eje_mecanico;
acople_rotor    = p.e_acople;
% servos de pata (en angulos del MODELO)
theta_pata_min = (360 - max(fisicos.th))*pi/180;
theta_pata_max = (360 - min(fisicos.th))*pi/180;
theta_pata_0   = deg2rad(postura_deg);
theta_pata_fin = deg2rad(pata_fw_fin + fisicos.pata_cero);
Kp_servo       = 12;
w_servo_max    = deg2rad(300);      % DS3240: 0,2 s por 60 grados a 5 V
banda_servo    = deg2rad(fisicos.banda_servo_deg);
vel_pata       = deg2rad(vel_pata_dps);
% tablas: como cambia el cuerpo con la postura (todo el recorrido del firmware)
grados_tabla = unique([fisicos.pata_cero + (0:1:30), postura_deg]);
tabla_theta   = deg2rad(grados_tabla(:));
tabla_a = zeros(size(tabla_theta));  tabla_h = tabla_a;  tabla_j = tabla_a;  tabla_k = tabla_a;
tabla_delta_G = tabla_a;
for i = 1:numel(tabla_theta)
    pi_ = motor_pendulo_invertido(parametros_pendulo_invertido(fisicos, grados_tabla(i)), fisicos);
    tabla_a(i) = pi_.a;  tabla_h(i) = pi_.h;  tabla_j(i) = pi_.j;  tabla_k(i) = pi_.k;
    tabla_delta_G(i) = pi_.delta_G;
end

%% 5. Que se construyo ======================================================
fprintf('ROBOT    %.0f g | centro de masa a %.1f cm del eje | pata del firmware %g = postura %.1f del modelo\n', ...
    1e3*p.m_total, 100*p.l, pata_fw, postura_deg);
fprintf('MOTORES  %s: %.4f N m/V y %.5f N m s/rad cada uno; %.1f V al motor; roce seco %.4f N m\n', ...
    'GA25-370 350 rpm', beta_V_motor, b_m_motor, V_motor, tau_seco_motor);
fprintf('CONTROL  k = [%.2f %.2f %.2f %.3f] (%s), cada %.0f ms, notch %.1f Hz, deadband %.2f\n', ...
    k_fw, ganancias, 1e3*Ts, notch_hz, db_fw);
fprintf('         equilibrio del cuerpo %.2f grados (la IMU marca %.1f mas)\n\n', ...
    -rad2deg(p.delta_G), fisicos.imu_delta_deg);

%% 6. Construir y simular ===================================================
modelo = 'segway_ajustado';
archivo = fullfile(aqui, [modelo '.slx']);
if ~exist(archivo, 'file')
    fprintf('construyendo %s...\n', [modelo '.slx']);
    construir_segway_ajustado(aqui, modelo);
end
salida = sim(modelo, 'StopTime', num2str(duracion));
t     = salida.sl_z.time;
z_sl  = salida.sl_z.signals.values;
U_sl  = salida.sl_U.signals.values;  t_U = salida.sl_U.time;   % discreta: su propio tiempo

%% 7. Contra lo medido el 3/11 (si es una de las alturas de la prueba) ======
medido = readtable(fullfile(raiz, 'modelado', 'ajuste', 'onda_cuadrada_medida.csv'));
m = medido(medido.pata == pata_fw, :);
figure('Name', 'Segway ajustado', 'Position', [60 60 1150 700], 'Color', 'w');
subplot(3,1,1); hold on; grid on
plot(t - t_onda, rad2deg(z_sl(:,3)), 'LineWidth', 1.4, 'DisplayName', 'Simulink ajustado');
if ~isempty(m), plot(m.t, m.th_rel, 'DisplayName', 'medido 3/11'); end
ylabel('\phi - equilibrio [\circ]'); legend('Location', 'northeast');
title(sprintf('Patas en %g (firmware): onda cuadrada de \\pm%.1f grados en la ref', pata_fw, rad2deg(amp_ref)));
subplot(3,1,2); hold on; grid on
x_sim = 1e3*(z_sl(:,1) - interp1(t, z_sl(:,1), t_onda));
plot(t - t_onda, x_sim, 'LineWidth', 1.4, 'DisplayName', 'Simulink ajustado');
if ~isempty(m), plot(m.t, m.x_mm, 'DisplayName', 'medido 3/11'); end
ylabel('x [mm]'); legend('Location', 'northeast');
subplot(3,1,3); hold on; grid on
plot(t_U - t_onda, U_sl(:,1)/V_motor, 'LineWidth', 1.0, 'DisplayName', 'Simulink ajustado');
if ~isempty(m), plot(m.t, m.u, 'DisplayName', 'medido 3/11'); end
ylabel('PWM'); xlabel('t desde la onda [s]'); legend('Location', 'northeast');
carpeta_res = fullfile(aqui, 'resultados');
if ~exist(carpeta_res, 'dir'), mkdir(carpeta_res); end
figura = fullfile(carpeta_res, sprintf('onda_pata_%g.png', pata_fw));
exportgraphics(gcf, figura, 'Resolution', 130);
if ~isempty(m)
    tt = 0:0.02:20.8;
    e_x = interp1(m.t, m.x_mm, tt) - interp1(t - t_onda, x_sim, tt);
    e_th = interp1(m.t, m.th_rel, tt) - interp1(t - t_onda, rad2deg(z_sl(:,3)), tt);
    fprintf('Contra lo medido: x %.1f mm rms, inclinacion %.2f grados rms\n', ...
        sqrt(mean(e_x.^2, 'omitnan')), sqrt(mean(e_th.^2, 'omitnan')));
end
fprintf('figura -> %s\nmodelo -> %s\n', figura, archivo);
