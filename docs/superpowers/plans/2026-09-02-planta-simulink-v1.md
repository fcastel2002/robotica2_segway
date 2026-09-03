# Planta Simulink v1 — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Planta Simulink del Segway con patas con actuadores eléctricos, reductor, servo, deslizamiento, sensores y controlador discreto, más 16 escenarios de prueba en dos variantes de robot.

**Architecture:** Funciones `.m` puras (aptas para MATLAB Function y `ode15s`) con una sola fuente de verdad por ecuación; Simulink solo las conecta. Dinámica del cuerpo deducida simbólicamente y generada a archivo. Controlador discreto con estados `persistent`.

**Tech Stack:** MATLAB R2023b, Simulink, Symbolic Math Toolbox, Control System Toolbox (`lqr`), MATLAB unit tests (`functiontests`). Ejecución vía MCP `matlab` (`run_matlab_test_file`, `evaluate_matlab_code`).

**Spec:** `docs/superpowers/specs/2026-09-02-planta-simulink-v1-design.md`

## Global Constraints

- Unidades SI internas (m, kg, s, rad, V, A). Parámetros de entrada en mm/g/grados solo dentro de `parametros_v1`.
- `simulacion/modelo_base/` (zip del grupo) no se modifica; se usa vía `addpath` (`cinematica_pata`, `barrido_pata`, `dinamica_sl`, `params_robot`, `empaquetar`).
- Todo el código nuevo va en `simulacion/planta_v1/`; tests en `simulacion/planta_v1/tests/`.
- Estado continuo fijo de 16 elementos; `pv` de 124 doubles con los índices de `empaquetar_v1`.
- Variantes: `'cad'` (AB 80 mm a 47.5°, N = 100, sin encoder) y `'corregido'` (AB 100 mm a 45°, N = 21.3, con encoder).
- No se hacen commits automáticos; el usuario decide cuándo commitear.
- Cada test se corre con `runtests('simulacion/planta_v1/tests/<archivo>.m')` desde la raíz del repo, o con el MCP `run_matlab_test_file`.

---

### Task 1: Parámetros y empaquetado

**Files:**
- Create: `simulacion/planta_v1/parametros_v1.m`
- Create: `simulacion/planta_v1/empaquetar_v1.m`
- Create: `simulacion/planta_v1/interp_lin.m`
- Test: `simulacion/planta_v1/tests/test_parametros_v1.m`

**Interfaces:**
- Consumes: `barrido_pata(P, n)` y `cinematica_pata(P, theta)` de `modelo_base` (usan `P.A, P.B, P.AD, P.BC, P.CD, P.DP, P.delta, P.rama, P.th, P.Rw, P.chasis.yc, P.chasis.alto, P.m.total`).
- Produces: `P = parametros_v1(variante, 'nombre', valor, ...)` con campos `P.din.{m_b,m_w,J_b,J_w,r_com,l_min,l_max,l0,G}`, `P.tab.{l,th,dthdl}` (21 puntos), `P.motor.*`, `P.rueda.*`, `P.bat.*`, `P.servo.*`, `P.cuerpo.*`, `P.sens.*`, `P.ctrl.*`, `P.cinematica` (salida de `barrido_pata`); `pv = empaquetar_v1(P, C)` (124×1); `y = interp_lin(xt, yt, x)`.

- [ ] **Step 1: Escribir el test**

```matlab
function tests = test_parametros_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_cad_cierra_y_masas(tc)
  P = parametros_v1('cad');
  tc.verifyTrue(P.cinematica.ok);
  tc.verifyEqual(P.AD, 0.140, 'AbsTol', 1e-9); tc.verifyEqual(P.AB, 0.080, 'AbsTol', 1e-9);
  tc.verifyGreaterThan(P.din.m_b, 0.70); tc.verifyLessThan(P.din.m_b, 0.80);
  tc.verifyEqual(P.din.m_w, 0.250, 'AbsTol', 1e-6);
  tc.verifyGreaterThan(P.din.l_max - P.din.l_min, 0.095); tc.verifyLessThan(P.din.l_max - P.din.l_min, 0.110);
  tc.verifyEqual(P.din.G, 0.198, 'AbsTol', 0.012);
  tc.verifyTrue(all(P.tab.dthdl < 0));
  tc.verifyTrue(issorted(P.tab.l));
end
function test_corregido_recta(tc)
  P = parametros_v1('corregido');
  tc.verifyLessThan(P.cinematica.desvio, 1.5e-3);
  P2 = parametros_v1('cad'); tc.verifyGreaterThan(P2.cinematica.desvio, 5e-3);
  tc.verifyEqual(P.motor.N, 21.3); tc.verifyTrue(P.sens.encoder);
end
function test_empaquetar(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P);
  tc.verifyEqual(numel(pv), 124); tc.verifyEqual(pv(18), 100); tc.verifyEqual(pv(61), 21);
  tc.verifyEqual(pv(62), P.din.l_min, 'AbsTol', 1e-12);
  tc.verifyEqual(pv(51:60), zeros(10,1));
end
function test_overrides(tc)
  P = parametros_v1('cad', 'V_bat', 9.6, 'gear_rigido', false);
  tc.verifyEqual(P.bat.V, 9.6); tc.verifyFalse(P.motor.gear_rigido);
  tc.verifyError(@() parametros_v1('cad','no_existe',1), ?MException);
end
function test_interp_lin(tc)
  xt = [0 1 2]'; yt = [0 10 40]';
  tc.verifyEqual(interp_lin(xt, yt, 0.5), 5, 'AbsTol', 1e-12);
  tc.verifyEqual(interp_lin(xt, yt, 1.5), 25, 'AbsTol', 1e-12);
  tc.verifyEqual(interp_lin(xt, yt, 3), 70, 'AbsTol', 1e-12);   % extrapola
  tc.verifyEqual(interp_lin(xt, yt, -1), -10, 'AbsTol', 1e-12);
end
```

- [ ] **Step 2: Correr el test y verificar que falla** (función no definida).

- [ ] **Step 3: Escribir `interp_lin.m`**

```matlab
function y = interp_lin(xt, yt, x)
%INTERP_LIN  Interpolacion lineal con extrapolacion, apta para codegen. xt creciente.
%#codegen
  n = numel(xt);
  k = 1;
  if x >= xt(n)
    k = n - 1;
  elseif x > xt(1)
    while k < n - 1 && xt(k+1) < x
      k = k + 1;
    end
  end
  t = (x - xt(k))/(xt(k+1) - xt(k));
  y = yt(k) + t*(yt(k+1) - yt(k));
end
```

- [ ] **Step 4: Escribir `parametros_v1.m`**

