function X0 = estado_inicial(P, phi0, l0)
%ESTADO_INICIAL  Estado de 20 elementos con el robot apoyado en el piso plano, en reposo.
%   X0 = estado_inicial(P)             vertical, pata en l0
%   X0 = estado_inicial(P, phi0, l0)   inclinado phi0 [rad], pata en l0 [m]
  if nargin < 2 || isempty(phi0), phi0 = 0; end
  if nargin < 3 || isempty(l0), l0 = P.din.l0; end
  X0 = zeros(20,1);
  X0(2) = P.Rw - P.m.total*P.g/(2*P.contacto.k);   % hundimiento estatico del neumatico
  X0(3) = phi0; X0(4) = l0; X0(19) = l0;
end
