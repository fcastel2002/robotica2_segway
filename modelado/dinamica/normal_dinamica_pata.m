function N = normal_dinamica_pata(theta, dtheta, ddtheta, p)
%NORMAL_DINAMICA_PATA Normal estimada por rueda en el caso apoyado.
  T = terminos_dinamica_pata(theta, p, 'parado');
  N = (p.m_total/p.n_patas).*(p.g + T.cCoM.*ddtheta + T.dcCoM.*dtheta.^2);
end
