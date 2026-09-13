function S = simular_slx(P, C, E, mdl)
%SIMULAR_SLX  Corre un escenario en robot_segway.slx y devuelve la misma estructura que simular_ode.
%   S = simular_slx(P, C, E)                          modelo con MATLAB Functions (robot_segway)
%   S = simular_slx(P, C, E, 'robot_segway_bloques')  modelo solo con bloques nativos
%   Si el modelo no esta cargado lo carga del disco, y si no existe lo construye.
  if nargin < 4 || isempty(mdl), mdl = 'robot_segway'; end
  aqui = fileparts(mfilename('fullpath'));
  if ~bdIsLoaded(mdl)
    if isfile(fullfile(aqui, [mdl '.slx'])), load_system(fullfile(aqui, [mdl '.slx']));
    elseif strcmp(mdl, 'robot_segway_bloques'), construir_robot_bloques(P, C, E);
    else, construir_robot_slx(P, C, E, mdl); end
  end
  cargar_workspace(P, C, E);
  set_param(mdl, 'ReturnWorkspaceOutputs', 'on');
  out = sim(mdl);
  Ts = P.sens.Ts; t = (0:Ts:E.tf)';
  if any(strcmp(out.who, 'estados_vec')), XX = a_matriz(out.estados_vec, t); Y = a_matriz(out.salidas_vec, t);
  else, XX = a_matriz(out.estados, t); Y = a_matriz(out.salidas, t); end      % modelo por bloques: buses
  U = a_matriz(out.comandos, t); ES = a_matriz(out.estimaciones, t); MM = a_matriz(out.medidas, t);
  ref_f = interp1(E.ref.time, E.ref.signals.values, t, 'previous', 'extrap');
  S = struct('t',t,'X',XX,'u',U,'y',Y,'meas',MM,'est',ES,'ref',ref_f,'E',E,'P',P,'C',C,'motor','simulink');
  S = resumen_corrida(S);
end
function M = a_matriz(obj, t)
% Convierte lo que devuelve To Workspace (timeseries, estructura con tiempo, o bus = estructura de
% timeseries) en una matriz n x k remuestreada a los instantes t (retencion de orden cero).
  if isa(obj, 'timeseries')
    d = obj.Data; if ndims(d) == 3, d = reshape(d, size(d,1)*size(d,2), [])'; end
    M = interp1(obj.Time, d, t, 'previous', 'extrap');
  elseif isstruct(obj) && isfield(obj, 'signals')
    d = obj.signals.values; if ndims(d) == 3, d = reshape(d, size(d,1)*size(d,2), [])'; end
    M = interp1(obj.time, d, t, 'previous', 'extrap');
  elseif isstruct(obj)
    f = fieldnames(obj); M = zeros(numel(t), numel(f));
    for k = 1:numel(f), M(:,k) = interp1(obj.(f{k}).Time, squeeze(obj.(f{k}).Data), t, 'previous', 'extrap'); end
  else
    error('simular_slx: tipo de registro no reconocido (%s)', class(obj));
  end
end
