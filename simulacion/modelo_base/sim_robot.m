function S = sim_robot(P, C, esc, tf)
%SIM_ROBOT  Simulacion no lineal a lazo cerrado, sin Simulink.
%   Sirve para ajustar los pesos del LQR y ver si los motores alcanzan
%   ANTES de armar el diagrama.
%
%   S = sim_robot(P, C)                  escenario por defecto
%   S = sim_robot(P, C, 'agachar', 6)    ver los escenarios abajo
%
%   Escenarios:
%     'equilibrio'  arranca inclinado 8 grados y se tiene que enderezar
%     'agachar'     se agacha y se vuelve a parar
%     'empujon'     recibe un golpe lateral a los 2 s
%     'avanzar'     va a x = 0.5 m
%     'escalon'     escalon de piso de 15 mm a los 3 s

  if nargin < 3 || isempty(esc), esc = 'equilibrio'; end
  if nargin < 4 || isempty(tf), tf = 6; end

  X0 = [0; 0; P.din.l0; 0; 0; 0];
  switch lower(esc)
    case 'equilibrio', X0(2) = 8*pi/180;
    case 'empujon',    % perturbacion aplicada dentro de la ODE
    case 'avanzar',    % consigna de posicion
    case 'agachar',    % consigna de pata
    case 'escalon',    % perturbacion de piso
  end

  ref_fun = @(t) referencia(t, esc, P);
  pert_fun = @(t) perturbacion(t, esc);

  opt = odeset('RelTol',1e-5,'AbsTol',1e-7,'MaxStep',0.02);
  [T, Y] = ode45(@(t,X) campo(t, X, P, C, ref_fun, pert_fun), [0 tf], X0, opt);

  n = numel(T);
  U = zeros(n,2); REF = zeros(n,2); INFO = zeros(n,4);
  for i = 1:n
    r = ref_fun(T(i));
    [u, ~] = controlador(Y(i,:)', r, C, P);
    [~, s] = dinamica_robot(Y(i,1:3)', Y(i,4:6)', u, P);
    U(i,:) = u'; REF(i,:) = r';
    INFO(i,:) = [s.N, s.f_roce, double(s.desliza), s.theta];
  end
  S.t = T; S.X = Y; S.u = U; S.ref = REF;
  S.N = INFO(:,1); S.f_roce = INFO(:,2); S.desliza = INFO(:,3); S.theta = INFO(:,4);
  S.altura = P.Rw + (Y(:,3) - P.din.r_com(2)) + P.chasis.yc + P.chasis.alto/2;
  S.esc = esc; S.P = P;

  S.resumen = struct( ...
    'phi_max_deg',  max(abs(Y(:,2)))*180/pi, ...
    'tau_w_max',    max(abs(U(:,1))), ...
    'tau_s_max',    max(abs(U(:,2))), ...
    'uso_rueda',    max(abs(U(:,1)))/P.act.tau_w_max, ...
    'uso_hombro',   max(abs(U(:,2)))/P.act.tau_s_max, ...
    'patino',       any(INFO(:,3)>0), ...
    'x_final',      Y(end,1), ...
    'phi_final_deg',Y(end,2)*180/pi);
end

% -------------------------------------------------------------------------
function dX = campo(t, X, P, C, ref_fun, pert_fun)
  [u, ~] = controlador(X, ref_fun(t), C, P);
  qdd = dinamica_robot(X(1:3), X(4:6), u, P);
  d = pert_fun(t);                       % perturbaciones [fuerza_x ; par_pitch]
  qdd(1) = qdd(1) + d(1)/(P.din.m_b + P.din.m_w);
  qdd(2) = qdd(2) + d(2)/(P.din.m_b*X(3)^2 + P.din.J_b);
  dX = [X(4:6); qdd];
end

function r = referencia(t, esc, P)
  r = [0; P.din.l0];
  switch lower(esc)
    case 'agachar'
      if t > 1 && t <= 3,      r(2) = P.din.l_min*1.10;
      elseif t > 3,            r(2) = P.din.l_max*0.95;  end
    case 'avanzar'
      if t > 1, r(1) = 0.5; end
  end
end

function d = perturbacion(t, esc)
  d = [0; 0];
  switch lower(esc)
    case 'empujon'
      if t >= 2 && t < 2.05, d(1) = 6; end          % 6 N durante 50 ms
    case 'escalon'
      if t >= 3 && t < 3.10, d(1) = -10; end
  end
end
