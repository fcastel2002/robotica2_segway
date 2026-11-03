%% EXPORTAR_PLANTA_ESCALON  Pasa el robot del modelo a la simulación de la bajada de escalón.
%
%  La simulación (banco_escalon.c) es plana: cuerpo + pata de cuatro barras movida por los
%  servos + rueda con motor, con contacto contra los escalones, vuelo y aterrizaje, y corre el
%  código C del firmware. Para que haya UNA sola fuente de valores, los números salen de
%  modelado/parametros/parametros_fisicos.m y de la cinemática de modelado/cinematica, y se
%  escriben en planta_escalon.h. Volver a correr este script cuando cambie algún parámetro.
%
%  Cómo se reparte el robot:
%    cuerpo     la caja: cabina, tapa, servos, batería, electrónica, tornillos
%    eslabones  manivelas, balancines y acopladores, en su centro de masa conjunto L (se mueve
%               con la pata); sus inercias propias se suman al cuerpo
%    eje        motores y ruedas, en el eje de la rueda P
%  La pata del firmware (0 a 30, 0 = agachado) es la postura del modelo menos 10: el servo del
%  modelo está en 350 - pata. Con eso el equilibrio del modelo sigue la tabla medida el 2/11
%  con un corrimiento casi constante, que es la IMU (IMU_DELTA, se ajusta abajo).
%
%  Marco de la planta: x ADELANTE, z arriba, origen en el centro de masa del cuerpo. La
%  cinemática del modelo usa x hacia atrás: acá se le cambia el signo.

clear; clc
aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
raiz = fileparts(fileparts(aqui));
addpath(fullfile(raiz, 'modelado', 'parametros'));
addpath(fullfile(raiz, 'modelado', 'cinematica'));
addpath(fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));

f = parametros_fisicos('segunda_iteracion');
G.AB = f.AB; G.beta = f.ang_AB; G.AD = f.k_AD*f.s_barras; G.BC = f.k_BC*f.s_barras;
G.CD = f.k_CD*f.s_barras; G.DP = f.k_DP*f.s_barras; G.delta = f.delta;
n = f.n_servos;
servo_de = @(pata) 350 - pata;          % ángulo del servo del modelo [grados]
PATA_REF = 15;

% Tabla medida el 2/11 (firmware/segway_v01/main/board_config.h, REF_TABLA_*)
tabla_patas = [0 5 10 15 20 25];
tabla_theta = [18.9 16.0 14.9 13.7 12.8 10.9];

%% 1. Cuerpo
m = 1e-3*[f.m_cabina; f.m_tapa; n*f.m_servo; f.m_bateria; f.m_electronica; f.m_tornilleria; f.m_carga];
r = 1e-3*[f.r_cabina; f.r_tapa; f.r_servo; f.r_bateria; f.r_electronica; f.r_tornilleria; f.r_carga];
r(:, 1) = -r(:, 1);                     % x adelante
Jp = [f.J_cabina; f.J_tapa; 0; 0; 0; 0; 0];
m_cuerpo = sum(m);
rG = sum(m.*r, 1)/m_cuerpo;             % centro de masa del cuerpo respecto de A
I_cuerpo = sum(Jp + m.*sum((r - rG).^2, 2)) + n*(f.J_AD + f.J_BC);

%% 2. Eslabones y eje
m_esl = n*1e-3*(f.m_AD + f.m_BC + f.m_CDP);
m_eje = n*1e-3*(f.m_motor + f.m_rueda);
J_rueda = n*0.75*1e-3*f.m_rueda*(1e-3*f.Rw)^2;      % entre disco (0,5) y aro (1): neumático
I_eslabon = n*f.J_CDP;                               % el acoplador, que lleva el motor

%% 3. Cinemática de la pata: eje P respecto del centro de masa del cuerpo, y giro del acoplador
paso = 0.5;  patas = (-4:paso:34)';
h = 0.01;
eje = @(pata) local_eje(pata, G, servo_de, rG, f);
T = zeros(numel(patas), 10);
for i = 1:numel(patas)
    a = patas(i);
    s0 = eje(a); s1 = eje(a + h); sm = eje(a - h);
    d = 2*deg2rad(h);
    ds = (s1 - sm)/d;
    T(i, :) = [s0(1:3), ds(1:3), s0(4:5), ds(4:5)];
end

%% 4. Equilibrio del modelo contra la tabla medida: el corrimiento es la IMU
th_eq = zeros(size(tabla_patas));
m_tot = m_cuerpo + m_esl + m_eje;
for i = 1:numel(tabla_patas)
    s = eje(tabla_patas(i));
    cg = (m_esl*s(4:5) + m_eje*s(1:2))/m_tot;   % centro de masa total respecto del cuerpo
    c = cg - s(1:2);                            % ... y respecto del eje
    th_eq(i) = rad2deg(atan2(-c(1), c(2)));
