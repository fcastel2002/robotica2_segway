%% DINAMICA_PATA Demostración reproducible del modelo reducido de la pata.
% La implementación reutilizable está en parametros_dinamica_pata,
% terminos_dinamica_pata y estado_dinamica_pata.
clear; clc; close all

p = parametros_dinamica_pata('corregido');
fprintf('Baseline %s: cabina %.0f g + %d patas de %.1f g = robot de %.0f g\n', ...
  p.variante, p.m_cabina*1e3, p.n_patas, ...
  (p.m_AD + p.m_BC + p.m_CDP + p.m_P)*1e3, p.m_total*1e3);

%% Tres reducciones de la dinámica
theta = linspace(p.theta_min, p.theta_max, 200);
Rb = terminos_dinamica_pata(theta, p, 'banco');
Rp = terminos_dinamica_pata(theta, p, 'parado');
Ra = terminos_dinamica_pata(theta, p, 'aire');
N_pie = p.m_total*p.g/p.n_patas;
tau_b = Rb.dV - N_pie*Rb.wP;
tau_p = Rp.dV;
tau_a = Ra.dV;

figure('Name', 'Los tres casos')
subplot(2,2,1); plot(rad2deg(theta), [Rb.Ieq; Rp.Ieq; Ra.Ieq]*1e3, 'LineWidth', 1.8); grid on
xlabel('\theta [°]'); ylabel('I_{eq} [g m^2]'); title('Inercia equivalente vista por el servo')
legend('banco', 'parado', 'aire', 'Location', 'best')
subplot(2,2,2); plot(rad2deg(theta), [tau_b; tau_p; tau_a]/0.0981, 'LineWidth', 1.8); grid on
yline(p.tau_max/0.0981, '--', 'límite nominal'); xlabel('\theta [°]'); ylabel('\tau estático [kg cm]')
legend('banco con peso', 'parado', 'aire', 'Location', 'best'); title('Par estático')
subplot(2,2,3); plot(rad2deg(theta), (p.Rw - Rp.yP)*1e3, 'LineWidth', 1.8); grid on
xlabel('\theta [°]'); ylabel('h [mm]'); title('Altura de la cabina')
subplot(2,2,4); plot(rad2deg(theta), [Rp.dbeta; Rp.dpsi], 'LineWidth', 1.8); grid on
xlabel('\theta [°]'); ylabel('[rad/rad]'); legend('\beta''', '\psi''', 'Location', 'best')

theta_tabla = deg2rad([10 25 40]);
Tb = terminos_dinamica_pata(theta_tabla, p, 'banco');
Tp = terminos_dinamica_pata(theta_tabla, p, 'parado');
Ta = terminos_dinamica_pata(theta_tabla, p, 'aire');
fprintf('\n theta   h[mm]  | Ieq [g m2]: banco  parado   aire | tau [kg cm]: banco parado aire\n');
for k = 1:numel(theta_tabla)
  fprintf('%5.0f  %6.1f  |            %6.2f  %6.2f %6.2f |          %6.2f %6.2f %5.2f\n', ...
    rad2deg(theta_tabla(k)), (p.Rw - Tp.yP(k))*1e3, Tb.Ieq(k)*1e3, ...
    Tp.Ieq(k)*1e3, Ta.Ieq(k)*1e3, ...
    (Tb.dV(k) - N_pie*Tb.wP(k))/0.0981, Tp.dV(k)/0.0981, Ta.dV(k)/0.0981);
end
fprintf('banco contra parado: diferencia máxima de par estático %.1e N m\n', max(abs(tau_b-tau_p)));
fprintf('aire: max |V''| = %.1e N m\n', max(abs(Ra.dV)));

%% Maniobra nominal: agacharse y pararse
caso = 'parado';
suave = @(s) 0.5 - 0.5*cos(pi*min(max(s, 0), 1));
theta_ref = @(t) p.theta_max + (p.theta_min-p.theta_max)*suave((t-0.2)/0.6) ...
  + (p.theta_max-p.theta_min)*suave((t-1.2)/0.6);
tau_servo = @(t,x) min(max(p.Kp*(theta_ref(t)-x(1))-p.Kd*x(2), -p.tau_max), p.tau_max);
[t, x] = ode45(@(ti,xi) estado_dinamica_pata(ti, xi, tau_servo(ti,xi), 0, p, caso), ...
  [0 2.5], [p.theta_max; 0]);
tau = arrayfun(@(k) tau_servo(t(k), x(k,:)'), 1:numel(t))';
S = terminos_dinamica_pata(x(:,1)', p, caso);
ddtheta = (tau' - p.b*x(:,2)' - 0.5*S.dIeq.*x(:,2)'.^2 - S.dV)./S.Ieq;
N_rueda = normal_dinamica_pata(x(:,1)', x(:,2)', ddtheta, p);

figure('Name', 'Agacharse y pararse')
subplot(4,1,1); plot(t, rad2deg(x(:,1)), t, rad2deg(theta_ref(t)), '--', 'LineWidth', 1.5); grid on
ylabel('\theta [°]'); legend('\theta', '\theta_{ref}', 'Location', 'best')
subplot(4,1,2); plot(t, (p.Rw-S.yP)*1e3, 'LineWidth', 1.5); grid on; ylabel('altura [mm]')
subplot(4,1,3); plot(t, tau/0.0981, 'LineWidth', 1.5); grid on; ylabel('\tau [kg cm]')
subplot(4,1,4); plot(t, N_rueda, 'LineWidth', 1.5); grid on; yline(0, '--'); ylabel('N/rueda [N]'); xlabel('t [s]')
fprintf('maniobra: par máximo %.1f kg cm de %.1f; normal entre %.2f y %.2f N\n', ...
  max(abs(tau))/0.0981, p.tau_max/0.0981, min(N_rueda), max(N_rueda));
if min(N_rueda) <= 0
  fprintf('ATENCIÓN: el supervisor debe cambiar de parado a aire.\n');
end
