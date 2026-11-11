% Margen del lazo (modelo de hoy, pata 15) con los filtros del firmware: notch, retardo del DLPF y
% el paso de retardo de cálculo. Solo imprime.
raiz = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));   % firmware/docs/<esta carpeta> -> raíz del repo
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
f = parametros_fisicos('ajustada');
p = parametros_pendulo_invertido(f, 15 + f.pata_cero);
[p, ~] = motor_pendulo_invertido(p, f);
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8, 'factor_R', 64);
Ts = 0.005; fs = 1/Ts; wf = 2*pi*20;
Af = [C.A, zeros(4,1); wf*[0 1 0 0], -wf]; Bf = [C.B; 0];
Cm = [1 0 0 0 0; 0 0 0 0 1; 0 0 1 0 0; 0 0 0 1 0];      % x, v filtrada, theta, omega
P = c2d(ss(Af, Bf, Cm, 0), Ts, 'zoh');
z = tf('z', Ts);
Vm = 12.3;
k_corre = [1.25 2.11 3.69 0.435] .* [0.86 0.86 0.87 0.87];
k_tabla = [1.25 2.11 3.69 0.435];

casos = {
  'sin filtros, sin DLPF',                 k_corre, [],              false
  'sin filtros, con DLPF (1 muestra)',     k_corre, [],              true
  'notch 7,5 Q0,7 (el del L298N), DLPF',   k_corre, [7.5 0.7],       true
  'notch 11,6 Q0,7, DLPF',                 k_corre, [11.6 0.7],      true
  'notch 7,7 Q2, DLPF',                    k_corre, [7.7 2],         true
  'HOY: 11,6 Q0,7 + 7,7 Q2, DLPF',         k_corre, [11.6 0.7; 7.7 2], true
  'HOY con la tabla al 100 %',             k_tabla, [11.6 0.7; 7.7 2], true
  'tabla 100 % con notch 7,5 Q0,7',        k_tabla, [7.5 0.7],       true
};
fprintf('%-38s | g_min  g_max | MF [grados] a f [Hz] | oscila en (g_max)\n', 'caso');
for i = 1:size(casos, 1)
    k = casos{i, 2}; nf = casos{i, 3}; dl = casos{i, 4};
    N = tf(1, 1, Ts);
    for j = 1:size(nf, 1)
        N = N * notch_tf(nf(j, 1), nf(j, 2), fs, Ts);
    end
    u1 = tf(1, 1, Ts); if dl, D = append(u1, u1, 1/z, 1/z); else, D = append(u1, u1, u1, u1); end
    L = minreal(ss(N * (1/z) * (Vm*k) * D * P), 1e-9);      % de V a V (realimentación positiva)
    radio = @(g) max(abs(eig(L.A + L.B*g*L.C / (1 - g*L.D))));
    gs = logspace(-2, 1.3, 2000);
    est = arrayfun(@(g) radio(g) < 1, gs);
    gmin = gs(find(est, 1, 'first')); gmax = gs(find(est, 1, 'last'));
    % frecuencia de la oscilación en g_max
    Acl = L.A + L.B*gmax*1.001*L.C / (1 - gmax*1.001*L.D);
    e = eig(Acl); [~, ii] = max(abs(e)); fosc = abs(angle(e(ii)))/(2*pi*Ts);
    m = allmargin(-L);
    pm = m.PhaseMargin; wc = m.PMFrequency;
    if isempty(pm), pms = '-'; else, pms = sprintf('%.0f a %.2f Hz', pm(1), wc(1)/2/pi); end
    fprintf('%-38s | %5.2f %5.2f | %-20s | %.1f Hz\n', casos{i, 1}, gmin, gmax, pms, fosc);
end

function N = notch_tf(f0, q, fs, Ts)
    w0 = 2*pi*f0/fs; al = sin(w0)/(2*q); a0 = 1 + al;
    N = tf([1 -2*cos(w0) 1]/a0, [1 -2*cos(w0)/a0 (1-al)/a0], Ts);
end