```matlab
function P = parametros_v1(variante, varargin)
%PARAMETROS_V1  Unica fuente de parametros de la planta v1 (SI internamente).
%   P = parametros_v1('cad')         robot tal como esta en el CAD primera_iteracion
%   P = parametros_v1('corregido')   bancada 100 mm a 45 grados, motor 280 rpm con encoder
%   P = parametros_v1('cad','V_bat',9.6,'mu',0.3,'gear_rigido',false)
%   Los nombres admitidos son los campos de la estructura o (ver abajo).
  if nargin < 1 || isempty(variante), variante = 'cad'; end
  mm = 1e-3; gr = 1e-3; d2r = pi/180;

  % ---------- geometria del cuatro barras (mm, grados) ----------
  o.s_barras = 100;
  o.k_AD = 1.400; o.k_BC = 1.350; o.k_CD = 0.510; o.k_DP = 1.400;
  o.delta = 164; o.th = [320 350]; o.rama = +1;
  o.Rw = 33;
  switch lower(variante)
    case 'cad'
      o.AB = 80;  o.ang_AB = 47.5; o.N = 100;  o.encoder = false;
      o.nombre_motor = 'JGA25-370 12V 60rpm (1:100, sin encoder)';
    case 'corregido'
      o.AB = 100; o.ang_AB = 45;   o.N = 21.3; o.encoder = true;
      o.nombre_motor = 'JGA25-371 12V 280rpm (1:21.3, con encoder)';
    otherwise
      error('parametros_v1: variante "%s" no definida', variante);
  end
  % ---------- masas [g], CoM respecto de A [mm] (x atras, y arriba), inercias propias [kg m2] ----------
  o.m_cabina = 207;   o.r_cabina = [13.1 5.0];   o.J_cabina = 4.8477e8*1.2e-12;
  o.m_tapa = 114;     o.r_tapa = [-28.1 47.2];   o.J_tapa = 2.7331e8*1.2e-12;
  o.m_servo = 60;     o.r_servo = [-9.7 0];
  o.m_bateria = 120;  o.r_bateria = [-18.5 21.0];
  o.m_electronica = 60; o.r_electronica = [-18.5 21.0];
  o.m_tornilleria = 50; o.r_tornilleria = [0 0];
  o.m_AD = 29;    o.f_AD = 0.428;    o.J_AD = 6.4467e7*1.1e-12;    % f: fraccion del CoM de A hacia D
  o.m_BC = 7;     o.f_BC = 0.5;      o.J_BC = 1.5631e7*1.1e-12;
  o.m_CDP = 19.5; o.f_CDP = 0.3145;  o.J_CDP = 5.8125e7*1.1e-12;  % f: de D hacia P
  o.m_rueda = 30; o.m_motor = 95;
  % ---------- rueda y contacto ----------
  o.b_w = 1e-4; o.mu = 0.7; o.v_s = 0.005; o.c_v = 0.5;
  % ---------- motor DC + reductor ----------
  o.R_m = 5.45; o.L_m = 1.5e-3; o.w_nl_motor_rpm = 6000; o.J_r = 6e-7;
  o.tau_c = 0.0015; o.b_m = 1e-6;
  o.gear_rigido = true; o.k_g = 50; o.c_g = 0.05; o.juego_deg = 1.5;
  o.eta = 0.7;
  % ---------- bateria ----------
  o.V_bat = 11.1; o.R_bat = 0.05;
  % ---------- servo DS3225MG ----------
  o.tau_s_max = 2.4; o.w_nl_servo = 7.7; o.Kp_s = 45; o.Kd_s = 1.0; o.n_servos = 2;
  % ---------- cuerpo ----------
  o.b_pitch = 1e-3; o.b_pata = 8.0; o.k_tope = 2e4; o.c_tope = 60;
  % ---------- sensores y control ----------
  o.Ts = 5e-3; o.n_delay = 1; o.d_imu = [-18.5 21.0];
  o.gyro_bias_dps = 0.5; o.gyro_rms_dps = 0.1; o.gyro_sat_dps = 2000; o.acc_rms_g = 0.02;
  o.CPR_motor = 11; o.k_comp = 0.02; o.fc_vel = 20; o.semilla = 1;
  o.g = 9.81;
  % ---------- sobrescribir ----------
  for i = 1:2:numel(varargin)
    if ~isfield(o, varargin{i}), error('parametros_v1: parametro desconocido "%s"', varargin{i}); end
    o.(varargin{i}) = varargin{i+1};
  end
  P.variante = lower(variante); P.opciones = o; P.g = o.g;

  % ---------- geometria en SI ----------
  s = o.s_barras*mm;
  P.AB = o.AB*mm; P.ang_AB = o.ang_AB*d2r;
  P.AD = o.k_AD*s; P.BC = o.k_BC*s; P.CD = o.k_CD*s; P.DP = o.k_DP*s;
  P.delta = o.delta*d2r; P.rama = o.rama;
  P.A = [0 0]; P.B = P.AB*[cos(P.ang_AB) sin(P.ang_AB)];
  P.th = o.th*d2r; P.Rw = o.Rw*mm;
  P.chasis.yc = 0.021; P.chasis.alto = 0.1045;    % solo los usa barrido_pata para h_total
  P.m.total = 0;                                  % idem, par informativo
  K = barrido_pata(P, 121);
  if ~K.ok, error('parametros_v1: el cuatro barras no cierra en todo el recorrido'); end
  P.cinematica = K;

  % ---------- cuerpo suspendido: masa, CoM e inercia ----------
  v = K.valido;
  A_ = K.A(v,:); B_ = K.B(v,:); C_ = K.C(v,:); D_ = K.D(v,:); W_ = K.P(v,:);
  r_AD = A_ + o.f_AD*(D_ - A_); r_BC = (B_ + C_)/2; r_CDP = D_ + o.f_CDP*(W_ - D_);
  it = { o.m_cabina,      o.r_cabina*mm,      o.J_cabina;
         o.m_tapa,        o.r_tapa*mm,        o.J_tapa;
         2*o.m_servo,     o.r_servo*mm,       2*0.060*(0.040^2+0.0405^2)/12;
         o.m_bateria,     o.r_bateria*mm,     0.120*(0.100^2+0.035^2)/12;
         o.m_electronica, o.r_electronica*mm, 0.060*(0.080^2+0.040^2)/12;
         o.m_tornilleria, o.r_tornilleria*mm, 0;
         2*o.m_AD,        mean(r_AD,1),       2*o.J_AD;
         2*o.m_BC,        mean(r_BC,1),       2*o.J_BC;
         2*o.m_CDP,       mean(r_CDP,1),      2*o.J_CDP };
  mtot = 0; r = [0 0];
  for i = 1:size(it,1), m = it{i,1}*gr; mtot = mtot + m; r = r + m*it{i,2}; end
  r = r/mtot; J = 0;
  for i = 1:size(it,1), m = it{i,1}*gr; dd = it{i,2} - r; J = J + it{i,3} + m*(dd*dd'); end
  P.din.m_b = mtot; P.din.r_com = r; P.din.J_b = J;
  P.din.m_w = 2*(o.m_rueda + o.m_motor)*gr;
  P.din.J_w = 0.5*o.m_rueda*gr*P.Rw^2;
  P.m.total = P.din.m_b + P.din.m_w;

  % ---------- mapa theta <-> l (l = distancia eje de rueda -> CoM del cuerpo) ----------
  th = K.theta(v); ll = -W_(:,2) + r(2);
  P.din.l_min = min(ll); P.din.l_max = max(ll); P.din.l0 = (P.din.l_min + P.din.l_max)/2;
  [ll_s, iu] = sort(ll); th_s = th(iu);
  ntab = 21; P.tab.l = linspace(ll_s(1), ll_s(end), ntab)';
  P.tab.th = interp1(ll_s, th_s, P.tab.l, 'linear');
  P.tab.dthdl = gradient(P.tab.th, P.tab.l);
  P.din.G = mean(abs(1./P.tab.dthdl));
  P.din.h_tapa_sobre_A = 0.0745;

  % ---------- rueda, motor, bateria, servo, sensores en SI ----------
  P.rueda.b_w = o.b_w; P.rueda.mu = o.mu; P.rueda.v_s = o.v_s; P.rueda.c_v = o.c_v;
  P.motor.R = o.R_m; P.motor.L = o.L_m; P.motor.N = o.N; P.motor.J_r = o.J_r;
  P.motor.Ke = 12/(o.w_nl_motor_rpm*2*pi/60); P.motor.Kt = P.motor.Ke;
  P.motor.tau_c = o.tau_c; P.motor.b_m = o.b_m; P.motor.eta = o.eta; P.motor.nombre = o.nombre_motor;
  P.motor.gear_rigido = logical(o.gear_rigido); P.motor.k_g = o.k_g; P.motor.c_g = o.c_g; P.motor.juego = o.juego_deg*d2r;
  P.motor.w_nl_out = o.w_nl_motor_rpm*2*pi/60/o.N;
  P.bat.V = o.V_bat; P.bat.R = o.R_bat;
  P.servo.tau_max = o.tau_s_max; P.servo.w_nl = o.w_nl_servo; P.servo.Kp = o.Kp_s; P.servo.Kd = o.Kd_s; P.servo.n = o.n_servos;
  P.servo.th_min = min(P.th); P.servo.th_max = max(P.th);
  P.cuerpo.b_pitch = o.b_pitch; P.cuerpo.b_pata = o.b_pata; P.cuerpo.k_tope = o.k_tope; P.cuerpo.c_tope = o.c_tope;
  P.sens.Ts = o.Ts; P.sens.n_delay = o.n_delay; P.sens.encoder = logical(o.encoder);
  P.sens.CPR = o.CPR_motor*o.N*4;
  d = o.d_imu*mm - r;                              % respecto del CoM, (x atras, y arriba)
  P.sens.d_imu = [-d(1) d(2)];                     % marco cuerpo: x adelante, y arriba
  P.sens.gyro_bias = o.gyro_bias_dps*d2r; P.sens.gyro_rms = o.gyro_rms_dps*d2r; P.sens.gyro_sat = o.gyro_sat_dps*d2r;
  P.sens.acc_rms = o.acc_rms_g*o.g; P.sens.semilla = o.semilla;
  P.ctrl.k_comp = o.k_comp; P.ctrl.fc_vel = o.fc_vel;
  P.unidades = 'SI (m, kg, s, rad, V, A)';
end
```

- [ ] **Step 5: Escribir `empaquetar_v1.m`**

```matlab
function pv = empaquetar_v1(P, C)
%EMPAQUETAR_V1  Aplana P (y las ganancias C) en un vector de 124 doubles.
%    1 m_b   2 m_w   3 J_b   4 J_w   5 Rw   6 g   7 l_min   8 l_max
%    9 b_pitch  10 b_pata  11 b_w  12 k_tope  13 c_tope
%   14 R_m  15 L_m  16 Kt  17 Ke  18 N  19 J_r  20 b_m  21 tau_c
%   22 gear_rigido  23 k_g  24 c_g  25 juego  26 mu_defecto  27 v_s  28 c_v
%   29 V_bat  30 R_bat
%   31 tau_s_max  32 w_nl_servo  33 Kp_s  34 Kd_s  35 n_servos  36 th_min  37 th_max
%   38 d_imu_x  39 d_imu_y  40 Ts  41 encoder  42 CPR  43 gyro_bias  44 gyro_sat  45 gyro_rms  46 acc_rms
%   47 k_comp  48 fc_vel  49 eta  50 n_delay
%   51:54 K1  55:58 K2  59 lA  60 lB        K(l) = K1 + K2*l  (ceros si no hay C)
%   61 n_tab  62:82 l_tab  83:103 th_tab  104:124 dthdl_tab
  if nargin < 2, C = []; end
  pv = zeros(124,1);
  pv(1)=P.din.m_b; pv(2)=P.din.m_w; pv(3)=P.din.J_b; pv(4)=P.din.J_w; pv(5)=P.Rw; pv(6)=P.g;
  pv(7)=P.din.l_min; pv(8)=P.din.l_max;
  pv(9)=P.cuerpo.b_pitch; pv(10)=P.cuerpo.b_pata; pv(11)=P.rueda.b_w; pv(12)=P.cuerpo.k_tope; pv(13)=P.cuerpo.c_tope;
  pv(14)=P.motor.R; pv(15)=P.motor.L; pv(16)=P.motor.Kt; pv(17)=P.motor.Ke; pv(18)=P.motor.N;
  pv(19)=P.motor.J_r; pv(20)=P.motor.b_m; pv(21)=P.motor.tau_c;
  pv(22)=double(P.motor.gear_rigido); pv(23)=P.motor.k_g; pv(24)=P.motor.c_g; pv(25)=P.motor.juego;
  pv(26)=P.rueda.mu; pv(27)=P.rueda.v_s; pv(28)=P.rueda.c_v;
  pv(29)=P.bat.V; pv(30)=P.bat.R;
  pv(31)=P.servo.tau_max; pv(32)=P.servo.w_nl; pv(33)=P.servo.Kp; pv(34)=P.servo.Kd; pv(35)=P.servo.n;
  pv(36)=P.servo.th_min; pv(37)=P.servo.th_max;
  pv(38)=P.sens.d_imu(1); pv(39)=P.sens.d_imu(2); pv(40)=P.sens.Ts; pv(41)=double(P.sens.encoder); pv(42)=P.sens.CPR;
  pv(43)=P.sens.gyro_bias; pv(44)=P.sens.gyro_sat; pv(45)=P.sens.gyro_rms; pv(46)=P.sens.acc_rms;
  pv(47)=P.ctrl.k_comp; pv(48)=P.ctrl.fc_vel; pv(49)=P.motor.eta; pv(50)=P.sens.n_delay;
  if ~isempty(C)
    pv(51:54)=C.Kfit(1,:).'; pv(55:58)=C.Kfit(2,:).'; pv(59)=C.l_lim(1); pv(60)=C.l_lim(2);
  end
  n = numel(P.tab.l); pv(61)=n;
  pv(62:62+n-1)=P.tab.l; pv(83:83+n-1)=P.tab.th; pv(104:104+n-1)=P.tab.dthdl;
end
```

- [ ] **Step 6: Correr el test y verificar que pasa.** Si `test_cad_cierra_y_masas` falla por `G` o por la carrera, imprimir `P.din` y ajustar la tolerancia solo si el valor real es coherente con el informe del CAD (G ≈ 0.198, carrera ≈ 0.1035).

---

### Task 2: Dinámica del cuerpo por Lagrange

**Files:**
- Create: `simulacion/planta_v1/derivar_dinamica_v1.m`
- Create (generado): `simulacion/planta_v1/dinamica_v1_gen.m`
- Test: `simulacion/planta_v1/tests/test_dinamica_v1.m`

**Interfaces:**
- Produces: `[M, C, Gv] = dinamica_v1_gen(phi, l, dphi, dl, m_b, m_w, J_b, g, alpha)` con `M` 3×3, `C` 3×1 (Coriolis+centrífugo), `Gv` 3×1 (gravedad, con pendiente `alpha`), coordenadas `q = [x; phi; l]`.

- [ ] **Step 1: Escribir el test**

```matlab
function tests = test_dinamica_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_coincide_con_modelo_base(tc)
  Pz = params_robot('s', 80, 'Dw', 80); pvz = empaquetar(Pz);
  rng(3);
  for k = 1:50
    q = [randn; 0.3*randn; Pz.din.l0 + 0.02*randn]; qd = 0.5*randn(3,1); u = [0.2*randn; 0.5*randn];
    qdd_z = dinamica_sl(q, qd, u, pvz);
    [M, C, Gv] = dinamica_v1_gen(q(2), q(3), qd(2), qd(3), Pz.din.m_b, Pz.din.m_w, Pz.din.J_b, Pz.g, 0);
    G = Pz.din.Gfit(1) + Pz.din.Gfit(2)*q(3);
    M(1,1) = M(1,1) + Pz.din.J_w/Pz.Rw^2;
    DD = [Pz.b.rueda/Pz.Rw^2*qd(1); Pz.b.pitch*qd(2); Pz.b.pata*qd(3)];
    QQ = [u(1)/Pz.Rw; -u(1); u(2)/G];
    qdd = M \ (QQ - C - Gv - DD);
    tc.verifyEqual(qdd, qdd_z, 'RelTol', 1e-9, 'AbsTol', 1e-9);
  end
end
function test_pendiente(tc)
  m_b = 0.75; m_w = 0.25; g = 9.81; alpha = 0.1;
  [~, ~, Gv] = dinamica_v1_gen(0, 0.15, 0, 0, m_b, m_w, 3e-3, g, alpha);
  tc.verifyEqual(Gv(1), (m_b + m_w)*g*sin(alpha), 'RelTol', 1e-12);
  tc.verifyEqual(Gv(2), m_b*g*0.15*sin(alpha), 'RelTol', 1e-12);      % -m_b g l sin(phi+alpha) con phi=0 -> signo
  tc.verifyEqual(Gv(3), m_b*g*cos(alpha), 'RelTol', 1e-12);
end
```

