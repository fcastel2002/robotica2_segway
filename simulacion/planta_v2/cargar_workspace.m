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
  % condiciones iniciales de los Unit Delay del controlador por bloques (robot_segway_bloques)
  assignin('base', 'encoders_iniciales', medidas0(4:5));
  assignin('base', 'inclinacion_inicial_est', atan2(-medidas0(2), medidas0(3)));
  l_ref0 = max(min(E.ref.signals.values(1,2), par.pata.l_max), par.pata.l_min);
  assignin('base', 'angulo_servo_inicial', interp_lin(par.pata.tabla_l, par.pata.tabla_theta, l_ref0));
  assignin('base', 'P', P); assignin('base', 'C', C); assignin('base', 'E', E);
end
