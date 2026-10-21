%% INICIAR_SEGWAY  El modelo completo del Segway en Simulink. Abrir y pulsar Run.
%
%  Arma (si falta) y simula segway_completo.slx, que tiene SEIS bloques grandes:
%
%     CONSIGNAS -> CONTROL -> ACTUADORES -> PLANTA -> SENSORES -+
%          ^                                                    |
%          +----------------------------------------------------+
%
%  Los CUATRO motores estan separados: dos de rueda y dos de pata, cada uno con
%  su propio bloque, aunque hoy los de rueda reciban la misma tension y los
%  servos la misma posicion.
%
%  Los SENSORES son bloques propios (encoders e IMU) con su entrada de ruido
%  puesta en cero, lista para encenderla.
%
%  TODO lo que el modelo lee queda en el workspace base al terminar este script,
%  porque es un script y no una funcion. Eso es a proposito: Simulink lee sus
%  parametros de ahi.
%
%  La verificacion del final compara contra planta_con_motor, que es una
%  implementacion independiente escrita a mano. Si las dos coinciden, el
%  diagrama esta bien cableado.
%
%  Ver tambien CONSTRUIR_SEGWAY_COMPLETO, y el capitulo 8 de
%  docs/modelo/modelo_del_segway.pdf.

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
variante       = 'segunda_iteracion';
postura_deg    = 25;        % postura de diseno del control: 10 plegada, 40 estirada
max_phi_deg    = 8;         % cuanta inclinacion tolera el LQR

% --- de donde arranca
x0             = 0;                 % [m]
v0             = 0;                 % [m/s]
phi0           = deg2rad(5);        % [rad]  arranca inclinado 5 grados
omega0         = 0;                 % [rad/s]

% --- que se le pide
x_destino      = 0.30;      % [m] adonde ir;  0 = quedarse quieto
t_consigna     = 2.0;       % [s] cuando
giro_ref       = 0;         % [V] diferencia entre las dos ruedas; 0 = derecho

% --- las patas
theta_pata_fin = postura_deg;   % [grados] postura final; igual a la inicial = patas quietas
t_patas        = 4.0;           % [s] cuando se mueven

% --- los sensores (hoy ideales). Poner un numero para que aparezca el ruido.
ruido_imu_angulo  = 0;      % [rad^2 s] densidad de ruido del angulo
ruido_imu_giro    = 0;      % [(rad/s)^2 s]
ruido_encoder_x   = 0;      % [m^2 s]
ruido_encoder_v   = 0;      % [(m/s)^2 s]
sesgo_imu         = 0;      % [rad] error constante del angulo
Ts_sensores       = 0.005;  % [s] cada cuanto se refresca el ruido
compensar_delta_G = 1;      % 1 = el firmware corrige el angulo segun la postura; 0 = no

duracion       = 8;         % [s]

%% 3. Planta, motor y controlador ==========================================
fisicos = parametros_fisicos(variante);
p = parametros_pendulo_invertido(fisicos, postura_deg);
[p, motor] = motor_pendulo_invertido(p, fisicos);
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', max_phi_deg);

%% 4. Variables que lee el modelo ==========================================
% --- control
K = C.K;

% --- motores de rueda: el modelo tiene UNO por bloque, asi que se reparte
V_bat        = motor.V_bat;
beta_V_motor = motor.beta_V / motor.n_motores;
b_m_motor    = motor.b_m    / motor.n_motores;
tau_traccion = limite_de_traccion(p);

% --- planta
r               = p.r;
b_x             = p.b_x;
b_phi           = p.b_phi;
b_eje_mecanico  = p.b_eje_mecanico;
acople_rotor    = p.e_acople;

% --- servos de pata
theta_pata_min = (360 - max(fisicos.th))*pi/180;   % plegada
theta_pata_max = (360 - min(fisicos.th))*pi/180;   % estirada
theta_pata_0   = deg2rad(postura_deg);
theta_pata_fin = deg2rad(theta_pata_fin);
Kp_servo       = 12;                               % [1/s] rigidez del lazo interno del servo
w_servo_max    = deg2rad(300);                     % [rad/s] velocidad maxima (DS3240)

