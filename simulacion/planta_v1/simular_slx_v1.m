function S = simular_slx_v1(P, C, E, mdl)
%SIMULAR_SLX_V1  Corre un escenario en planta_segway_v1.slx y devuelve la misma estructura que simular_ode_v1.
%   Si el modelo no esta cargado lo carga del disco, y si no existe lo construye.
  if nargin < 4 || isempty(mdl), mdl = 'planta_segway_v1'; end
  aqui = fileparts(mfilename('fullpath'));
  if ~bdIsLoaded(mdl)
    if isfile(fullfile(aqui, [mdl '.slx'])), load_system(fullfile(aqui, [mdl '.slx'])); else, construir_planta(P, C, E, mdl); end
  end
  cargar_workspace_v1(P, C, E);
  if P.motor.gear_rigido, set_param(mdl, 'MaxStep','2e-3', 'RelTol','1e-5'); else, set_param(mdl, 'MaxStep','5e-4', 'RelTol','1e-4'); end
  set_param(mdl, 'ReturnWorkspaceOutputs','on');
  out = sim(mdl);
  Ts = P.sens.Ts; t = (0:Ts:E.tf)';
  rem = @(s) interp1(s.time, aplanar(s.signals.values), t, 'previous', 'extrap');
  XX = rem(out.Xout); Y = rem(out.Yout); U = rem(out.Uout); ES = rem(out.Eout); MM = rem(out.Mout);
  ref_f = interp1(E.ref.time, E.ref.signals.values, t, 'previous', 'extrap');
  S = struct('t',t,'X',XX,'u',U,'y',Y,'meas',MM,'est',ES,'ref',ref_f,'E',E,'P',P,'C',C,'motor','simulink');
  S = resumen_v1(S);
end
function v = aplanar(v)
% To Workspace guarda las senales vectoriales (k x 1) como k x 1 x n; se pasan a n x k.
  if ndims(v) == 3, v = reshape(v, size(v,1)*size(v,2), [])'; end
end
