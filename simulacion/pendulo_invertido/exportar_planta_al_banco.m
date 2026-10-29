%% EXPORTAR_PLANTA_AL_BANCO  Pasa la planta del modelo al banco en C del firmware.
%
%  El banco (firmware/segway_v01/test_host/banco_lqr.c) corre el codigo C del firmware
%  -filtro complementario, odometria y LQR- contra una copia en C de planta_con_motor,
%  con sensores simulados. Para que haya UNA sola fuente de valores, los numeros salen de
%  aca, de parametros_fisicos.m, y se escriben en test_host/planta_modelo.h. Volver a
%  correr este script cada vez que cambie algun parametro del robot.
%
%  Tambien escribe test_host/referencia_planta.csv: la planta de MATLAB con el LQR
%  continuo, arrancando inclinada 5 grados. El banco la repite con su copia en C y exige
%  que coincidan; asi se comprueba que la copia de las ecuaciones esta bien.

clear; clc

aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
raiz = fileparts(fileparts(aqui));
addpath(fullfile(raiz, 'modelado', 'parametros'));
addpath(fullfile(raiz, 'modelado', 'cinematica'));
addpath(fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
destino = fullfile(raiz, 'firmware', 'segway_v01', 'test_host');

postura_deg = 25;           % la misma postura de diseno del LQR
fisicos = parametros_fisicos('segunda_iteracion');
p = parametros_pendulo_invertido(fisicos, postura_deg);
[p, motor] = motor_pendulo_invertido(p, fisicos);
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8);
tau_traccion = limite_de_traccion(p);

% IMU respecto del eje de las ruedas, en ejes del cuerpo (adelante, arriba) [m].
% d_imu esta en mm con x hacia ATRAS; la planta usa x hacia adelante.
imu_A = [-fisicos.d_imu(1), fisicos.d_imu(2)]/1000;
imu_P = imu_A - p.r_P_A(:).';

%% 1. Encabezado con los valores
valores = {
    'PLANTA_A',            p.a,                 'masa efectiva de avance [kg]'
    'PLANTA_H',            p.h,                 'masa por brazo [kg m]'
    'PLANTA_J',            p.j,                 'inercia de cabeceo [kg m2]'
    'PLANTA_K',            p.k,                 'par de gravedad [N m/rad]'
    'PLANTA_E_ACOPLE',     p.e_acople,          'acople del rotor [kg m]'
    'PLANTA_R',            p.r,                 'radio de rueda [m]'
    'PLANTA_B_EJE',        p.b_eje_mecanico,    'friccion del eje, sin el motor [N m s/rad]'
    'PLANTA_B_X',          p.b_x,               'arrastre de avance [N s/m]'
    'PLANTA_B_PHI',        p.b_phi,             'amortiguamiento de cabeceo [N m s/rad]'
    'PLANTA_BETA_V',       motor.beta_V,        'par de los dos motores por voltio [N m/V]'
    'PLANTA_B_M',          motor.b_m,           'contraelectromotriz de los dos motores [N m s/rad]'
    'PLANTA_V_BAT',        motor.V_bat,         'tension de la bateria en el modelo [V]'
    'PLANTA_TAU_TRACCION', tau_traccion,        'par maximo antes de patinar [N m]'
    'PLANTA_DELTA_G',      p.delta_G,           'phi = inclinacion del cuerpo + DELTA_G [rad]'
    'PLANTA_IMU_ADELANTE', imu_P(1),            'IMU respecto del eje, hacia adelante [m]'
    'PLANTA_IMU_ARRIBA',   imu_P(2),            'IMU respecto del eje, hacia arriba [m]'
    'PLANTA_G',            p.g,                 'gravedad [m/s2]'
    'PLANTA_GYRO_BIAS',    deg2rad(fisicos.gyro_bias_dps),  'sesgo del giroscopo [rad/s]'
    'PLANTA_GYRO_RMS',     deg2rad(fisicos.gyro_rms_dps),   'ruido del giroscopo [rad/s rms]'
    'PLANTA_ACC_RMS',      fisicos.acc_rms_g*p.g,           'ruido del acelerometro [m/s2 rms]'
    };
fid = fopen(fullfile(destino, 'planta_modelo.h'), 'w', 'n', 'UTF-8');
fprintf(fid, '// GENERADO por simulacion/pendulo_invertido/exportar_planta_al_banco.m el %s.\n', ...
    char(datetime('now', 'Format', 'yyyy-MM-dd HH:mm')));
fprintf(fid, '// No editar a mano: cambiar modelado/parametros/parametros_fisicos.m y volver a correrlo.\n');
fprintf(fid, '// Planta de planta_con_motor.m en la postura de %g grados, robot de %.1f g.\n', ...
    postura_deg, 1e3*p.m_total);
fprintf(fid, '#pragma once\n\n');
for i = 1:size(valores, 1)
    fprintf(fid, '#define %-20s %.9g    // %s\n', valores{i,1}, valores{i,2}, valores{i,3});
end
fprintf(fid, '\n// LQR del modelo en voltios, V = -K z con z = [x v phi omega] (solo para la referencia)\n');
fprintf(fid, '#define PLANTA_K_LQR { %.9g, %.9g, %.9g, %.9g }\n', C.K);
fclose(fid);

%% 2. Trayectoria de referencia: LQR continuo desde 5 grados
z0 = [0; 0; deg2rad(5); 0];
ode = @(t, z) planta_con_motor(z, -C.K*z, p);
sol = ode45(ode, [0 3], z0, odeset('RelTol', 1e-10, 'AbsTol', 1e-12, 'MaxStep', 1e-3));
t = (0:0.005:3).';
z = deval(sol, t).';
writematrix([t z], fullfile(destino, 'referencia_planta.csv'));

fprintf('planta_modelo.h y referencia_planta.csv escritos en %s\n', destino);
fprintf('IMU a %.1f mm adelante y %.1f mm arriba del eje; DELTA_G = %.2f grados\n', ...
    1e3*imu_P(1), 1e3*imu_P(2), rad2deg(p.delta_G));
