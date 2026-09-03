function P = parametros_v1(variante, varargin)
%PARAMETROS_V1  Unica fuente de parametros de la planta v1 (SI internamente).
%   P = parametros_v1('cad')         robot tal como esta en el CAD primera_iteracion
%   P = parametros_v1('corregido')   bancada 100 mm a 45 grados, motor 280 rpm con encoder
%   P = parametros_v1('cad','V_bat',9.6,'mu',0.3,'gear_rigido',false)
%   Los nombres admitidos son los campos de la estructura o (ver abajo). Los argumentos se dan
%   en mm / g / grados; P queda en SI.
  if nargin < 1 || isempty(variante), variante = 'cad'; end
  mm = 1e-3; gr = 1e-3; d2r = pi/180;

  % ---------- geometria del cuatro barras (mm, grados) ----------
  o.s_barras = 100;                 % escala de las barras impresas (CAD)
  o.k_AD = 1.400; o.k_BC = 1.350; o.k_CD = 0.510; o.k_DP = 1.400;
  o.delta = 164; o.th = [320 350]; o.rama = +1;
  o.Rw = 33;                        % radio de rueda [mm], rueda comercial de 65
  switch lower(variante)
    case 'cad'
      o.AB = 80;  o.ang_AB = 47.5; o.N = 100;  o.encoder = true;
      o.nombre_motor = 'JGA25-370 12V 60rpm (1:100) + encoder';
      % Sin encoder no hay medida de x ni de velocidad y el lazo no cierra (ver escenario sin_encoder);
      % se asume que el motor comprado sera la version -371 con encoder.
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
  o.eta = 0.7;                      % rendimiento que asume el controlador para par -> tension
  % ---------- bateria ----------
  o.V_bat = 11.1; o.R_bat = 0.05;
  % ---------- servo DS3225MG ----------
  o.tau_s_max = 2.4; o.w_nl_servo = 7.7; o.Kp_s = 45; o.Kd_s = 1.0; o.n_servos = 2;
  % ---------- cuerpo ----------
  o.b_pitch = 1e-3; o.b_pata = 8.0; o.k_tope = 2e4; o.c_tope = 60;
  % ---------- sensores y control ----------
  o.Ts = 5e-3; o.n_delay = 1; o.d_imu = [-18.5 21.0];   % IMU en el centro de la cabina, respecto de A
  o.gyro_bias_dps = 0.5; o.gyro_rms_dps = 0.1; o.gyro_sat_dps = 2000; o.acc_rms_g = 0.02;
  o.CPR_motor = 11; o.k_comp = 0.005; o.fc_vel = 20; o.semilla = 1;   % k_comp: tau del filtro = Ts/k = 1 s
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
  P.chasis.yc = 0.021; P.chasis.alto = 0.1045;    % solo los usa barrido_pata (altura informativa)
  P.m.total = 0;                                  % idem (par informativo)
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
  P.tab.dthdl = gradient(P.tab.th, P.tab.l);      % dtheta/dl con signo (negativo en esta geometria)
  P.din.G = mean(abs(1./P.tab.dthdl));            % |dl/dtheta| medio [m/rad]
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