Nota sobre el signo de `Gv(2)` en `test_pendiente`: con `V = m_b g (sin α (x + l sin φ) + cos α l cos φ)`, `∂V/∂φ = m_b g l (sin α cos φ − cos α sin φ) = −m_b g l sin(φ − α)`; en φ = 0 vale `+m_b g l sin α`. Si el test falla por signo, revisar la deducción y no el test.

- [ ] **Step 2: Correr el test y verificar que falla** (`dinamica_v1_gen` no existe).

- [ ] **Step 3: Escribir `derivar_dinamica_v1.m` y ejecutarlo una vez**

```matlab
function derivar_dinamica_v1()
%DERIVAR_DINAMICA_V1  Deduce por Lagrange las ecuaciones del cuerpo y genera dinamica_v1_gen.m.
%   q = [x; phi; l]. Piso con pendiente alpha: x a lo largo del piso, phi desde la normal al piso.
%   Se corre una sola vez; el archivo generado se versiona.
  syms x phi l dx dphi dl m_b m_w J_b g alpha real
  q = [x; phi; l]; dq = [dx; dphi; dl];
  r_w = [x; 0];
  r_b = [x + l*sin(phi); l*cos(phi)];
  v_b = jacobian(r_b, q)*dq;
  T = m_w*dx^2/2 + m_b*(v_b.'*v_b)/2 + J_b*dphi^2/2;
  gvec = g*[-sin(alpha); -cos(alpha)];
  V = -m_b*(gvec.'*r_b) - m_w*(gvec.'*r_w);
  M = simplify(hessian(T, dq));
  n = 3; C = sym(zeros(n,1));
  for i = 1:n
    for j = 1:n
      for k = 1:n
        C(i) = C(i) + (diff(M(i,j),q(k)) + diff(M(i,k),q(j)) - diff(M(j,k),q(i)))/2*dq(j)*dq(k);
      end
    end
  end
  C = simplify(C);
  Gv = simplify(jacobian(V, q).');
  aqui = fileparts(mfilename('fullpath'));
  matlabFunction(M, C, Gv, 'File', fullfile(aqui, 'dinamica_v1_gen.m'), ...
     'Vars', {phi, l, dphi, dl, m_b, m_w, J_b, g, alpha}, 'Outputs', {'M','C','Gv'}, 'Optimize', false);
  fprintf('dinamica_v1_gen.m generado en %s\n', aqui);
end
```

Ejecutar: `derivar_dinamica_v1()` desde MATLAB con `simulacion/planta_v1` en el path.

- [ ] **Step 4: Correr el test y verificar que pasa.**

---

### Task 3: Motor DC con reductor

**Files:**
- Create: `simulacion/planta_v1/motor_lado.m`
- Test: `simulacion/planta_v1/tests/test_motor_v1.m`

**Interfaces:**
- Produces: `[tau_g, dwm, di, i_eff, J_add] = motor_lado(V, i, wm, thm, ww, thw, pv)`: par sobre la rueda, derivada de la velocidad del rotor, derivada de la corriente, corriente efectiva (algebraica si `L_m = 0`), inercia a sumar a la rueda (`N²·J_r` si rígido, 0 si elástico).

- [ ] **Step 1: Escribir el test**

```matlab
function tests = test_motor_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_bloqueo(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P); pv(15) = 0;   % L = 0 -> corriente algebraica
  [tau_g, dwm, di, i, J_add] = motor_lado(12, 0, 0, 0, 0, 0, pv);
  tc.verifyEqual(i, 12/P.motor.R, 'RelTol', 1e-9);
  tc.verifyEqual(tau_g, P.motor.N*P.motor.Kt*12/P.motor.R, 'RelTol', 1e-9);
  tc.verifyEqual(dwm, 0); tc.verifyEqual(di, 0);
  tc.verifyEqual(J_add, P.motor.N^2*P.motor.J_r, 'RelTol', 1e-12);
end
function test_vacio(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P); pv(15) = 0;
  J_eq = P.din.J_w + P.motor.N^2*P.motor.J_r;
  f = @(~, z) dz_vacio(z, pv, J_eq, P.rueda.b_w);
  [~, Z] = ode15s(f, [0 3], 0, odeset('RelTol',1e-6));
  w_fin = Z(end);
  tc.verifyGreaterThan(w_fin, 0.90*P.motor.w_nl_out);
  tc.verifyLessThan(w_fin, 1.00*P.motor.w_nl_out);
end
function test_elastico_transmite(tc)
  P = parametros_v1('cad', 'gear_rigido', false); pv = empaquetar_v1(P);
  e = 2*P.motor.juego;                                   % rotor adelantado mas alla del juego
  [tau_g, dwm, ~, ~, J_add] = motor_lado(0, 0, 0, e*P.motor.N, 0, 0, pv);
  tc.verifyEqual(tau_g, P.motor.k_g*(e - P.motor.juego/2), 'RelTol', 1e-9);
  tc.verifyLessThan(dwm, 0);                              % el resorte frena al rotor
  tc.verifyEqual(J_add, 0);
  [tau_g0] = motor_lado(0, 0, 0, 0.2*P.motor.juego*P.motor.N, 0, 0, pv);
  tc.verifyEqual(tau_g0, 0, 'AbsTol', 1e-12);             % dentro del juego no transmite
end
function dz = dz_vacio(z, pv, J_eq, b_w)
  ww = z(1);
  tau_g = motor_lado(12, 0, pv(18)*ww, 0, ww, 0, pv);
  dz = (tau_g - b_w*ww)/J_eq;
end
```

- [ ] **Step 2: Correr el test y verificar que falla.**

- [ ] **Step 3: Escribir `motor_lado.m`**

```matlab
function [tau_g, dwm, di, i_eff, J_add] = motor_lado(V, i, wm, thm, ww, thw, pv)
%MOTOR_LADO  Motor DC + reductor de un lado: par sobre la rueda y derivadas del rotor y la corriente.
%   V tension aplicada [V], i corriente [A], wm/thm velocidad y angulo del rotor (lado motor),
%   ww/thw velocidad y angulo de la rueda. Con pv(22)=1 el reductor es rigido (rotor unido a la rueda,
%   inercia N^2*J_r devuelta en J_add); con 0 hay eje elastico con juego.
%#codegen
  R_m=pv(14); L_m=pv(15); Kt=pv(16); Ke=pv(17); N=pv(18); J_r=pv(19); b_m=pv(20); tau_c=pv(21);
  rigido = pv(22) > 0.5; k_g=pv(23); c_g=pv(24); juego=pv(25);
  if rigido, wm = N*ww; end
  if L_m <= 0
    i_eff = (V - Ke*wm)/R_m; di = 0;
  else
    i_eff = i; di = (V - R_m*i - Ke*wm)/L_m;
  end
  tau_e = Kt*i_eff;
  tau_fr = tau_c*tanh(wm/0.5) + b_m*wm;
  if rigido
    tau_g = N*(tau_e - tau_fr); dwm = 0; J_add = N^2*J_r;
  else
    e = thm/N - thw;
    dz = sign(e)*max(0, abs(e) - juego/2);
    tau_g = k_g*dz + c_g*(wm/N - ww);
    dwm = (tau_e - tau_fr - tau_g/N)/J_r; J_add = 0;
  end
end
```

- [ ] **Step 4: Correr el test y verificar que pasa.**

---

### Task 4: Planta continua completa

**Files:**
- Create: `simulacion/planta_v1/planta_sl.m`
- Test: `simulacion/planta_v1/tests/test_planta_v1.m`

**Interfaces:**
- Consumes: `dinamica_v1_gen`, `motor_lado`, `interp_lin`.
- Produces: `[Xdot, y] = planta_sl(X, u, d, pv)` con `X` 16×1 = `[x phi l dx dphi dl thwL wwL thwR wwR thmL wmL thmR wmR iL iR]`, `u` = `[V_L; V_R; th_ref]`, `d` = `[F_x; M_p; alpha; mu; F_esc]`, `y` 16×1 = `[ddx ddphi ddl N_tot f_L f_R desliza tau_gL tau_gR tau_s th_s i_L i_R V_bus fb_x fb_y]`.

- [ ] **Step 1: Escribir el test**

```matlab
function tests = test_planta_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_tamanos(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P);
  X = zeros(16,1); X(3) = P.din.l0;
  [Xdot, y] = planta_sl(X, [0;0;interp_lin(P.tab.l,P.tab.th,P.din.l0)], [0;0;0;0.7;0], pv);
  tc.verifyEqual(size(Xdot), [16 1]); tc.verifyEqual(size(y), [16 1]);
  tc.verifyTrue(all(isfinite(Xdot)));
end
function test_servo_sostiene_el_peso(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P);
  l = P.din.l0; th = interp_lin(P.tab.l, P.tab.th, l); dthdl = interp_lin(P.tab.l, P.tab.dthdl, l);
  tau_nec = P.din.m_b*P.g/(P.servo.n*abs(dthdl));       % par por servo para sostener el cuerpo
  tc.verifyLessThan(tau_nec, P.servo.tau_max);
  X = zeros(16,1); X(3) = l;
  th_ref = th + sign(dthdl)*(-tau_nec)/P.servo.Kp;       % error que produce exactamente tau_nec con el signo correcto
  [Xdot, y] = planta_sl(X, [0;0;th_ref], [0;0;0;0.7;0], pv);
  tc.verifyEqual(Xdot(6), 0, 'AbsTol', 1e-6);            % ddl = 0: el servo sostiene
  tc.verifyEqual(abs(y(10)), tau_nec, 'RelTol', 1e-6);
  [Xdot2] = planta_sl(X, [0;0;th], [0;0;0;0.7;0], pv);
  tc.verifyLessThan(Xdot2(6), 0);                         % sin error el cuerpo baja
end
function test_imu_en_reposo(tc)
  P = parametros_v1('cad'); pv = empaquetar_v1(P);
  phi = 0.2; l = P.din.l0; th = interp_lin(P.tab.l, P.tab.th, l); dthdl = interp_lin(P.tab.l, P.tab.dthdl, l);
  tau_nec = P.din.m_b*P.g*cos(phi)/(P.servo.n*abs(dthdl));
  th_ref = th + sign(dthdl)*(-tau_nec)/P.servo.Kp;
  X = zeros(16,1); X(2) = phi; X(3) = l;
  M_p = P.din.m_b*P.g*l*sin(phi);                         % compensa la gravedad en phi
  [Xdot, y] = planta_sl(X, [0;0;th_ref], [0;M_p;0;0.7;0], pv);
  tc.verifyEqual(Xdot(4:6), zeros(3,1), 'AbsTol', 1e-6);   % reposo
  tc.verifyEqual(atan2(-y(15), y(16)), phi, 'AbsTol', 1e-6);
  tc.verifyEqual(hypot(y(15), y(16)), P.g, 'RelTol', 1e-9);
end
function test_rodadura_vs_modelo_base(tc)
  % con reductor rigido, J_r = 0, L = 0, sin friccion y contacto muy rigido, la planta reproduce
  % la dinamica de modelo_base con el mismo par de rueda en lazo abierto.
  P = parametros_v1('cad', 'J_r', 0, 'L_m', 0, 'tau_c', 0, 'b_m', 0, 'b_w', 0, 'mu', 5, 'v_s', 1e-4, 'c_v', 0);
  pv = empaquetar_v1(P);
  Pz = params_robot('s', 80, 'Dw', 66);
  Pz.din.m_b = P.din.m_b; Pz.din.m_w = P.din.m_w; Pz.din.J_b = P.din.J_b; Pz.din.J_w = P.din.J_w;
  Pz.b.rueda = 0; Pz.b.pitch = P.cuerpo.b_pitch; Pz.b.pata = P.cuerpo.b_pata;
  Pz.din.l_min = P.din.l_min; Pz.din.l_max = P.din.l_max;
  pvz = empaquetar(Pz);
  V = 2; N = P.motor.N; Kt = P.motor.Kt; Ke = P.motor.Ke; R = P.motor.R; Rw = P.Rw;
  l = P.din.l0; th = interp_lin(P.tab.l, P.tab.th, l); dthdl = interp_lin(P.tab.l, P.tab.dthdl, l);
  tau_nec = P.din.m_b*P.g/(P.servo.n*abs(dthdl)); th_ref = th + sign(dthdl)*(-tau_nec)/P.servo.Kp;
  X0 = zeros(16,1); X0(2) = 0.05; X0(3) = l;
  opts = odeset('RelTol',1e-7,'AbsTol',1e-9,'MaxStep',1e-3);
  [~, Xa] = ode15s(@(t,X) planta_sl(X, [V;V;th_ref], [0;0;0;5;0], pv), [0 0.2], X0, opts);
  % modelo_base: mismo par de rueda tau = 2*N*Kt*(V - Ke*N*dx/Rw)/R, mismo servo (fuerza fija en l)
  f = @(t,Z) campo_z(Z, V, N, Kt, Ke, R, Rw, P, pvz, tau_nec, dthdl);
  [~, Za] = ode15s(f, [0 0.2], [0; 0.05; l; 0; 0; 0], opts);
  tc.verifyEqual(Xa(end,1:2), Za(end,1:2), 'RelTol', 0.02, 'AbsTol', 1e-3);
end
function dZ = campo_z(Z, V, N, Kt, Ke, R, Rw, P, pvz, tau_nec, dthdl)
  q = Z(1:3); qd = Z(4:6);
  tau = 2*N*Kt*(V - Ke*N*qd(1)/Rw)/R;
  % el servo de la planta v1 con el mismo error da la misma fuerza: usamos u2 tal que u2/G = F_l
  G = pvz(7) + pvz(8)*q(3);
  F_l = P.servo.n*tau_nec*abs(dthdl)*0 + P.din.m_b*P.g;    % en t=0 sostiene exactamente el peso
  qdd = dinamica_sl(q, qd, [tau; F_l*G], pvz);
  dZ = [qd; qdd];
end
```

