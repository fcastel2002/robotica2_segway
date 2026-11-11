% Lo mismo que vaiven_complementario.m, sumando la referencia automática: d(ref)/dt = -0,035 * x
raiz = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));   % firmware/docs/<esta carpeta> -> raíz del repo
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
f = parametros_fisicos('ajustada');
p = parametros_pendulo_invertido(f, 15 + f.pata_cero);
[p, ~] = motor_pendulo_invertido(p, f);
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8, 'factor_R', 64);
A = C.A; B = C.B; Vm = 12.3; g = 9.81; wf = 2*pi*20; h = 0.15;
k = [1.25 2.11 3.69 0.435] .* [0.86 0.86 0.87 0.87];
for ra = [0 0.035]
  for tau = [0.5 1 2]
    % estados: x v theta omega theta_e v_f ref
    K = Vm * [k(1), 0, 0, k(4), k(3), k(2), -k(3)];
    Ap = [A, zeros(4, 3); zeros(3, 7)] + [B; 0; 0; 0] * K;
    Ap(6, :) = 0; Ap(6, 2) = wf; Ap(6, 6) = -wf;
    xdd = Ap(2, :); wd = Ap(4, :);
    fila = zeros(1, 7); fila(4) = 1; fila(3) = 1/tau; fila = fila - (xdd + h*wd)/(g*tau); fila(5) = fila(5) - 1/tau;
    Ap(5, :) = fila;
    Ap(7, :) = 0; Ap(7, 1) = -ra;
    e = eig(Ap); e = e(abs(e) > 1e-6 & abs(e) < 2*pi*3); [~, o] = sort(abs(e)); e = e(o);
    txt = strjoin(arrayfun(@(s) sprintf('%.2f Hz z=%.2f', abs(s)/2/pi, -real(s)/abs(s)), e(imag(e) >= 0)', 'UniformOutput', false), ' | ');
    fprintf('refauto %-5g tau %-3g | %s\n', ra, tau, txt);
  end
end
