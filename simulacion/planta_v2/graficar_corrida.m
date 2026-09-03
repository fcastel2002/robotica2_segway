function graficar_corrida(S)
%GRAFICAR_CORRIDA  Seis paneles con lo que importa de una corrida (salida de simular_ode o simular_slx).
  P = S.P; r2d = 180/pi; t = S.t; mm = 1e3; peso = P.m.total*P.g;
  figure('Color','w','Name',sprintf('%s (%s, %s)', S.E.nombre, P.variante, S.motor), 'Position',[60 60 1200 780]);
  subplot(3,2,1); plot(t, S.X(:,3)*r2d, 'LineWidth',1.6); hold on; plot(t, S.est(:,1)*r2d, '--'); grid on;
  ylabel('inclinacion \phi [deg]'); legend('real','estimada','Location','best'); title('Inclinacion del cuerpo');
  subplot(3,2,2); plot(t, S.X(:,2)*mm, 'LineWidth',1.6); hold on; plot(t, S.piso_bajo_rueda*mm, 'k-', 'LineWidth',1.2);
  plot(t, (S.piso_bajo_rueda + P.Rw)*mm, 'k:'); grid on; ylabel('[mm]'); legend('eje de rueda','piso bajo la rueda','piso + R_w','Location','best'); title('Altura del eje y perfil del piso');
  subplot(3,2,3); plot(t, S.u(:,1:2), 'LineWidth',1.3); hold on; plot(t, [1 -1].*P.bat.V.*ones(numel(t),2), 'r:'); grid on;
  ylabel('tension [V]'); title('Tension de cada motor');
  subplot(3,2,4); plot(t, S.X(:,1), 'LineWidth',1.6); hold on; plot(t, S.ref(:,1), '--'); plot(t, S.est(:,2), ':'); grid on;
  ylabel('x [m]'); legend('real','consigna','estimada','Location','best'); title('Posicion de la base');
  subplot(3,2,5); yyaxis left; plot(t, S.y(:,5)/peso, 'LineWidth',1.3); ylabel('normal / peso');
  yyaxis right; plot(t, S.y(:,11), 'LineWidth',1.2); ylabel('par servo [N m]'); grid on; xlabel('t [s]'); title('Fuerza de piso y par de servo');
  subplot(3,2,6); plot(t, S.X(:,4)*mm, 'LineWidth',1.6); hold on; plot(t, S.ref(:,2)*mm, '--');
  if P.flexor.activo, plot(t, S.X(:,19)*mm, ':', 'LineWidth',1.2); legend('l real','l consigna','l del mecanismo','Location','best'); else, legend('l real','l consigna','Location','best'); end
  grid on; ylabel('largo de pata l [mm]'); xlabel('t [s]'); title('Largo del pendulo');
end
