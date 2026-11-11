% Lazo con un encoder muerto: la odometría promedia las dos ruedas, así que ve
% x_m = r*(a/2 + theta) = x/2 + r*theta/2  y  v_m = v/2 + r*omega/2.
raiz = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));   % firmware/docs/<esta carpeta> -> raíz del repo
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
f = parametros_fisicos('ajustada');
p = parametros_pendulo_invertido(f, 15 + f.pata_cero);
[p, ~] = motor_pendulo_invertido(p, f);
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8, 'factor_R', 64);
Ts = 0.005; fs = 1/Ts; z = tf('z', Ts); Vm = 12.3; r = 0.04; wf = 2*pi*20;
k = [1.25 2.11 3.69 0.435] .* [0.86 0.86 0.87 0.87];
N = notch_tf(11.6, 0.7, fs, Ts) * notch_tf(7.7, 2, fs, Ts);
u1 = tf(1, 1, Ts); D = append(u1, u1, 1/z, 1/z);
Af = [C.A, zeros(4,1); wf*[0 1 0 0], -wf]; Bf = [C.B; 0];
for caso = 1:2
    if caso == 1
        Cm = [1 0 0 0 0; 0 0 0 0 1; 0 0 1 0 0; 0 0 0 1 0]; nombre = 'dos encoders';
    else
        % x medida = x/2 + r*theta/2 ; v medida (filtrada) = vf/2 + r*omega/2 (aprox., el filtro sobre los dos)
        Cm = [0.5 0 r/2 0 0; 0 0 0 r/2 0.5; 0 0 1 0 0; 0 0 0 1 0]; nombre = 'encoder izquierdo muerto';
    end
    P = c2d(ss(Af, Bf, Cm, 0), Ts, 'zoh');
    L = minreal(ss(N * (1/z) * (Vm*k) * D * P), 1e-9);
    radio = @(g) max(abs(eig(L.A + L.B*g*L.C / (1 - g*L.D))));
    gs = logspace(-2, 1.3, 2000);
    est = arrayfun(@(g) radio(g) < 1, gs);
    if any(est)
        gmin = gs(find(est, 1, 'first')); gmax = gs(find(est, 1, 'last'));
    else
        gmin = NaN; gmax = NaN;
    end
    e = eig(L.A + L.B*1*L.C / (1 - L.D));
    s = log(e(abs(e) > 1e-6))/Ts; s = s(imag(s) >= 0 & abs(s) < 2*pi*10);
    [~, o] = sort(abs(s)); s = s(o);
    txt = strjoin(arrayfun(@(q) sprintf('%.2f Hz z=%.2f', abs(q)/2/pi, -real(q)/abs(q)), s', 'UniformOutput', false), ' | ');
    fprintf('%-26s | estable de x%.2f a x%.2f (radio a x1: %.3f)\n   modos < 10 Hz: %s\n', nombre, gmin, gmax, radio(1), txt);
end
function N = notch_tf(f0, q, fs, Ts)
    w0 = 2*pi*f0/fs; al = sin(w0)/(2*q); a0 = 1 + al;
    N = tf([1 -2*cos(w0) 1]/a0, [1 -2*cos(w0)/a0 (1-al)/a0], Ts);
end
