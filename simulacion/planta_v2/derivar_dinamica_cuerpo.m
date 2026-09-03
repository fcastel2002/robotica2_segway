function derivar_dinamica_cuerpo()
%DERIVAR_DINAMICA_CUERPO  Deduce por Lagrange las ecuaciones del cuerpo con el eje libre en vertical
%   y genera dinamica_cuerpo_gen.m.  q = [x; y; phi; l]: posicion del eje de rueda (x, y), angulo del
%   cuerpo desde la normal al piso y largo del pendulo. Piso con pendiente alpha (gravedad rotada).
%   Se corre una sola vez; el archivo generado se versiona.
  syms x y phi l dx dy dphi dl m_b m_w J_b g real
  alpha = sym('alpha', 'real');
  q = [x; y; phi; l]; dq = [dx; dy; dphi; dl];
  r_w = [x; y];
  r_b = [x + l*sin(phi); y + l*cos(phi)];
  v_w = jacobian(r_w, q)*dq; v_b = jacobian(r_b, q)*dq;
  T = m_w*(v_w.'*v_w)/2 + m_b*(v_b.'*v_b)/2 + J_b*dphi^2/2;
  gvec = g*[-sin(alpha); -cos(alpha)];
  V = -m_b*(gvec.'*r_b) - m_w*(gvec.'*r_w);
  M = simplify(hessian(T, dq));
  n = 4; C = sym(zeros(n,1));
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
  matlabFunction(M, C, Gv, 'File', fullfile(aqui, 'dinamica_cuerpo_gen.m'), ...
     'Vars', {phi, l, dphi, dl, m_b, m_w, J_b, g, alpha}, 'Outputs', {'M','C','Gv'}, 'Optimize', false);
  fprintf('dinamica_cuerpo_gen.m generado en %s\n', aqui);
end
