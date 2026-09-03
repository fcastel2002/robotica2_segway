function derivar_dinamica_v1()
%DERIVAR_DINAMICA_V1  Deduce por Lagrange las ecuaciones del cuerpo y genera dinamica_v1_gen.m.
%   q = [x; phi; l]. Piso con pendiente alpha: x a lo largo del piso, phi desde la normal al piso.
%   Cuerpo: masa m_b e inercia J_b en el CoM, a distancia l del eje de rueda; m_w en el eje.
%   Se corre una sola vez; el archivo generado se versiona.
  syms x phi l dx dphi dl m_b m_w J_b g real
  alpha = sym('alpha', 'real');            % 'alpha' es tambien una funcion de MATLAB: se crea con sym
  q = [x; phi; l]; dq = [dx; dphi; dl];
  r_w = [x; 0];
  r_b = [x + l*sin(phi); l*cos(phi)];
  v_b = jacobian(r_b, q)*dq;
  T = m_w*dx^2/2 + m_b*(v_b.'*v_b)/2 + J_b*dphi^2/2;
  gvec = g*[-sin(alpha); -cos(alpha)];
  V = -m_b*(gvec.'*r_b) - m_w*(gvec.'*r_w);
  M = simplify(hessian(T, dq));
  n = 3; C = sym(zeros(n,1));
  for i = 1:n
    for j = 1:n
      for k = 1:n
        C(i) = C(i) + (diff(M(i,j),q(k)) + diff(M(i,k),q(j)) - diff(M(j,k),q(i)))/2*dq(j)*dq(k);
      end
    end
  end
  C = simplify(C);
  Gv = simplify(jacobian(V, q).');
  aqui = fileparts(mfilename('fullpath'));
  matlabFunction(M, C, Gv, 'File', fullfile(aqui, 'dinamica_v1_gen.m'), ...
     'Vars', {phi, l, dphi, dl, m_b, m_w, J_b, g, alpha}, 'Outputs', {'M','C','Gv'}, 'Optimize', false);
  fprintf('dinamica_v1_gen.m generado en %s\n', aqui);
end
