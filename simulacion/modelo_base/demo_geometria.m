% DEMO_GEOMETRIA  Punto de entrada: arma el robot, lo verifica y barre la escala.
%   Todo depende de un unico parametro: s = |AB|, la bancada, en mm.
clear; clc;

s = 80;                 % <<<<<<<<<<  LA ESCALA. Cambia esto y cambia todo el robot.
Dw = 80;                % <<<<<<<<<<  diametro de rueda [mm] (menu: 72 76 80 84 90 100 110)

P = params_robot('s', s, 'Dw', Dw, 'ch_largo', 150, 'ch_alto', 100, 'ch_ancho', 130);
K = barrido_pata(P);
mostrar_params(P, K);
verificar_geometria(P);

% ---- barrido de la escala ------------------------------------------------
fprintf('=========== COMO CAMBIA TODO CON LA ESCALA (rueda fija en %.0f mm) ===========\n', Dw);
fprintf('  %6s %10s %10s %9s %9s %9s %9s\n', ...
        's [mm]', 'alto [mm]', 'carrera', 'desvio', 'mu min', 'tau[kgcm]', 'huella sagital');
for si = 60:10:120
  Pi = params_robot('s', si, 'Dw', Dw, 'ch_largo', 150, 'ch_alto', 100);
  Ki = barrido_pata(Pi);
  v = Ki.valido;
  [~, Ri] = verificar_geometria(Pi, false);
  hu = ''; for r = 1:size(Ri,1)
    if strncmp(Ri{r,1},'huella',6), hu = Ri{r,3}; end
  end
  fprintf('  %6.0f %4.0f..%-5.0f %9.1f %9.2f %8.0f %9.1f   %s\n', si, ...
          min(Ki.h_total(v))*1e3, max(Ki.h_total(v))*1e3, Ki.carrera*1e3, ...
          Ki.desvio*1e3, Ki.mu_min*180/pi, Ki.tau_hombro*10.1972, hu);
end
fprintf('\n');

% ---- dibujo ---------------------------------------------------------------
figure('Color','w','Position',[100 100 900 700]);
dibujar_pata(P);
