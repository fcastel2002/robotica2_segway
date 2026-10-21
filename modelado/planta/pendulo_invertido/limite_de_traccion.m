function [tau_max, F_max, c1] = limite_de_traccion(p)
%LIMITE_DE_TRACCION Par del motor con el que la rueda llega al limite de adherencia.
%   [tau_max, F_max, c1] = limite_de_traccion(p)
%     tau_max  par del motor que pone exactamente F_max en el piso [N m]
%     F_max    fuerza que el piso puede transmitir, f*mu*N estatica [N]
%     c1       fuerza en el piso por cada N m de par, en phi = 0 [N/(N m)]
%
%   --- Por que NO es mu*N*r ---
%   Esa conversion supone que todo el par del motor se convierte en fuerza contra
%   el piso, y es falsa: parte del par acelera la inercia reflejada del rotor, que
%   con el reductor 1:20 equivale a 0.44 kg sobre un robot de 1.0 kg. Usar mu*N*r
%   limita el par a un TERCIO del valor correcto, o sea que vuelve al robot mucho
%   mas torpe de lo que es.
%
%   La fuerza en el contacto sale de Newton sobre TODO el robot, porque el
%   rozamiento es la unica fuerza horizontal externa. Con x_CoM = x - (h/m) sin(phi):
%
%       F = m_total*x'' - h cos(phi) phi'' + h sin(phi) phi'^2
%
%   y como q'' = M \ (H tau + resto), F depende de tau de forma afin:
%
%       F = c1*tau + c0,     c1 = [m_total, -h cos(phi)] * inv(M) * H
%
%   El limite se evalua en phi = 0, que es donde opera el robot, con la normal
%   estatica y un factor de seguridad p.factor_traccion (0.9 por defecto).
%
%   --- Lectura del resultado ---
%   Con los parametros vigentes tau_max sale apenas por encima del par de bloqueo del
%   motor: a tension plena desde el reposo usa el 98 % del agarre. O sea que el motor
%   NO llega a hacer patinar la rueda, pero por muy poco, y el veredicto cuelga de mu,
%   que es el unico parametro del modelo SIN MEDIR (0.7 supuesto). Si el piso diera
%   mu < 0.69, a fondo patina. Lo que hay que mirar para decidir si importa: el
%   equilibrio normal, de mas menos 2 grados, pide apenas mu = 0.20; recuperarse de
%   10 grados pide 0.69. Ver el ensayo M-1 en docs/gestion/2026-10-21-plan-de-ensayos.md
%   y la figura fig_traccion.png de esta carpeta.
%
%   Hasta el 21/10/2026, con las masas estimadas, el robot pesaba 1006 g y este numero
%   daba 87 %. Al pesarlo resulto de 920 g y, contra la intuicion, el uso del agarre
%   SUBIO: mas liviano significa menos peso sobre la rueda, o sea menos friccion
%   disponible, y el par del motor no cambio.
%
%   La saturacion queda igual como red de seguridad por si cambian la rueda, el piso
%   o el motor.

    if isfield(p, 'factor_traccion'), f = p.factor_traccion; else, f = 0.9; end
    if isfield(p, 'e_acople'), e = p.e_acople; else, e = 0; end
    validateattributes(p.mu, {'numeric'}, {'scalar', 'real', 'finite', 'nonnegative'});

    M0 = [p.a, -p.h + e; -p.h + e, p.j];
    c1 = [p.m_total, -p.h] * (M0 \ [-1/p.r; -1]);
    assert(abs(c1) > eps, 'La fuerza en el piso no depende del par: revisar la planta.');

    F_max = f*p.mu*p.m_total*p.g;
    tau_max = F_max/abs(c1);
end
