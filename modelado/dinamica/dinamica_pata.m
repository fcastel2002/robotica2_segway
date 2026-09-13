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
%   Funciones al final: terminos(theta, p, caso) y f_pata(t, x, tau, N, p, caso).
clear; clc; close all

%% 1. Parámetros (editar acá) ==============================================================
% --- geometría de la pata [m, rad]  (mismos valores que ../cinematica/parametros_geometria.m)
p.AB    = 100e-3;          % bancada, de A (servo) a B
p.AD    = 140e-3;          % manivela
p.BC    = 135e-3;          % balancín
p.CD    = 51e-3;           % acoplador, lado D->C
p.DP    = 140e-3;          % acoplador, de D al eje de la rueda P
p.a45   = deg2rad(45);     % inclinación de AB respecto de la horizontal
p.delta = deg2rad(164);    % ángulo del acoplador en D, de D->C a D->P
p.Rw    = 33e-3;           % radio de la rueda
p.theta_min = deg2rad(10); % carrera del servo: plegada
p.theta_max = deg2rad(40); %                    estirada
% --- piezas de la pata: masa [kg], centro de masa [m], inercia respecto de SU centro de masa [kg m^2]
%     (estimadas del CAD con PLA; PESAR las piezas cuando estén impresas)
p.m_AD  = 0.029;   p.AG = 0.428*p.AD;   p.IG_AD  = 7.09e-5;   % manivela:  masa, distancia A->G_AD, inercia
p.m_BC  = 0.007;   p.BG = 0.5*p.BC;     p.IG_BC  = 1.72e-5;   % balancín:  masa, distancia B->G_BC, inercia
p.m_CDP = 0.0195;  p.dG = 0.3145*p.DP;  p.IG_CDP = 6.39e-5;   % acoplador: masa, distancia D->G_CDP, inercia
p.epsG  = p.delta;                                            % ángulo de D->G_CDP desde D->C (G sobre la recta D->P)
p.m_P   = 0.030 + 0.095;   % rueda (30 g) + motorreductor (95 g) colgados de P
% --- cabina: todo lo que NO es pata. Solo hace falta su masa, no dónde está su centro de masa,
%     porque no gira (el control de equilibrio mantiene la inclinación) y solo se traslada.
p.m_cabina = 0.207 + 0.114 + 2*0.060 + 0.120 + 0.060 + 0.050;  % cabeza + tapa + 2 servos + batería + electrónica + tornillería
p.n_patas  = 2;            % patas iguales, movidas a la vez por sus dos servos
% --- servo, fricción y entorno
p.b       = 0;             % fricción viscosa en el eje del servo [N m s/rad]
p.tau_max = 21*0.0981;     % par máximo del servo DS3225MG [N m]  (21 kg cm)
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
yline(p.tau_max/0.0981, '--', 'servo DS3225MG'); xlabel('\theta [°]'); ylabel('\tau estático [kg cm]')
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
ddth = (tau' - p.b*x(:,2)' - 0.5*S.dIeq.*x(:,2)'.^2 - S.dV)./S.Ieq;         % ec. 23 despejada
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

%% Funciones ================================================================================
function R = terminos(th, p, caso)
% Todos los términos de la ecuación de movimiento para un vector de theta [rad] y un caso.
%   R.BD R.beta1 R.beta2 R.beta R.alfa1 R.alfa2 R.psi   geometría (ec. 1 a 4)
%   R.dbeta R.dpsi        beta'(theta), psi'(theta)     (ec. 10)
%   R.u (2 x n)           velocidad de la cabina por unidad de theta' (ec. 16 a 18)
%   R.Ieq R.dIeq          inercia equivalente y su derivada           (ec. 19)
%   R.V R.dV R.d2V        energía potencial y sus derivadas           (ec. 20 y 21)
%   R.wP                  velocidad vertical de P en el piso, por unidad de theta' (ec. 22)
%   R.cCoM R.dcCoM        velocidad vertical del centro de masa del robot y su derivada (ec. 25)
%   R.yP R.xP R.dyP       posición del eje de la rueda respecto de A y dyP/dtheta
%   R.A R.B R.C R.D R.P R.GAD R.GBC R.GCDP   puntos (2 x n)
  th = th(:)';  h = 1e-6;
  [Ieq, dV, R] = nucleo(th, p, caso);
  [Ip, dVp] = nucleo(th + h, p, caso);  [Im, dVm] = nucleo(th - h, p, caso);
  R.Ieq = Ieq;  R.dIeq = (Ip - Im)/(2*h);
  R.dV  = dV;   R.d2V  = (dVp - dVm)/(2*h);
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
  R = struct('theta', th, 'caso', caso, 'BD', BD, 'beta1', b1, 'beta2', b2, 'beta', beta, ...
             'alfa1', a1, 'alfa2', a2, 'psi', psi, 'dBD', dBD, 'dbeta', dbeta, 'dpsi', dpsi, ...
             'u', u, 'wP', u(2,:) + cP(2,:), 'dyP', cP(2,:), 'xP', P(1,:), 'yP', P(2,:), ...
             'A', A, 'B', B, 'C', C, 'D', D, 'P', P, 'GAD', GAD, 'GBC', GBC, 'GCDP', GCDP);
end

function dx = f_pata(~, x, tau, N, p, caso)
% Ecuación de movimiento en forma de estado (ec. 26): x = [theta; theta'].
  T  = terminos(x(1), p, caso);
  dx = [x(2); (tau - p.b*x(2) + N*T.wP - 0.5*T.dIeq*x(2)^2 - T.dV)/T.Ieq];
end
