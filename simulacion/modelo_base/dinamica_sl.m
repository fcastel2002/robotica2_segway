function [qdd, N, f_roce, desliza, theta_m, G] = dinamica_sl(q, qd, u, pv)
%DINAMICA_SL  Dinamica de 3 GDL, version numerica pura (apta para Simulink).
%   Misma fisica que dinamica_robot, sin structs: se puede compilar en un
%   bloque MATLAB Function y tambien correr desde ode45.
%
%   q  = [x; phi; l]    qd = [dx; dphi; dl]    u = [tau_w; tau_s]
%   pv = empaquetar(P)
%#codegen
  m_b=pv(1); m_w=pv(2); J_b=pv(3); J_w=pv(4); R=pv(5); g=pv(6);
  ga=pv(7); gb=pv(8); l_min=pv(9); l_max=pv(10);
  b_w=pv(11); b_p=pv(12); b_l=pv(13); mu=pv(17);
  tha=pv(20); thb=pv(21);

  phi = q(2);  l = q(3);  if l < 1e-3, l = 1e-3; end
  dx = qd(1);  dphi = qd(2);  dl = qd(3);
  c = cos(phi); sn = sin(phi);

  G = ga + gb*l;                       % dl/dtheta del cuatro barras
  if abs(G) < 1e-4, G = 1e-4; end

  Mt = m_w + J_w/R^2 + m_b;
  MM = [ Mt,       m_b*l*c,        m_b*sn ;
         m_b*l*c,  m_b*l^2 + J_b,  0      ;
         m_b*sn,   0,              m_b    ];
  CC = [ m_b*(2*dl*dphi*c - l*dphi^2*sn) ;
         2*m_b*l*dl*dphi                 ;
        -m_b*l*dphi^2                    ];
  GG = [ 0 ; -m_b*g*l*sn ; m_b*g*c ];
  DD = [ b_w/R^2*dx ; b_p*dphi ; b_l*dl ];

  f_tope = 0;                          % topes de carrera de la pata
  if l < l_min, f_tope = 2e4*(l_min - l) - 60*dl; end
  if l > l_max, f_tope = 2e4*(l_max - l) - 60*dl; end

  QQ = [ u(1)/R ; -u(1) ; u(2)/G + f_tope ];
  qdd = MM \ (QQ - CC - GG - DD);

  N = (m_w + m_b)*g + m_b*(qdd(3)*c - l*qdd(2)*sn - l*dphi^2*c - 2*dl*dphi*sn);
  f_roce = u(1)/R;
  if N < 1e-6, N = 1e-6; end
  desliza = double(abs(f_roce) > mu*N);
  theta_m = tha + thb*l;
end
