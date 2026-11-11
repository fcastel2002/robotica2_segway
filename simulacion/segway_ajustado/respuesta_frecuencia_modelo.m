%% RESPUESTA_FRECUENCIA_MODELO  Lo que el modelo ajustado (cuerpo rígido) dice de la respuesta en frecuencia,
% para compararla con la medida en el robot con "set exc" (modelado/ajuste/identificar_lazo.py, 7/11).
%
%  Para la pata dada (15° por defecto), de 0,5 a 25 Hz y por unidad de PWM (el motor recibe V_motor·u):
%    P_w   velocidad de cabeceo [rad/s] por unidad de PWM
%    P_v   velocidad de avance [m/s] por unidad de PWM
%    L     el lazo abierto del firmware: LQR (ganancias de la tabla por los factores), velocidad filtrada a
%          20 Hz, los dos notch, un ciclo de retardo; L = -C·P (el robot es estable si 1 + L no rodea el 0)
%  Escribe respuesta_frecuencia_modelo.csv al lado de este archivo.

if ~exist('pata', 'var'), pata = 15; end              % se puede poner antes de correrlo: pata = 30;
f_rapido = 0.87;  f_lento = 0.86;                       % lo del ajuste automático del 7/11
notch = 11.6;  notch2 = 7.7;                            % Hz (Q 0,7 y 2, como balance.c)
aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
raiz = fileparts(fileparts(aqui));
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
f = parametros_fisicos('ajustada');
V = f.V_bat - f.caida_driver;
p = parametros_pendulo_invertido(f, pata + f.pata_cero);
[p, ~] = motor_pendulo_invertido(p, f);
C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8, 'factor_R', 64);
Ts = f.Ts;
% planta por unidad de PWM: z = [x v phi w]
Pc = ss(C.A, C.B*V, eye(4), 0);
% la del firmware: k = factores · LQR_TABLA_DRV en la pata (fila de 15°: 1.25 2.11 3.69 0.435)
tabla = [1.25 2.10 3.13 0.329; 1.25 2.10 3.34 0.364; 1.25 2.10 3.52 0.399; 1.25 2.11 3.69 0.435; ...
         1.25 2.11 3.85 0.470; 1.25 2.12 4.00 0.506; 1.25 2.13 4.15 0.544];
k = interp1((0:5:30)', tabla, pata) .* [f_lento f_lento f_rapido f_rapido];
s = tf('s');
filtro_v = (2*pi*f.fc_vel)/(s + 2*pi*f.fc_vel);
N1 = (s^2 + (2*pi*notch)^2)/(s^2 + 2*pi*notch/0.7*s + (2*pi*notch)^2);
N2 = (s^2 + (2*pi*notch2)^2)/(s^2 + 2*pi*notch2/2*s + (2*pi*notch2)^2);
retardo = exp(-Ts*s);
fr = logspace(log10(0.5), log10(25), 300)';
w = 2*pi*fr;
H = freqresp(Pc, w);                                  % 4 x 1 x n
Pw = squeeze(H(4, 1, :));  Pv = squeeze(H(2, 1, :));
Px = squeeze(H(1, 1, :));  Pphi = squeeze(H(3, 1, :));
Fv = squeeze(freqresp(filtro_v, w));  F = squeeze(freqresp(N1*N2*retardo, w));
% u = F · (kx x + kv v_f + kphi phi + kw w) con todo positivo adelante (balance.h): L = -u/u_entrada
Cu = k(1)*Px + k(2)*Fv.*Pv + k(3)*Pphi + k(4)*Pw;
L = -F .* Cu;
T = table(fr, abs(Pw), rad2deg(angle(Pw)), abs(Pv), rad2deg(angle(Pv)), abs(L), rad2deg(unwrap(angle(L))), ...
    'VariableNames', {'f_hz', 'Pw_mag', 'Pw_fase', 'Pv_mag', 'Pv_fase', 'L_mag', 'L_fase'});
writetable(T, fullfile(aqui, 'respuesta_frecuencia_modelo.csv'));
S = 1 ./ (1 + L);
[Ms, i] = max(abs(S));
fprintf('Modelo, pata %g, k = [%.3f %.3f %.3f %.4f]: pico de sensibilidad %.2f en %.1f Hz\n', pata, k, Ms, fr(i));
fprintf('-> respuesta_frecuencia_modelo.csv\n');
