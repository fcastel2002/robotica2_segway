function R = correr_escenarios_robot(variante, nombres, motor, w)
%CORRER_ESCENARIOS_ROBOT  Corre escenarios (Simulink u ode15s) y arma la tabla resumen.
%   R = correr_escenarios_robot('corregido')                       todos, en Simulink
%   R = correr_escenarios_robot('cad', {'escalera','escalera_flexor'}, 'ode')
%   Guarda resultados/resultados_<variante>_<motor>.mat y .md junto a este archivo.
  if nargin < 1 || isempty(variante), variante = 'corregido'; end
  if nargin < 2 || isempty(nombres), nombres = escenarios_robot('lista'); end
  if nargin < 3 || isempty(motor), motor = 'simulink'; end
  if nargin < 4, w = struct(); end
  P0 = parametros_robot(variante); C = disenar_lqr_robot(P0, w);
  n = numel(nombres);
  R.variante = variante; R.motor = motor; R.S = cell(n,1); R.C = C;
  T = table('Size', [n 14], 'VariableTypes', [{'string'} repmat({'double'}, 1, 13)], 'VariableNames', ...
      {'escenario','phi_max_deg','phi_fin_deg','se_cae','t_asent_s','uso_V_pct','uso_servo_pct','desliza_pct','I_pico_A','N_max_pesos','a_cuerpo_g','t_vuelo_s','escalones','x_fin_m'});
  for i = 1:n
    E = escenarios_robot(nombres{i}, P0);
    P = P0; if ~isempty(E.overrides), P = parametros_robot(variante, E.overrides{:}); E = escenarios_robot(nombres{i}, P); end
    fprintf('[%s/%s] %-18s ', variante, motor, nombres{i}); tic;
    switch motor
      case 'ode', S = simular_ode(P, C, E);
      otherwise,  S = simular_slx(P, C, E);
    end
    r = S.resumen; R.S{i} = S;
    T(i,:) = {string(nombres{i}), r.phi_max_deg, r.phi_fin_deg, double(r.cayo), r.t_asent, 100*r.uso_V, 100*r.uso_servo, r.pct_desliza, r.i_pico, r.N_max_g, r.a_cuerpo_max_g, r.t_vuelo, r.escalones_bajados, r.x_fin};
    fprintf('%5.1fs  phi max %5.1f deg  %s\n', toc, r.phi_max_deg, ternario(r.cayo, 'SE CAE', 'ok'));
  end
  R.T = T;
  lineas = "| escenario | phi max [deg] | phi final [deg] | se cae | t asent [s] | uso V [%] | uso servo [%] | desliza [%] | I pico [A] | N max [pesos] | a cuerpo [g] | vuelo [s] | escalones | x final [m] |";
  lineas(2) = "|---|---:|---:|:--:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|";
  for i = 1:n
    lineas(end+1) = sprintf('| %s | %.1f | %.1f | %s | %.2f | %.0f | %.0f | %.0f | %.2f | %.1f | %.1f | %.2f | %d | %.2f |', nombres{i}, T.phi_max_deg(i), T.phi_fin_deg(i), ...
        ternario(T.se_cae(i) > 0.5, 'SI', 'no'), T.t_asent_s(i), T.uso_V_pct(i), T.uso_servo_pct(i), T.desliza_pct(i), T.I_pico_A(i), T.N_max_pesos(i), T.a_cuerpo_g(i), T.t_vuelo_s(i), T.escalones(i), T.x_fin_m(i)); %#ok<AGROW>
  end
  R.tabla = char(strjoin(lineas, newline));
  carpeta = fullfile(fileparts(mfilename('fullpath')), 'resultados');
  if ~isfolder(carpeta), mkdir(carpeta); end
  save(fullfile(carpeta, sprintf('resultados_%s_%s.mat', variante, motor)), 'R', '-v7.3');
  fid = fopen(fullfile(carpeta, sprintf('resultados_%s_%s.md', variante, motor)), 'w');
  fprintf(fid, '# Resultados %s (%s)\n\nMotor: %s. Pesos LQR: Q = diag(%s), R = %g. Generado %s.\n\n%s\n', variante, motor, ...
      P0.motor.nombre, num2str(diag(C.Q)', '%g '), C.R, datestr(now), R.tabla);
  fclose(fid);
  disp(R.T);
end
function y = ternario(c, a, b)
  if c, y = a; else, y = b; end
end
