% Cuánto margen le cuesta al lazo el pasabajos de la velocidad (modelo de hoy, pata 15, notch de hoy, DLPF).
raiz = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));   % firmware/docs/<esta carpeta> -> raíz del repo
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
f = parametros_fisicos('ajustada');
p = parametros_pendulo_invertido(f, 15 + f.pata_cero);
[p, ~] = motor_pendulo_invertido(p, f);
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8, 'factor_R', 64);
Ts = 0.005; fs = 1/Ts; z = tf('z', Ts); Vm = 12.3;
k = [1.25 2.11 3.69 0.435] .* [0.86 0.86 0.87 0.87];
N = notch_tf(11.6, 0.7, fs, Ts) * notch_tf(7.7, 2, fs, Ts);
u1 = tf(1, 1, Ts); D = append(u1, u1, 1/z, 1/z);
fprintf('%-28s | g_min g_max | MF a f | oscila en\n', 'velocidad');
for fc = [10 20 40 80 0]
    if fc > 0
        wf = 2*pi*fc;
        Af = [C.A, zeros(4,1); wf*[0 1 0 0], -wf]; Bf = [C.B; 0];
        Cm = [1 0 0 0 0; 0 0 0 0 1; 0 0 1 0 0; 0 0 0 1 0];
        nombre = sprintf('pasabajos %d Hz', fc);
    else
        Af = C.A; Bf = C.B; Cm = eye(4); nombre = 'sin filtro (v perfecta)';
    end
    P = c2d(ss(Af, Bf, Cm, 0), Ts, 'zoh');
    L = minreal(ss(N * (1/z) * (Vm*k) * D * P), 1e-9);
    radio = @(g) max(abs(eig(L.A + L.B*g*L.C / (1 - g*L.D))));
    gs = logspace(-2, 1.3, 2000);
    est = arrayfun(@(g) radio(g) < 1, gs);
    gmin = gs(find(est, 1, 'first')); gmax = gs(find(est, 1, 'last'));
    Acl = L.A + L.B*gmax*1.001*L.C / (1 - gmax*1.001*L.D);
    e = eig(Acl); [~, ii] = max(abs(e)); fosc = abs(angle(e(ii)))/(2*pi*Ts);
    m = allmargin(-L);
    fprintf('%-28s | %5.2f %5.2f | %.0f a %.2f Hz | %.1f Hz\n', nombre, gmin, gmax, m.PhaseMargin(1), m.PMFrequency(1)/2/pi, fosc);
end

function N = notch_tf(f0, q, fs, Ts)
    w0 = 2*pi*f0/fs; al = sin(w0)/(2*q); a0 = 1 + al;
    N = tf([1 -2*cos(w0) 1]/a0, [1 -2*cos(w0)/a0 (1-al)/a0], Ts);
end
