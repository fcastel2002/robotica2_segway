function S = simular_ode_v1(P, C, E)
%SIMULAR_ODE_V1  Corre un escenario en MATLAB puro: planta continua (ode15s) entre muestras del control.
%   Misma estructura que el Simulink: sensores + retardo de E.n_delay muestras + control a Ts (ZOH).
%   Corta la corrida si |phi| supera 90 grados (el robot ya se cayo).
  pv = empaquetar_v1(P, C);
  Ts = P.sens.Ts; nd = E.n_delay; tf = E.tf;
  rng(E.semilla);
  nk = floor(tf/Ts);
  ref_f  = @(tt) interp1(E.ref.time,  E.ref.signals.values,  tt, 'previous', 'extrap');
  pert_f = @(tt) interp1(E.pert.time, E.pert.signals.values, tt, 'previous', 'extrap');
  T = zeros(nk+1,1); XX = zeros(nk+1,16); U = zeros(nk+1,3); Y = zeros(nk+1,16);
  MEAS = zeros(nk+1,5); EST = zeros(nk+1,6); REF = zeros(nk+1,2);
  opts = odeset('RelTol',1e-5,'AbsTol',1e-7,'MaxStep',Ts);
  X = E.X0; t = 0; u = [0; 0; interp_lin(P.tab.l, P.tab.th, E.X0(3))];
  d0 = pert_f(0)';
  m0 = medida_inicial_v1(X, d0(3), pv);          % medida en reposo: inicializa el filtro y la cola del retardo
  buf = repmat({m0}, nd + 1, 1);
  control_v1(m0, ref_f(0)', pv, 1);
  kfin = nk + 1;
  for k = 1:nk+1
    d = pert_f(t)'; r = ref_f(t)';
    [~, y] = planta_sl(X, u, d, pv);
    meas = sensores_sl(X, y, randn(3,1), pv);
    buf = [buf(2:end); {meas}]; meas_d = buf{1};
    [u, est] = control_v1(meas_d, r, pv, 0);
    T(k)=t; XX(k,:)=X'; U(k,:)=u'; Y(k,:)=y'; MEAS(k,:)=meas_d'; EST(k,:)=est'; REF(k,:)=r';
    if k == nk+1 || abs(X(2)) > pi/2, kfin = k; break; end
    [~, Xo] = ode15s(@(tt, Xi) planta_sl(Xi, u, pert_f(tt)', pv), [t t+Ts], X, opts);
    X = Xo(end,:)'; t = t + Ts;
  end
  T = T(1:kfin); XX = XX(1:kfin,:); U = U(1:kfin,:); Y = Y(1:kfin,:); MEAS = MEAS(1:kfin,:); EST = EST(1:kfin,:); REF = REF(1:kfin,:);
  S = struct('t',T,'X',XX,'u',U,'y',Y,'meas',MEAS,'est',EST,'ref',REF,'E',E,'P',P,'C',C,'motor','ode15s');
  S = resumen_v1(S);
end
