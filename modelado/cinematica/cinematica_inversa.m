function theta = cinematica_inversa(yP, G)
%CINEMATICA_INVERSA  Angulo del servo para una altura dada del eje de rueda.
%   theta = cinematica_inversa(yP)      yP en mm respecto de A (negativo: la rueda esta debajo de A);
%   theta = cinematica_inversa(yP, G)   escalar o vector. Devuelve theta en GRADOS.
%
%   No hay formula cerrada (hay que resolver y_P(theta) = yP, con y_P trascendente en theta), pero en
%   el recorrido del servo y_P(theta) es monotona creciente, asi que se resuelve por biseccion.
%   Fuera del recorrido devuelve NaN.
  if nargin < 2 || isempty(G), G = parametros_geometria(); end
  theta = nan(size(yP));
  for k = 1:numel(yP)
    lo = G.theta(1); hi = G.theta(2);
    ylo = altura(lo, G); yhi = altura(hi, G);
    if yP(k) < min(ylo, yhi) || yP(k) > max(ylo, yhi), continue; end
    for it = 1:60
      mid = (lo + hi)/2; ym = altura(mid, G);
      if (ym - yP(k))*(ylo - yP(k)) <= 0, hi = mid; else, lo = mid; ylo = ym; end
    end
    theta(k) = (lo + hi)/2;
  end
end

function y = altura(theta, G)
  K = cinematica_directa(theta, G); y = K.P(2);
end