% --- tablas: como cambia el cuerpo con la postura de las patas
grados_tabla = unique([10:1:40, postura_deg]);
tabla_theta   = deg2rad(grados_tabla(:));
tabla_a       = zeros(size(tabla_theta));
tabla_h       = zeros(size(tabla_theta));
tabla_j       = zeros(size(tabla_theta));
tabla_k       = zeros(size(tabla_theta));
tabla_delta_G = zeros(size(tabla_theta));
for i = 1:numel(tabla_theta)
    pi_ = motor_pendulo_invertido(parametros_pendulo_invertido(fisicos, grados_tabla(i)), fisicos);
    tabla_a(i)       = pi_.a;
    tabla_h(i)       = pi_.h;
    tabla_j(i)       = pi_.j;
    tabla_k(i)       = pi_.k;
    tabla_delta_G(i) = pi_.delta_G;
end

%% 5. Que se construyo ======================================================
fprintf('ROBOT    %.0f g | centro de masa a %.1f cm del eje | ruedas de %.0f mm\n', ...
    1e3*p.m_total, 100*p.l, 1e3*p.r);
fprintf('MOTORES  2 de rueda: %s\n', motor.nombre);
fprintf('         cada uno da %.4f N m por voltio y pierde %.5f N m por rad/s\n', ...
    beta_V_motor, b_m_motor);
fprintf('         2 de pata: DS3240, recorrido de %.0f a %.0f grados\n', ...
    rad2deg(theta_pata_min), rad2deg(theta_pata_max));
fprintf('PLANTA   postura %g grados. Coeficientes en esa postura:\n', postura_deg);
fprintf('         masa efectiva a = %.4f kg     (el robot pesa %.3f kg: la diferencia es el rotor)\n', ...
    p.a, p.m_total);
fprintf('         masa por brazo h = %.4f kg m   inercia j = %.6f kg m2\n', p.h, p.j);
fprintf('         par de gravedad  k = %.4f N m/rad   acople del rotor = %.5f\n', p.k, p.e_acople);
fprintf('CONTROL  K = [%.1f %.1f %.1f %.1f] V por (m, m/s, rad, rad/s)\n', C.K);
fprintf('         polo inestable %.2f 1/s: la inclinacion se duplica cada %.0f ms\n\n', ...
    max(real(C.autovalores_lazo_abierto)), 1000*log(2)/max(real(C.autovalores_lazo_abierto)));

if abs(theta_pata_fin - theta_pata_0) < 1e-9
    fprintf('PATAS    quietas en %g grados: la planta es la verificada\n', postura_deg);
else
    fprintf('PATAS    se mueven de %.0f a %.0f grados en t = %.1f s\n', ...
        rad2deg(theta_pata_0), rad2deg(theta_pata_fin), t_patas);
    if compensar_delta_G
        fprintf('         con compensacion de delta_G: el robot no deberia correrse\n');
    else
        fprintf('         SIN compensar delta_G: el robot se va a correr del lugar\n');
    end
end
fprintf('SENSORES %s\n\n', ...
    ternario(all([ruido_imu_angulo ruido_imu_giro ruido_encoder_x ruido_encoder_v sesgo_imu] == 0), ...
    'ideales, sin ruido ni sesgo', 'con ruido o sesgo activados'));

%% 6. Construir y simular ===================================================
modelo = 'segway_completo';
archivo = fullfile(aqui, [modelo '.slx']);
if ~exist(archivo, 'file')
    fprintf('construyendo %s...\n', [modelo '.slx']);
    construir_segway_completo(aqui, modelo);
end
salida = sim(modelo, 'StopTime', num2str(duracion));

t       = salida.sl_z.time;
z_sl    = salida.sl_z.signals.values;
z_med   = salida.sl_z_med.signals.values;
U_sl    = salida.sl_U.signals.values;
tau_sl  = salida.sl_tau.signals.values;
th_sl   = salida.sl_theta.signals.values;

%% 7. Verificar contra el modelo de referencia ==============================
% Solo tiene sentido con las patas quietas: planta_con_motor es de postura fija.
if abs(theta_pata_fin - theta_pata_0) < 1e-9
    referencia = @(tt) [x_destino*(tt >= t_consigna); 0; 0; 0];
    ode = @(tt, z) planta_con_motor(z, -C.K*(z - referencia(tt)), p);
    sol = ode45(ode, [0 duracion], [x0; v0; phi0; omega0], ...
        odeset('RelTol', 1e-10, 'AbsTol', 1e-12, 'MaxStep', 1e-3));
    z_ml = deval(sol, t).';
    error_estado = max(abs(z_sl - z_ml), [], 1);
    fprintf('VERIFICACION contra planta_con_motor (implementacion independiente)\n');
    fprintf('        x %.2e m | v %.2e m/s | phi %.2e rad | omega %.2e rad/s\n', error_estado);
    if max(error_estado) < 1e-6
        fprintf('        -> el diagrama reproduce el modelo matematico\n\n');
    else
        warning('INICIAR_SEGWAY:verificacion', ...
            'El diagrama NO coincide con el modelo de referencia. Revisar el cableado.');
    end
