function C = disenar_lqr_robot(P, w)
%DISENAR_LQR_ROBOT  LQR del lazo de equilibrio sobre el modelo reducido, programado por l.
%   C = disenar_lqr_robot(P)
%   C = disenar_lqr_robot(P, struct('q_x',3,'q_phi',60,'q_dx',2,'q_dphi',2,'r',12))
%   C.Kfit (2x4): K(l) = Kfit(1,:) + Kfit(2,:)*l ; C.l_lim rango del ajuste.
%   Pesos por defecto segun la variante (barrido sobre equilibrio_8, ver README de planta_v1):
%   cad (N = 100) necesita ganancias mucho mayores por la inercia reflejada del rotor.
  if nargin < 2, w = struct(); end
  d = @(c, v) get_def(w, c, v);
  if strcmp(P.variante, 'cad')
    Q = diag([d('q_x',40) d('q_phi',100) d('q_dx',20) d('q_dphi',3)]); Rr = d('r',2);
  else
    Q = diag([d('q_x',3) d('q_phi',60) d('q_dx',2) d('q_dphi',2)]); Rr = d('r',12);
  end
  nl = 9;
  C.l = linspace(P.din.l_min*1.02, P.din.l_max*0.98, nl)';
  C.K = zeros(nl,4); C.polos_la = zeros(nl,1); C.polos_lc = cell(nl,1);
  for i = 1:nl
    [A, B] = modelo_lineal_robot(P, C.l(i));
    C.K(i,:) = lqr(A, B, Q, Rr);
    C.polos_la(i) = max(real(eig(A)));
    C.polos_lc{i} = eig(A - B*C.K(i,:));
  end
  Aj = [ones(nl,1) C.l];
  C.Kfit = Aj \ C.K;
  C.Kerr = max(max(abs(Aj*C.Kfit - C.K)));
  C.l_lim = [C.l(1) C.l(end)]; C.Q = Q; C.R = Rr;
  C.Kf = @(l) C.Kfit(1,:) + C.Kfit(2,:)*l;
end
function v = get_def(s, c, v)
  if isfield(s, c), v = s.(c); end
end