Nota para `test_rodadura_vs_modelo_base`: el servo de v1 es un lazo P-D que no mantiene la fuerza exactamente constante cuando `l` se mueve; por eso se compara solo `x` y `phi` a los 0.2 s con 2 % de tolerancia, y `l` no se compara. Si la diferencia es mayor, subir `Kp_s` en el test (`parametros_v1(..., 'Kp_s', 4500, 'Kd_s', 100)`) para que el servo sea casi una posición fija, y volver a comparar.

- [ ] **Step 2: Correr el test y verificar que falla.**

- [ ] **Step 3: Escribir `planta_sl.m`**

```matlab
function [Xdot, y] = planta_sl(X, u, d, pv)
%PLANTA_SL  Derivada del estado de la planta completa (cuerpo + ruedas + motores + servo).
%   X (16) = [x phi l dx dphi dl thwL wwL thwR wwR thmL wmL thmR wmR iL iR]
%   u (3)  = [V_L V_R th_ref]      d (5) = [F_x M_p alpha mu F_esc]
%   y (16) = [ddx ddphi ddl N_tot f_L f_R desliza tau_gL tau_gR tau_s th_s i_L i_R V_bus fb_x fb_y]
%   Marco: x a lo largo del piso (+ adelante), phi desde la normal al piso (+ adelante),
%   l = distancia eje de rueda -> CoM del cuerpo. fb = fuerza especifica en la IMU, marco cuerpo
%   (x adelante, y hacia arriba de la pata); el angulo del acelerometro es atan2(-fb_x, fb_y).
%#codegen
  m_b=pv(1); m_w=pv(2); J_b=pv(3); J_w=pv(4); Rw=pv(5); g=pv(6); l_min=pv(7); l_max=pv(8);
  b_pitch=pv(9); b_pata=pv(10); b_w=pv(11); k_tope=pv(12); c_tope=pv(13);
  mu_def=pv(26); v_s=pv(27); c_v=pv(28); V_bat=pv(29); R_bat=pv(30);
  tau_s_max=pv(31); w_nl_s=pv(32); Kp_s=pv(33); Kd_s=pv(34); n_serv=pv(35);
  d_ix=pv(38); d_iy=pv(39);
  n = round(pv(61)); l_tab = pv(62:62+n-1); th_tab = pv(83:83+n-1); dthdl_tab = pv(104:104+n-1);

  phi=X(2); l=X(3); dx=X(4); dphi=X(5); dl=X(6);
  thwL=X(7); wwL=X(8); thwR=X(9); wwR=X(10); thmL=X(11); wmL=X(12); thmR=X(13); wmR=X(14); iL=X(15); iR=X(16);
  th_ref=u(3); F_x=d(1); M_p=d(2); alpha=d(3); mu=d(4); F_esc=d(5);
  if mu <= 0, mu = mu_def; end
  if l < 1e-3, l = 1e-3; end
  c = cos(phi); s = sin(phi);

  % --- bateria y motores ---
  V_bus = max(V_bat - R_bat*(abs(iL) + abs(iR)), 0);
  V_L = max(min(u(1), V_bus), -V_bus); V_R = max(min(u(2), V_bus), -V_bus);
  [tau_gL, dwmL, diL, iL_eff, J_add] = motor_lado(V_L, iL, wmL, thmL, wwL, thwL, pv);
  [tau_gR, dwmR, diR, iR_eff, ~]     = motor_lado(V_R, iR, wmR, thmR, wwR, thwR, pv);
  J_eq = J_w + J_add;

  % --- servo: fuerza sobre l a traves del cuatro barras ---
  th_s = interp_lin(l_tab, th_tab, l);
  dthdl = interp_lin(l_tab, dthdl_tab, l);
  dth_s = dthdl*dl;
  tau_cmd = Kp_s*(th_ref - th_s) - Kd_s*dth_s;
  if tau_cmd*dth_s > 0
    lim = tau_s_max*max(0, 1 - abs(dth_s)/w_nl_s);
  else
    lim = tau_s_max;
  end
  tau_s = max(min(tau_cmd, lim), -lim);
  F_l = n_serv*tau_s*dthdl;
  f_tope = 0;
  if l < l_min, f_tope = k_tope*(l_min - l) - c_tope*dl; end
  if l > l_max, f_tope = k_tope*(l_max - l) - c_tope*dl; end

  % --- cuerpo: dos pasadas para la normal ---
  [M, C, Gv] = dinamica_v1_gen(phi, l, dphi, dl, m_b, m_w, J_b, g, alpha);
  N_tot = (m_w + m_b)*g*cos(alpha);
  qdd = zeros(3,1); f_L = 0; f_R = 0; dwwL = 0; dwwR = 0; ay_com = 0;
  for pasada = 1:2
    N_i = max(N_tot, 0)/2;
    vsL = Rw*wwL - dx; vsR = Rw*wwR - dx;
    f_L = mu*N_i*tanh(vsL/v_s) - c_v*vsL;
    f_R = mu*N_i*tanh(vsR/v_s) - c_v*vsR;
    dwwL = (tau_gL - Rw*f_L - b_w*wwL)/J_eq;
    dwwR = (tau_gR - Rw*f_R - b_w*wwR)/J_eq;
    Q = [ f_L + f_R + F_x + F_esc;
         -(tau_gL + tau_gR) + M_p + F_x*l*c - b_pitch*dphi;
          F_l + F_x*s - b_pata*dl + f_tope ];
    qdd = M \ (Q - C - Gv);
    ay_com = qdd(3)*c - 2*dl*dphi*s - l*qdd(2)*s - l*dphi^2*c;
    N_tot = (m_w + m_b)*g*cos(alpha) + m_b*ay_com;
  end
  desliza = double(abs(Rw*wwL - dx) > 2*v_s || abs(Rw*wwR - dx) > 2*v_s);

  % --- fuerza especifica en la IMU ---
  ax_com = qdd(1) + qdd(3)*s + 2*dl*dphi*c + l*qdd(2)*c - l*dphi^2*s;
  dwx = c*d_ix + s*d_iy;  dwy = -s*d_ix + c*d_iy;
  a_imu = [ax_com; ay_com] + qdd(2)*[dwy; -dwx] - dphi^2*[dwx; dwy];
  gvec = g*[-sin(alpha); -cos(alpha)];
  fw = a_imu - gvec;
  fb_x = c*fw(1) - s*fw(2);
  fb_y = s*fw(1) + c*fw(2);

  Xdot = [dx; dphi; dl; qdd; wwL; dwwL; wwR; dwwR; wmL; dwmL; wmR; dwmR; diL; diR];
  y = [qdd; N_tot; f_L; f_R; desliza; tau_gL; tau_gR; tau_s; th_s; iL_eff; iR_eff; V_bus; fb_x; fb_y];
end
```

- [ ] **Step 4: Correr el test y verificar que pasa.** Si `test_rodadura_vs_modelo_base` no cierra al 2 %, aplicar la nota del Step 1 (servo casi rígido) antes de tocar la planta.

---

### Task 5: Sensores y controlador discreto

**Files:**
- Create: `simulacion/planta_v1/sensores_sl.m`
- Create: `simulacion/planta_v1/control_v1.m`
- Test: `simulacion/planta_v1/tests/test_control_v1.m`

**Interfaces:**
- Produces: `meas = sensores_sl(X, y, ruido, pv)` (5×1 = `[gyro; fb_x; fb_y; enc_L; enc_R]`, `ruido` 3×1 gaussiano unitario); `[u, est] = control_v1(meas, ref, pv, reset)` con `ref = [x_ref; l_ref]`, `u = [V_L; V_R; th_cmd]`, `est = [phi_hat; x_hat; dx_hat; l_hat; tau_w; sat_V]`. `control_v1` tiene estados `persistent`; `reset = 1` los inicializa.

- [ ] **Step 1: Escribir el test**

