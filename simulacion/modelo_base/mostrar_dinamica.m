function mostrar_dinamica(P, C)
%MOSTRAR_DINAMICA  Resumen del modelo dinamico y del control.
  r2d = 180/pi;
  L = linealizar(P);
  fprintf('\n=========== MODELO DINAMICO ===========\n');
  fprintf('  masa suspendida (cuerpo)   m_b = %.3f kg\n', P.din.m_b);
  fprintf('  masa no suspendida (ruedas) m_w = %.3f kg\n', P.din.m_w);
  fprintf('  inercia del cuerpo         J_b = %.2e kg.m2\n', P.din.J_b);
  fprintf('  inercia de rueda           J_w = %.2e kg.m2\n', P.din.J_w);
  fprintf('  CoM del cuerpo respecto de A : (%+.1f , %+.1f) mm\n', P.din.r_com*1e3);
  fprintf('  largo del pendulo l : %.0f a %.0f mm  (l0 = %.0f)\n', ...
          P.din.l_min*1e3, P.din.l_max*1e3, P.din.l0*1e3);
  fprintf('  ganancia G = dl/dtheta : %.3f m/rad  (ajuste lineal, error %.1f %%)\n', ...
          P.din.G, 100*P.din.Gerr/P.din.G);
  fprintf('  par de hombro en equilibrio : %.3f N.m = %.1f kg.cm  (%.1f por servo)\n', ...
          L.tau_s0, L.tau_s0*10.1972, L.tau_s0*10.1972/2);
  fprintf('  polo inestable : %+.2f rad/s  ->  se cae en %.0f ms\n', ...
          max(real(L.polos)), 1000/max(real(L.polos)));
  fprintf('  controlable : %d\n', L.controlable);

  fprintf('\n=========== CONTROL ===========\n');
  fprintf('  pesos LQR: Q = diag(%g %g %g %g), R = %g\n', diag(C.Q), C.R);
  K0 = C.Kfit(1,:) + C.Kfit(2,:)*P.din.l0;
  fprintf('  K en l0 = [%.3f  %.3f  %.3f  %.3f]   (x  phi  dx  dphi)\n', K0);
  mx = -inf; for i=1:numel(C.polos), mx = max(mx, max(real(C.polos{i}))); end
  fprintf('  peor polo de lazo cerrado en toda la carrera : %+.2f  ->  %s\n', ...
          mx, ternario(mx<0,'ESTABLE','INESTABLE'));
  fprintf('  par de rueda para corregir 5 deg : %.3f N.m de %.2f disponibles\n', ...
          abs(K0*[0;5/r2d;0;0]), P.act.tau_w_max);
  fprintf('\n');
end
function y = ternario(c,a,b), if c, y=a; else, y=b; end, end
