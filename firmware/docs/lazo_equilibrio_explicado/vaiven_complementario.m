% ¿El vaivén lento sale del filtro complementario? El acelerómetro mide la inclinación MENOS la
% aceleración del robot sobre g (theta_acc = theta - (xdd + h*wd)/g), y el filtro le cree por debajo de
% 1/(2 pi tau). Lazo continuo (el modo lento es de ~0,4 Hz, lejos del muestreo), pata 15, modelo de hoy.
raiz = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));   % firmware/docs/<esta carpeta> -> raíz del repo
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
f = parametros_fisicos('ajustada');
p = parametros_pendulo_invertido(f, 15 + f.pata_cero);
[p, ~] = motor_pendulo_invertido(p, f);
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8, 'factor_R', 64);
A = C.A; B = C.B; Vm = 12.3; g = 9.81; wf = 2*pi*20;
k0 = [1.25 2.11 3.69 0.435] .* [0.86 0.86 0.87 0.87];
fprintf('h = altura de la IMU sobre el eje; tau del complementario; modo más lento del lazo\n');
fprintf('%-26s %-6s %-6s | %-28s | %s\n', 'ganancias', 'h [m]', 'tau', 'modo lento: f [Hz], amort.', 'max Re');
casos = {'las de hoy', k0; 'kx x0,7', k0.*[0.7 1 1 1]; 'kx x1,3', k0.*[1.3 1 1 1]; 'tabla 100 %', [1.25 2.11 3.69 0.435]};
for ic = 1:size(casos, 1)
    k = casos{ic, 2};
    for h = [0 0.15]
        for tau = [0.25 0.5 1 2 Inf]
            % estados: x v theta omega theta_e v_f
            K = Vm * [k(1), 0, 0, k(4), k(3), k(2)];        % V = K * s
            Ap = [A, zeros(4, 2); zeros(2, 6)] + [B; 0; 0] * K;   % planta con V
            Ap(6, :) = 0; Ap(6, 2) = wf; Ap(6, 6) = -wf;     % v filtrada
            xdd = Ap(2, :); wd = Ap(4, :);                    % aceleraciones del lazo cerrado
            if isinf(tau)
                Ap(5, :) = Ap(3, :) * 0; Ap(5, 4) = 1;        % solo giróscopo: theta_e' = omega
                Ap(5, :) = Ap(5, :);                          % (theta_e arranca igual a theta)
            else
                fila = zeros(1, 6); fila(4) = 1;              % omega
                fila(3) = fila(3) + 1/tau;                    % + theta/tau
                fila = fila - (xdd + h*wd)/(g*tau);           % - aceleración/(g tau)
                fila(5) = fila(5) - 1/tau;                    % - theta_e/tau
                Ap(5, :) = fila;
            end
            e = eig(Ap);
            e = e(abs(e) > 1e-6 & abs(e) < 2*pi*3);       % los modos de menos de 3 Hz
            [~, o] = sort(abs(e)); e = e(o);
            txt = strjoin(arrayfun(@(s) sprintf('%.2f Hz z=%.2f', abs(s)/2/pi, -real(s)/abs(s)), e(imag(e) >= 0)', 'UniformOutput', false), ' | ');
            fprintf('%-14s h=%-5.2f tau=%-4g | %s\n', casos{ic, 1}, h, tau, txt);
        end
    end
end
