function y = interp_lin(xt, yt, x)
%INTERP_LIN  Interpolacion lineal con extrapolacion, apta para codegen. xt creciente.
%#codegen
  n = numel(xt);
  k = 1;
  if x >= xt(n)
    k = n - 1;
  elseif x > xt(1)
    while k < n - 1 && xt(k+1) < x
      k = k + 1;
    end
  end
  t = (x - xt(k))/(xt(k+1) - xt(k));
  y = yt(k) + t*(yt(k+1) - yt(k));
end
