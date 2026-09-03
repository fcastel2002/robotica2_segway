% ARRANCAR_V1  Punto de entrada de la planta v1.
%   1. parametros de la variante   2. LQR   3. un escenario en ode15s con graficos
%   4. modelo Simulink             5. barrido de escenarios en Simulink
clear; clc; close all;
aqui = fileparts(mfilename('fullpath'));
addpath(aqui); addpath(fullfile(aqui, '..', 'modelo_base'));

% ================== LO QUE SE TOCA ==================
variante = 'corregido';      % 'cad' (tal como esta el CAD) o 'corregido'
escenario = 'empujon_6N';
w = struct();                % pesos del LQR; vacio = los de disenar_control_v1
% ====================================================

P = parametros_v1(variante);
C = disenar_control_v1(P, w);
fprintf('\n%s: m_b = %.3f kg, m_w = %.3f kg, J_b = %.2e, l = %.0f..%.0f mm, G = %.3f m/rad\n', ...
    P.variante, P.din.m_b, P.din.m_w, P.din.J_b, P.din.l_min*1e3, P.din.l_max*1e3, P.din.G);
fprintf('motor: %s | polo inestable en l0: %+.2f rad/s | K(l0) = [%s]\n', P.motor.nombre, ...
    C.polos_la(5), num2str(C.Kf(P.din.l0), '%8.3f'));

E = escenarios_v1(escenario, P);
S = simular_ode_v1(P, C, E);
disp(S.resumen); graficar_v1(S);

construir_planta(P, C, E);
R = correr_escenarios(variante);              % todos los escenarios en Simulink
disp(R.tabla);
