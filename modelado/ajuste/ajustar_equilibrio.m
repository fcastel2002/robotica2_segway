function ajustar_equilibrio()
%AJUSTAR_EQUILIBRIO  Qué hay que corregir del modelo para que dé el equilibrio medido el 3/11.
%
%  Medido (firmware/docs/equilibrio_patas_2026-11-03.csv, FW-017): el ángulo de la IMU con el
%  robot quieto, de 0 a 30° de pata de a 2,5°, cuatro pasadas. En cada altura se toma el centro
%  entre subiendo y bajando (la pata tiene ~0,9° de histéresis).
%
%  Modelo (el mismo cálculo que exportar_planta_escalon.m): con el robot quieto el centro de masa
%  de todo queda sobre el eje de la rueda, así que la IMU marca
%
%       theta_imu(p) = delta_imu + atan2(-cx, cz)
%
%  con (cx, cz) el centro de masa total respecto del eje, en ejes del cuerpo, para la pata p.
%  Se prueban, solas y combinadas, las correcciones que puede haber: delta_imu (cómo está pegada
%  la IMU), el centro de masa de la caja (dx adelante, dz arriba: el reparto de los 542 g es
%  estimado y la LiPo puede no estar donde dice el modelo), y un corrimiento del cero de la pata
%  (dp: la pata real = la pedida + dp).
%
%  Resultado en la ventana de comandos y en ajuste_equilibrio.csv (lo grafica fig_ajuste.py). Lo que
%  se eligió (IMU + caja adelante/atrás + cero de la pata) quedó en la variante 'ajustada' de
%  parametros_fisicos.m.

aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
raiz = fileparts(fileparts(aqui));
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'));

%% 1. Lo medido: centro entre subiendo y bajando en cada altura
T = readtable(fullfile(raiz, 'firmware', 'docs', 'equilibrio_patas_2026-11-03.csv'), 'TextType', 'string');
patas = unique(T.patas);
medido = zeros(size(patas));
for i = 1:numel(patas)
    sel = T.patas == patas(i);
    sube = T.theta(sel & T.sentido == "sube");
    baja = T.theta(sel & T.sentido == "baja");
    medido(i) = mean([mean(sube, 'omitnan'), mean(baja, 'omitnan')], 'omitnan');
end

%% 2. Modelo: masas y cinemática de la segunda iteración
f = parametros_fisicos('segunda_iteracion');
G.AB = f.AB; G.beta = f.ang_AB; G.AD = f.k_AD*f.s_barras; G.BC = f.k_BC*f.s_barras;
G.CD = f.k_CD*f.s_barras; G.DP = f.k_DP*f.s_barras; G.delta = f.delta;
n = f.n_servos;
m = 1e-3*[f.m_cabina; f.m_tapa; n*f.m_servo; f.m_bateria; f.m_electronica; f.m_tornilleria; f.m_carga];
r = 1e-3*[f.r_cabina; f.r_tapa; f.r_servo; f.r_bateria; f.r_electronica; f.r_tornilleria; f.r_carga];
r(:, 1) = -r(:, 1);                         % x adelante
m_caja = sum(m);
rG = sum(m.*r, 1)/m_caja;                   % centro de masa de la caja respecto de A [m]
m_esl = n*1e-3*(f.m_AD + f.m_BC + f.m_CDP);
m_eje = n*1e-3*(f.m_motor + f.m_rueda);

% eje (P) y centro de masa de los eslabones (L) respecto de A, x adelante [m], para la pata p
    function [P, L] = pata(p)
        K = cinematica_directa(350 - p, G);
        cAD = K.A + f.f_AD*(K.D - K.A);  cBC = K.B + f.f_BC*(K.C - K.B);  cCDP = K.D + f.f_CDP*(K.P - K.D);
        Lm = (f.m_AD*cAD + f.m_BC*cBC + f.m_CDP*cCDP)/(f.m_AD + f.m_BC + f.m_CDP);
        P = 1e-3*[-K.P(:, 1), K.P(:, 2)];
        L = 1e-3*[-Lm(:, 1), Lm(:, 2)];
    end

% los parametros libres (libre) en y, el resto como en x0
    function x = armar(y)
        x = x0;
        x(libre) = y;
    end

% IMU en equilibrio [grados]: x = [delta_imu (grados), dx, dz (mm, caja), dp (grados), factor de la caja]
    function th = modelo(x, p)
        [P, L] = pata(p + x(4));
        mc = m_caja*x(5);
        cg = (mc*(rG + 1e-3*[x(2) x(3)]) + m_esl*L + m_eje*P)/(mc + m_esl + m_eje);
        ce = cg - P;                        % (ojo: las funciones anidadas comparten variables)
        th = x(1) + rad2deg(atan2(-ce(:, 1), ce(:, 2)));
    end

%% 3. Ajustes: qué corrección explica lo medido
x0 = [9.8 0 0 0 1];
casos = {
    'solo la IMU (como hasta ahora)',           [1 0 0 0 0]
    'IMU + caja adelante/atras',               [1 1 0 0 0]
    'IMU + caja adelante/atras y arriba/abajo', [1 1 1 0 0]
    'IMU + cero de la pata',                   [1 0 0 1 0]
    'IMU + caja adelante/atras + cero de la pata', [1 1 0 1 0]
    'IMU + caja (x, z) + cero de la pata',     [1 1 1 1 0]
    };
opciones = optimoptions('lsqnonlin', 'Display', 'off', 'FunctionTolerance', 1e-12, 'StepTolerance', 1e-10);
fprintf('Medido (centro subiendo/bajando): %s\n\n', mat2str(round(medido', 2)));
fprintf('%-46s %7s %7s %7s %7s   rms    max\n', 'corrección', 'IMU', 'dx mm', 'dz mm', 'dp');
resultados = cell(size(casos, 1), 1);
for k = 1:size(casos, 1)
    libre = logical(casos{k, 2});
    res = @(y) modelo(armar(y), patas) - medido;
    y = lsqnonlin(res, x0(libre), [], [], opciones);
    x = armar(y);
    e = res(y);
    resultados{k} = x;
    fprintf('%-46s %7.2f %7.1f %7.1f %7.2f  %5.2f  %5.2f\n', casos{k, 1}, x(1:4), sqrt(mean(e.^2)), max(abs(e)));
end

%% 4. Para graficar
pf = (0:0.5:30)';
original = [9.8 0 0 0 1];                  % el modelo como estaba (IMU 9.8 del 2/11)
salida = table(pf, modelo(original, pf), modelo(resultados{1}, pf), modelo(resultados{5}, pf), ...
    'VariableNames', {'pata', 'original', 'solo_imu', 'ajustada'});
e = modelo(original, patas) - medido;
fprintf('\nEl modelo como estaba (IMU 9.8): rms %.2f, max %.2f grados\n', sqrt(mean(e.^2)), max(abs(e)));
writetable(salida, fullfile(aqui, 'ajuste_equilibrio.csv'));
writetable(table(patas, medido), fullfile(aqui, 'equilibrio_medido_centro.csv'));
fprintf('\nCaja: %.1f g, centro de masa a [%.1f %.1f] mm de A (x adelante)\n', 1e3*m_caja, 1e3*rG);
end
