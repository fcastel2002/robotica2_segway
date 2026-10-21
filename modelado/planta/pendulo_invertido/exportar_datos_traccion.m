%EXPORTAR_DATOS_TRACCION  Calcula cuánto agarre (mu) pide el control y lo deja en un .txt.
%
%   Escribe datos_traccion.txt en esta misma carpeta, que es lo que dibuja fig_traccion.py.
%   Así los números de la figura salen del modelo y no están copiados a mano.
%
%   Qué calcula, para cada inclinación inicial:
%     - el par pico que pide el LQR al recuperarse desde ahí (lazo cerrado, modelo lineal)
%     - el mu mínimo que hace falta para que la rueda entregue ese par sin patinar,
%       usando limite_de_traccion (F = c1*tau, NO mu*N*r)
%   Y, aparte, la aceleración disponible en función de mu, que es lo que se pierde
%   cuando el piso resbala.
%
%   Correr:  exportar_datos_traccion   (después:  python fig_traccion.py)
%
%   Ver también LIMITE_DE_TRACCION, DISENAR_LQR_PENDULO_INVERTIDO.

aqui = fileparts(mfilename('fullpath'));
addpath(fullfile(aqui, '..', '..', 'parametros'), fullfile(aqui, '..', '..', 'cinematica'), aqui);

o = parametros_fisicos('segunda_iteracion');
p = parametros_pendulo_invertido(o, 25);
[p, m] = motor_pendulo_invertido(p, o);
C = disenar_lqr_pendulo_invertido(p);
[~, ~, c1] = limite_de_traccion(p);
A = C.A;  B = C.B;  K = C.K;

ang = 0.25:0.25:12;                       % inclinación inicial [grados]
mu_nec = zeros(size(ang));
for i = 1:numel(ang)
  [~, xx] = ode45(@(t, x) (A - B*K)*x, [0 4], [0; 0; deg2rad(ang(i)); 0]);
  U = -(K*xx').';
  [~, k] = max(abs(U));                   % el instante en que más par pide
  U_k = max(min(U(k), m.V_bat), -m.V_bat);            % la batería satura
  w_rel = xx(k, 2)/p.r - xx(k, 4);                    % velocidad relativa en el eje
  tau = abs(m.beta_V*U_k - m.b_m*w_rel);              % par que realmente entrega
  mu_nec(i) = abs(c1)*tau/(p.m_total*p.g);
end
a_motor = abs(c1)*m.tau_bloqueo/p.m_total;            % aceleración máxima de los motores a fondo

f = fopen(fullfile(aqui, 'datos_traccion.txt'), 'w');
fprintf(f, '# Generado por exportar_datos_traccion.m. NO editar a mano.\n');
fprintf(f, '# robot_kg %.4f\n', p.m_total);
fprintf(f, '# l_m %.4f\n', p.l);
fprintf(f, '# c1 %.4f\n', c1);
fprintf(f, '# tau_bloqueo_Nm %.4f\n', m.tau_bloqueo);
fprintf(f, '# V_bat %.2f\n', m.V_bat);
fprintf(f, '# mu_supuesto %.2f\n', p.mu);
fprintf(f, '# a_motor_ms2 %.3f\n', a_motor);
fprintf(f, '# mu_tope %.4f\n', max(mu_nec));
fprintf(f, '# r_rueda_m %.4f\n', p.r);
fprintf(f, 'ang_deg mu_necesario\n');
fprintf(f, '%.4f %.6f\n', [ang; mu_nec]);
fclose(f);

fprintf('datos_traccion.txt escrito.\n');
fprintf('  robot %.0f g | mu necesario: %.2f a 2 grados, %.2f a 5, %.2f a 10\n', ...
        1e3*p.m_total, mu_nec(ang == 2), mu_nec(ang == 5), mu_nec(ang == 10));
fprintf('  arriba de mu = %.2f el limite deja de ser el piso y pasa a ser la bateria\n', max(mu_nec));
fprintf('  aceleracion maxima de los motores: %.2f m/s2\n', a_motor);
