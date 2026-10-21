%% INICIAR_PENDULO_SIMULINK  Pendulo invertido con motor y LQR, en Simulink.
%
%  Abrir y pulsar Run. Construye el modelo si falta, lo simula, lo compara
%  contra el modelo de referencia de MATLAB y deja figura y resumen en
%  resultados/.
%
%  Hace las DOS cosas que se le piden al robot:
%     a) mantenerse parado en el mismo lugar (recuperarse de una inclinacion)
%     b) ir a otra posicion (consigna escalon en x)
%
%  Las cinco areas del diagrama, que son las cinco etapas fisicas:
%     Consigna   z_ref = [x_destino; 0; 0; 0]
%     Control    U = -K (z - z_ref)                  realimentacion de estado
%     Actuador   bateria -> motor -> agarre          los dos limites reales
%     Planta     M(phi) q'' = H tau - D q' + no lineal
%
%  NOMBRES: tension U, velocidad de avance v. No se repite la letra.
%
%  Alcance: patas BLOQUEADAS en la postura elegida, piso plano, rodadura sin
%  deslizamiento, estado medido perfecto y sin retardo. No hay sensores, ni
%  ruido, ni periodo de muestreo, ni la tercera coordenada de la pata.
%  Los parametros salen de modelado/parametros/parametros_fisicos.m y varios
%  siguen SIN medir. Los resultados son de diseno, no una prediccion.

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
variante      = 'segunda_iteracion';  % geometria y componentes vigentes
postura_deg   = 25;                   % patas: 10 plegada, 40 estirada
incluir_rotor = true;                 % inercia del rotor reflejada
max_phi_deg   = 8;                    % peso del LQR: inclinacion tolerable

phi0_deg      = 5;                    % inclinacion inicial [grados]
x0            = 0;                    % posicion inicial del eje [m]
v0            = 0;                    % velocidad inicial [m/s]
omega0        = 0;                    % velocidad de cabeceo inicial [rad/s]

x_destino     = 0.30;                 % adonde se le pide ir [m]; 0 = quedarse quieto
t_consigna    = 2.0;                  % cuando se le pide [s]
duracion      = 8;                    % [s]

%% 3. Planta, motor y controlador ==========================================
fisicos = parametros_fisicos(variante);
p = parametros_pendulo_invertido(fisicos, postura_deg);
[p, motor] = motor_pendulo_invertido(p, fisicos, 'incluir_rotor', incluir_rotor);
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', max_phi_deg);

fprintf('MOTOR   %s\n', motor.nombre);
fprintf('        reduccion 1:%g, Ke = Kt = %.5f, R = %.2f ohm, rendimiento supuesto %.0f %%\n', ...
    motor.n_g, motor.Ke, motor.R_m, 100*motor.eta);
fprintf('        par de bloqueo %.3f N m (util %.3f), velocidad maxima %.2f m/s\n', ...
    motor.tau_bloqueo, motor.tau_bloqueo_util, motor.v_max);
fprintf('PLANTA  postura %g grados, cuerpo %.0f g + ruedas %.0f g\n', ...
    postura_deg, 1e3*p.m_cuerpo, 1e3*p.m_ruedas);
fprintf('        polo inestable %.2f 1/s: la inclinacion se duplica cada %.0f ms\n', ...
    max(real(C.autovalores_lazo_abierto)), 1000*log(2)/max(real(C.autovalores_lazo_abierto)));
