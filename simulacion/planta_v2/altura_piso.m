function yg = altura_piso(x, piso)
%ALTURA_PISO  Altura del piso (descanso) debajo de la coordenada x, para graficar y para medir alturas.
%   Vectorizada en x. Coincide con el perfil que usa perfil_piso (sin las contrahuellas).
  k = floor((x - piso.x0)/piso.ancho) + 1;
  k = min(max(k, 0), piso.n);
  yg = -k*piso.alto;
end