end
IMU_DELTA = mean(tabla_theta - th_eq);
fprintf('Equilibrio del modelo [grados]: %s\n', mat2str(round(th_eq, 2)));
fprintf('Medido - modelo: %s -> IMU_DELTA = %.2f (desvio %.2f)\n', ...
    mat2str(round(tabla_theta - th_eq, 2)), IMU_DELTA, std(tabla_theta - th_eq));

%% 5. Motores, servos, contacto
p = parametros_pendulo_invertido(f, PATA_REF + 10);
[~, motor] = motor_pendulo_invertido(p, f);
N_med = 899/(4*11);                     % 20,4: reductor medido con el encoder (FW-009)
V_motor = 10.0;                         % LiPo cargada menos la caída del L298N (MED-005: 10,6 V a 12 V)
servo_par = n*41*0.0981;                % DS3240 a 6 V (ficha: 36 kg cm a 5 V, 45 a 6,8 V; la placa da 6 V, SUP-40)
servo_vel = deg2rad(327);               % [rad/s] en vacío a 6 V (ficha: 300 grados/s a 5 V, 353 a 6,8 V)
servo_J = n*0.004;                      % SUPUESTO: inercia del motor del servo vista en la pata

% IMU (centro de la cabina) y sensor de distancia: respecto de A, x adelante
imu_A = 1e-3*[-f.d_imu(1), f.d_imu(2)];

% Contorno de la cabina para los golpes (cabeza_v31: de 89,5 mm adelante de A a 52,5 atrás, de
% 29 mm abajo de A a 74,5 arriba; base_conocimiento/dimensiones_cad_primera_iteracion.md):
% puntos cada ~20 mm en el piso y en las caras de adelante y de atrás
xs = linspace(-52.5, 89.5, 8)'; zs = linspace(-29, 74.5, 6)';
contorno_A = 1e-3*unique([xs, -29*ones(size(xs)); 89.5*ones(size(zs)), zs; -52.5*ones(size(zs)), zs], 'rows');
% Sensor de distancia (propuesta, a medir cuando se monte): cara de atrás de la cabina, 2 cm
% arriba del eje de los servos, el haz 40 grados hacia atrás de la vertical del cuerpo. Así
% queda a más de 10 cm del piso (mínimo del Sharp) aun con las patas en 0.
sensor_A = 1e-3*[-52.5 20];
sensor_ang = 40;

%% 6. Encabezado
fid = fopen(fullfile(aqui, 'planta_escalon.h'), 'w', 'n', 'UTF-8');
fprintf(fid, '// GENERADO por simulacion/escalon/exportar_planta_escalon.m el %s.\n', ...
    char(datetime('now', 'Format', 'yyyy-MM-dd HH:mm')));
fprintf(fid, '// No editar a mano: cambiar modelado/parametros/parametros_fisicos.m y volver a correrlo.\n');
fprintf(fid, '// Marco: x adelante, z arriba, origen en el centro de masa del cuerpo; pata del firmware.\n');
fprintf(fid, '#pragma once\n\n');
v = {
    'PE_M_CUERPO', m_cuerpo, 'caja + manivelas + balancines [kg]'
    'PE_I_CUERPO', I_cuerpo, 'alrededor de su centro de masa [kg m2]'
    'PE_M_RUEDA', m_eje, 'motores + ruedas, en el eje [kg]'
    'PE_M_ESLABONES', m_esl, 'manivelas + balancines + acopladores [kg]'
    'PE_I_ESLABON', I_eslabon, 'lo que gira con el acoplador [kg m2]'
    'PE_J_RUEDA', J_rueda, 'las dos ruedas alrededor del eje [kg m2]'
    'PE_J_ROTOR', n*f.J_r, 'los dos rotores [kg m2]'
    'PE_N_REDUCTOR', N_med, 'medido con el encoder'
    'PE_J_SERVO', servo_J, 'servos vistos desde la pata [kg m2] (supuesto)'
    'PE_R_RUEDA', 1e-3*f.Rw, '[m]'
    'PE_BETA_V', motor.beta_V, 'par de los dos motores por voltio [N m/V]'
    'PE_B_M', motor.b_m, 'contraelectromotriz de los dos motores [N m s/rad]'
    'PE_B_EJE', n*f.b_w, 'friccion del eje [N m s/rad]'
    'PE_V_MOTOR', V_motor, 'lo que llega al motor con PWM 1 [V]'
    'PE_SERVO_PAR_MAX', servo_par, 'de calado, los dos [N m]'
    'PE_SERVO_VEL_MAX', servo_vel, 'en vacio [rad/s]'
    'PE_SERVO_GANANCIA', 1/deg2rad(5), 'a fondo con 5 grados de error [1/rad]'
    'PE_SERVO_B', 0.02, 'friccion viscosa del reductor [N m s/rad]'
    'PE_K_RUEDA', n*f.k_contacto, 'las dos ruedas [N/m]'
    'PE_C_RUEDA', n*f.c_contacto, '[N s/m]'
    'PE_K_CUERPO', 1e5, 'golpe del cuerpo contra el escalon [N/m]'
    'PE_C_CUERPO', 300, '[N s/m]'
    'PE_MU', f.mu, 'friccion rueda-piso'
    'PE_IMU_X', imu_A(1) - rG(1), 'IMU respecto del centro de masa del cuerpo [m]'
    'PE_IMU_Z', imu_A(2) - rG(2), '[m]'
    'PE_IMU_DELTA', deg2rad(IMU_DELTA), 'la IMU marca esto de mas (ajustado a la tabla medida) [rad]'
    'PE_SENSOR_X', sensor_A(1) - rG(1), 'sensor de distancia respecto del centro de masa [m]'
    'PE_SENSOR_Z', sensor_A(2) - rG(2), '[m]'
    'PE_SENSOR_ANG', deg2rad(sensor_ang), 'haz desde la vertical del cuerpo hacia atras [rad]'
    'PE_A_X', -rG(1), 'eje del servo (A) respecto del centro de masa [m]'
    'PE_A_Z', -rG(2), '[m]'
    };
