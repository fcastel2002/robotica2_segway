function ajustar_equilibrio(m_carga, archivo, imu_medida)
%AJUSTAR_EQUILIBRIO  Qué hay que corregir del modelo para que dé el equilibrio medido el 3/11.
%
%  ajustar_equilibrio()        con la carga extra de la variante 'ajustada' (5/11: los 234 g que le
%                              faltaban al modelo para pesar los 1196 g medidos con la LiPo)
%  ajustar_equilibrio(0)       como el 3/11 (sin la carga: el modelo de 962 g)
%  ajustar_equilibrio(m, 'equilibrio_pcb.csv')   con otra medición (graficar_equilibrio.py --csv, de
%                              sesion_placa.py medir_equilibrio). 7/11: con las PCB la IMU está en otro
%                              lugar: en el último caso se ajusta la IMU, con la caja del 5/11; el cero
%                              de la pata sigue siendo el del 3/11 (es del mecanismo). Escribe
%                              ajuste_equilibrio_<archivo>.csv y equilibrio_medido_<archivo>.csv
%  ajustar_equilibrio(m, 'equilibrio_pcb.csv', imu)   con la IMU medida contra la caja (el theta que
%                              marca con las aristas de la caja a plomo): ajusta la caja (x, z) con esa IMU
%
%  5/11: la curva medida no cambia con el peso (es el centro de masa de todo, LiPo incluida), y la
%  IMU y el cero de la pata no dependen del peso: con la carga quedan como el 3/11 y solo se corre la
%  caja (adelante/atrás y arriba/abajo). Es el último caso y el que se grafica como 'ajustada'.
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
if nargin < 2 || isempty(archivo)
    archivo = fullfile(raiz, 'firmware', 'docs', 'equilibrio_patas_2026-11-03.csv');
    sufijo = '';
else
    [~, nombre] = fileparts(archivo);
    sufijo = ['_' nombre];
end
T = readtable(archivo, 'TextType', 'string');
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
if nargin < 1 || isempty(m_carga)
    fa = parametros_fisicos('ajustada');
    m_carga = fa.m_carga;
end
f.m_carga = m_carga;                        % en la cabina (r_carga)
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

% los parametros libres (libre) en y, el resto como en base
    function x = armar(y)
        x = base;
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
x_3nov = [4.17 0 0 10.41 1];                % la IMU y el cero de la pata del 3/11
casos = {
    'solo la IMU (como hasta ahora)',           [1 0 0 0 0], x0
    'IMU + caja adelante/atras',               [1 1 0 0 0], x0
    'IMU + caja adelante/atras y arriba/abajo', [1 1 1 0 0], x0
    'IMU + cero de la pata',                   [1 0 0 1 0], x0
    'IMU + caja adelante/atras + cero de la pata', [1 1 0 1 0], x0
    'IMU + caja (x, z) + cero de la pata',     [1 1 1 1 0], x0
    'solo la caja (x, z), IMU y pata del 3/11', [0 1 1 0 0], x_3nov
    };
if ~isempty(sufijo)
    % La IMU en la PCB: otra inclinación; la pata es la del 3/11. La curva sola no separa la IMU de la x
    % de la caja (con los datos del 3/11, IMU + caja x, z da IMU -0,9 y la caja 51 mm atrás y 43 arriba:
    % 0,09 contra 0,12 de rms). Por eso, si se midió la IMU contra la caja (imu_medida: el theta que
    % marca con las aristas de la caja a plomo), se ajusta la caja con esa IMU; si no, solo la IMU, con
    % la caja del 5/11 (el reparto de masas casi no cambió con las PCB).
    x_5nov = [4.17 -24.7 -8.2 10.41 1];
    casos(end + 1, :) = {'IMU y caja (x, z), pata del 3/11 (mal condicionado)', [1 1 1 0 0], x_3nov};
    if nargin >= 3 && ~isempty(imu_medida)
        casos(end + 1, :) = {sprintf('caja (x, z) con la IMU medida (%.2f), pata del 3/11', imu_medida), ...
                             [0 1 1 0 0], [imu_medida 0 0 10.41 1]};
    else
        casos(end + 1, :) = {'solo la IMU, caja del 5/11 y pata del 3/11', [1 0 0 0 0], x_5nov};
    end
end
opciones = optimoptions('lsqnonlin', 'Display', 'off', 'FunctionTolerance', 1e-12, 'StepTolerance', 1e-10);
fprintf('Medido (centro subiendo/bajando): %s\n\n', mat2str(round(medido', 2)));
fprintf('%-46s %7s %7s %7s %7s   rms    max\n', 'corrección', 'IMU', 'dx mm', 'dz mm', 'dp');
resultados = cell(size(casos, 1), 1);
for k = 1:size(casos, 1)
    libre = logical(casos{k, 2});
    base = casos{k, 3};
    res = @(y) modelo(armar(y), patas) - medido;
    y = lsqnonlin(res, base(libre), [], [], opciones);
    x = armar(y);
    e = res(y);
    resultados{k} = x;
    fprintf('%-46s %7.2f %7.1f %7.1f %7.2f  %5.2f  %5.2f\n', casos{k, 1}, x(1:4), sqrt(mean(e.^2)), max(abs(e)));
end

%% 4. Para graficar
pf = (0:0.5:30)';
original = [9.8 0 0 0 1];                  % el modelo como estaba (IMU 9.8 del 2/11)
ajustada = modelo(resultados{end}, pf);
solo_imu = modelo(resultados{1}, pf);
% el de antes, sin la carga (el último ítem de la caja): modelo() usa estas dos
m_con_carga = m_caja;  rG_con_carga = rG;   % (ojo: modelo() ya usa el nombre mc)
m_caja = sum(m(1:end-1));  rG = sum(m(1:end-1).*r(1:end-1, :), 1)/m_caja;
salida = table(pf, modelo(original, pf), solo_imu, ajustada, ...
    'VariableNames', {'pata', 'original', 'solo_imu', 'ajustada'});
e = modelo(original, patas) - medido;
m_caja = m_con_carga;  rG = rG_con_carga;
fprintf('\nEl modelo como estaba (IMU 9.8): rms %.2f, max %.2f grados\n', sqrt(mean(e.^2)), max(abs(e)));
writetable(salida, fullfile(aqui, ['ajuste_equilibrio' sufijo '.csv']));
writetable(table(patas, medido), fullfile(aqui, ['equilibrio_medido_centro' sufijo '.csv']));
x = resultados{end};
fprintf(['\nPara la variante ''ajustada'' (el último caso): imu_delta_deg = %.2f; corr_caja = [%.1f %.1f] ' ...
         '(mm, x hacia atrás e y hacia arriba, como en parametros_fisicos.m)\n'], x(1), -x(2), x(3));
fprintf('\nCaja: %.1f g, centro de masa a [%.1f %.1f] mm de A (x adelante)\n', 1e3*m_caja, 1e3*rG);
end
