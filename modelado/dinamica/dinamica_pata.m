%% DINAMICA_PATA  Dinámica de una pata del Segway por Lagrange (cabina fija, un grado de libertad: theta)
%
%   Ieq(th)·th'' + 1/2·Ieq'(th)·th'^2 + V'(th) = tau - b·th' + N·yP'(th)        (ec. 22 del PDF)
%
%   theta = ángulo de AD por debajo de la horizontal (10° plegada .. 40° estirada); en el código va en rad.
%   Desarrollo y numeración de las ecuaciones: dinamica_resumen.pdf.
%
%   Secciones:  1. parámetros (editar acá)     2. términos en función de theta (tabla y curvas)
%               3. ejemplo de simulación de una trayectoria con ode45
%   Funciones al final del archivo:  terminos(theta, p)  y  f_pata(t, x, tau, N, p)
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
% --- masas [kg], centros de masa [m] e inercias respecto del centro de masa [kg m^2]
%     (estimados del CAD con PLA; pesar las piezas cuando estén impresas)
p.m_AD  = 0.029;   p.AG = 0.428*p.AD;   p.IG_AD  = 7.09e-5;   % manivela:  masa, distancia A->G_AD, inercia
p.m_BC  = 0.007;   p.BG = 0.5*p.BC;     p.IG_BC  = 1.72e-5;   % balancín:  masa, distancia B->G_BC, inercia
p.m_CDP = 0.0195;  p.dG = 0.3145*p.DP;  p.IG_CDP = 6.39e-5;   % acoplador: masa, distancia D->G_CDP, inercia
p.epsG  = p.delta;                                            % ángulo de D->G_CDP medido desde D->C (G sobre la recta D->P)
p.m_P   = 0.030 + 0.095;   % rueda (30 g) + motorreductor (95 g) colgados de P
% --- servo, fricción y entorno
p.b       = 0;             % fricción viscosa en el eje del servo [N m s/rad]
p.tau_max = 21*0.0981;     % par máximo del servo DS3225MG [N m]  (21 kg cm)
p.m_robot = 1.03;          % masa del robot [kg]: reacción del piso por pata parado, N = m_robot·g/2
p.g       = 9.81;

%% 2. Términos de la ecuación en función de theta =========================================
th = linspace(p.theta_min, p.theta_max, 200);
T  = terminos(th, p);
N_parado = p.m_robot*p.g/2;
tau_aire   = T.dV;                       % par estático con la pata en el aire      (ec. 24 con N = 0)
tau_parado = T.dV - N_parado*T.dyP;      % par estático con el robot parado

figure('Name', 'Términos de la dinámica de la pata')
subplot(2,2,1); plot(rad2deg(th), T.Ieq*1e3, 'LineWidth', 1.5); grid on
xlabel('\theta [°]'); ylabel('I_{eq} [g m^2]'); title('Inercia equivalente vista por el servo')
subplot(2,2,2); plot(rad2deg(th), [T.dbeta; T.dpsi], 'LineWidth', 1.5); grid on
xlabel('\theta [°]'); ylabel('[rad/rad]'); legend('\beta''', '\psi''', 'Location', 'best'); title('Relaciones de transmisión')
subplot(2,2,3); plot(rad2deg(th), T.yP*1e3, 'LineWidth', 1.5); grid on
xlabel('\theta [°]'); ylabel('y_P [mm]'); title('Altura del eje de la rueda respecto de A')
subplot(2,2,4); plot(rad2deg(th), [tau_aire; tau_parado]/0.0981, 'LineWidth', 1.5); grid on
yline(p.tau_max/0.0981, '--', 'servo'); xlabel('\theta [°]'); ylabel('[kg cm]')
legend('en el aire', 'parado', 'Location', 'best'); title('Par estático del servo')

