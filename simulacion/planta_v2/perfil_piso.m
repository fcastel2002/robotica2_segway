function [delta, nx, ny, px, py] = perfil_piso(xc, yc, R, piso)
%PERFIL_PISO  Contacto de una rueda (centro xc, yc; radio R) con el piso de escalones descendentes.
%   piso.x0    donde termina el primer descanso (alli baja el primer escalon)
%   piso.alto  alto de cada escalon      piso.ancho  ancho de cada descanso     piso.n  cantidad (0 = plano)
%   El piso es: altura 0 para x < x0; -k*alto en el descanso k (k = 1..n); el ultimo descanso sigue
%   hasta el infinito. Devuelve la penetracion delta = R - (distancia al punto mas cercano del piso),
%   la normal (nx, ny) que apunta del piso hacia el centro y el punto de contacto (px, py).
%   delta > 0 significa contacto.
%#codegen
  n = round(piso.n); x0 = piso.x0; H = piso.alto; W = piso.ancho;
  mejor = 1e9; px = xc; py = 0;
  % descansos k = 0..n: altura -k*H, x entre xa y xb
  for k = 0:n
    hk = -k*H;
    if k == 0, xa = -1e6; else, xa = x0 + (k-1)*W; end
    if k == n, xb = 1e6;  else, xb = x0 + k*W;     end
    xq = min(max(xc, xa), xb);
    dq = hypot(xc - xq, yc - hk);
    if dq < mejor, mejor = dq; px = xq; py = hk; end
  end
  % contrahuellas k = 1..n: en x = x0 + (k-1)*W, y entre -k*H y -(k-1)*H
  for k = 1:n
    xk = x0 + (k-1)*W;
    yq = min(max(yc, -k*H), -(k-1)*H);
    dq = hypot(xc - xk, yc - yq);
    if dq < mejor, mejor = dq; px = xk; py = yq; end
  end
  delta = R - mejor;
  if mejor > 1e-9
    nx = (xc - px)/mejor; ny = (yc - py)/mejor;
  else
    nx = 0; ny = 1;
  end
end
