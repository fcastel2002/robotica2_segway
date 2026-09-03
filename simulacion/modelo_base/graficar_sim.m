function graficar_sim(S)
%GRAFICAR_SIM  Cuatro paneles con lo que importa de una simulacion.
  P = S.P; r2d = 180/pi;
  figure('Color','w','Name',['Simulacion: ' S.esc],'Position',[80 80 1000 720]);

  subplot(2,2,1);
  plot(S.t, S.X(:,2)*r2d, 'LineWidth', 1.8); grid on;
  ylabel('\phi [deg]'); xlabel('t [s]'); title('Inclinacion del cuerpo');

  subplot(2,2,2);
  plot(S.t, S.altura*1e3, 'LineWidth', 1.8); hold on;
  plot(S.t, S.ref(:,2)*1e3 + (P.Rw - P.din.r_com(2) + P.chasis.yc + P.chasis.alto/2)*1e3, ...
       '--', 'LineWidth', 1.2);
  grid on; ylabel('altura del chasis [mm]'); xlabel('t [s]');
  legend('real','consigna','Location','best'); title('Altura');

  subplot(2,2,3);
  plot(S.t, S.u(:,1), 'LineWidth', 1.8); hold on;
  plot(S.t, [1 -1].*P.act.tau_w_max.*ones(numel(S.t),2), 'r:', 'LineWidth', 1);
  grid on; ylabel('\tau_{rueda} [N.m]'); xlabel('t [s]'); title('Par de ruedas (las dos)');

  subplot(2,2,4);
  plot(S.t, S.u(:,2), 'LineWidth', 1.8); hold on;
  plot(S.t, [1 -1].*P.act.tau_s_max.*ones(numel(S.t),2), 'r:', 'LineWidth', 1);
  grid on; ylabel('\tau_{hombro} [N.m]'); xlabel('t [s]'); title('Par de hombros (los dos)');
end
