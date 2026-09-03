function cargar_workspace_v1(P, C, E)
%CARGAR_WORKSPACE_V1  Deja en el workspace base todo lo que lee planta_segway_v1.slx.
%   n_delay se fuerza a >= 1 para que el lazo sensores -> controlador -> planta no sea algebraico.
  pv = empaquetar_v1(P, C);
  meas0 = medida_inicial_v1(E.X0, E.pert.signals.values(1,3), pv);   % condicion inicial del retardo = medida en reposo
  meas0 = repmat(meas0, [1 1 max(E.n_delay, 1)]);                     % el bloque Delay pide [5 x 1 x n_delay] para una senal 5x1
  assignin('base','meas0',meas0);
  assignin('base','pv',pv); assignin('base','X0',E.X0); assignin('base','Ts',P.sens.Ts);
  assignin('base','Tfin',E.tf); assignin('base','n_delay',max(E.n_delay,1)); assignin('base','semilla',E.semilla);
  assignin('base','ref_ts',E.ref); assignin('base','pert_ts',E.pert);
  assignin('base','P',P); assignin('base','C',C); assignin('base','E',E);
end
