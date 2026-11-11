%% AJUSTAR_PATA_FLEXIBLE  El modelo lineal con la pata que cede, ajustado con los barridos del 11/11.
%
%  El robot en tres cuerpos: la rueda (avance x), la PATA (manivelas, balancines, acopladores y las carcasas de
%  los motores; ángulo phi1) y la CAJA (todo lo demás, con la IMU; ángulo phi2). Los dos cuerpos giran alrededor
%  del eje de la rueda y los une un resorte de torsión k_s con su amortiguador c_s: el servo, su reductora y las
%  barras que ceden. El motor empuja entre la rueda y la pata (su carcasa va en el acoplador); la IMU mide la caja.
%  Además, la REDUCTORA del motor también cede: el rotor (que pesa 8,5 veces la rueda vista desde el eje) es un
%  cuerpo aparte, unido a la rueda por un resorte de torsión k_g con su amortiguador c_g (visto del lado de la
%  rueda). Con k_s y k_g infinitos es el modelo rígido de siempre (lo medido el 10-11/11, ajustar_modelo_11nov.m).
%
%  Se ajustan k_s, c_s, el roce equivalente de la reductora y el retardo con la planta medida (cabeceo de la
%  caja y avance por unidad de PWM, 2 a 15 Hz, patas 0, 15 y 30 a la vez: frf_barridos.py). Simplificación: el
%  giro relativo es alrededor del eje de la rueda, no del eje del servo; el rebote de arriba abajo no está.
%
%  Imprime k_s, c_s y la frecuencia del modo según la pata; deja fig_pata_flexible.png y pata_flexible.csv.

aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
raiz = fileparts(fileparts(aqui));
addpath(fullfile(raiz, 'modelado', 'parametros'), fullfile(raiz, 'modelado', 'cinematica'), ...
        fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
f = parametros_fisicos('ajustada');
T = readtable(fullfile(aqui, 'barridos_2026-11-11_frf.csv'));
patas = unique(T.pata)';
v_bat = arrayfun(@(p) T.v_bat(find(T.pata == p, 1)), patas);
banda = T.f_hz >= 2 & T.f_hz <= 15;
D = T(banda, :);
op = optimoptions('lsqnonlin', 'Display', 'off', 'FunctionTolerance', 1e-12, 'StepTolerance', 1e-10);

% y = [k_s (N m/rad), c_s (N m s/rad), b_roce (N m s/rad), retardo (s), k_g (N m/rad), c_g (N m s/rad)]
RIGIDO = 1e4;
res = @(y) residuo(f, y, D, patas, v_bat);
y_rig = [RIGIDO 0 f.b_roce_equivalente f.retardo_s RIGIDO 0];
fprintf('Rígido (lo del 11/11): error %.3f (2 a 15 Hz)\n', sqrt(mean(res(y_rig).^2)));
casos = {'solo la pata cede', [1 1 1 1 0 0]
         'solo la reductora cede', [0 0 1 1 1 1]
         'las dos', [1 1 1 1 1 1]};
lb = [0.5 0 0 0 0.5 0];  ub = [RIGIDO 5 0.2 0.03 RIGIDO 5];
for k = 1:size(casos, 1)
    libre = logical(casos{k, 2});
    mejor = [];  emejor = inf;
    for ks0 = [5 20 60]
        for kg0 = [1 3 10]
            y0 = y_rig;  y0(1) = ks0;  y0(2) = 0.05;  y0(5) = kg0;  y0(6) = 0.01;
            y0(~libre) = y_rig(~libre);
            z = lsqnonlin(@(z) res(armar(y0, libre, z)), y0(libre), lb(libre), ub(libre), op);
            yk = armar(y0, libre, z);
            e = sqrt(mean(res(yk).^2));
            if e < emejor, emejor = e; mejor = yk; end
        end
    end
    fprintf('%-24s k_s %7.1f  c_s %.3f  k_g %7.2f  c_g %.4f  roce %.4f  retardo %4.1f ms -> error %.3f\n', ...
        casos{k, 1}, mejor(1), mejor(2), mejor(5), mejor(6), mejor(3), 1e3 * mejor(4), emejor);
end
y = mejor;          % el último: las dos
filas = [];
for ip = 1:numel(patas)
    [A, ~, ~, info] = planta_flexible(f, y, patas(ip), v_bat(ip));
    ev = eig(A);
    osc = sort(ev(imag(ev) > 1), 'ComparisonMethod', 'abs');
    fn = abs(osc) / (2 * pi);  z = -real(osc) ./ abs(osc);
    fprintf('   patas %2d: la caja %.3f kg (l %.0f mm, J %.4f), la pata %.3f kg (l %.0f mm, J %.4f); modos %s Hz, amortiguamiento %s\n', ...
        patas(ip), info.m2, 1e3 * info.l2, info.j2, info.m1, 1e3 * info.l1, info.j1, mat2str(round(fn', 1)), ...
        mat2str(round(z', 2)));
    filas = [filas; patas(ip), fn(1), z(1), fn(end), z(end)]; %#ok<AGROW>
end
writetable(array2table([repmat(y, size(filas, 1), 1), filas], 'VariableNames', ...
    {'k_s', 'c_s', 'b_roce', 'retardo_s', 'k_g', 'c_g', 'pata', 'f_modo1_hz', 'amort1', 'f_modo2_hz', 'amort2'}), ...
    fullfile(aqui, 'pata_flexible.csv'));

%% El lazo cerrado con el control de hoy: ¿da el pico de sensibilidad medido?
tabla = [1.25 2.10 3.13 0.329; 1.25 2.10 3.34 0.364; 1.25 2.10 3.52 0.399; 1.25 2.11 3.69 0.435; ...
         1.25 2.11 3.85 0.470; 1.25 2.12 4.00 0.506; 1.25 2.13 4.15 0.544];      % LQR_TABLA_DRV, patas 0:5:30
fprintf('Pico de sensibilidad con el control de hoy (tabla x 0,86/0,87, notch 11,6 y 7,7, velocidad a 20 Hz):\n');
for ip = 1:numel(patas)
    kf = interp1((0:5:30)', tabla, patas(ip)) .* [0.86 0.86 0.87 0.87];
    Dp = T(T.pata == patas(ip), :);
    Sm = abs(Dp.S_re + 1i * Dp.S_im);
    fr = linspace(1, 20, 400)';
    [Sr, ~] = sensibilidad(f, y_rig, patas(ip), v_bat(ip), fr, kf);
    [Sf, ~] = sensibilidad(f, y, patas(ip), v_bat(ip), fr, kf);
    [a, i] = max(Sm);  [b, jr] = max(abs(Sr));  [c, jf] = max(abs(Sf));
    fprintf('   patas %2d: robot %.2f en %.1f Hz | rígido %.2f en %.1f Hz | con lo que cede %.2f en %.1f Hz', ...
        patas(ip), a, Dp.f_hz(i), b, fr(jr), c, fr(jf));
    for extra = [0.0025 0.005 0.0075]       % retardo de más en el control (no está en la planta medida)
        yy = y;  yy(4) = y(4) + extra;
        Se = sensibilidad(f, yy, patas(ip), v_bat(ip), fr, kf);
        [c2, j2] = max(abs(Se));
        fprintf(' | +%.1f ms: %.2f en %.1f Hz', 1e3 * extra, c2, fr(j2));
    end
    fprintf('\n');
end

%% ¿Hasta qué lqrfac aguanta? (en el robot, 7/11: con 1,0 oscila, con 0,87 anda)
fprintf('lqrfac (kphi y kw sobre la tabla) con el que el lazo empieza a oscilar:\n');
for ip = 1:numel(patas)
    kt = interp1((0:5:30)', tabla, patas(ip));
    fr = linspace(0.5, 25, 3000)';
    lim = zeros(1, 2);  modelos = {y_rig, y};
    for im = 1:2
        [~, Lx] = sensibilidad(f, modelos{im}, patas(ip), v_bat(ip), fr, kt .* [0.86 0.86 0 0]);
        [~, Lp] = sensibilidad(f, modelos{im}, patas(ip), v_bat(ip), fr, kt .* [0 0 1 1]);
        g = -(1 + Lx) ./ Lp;                     % 1 + Lx + g Lp = 0 con g real positivo
        cruce = find(diff(sign(imag(g))) ~= 0);
        gr = real(g(cruce));  gr = gr(gr > 0);
        if isempty(gr), lim(im) = NaN; else, lim(im) = min(gr(gr > 0.3)); end
    end
    fprintf('   patas %2d: rígido %.2f | con lo que cede %.2f\n', patas(ip), lim);
end

%% Figura
fig = figure('Visible', 'off', 'Position', [50 50 1500 800], 'Color', 'w');
for ip = 1:numel(patas)
    Dp = T(T.pata == patas(ip), :);  w = 2 * pi * Dp.f_hz;
    Pw = Dp.Pw_re + 1i * Dp.Pw_im;
    [~, ~, ~, ~, Pr] = planta_flexible(f, y_rig, patas(ip), v_bat(ip), w);
    [~, ~, ~, ~, Pf] = planta_flexible(f, y, patas(ip), v_bat(ip), w);
    subplot(2, 3, ip); hold on; grid on
    plot(Dp.f_hz, abs(Pw), 'o-', 'Color', [0.93 0.69 0.13], 'MarkerSize', 3, 'DisplayName', 'robot');
    plot(Dp.f_hz, abs(Pr), '-', 'Color', [0 0.45 0.74], 'DisplayName', 'rígido (11/11)');
    plot(Dp.f_hz, abs(Pf), '-', 'Color', [0.85 0.33 0.1], 'LineWidth', 1.4, 'DisplayName', 'con la pata y la reductora que ceden');
    set(gca, 'XScale', 'log'); xlim([1 20]); title(sprintf('patas %d°: |cabeceo / PWM|', patas(ip)));
    if ip == 1, ylabel('rad/s'); legend('Location', 'northeast'); end
    subplot(2, 3, 3 + ip); hold on; grid on
    plot(Dp.f_hz, rad2deg(unwrap(angle(Pw))), 'o-', 'Color', [0.93 0.69 0.13], 'MarkerSize', 3);
    plot(Dp.f_hz, rad2deg(unwrap(angle(Pr))), '-', 'Color', [0 0.45 0.74]);
    plot(Dp.f_hz, rad2deg(unwrap(angle(Pf))), '-', 'Color', [0.85 0.33 0.1], 'LineWidth', 1.4);
    set(gca, 'XScale', 'log'); xlim([1 20]); xlabel('Hz'); title('fase [°] (con el retardo)');
end
sgtitle(sprintf(['Lo que cede: la pata k_s %.1f N m/rad (modo %.1f / %.1f / %.1f Hz en 0 / 15 / 30°) y la reductora ' ...
    'k_g %.2f N m/rad (%.1f Hz); retardo %.1f ms'], y(1), filas(:, 4), y(5), filas(2, 2), 1e3 * y(4)));
exportgraphics(fig, fullfile(aqui, 'fig_pata_flexible.png'), 'Resolution', 110);
fprintf('-> fig_pata_flexible.png, pata_flexible.csv\n');

%% ------------------------------------------------------------------ funciones
function r = residuo(f, y, D, patas, v_bat)
    r = [];
    for ip = 1:numel(patas)
        Dp = D(D.pata == patas(ip), :);
        [~, ~, ~, ~, Pw, Pv] = planta_flexible(f, y, patas(ip), v_bat(ip), 2 * pi * Dp.f_hz);
        ew = log((Dp.Pw_re + 1i * Dp.Pw_im) ./ Pw);
        ev = log((Dp.Pv_re + 1i * Dp.Pv_im) ./ Pv);
        cw = sqrt(Dp.coh_w);  cv = sqrt(Dp.coh_v);
        r = [r; cw .* real(ew); cw .* imag(ew); cv .* real(ev); cv .* imag(ev)]; %#ok<AGROW>
    end
end

function [S, L] = sensibilidad(f, y, pata, V, fr, kf)
    % u = N1 N2 (kx x + kv v_f + kphi phi + kw w), con lo que mide el firmware: la IMU en la caja y la
    % odometría x = r (giro del encoder + phi), el encoder en el rotor respecto de la carcasa (alfa)
    [A, B] = planta_flexible(f, y, pata, V);
    r = 1e-3 * f.Rw;
    w = 2 * pi * fr(:);  s = 1i * w;
    N1 = notch_c(s, 11.6, 0.7);  N2 = notch_c(s, 7.7, 2);  Fv = (2 * pi * f.fc_vel) ./ (s + 2 * pi * f.fc_vel);
    L = zeros(size(s));
    for n = 1:numel(s)
        X = ((s(n) * eye(8) - A) \ B) * exp(-s(n) * y(4));
        xm = r * (X(4) + X(3));  vm = r * (X(8) + X(7));
        L(n) = -N1(n) * N2(n) * (kf(1) * xm + kf(2) * Fv(n) * vm + kf(3) * X(3) + kf(4) * X(7));
    end
    S = 1 ./ (1 + L);
end

function N = notch_c(s, f0, Q)
    w0 = 2 * pi * f0;
    N = (s.^2 + w0^2) ./ (s.^2 + w0 / Q * s + w0^2);
end

function v = armar(v, libre, z)
    v(libre) = z;
end

function [A, B, M, info, Pw, Pv] = planta_flexible(f, y, pata, V, w)
    % q = [x; phi1 (la pata); phi2 (la caja); alfa (el rotor respecto de la pata, visto del lado de la rueda)],
    % positivos hacia adelante; u en fracción de PWM
    p = parametros_pendulo_invertido(f, pata + f.pata_cero);
    [p, mot] = motor_pendulo_invertido(p, f);
    P = p.piezas;
    pata_i = ismember(P.nombre, {'manivelas AD', 'balancines BC', 'acopladores CDP', 'carcasas de motores'});
    rP = p.r_P_A;
    % el equilibrio: el centro de masa del cuerpo sobre el eje (se gira todo hasta que quede vertical)
    gv = p.r_G_A - rP;
    d = atan2(gv(1), gv(2));
    R = [cos(d), -sin(d); sin(d), cos(d)];
    grupos = {pata_i, ~pata_i};
    m = zeros(1, 2);  z = m;  j = m;  l = m;
    for g = 1:2
        sg = grupos{g};
        mg = sum(P.masa_kg(sg));
        pos = ([P.x_A_m(sg), P.y_A_m(sg)] - rP) * R';
        cg = sum(P.masa_kg(sg) .* pos, 1) / mg;
        Jg = sum(P.inercia_propia_kgm2(sg) + P.masa_kg(sg) .* sum((pos - cg).^2, 2));
        if g == 2 && isfield(f, 'J_extra'), Jg = Jg + f.J_extra; end
        m(g) = mg;  z(g) = cg(2);  l(g) = norm(cg);  j(g) = Jg + mg * l(g)^2;
    end
    h = m .* z;  k = m .* p.g .* z;
    n = mot.n_g;  Jr = mot.n_motores * f.J_r;
    vr = [0; 1; 0; n];                                  % el giro absoluto del rotor
    M = [p.m_total + p.J_ruedas / p.r^2, h(1), h(2), 0; h(1), j(1), 0, 0; h(2), 0, j(2), 0; 0 0 0 0] + Jr * (vr * vr');
    ks = y(1);  cs = y(2);  kg = y(5);  cg_ = y(6);
    gg = [-1 / p.r; 1; 0; 1];                           % alfa - giro de la rueda respecto de la pata
    gs = [0; -1; 1; 0];                                 % phi2 - phi1
    b = p.b_eje + y(3);                                 % contraelectromotriz (ya en p.b_eje) + roce, en el rotor
    Dm = cs * (gs * gs') + cg_ * (gg * gg') + diag([0, 0, p.b_phi, b]);
    Km = ks * (gs * gs') + kg * (gg * gg') - diag([0, k(1), k(2), 0]);
    H = [0; 0; 0; 1] * mot.beta_V * V;
    A = [zeros(4), eye(4); -M \ Km, -M \ Dm];
    B = [zeros(4, 1); M \ H];
    info = struct('m1', m(1), 'm2', m(2), 'l1', l(1), 'l2', l(2), 'j1', j(1) - m(1) * l(1)^2, 'j2', j(2) - m(2) * l(2)^2);
    Pw = [];  Pv = [];
    if nargin >= 5
        s = 1i * w(:);  Pw = zeros(size(s));  Pv = Pw;
        for n = 1:numel(s)
            X = (s(n) * eye(8) - A) \ B;
            Pw(n) = X(7);  Pv(n) = X(5);
        end
        dl = exp(-s * y(4));
        Pw = Pw .* dl;  Pv = Pv .* dl;
    end
end