for i = 1:size(v, 1)
    fprintf(fid, '#define %-20s %.9g    // %s\n', v{i, 1}, v{i, 2}, v{i, 3});
end
fprintf(fid, '\n// Pata: cada PE_TABLA_PASO desde PE_TABLA_A0 [rad]: px, pz [m], g [rad], sus derivadas,\n');
fprintf(fid, '// y el centro de masa de los eslabones lx, lz [m] con sus derivadas\n');
fprintf(fid, '#define PE_TABLA_A0          %.9g\n', deg2rad(patas(1)));
fprintf(fid, '#define PE_TABLA_PASO        %.9g\n', deg2rad(paso));
fprintf(fid, '#define PE_TABLA_N           %d\n', numel(patas));
fprintf(fid, 'static const double PE_TABLA[PE_TABLA_N][10] = {\n');
for i = 1:numel(patas)
    fprintf(fid, ['    {', repmat(' %.9g,', 1, 9), ' %.9g },  // %.1f\n'], T(i, :), patas(i));
end
fprintf(fid, '};\n\n// Contorno de la cabina (respecto del centro de masa) para los golpes\n');
fprintf(fid, '#define PE_N_PUNTOS          %d\n', size(contorno_A, 1));
fprintf(fid, '#define PE_PUNTOS { ');
for i = 1:size(contorno_A, 1)
    fprintf(fid, '{ %.6g, %.6g }%s', contorno_A(i, 1) - rG(1), contorno_A(i, 2) - rG(2), ...
        ternario(i < size(contorno_A, 1), ', ', ' }'));
end
fprintf(fid, '\n');
fclose(fid);

fprintf('Cuerpo %.1f g, centro de masa a [%.1f %.1f] mm de A, I = %.3g kg m2\n', ...
    1e3*m_cuerpo, 1e3*rG, I_cuerpo);
fprintf('Eslabones %.1f g, eje %.1f g; total %.1f g\n', 1e3*m_esl, 1e3*m_eje, 1e3*m_tot);
fprintf('El eje baja de %.1f mm (pata 0) a %.1f mm (pata 30) respecto de A\n', ...
    1e3*(T(patas == 0, 2) + rG(2)), 1e3*(T(patas == 30, 2) + rG(2)));
fprintf('planta_escalon.h escrito\n');

% [px pz g lx lz]: eje y centro de masa de los eslabones respecto del centro de masa del cuerpo
% (x adelante), y dirección D->P del acoplador
function s = local_eje(pata, G, servo_de, rG, f)
    K = cinematica_directa(servo_de(pata), G);
    cAD = K.A + f.f_AD*(K.D - K.A);
    cBC = K.B + f.f_BC*(K.C - K.B);
    cCDP = K.D + f.f_CDP*(K.P - K.D);
    L = (f.m_AD*cAD + f.m_BC*cBC + f.m_CDP*cCDP)/(f.m_AD + f.m_BC + f.m_CDP);
    s = [-1e-3*K.P(1) - rG(1), 1e-3*K.P(2) - rG(2), deg2rad(K.theta_DP), ...
         -1e-3*L(1) - rG(1), 1e-3*L(2) - rG(2)];
end

function s = ternario(c, a, b)
    if c, s = a; else, s = b; end
end
