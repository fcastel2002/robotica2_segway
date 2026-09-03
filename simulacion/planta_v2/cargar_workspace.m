function cargar_workspace(P, C, E)
%CARGAR_WORKSPACE  Deja en el workspace base todo lo que lee robot_segway.slx, con nombres legibles.
  par = parametros_simulink(P, C);
  medidas0 = medida_inicial(E.X0, E.pert.signals.values(1,3), par);
  retardo = max(E.n_delay, 1);                               % >= 1 para que el lazo no sea algebraico
  assignin('base', 'par', par);
  assignin('base', 'estados_iniciales', E.X0);
  assignin('base', 'medidas_iniciales', repmat(medidas0, [1 1 retardo]));
  assignin('base', 'Ts', P.sens.Ts);
  assignin('base', 'tiempo_final', E.tf);
  assignin('base', 'retardo_muestras', retardo);
  assignin('base', 'semilla', E.semilla);
  assignin('base', 'referencias_ts', E.ref);
  assignin('base', 'perturbaciones_ts', E.pert);
  assignin('base', 'P', P); assignin('base', 'C', C); assignin('base', 'E', E);
end
