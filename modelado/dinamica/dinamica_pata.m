%% DINAMICA_PATA  Dinámica de la pata del Segway por Lagrange. Un grado de libertad: theta
%
%   Ieq(th)·th'' + 1/2·Ieq'(th)·th'^2 + V'(th) = tau - b·th' + N·wP(th)            (ec. 23 del PDF)
%
%   theta = ángulo de AD por debajo de la horizontal (10° plegada .. 40° estirada); en el código va en rad.
%   La misma ecuación sirve para tres casos, que se eligen con el argumento 'caso'. Lo único que cambia
%   es u(th), la velocidad de la cabina por unidad de th' (ec. 16 a 18 del PDF):
%
%     'banco'   la cabina está sujeta y sube y baja la rueda.   u = 0.        Banco de pruebas.
%     'parado'  la rueda está en el piso y sube y baja la cabina. u = -cP.    EL ROBOT REAL DE PIE.
%     'aire'    nada está quieto, el centro de masa no se mueve.  u = -2S/m.  Estimación para el vuelo.
%
%   Desarrollo y numeración de las ecuaciones: dinamica_resumen.pdf. Dibujos: fig_dinamica.png, fig_casos.png.
%
%   Secciones:  1. parámetros (editar acá)      2. los tres casos, tabla y curvas
%               3. simulación de agacharse y pararse (caso 'parado', con la normal del piso)
%               4. verificación contra los diagramas de cuerpo libre de ../dcl/
%               5. caída de un escalón: qué par hace falta para absorber el golpe
%               6. fuerza radial en el eje del servo durante esa caída
%   Funciones al final: terminos(theta, p, caso) y f_pata(t, x, tau, N, p, caso).
clear; clc; close all

%% 1. Parámetros (editar acá) ==============================================================
% --- geometría de la pata [m, rad]. Segunda iteración del CAD, barras a escala 80 (medidas sobre los STEP del 14/9).
%     Mismos valores que ../parametros/parametros_fisicos.m, que es la fuente para todo el proyecto.
p.AB    = 80e-3;           % bancada, de A (servo) a B (en el STEP está en 77.9 mm a 46.6°: B quedó 3 mm corto; se modela la intención)
p.AD    = 112e-3;          % manivela
p.BC    = 108e-3;          % balancín
p.CD    = 40.8e-3;         % acoplador, lado D->C
p.DP    = 112e-3;          % acoplador, de D al eje de la rueda P
p.a45   = deg2rad(45);     % inclinación de AB respecto de la horizontal
p.delta = deg2rad(164);    % ángulo del acoplador en D, de D->C a D->P
p.Rw    = 33e-3;           % radio de la rueda
p.theta_min = deg2rad(10); % carrera del servo: plegada
p.theta_max = deg2rad(40); %                    estirada
% --- piezas de la pata: masa [kg], centro de masa [m], inercia respecto de SU centro de masa [kg m^2]
%     (las de la primera iteración escaladas a 80: la masa baja con el largo, x0.8, y la inercia x0.8^3;
%      PESAR las piezas cuando estén impresas)
p.m_AD  = 0.0232;  p.AG = 0.428*p.AD;   p.IG_AD  = 3.63e-5;   % manivela:  masa, distancia A->G_AD, inercia
p.m_BC  = 0.0056;  p.BG = 0.5*p.BC;     p.IG_BC  = 0.88e-5;   % balancín:  masa, distancia B->G_BC, inercia
p.m_CDP = 0.0156;  p.dG = 0.3145*p.DP;  p.IG_CDP = 3.27e-5;   % acoplador: masa, distancia D->G_CDP, inercia
p.epsG  = p.delta;                                            % ángulo de D->G_CDP desde D->C (G sobre la recta D->P)
p.m_P   = 0.030 + 0.152;   % rueda (30 g) + motorreductor JGB37-520 con encoder (152 g, ficha; PESAR) colgados de P
% --- cabina: todo lo que NO es pata. Solo hace falta su masa, no dónde está su centro de masa,
%     porque no gira (el control de equilibrio mantiene la inclinación) y solo se traslada.
p.m_cabina = 0.207 + 0.114 + 2*0.058 + 0.120 + 0.060 + 0.050;  % cabeza + tapa + 2 servos de 40 kg cm (58 g) + batería + electrónica + tornillería
p.n_patas  = 2;            % patas iguales, movidas a la vez por sus dos servos
% --- fricción viscosa en cada articulación [N m s/rad]: par de roce = -b_eq(theta)*theta'
%     NINGUNA está medida todavía, por eso valen cero y el modelo no tiene pérdidas. Para medirlas,
%     soltar la pata desde estirada con el servo libre y comparar la caída con la simulación.
p.b_A     = 0;             % en A, entre la cabina y la manivela. Incluye la reductora del servo (la grande)
p.b_B     = 0;             % en B, entre la cabina y el balancín
p.b_C     = 0;             % en C, entre el balancín y el acoplador
p.b_D     = 0;             % en D, entre la manivela y el acoplador
% --- servo y entorno
p.tau_max = 40*0.0981;     % par máximo del servo elegido [N m]  (40 kg cm; verificar a qué tensión lo da la ficha)
p.k_rueda = 30e3;          % rigidez del neumático por rueda [N/m]. SUPUESTO: medir apretando la rueda
p.g       = 9.81;
p.m_total = p.m_cabina + p.n_patas*(p.m_AD + p.m_BC + p.m_CDP + p.m_P);   % masa del robot [kg] (derivada)

