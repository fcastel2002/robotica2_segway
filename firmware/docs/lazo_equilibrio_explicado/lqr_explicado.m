% Reproduce el LQR de LQR_TABLA_DRV en la pata de 15 grados y lo compara con lo que corre en el firmware.
% Solo imprime: no escribe nada en el repositorio.
raiz = fileparts(fileparts(fileparts(fileparts(mfilename('fullpath')))));   % firmware/docs/<esta carpeta> -> raíz del repo
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));

f_hoy = parametros_fisicos('ajustada');
% El modelo como estaba el 7/11 cuando se hizo LQR_TABLA_DRV: 1196 g y el motor de la ficha a 26 RPM/V
f_7 = f_hoy;
f_7.m_carga = 234; f_7.R_m = 10.28; f_7.i_vacio = 0.060; f_7.w_nl_motor_rpm = 6060;
f_7.tau_c = 0.0015; f_7.b_m = 1e-6; f_7.J_r = 6e-7;

pata = 15;
k_tabla = [1.25 2.11 3.69 0.435];                 % LQR_TABLA_DRV en 15 grados
k_corre = k_tabla .* [0.86 0.86 0.87 0.87];       % lo que corre (lqrfacx, lqrfac)
variantes = {'modelo del 7/11 (el de la tabla)', f_7; 'modelo de hoy (motor medido)', f_hoy};
for iv = 1:2
    f = variantes{iv, 2};
    V_motor = f.V_bat - f.caida_driver;
    p = parametros_pendulo_invertido(f, pata + f.pata_cero);
    [p, m] = motor_pendulo_invertido(p, f);
    C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8, 'factor_R', 64);
    k = -C.K / V_motor;
    fprintf('\n===== %s, pata %d =====\n', variantes{iv, 1}, pata);
    fprintf('V_bat %.2f V, caida %.2f V -> V_motor %.2f V; masa %.0f g; l = %.1f mm\n', f.V_bat, f.caida_driver, V_motor, f.m_carga + 962, 1e3*p.l);
    fprintf('A =\n'); disp(C.A);
    fprintf('B (por voltio) =\n'); disp(C.B');
    fprintf('Q = diag(%s)\n', sprintf('%.4g ', diag(C.Q)));
    fprintf('R (por V^2) = %.5g ; R en PWM = R*V_motor^2 = %.4g ; max_tension %.2f\n', C.R, C.R*V_motor^2, C.limites.max_tension);
    fprintf('K [V] = %s\n', sprintf('%.4f ', C.K));
    fprintf('k [PWM] = %s\n', sprintf('%.4f ', k));
    fprintf('sqrt(Qx/R_pwm) = %.4f\n', sqrt(C.Q(1,1)/(C.R*V_motor^2)));
    ol = eig(C.A); fprintf('polos lazo abierto: %s\n', sprintf('%.3f%+.3fi  ', [real(ol) imag(ol)]'));
    polos_info('LQR optimo', C.polos);
    polos_info('tabla del firmware', eig(C.A + C.B*(V_motor*k_tabla)));
    polos_info('lo que corre (x0.86/0.87)', eig(C.A + C.B*(V_motor*k_corre)));
    % lazo muestreado: 5 ms, un paso de retardo, velocidad filtrada a 20 Hz
    Ts = f.Ts; wf = 2*pi*f.fc_vel;
    for kk = {k, k_tabla, k_corre}
        kj = kk{1};
        K = -kj*V_motor;
        Af = [C.A, zeros(4,1); wf*[0 1 0 0], -wf]; Bf = [C.B; 0];
        Kf = [K(1), 0, K(3), K(4), K(2)];
        d = c2d(ss(Af, Bf, eye(5), 0), Ts, 'zoh');
        radio = @(g) max(abs(eig([d.A, d.B; -g*Kf, 0])));
        lo = 1; hi = 20; for it = 1:40, mm = (lo+hi)/2; if radio(mm) < 1, lo = mm; else, hi = mm; end, end
        zl = eig([d.A, d.B; -Kf, 0]);
        sl = log(zl(abs(zl) > 1e-6))/Ts;
        [~, ii] = sort(abs(sl));
        fprintf('  k=[%s] muestreado: radio %.4f, aguanta x%.2f de ganancia\n', sprintf('%.3f ', kj), radio(1), lo);
        fprintf('     polos equivalentes s: %s\n', sprintf('%.2f%+.2fi  ', [real(sl(ii)) imag(sl(ii))]'));
    end
    % Que tension pide cada estado en su "maximo tolerable"
    fprintf('u por 1 grado: %.4f PWM; por 1 cm: %.4f; por 0,1 m/s: %.4f; por 10 grados/s: %.4f\n', ...
        k(3)*pi/180, k(1)*0.01, k(2)*0.1, k(4)*10*pi/180);
    fprintf('beta_V (par 2 motores por voltio) = %.4f N m/V ; b_m = %.4f N m s/rad ; Kt=%.4f Ke=%.4f R=%.2f\n', m.beta_V, m.b_m, m.Kt, m.Ke, f.R_m);
end

function polos_info(nombre, s)
    s = sort(s);
    fprintf('  %s:\n', nombre);
    for i = 1:numel(s)
        wn = abs(s(i)); z = -real(s(i))/wn;
        fprintf('     %9.3f %+8.3fi   wn %.2f rad/s = %.2f Hz, amort %.2f\n', real(s(i)), imag(s(i)), wn, wn/2/pi, z);
    end
end
