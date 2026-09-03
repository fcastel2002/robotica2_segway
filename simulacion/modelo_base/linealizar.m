function L = linealizar(P, l0)
%LINEALIZAR  Modelo lineal alrededor del equilibrio vertical con la pata en l0.
%
%   L = linealizar(P)        usa l0 = P.din.l0
%   L = linealizar(P, l0)
%
%   L.A6 L.B6   modelo completo, X = [x; phi; l; dx; dphi; dl], u = [tau_w; tau_s]
%   L.A  L.B    modelo de equilibrio,  X = [x; phi; dx; dphi],  u = tau_w
%   L.tau_s0    par de hombro que sostiene el peso en esa pose  [N.m]
%   L.polos     polos del lazo abierto (equilibrio)
%
%   Se lineariza numericamente por diferencias centradas: no hay algebra a mano
%   que se pueda equivocar, y sigue exactamente al modelo no lineal.

  if nargin < 2 || isempty(l0), l0 = P.din.l0; end
  l0 = min(max(l0, P.din.l_min), P.din.l_max);

  % par de hombro en equilibrio: sostiene el peso del cuerpo
  G0 = interp1(P.din.map.l, P.din.map.G, l0, 'linear', 'extrap');
  tau_s0 = P.din.m_b * P.g * G0;
  X0 = [0; 0; l0; 0; 0; 0];  U0 = [0; tau_s0];

  f = @(X,U) [X(4:6); dinamica_robot(X(1:3), X(4:6), U, P)];

  n = 6; m = 2;
  A6 = zeros(n); B6 = zeros(n,m);
  hX = 1e-6; hU = 1e-6;
  for i = 1:n
    e = zeros(n,1); e(i) = hX;
    A6(:,i) = (f(X0+e,U0) - f(X0-e,U0)) / (2*hX);
  end
  for j = 1:m
    e = zeros(m,1); e(j) = hU;
    B6(:,j) = (f(X0,U0+e) - f(X0,U0-e)) / (2*hU);
  end
  L.A6 = A6; L.B6 = B6; L.X0 = X0; L.U0 = U0;
  L.tau_s0 = tau_s0; L.G0 = G0; L.l0 = l0;

  % submodelo de equilibrio: [x phi dx dphi] con tau_w
  idx = [1 2 4 5];
  L.A = A6(idx, idx);  L.B = B6(idx, 1);
  L.C = eye(4);  L.D = zeros(4,1);
  L.estados = {'x','phi','dx','dphi'};
  L.polos = eig(L.A);
  L.controlable = rank([L.B, L.A*L.B, L.A^2*L.B, L.A^3*L.B]) == 4;
end
