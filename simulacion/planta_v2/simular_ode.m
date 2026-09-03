function S = simular_ode(P, C, E)
%SIMULAR_ODE  Corre un escenario en MATLAB puro: planta continua (ode15s) entre muestras del control.
%   Misma estructura que el Simulink: sensores + retardo de E.n_delay muestras + control a Ts (ZOH).
%   Corta la corrida si |phi| supera 90 grados (el robot ya se cayo).
  par = parametros_simulink(P, C);
  Ts = P.sens.Ts; nd = E.n_delay; tf = E.tf;
  rng(E.semilla);
  nk = floor(tf/Ts);
  ref_f  = @(tt) interp1(E.ref.time,  E.ref.signals.values,  tt, 'previous', 'extrap');
  pert_f = @(tt) interp1(E.pert.time, E.pert.signals.values, tt, 'previous', 'extrap');
  T = zeros(nk+1,1); XX = zeros(nk+1,20); U = zeros(nk+1,3); Y = zeros(nk+1,18);
  MEAS = zeros(nk+1,5); EST = zeros(nk+1,7); REF = zeros(nk+1,2);
  opts = odeset('RelTol',1e-5,'AbsTol',1e-7,'MaxStep',1e-3);
  X = E.X0; t = 0; u = [0; 0; interp_lin(P.tab.l, P.tab.th, E.X0(4))];
  d0 = pert_f(0)';
  m0 = medida_inicial(X, d0(3), par);
  buf = repmat({m0}, nd + 1, 1);
  robot_controlador(m0, ref_f(0)', par, 1);
  kfin = nk + 1;
  for k = 1:nk+1
    d = pert_f(t)'; r = ref_f(t)';
    [~, y] = robot_planta(X, u, d, par);
    meas = robot_sensores(X, y, randn(3,1), par);
    buf = [buf(2:end); {meas}]; meas_d = buf{1};
    [u, est] = robot_controlador(meas_d, r, par, 0);
    T(k)=t; XX(k,:)=X'; U(k,:)=u'; Y(k,:)=y'; MEAS(k,:)=meas_d'; EST(k,:)=est'; REF(k,:)=r';
    if k == nk+1 || abs(X(3)) > pi/2, kfin = k; break; end
    [~, Xo] = ode15s(@(tt, Xi) robot_planta(Xi, u, pert_f(tt)', par), [t t+Ts], X, opts);
    X = Xo(end,:)'; t = t + Ts;
  end
  T = T(1:kfin); XX = XX(1:kfin,:); U = U(1:kfin,:); Y = Y(1:kfin,:); MEAS = MEAS(1:kfin,:); EST = EST(1:kfin,:); REF = REF(1:kfin,:);
  S = struct('t',T,'X',XX,'u',U,'y',Y,'meas',MEAS,'est',EST,'ref',REF,'E',E,'P',P,'C',C,'motor','ode15s');
  S = resumen_corrida(S);
end
