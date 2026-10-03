function [derivada, R] = ecuaciones_pendulo_invertido(estado, tau_total, p)
%ECUACIONES_PENDULO_INVERTIDO Modelo NO lineal, con las patas fijas.
%   estado = [x; velocidad_x; phi; velocidad_phi], en SI.
%   tau_total: suma de los pares aplicados A LAS RUEDAS [N m].
%   phi: angulo horario de P->G desde la vertical hacia adelante [rad].
%   R entrega energias, fuerzas y balance de potencia para interpretar la ODE.

    velocidad_x = estado(2);
    phi = estado(3);
    velocidad_phi = estado(4);

    %% Matriz de masa: las aceleraciones del eje y del cuerpo estan acopladas.
    acoplamiento = p.h * cos(phi);
    matriz_masa = [p.a, acoplamiento; acoplamiento, p.j];

    %% Par motor y perdidas en el eje relativo rueda/cuerpo.
    velocidad_relativa = velocidad_x / p.r - velocidad_phi;
    par_friccion_eje = p.b_eje * velocidad_relativa;
    par_efectivo_ruedas = tau_total - par_friccion_eje;
    fuerza_arrastre = p.b_x * velocidad_x;
    par_arrastre_cuerpo = p.b_phi * velocidad_phi;

    % Fuerzas generalizadas. La reaccion del motor sobre el cuerpo es -tau.
    Q_x = par_efectivo_ruedas / p.r - fuerza_arrastre;
    Q_phi = -par_efectivo_ruedas - par_arrastre_cuerpo;

    %% Lagrange: llevar terminos centrifugo y gravitatorio al lado derecho.
    termino_centrifugo = p.h * sin(phi) * velocidad_phi^2;
    termino_gravedad = p.k * sin(phi);
    lado_derecho = [Q_x + termino_centrifugo; Q_phi + termino_gravedad];

    % Resolver el sistema 2 x 2. No se calcula inv(matriz_masa).
    aceleraciones = matriz_masa \ lado_derecho;
    aceleracion_x = aceleraciones(1);
    aceleracion_phi = aceleraciones(2);
    derivada = [velocidad_x; aceleracion_x; velocidad_phi; aceleracion_phi];

    %% Energias y potencia: E_dot debe coincidir con potencia_neta.
    velocidad_generalizada = [velocidad_x; velocidad_phi];
    R.cinetica = 0.5 * velocidad_generalizada.' * matriz_masa * velocidad_generalizada;
    R.potencial = p.k * cos(phi);   % referencia: altura del eje P
    R.energia = R.cinetica + R.potencial;
    R.potencia_motor = tau_total * velocidad_relativa;
    R.potencia_disipada = p.b_eje * velocidad_relativa^2 ...
        + p.b_x * velocidad_x^2 + p.b_phi * velocidad_phi^2;
    R.potencia_neta = R.potencia_motor - R.potencia_disipada;

    %% Reacciones necesarias para que la rodadura impuesta sea posible.
    aceleracion_vertical_G = -p.l * (sin(phi) * aceleracion_phi ...
        + cos(phi) * velocidad_phi^2);
    R.normal = p.m_total * p.g + p.m_cuerpo * aceleracion_vertical_G;
    R.fuerza_tangencial = par_efectivo_ruedas / p.r ...
        - p.J_ruedas * aceleracion_x / p.r^2;
    R.margen_adherencia = p.mu * R.normal - abs(R.fuerza_tangencial);
    R.contacto_valido = R.normal > 0 && R.margen_adherencia >= 0;
    R.matriz_masa = matriz_masa;
    R.determinante = det(matriz_masa);
    R.Q = [Q_x; Q_phi];
    R.velocidad_relativa = velocidad_relativa;
end