```matlab
function tests = test_control_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_sensores(tc)
  P = parametros_v1('corregido'); pv = empaquetar_v1(P);
  X = zeros(16,1); X(5) = 0.3; X(7) = 2*pi; X(9) = pi;
  y = zeros(16,1); y(15) = 0; y(16) = P.g;
  m = sensores_sl(X, y, [0;0;0], pv);
  tc.verifyEqual(m(1), 0.3 + P.sens.gyro_bias, 'AbsTol', 1e-12);
  tc.verifyEqual(m(4), P.sens.CPR); tc.verifyEqual(m(5), floor(P.sens.CPR/2));
  P2 = parametros_v1('cad'); m2 = sensores_sl(X, y, [0;0;0], empaquetar_v1(P2));
  tc.verifyTrue(all(isnan(m2(4:5))));
  m3 = sensores_sl(X, y, [1;0;0], pv);
  tc.verifyEqual(m3(1) - m(1), P.sens.gyro_rms, 'AbsTol', 1e-12);
end
function test_filtro_complementario(tc)
  P = parametros_v1('corregido'); pv = empaquetar_v1(P); pv(51:60) = 0;
  phi = 5*pi/180; meas = [0; -P.g*sin(phi); P.g*cos(phi); 0; 0];
  control_v1(meas, [0; P.din.l0], pv, 1);
  for k = 1:600, [~, est] = control_v1(meas, [0; P.din.l0], pv, 0); end
  tc.verifyEqual(est(1), phi, 'AbsTol', 0.1*pi/180);
end
function test_lqr_y_tension(tc)
  P = parametros_v1('corregido'); pv = empaquetar_v1(P);
  pv(51:54) = [-0.3 -3 -0.4 -0.5]; pv(55:58) = 0; pv(59) = P.din.l_min; pv(60) = P.din.l_max;
  meas0 = [0; 0; P.g; 0; 0];
  control_v1(meas0, [0; P.din.l0], pv, 1);
  [u, est] = control_v1([0; -P.g*sin(0.1); P.g*cos(0.1); 0; 0], [0; P.din.l0], pv, 0);
  tc.verifyGreaterThan(est(5), 0);                          % inclinado adelante -> par positivo
  tc.verifyGreaterThan(u(1), 0); tc.verifyEqual(u(1), u(2), 'AbsTol', 1e-12);
  tc.verifyLessThanOrEqual(abs(u(1)), P.bat.V);
end
function test_servo_limitado(tc)
  P = parametros_v1('corregido'); pv = empaquetar_v1(P);
  meas0 = [0; 0; P.g; 0; 0];
  control_v1(meas0, [0; P.din.l_max], pv, 1);
  th_max_l = interp_lin(P.tab.l, P.tab.th, P.din.l_max);
  [u1] = control_v1(meas0, [0; P.din.l_min], pv, 0);
  tc.verifyEqual(abs(u1(3) - th_max_l), 0.8*P.servo.w_nl*P.sens.Ts, 'RelTol', 1e-9);   % un paso limitado
  for k = 1:2000, u = control_v1(meas0, [0; P.din.l_min], pv, 0); end
  tc.verifyEqual(u(3), interp_lin(P.tab.l, P.tab.th, P.din.l_min), 'AbsTol', 1e-9);
  tc.verifyGreaterThanOrEqual(u(3), P.servo.th_min); tc.verifyLessThanOrEqual(u(3), P.servo.th_max);
end
function test_encoder_estima_x(tc)
  P = parametros_v1('corregido'); pv = empaquetar_v1(P); pv(51:60) = 0;
  meas = [0; 0; P.g; 0; 0]; control_v1(meas, [0; P.din.l0], pv, 1);
  cnt = P.sens.CPR;                      % una vuelta por muestra en las dos ruedas
  for k = 1:50, [~, est] = control_v1([0; 0; P.g; k*cnt; k*cnt], [0; P.din.l0], pv, 0); end
  tc.verifyEqual(est(2), 50*2*pi*P.Rw, 'RelTol', 1e-9);
  tc.verifyEqual(est(3), 2*pi*P.Rw/P.sens.Ts, 'RelTol', 0.01);
end
```

- [ ] **Step 2: Correr el test y verificar que falla.**

- [ ] **Step 3: Escribir `sensores_sl.m`**

```matlab
function meas = sensores_sl(X, y, ruido, pv)
%SENSORES_SL  Medidas crudas: [gyro; fb_x; fb_y; enc_L; enc_R]. ruido = 3 gaussianas unitarias.
%#codegen
  encoder = pv(41) > 0.5; CPR = pv(42); gyro_bias = pv(43); gyro_sat = pv(44); gyro_rms = pv(45); acc_rms = pv(46);
  gyro = X(5) + gyro_bias + gyro_rms*ruido(1);
  gyro = max(min(gyro, gyro_sat), -gyro_sat);
  fbx = y(15) + acc_rms*ruido(2);
  fby = y(16) + acc_rms*ruido(3);
  if encoder
    encL = floor(X(7)*CPR/(2*pi)); encR = floor(X(9)*CPR/(2*pi));
  else
    encL = NaN; encR = NaN;
  end
  meas = [gyro; fbx; fby; encL; encR];
end
```

- [ ] **Step 4: Escribir `control_v1.m`**

```matlab
function [u, est] = control_v1(meas, ref, pv, reset)
%CONTROL_V1  Ley de control discreta a Ts. meas = [gyro fb_x fb_y enc_L enc_R], ref = [x_ref l_ref].
%   u = [V_L; V_R; th_cmd]      est = [phi_hat; x_hat; dx_hat; l_hat; tau_w; sat_V]
%   Estados persistentes: filtro complementario, integracion de encoders, consigna de servo.
%#codegen
  persistent phi_hat x_hat w_hat enc_prev th_cmd listo
  if isempty(listo), listo = false; phi_hat = 0; x_hat = 0; w_hat = [0 0]; enc_prev = [0 0]; th_cmd = 0; end
  Rw=pv(5); l_min=pv(7); l_max=pv(8); R_m=pv(14); Kt=pv(16); Ke=pv(17); N=pv(18); V_bat=pv(29);
  w_nl_s=pv(32); th_min=pv(36); th_max=pv(37); Ts=pv(40); encoder=pv(41)>0.5; CPR=pv(42);
  k_comp=pv(47); fc_vel=pv(48); eta=pv(49);
  K1=pv(51:54); K2=pv(55:58); lA=pv(59); lB=pv(60);
  n=round(pv(61)); l_tab=pv(62:62+n-1); th_tab=pv(83:83+n-1);
  th_inv = flipud(th_tab(:)); l_inv = flipud(l_tab(:));      % theta creciente para invertir el mapa

  gyro=meas(1); fbx=meas(2); fby=meas(3); enc=[meas(4) meas(5)];
  x_ref=ref(1); l_ref=max(min(ref(2), l_max), l_min);
  th_target = interp_lin(l_tab, th_tab, l_ref);
  if ~listo || reset > 0.5
    listo = true; phi_hat = atan2(-fbx, fby); x_hat = 0; w_hat = [0 0]; th_cmd = th_target;
    if any(isnan(enc)), enc_prev = [0 0]; else, enc_prev = enc; end
  end
  % --- angulo: filtro complementario ---
  phi_acc = atan2(-fbx, fby);
  phi_hat = (1 - k_comp)*(phi_hat + gyro*Ts) + k_comp*phi_acc;
  dphi_hat = gyro;
  % --- posicion y velocidad de rueda desde encoders ---
  if encoder && ~any(isnan(enc))
    dth = (enc - enc_prev)*2*pi/CPR; enc_prev = enc;
    a = exp(-2*pi*fc_vel*Ts);
    w_hat = a*w_hat + (1 - a)*dth/Ts;
    x_hat = x_hat + Rw*mean(dth);
    dx_hat = Rw*mean(w_hat);
  else
    w_hat = [0 0]; dx_hat = 0;
  end
  % --- LQR programado por altura de pata (l estimado desde la consigna de servo) ---
  l_hat = interp_lin(th_inv, l_inv, th_cmd);
  lk = max(min(l_hat, lB), lA);
  K = K1 + K2*lk;
  tau_w = -(K(1)*(x_hat - x_ref) + K(2)*phi_hat + K(3)*dx_hat + K(4)*dphi_hat);
  % --- par -> tension por motor con compensacion de fcem ---
  V = zeros(2,1); sat_V = 0;
  for k = 1:2
    Vk = R_m*(tau_w/2)/(Kt*N*eta) + Ke*N*w_hat(k);
    if abs(Vk) > V_bat, sat_V = 1; end
    V(k) = max(min(Vk, V_bat), -V_bat);
  end
  % --- consigna de servo con limitador de velocidad ---
  paso = 0.8*w_nl_s*Ts;
  th_cmd = th_cmd + max(min(th_target - th_cmd, paso), -paso);
  th_cmd = max(min(th_cmd, th_max), th_min);
  u = [V(1); V(2); th_cmd];
  est = [phi_hat; x_hat; dx_hat; l_hat; tau_w; sat_V];
end
```

- [ ] **Step 5: Correr el test y verificar que pasa.** En `test_lqr_y_tension` el signo esperado supone `K(2) < 0` (convención de `modelo_base`: `tau_w = -K·X`, con `K` negativa el par es positivo hacia adelante); si `lqr` devolviera ganancias positivas en la Task 6, revisar el signo de `B` en `modelo_lineal_v1`, no el test.

---

### Task 6: Modelo lineal y diseño LQR

**Files:**
- Create: `simulacion/planta_v1/modelo_lineal_v1.m`
- Create: `simulacion/planta_v1/disenar_control_v1.m`
- Test: `simulacion/planta_v1/tests/test_lqr_v1.m`

**Interfaces:**
- Produces: `[A, B, M2] = modelo_lineal_v1(P, l0)` (estados `[x phi dx dphi]`, entrada `tau_w` total, rodadura, reductor rígido); `C = disenar_control_v1(P, w)` con `C.Kfit` (2×4), `C.l_lim` (1×2), `C.K` (9×4), `C.l` (9×1), `C.polos_la`, `C.polos_lc`, `C.Q`, `C.R`, `C.Kf`.

- [ ] **Step 1: Escribir el test**

```matlab
function tests = test_lqr_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_polo_inestable(tc)
  for v = {'cad','corregido'}
    P = parametros_v1(v{1});
    for l0 = [P.din.l_min P.din.l0 P.din.l_max]
      A = modelo_lineal_v1(P, l0);
      p = max(real(eig(A)));
      tc.verifyGreaterThan(p, 5); tc.verifyLessThan(p, 13);
      [~, B] = modelo_lineal_v1(P, l0);
      tc.verifyEqual(rank(ctrb(A, B)), 4);
    end
  end
end
function test_lqr_estable_y_signo(tc)
  for v = {'cad','corregido'}
    P = parametros_v1(v{1}); C = disenar_control_v1(P);
    for i = 1:numel(C.polos_lc), tc.verifyLessThan(max(real(C.polos_lc{i})), 0); end
    K0 = C.Kf(P.din.l0);
    tc.verifyLessThan(K0(2), 0);                 % phi positivo -> tau_w = -K*X positivo
    tc.verifyLessThan(C.Kerr, 0.5*max(abs(K0)));
  end
end
function test_inercia_reflejada(tc)
  P = parametros_v1('cad'); [~, ~, M2] = modelo_lineal_v1(P, P.din.l0);
  tc.verifyGreaterThan(M2(1,1), 5);              % N=100: el rotor reflejado equivale a varios kg
  P2 = parametros_v1('corregido'); [~, ~, M2b] = modelo_lineal_v1(P2, P2.din.l0);
  tc.verifyLessThan(M2b(1,1), 2);
end
```

- [ ] **Step 2: Correr el test y verificar que falla.**

- [ ] **Step 3: Escribir `modelo_lineal_v1.m`**

```matlab
function [A, B, M2] = modelo_lineal_v1(P, l0)
%MODELO_LINEAL_V1  Modelo lineal [x phi dx dphi] con entrada tau_w (par total de rueda).
%   Rodadura sin deslizar, reductor rigido (rotor reflejado), pata fija en l0, piso horizontal.
  m_b=P.din.m_b; m_w=P.din.m_w; J_b=P.din.J_b; g=P.g; R=P.Rw;
  J_eq = P.din.J_w + P.motor.N^2*P.motor.J_r;
  Mt = m_w + m_b + 2*J_eq/R^2;
  M2 = [Mt, m_b*l0; m_b*l0, m_b*l0^2 + J_b];
  Kq = [0 0; 0 -m_b*g*l0];
  D  = diag([2*P.rueda.b_w/R^2, P.cuerpo.b_pitch]);
  A = [zeros(2) eye(2); -M2\Kq, -M2\D];
  B = [0; 0; M2\[1/R; -1]];
end
```

- [ ] **Step 4: Escribir `disenar_control_v1.m`**

