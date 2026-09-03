% ARRANCAR  Punto de entrada de la planta v2 (escalones, flexor, Simulink legible).
%   1. parametros de la variante   2. LQR   3. un escenario en ode15s con graficos
%   4. modelo Simulink robot_segway.slx   5. barrido de escenarios en Simulink
clear; clc; close all;
aqui = fileparts(mfilename('fullpath'));
addpath(aqui); addpath(fullfile(aqui, '..', 'modelo_base'));

% ================== LO QUE SE TOCA ==================
variante  = 'corregido';     % 'cad' (tal como esta el CAD) o 'corregido' (bancada 100 mm a 45 grados)
escenario = 'escalera';      % ver escenarios_robot('lista'); 'escalera_flexor' agrega el flexor del docx
w = struct();                % pesos del LQR; vacio = los de disenar_lqr_robot
% ====================================================

P0 = parametros_robot(variante);
C = disenar_lqr_robot(P0, w);
E = escenarios_robot(escenario, P0);
P = P0; if ~isempty(E.overrides), P = parametros_robot(variante, E.overrides{:}); E = escenarios_robot(escenario, P); end
fprintf('\n%s: m_b = %.3f kg, m_w = %.3f kg, l = %.0f..%.0f mm, motor %s\n', P.variante, P.din.m_b, P.din.m_w, P.din.l_min*1e3, P.din.l_max*1e3, P.motor.nombre);
fprintf('escenario %s: %d escalones de %.0f x %.0f cm, flexor %d, velocidad %.2f m/s, %g s\n', escenario, P.piso.n, P.piso.alto*100, P.piso.ancho*100, P.flexor.activo, E.v_ap, E.tf);

S = simular_ode(P, C, E);
disp(S.resumen); graficar_corrida(S);

construir_robot_slx(P, C, E);            % robot_segway.slx, listo para abrir y correr
R = correr_escenarios_robot(variante);   % todos los escenarios en Simulink
disp(R.tabla);