fprintf('LQR     K = [%.1f %.1f %.1f %.1f] V por (m, m/s, rad, rad/s)\n', C.K);
fprintf('        polos %s, asentamiento %.2f s\n\n', mat2str(round(C.polos, 2)'), C.tiempo_de_asentamiento);

%% 4. Variables que lee el modelo ==========================================
K = C.K;  V_bat = motor.V_bat;  beta_V = motor.beta_V;  b_m = motor.b_m;
tau_traccion = limite_de_traccion(p);
a = p.a;  h = p.h;  j = p.j;  k = p.k;  e_acople = p.e_acople;  r = p.r;
b_eje = p.b_eje_mecanico;   % el motor esta afuera: aca va solo la friccion
b_x = p.b_x;  b_phi = p.b_phi;
q0 = [x0; deg2rad(phi0_deg)];        % [x; phi]
q_punto0 = [v0; omega0];             % [v; omega]

% OJO con la lectura: tau/r NO es la fuerza en el piso. Parte del par acelera la inercia
% reflejada del rotor (0.44 kg sobre un robot de 1.0 kg), asi que la fuerza util en el
% contacto es bastante menor. El detalle esta en limite_de_traccion.
[~, ~, c1] = limite_de_traccion(p);
F_motor = abs(c1)*motor.tau_bloqueo;   F_piso = p.mu*p.m_total*p.g;
fprintf('LIMITES del actuador\n');
fprintf('        par de bloqueo del motor       %.3f N m\n', motor.tau_bloqueo);
fprintf('        fuerza que pone en el piso     %.2f N   (NO es tau/r = %.1f N)\n', F_motor, motor.tau_bloqueo/r);
fprintf('        friccion disponible            %.2f N   (mu = %.1f)\n', F_piso, p.mu);
if F_motor < F_piso
    fprintf('        -> usa el %.0f %% del agarre: el motor NO puede hacer patinar la rueda\n\n', 100*F_motor/F_piso);
else
    fprintf('        -> supera el agarre %.1f veces: manda el neumatico\n\n', F_motor/F_piso);
end

%% 5. Construir y simular ==================================================
modelo = 'pendulo_invertido_lqr';
archivo = fullfile(aqui, [modelo '.slx']);
if ~exist(archivo, 'file')
    fprintf('construyendo %s...\n', [modelo '.slx']);
    construir_pendulo_simulink(aqui, modelo);
end
salida = sim(modelo, 'StopTime', num2str(duracion));

t      = salida.sl_z.time;
z_sl   = salida.sl_z.signals.values;
U_sl   = salida.sl_tension.signals.values;
tau_sl = salida.sl_par.signals.values;
ref_sl = salida.sl_ref.signals.values;

%% 6. Comparar contra el modelo de MATLAB ==================================
referencia = @(tt) [x_destino*(tt >= t_consigna); 0; 0; 0];
ode = @(tt, z) planta_con_motor(z, -C.K*(z - referencia(tt)), p);
sol = ode45(ode, [0 duracion], [q0(1); q_punto0(1); q0(2); q_punto0(2)], ...
    odeset('RelTol', 1e-10, 'AbsTol', 1e-12, 'MaxStep', 1e-3));
z_ml = deval(sol, t).';
error_estado = max(abs(z_sl - z_ml), [], 1);

fprintf('SIMULINK contra el modelo de MATLAB (planta_con_motor)\n');
fprintf('        x %.2e m | v %.2e m/s | phi %.2e rad | omega %.2e rad/s\n\n', error_estado);

%% 7. Lectura del resultado ================================================
antes = t < t_consigna;  despues = t >= t_consigna;
patina = abs(tau_sl) >= tau_traccion - 1e-9;
contacto_ok = true;  normal_min = inf;
for i = 1:numel(t)
    [~, R] = planta_con_motor(z_ml(i,:).', -C.K*(z_ml(i,:).' - referencia(t(i))), p);
    contacto_ok = contacto_ok && R.contacto_valido;
    normal_min = min(normal_min, R.normal);
end
retroceso = min(z_sl(despues, 1)) - z_sl(find(despues, 1), 1);

fprintf('a) QUEDARSE PARADO: arranca inclinado %g grados\n', phi0_deg);
fprintf('        inclinacion a los %.1f s       %.4f grados\n', t_consigna, rad2deg(z_sl(find(antes,1,'last'),3)));
fprintf('        se corrio del lugar            %.1f mm\n', 1e3*max(abs(z_sl(antes,1))));
fprintf('b) IR A OTRA POSICION: se le pide %.2f m en t = %.1f s\n', x_destino, t_consigna);
fprintf('        llega a                        %.4f m (error %.1f mm)\n', z_sl(end,1), 1e3*abs(z_sl(end,1)-x_destino));
fprintf('        PRIMERO RETROCEDE              %.1f mm  (el cero de fase no minima)\n', 1e3*abs(retroceso));
fprintf('        se inclina hasta               %.2f grados para arrancar\n', max(abs(rad2deg(z_sl(despues,3)))));
fprintf('        tarda                          %.2f s en llegar al 98 %%\n', ...
    tiempo_de_llegada(t, z_sl(:,1), x_destino, t_consigna));
fprintf('COMUN\n');
fprintf('        tension pico                   %.2f V de %.1f\n', max(abs(U_sl)), V_bat);
fprintf('        par pico                       %.4f N m;  motor %.4f, agarre %.4f\n', max(abs(tau_sl)), motor.tau_bloqueo, tau_traccion);
fprintf('        saturado el agarre             %.0f %% del tiempo\n', 100*mean(patina));
fprintf('        velocidad pico                 %.2f m/s de %.2f\n', max(abs(z_sl(:,2))), motor.v_max);
fprintf('        normal minima                  %.1f N; rodadura valida: %s\n', normal_min, string(contacto_ok));

%% 8. Figura y resumen =====================================================
carpeta_res = fullfile(aqui, 'resultados');
if ~exist(carpeta_res, 'dir'), mkdir(carpeta_res); end

figura = figure('Name', 'Pendulo invertido con LQR', 'Position', [50 50 1200 800], 'Color', 'w');
subplot(3,2,1)
plot(t, z_sl(:,1), 'LineWidth', 1.8); hold on
plot(t, ref_sl(:,1), '--', 'LineWidth', 1.4); grid on
ylabel('x [m]'); title('Posicion: sigue la consigna')
legend('x', 'consigna', 'Location', 'southeast')

subplot(3,2,2)
plot(t, rad2deg(z_sl(:,3)), 'LineWidth', 1.8); hold on
plot(t, rad2deg(z_ml(:,3)), '--', 'LineWidth', 1.1); grid on; yline(0, ':')
ylabel('\phi [grados]'); title('Inclinacion: Simulink contra MATLAB')
legend('Simulink', 'referencia MATLAB', 'Location', 'best')

subplot(3,2,3)
k_zoom = t >= t_consigna - 0.2 & t <= t_consigna + 1.5;
plot(t(k_zoom), 1e3*z_sl(k_zoom,1), 'LineWidth', 1.8); grid on; hold on
yline(0, ':'); xline(t_consigna, '--r')
ylabel('x [mm]'); title('Zoom: para avanzar primero retrocede')

subplot(3,2,4)
plot(t, U_sl, 'LineWidth', 1.8); grid on; hold on
yline([-V_bat V_bat], '--r'); ylabel('U [V]'); title('Tension: satura en la bateria')

subplot(3,2,5)
plot(t, tau_sl, 'LineWidth', 1.8); grid on; hold on
yline([-tau_traccion tau_traccion], '--r', 'agarre');
ylim(1.4*tau_traccion*[-1 1]);
xlabel('t [s]'); ylabel('\tau [N m]'); title('Par: lo limita el agarre')

subplot(3,2,6)
semilogy(t, max(abs(z_sl - z_ml), [], 2) + eps, 'LineWidth', 1.5); grid on
xlabel('t [s]'); ylabel('error'); title('Diferencia Simulink - MATLAB')

exportgraphics(figura, fullfile(carpeta_res, 'respuesta_lqr.png'), 'Resolution', 150);

resumen = fullfile(carpeta_res, 'resultado_lqr.md');
fid = fopen(resumen, 'w');
fprintf(fid, '# Pendulo invertido con motor y LQR en Simulink\n\n');
fprintf(fid, '- MATLAB %s. Variante `%s`, postura %g grados, rotor: %s.\n', ...
    version, variante, postura_deg, string(incluir_rotor));
fprintf(fid, '- Modelo `%s.slx`, generado por `construir_pendulo_simulink.m`, solo bloques nativos.\n', modelo);
fprintf(fid, '- Motor: %s.\n\n', motor.nombre);
fprintf(fid, '| Magnitud | Valor |\n|---|---:|\n');
fprintf(fid, '| Polo inestable a lazo abierto | %.2f 1/s (duplica cada %.0f ms) |\n', ...
    max(real(C.autovalores_lazo_abierto)), 1000*log(2)/max(real(C.autovalores_lazo_abierto)));
fprintf(fid, '| K (V por m, m/s, rad, rad/s) | [%.1f, %.1f, %.1f, %.1f] |\n', C.K);
fprintf(fid, '| Polos a lazo cerrado | %s |\n', mat2str(round(C.polos, 2)'));
fprintf(fid, '| Par de bloqueo del motor | %.3f N m (%.1f N en el piso) |\n', motor.tau_bloqueo, motor.tau_bloqueo/r);
fprintf(fid, '| Par que el piso transmite | %.3f N m (%.1f N) |\n', tau_traccion, tau_traccion/r);
fprintf(fid, '| Velocidad maxima | %.2f m/s |\n', motor.v_max);
fprintf(fid, '| Se corre del lugar estando quieto | %.1f mm |\n', 1e3*max(abs(z_sl(antes,1))));
fprintf(fid, '| Consigna de posicion | %.2f m |\n', x_destino);
fprintf(fid, '| Retroceso antes de avanzar | %.1f mm |\n', 1e3*abs(retroceso));
fprintf(fid, '| Tiempo en llegar al 98 %% | %.2f s |\n', tiempo_de_llegada(t, z_sl(:,1), x_destino, t_consigna));
fprintf(fid, '| Tension pico | %.2f V de %.1f |\n', max(abs(U_sl)), V_bat);
fprintf(fid, '| Error Simulink vs MATLAB (phi) | %.2e rad |\n', error_estado(3));
fprintf(fid, '| Rodadura valida | %s |\n\n', string(contacto_ok));
fprintf(fid, '![Respuesta](respuesta_lqr.png)\n');
fclose(fid);

fprintf('\nfigura  -> %s\nresumen -> %s\n', fullfile(carpeta_res, 'respuesta_lqr.png'), resumen);

%% funciones auxiliares ====================================================

function tll = tiempo_de_llegada(t, x, destino, t0)
    if abs(destino) < 1e-9, tll = NaN; return; end
    fuera = find(abs(x - destino) > 0.02*abs(destino) & t >= t0, 1, 'last');
    if isempty(fuera), tll = 0; else, tll = t(fuera) - t0; end
end
