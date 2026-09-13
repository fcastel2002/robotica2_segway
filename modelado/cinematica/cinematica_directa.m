function K = cinematica_directa(theta, G)
%CINEMATICA_DIRECTA  Posicion de los puntos de la pata (cuatro barras) para el angulo del servo.
%   K = cinematica_directa(theta)       theta en GRADOS, escalar o vector; cotas de parametros_geometria
%   K = cinematica_directa(theta, G)    G con los campos AB, beta, AD, BC, CD, DP, delta
%
%   Devuelve, con una fila por valor de theta (mm y grados):
%     K.A K.B K.C K.D K.P     coordenadas [x y] respecto de A (x positivo hacia atras, y hacia arriba)
%     K.BD                    diagonal B-D
%     K.alfa_DB               direccion de D->B desde +x
%     K.gamma                 angulo en D del triangulo B-D-C
%     K.theta_DC, K.theta_DP  direccion de D->C y de D->P desde +x
%     K.theta_BC              direccion de B->C desde +x (angulo del balancin)
%     K.mu                    angulo de transmision en C, entre C->D y C->B
%     K.valido                true si el cuatro barras cierra (|BC-CD| <= BD <= BC+CD)
%
%   Ecuaciones (ver cinematica_resumen.pdf):
%     D  = A + AD (cos theta, sin theta)
%     BD = sqrt(AB^2 + AD^2 - 2 AB AD cos(theta - beta))          alfa_DB = atan2(yB - yD, xB - xD)
%     cos gamma = (CD^2 + BD^2 - BC^2) / (2 CD BD)
%     theta_DC = alfa_DB - gamma      (C a la derecha de D->B: asi esta armado el CAD)
%     C  = D + CD (cos theta_DC, sin theta_DC)
%     theta_DP = theta_DC + delta ;   P = D + DP (cos theta_DP, sin theta_DP)
  if nargin < 2 || isempty(G), G = parametros_geometria(); end
  t = deg2rad(theta(:)); b = deg2rad(G.beta); dl = deg2rad(G.delta); n = numel(t);
  xB = G.AB*cos(b); yB = G.AB*sin(b);
  xD = G.AD*cos(t); yD = G.AD*sin(t);
  BD = sqrt(G.AB^2 + G.AD^2 - 2*G.AB*G.AD*cos(t - b));
  alfa = atan2(yB - yD, xB - xD);
  cg = (G.CD^2 + BD.^2 - G.BC^2) ./ (2*G.CD*BD);
  valido = abs(cg) <= 1;
  gamma = acos(max(min(cg, 1), -1));
  tDC = alfa - gamma;
  xC = xD + G.CD*cos(tDC); yC = yD + G.CD*sin(tDC);
  tDP = tDC + dl;
  xP = xD + G.DP*cos(tDP); yP = yD + G.DP*sin(tDP);
  tBC = atan2(yC - yB, xC - xB);
  % angulo de transmision en C (entre el acoplador C->D y el balancin C->B)
  u1 = [xD - xC, yD - yC]; u2 = [xB - xC, yB - yC];
  cm = sum(u1.*u2, 2) ./ (sqrt(sum(u1.^2, 2)) .* sqrt(sum(u2.^2, 2)));
  mu = acos(max(min(cm, 1), -1)); mu = min(mu, pi - mu);

  K.theta = theta(:);
  K.A = zeros(n, 2); K.B = repmat([xB yB], n, 1);
  K.D = [xD yD]; K.C = [xC yC]; K.P = [xP yP];
  K.BD = BD; K.alfa_DB = rad2deg(alfa); K.gamma = rad2deg(gamma);
  K.theta_DC = rad2deg(tDC); K.theta_DP = rad2deg(tDP); K.theta_BC = rad2deg(tBC); K.mu = rad2deg(mu);
  K.valido = valido;
  K.C(~valido, :) = NaN; K.P(~valido, :) = NaN;
end
