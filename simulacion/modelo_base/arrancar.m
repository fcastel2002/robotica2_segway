% ARRANCAR  Punto de entrada del modelo dinamico.
%   1. arma los parametros a partir de la escala
%   2. disena el LQR
%   3. simula en MATLAB (rapido, para ajustar)
%   4. arma el Simulink
clear; clc; close all;

% ================== LO QUE SE TOCA ==================
s   = 80;      % escala: bancada |AB| [mm]
Dw  = 80;      % diametro de rueda [mm]
% pesos del LQR de equilibrio
w.q_x = 1; w.q_phi = 60; w.q_dx = 1; w.q_dphi = 2; w.r = 12;
% ====================================================

P = params_robot('s', s, 'Dw', Dw);
C = disenar_lqr(P, w);
mostrar_params(P);
verificar_geometria(P);
mostrar_dinamica(P, C);

% --- barrido de escenarios en MATLAB puro ---
escenarios = {'equilibrio','agachar','empujon','avanzar'};
fprintf('=========== SIMULACIONES ===========\n');
fprintf('%-12s %9s %9s %7s %9s %7s %8s\n', ...
        'escenario','phi max','tau_w','uso','tau_s','uso','patina');
S = cell(size(escenarios));
for i = 1:numel(escenarios)
  S{i} = sim_robot(P, C, escenarios{i}, 5);
  r = S{i}.resumen;
  fprintf('%-12s %7.1f d %9.3f %6.0f%% %9.3f %6.0f%% %8d\n', escenarios{i}, ...
      r.phi_max_deg, r.tau_w_max, 100*r.uso_rueda, r.tau_s_max, 100*r.uso_hombro, r.patino);
end
fprintf('\n');
try, graficar_sim(S{1}); catch, disp('(sin graficos en este entorno)'); end

% --- Simulink ---
% construir_simulink(P, C);      % descomentar cuando quieras armar el modelo
