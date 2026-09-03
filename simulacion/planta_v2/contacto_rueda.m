function [Fx, Fy, tau_L, tau_R, N, fL, fR, desliza, delta] = contacto_rueda(x, y, dx, dy, wL, wR, par, mu)
%CONTACTO_RUEDA  Fuerzas de contacto de las dos ruedas con el piso (comparten el perfil).
%   (x, y) y (dx, dy): posicion y velocidad del eje; wL, wR: velocidad de giro de cada rueda
%   (positiva = rodar hacia adelante); mu opcional (si se omite se usa par.rueda.mu).
%   Devuelve la fuerza sobre el eje (Fx, Fy), el par sobre cada rueda, la normal total N, las fuerzas
%   tangenciales fL y fR, un indicador de deslizamiento y la penetracion delta.
%   Sin contacto (delta <= 0) todo es cero: vuelo libre.
%   Normal por rueda: N_i = max(0, k*delta + c*ddelta) (rigidez y amortiguacion del neumatico).
%   Tangencial: Coulomb suavizado, f = mu*N_i*tanh(v_s/v0) - c_v*v_s, con v_s = R*w - v_tangencial.
%#codegen
  if nargin < 8, mu = par.rueda.mu; end
  R = par.rueda.radio;
  [delta, nx, ny] = perfil_piso(x, y, R, par.piso);
  Fx = 0; Fy = 0; tau_L = 0; tau_R = 0; N = 0; fL = 0; fR = 0; desliza = 0;
  if delta <= 0, return; end
  ddelta = -(dx*nx + dy*ny);                       % velocidad con que el centro se hunde en el piso
  N_i = max(0, par.contacto.k*delta + par.contacto.c*ddelta);
  tx = ny; ty = -nx;                               % tangente "hacia adelante" (en piso plano: +x)
  vt = dx*tx + dy*ty;                              % velocidad del centro a lo largo de la tangente
  vsL = R*wL - vt; vsR = R*wR - vt;
  fL = mu*N_i*tanh(vsL/par.rueda.v0) - par.rueda.c_v*vsL;
  fR = mu*N_i*tanh(vsR/par.rueda.v0) - par.rueda.c_v*vsR;
  Fx = 2*N_i*nx + (fL + fR)*tx;
  Fy = 2*N_i*ny + (fL + fR)*ty;
  tau_L = -R*fL; tau_R = -R*fR;
  N = 2*N_i;
  desliza = double(abs(vsL) > 2*par.rueda.v0 || abs(vsR) > 2*par.rueda.v0);
end