fprintf('cabina %.0f g + %d patas de %.1f g = robot de %.0f g\n', p.m_cabina*1e3, p.n_patas, ...
        (p.m_AD + p.m_BC + p.m_CDP + p.m_P)*1e3, p.m_total*1e3);

%% 2. Los tres casos ========================================================================
th = linspace(p.theta_min, p.theta_max, 200);
Rb = terminos(th, p, 'banco');  Rp = terminos(th, p, 'parado');  Ra = terminos(th, p, 'aire');
N_pie = p.m_total*p.g/2;                 % reacción del piso por rueda, robot parado y quieto
tau_b = Rb.dV - N_pie*Rb.wP;             % banco cargado con el peso del robot   (ec. 24)
tau_p = Rp.dV;                           % parado: wP = 0, el peso de la cabina ya está en V
tau_a = Ra.dV;                           % en el aire: vale 0

figure('Name', 'Los tres casos')
subplot(2,2,1); plot(rad2deg(th), [Rb.Ieq; Rp.Ieq; Ra.Ieq]*1e3, 'LineWidth', 1.8); grid on
xlabel('\theta [°]'); ylabel('I_{eq} [g m^2]'); title('Inercia equivalente vista por el servo')
legend('banco (cabina sujeta)', 'parado (sube la cabina)', 'en el aire', 'Location', 'best')
subplot(2,2,2); plot(rad2deg(th), [tau_b; tau_p; tau_a]/0.0981, 'LineWidth', 1.8); grid on
yline(p.tau_max/0.0981, '--', 'servo servo'); xlabel('\theta [°]'); ylabel('\tau estático [kg cm]')
legend('banco con el peso encima', 'parado', 'en el aire', 'Location', 'best'); title('Par estático (los dos primeros coinciden)')
subplot(2,2,3); plot(rad2deg(th), (p.Rw - Rp.yP)*1e3, 'LineWidth', 1.8); grid on
xlabel('\theta [°]'); ylabel('h [mm]'); title('Altura de la cabina sobre el piso: h = R_w - y_P(\theta)')
subplot(2,2,4); plot(rad2deg(th), [Rp.dbeta; Rp.dpsi], 'LineWidth', 1.8); grid on
xlabel('\theta [°]'); ylabel('[rad/rad]'); legend('\beta''', '\psi''', 'Location', 'best'); title('Relaciones de transmisión')

th_t = deg2rad([10 25 40]);
Tb = terminos(th_t, p, 'banco'); Tp = terminos(th_t, p, 'parado'); Ta = terminos(th_t, p, 'aire');
fprintf('\n theta   h[mm]  | Ieq [g m2]: banco  parado   aire | parado/banco aire/banco | tau [kg cm]: banco parado  aire\n');
for k = 1:numel(th_t)
  fprintf('%5.0f  %6.1f  |            %6.2f  %6.2f %6.2f |    %5.2f      %5.2f   |          %6.2f %6.2f %5.2f\n', ...
    rad2deg(th_t(k)), (p.Rw - Tp.yP(k))*1e3, Tb.Ieq(k)*1e3, Tp.Ieq(k)*1e3, Ta.Ieq(k)*1e3, ...
    Tp.Ieq(k)/Tb.Ieq(k), Ta.Ieq(k)/Tb.Ieq(k), (Tb.dV(k) - N_pie*Tb.wP(k))/0.0981, Tp.dV(k)/0.0981, Ta.dV(k)/0.0981);
end
% comprobaciones de consistencia entre los tres casos
fprintf('banco con N = m g/n contra parado: diferencia máxima de par estático %.1e N m (deben coincidir)\n', ...
        max(abs(tau_b - tau_p)));
fprintf('en el aire la gravedad no actúa sobre theta: max |V''| = %.1e N m (debe ser cero)\n', max(abs(Ra.dV)));

%% 3. Simulación: agacharse y pararse, con el robot de pie ==================================
% Servo modelado como control de posición con par saturado. Consigna: partir estirado (40°),
% agacharse a 10° en 0.6 s, esperar, y volver a pararse en 0.6 s.
caso = 'parado';  Kp = 30;  Kd = 0.5;  N_sim = 0;    % en 'parado' la normal no hace trabajo: N no entra
suave  = @(s) 0.5 - 0.5*cos(pi*min(max(s, 0), 1));
th_ref = @(t) p.theta_max + (p.theta_min - p.theta_max)*suave((t - 0.2)/0.6) ...
                          + (p.theta_max - p.theta_min)*suave((t - 1.2)/0.6);
