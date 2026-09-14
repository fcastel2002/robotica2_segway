function R = terminos_dinamica_pata(theta, p, caso)
%TERMINOS_DINAMICA_PATA Términos del modelo reducido de una pata.
%   R = terminos_dinamica_pata(theta,p,caso), con theta en radianes y
%   caso igual a 'banco', 'parado' o 'aire'. Acepta theta escalar o vector.
  theta = theta(:)';
  h = p.paso_derivada;
  [Ieq, dV, R] = nucleo(theta, p, caso);
  [Ip, dVp] = nucleo(theta + h, p, caso);
  [Im, dVm] = nucleo(theta - h, p, caso);
  R.Ieq = Ieq;
  R.dIeq = (Ip - Im)/(2*h);
  R.dV = dV;
  R.d2V = (dVp - dVm)/(2*h);
  R.cCoM = p.n_patas*R.dV/(p.g*p.m_total);
  R.dcCoM = p.n_patas*R.d2V/(p.g*p.m_total);
end

function [Ieq, dV, R] = nucleo(theta, p, caso)
  AB = p.AB; AD = p.AD; BC = p.BC; CD = p.CD; DP = p.DP;
  BD = sqrt(AB^2 + AD^2 - 2*AB*AD*cos(theta + p.a45));
  cb1 = (AB^2 + BD.^2 - AD^2)./(2*AB*BD);
  cb2 = (BC^2 + BD.^2 - CD^2)./(2*BC*BD);
  ca1 = (AD^2 + BD.^2 - AB^2)./(2*AD*BD);
  ca2 = (CD^2 + BD.^2 - BC^2)./(2*CD*BD);
  cierre = max([abs(cb1(:)); abs(cb2(:)); abs(ca1(:)); abs(ca2(:))]);
  if cierre > 1 + 1e-10
    error('terminos_dinamica_pata:Cierre', 'El cuatro barras no cierra para theta solicitado.');
  end
  cb1 = max(min(cb1, 1), -1); cb2 = max(min(cb2, 1), -1);
  ca1 = max(min(ca1, 1), -1); ca2 = max(min(ca2, 1), -1);
  b1 = acos(cb1); b2 = acos(cb2); a1 = acos(ca1); a2 = acos(ca2);
  beta = b1 + b2;
  psi = pi - theta - a1 - a2;

  n = numel(theta);
  A = zeros(2, n);
  B = [AB*cos(p.a45); AB*sin(p.a45)].*ones(1, n);
  D = AD*[cos(theta); -sin(theta)];
  C = D + CD*[cos(psi); sin(psi)];
  P = D + DP*[cos(psi + p.delta); sin(psi + p.delta)];
  GAD = p.AG*[cos(theta); -sin(theta)];
  GBC = B + p.BG*[cos(5*pi/4 + beta); sin(5*pi/4 + beta)];
  GCDP = D + p.dG*[cos(psi + p.epsG); sin(psi + p.epsG)];

  dBD = AB*AD*sin(theta + p.a45)./BD;
  dbeta = -(cot(a1) + cot(a2)).*dBD./BD;
  dpsi = -1 + (cot(b1) + cot(b2)).*dBD./BD;
  girar = @(r) [-r(2,:); r(1,:)];
  cD = -girar(D);
  cGAD = -girar(GAD);
  cGBC = dbeta.*girar(GBC - B);
  cGCDP = cD + dpsi.*girar(GCDP - D);
  cP = cD + dpsi.*girar(P - D);

  switch lower(char(caso))
    case 'banco'
      u = zeros(2, n);
    case 'parado'
      u = -cP;
    case 'aire'
      S = p.m_AD*cGAD + p.m_BC*cGBC + p.m_CDP*cGCDP + p.m_P*cP;
      u = -p.n_patas*S/p.m_total;
    otherwise
      error('terminos_dinamica_pata:Caso', ...
            'Caso "%s" desconocido; usar banco, parado o aire.', char(caso));
  end

  norma2 = @(v) sum(v.^2, 1);
  Ieq = p.IG_AD + p.IG_BC*dbeta.^2 + p.IG_CDP*dpsi.^2 ...
      + (p.m_cabina/p.n_patas)*norma2(u) ...
      + p.m_AD*norma2(u + cGAD) + p.m_BC*norma2(u + cGBC) ...
      + p.m_CDP*norma2(u + cGCDP) + p.m_P*norma2(u + cP);
  dV = p.g*((p.m_cabina/p.n_patas)*u(2,:) ...
       + p.m_AD*(u(2,:) + cGAD(2,:)) + p.m_BC*(u(2,:) + cGBC(2,:)) ...
       + p.m_CDP*(u(2,:) + cGCDP(2,:)) + p.m_P*(u(2,:) + cP(2,:)));

  R = struct('theta', theta, 'caso', lower(char(caso)), 'BD', BD, ...
    'beta1', b1, 'beta2', b2, 'beta', beta, 'alfa1', a1, 'alfa2', a2, ...
    'psi', psi, 'dBD', dBD, 'dbeta', dbeta, 'dpsi', dpsi, 'u', u, ...
    'wP', u(2,:) + cP(2,:), 'dyP', cP(2,:), 'xP', P(1,:), 'yP', P(2,:), ...
    'A', A, 'B', B, 'C', C, 'D', D, 'P', P, 'GAD', GAD, 'GBC', GBC, ...
    'GCDP', GCDP);
end
