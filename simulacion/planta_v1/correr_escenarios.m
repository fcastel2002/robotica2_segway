function R = correr_escenarios(variante, nombres, motor, w)
%CORRER_ESCENARIOS  Corre escenarios (Simulink u ode15s) y arma la tabla resumen.
%   R = correr_escenarios('cad')                                  todos, en Simulink
%   R = correr_escenarios('corregido', {'equilibrio_8'}, 'ode')
%   R = correr_escenarios('cad', [], 'simulink', struct('q_x',10)) con otros pesos del LQR
%   Guarda resultados/resultados_<variante>_<motor>.mat y .md junto a este archivo.
  if nargin < 1 || isempty(variante), variante = 'cad'; end
  if nargin < 2 || isempty(nombres), nombres = escenarios_v1('lista'); end
  if nargin < 3 || isempty(motor), motor = 'simulink'; end
  if nargin < 4, w = struct(); end
  P0 = parametros_v1(variante); C = disenar_control_v1(P0, w);
  n = numel(nombres);
  R.variante = variante; R.motor = motor; R.S = cell(n,1); R.C = C;
  esc = strings(n,1); phimax = zeros(n,1); phifin = zeros(n,1); cayo = false(n,1); tas = zeros(n,1);
  usoV = zeros(n,1); usoS = zeros(n,1); desl = zeros(n,1); ipico = zeros(n,1); mah = zeros(n,1); xfin = zeros(n,1);
  for i = 1:n
    E = escenarios_v1(nombres{i}, P0);
    P = P0; if ~isempty(E.overrides), P = parametros_v1(variante, E.overrides{:}); end
    fprintf('[%s/%s] %-18s ', variante, motor, nombres{i}); tic;
    switch motor
      case 'ode', S = simular_ode_v1(P, C, E);
      otherwise,  S = simular_slx_v1(P, C, E);
    end
    r = S.resumen; R.S{i} = S;
    esc(i) = nombres{i}; phimax(i) = r.phi_max_deg; phifin(i) = r.phi_fin_deg; cayo(i) = r.cayo; tas(i) = r.t_asent;
    usoV(i) = 100*r.uso_V; usoS(i) = 100*r.uso_servo; desl(i) = r.pct_desliza; ipico(i) = r.i_pico; mah(i) = r.mAh; xfin(i) = r.x_fin;
    fprintf('%5.1fs  phi max %5.1f deg  %s\n', toc, r.phi_max_deg, ternario(r.cayo, 'SE CAE', 'ok'));
  end
  R.T = table(esc, phimax, phifin, cayo, tas, usoV, usoS, desl, ipico, mah, xfin, 'VariableNames', ...
      {'escenario','phi_max_deg','phi_fin_deg','se_cae','t_asent_s','uso_V_pct','uso_servo_pct','desliza_pct','I_pico_A','mAh','x_fin_m'});
  lineas = "| escenario | phi max [deg] | phi final [deg] | se cae | t asent [s] | uso V [%] | uso servo [%] | desliza [%] | I pico [A] | mAh | x final [m] |";
  lineas(2) = "|---|---:|---:|:--:|---:|---:|---:|---:|---:|---:|---:|";
  for i = 1:n
    lineas(end+1) = sprintf('| %s | %.1f | %.1f | %s | %.2f | %.0f | %.0f | %.0f | %.2f | %.1f | %.3f |', esc(i), phimax(i), phifin(i), ...
        ternario(cayo(i), 'SI', 'no'), tas(i), usoV(i), usoS(i), desl(i), ipico(i), mah(i), xfin(i)); %#ok<AGROW>
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