```matlab
function C = disenar_control_v1(P, w)
%DISENAR_CONTROL_V1  LQR del lazo de equilibrio sobre el modelo reducido, programado por l.
%   C = disenar_control_v1(P)
%   C = disenar_control_v1(P, struct('q_x',1,'q_phi',60,'q_dx',1,'q_dphi',2,'r',12))
  if nargin < 2, w = struct(); end
  d = @(c, v) get_def(w, c, v);
  Q = diag([d('q_x',1) d('q_phi',60) d('q_dx',1) d('q_dphi',2)]); Rr = d('r',12);
  nl = 9;
  C.l = linspace(P.din.l_min*1.02, P.din.l_max*0.98, nl)';
  C.K = zeros(nl,4); C.polos_la = zeros(nl,1); C.polos_lc = cell(nl,1);
  for i = 1:nl
    [A, B] = modelo_lineal_v1(P, C.l(i));
    C.K(i,:) = lqr(A, B, Q, Rr);
    C.polos_la(i) = max(real(eig(A)));
    C.polos_lc{i} = eig(A - B*C.K(i,:));
  end
  Aj = [ones(nl,1) C.l];
  C.Kfit = Aj \ C.K;
  C.Kerr = max(max(abs(Aj*C.Kfit - C.K)));
  C.l_lim = [C.l(1) C.l(end)]; C.Q = Q; C.R = Rr;
  C.Kf = @(l) C.Kfit(1,:) + C.Kfit(2,:)*l;
end
function v = get_def(s, c, v)
  if isfield(s, c), v = s.(c); end
end
```

- [ ] **Step 5: Correr el test y verificar que pasa.** Si `test_polo_inestable` da un polo fuera de [5, 13] rad/s, imprimir `sqrt(m_b*g*l0/(m_b*l0^2+J_b))` como referencia: el polo del péndulo simple está cerca de ese valor y el test debe ajustarse solo si el número es físicamente razonable.

---

### Task 7: Escenarios, simulación en MATLAB puro y gráficos

**Files:**
- Create: `simulacion/planta_v1/escenarios_v1.m`
- Create: `simulacion/planta_v1/simular_ode_v1.m`
- Create: `simulacion/planta_v1/resumen_v1.m`
- Create: `simulacion/planta_v1/graficar_v1.m`
- Test: `simulacion/planta_v1/tests/test_lazo_v1.m`

**Interfaces:**
- Produces: `E = escenarios_v1(nombre, P)` (`E.nombre, E.tf, E.X0, E.ref, E.pert, E.overrides, E.n_delay, E.semilla`; `escenarios_v1('lista')` devuelve la lista de nombres); `S = simular_ode_v1(P, C, E)` con `S.t, S.X, S.u, S.y, S.meas, S.est, S.ref, S.P, S.C, S.E, S.altura, S.resumen`; `S = resumen_v1(S)`; `graficar_v1(S)`.

- [ ] **Step 1: Escribir el test**

```matlab
function tests = test_lazo_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_lista_y_estructura(tc)
  P = parametros_v1('cad');
  lista = escenarios_v1('lista'); tc.verifyEqual(numel(lista), 16);
  for i = 1:numel(lista)
    E = escenarios_v1(lista{i}, P);
    tc.verifyEqual(size(E.X0), [16 1]);
    tc.verifyEqual(size(E.ref.signals.values, 2), 2);
    tc.verifyEqual(size(E.pert.signals.values, 2), 5);
    tc.verifyEqual(E.ref.time(end), E.tf, 'AbsTol', 1e-9);
  end
  E = escenarios_v1('escalon_10mm', P);
  tc.verifyLessThan(min(E.pert.signals.values(:,5)), -10);
end
function test_equilibrio_8_recupera(tc)
  for v = {'corregido','cad'}
    P = parametros_v1(v{1}); C = disenar_control_v1(P);
    E = escenarios_v1('equilibrio_8', P); E.tf = 4;
    S = simular_ode_v1(P, C, E);
    tc.verifyFalse(S.resumen.cayo, ['se cae en ' v{1}]);
    fin = S.t > 3;
    tc.verifyLessThan(max(abs(S.X(fin,2)))*180/pi, 1.0, ['no asienta en ' v{1}]);
  end
end
function test_agachar_llega(tc)
  P = parametros_v1('corregido'); C = disenar_control_v1(P);
  E = escenarios_v1('agachar', P);
  S = simular_ode_v1(P, C, E);
  tc.verifyFalse(S.resumen.cayo);
  i = find(S.t > 2.9, 1); tc.verifyEqual(S.X(i,3), P.din.l_min*1.05, 'AbsTol', 0.005);
  tc.verifyEqual(S.X(end,3), P.din.l_max*0.97, 'AbsTol', 0.005);
end
```

- [ ] **Step 2: Correr el test y verificar que falla.**

- [ ] **Step 3: Escribir `escenarios_v1.m`**

```matlab
function E = escenarios_v1(nombre, P)
%ESCENARIOS_V1  Estado inicial, referencias, perturbaciones y overrides de cada escenario.
%   E = escenarios_v1('equilibrio_8', P)      lista = escenarios_v1('lista')
%   E.ref / E.pert son estructuras para From Workspace: .time (n x 1), .signals.values (n x k).
  lista = {'equilibrio_3','equilibrio_8','equilibrio_15','empujon_3N','empujon_6N','agachar','avanzar', ...
           'velocidad','pendiente_5','pendiente_10','escalon_5mm','escalon_10mm','resbaloso','bateria_baja', ...
           'sensor_retardo_10','sin_encoder'};
  if strcmp(nombre, 'lista'), E = lista; return; end
  d2r = pi/180; dt = 1e-3;
  E.nombre = nombre; E.tf = 6; E.overrides = {}; E.n_delay = P.sens.n_delay; E.semilla = P.sens.semilla;
  X0 = zeros(16,1); X0(3) = P.din.l0;
  t = (0:dt:E.tf)';
  x_ref = zeros(size(t)); l_ref = P.din.l0*ones(size(t));
  F_x = zeros(size(t)); M_p = zeros(size(t)); alpha = zeros(size(t)); mu = P.rueda.mu*ones(size(t)); F_esc = zeros(size(t));
  pulso = @(t0, dur) double(t >= t0 & t < t0 + dur);
  m_tot = P.din.m_b + P.din.m_w;
  switch nombre
    case 'equilibrio_3',  X0(2) = 3*d2r;
    case 'equilibrio_8',  X0(2) = 8*d2r;
    case 'equilibrio_15', X0(2) = 15*d2r;
    case 'empujon_3N',    F_x = 3*pulso(2, 0.05);
    case 'empujon_6N',    F_x = 6*pulso(2, 0.05);
    case 'agachar',       l_ref(t > 1 & t <= 3) = P.din.l_min*1.05; l_ref(t > 3) = P.din.l_max*0.97;
    case 'avanzar',       x_ref(t > 1 & t <= 4) = 0.5;
    case 'velocidad',     x_ref = 0.2*max(t - 1, 0);
    case 'pendiente_5',   alpha(:) = 5*d2r;
    case 'pendiente_10',  alpha(:) = 10*d2r;
    case 'escalon_5mm',   F_esc = -m_tot*sqrt(2*P.g*0.005)/0.02*pulso(3, 0.02);
    case 'escalon_10mm',  F_esc = -m_tot*sqrt(2*P.g*0.010)/0.02*pulso(3, 0.02);
    case 'resbaloso',     mu(:) = 0.3; F_x = 3*pulso(2, 0.05); E.overrides = {'mu', 0.3};
    case 'bateria_baja',  F_x = 6*pulso(2, 0.05); E.overrides = {'V_bat', 9.6};
    case 'sensor_retardo_10', F_x = 6*pulso(2, 0.05); E.n_delay = 2; E.overrides = {'n_delay', 2};
    case 'sin_encoder',   x_ref(t > 1 & t <= 4) = 0.5; E.overrides = {'encoder', false};
    otherwise, error('escenarios_v1: escenario "%s" no definido', nombre);
  end
  E.X0 = X0;
  E.ref.time = t;  E.ref.signals.values = [x_ref l_ref];                E.ref.signals.dimensions = 2;
  E.pert.time = t; E.pert.signals.values = [F_x M_p alpha mu F_esc];    E.pert.signals.dimensions = 5;
end
```

- [ ] **Step 4: Escribir `resumen_v1.m`**

```matlab
function S = resumen_v1(S)
%RESUMEN_V1  Metricas estandar de una corrida. Espera S.t, S.X, S.u, S.y, S.P.
  P = S.P; r2d = 180/pi; t = S.t; phi = S.X(:,2);
  R.phi_max_deg = max(abs(phi))*r2d;
  R.phi_fin_deg = phi(end)*r2d;
  R.cayo = any(abs(phi) > 45*pi/180);
  fuera = abs(phi) >= 1*pi/180; idx = find(fuera, 1, 'last');
  if isempty(idx), R.t_asent = 0; elseif idx == numel(t), R.t_asent = Inf; else, R.t_asent = t(idx+1); end
  R.uso_V = max(max(abs(S.u(:,1:2))))/P.bat.V;
  R.uso_servo = max(abs(S.y(:,10)))/P.servo.tau_max;
  R.pct_desliza = 100*mean(S.y(:,7) > 0.5);
  i_tot = abs(S.y(:,12)) + abs(S.y(:,13));
  R.i_pico = max(i_tot);
  R.mAh = trapz(t, i_tot)/3600*1000;
  R.x_fin = S.X(end,1); R.l_fin = S.X(end,3);
  S.altura = P.Rw + S.X(:,3) - P.din.r_com(2) + P.din.h_tapa_sobre_A;
  S.resumen = R;
end
```

- [ ] **Step 5: Escribir `simular_ode_v1.m`**

```matlab
function S = simular_ode_v1(P, C, E)
%SIMULAR_ODE_V1  Corre un escenario en MATLAB puro: planta continua (ode15s) entre muestras del control.
%   Misma estructura que el Simulink: sensores + retardo de E.n_delay muestras + control a Ts (ZOH).
  pv = empaquetar_v1(P, C);
  Ts = P.sens.Ts; nd = E.n_delay; tf = E.tf;
  rng(E.semilla);
  nk = floor(tf/Ts);
  ref_f  = @(tt) interp1(E.ref.time,  E.ref.signals.values,  tt, 'previous', 'extrap');
  pert_f = @(tt) interp1(E.pert.time, E.pert.signals.values, tt, 'previous', 'extrap');
  m0 = [0; 0; P.g; NaN; NaN];
  buf = repmat({m0}, nd + 1, 1);
  T = zeros(nk+1,1); XX = zeros(nk+1,16); U = zeros(nk+1,3); Y = zeros(nk+1,16);
  MEAS = zeros(nk+1,5); EST = zeros(nk+1,6); REF = zeros(nk+1,2);
  opts = odeset('RelTol',1e-5,'AbsTol',1e-7,'MaxStep',Ts);
  control_v1(m0, [0; P.din.l0], pv, 1);
  X = E.X0; t = 0; u = [0; 0; interp_lin(P.tab.l, P.tab.th, E.X0(3))];
  for k = 1:nk+1
    d = pert_f(t)'; r = ref_f(t)';
    [~, y] = planta_sl(X, u, d, pv);
    meas = sensores_sl(X, y, randn(3,1), pv);
    buf = [buf(2:end); {meas}]; meas_d = buf{1};
    [u, est] = control_v1(meas_d, r, pv, 0);
    T(k)=t; XX(k,:)=X'; U(k,:)=u'; Y(k,:)=y'; MEAS(k,:)=meas_d'; EST(k,:)=est'; REF(k,:)=r';
    if k == nk+1, break; end
    [~, Xo] = ode15s(@(tt, Xi) planta_sl(Xi, u, pert_f(tt)', pv), [t t+Ts], X, opts);
    X = Xo(end,:)'; t = t + Ts;
    if abs(X(2)) > pi/2, T = T(1:k+1); XX = XX(1:k+1,:); U = U(1:k+1,:); Y = Y(1:k+1,:); MEAS = MEAS(1:k+1,:); EST = EST(1:k+1,:); REF = REF(1:k+1,:);
       T(k+1) = t; XX(k+1,:) = X'; U(k+1,:) = u'; Y(k+1,:) = y'; MEAS(k+1,:) = meas_d'; EST(k+1,:) = est'; REF(k+1,:) = r'; break; end
  end
  S = struct('t',T,'X',XX,'u',U,'y',Y,'meas',MEAS,'est',EST,'ref',REF,'E',E,'P',P,'C',C,'motor','ode15s');
  S = resumen_v1(S);
end
```

