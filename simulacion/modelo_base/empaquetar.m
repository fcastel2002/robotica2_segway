function pv = empaquetar(P, C)
%EMPAQUETAR  Aplana los parametros en un vector de doubles.
%   Simulink no puede meter structs con handles ni cells dentro de un bloque
%   MATLAB Function, asi que la planta y el control trabajan con este vector.
%   Es tambien la unica fuente de verdad: dinamica_robot y controlador lo usan.
%
%   pv = empaquetar(P)        sin control (solo planta)
%   pv = empaquetar(P, C)     con las ganancias del LQR
  if nargin < 2, C = []; end
  pv = zeros(31,1);
  pv(1)=P.din.m_b;  pv(2)=P.din.m_w;  pv(3)=P.din.J_b;  pv(4)=P.din.J_w;
  pv(5)=P.Rw;       pv(6)=P.g;
  pv(7)=P.din.Gfit(1); pv(8)=P.din.Gfit(2);
  pv(9)=P.din.l_min;   pv(10)=P.din.l_max;
  pv(11)=P.b.rueda; pv(12)=P.b.pitch; pv(13)=P.b.pata;
  pv(14)=P.act.tau_w_max; pv(15)=P.act.tau_s_max; pv(16)=P.act.kp_servo;
  pv(17)=P.mu_piso;
  pv(18)=P.din.r_com(1); pv(19)=P.din.r_com(2);
  pv(20)=P.din.THfit(1); pv(21)=P.din.THfit(2);
  if ~isempty(C)
    pv(22:25)=C.Kfit(1,:).'; pv(26:29)=C.Kfit(2,:).';
    pv(30)=C.l_lim(1);       pv(31)=C.l_lim(2);
  end
end