tau_servo = @(t, x) min(max(Kp*(th_ref(t) - x(1)) - Kd*x(2), -p.tau_max), p.tau_max);
[t, x] = ode45(@(t, x) f_pata(t, x, tau_servo(t, x), N_sim, p, caso), [0 2.5], [p.theta_max; 0]);
tau = arrayfun(@(k) tau_servo(t(k), x(k,:)'), 1:numel(t))';
S = terminos(x(:,1)', p, caso);
ddth = (tau' - S.beq.*x(:,2)' - 0.5*S.dIeq.*x(:,2)'.^2 - S.dV)./S.Ieq;      % ec. 23 despejada
N_rueda = (p.m_total/2)*(p.g + S.cCoM.*ddth + S.dcCoM.*x(:,2)'.^2);         % ec. 25: si llega a 0, despega

figure('Name', 'Agacharse y pararse (robot de pie)')
subplot(4,1,1); plot(t, rad2deg(x(:,1)), t, rad2deg(th_ref(t)), '--', 'LineWidth', 1.5); grid on
ylabel('\theta [°]'); legend('\theta', '\theta_{ref}', 'Location', 'best'); title('Agacharse y pararse con la rueda en el piso')
subplot(4,1,2); plot(t, (p.Rw - S.yP)*1e3, 'LineWidth', 1.5); grid on; ylabel('altura cabina [mm]')
subplot(4,1,3); plot(t, tau/0.0981, 'LineWidth', 1.5); grid on; yline([-1 1]*p.tau_max/0.0981, '--'); ylabel('\tau servo [kg cm]')
subplot(4,1,4); plot(t, N_rueda, 'LineWidth', 1.5); grid on; yline(0, '--'); yline(N_pie, ':'); ylabel('N por rueda [N]'); xlabel('t [s]')
fprintf('\nsimulación: par máximo %.1f kg cm (servo %.0f), normal entre %.2f y %.2f N (estática %.2f N)\n', ...
        max(abs(tau))/0.0981, p.tau_max/0.0981, min(N_rueda), max(N_rueda), N_pie);
if min(N_rueda) <= 0, fprintf('  ATENCION: la normal llega a cero, el robot despega en esta maniobra\n'); end

%% 4. Verificación contra los diagramas de cuerpo libre (../dcl/dcl_pata.png) ===============
% Robot parado, postura más desfavorable theta = 10°. Equilibrio de los tres cuerpos de la pata
% (fuerzas y momentos en AD, BC y CDP+rueda): 9 ecuaciones, 9 incógnitas [Ax Ay tau Bx By Cx Cy Dx Dy].
% (Dx,Dy) es la fuerza del acoplador sobre AD en D, y (Cx,Cy) la del acoplador sobre BC en C.
th0 = deg2rad(10); T0 = terminos(th0, p, 'banco'); g = p.g; N0 = N_pie;
A0 = T0.A'; B0 = T0.B'; C0 = T0.C'; D0 = T0.D'; P0 = T0.P'; GAD = T0.GAD'; GBC = T0.GBC'; GCDP = T0.GCDP';
M9 = zeros(9); b9 = zeros(9,1);
M9(1,[1 8]) = [1 1];
M9(2,[2 9]) = [1 1];                            b9(2) = p.m_AD*g;
M9(3,[3 8 9]) = [-1, -D0(2), D0(1)];            b9(3) = p.m_AD*g*GAD(1);
M9(4,[4 6]) = [1 1];
M9(5,[5 7]) = [1 1];                            b9(5) = p.m_BC*g;
M9(6,[6 7]) = [-(C0(2)-B0(2)), C0(1)-B0(1)];    b9(6) = p.m_BC*g*(GBC(1)-B0(1));
M9(7,[6 8]) = [-1 -1];
M9(8,[7 9]) = [-1 -1];                          b9(8) = (p.m_CDP + p.m_P)*g - N0;
M9(9,[6 7]) = [C0(2)-D0(2), -(C0(1)-D0(1))];
b9(9) = p.m_CDP*g*(GCDP(1)-D0(1)) + (p.m_P*g - N0)*(P0(1)-D0(1));
sol = M9\b9;  tau_dcl = sol(3);
tau_banco  = T0.dV - N0*T0.wP;                       % Lagrange, caso 'banco' con N externo
tau_parado = getfield(terminos(th0, p, 'parado'), 'dV');   % Lagrange, caso 'parado' (sin N)
fprintf('\npar del servo en theta = 10°, robot parado, tres caminos distintos:\n');
fprintf('  DCL (9 ecuaciones)      %.4f N m = %.2f kg cm\n', tau_dcl, tau_dcl/0.0981);
fprintf('  Lagrange caso banco     %.4f N m = %.2f kg cm   (diferencia %.1e)\n', tau_banco, tau_banco/0.0981, tau_banco - tau_dcl);
fprintf('  Lagrange caso parado    %.4f N m = %.2f kg cm   (diferencia %.1e)\n', tau_parado, tau_parado/0.0981, tau_parado - tau_dcl);

%% 5. Caída de un escalón ==================================================================
% El robot rueda y sale de un escalón: cae libre, la rueda golpea el piso de abajo, y la pata tiene
% que frenar a la cabina antes de llegar al tope de plegado. Tres fases:
%   1. caída libre   el eje de la rueda baja la altura del escalón. Caso 'aire': el servo casi no trabaja
%   2. impacto       la rueda se detiene de golpe y la cabina, que sigue bajando, arrastra a theta (impulsivo)
%   3. absorción     el servo frena, plegando la pata desde th_land hacia el tope
h_escalon = 0.18;                 % altura del escalón [m]                              <-- editar
th_land   = p.theta_max;          % postura al tocar el piso (estirada = toda la carrera disponible)
th_tope   = p.theta_min;          % tope de plegado

% --- fase 1: caída libre
v_imp   = sqrt(2*p.g*h_escalon);
t_caida = v_imp/p.g;

% --- fase 2: impacto. Matriz de masa por servo en las coordenadas (Y_A, theta), con Y_A la altura de la
%     cabina: M11 = m/n, M12 = suma de m_j cy_j de una pata, M22 = Ieq del caso 'banco'. El impulso vertical
%     del piso detiene la rueda y reparte el resto del movimiento entre la cabina y theta:
%         M (q+ - q-) = J [1; yP'],   q- = (-v_imp, 0),   q+ = (-yP' th'+, th'+)
T1  = terminos(th_land, p, 'banco');
M11 = p.m_total/p.n_patas;
M12 = p.m_AD*T1.cGAD(2) + p.m_BC*T1.cGBC(2) + p.m_CDP*T1.cGCDP(2) + p.m_P*T1.cP(2);
M22 = T1.Ieq;   yPp = T1.dyP;
Ip  = M22 - 2*M12*yPp + M11*yPp^2;             % inercia con la rueda apoyada (= Ieq del caso 'parado')
dth_imp = v_imp*(M11*yPp - M12)/Ip;            % velocidad de plegado justo después del golpe [rad/s]
K_antes = 0.5*M11*v_imp^2;   K_desp = 0.5*Ip*dth_imp^2;

% --- fase 3: energía a disipar y par medio necesario sobre la carrera
Tg      = terminos(linspace(th_tope, th_land, 400), p, 'parado');
DV      = trapz(Tg.theta, Tg.dV);              % V(th_land) - V(th_tope): al plegarse la gravedad suma energía
carrera = th_land - th_tope;
E_abs   = K_desp + DV;                         % energía que el servo debe absorber, por servo
tau_med = E_abs/carrera;
E_servo = p.tau_max*carrera;                   % lo máximo que puede absorber frenando a fondo
h_max   = h_escalon*(E_servo - DV)/K_desp;     % escalón que sí entra en la carrera

% --- fase 3 simulada: el servo frena a fondo desde el golpe hasta detenerse o tocar el tope
opc = odeset('Events', @(t, x) ev_absorcion(t, x, p), 'RelTol', 1e-8, 'AbsTol', 1e-10);
[t3, x3] = ode45(@(t, x) f_pata(t, x, p.tau_max, 0, p, 'parado'), [0 1], [th_land; dth_imp], opc);
S3  = terminos(x3(:,1)', p, 'parado');
dd3 = (p.tau_max - S3.beq.*x3(:,2)' - 0.5*S3.dIeq.*x3(:,2)'.^2 - S3.dV)./S3.Ieq;
N3  = (p.m_total/p.n_patas)*(p.g + S3.cCoM.*dd3 + S3.dcCoM.*x3(:,2)'.^2);
K_fin = 0.5*S3.Ieq(end)*x3(end,2)^2;

fprintf('\n=== caída de un escalón de %.0f cm, aterrizando estirada (theta = %.0f°) ===\n', h_escalon*100, rad2deg(th_land));
fprintf('  1. caída libre: %.0f ms, la rueda llega al piso a %.2f m/s\n', t_caida*1e3, v_imp);
fprintf('  2. impacto: la pata arranca a plegarse a %.1f rad/s (%.0f °/s). Energía por servo %.3f J -> %.3f J\n', ...
        abs(dth_imp), abs(rad2deg(dth_imp)), K_antes, K_desp);
fprintf('     (el golpe se lleva el %.0f por ciento, que es el momento de la rueda y el motor)\n', 100*(1 - K_desp/K_antes));
fprintf('  3. absorción: hay que disipar %.3f J por servo (%.3f del golpe + %.3f que suma la gravedad) en %.0f° de carrera\n', ...
        E_abs, K_desp, DV, rad2deg(carrera));
fprintf('     PAR MEDIO NECESARIO %.2f N m = %.1f kg cm por servo   (el servo da %.0f kg cm)\n', ...
        tau_med, tau_med/0.0981, p.tau_max/0.0981);
fprintf('     frenando a fondo el servo absorbe %.3f J: le alcanza hasta un escalón de %.0f cm\n', E_servo, h_max*100);
if x3(end,1) <= th_tope + 1e-9
  fprintf('     SIMULACION: NO alcanza a frenar. Toca el tope a %.1f rad/s con %.3f J sin disipar (%.0f por ciento del golpe)\n', ...
          abs(x3(end,2)), K_fin, 100*K_fin/K_desp);
else
  fprintf('     SIMULACION: frena en %.0f ms usando %.1f° de los %.0f° de carrera\n', ...
          t3(end)*1e3, rad2deg(th_land - x3(end,1)), rad2deg(carrera));
end
N_est = p.m_total*p.g/p.n_patas;
fprintf('     fuerza contra el piso mientras el servo frena: hasta %.0f N por rueda = %.1f veces la carga estática\n', ...
        max(N3), max(N3)/N_est);
if K_fin > 0
  d_neum = sqrt(2*K_fin/p.k_rueda);            % lo que resta se lo come el neumático al tocar el tope
  fprintf('     el golpe contra el tope hunde el neumático %.1f mm y le pega %.0f N = %.0f veces la carga estática\n', ...
          d_neum*1e3, p.k_rueda*d_neum, p.k_rueda*d_neum/N_est);
end

% --- par medio necesario en función de la altura del escalón (K del golpe es proporcional a h)
h_barrido = linspace(0.02, 0.30, 200);
tau_h = (K_desp*(h_barrido/h_escalon) + DV)/carrera;

figure('Name', sprintf('Caída de un escalón de %.0f cm', h_escalon*100))
subplot(2,2,1); plot(t3*1e3, rad2deg(x3(:,1)), 'LineWidth', 1.5); grid on
yline(rad2deg(th_tope), '--', 'tope de plegado'); ylabel('\theta [°]'); xlabel('t [ms]')
title(sprintf('Escalón de %.0f cm: la pata se pliega para frenar', h_escalon*100))
subplot(2,2,2); plot(t3*1e3, (p.Rw - S3.yP)*1e3, 'LineWidth', 1.5); grid on
ylabel('altura de la cabina [mm]'); xlabel('t [ms]'); title('La cabina baja mientras la rueda está quieta')
subplot(2,2,3); plot(t3*1e3, N3, 'LineWidth', 1.5); grid on
yline(N_est, ':', 'carga estática'); ylabel('N por rueda [N]'); xlabel('t [ms]'); title('Fuerza contra el piso')
subplot(2,2,4); plot(h_barrido*100, tau_h/0.0981, 'LineWidth', 1.8); grid on
yline(p.tau_max/0.0981, '--', 'servo'); xline(h_max*100, ':', sprintf('%.0f cm', h_max*100))
xlabel('altura del escalón [cm]'); ylabel('\tau medio necesario [kg cm]'); title('Hasta qué escalón alcanza el servo')

%% 6. Fuerza radial en el eje del servo durante la caída ====================================
% Con theta(t), theta'(t) y theta''(t) de la sección 5 quedan determinadas TODAS las aceleraciones, así que
% se puede resolver el mismo sistema de la sección 4 pero dinámico: para cada pieza, suma de fuerzas = m a
% y suma de momentos respecto de SU centro de masa = I alfa. Nueve ecuaciones, nueve incógnitas
% [Ax Ay tau Bx By Cx Cy Dx Dy]. La que interesa es (Ax, Ay): lo que la manivela le tira al eje del servo.
% N y F (normal y tangencial del piso) no son incógnitas: salen de la aceleración del centro de masa.

% --- chequeo: en estático tiene que dar lo mismo que la sección 4
[z0, N0d] = reacciones(deg2rad(10), 0, 0, p);
fprintf('\nchequeo estático de las reacciones en theta = 10°: tau = %.2f kg cm, A = (%.2f, %.2f) N, N = %.2f N\n', ...
        z0(3)/0.0981, z0(1), z0(2), N0d);

% --- durante el frenado del escalón
nT = numel(t3);  Z = zeros(nT, 9);  Nv = zeros(nT, 1);
for k = 1:nT
  [Z(k,:), Nv(k)] = reacciones(x3(k,1), x3(k,2), dd3(k), p);
end
radial_A = hypot(Z(:,1), Z(:,2));      % lo que ve el eje del servo
radial_B = hypot(Z(:,4), Z(:,5));
radial_C = hypot(Z(:,6), Z(:,7));
radial_D = hypot(Z(:,8), Z(:,9));
[rA_max, kA] = max(radial_A);

% --- el instante peor no es el frenado sino el golpe contra el tope: ahí la normal salta al valor
%     que impone el neumático. Se estima cuasi-estático con esa normal.
if K_fin > 0
  N_tope = p.k_rueda*sqrt(2*K_fin/p.k_rueda);
  z_tope = reacciones_con_N(th_tope, 0, 0, N_tope, 0, p);
  rA_tope = hypot(z_tope(1), z_tope(2));
else
  N_tope = NaN; rA_tope = NaN;
end

fprintf('\n=== fuerza radial en el eje del servo, escalón de %.0f cm ===\n', h_escalon*100);
fprintf('  parado y quieto (referencia)      %5.1f N\n', hypot(z0(1), z0(2)));
fprintf('  durante el frenado, máximo        %5.1f N   (a los %.0f ms, con N = %.1f N por rueda)\n', ...
        rA_max, t3(kA)*1e3, Nv(kA));
if ~isnan(rA_tope)
  fprintf('  al golpear el tope de plegado      %5.1f N   (N = %.0f N por rueda, del neumático)\n', rA_tope, N_tope);
end
fprintf('  máximos en los otros pasadores durante el frenado: B %.1f N, C %.1f N, D %.1f N\n', ...
        max(radial_B), max(radial_C), max(radial_D));

% --- ¿de qué depende el pico? Con más par el servo frena antes y no llega a golpear el tope
fprintf('\n  cómo cambia el pico con el par del servo:\n');
for tk = [21 25 35 40]
  pp = p;  pp.tau_max = tk*0.0981;
  [tt, xx] = ode45(@(t, x) f_pata(t, x, pp.tau_max, 0, pp, 'parado'), [0 1], [th_land; dth_imp], opc);
  SS  = terminos(xx(:,1)', pp, 'parado');
  ddx = (pp.tau_max - SS.beq.*xx(:,2)' - 0.5*SS.dIeq.*xx(:,2)'.^2 - SS.dV)./SS.Ieq;
  if xx(end,1) <= th_tope + 1e-9                              % llega al tope con energía sobrante
    Kf = 0.5*SS.Ieq(end)*xx(end,2)^2;   Nt = sqrt(2*Kf*pp.k_rueda);
    zt = reacciones_con_N(th_tope, 0, 0, Nt, 0, pp);
    fprintf('    %2.0f kg cm: golpea el tope a %.1f rad/s  ->  pico en A %5.1f N\n', tk, abs(xx(end,2)), hypot(zt(1), zt(2)));
  else
    rr = zeros(numel(tt),1);
    for k = 1:numel(tt), zz = reacciones(xx(k,1), xx(k,2), ddx(k), pp); rr(k) = hypot(zz(1), zz(2)); end
    fprintf('    %2.0f kg cm: frena sin tocar el tope        ->  pico en A %5.1f N\n', tk, max(rr));
  end
end

% --- el otro pico, que el modelo de golpe rígido esconde: el instante del toque. La energía que el
%     golpe "pierde" no desaparece, la absorbe el neumático al frenar en seco la rueda y el motor.
E_golpe = K_antes - K_desp;
d_toque = sqrt(2*E_golpe/p.k_rueda);   N_toque = p.k_rueda*d_toque;
z_toque = reacciones_con_N(th_land, dth_imp, 0, N_toque, 0, p);
fprintf('\n  el otro pico, en el instante del toque (estimación cuasi-estática):\n');
fprintf('    los %.3f J que se lleva el golpe los absorbe el neumático: se hunde %.1f mm y recibe %.0f N (%.0f veces la estática)\n', ...
        E_golpe, d_toque*1e3, N_toque, N_toque/N_est);
fprintf('    con esa normal el eje del servo vería %.0f N\n', hypot(z_toque(1), z_toque(2)));

figure('Name', 'Fuerza en los pasadores durante la caída')
subplot(2,1,1); plot(t3*1e3, [radial_A radial_B radial_C radial_D], 'LineWidth', 1.5); grid on
legend('A (eje del servo)', 'B', 'C', 'D', 'Location', 'best')
ylabel('fuerza radial [N]'); title(sprintf('Escalón de %.0f cm: carga en los pasadores mientras el servo frena', h_escalon*100))
subplot(2,1,2); plot(t3*1e3, Z(:,3)/0.0981, 'LineWidth', 1.5); grid on
yline(p.tau_max/0.0981, '--', 'servo'); ylabel('\tau [kg cm]'); xlabel('t [ms]')

%% Funciones ================================================================================
function R = terminos(th, p, caso)
% Todos los términos de la ecuación de movimiento para un vector de theta [rad] y un caso.
%   R.BD R.beta1 R.beta2 R.beta R.alfa1 R.alfa2 R.psi   geometría (ec. 1 a 4)
%   R.dbeta R.dpsi        beta'(theta), psi'(theta)     (ec. 10)
%   R.u (2 x n)           velocidad de la cabina por unidad de theta' (ec. 16 a 18)
%   R.Ieq R.dIeq          inercia equivalente y su derivada           (ec. 19)
%   R.dV R.d2V            derivadas de la energía potencial          (ec. 20 y 21)
%   R.cGAD R.cGBC R.cGCDP R.cP   coeficientes de velocidad en el marco de la cabina (ec. 11 a 14)
%   R.wP                  velocidad vertical de P en el piso, por unidad de theta' (ec. 22)
%   R.beq                 fricción viscosa equivalente vista por el servo [N m s/rad]
%   R.cCoM R.dcCoM        velocidad vertical del centro de masa del robot y su derivada (ec. 25)
%   R.yP R.xP R.dyP       posición del eje de la rueda respecto de A y dyP/dtheta
%   R.A R.B R.C R.D R.P R.GAD R.GBC R.GCDP   puntos (2 x n)
  th = th(:)';  h = 1e-6;
  [Ieq, dV, R] = nucleo(th, p, caso);
  [Ip, dVp, Rp] = nucleo(th + h, p, caso);  [Im, dVm, Rm] = nucleo(th - h, p, caso);
  R.Ieq = Ieq;  R.dIeq = (Ip - Im)/(2*h);
  R.dV  = dV;   R.d2V  = (dVp - dVm)/(2*h);
  d = @(f) (Rp.(f) - Rm.(f))/(2*h);       % derivadas respecto de theta, para las aceleraciones
  R.ddbeta = d('dbeta');  R.ddpsi = d('dpsi');
  R.dcGAD = d('cGAD');  R.dcGBC = d('cGBC');  R.dcGCDP = d('cGCDP');  R.dcP = d('cP');
  R.dcCoMv = d('cCoMv');
  R.cCoM  = 2*R.dV /(p.g*p.m_total);      % dy_CoM/dtheta : de dV = g m_total cCoM / 2 (por servo)
  R.dcCoM = 2*R.d2V/(p.g*p.m_total);
end

function [Ieq, dV, R] = nucleo(th, p, caso)
  AB = p.AB; AD = p.AD; BC = p.BC; CD = p.CD; DP = p.DP; a45 = p.a45; dl = p.delta;
  % --- geometría: ley del coseno (ec. 1 a 3) y giro del acoplador (ec. 4)
  BD = sqrt(AB^2 + AD^2 - 2*AB*AD*cos(th + a45));
  b1 = acos((AB^2 + BD.^2 - AD^2)./(2*AB*BD));  b2 = acos((BC^2 + BD.^2 - CD^2)./(2*BC*BD));
  a1 = acos((AD^2 + BD.^2 - AB^2)./(2*AD*BD));  a2 = acos((CD^2 + BD.^2 - BC^2)./(2*CD*BD));
  beta = b1 + b2;  psi = pi - th - a1 - a2;
  % --- posiciones (ec. 5 y 6), 2 x n
  A = zeros(2, numel(th));  B = [AB*cos(a45); AB*sin(a45)].*ones(1, numel(th));
  D = AD*[cos(th); -sin(th)];
  C = D + CD*[cos(psi); sin(psi)];   P = D + DP*[cos(psi + dl); sin(psi + dl)];
  GAD = p.AG*[cos(th); -sin(th)];    GBC = B + p.BG*[cos(5*pi/4 + beta); sin(5*pi/4 + beta)];
  GCDP = D + p.dG*[cos(psi + p.epsG); sin(psi + p.epsG)];
  % --- derivadas (ec. 7 a 10): d(ángulo)/dBD = -cot(ángulo del otro extremo)/BD
  dBD   = AB*AD*sin(th + a45)./BD;
  dbeta = -(cot(a1) + cot(a2)).*dBD./BD;
  dpsi  = -1 + (cot(b1) + cot(b2)).*dBD./BD;
  % --- coeficientes de velocidad en el marco de la cabina (ec. 11 a 14): c_Q = dr_Q/dtheta
  gir = @(r) [-r(2,:); r(1,:)];                    % k x r
  cD    = -gir(D);                                 % AD gira alrededor de A con velocidad angular -1
  cGAD  = -gir(GAD);
  cGBC  = dbeta.*gir(GBC - B);                     % BC gira alrededor de B con velocidad angular dbeta
  cGCDP = cD + dpsi.*gir(GCDP - D);                % acoplador: v = v_D + dpsi (k x (Q - D))
  cP    = cD + dpsi.*gir(P - D);
  % --- velocidad de la cabina por unidad de theta' (ec. 16 a 18): lo único que distingue los tres casos
  switch caso
    case 'banco',  u = zeros(2, numel(th));
    case 'parado', u = -cP;
    case 'aire'
      S = p.m_AD*cGAD + p.m_BC*cGBC + p.m_CDP*cGCDP + p.m_P*cP;          % por pata
      u = -p.n_patas*S/p.m_total;
    otherwise, error('dinamica_pata: caso "%s" desconocido (usar banco, parado o aire)', caso);
  end
  % --- inercia equivalente por servo (ec. 19) y energía potencial (ec. 20 y 21)
  q = @(v) sum(v.^2, 1);
  Ieq = p.IG_AD + p.IG_BC*dbeta.^2 + p.IG_CDP*dpsi.^2 ...                % giro propio de las tres piezas
      + (p.m_cabina/p.n_patas)*q(u) + p.m_AD*q(u + cGAD) + p.m_BC*q(u + cGBC) ...
      + p.m_CDP*q(u + cGCDP) + p.m_P*q(u + cP);
  dV = p.g*((p.m_cabina/p.n_patas)*u(2,:) + p.m_AD*(u(2,:) + cGAD(2,:)) + p.m_BC*(u(2,:) + cGBC(2,:)) ...
          + p.m_CDP*(u(2,:) + cGCDP(2,:)) + p.m_P*(u(2,:) + cP(2,:)));
  % --- fricción equivalente vista por el servo: cada articulación con su velocidad angular relativa
  beq = p.b_A + p.b_B*dbeta.^2 + p.b_C*(dpsi - dbeta).^2 + p.b_D*(dpsi + 1).^2;
  % --- velocidad del centro de masa del robot por unidad de theta' (vector), para las fuerzas del piso
  cCoMv = ((p.m_cabina/p.n_patas)*u + p.m_AD*(u + cGAD) + p.m_BC*(u + cGBC) ...
           + p.m_CDP*(u + cGCDP) + p.m_P*(u + cP)) / (p.m_total/p.n_patas);
  R = struct('theta', th, 'caso', caso, 'BD', BD, 'beta1', b1, 'beta2', b2, 'beta', beta, ...
             'alfa1', a1, 'alfa2', a2, 'psi', psi, 'dBD', dBD, 'dbeta', dbeta, 'dpsi', dpsi, ...
             'u', u, 'wP', u(2,:) + cP(2,:), 'dyP', cP(2,:), 'xP', P(1,:), 'yP', P(2,:), 'beq', beq, ...
             'cCoMv', cCoMv, ...
             'A', A, 'B', B, 'C', C, 'D', D, 'P', P, 'GAD', GAD, 'GBC', GBC, 'GCDP', GCDP, ...
             'cGAD', cGAD, 'cGBC', cGBC, 'cGCDP', cGCDP, 'cP', cP);
end

function [z, N, F] = reacciones(th, dth, ddth, p)
% Reacciones en las cuatro articulaciones con el robot apoyado, para un estado (theta, theta', theta'').
% N y F, las fuerzas normal y tangencial del piso por rueda, salen de la aceleración del centro de masa.
  T = terminos(th, p, 'parado');
  aCoM = T.cCoMv*ddth + T.dcCoMv*dth^2;
  N = (p.m_total/p.n_patas)*(p.g + aCoM(2));
  F = (p.m_total/p.n_patas)*aCoM(1);
  z = reacciones_con_N(th, dth, ddth, N, F, p);
end

function z = reacciones_con_N(th, dth, ddth, N, F, p)
% Igual que reacciones, pero con las fuerzas del piso impuestas desde afuera. Sirve para el golpe contra
% el tope, donde la normal la fija el neumático y no la aceleración del mecanismo.
% z = [Ax Ay tau Bx By Cx Cy Dx Dy]. Signos: (Dx,Dy) es lo que el acoplador le hace a la manivela en D,
% (Cx,Cy) lo que el acoplador le hace al balancín en C, y tau es positivo en el sentido en que crece theta.
  T = terminos(th, p, 'parado');  g = p.g;
  rA = T.A; rB = T.B; rC = T.C; rD = T.D; rP = T.P;
  rGAD = T.GAD; rGBC = T.GBC; rGCDP = T.GCDP;
  rQ = rP + [0; -p.Rw];                                     % punto de contacto con el piso
  % --- aceleraciones: a_Q = (cQ - cP) theta'' + (cQ' - cP') theta'^2, porque P está quieto
  acel = @(c, dc) (c - T.cP)*ddth + (dc - T.dcP)*dth^2;
  aGAD = acel(T.cGAD, T.dcGAD);  aGBC = acel(T.cGBC, T.dcGBC);  aGCDP = acel(T.cGCDP, T.dcGCDP);
  alAD  = -ddth;                                            % la manivela gira a -theta'
  alBC  = T.dbeta*ddth + T.ddbeta*dth^2;
  alCDP = T.dpsi*ddth  + T.ddpsi*dth^2;
  % --- acoplador + rueda + motor como un solo cuerpo rígido
  mcw  = p.m_CDP + p.m_P;
  rGcw = (p.m_CDP*rGCDP + p.m_P*rP)/mcw;
  Icw  = p.IG_CDP + p.m_CDP*sum((rGCDP - rGcw).^2) + p.m_P*sum((rP - rGcw).^2);
  aGcw = p.m_CDP*aGCDP/mcw;                                 % la rueda está quieta, su aceleración es cero
  % --- brazos respecto del centro de masa de cada cuerpo
  pA = rA - rGAD;  pD = rD - rGAD;
  qB = rB - rGBC;  qC = rC - rGBC;
  sD = rD - rGcw;  sC = rC - rGcw;  sQ = rQ - rGcw;
  % --- las nueve ecuaciones
  M = zeros(9);  b = zeros(9,1);
  M(1,[1 8]) = [1 1];                                    b(1) = p.m_AD*aGAD(1);
  M(2,[2 9]) = [1 1];                                    b(2) = p.m_AD*(aGAD(2) + g);
  M(3,[1 2 3 8 9]) = [-pA(2), pA(1), -1, -pD(2), pD(1)]; b(3) = p.IG_AD*alAD;
  M(4,[4 6]) = [1 1];                                    b(4) = p.m_BC*aGBC(1);
  M(5,[5 7]) = [1 1];                                    b(5) = p.m_BC*(aGBC(2) + g);
  M(6,[4 5 6 7]) = [-qB(2), qB(1), -qC(2), qC(1)];       b(6) = p.IG_BC*alBC;
  M(7,[6 8]) = [-1 -1];                                  b(7) = mcw*aGcw(1) - F;
  M(8,[7 9]) = [-1 -1];                                  b(8) = mcw*(aGcw(2) + g) - N;
  M(9,[6 7 8 9]) = [sC(2), -sC(1), sD(2), -sD(1)];       b(9) = Icw*alCDP - sQ(1)*N + sQ(2)*F;
  z = (M\b)';
end

function [v, term, dir] = ev_absorcion(~, x, p)
% Fin de la absorción: la pata se detiene (theta' = 0) o llega al tope de plegado.
  v = [x(2); x(1) - p.theta_min];   term = [1; 1];   dir = [1; -1];
end

function dx = f_pata(~, x, tau, N, p, caso)
% Ecuación de movimiento en forma de estado (ec. 26): x = [theta; theta'].
  T  = terminos(x(1), p, caso);
  dx = [x(2); (tau - T.beq*x(2) + N*T.wP - 0.5*T.dIeq*x(2)^2 - T.dV)/T.Ieq];
end