- [ ] **Step 6: Escribir `graficar_v1.m`**

```matlab
function graficar_v1(S)
%GRAFICAR_V1  Seis paneles con lo que importa de una corrida.
  P = S.P; r2d = 180/pi; t = S.t;
  figure('Color','w','Name',sprintf('%s (%s, %s)', S.E.nombre, P.variante, S.motor), 'Position',[60 60 1150 760]);
  subplot(3,2,1); plot(t, S.X(:,2)*r2d, 'LineWidth',1.6); hold on; plot(t, S.est(:,1)*r2d, '--'); grid on;
  ylabel('\phi [deg]'); legend('real','estimado','Location','best'); title('Inclinacion');
  subplot(3,2,2); plot(t, S.altura*1e3, 'LineWidth',1.6); hold on;
  plot(t, (P.Rw + S.ref(:,2) - P.din.r_com(2) + P.din.h_tapa_sobre_A)*1e3, '--'); grid on;
  ylabel('tope de la tapa [mm]'); legend('real','consigna','Location','best'); title('Altura');
  subplot(3,2,3); plot(t, S.u(:,1:2), 'LineWidth',1.4); hold on; plot(t, [1 -1].*P.bat.V.*ones(numel(t),2), 'r:'); grid on;
  ylabel('V motor [V]'); title('Tension de motores');
  subplot(3,2,4); plot(t, S.y(:,12:13), 'LineWidth',1.4); grid on; ylabel('I [A]'); title('Corriente de motores');
  subplot(3,2,5); plot(t, S.X(:,1), 'LineWidth',1.6); hold on; plot(t, S.ref(:,1), '--'); plot(t, S.est(:,2), ':'); grid on;
  ylabel('x [m]'); xlabel('t [s]'); legend('real','consigna','estimado','Location','best'); title('Posicion');
  subplot(3,2,6); yyaxis left; plot(t, S.y(:,10), 'LineWidth',1.4); ylabel('\tau servo [N m]');
  yyaxis right; plot(t, S.y(:,7), 'LineWidth',1); ylabel('desliza'); grid on; xlabel('t [s]'); title('Servo y deslizamiento');
end
```

- [ ] **Step 7: Correr el test y verificar que pasa.** `test_equilibrio_8_recupera` es el primer test de lazo cerrado real. Si la variante `cad` se cae, primero graficar (`graficar_v1(S)`) y revisar en este orden: (1) signo de `tau_w` respecto de `V` (par positivo debe empujar la base hacia adelante bajo un cuerpo inclinado hacia adelante), (2) saturación de tensión (`S.resumen.uso_V`), (3) pesos del LQR: probar `disenar_control_v1(P, struct('q_phi',100,'r',4))`. Anotar en el README qué pesos quedaron y por qué.

---

### Task 8: Modelo Simulink

**Files:**
- Create: `simulacion/planta_v1/cargar_workspace_v1.m`
- Create: `simulacion/planta_v1/construir_planta.m`
- Create: `simulacion/planta_v1/simular_slx_v1.m`
- Test: `simulacion/planta_v1/tests/test_simulink_v1.m`

**Interfaces:**
- Produces: `cargar_workspace_v1(P, C, E)` (deja `pv, X0, Ts, Tfin, n_delay, semilla, ref_ts, pert_ts, P, C, E` en el workspace base); `mdl = construir_planta(P, C, E, nombre)` (crea y guarda `simulacion/planta_v1/planta_segway_v1.slx`); `S = simular_slx_v1(P, C, E)` (misma estructura de salida que `simular_ode_v1`, remuestreada a `Ts`, `S.motor = 'simulink'`).

- [ ] **Step 1: Escribir el test**

```matlab
function tests = test_simulink_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_construye_y_coincide_con_ode(tc)
  P = parametros_v1('corregido'); C = disenar_control_v1(P);
  E = escenarios_v1('equilibrio_8', P); E.tf = 3;
  mdl = construir_planta(P, C, E);
  tc.verifyTrue(bdIsLoaded(mdl));
  tc.verifyTrue(isfile(fullfile(fileparts(which('construir_planta')), [mdl '.slx'])));
  Ss = simular_slx_v1(P, C, E);
  So = simular_ode_v1(P, C, E);
  tc.verifyFalse(Ss.resumen.cayo);
  tc.verifyEqual(Ss.resumen.phi_max_deg, So.resumen.phi_max_deg, 'RelTol', 0.05);
  tc.verifyEqual(Ss.X(end,2), So.X(end,2), 'AbsTol', 0.5*pi/180);
  tc.verifyEqual(size(Ss.X, 2), 16); tc.verifyEqual(size(Ss.y, 2), 16);
end
function test_variante_cad_en_simulink(tc)
  P = parametros_v1('cad'); C = disenar_control_v1(P);
  E = escenarios_v1('empujon_3N', P); E.tf = 4;
  S = simular_slx_v1(P, C, E);
  tc.verifyFalse(S.resumen.cayo);
end
```

- [ ] **Step 2: Correr el test y verificar que falla.**

- [ ] **Step 3: Escribir `cargar_workspace_v1.m`**

```matlab
function cargar_workspace_v1(P, C, E)
%CARGAR_WORKSPACE_V1  Deja en el workspace base todo lo que lee planta_segway_v1.slx.
  pv = empaquetar_v1(P, C);
  assignin('base','pv',pv); assignin('base','X0',E.X0); assignin('base','Ts',P.sens.Ts);
  assignin('base','Tfin',E.tf); assignin('base','n_delay',max(E.n_delay,1)); assignin('base','semilla',E.semilla);
  assignin('base','ref_ts',E.ref); assignin('base','pert_ts',E.pert);
  assignin('base','P',P); assignin('base','C',C); assignin('base','E',E);
end
```

- [ ] **Step 4: Escribir `construir_planta.m`**

```matlab
function mdl = construir_planta(P, C, E, nombre)
%CONSTRUIR_PLANTA  Arma planta_segway_v1.slx por codigo y lo guarda junto a este archivo.
%   mdl = construir_planta(P, C, E)
%   Diagrama:  ref --ZOH--> [Controlador] --u--> [Planta] --Xdot--> 1/s --X--+--> Xout
%                                ^                  ^  pert            |
%                                |                  |                  v
%                             [Delay] <-- [Sensores] <-- ZOH <---------+ (X, y)
  if nargin < 4 || isempty(nombre), nombre = 'planta_segway_v1'; end
  mdl = nombre;
  cargar_workspace_v1(P, C, E);
  if bdIsLoaded(mdl), close_system(mdl, 0); end
  new_system(mdl); open_system(mdl);
  ab = @(src, nom, pos, varargin) add_block(src, [mdl '/' nom], 'Position', pos, varargin{:});

  ab('simulink/Sources/From Workspace', 'ref',   [30 40 110 70],   'VariableName','ref_ts',  'SampleTime','Ts', 'Interpolate','off');
  ab('simulink/Discrete/Zero-Order Hold', 'zoh_ref', [140 40 170 70], 'SampleTime','Ts');
  ab('simulink/Sources/Constant', 'reset',        [30 110 110 140], 'Value','0', 'SampleTime','Ts');
  ab('simulink/Sources/From Workspace', 'pert',  [30 200 110 230],  'VariableName','pert_ts', 'SampleTime','0',  'Interpolate','off');
  ab('simulink/Sources/Constant', 'pv',           [30 300 110 330], 'Value','pv');

  ab('simulink/User-Defined Functions/MATLAB Function', 'Controlador', [200 40 320 150]);
  ab('simulink/User-Defined Functions/MATLAB Function', 'Planta',      [420 160 540 280]);
  ab('simulink/Continuous/Integrator', 'int_X',   [600 200 630 230], 'InitialCondition','X0');
  ab('simulink/Discrete/Zero-Order Hold', 'zoh_X', [300 340 340 370], 'SampleTime','Ts');
  ab('simulink/Discrete/Zero-Order Hold', 'zoh_y', [300 390 340 420], 'SampleTime','Ts');
  ab('simulink/Sources/Random Number', 'ruido',    [300 440 340 470], 'Mean','0', 'Variance','1', 'Seed','semilla+[0 1 2]', 'SampleTime','Ts');
  ab('simulink/User-Defined Functions/MATLAB Function', 'Sensores',    [420 340 540 470]);
  ab('simulink/Discrete/Delay', 'retardo',         [600 390 640 420], 'DelayLength','n_delay', 'InitialCondition','[0;0;9.81;NaN;NaN]', 'SampleTime','Ts');

  ab('simulink/Sinks/To Workspace', 'Xout', [700 200 760 230], 'VariableName','Xout', 'SaveFormat','Structure With Time');
  ab('simulink/Sinks/To Workspace', 'Yout', [700 250 760 280], 'VariableName','Yout', 'SaveFormat','Structure With Time');
  ab('simulink/Sinks/To Workspace', 'Uout', [700 60 760 90],   'VariableName','Uout', 'SaveFormat','Structure With Time');
  ab('simulink/Sinks/To Workspace', 'Eout', [700 110 760 140], 'VariableName','Eout', 'SaveFormat','Structure With Time');
  ab('simulink/Sinks/To Workspace', 'Mout', [700 390 760 420], 'VariableName','Mout', 'SaveFormat','Structure With Time');
  ab('simulink/Sinks/Scope', 'Estados',  [850 200 890 230]);
  ab('simulink/Sinks/Scope', 'Comandos', [850 60 890 90]);

  poner_codigo([mdl '/Controlador'], ['function [u, est] = fcn(meas, ref, pv, reset)\n%%#codegen\n' ...
                                      '[u, est] = control_v1(meas, ref, pv, reset);\n']);
  poner_codigo([mdl '/Planta'],      ['function [Xdot, y] = fcn(X, u, d, pv)\n%%#codegen\n' ...
                                      '[Xdot, y] = planta_sl(X, u, d, pv);\n']);
  poner_codigo([mdl '/Sensores'],    ['function meas = fcn(X, y, ruido, pv)\n%%#codegen\n' ...
                                      'meas = sensores_sl(X, y, ruido, pv);\n']);

  L = @(a, b) add_line(mdl, a, b, 'autorouting','on');
  L('ref/1','zoh_ref/1'); L('zoh_ref/1','Controlador/2'); L('pv/1','Controlador/3'); L('reset/1','Controlador/4');
  L('Controlador/1','Planta/2'); L('pert/1','Planta/3'); L('pv/1','Planta/4');
  L('Planta/1','int_X/1'); L('int_X/1','Planta/1');
  L('int_X/1','zoh_X/1'); L('Planta/2','zoh_y/1');
  L('zoh_X/1','Sensores/1'); L('zoh_y/1','Sensores/2'); L('ruido/1','Sensores/3'); L('pv/1','Sensores/4');
  L('Sensores/1','retardo/1'); L('retardo/1','Controlador/1');
  L('int_X/1','Xout/1'); L('Planta/2','Yout/1'); L('Controlador/1','Uout/1'); L('Controlador/2','Eout/1'); L('retardo/1','Mout/1');
  L('int_X/1','Estados/1'); L('Controlador/1','Comandos/1');

  if P.motor.gear_rigido
    set_param(mdl, 'Solver','ode15s', 'RelTol','1e-5', 'AbsTol','1e-7', 'MaxStep','2e-3');
  else
    set_param(mdl, 'Solver','ode15s', 'RelTol','1e-4', 'AbsTol','1e-7', 'MaxStep','5e-4');
  end
  set_param(mdl, 'StopTime','Tfin', 'ReturnWorkspaceOutputs','on');
  Simulink.BlockDiagram.arrangeSystem(mdl);
  save_system(mdl, fullfile(fileparts(mfilename('fullpath')), [mdl '.slx']));
  fprintf('Modelo %s.slx creado.\n', mdl);
end
function poner_codigo(ruta, txt)
  txt = sprintf(txt);
  S = sfroot; blk = S.find('-isa','Stateflow.EMChart','Path',ruta); blk.Script = txt;
end
```

