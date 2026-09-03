function C = disenar_lqr(P, opts)
%DISENAR_LQR  Realimentacion de estados para el lazo de equilibrio, programada
%   por ganancias a lo largo de toda la carrera de la pata.
%
%   C = disenar_lqr(P)
%   C = disenar_lqr(P, struct('q_x',1,'q_phi',60,'q_dx',1,'q_dphi',2,'r',12))
%
%   C.l      grilla de largos de pata                 [m]
%   C.K      ganancias, una fila por largo  (4 columnas: x phi dx dphi)
%   C.Kf     funcion K = Kf(l), interpolada
%   C.info   tabla con polos de lazo cerrado y margen de par

  if nargin < 2, opts = struct(); end
  d = @(c,v) getfield_def(opts, c, v);
  Q = diag([d('q_x',1), d('q_phi',60), d('q_dx',1), d('q_dphi',2)]);
  R = d('r', 12);

  C.l = linspace(P.din.l_min*1.02, P.din.l_max*0.98, 9)';
  C.K = zeros(numel(C.l), 4);
  C.polos = cell(numel(C.l),1);
  C.tau_s0 = zeros(numel(C.l),1);
  for i = 1:numel(C.l)
    L = linealizar(P, C.l(i));
    K = lqr_local(L.A, L.B, Q, R);
    C.K(i,:) = K;
    C.polos{i} = eig(L.A - L.B*K);
    C.tau_s0(i) = L.tau_s0;
  end
  C.Q = Q; C.R = R;
  % K(l) ~ K0 + K1*l : las ganancias varian poco, un ajuste lineal alcanza y
  % es mucho mas rapido que interp1 dentro de la ODE.
  Aj = [ones(numel(C.l),1) C.l];
  C.Kfit = Aj \ C.K;                       % 2x4
  C.Kerr = max(max(abs(Aj*C.Kfit - C.K)));
  C.Kf = @(l) C.Kfit(1,:) + C.Kfit(2,:)*l;
  C.l_lim = [C.l(1) C.l(end)];
end

function K = lqr_local(A, B, Q, R)
%LQR_LOCAL  Riccati continua por el metodo del hamiltoniano.
%   No necesita Control System Toolbox: sirve igual en MATLAB base y en Octave.
  if exist('lqr','file') == 2
    try
      K = lqr(A, B, Q, R); return;
    catch
    end
  end
  n = size(A,1);
  H = [ A,            -B*(R\(B')) ;
       -Q,            -A'          ];
  [V, D] = eig(H);
  d = diag(D);
  est = real(d) < 0;                       % subespacio estable
  if sum(est) ~= n
    [~, o] = sort(real(d)); est = false(size(d)); est(o(1:n)) = true;
  end
  U = V(:, est);
  X1 = U(1:n, :);  X2 = U(n+1:end, :);
  S = real(X2 / X1);
  S = (S + S')/2;
  K = R \ (B' * S);
end

function v = getfield_def(s, c, v)
  if isfield(s, c), v = s.(c); end
end