th_tab = deg2rad([10 25 40]); Tt = terminos(th_tab, p);
disp('theta[°]   BD[mm]  beta[°]  psi[°]   beta''    psi''    Ieq[kg m2]  dV[N m]  yP[mm]  tau_aire[kg cm]  tau_parado[kg cm]')
disp([rad2deg(th_tab); Tt.BD*1e3; rad2deg(Tt.beta); rad2deg(Tt.psi); Tt.dbeta; Tt.dpsi; Tt.Ieq; Tt.dV; Tt.yP*1e3; ...
      Tt.dV/0.0981; (Tt.dV - N_parado*Tt.dyP)/0.0981]')

%% 3. Ejemplo: simular una trayectoria ======================================================
% El servo se modela como control de posición con par saturado:  tau = sat(Kp (th_ref - th) - Kd th')
% Consigna: estirar de 10° a 40° en 1 s, quedarse 0.5 s y volver a plegar en 1 s.  N = 0 (pata en el aire).
Kp = 30; Kd = 0.5;                                   % ganancias del servo [N m/rad], [N m s/rad]
N  = 0;                                              % 0 en el aire; N_parado con el robot apoyado
th_ref = @(t) p.theta_min + (p.theta_max - p.theta_min)*(min(max(t, 0), 1) - min(max(t - 1.5, 0), 1));
tau_servo = @(t, x) min(max(Kp*(th_ref(t) - x(1)) - Kd*x(2), -p.tau_max), p.tau_max);
[t, x] = ode45(@(t, x) f_pata(t, x, tau_servo(t, x), N, p), [0 3], [p.theta_min; 0]);
tau = arrayfun(@(k) tau_servo(t(k), x(k,:)'), 1:numel(t))';
Ts  = terminos(x(:,1)', p);

figure('Name', 'Trayectoria de la pata')
subplot(3,1,1); plot(t, rad2deg(x(:,1)), t, rad2deg(th_ref(t)), '--', 'LineWidth', 1.5); grid on
ylabel('\theta [°]'); legend('\theta', '\theta_{ref}', 'Location', 'best'); title('Estirar y plegar la pata en el aire')
subplot(3,1,2); plot(t, tau/0.0981, 'LineWidth', 1.5); grid on; yline([-1 1]*p.tau_max/0.0981, '--')
ylabel('\tau servo [kg cm]')
subplot(3,1,3); plot(t, Ts.yP*1e3, 'LineWidth', 1.5); grid on; ylabel('y_P [mm]'); xlabel('t [s]')

%% Funciones ================================================================================
function T = terminos(th, p)
% Ecuaciones (1) a (18) del PDF para un vector fila de theta [rad]. Todo en SI, ángulos en rad.
%   T.BD T.beta1 T.beta2 T.beta T.alfa1 T.alfa2 T.psi      geometría
%   T.dbeta T.dpsi          beta'(theta), psi'(theta)
%   T.Ieq T.dIeq            inercia equivalente y su derivada (diferencias centradas)
%   T.V T.dV                energía potencial y su derivada
%   T.yP T.dyP T.xP         posición del eje de la rueda respecto de A y dyP/dtheta
%   T.A T.B T.C T.D T.P     puntos (2 x n), para dibujar
  th = th(:)';
  [Ieq, T] = nucleo(th, p);
  h = 1e-6;
  T.Ieq  = Ieq;
  T.dIeq = (nucleo(th + h, p) - nucleo(th - h, p))/(2*h);
end

function [Ieq, T] = nucleo(th, p)
  AB = p.AB; AD = p.AD; BC = p.BC; CD = p.CD; DP = p.DP; a45 = p.a45; dl = p.delta;
  % --- geometría: ley del coseno (1)-(3) y giro del acoplador (4)
  BD = sqrt(AB^2 + AD^2 - 2*AB*AD*cos(th + a45));
  b1 = acos((AB^2 + BD.^2 - AD^2)./(2*AB*BD));  b2 = acos((BC^2 + BD.^2 - CD^2)./(2*BC*BD));
  a1 = acos((AD^2 + BD.^2 - AB^2)./(2*AD*BD));  a2 = acos((CD^2 + BD.^2 - BC^2)./(2*CD*BD));
  beta = b1 + b2;  psi = pi - th - a1 - a2;
  % --- posiciones (5)-(6)
  A = zeros(2, numel(th));  B = AB*[cos(a45); sin(a45)]*ones(1, numel(th));
  D = AD*[cos(th); -sin(th)];
  C = D + CD*[cos(psi); sin(psi)];  P = D + DP*[cos(psi + dl); sin(psi + dl)];
  GAD = p.AG*[cos(th); -sin(th)];   GBC = B + p.BG*[cos(5*pi/4 + beta); sin(5*pi/4 + beta)];
  GCDP = D + p.dG*[cos(psi + p.epsG); sin(psi + p.epsG)];
  % --- derivadas (7)-(10): d(ángulo)/dBD = -cot(ángulo del otro extremo)/BD
  dBD   = AB*AD*sin(th + a45)./BD;
  dbeta = -(cot(a1) + cot(a2)).*dBD./BD;
  dpsi  = -1 + (cot(b1) + cot(b2)).*dBD./BD;
  % --- velocidad al cuadrado de un punto del acoplador por unidad de theta'^2 (12)
  vQ2 = @(d, e) AD^2 + d^2*dpsi.^2 - 2*AD*d*dpsi.*cos(th + psi + e);
  % --- energía cinética: inercia equivalente (15)
  I_AD = p.IG_AD + p.m_AD*p.AG^2;   I_BC = p.IG_BC + p.m_BC*p.BG^2;    % respecto de los pivotes A y B
  Ieq = I_AD + I_BC*dbeta.^2 + p.IG_CDP*dpsi.^2 + p.m_CDP*vQ2(p.dG, p.epsG) + p.m_P*vQ2(DP, dl);
  % --- energía potencial (16)-(18)
  V   = p.g*(p.m_AD*GAD(2,:) + p.m_BC*GBC(2,:) + p.m_CDP*GCDP(2,:) + p.m_P*P(2,:));
  dyP = -AD*cos(th) + DP*cos(psi + dl).*dpsi;
  dV  = p.g*(-p.m_AD*p.AG*cos(th) - p.m_BC*p.BG*cos(a45 + beta).*dbeta ...
             + p.m_CDP*(-AD*cos(th) + p.dG*cos(psi + p.epsG).*dpsi) + p.m_P*dyP);
  T = struct('theta', th, 'BD', BD, 'beta1', b1, 'beta2', b2, 'beta', beta, 'alfa1', a1, 'alfa2', a2, 'psi', psi, ...
             'dbeta', dbeta, 'dpsi', dpsi, 'V', V, 'dV', dV, 'xP', P(1,:), 'yP', P(2,:), 'dyP', dyP, ...
             'A', A, 'B', B, 'C', C, 'D', D, 'P', P);
end

function dx = f_pata(~, x, tau, N, p)
% Ecuación de movimiento en forma de estado (23): x = [theta; theta'], tau = par del servo, N = reacción del piso.
  T  = terminos(x(1), p);
  dx = [x(2); (tau - p.b*x(2) + N*T.dyP - 0.5*T.dIeq*x(2)^2 - T.dV)/T.Ieq];
end