- [ ] **Step 5: Escribir `simular_slx_v1.m`**

```matlab
function S = simular_slx_v1(P, C, E, mdl)
%SIMULAR_SLX_V1  Corre un escenario en planta_segway_v1.slx y devuelve la misma estructura que simular_ode_v1.
  if nargin < 4 || isempty(mdl), mdl = 'planta_segway_v1'; end
  aqui = fileparts(mfilename('fullpath'));
  if ~bdIsLoaded(mdl)
    if isfile(fullfile(aqui, [mdl '.slx'])), load_system(fullfile(aqui, [mdl '.slx'])); else, construir_planta(P, C, E, mdl); end
  end
  cargar_workspace_v1(P, C, E);
  if P.motor.gear_rigido, set_param(mdl, 'MaxStep','2e-3', 'RelTol','1e-5'); else, set_param(mdl, 'MaxStep','5e-4', 'RelTol','1e-4'); end
  out = sim(mdl);
  Ts = P.sens.Ts; t = (0:Ts:E.tf)';
  rem = @(s) interp1(s.time, s.signals.values, t, 'previous', 'extrap');
  XX = rem(out.Xout); Y = rem(out.Yout); U = rem(out.Uout); ES = rem(out.Eout); MM = rem(out.Mout);
  ref_f = interp1(E.ref.time, E.ref.signals.values, t, 'previous', 'extrap');
  S = struct('t',t,'X',XX,'u',U,'y',Y,'meas',MM,'est',ES,'ref',ref_f,'E',E,'P',P,'C',C,'motor','simulink');
  S = resumen_v1(S);
end
```

- [ ] **Step 6: Correr el test y verificar que pasa.** Errores esperables y su arreglo: (a) "Undefined function" en un bloque MATLAB Function → falta `addpath` de `planta_v1` y `modelo_base` en la sesión antes de `sim`; (b) error de tamaño en `Delay` → confirmar que `Sensores` devuelve 5×1 y la condición inicial es 5×1; (c) lazo algebraico → `n_delay` debe ser ≥ 1 (lo fuerza `cargar_workspace_v1`); (d) `out.Xout` inexistente → `set_param(mdl,'ReturnWorkspaceOutputs','on')` ya está en `construir_planta`; si el modelo viene de disco, aplicar el mismo `set_param` en `simular_slx_v1`.

---

### Task 9: Barrido de escenarios, punto de entrada y README

**Files:**
- Create: `simulacion/planta_v1/correr_escenarios.m`
- Create: `simulacion/planta_v1/arrancar_v1.m`
- Create: `simulacion/planta_v1/README.md`
- Test: `simulacion/planta_v1/tests/test_escenarios_v1.m`

**Interfaces:**
- Produces: `R = correr_escenarios(variante, nombres, motor)` (`motor` = `'simulink'` | `'ode'`; `R.S` celda de corridas, `R.tabla` texto Markdown, `R.T` tabla MATLAB); escribe `simulacion/planta_v1/resultados/resultados_<variante>_<motor>.mat` y `.md`.

- [ ] **Step 1: Escribir el test**

```matlab
function tests = test_escenarios_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_barrido_ode_corregido(tc)
  R = correr_escenarios('corregido', {'equilibrio_3','empujon_3N','pendiente_5'}, 'ode');
  tc.verifyEqual(numel(R.S), 3);
  tc.verifyEqual(height(R.T), 3);
  tc.verifyTrue(contains(R.tabla, 'equilibrio_3'));
  for i = 1:3, tc.verifyFalse(R.S{i}.resumen.cayo); end
  tc.verifyTrue(isfile(fullfile(fileparts(which('correr_escenarios')), 'resultados', 'resultados_corregido_ode.md')));
end
function test_overrides_se_aplican(tc)
  R = correr_escenarios('cad', {'bateria_baja','sin_encoder'}, 'ode');
  tc.verifyEqual(R.S{1}.P.bat.V, 9.6);
  tc.verifyFalse(R.S{2}.P.sens.encoder);
end
```

- [ ] **Step 2: Correr el test y verificar que falla.**

- [ ] **Step 3: Escribir `correr_escenarios.m`**

```matlab
function R = correr_escenarios(variante, nombres, motor)
%CORRER_ESCENARIOS  Corre escenarios (Simulink u ode15s) y arma la tabla resumen.
%   R = correr_escenarios('cad')                                  todos, en Simulink
%   R = correr_escenarios('corregido', {'equilibrio_8'}, 'ode')
  if nargin < 1 || isempty(variante), variante = 'cad'; end
  if nargin < 2 || isempty(nombres), nombres = escenarios_v1('lista'); end
  if nargin < 3 || isempty(motor), motor = 'simulink'; end
  P0 = parametros_v1(variante); C = disenar_control_v1(P0);
  n = numel(nombres);
  R.variante = variante; R.motor = motor; R.S = cell(n,1);
  esc = strings(n,1); phimax = zeros(n,1); phifin = zeros(n,1); cayo = false(n,1); tas = zeros(n,1);
  usoV = zeros(n,1); usoS = zeros(n,1); desl = zeros(n,1); ipico = zeros(n,1); mah = zeros(n,1);
  for i = 1:n
    E = escenarios_v1(nombres{i}, P0);
    P = P0; if ~isempty(E.overrides), P = parametros_v1(variante, E.overrides{:}); end
    fprintf('[%s/%s] %-18s ', variante, motor, nombres{i}); tic;
    switch motor
      case 'ode', S = simular_ode_v1(P, C, E);
      otherwise,  S = simular_slx_v1(P, C, E);
    end
    r = S.resumen; R.S{i} = S;
    esc(i) = nombres{i}; phimax(i) = r.phi_max_deg; phifin(i) = r.phi_fin_deg; cayo(i) = r.cayo; tas(i) = r.t_asent;
    usoV(i) = 100*r.uso_V; usoS(i) = 100*r.uso_servo; desl(i) = r.pct_desliza; ipico(i) = r.i_pico; mah(i) = r.mAh;
    fprintf('%5.1fs  phi max %5.1f deg  %s\n', toc, r.phi_max_deg, ternario(r.cayo, 'SE CAE', 'ok'));
  end
  R.T = table(esc, phimax, phifin, cayo, tas, usoV, usoS, desl, ipico, mah, 'VariableNames', ...
      {'escenario','phi_max_deg','phi_fin_deg','se_cae','t_asent_s','uso_V_pct','uso_servo_pct','desliza_pct','I_pico_A','mAh'});
  lineas = "| escenario | phi max [deg] | phi final [deg] | se cae | t asent [s] | uso V [%] | uso servo [%] | desliza [%] | I pico [A] | mAh |";
  lineas(2) = "|---|---:|---:|:--:|---:|---:|---:|---:|---:|---:|";
  for i = 1:n
    lineas(end+1) = sprintf('| %s | %.1f | %.1f | %s | %.2f | %.0f | %.0f | %.0f | %.2f | %.1f |', esc(i), phimax(i), phifin(i), ...
        ternario(cayo(i), 'SI', 'no'), tas(i), usoV(i), usoS(i), desl(i), ipico(i), mah(i)); %#ok<AGROW>
  end
  R.tabla = char(strjoin(lineas, newline));
  carpeta = fullfile(fileparts(mfilename('fullpath')), 'resultados');
  if ~isfolder(carpeta), mkdir(carpeta); end
  save(fullfile(carpeta, sprintf('resultados_%s_%s.mat', variante, motor)), 'R', '-v7.3');
  fid = fopen(fullfile(carpeta, sprintf('resultados_%s_%s.md', variante, motor)), 'w');
  fprintf(fid, '# Resultados %s (%s)\n\nMotor: %s. Generado %s.\n\n%s\n', variante, motor, P0.motor.nombre, datestr(now), R.tabla);
  fclose(fid);
  disp(R.T);
end
function y = ternario(c, a, b)
  if c, y = a; else, y = b; end
end
```

- [ ] **Step 4: Escribir `arrancar_v1.m`**

```matlab
% ARRANCAR_V1  Punto de entrada de la planta v1.
%   1. parametros de la variante   2. LQR   3. un escenario en ode15s con graficos
%   4. modelo Simulink             5. barrido de escenarios en Simulink
clear; clc; close all;
aqui = fileparts(mfilename('fullpath'));
addpath(aqui); addpath(fullfile(aqui, '..', 'modelo_base'));

% ================== LO QUE SE TOCA ==================
variante = 'corregido';      % 'cad' (tal como esta el CAD) o 'corregido'
escenario = 'empujon_6N';
w.q_x = 1; w.q_phi = 60; w.q_dx = 1; w.q_dphi = 2; w.r = 12;
% ====================================================

P = parametros_v1(variante);
C = disenar_control_v1(P, w);
fprintf('\n%s: m_b = %.3f kg, m_w = %.3f kg, J_b = %.2e, l = %.0f..%.0f mm, G = %.3f m/rad\n', ...
    P.variante, P.din.m_b, P.din.m_w, P.din.J_b, P.din.l_min*1e3, P.din.l_max*1e3, P.din.G);
fprintf('motor: %s | polo inestable en l0: %+.2f rad/s | K(l0) = [%s]\n', P.motor.nombre, ...
    C.polos_la(5), num2str(C.Kf(P.din.l0), '%8.3f'));

E = escenarios_v1(escenario, P);
S = simular_ode_v1(P, C, E);
disp(S.resumen); graficar_v1(S);

construir_planta(P, C, E);
R = correr_escenarios(variante);              % todos los escenarios en Simulink
disp(R.tabla);
```

- [ ] **Step 5: Escribir `README.md`** con: propósito, cómo correr (`arrancar_v1`, tests con `runtests('simulacion/planta_v1/tests')`), convenciones de ejes, tabla de estados `X`, tabla de `y`, índices de `pv` (copiar el encabezado de `empaquetar_v1`), lista de escenarios, parámetros extrapolados que hay que confirmar (JGA25 de 60 rpm, `J_r`, juego, masas impresas), y qué pesos de LQR quedaron para cada variante y por qué.

- [ ] **Step 6: Correr el test y verificar que pasa.**

- [ ] **Step 7: Correr todos los tests** con `runtests('simulacion/planta_v1/tests')` y anotar el resultado en el README (fecha, cuántos pasan).

- [ ] **Step 8: Correr el barrido completo** `correr_escenarios('cad')` y `correr_escenarios('corregido')` en Simulink, y dejar los `.md` de resultados en `simulacion/planta_v1/resultados/`.
