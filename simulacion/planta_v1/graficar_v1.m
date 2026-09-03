function graficar_v1(S)
%GRAFICAR_V1  Seis paneles con lo que importa de una corrida (salida de simular_ode_v1 o simular_slx_v1).
  P = S.P; r2d = 180/pi; t = S.t;
  figure('Color','w','Name',sprintf('%s (%s, %s)', S.E.nombre, P.variante, S.motor), 'Position',[60 60 1150 760]);
  subplot(3,2,1); plot(t, S.X(:,2)*r2d, 'LineWidth',1.6); hold on; plot(t, S.est(:,1)*r2d, '--'); grid on;
  ylabel('\phi [deg]'); legend('real','estimado','Location','best'); title('Inclinacion');
  subplot(3,2,2); plot(t, S.altura*1e3, 'LineWidth',1.6); hold on;
  plot(t, (P.Rw + S.ref(:,2) - P.din.r_com(2) + P.din.h_tapa_sobre_A)*1e3, '--'); grid on;
  ylabel('tope de la tapa [mm]'); legend('real','consigna','Location','best'); title('Altura');
  subplot(3,2,3); plot(t, S.u(:,1:2), 'LineWidth',1.4); hold on; plot(t, [1 -1].*P.bat.V.*ones(numel(t),2), 'r:'); grid on;
  ylabel('V motor [V]'); title('Tension de motores');
  subplot(3,2,4); plot(t, S.y(:,12:13), 'LineWidth',1.4); grid on; ylabel('I [A]'); title('Corriente de motores');
  subplot(3,2,5); plot(t, S.X(:,1), 'LineWidth',1.6); hold on; plot(t, S.ref(:,1), '--'); plot(t, S.est(:,2), ':'); grid on;
  ylabel('x [m]'); xlabel('t [s]'); legend('real','consigna','estimado','Location','best'); title('Posicion');
  subplot(3,2,6); yyaxis left; plot(t, S.y(:,10), 'LineWidth',1.4); ylabel('\tau servo [N m]');
  yyaxis right; plot(t, S.y(:,7), 'LineWidth',1); ylabel('desliza'); grid on; xlabel('t [s]'); title('Servo y deslizamiento');
end
