function K = cinematica_pata(P, theta)
%CINEMATICA_PATA  Posicion de todos los puntos de la pata para un angulo de motor.
%
%   K = cinematica_pata(P, theta)   theta en RADIANES, escalar o vector.
%
%   Devuelve, con una fila por valor de theta (todo en SI, metros):
%     K.A K.B K.C K.D K.P   coordenadas [x y], relativas al pivote A
%     K.mu                  angulo de transmision en C            [rad]
%     K.ok                  true si el mecanismo cierra en todos los theta
%     K.valido              vector logico por cada theta
%
%   Convencion de angulos:  theta se mide desde el eje +x, sentido antihorario,
%   y define la direccion de la manivela A->D.
%   El punto P (eje de rueda) se obtiene girando la direccion D->C un angulo
%   delta y avanzando DP.  delta = 164 grados en la geometria del grupo.

  theta = theta(:);
  n = numel(theta);
  K.A = repmat(P.A, n, 1);
  K.B = repmat(P.B, n, 1);
  K.C = nan(n,2); K.D = nan(n,2); K.P = nan(n,2);
  K.mu = nan(n,1);
  K.valido = false(n,1);

  for i = 1:n
    D = P.A + P.AD * [cos(theta(i)) sin(theta(i))];
    v = P.B - D;
    d = hypot(v(1), v(2));
    if d > P.BC + P.CD - 1e-12 || d < abs(P.BC - P.CD) + 1e-12 || d < 1e-12
      continue;                                  % el cuatro barras no cierra
    end
    a  = (P.CD^2 - P.BC^2 + d^2) / (2*d);
    h2 = P.CD^2 - a^2;
    if h2 <= 0, continue; end
    h  = sqrt(h2);
    M2 = D + a * v / d;
    C  = [M2(1) + P.rama*h*v(2)/d, M2(2) - P.rama*h*v(1)/d];

    angDC = atan2(C(2)-D(2), C(1)-D(1));
    Pw = D + P.DP * [cos(angDC + P.delta) sin(angDC + P.delta)];

    % angulo de transmision en C, entre el acoplador (C->D) y el balancin (C->B)
    u1 = D - C;  u2 = P.B - C;
    c  = (u1*u2') / (norm(u1)*norm(u2));
    mu = acos(max(min(c,1),-1));
    K.mu(i) = min(mu, pi - mu);

    K.C(i,:) = C; K.D(i,:) = D; K.P(i,:) = Pw;
    K.valido(i) = true;
  end
  K.theta = theta;
  K.ok = all(K.valido);
end
