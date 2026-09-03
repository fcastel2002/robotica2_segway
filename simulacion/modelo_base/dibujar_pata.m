function dibujar_pata(P, theta, ax)
%DIBUJAR_PATA  Dibuja el robot completo con el suelo en y = 0.
%   dibujar_pata(P)              dibuja las dos poses extremas
%   dibujar_pata(P, theta)       dibuja una pose (theta en rad)
  if nargin < 3, ax = gca; end
  mm = 1e3;
  if nargin < 2 || isempty(theta), theta = P.th; end
  Kf = barrido_pata(P, 241);
  cla(ax); hold(ax,'on'); axis(ax,'equal'); grid(ax,'on');

  plot(ax, [-400 400], [0 0], 'k-', 'LineWidth', 2.5);
  plot(ax, [0 0], [-20 400], 'k--', 'LineWidth', 0.8);

  for j = 1:numel(theta)
    K = cinematica_pata(P, theta(j));
    if ~K.valido(1), continue; end
    z = P.Rw - K.P(1,2);                       % altura de A sobre el suelo
    T = @(q) [q(1)*mm, (q(2)+z)*mm];
    A=T(P.A); B=T(P.B); C=T(K.C(1,:)); D=T(K.D(1,:)); W=T(K.P(1,:));
    principal = (j == 1);
    if principal, lw = 3; al = 1; col=[0.85 0.33 0.10]; else, lw = 1.8; al = .35; col=[.45 .45 .45]; end

    % cabina y placa (relativas a A)
    cx = (P.chasis.xc)*mm + A(1); cy = (P.chasis.yc)*mm + A(2);
    rectangle(ax,'Position',[cx-P.chasis.largo*mm/2, cy-P.chasis.alto*mm/2, ...
              P.chasis.largo*mm, P.chasis.alto*mm], 'EdgeColor',[0 .45 .74], ...
              'LineWidth', 1.5*lw/3, 'LineStyle', ternario(principal,'-','--'));
    rectangle(ax,'Position',[P.placa.x(1)*mm+A(1), P.placa.y(1)*mm+A(2), ...
              P.placa.largo*mm, P.placa.alto*mm], 'EdgeColor',[.5 .5 .5], ...
              'LineWidth', 1, 'LineStyle', ':');

    for seg = {[A;D],[B;C],[C;D],[D;W]}
      s = seg{1};
      plot(ax, s(:,1), s(:,2), '-', 'Color', col, 'LineWidth', lw);
    end
    plot(ax, [A(1) B(1) C(1) D(1)], [A(2) B(2) C(2) D(2)], 'ko', ...
         'MarkerFaceColor','k','MarkerSize',4);
    t = linspace(0,2*pi,60);
    plot(ax, W(1)+P.Rw*mm*cos(t), W(2)+P.Rw*mm*sin(t), '-', 'Color', col*0+.15, 'LineWidth', lw*0.8);
    if principal
      text(ax, A(1)-6, A(2)+6, 'A'); text(ax, B(1)+4, B(2)+4, 'B');
      text(ax, C(1)+4, C(2)+4, 'C'); text(ax, D(1)+4, D(2)-8, 'D');
      text(ax, W(1)+P.Rw*mm+3, W(2), 'P');
    end
  end
  v = Kf.valido;
  title(ax, sprintf('s = %.0f mm | rueda %.0f mm | alto %.0f a %.0f mm | carrera %.0f mm | tau %.1f kg.cm', ...
        P.s*mm, P.Dw*mm, min(Kf.h_total(v))*mm, max(Kf.h_total(v))*mm, ...
        Kf.carrera*mm, Kf.tau_hombro*10.1972));
  xlabel(ax,'x [mm]'); ylabel(ax,'y [mm]'); hold(ax,'off');
end

function y = ternario(c,a,b)
  if c, y = a; else, y = b; end
end