else
    error_estado = nan(1, 4);
    fprintf('VERIFICACION omitida: con las patas en movimiento no hay modelo de referencia\n\n');
end

%% 8. Lectura del resultado =================================================
antes   = t < t_consigna;
fprintf('a) QUEDARSE PARADO: arranca inclinado %.0f grados\n', rad2deg(phi0));
fprintf('        inclinacion a los %.1f s      %8.4f grados\n', t_consigna, ...
    rad2deg(abs(interp1(t, z_sl(:,3), t_consigna))));
fprintf('        se corrio del lugar          %8.1f mm\n', 1e3*max(abs(z_sl(antes,1))));
if abs(x_destino) > 1e-9
    fprintf('b) IR A OTRA POSICION: se le pide %.2f m en t = %.1f s\n', x_destino, t_consigna);
    fprintf('        llega a                      %8.4f m\n', z_sl(end,1));
    fprintf('        inclinacion maxima           %8.2f grados\n', rad2deg(max(abs(z_sl(:,3)))));
end
fprintf('COMUN\n');
fprintf('        tension que PIDE el control  %8.2f V  (la bateria da %.1f; el resto lo satura cada motor)\n', ...
    max(abs(U_sl(:))), V_bat);
fprintf('        par de cada motor, pico      %8.4f N m\n', max(abs(tau_sl(:))));
fprintf('        postura de las patas         %8.1f a %.1f grados\n', ...
    rad2deg(min(th_sl)), rad2deg(max(th_sl)));
fprintf('        diferencia medido vs real    %8.2e (sensores ideales -> cero)\n', ...
    max(max(abs(z_med - z_sl))));

%% 9. Figura ================================================================
carpeta_res = fullfile(aqui, 'resultados');
if ~exist(carpeta_res, 'dir'), mkdir(carpeta_res); end
figure('Name', 'Segway completo', 'Position', [60 60 1150 780], 'Color', 'w');

subplot(3,2,1); plot(t, z_sl(:,1)*100, 'LineWidth', 1.6); grid on
ylabel('x [cm]'); title('Posicion de avance'); xlabel('t [s]')
subplot(3,2,2); plot(t, rad2deg(z_sl(:,3)), 'LineWidth', 1.6); grid on
ylabel('\phi [\circ]'); title('Inclinacion'); xlabel('t [s]')
subplot(3,2,3); plot(t, U_sl, 'LineWidth', 1.4); grid on
yline(V_bat, '--r'); yline(-V_bat, '--r');
ylabel('U [V]'); title('Tension de cada motor de rueda'); xlabel('t [s]')
legend('izquierda', 'derecha', 'Location', 'best')
subplot(3,2,4); plot(t, tau_sl, 'LineWidth', 1.4); grid on
ylabel('\tau [N m]'); title('Par de cada motor de rueda'); xlabel('t [s]')
legend('izquierda', 'derecha', 'Location', 'best')
subplot(3,2,5); plot(t, rad2deg(th_sl), 'LineWidth', 1.6); grid on
ylabel('\theta [\circ]'); title('Postura de las patas'); xlabel('t [s]')
ylim([rad2deg(theta_pata_min)-2 rad2deg(theta_pata_max)+2])
subplot(3,2,6); plot(t, z_sl(:,2), 'LineWidth', 1.6); grid on
ylabel('v [m/s]'); title('Velocidad de avance'); xlabel('t [s]')

figura = fullfile(carpeta_res, 'respuesta_segway.png');
exportgraphics(gcf, figura, 'Resolution', 150);
fprintf('\nfigura -> %s\n', figura);
fprintf('modelo -> %s\n', archivo);

%% ==========================================================================
function s = ternario(cond, a, b)
    if cond, s = a; else, s = b; end
end
