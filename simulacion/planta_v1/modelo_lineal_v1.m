function [A, B, M2] = modelo_lineal_v1(P, l0)
%MODELO_LINEAL_V1  Modelo lineal [x phi dx dphi] con entrada tau_w (par total de rueda).
%   Rodadura sin deslizar, reductor rigido (rotor reflejado), pata fija en l0, piso horizontal.
%   M2 es la matriz de masa reducida; M2(1,1) incluye la inercia del rotor reflejada al piso.
  m_b=P.din.m_b; m_w=P.din.m_w; J_b=P.din.J_b; g=P.g; R=P.Rw;
  J_eq = P.din.J_w + P.motor.N^2*P.motor.J_r;
  Mt = m_w + m_b + 2*J_eq/R^2;
  M2 = [Mt, m_b*l0; m_b*l0, m_b*l0^2 + J_b];
  Kq = [0 0; 0 -m_b*g*l0];
  D  = diag([2*P.rueda.b_w/R^2, P.cuerpo.b_pitch]);
  A = [zeros(2) eye(2); -M2\Kq, -M2\D];
  B = [0; 0; M2\[1/R; -1]];
end
