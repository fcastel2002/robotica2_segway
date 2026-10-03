function L = linealizar_pendulo_invertido(p)
%LINEALIZAR_PENDULO_INVERTIDO Taylor alrededor de phi=0, velocidades=0, tau=0.
%   Orden de estado: [x; velocidad_x; phi; velocidad_phi].
%   Entrada: par TOTAL en las dos ruedas. No requiere Control System Toolbox.

    %% Modelo de segundo orden M0*q_ddot + D*q_dot = gravedad + H*tau.
    M0 = [p.a, -p.h; -p.h, p.j];
    D = [p.b_x + p.b_eje / p.r^2, p.b_eje / p.r; ...
         p.b_eje / p.r, p.b_eje + p.b_phi];
    H = [-1 / p.r; -1];
    respuesta_gravedad = M0 \ [0; p.k];
    respuesta_velocidad = -(M0 \ D);
    respuesta_par = M0 \ H;

    %% Reordenar las dos aceleraciones dentro del vector de cuatro estados.
    L.A = zeros(4, 4);
    L.A(1, 2) = 1;
    L.A(3, 4) = 1;
    L.A([2, 4], 3) = respuesta_gravedad;
    L.A([2, 4], [2, 4]) = respuesta_velocidad;
    L.B = [0; respuesta_par(1); 0; respuesta_par(2)];
    L.M0 = M0;
    L.D = D;
    L.autovalores = eig(L.A);

    % Controlabilidad local para una entrada comun a los dos motores.
    L.controlabilidad = [L.B, L.A * L.B, L.A^2 * L.B, L.A^3 * L.B];
    L.rango_controlabilidad = rank(L.controlabilidad);
    L.lambda_inestable_sin_friccion = sqrt(p.a * p.k / (p.a * p.j - p.h^2));
end
