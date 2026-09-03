function P = params_robot(varargin)
%PARAMS_ROBOT  Unica fuente de verdad de la geometria y las masas del robot.
%
%   TODA la geometria sale de UN parametro de escala: s = |AB| (bancada).
%   El resto de las barras son multiplos adimensionales de s.
%
%   CONVENCION DE EJES (mirando el robot de perfil):
%     +x  = HACIA ATRAS      -x = HACIA ADELANTE (el frente del robot)
%     +y  = hacia arriba,  suelo en y = 0
%   El hombro A va adelante, el segundo pivote B queda DETRAS y arriba,
%   y la pata se pliega hacia atras (C y D barren x positivo).
%
%   UNIDADES INTERNAS: SI  ->  metros, kilogramos, radianes.
%   Los argumentos se pasan en MILIMETROS y GRAMOS (comodo para CAD);
%   params_robot los convierte. Usar mostrar_params(P) para verlos en mm.
%
%   P = params_robot()                        % escala por defecto s = 80 mm
%   P = params_robot('s', 100)                % bancada de 100 mm
%   P = params_robot('s', 80, 'Dw', 90)       % ademas rueda de 90 mm de diametro
%   P = params_robot('geom','hibrida')        % otra familia de relaciones
%
%   Campos principales de P (todos en SI):
%     P.s                escala = |AB|                      [m]
%     P.AD .BC .CD .DP   largos de barra                    [m]
%     P.A  .B            pivotes fijos, relativos a A       [m]
%     P.delta            angulo del acoplador (rama D->C a D->P) [rad]
%     P.Rw               radio de rueda                     [m]
%     P.th               [th_min th_max] recorrido del motor [rad]
%     P.chasis           .largo .alto .ancho .xc .yc        [m]
%     P.m                masas de cada item                 [kg]

  % ---------- valores por defecto (en mm / g / grados) ----------
  o.s      = 80;        % ESCALA: distancia entre los dos pivotes fijos A y B [mm]
  o.Dw     = 80;        % diametro de rueda [mm]  (menu comercial: 72 76 80 84 90 100 110)
  o.ancho_rueda = 24;   % ancho del nucleo de la rueda [mm]
  o.geom   = 'grupo';   % familia de relaciones adimensionales
  o.ch_largo = 150;     % CABINA: largo en el plano sagital [mm]
  o.ch_alto  = 100;     % CABINA: alto [mm]
  o.ch_ancho = 130;     % CABINA: ancho entre placas [mm]
  o.ch_xc  = 0;         % centro de la cabina respecto de A [mm]. 0 = A en el medio de la caja.
                        % Poner [] para que lo calcule por balance de masas.
  o.ch_yc  = 25;        % centro de la cabina respecto de A, vertical [mm]
  o.x_bat  = [];        % posicion de la bateria dentro de la caja [mm]; [] = lo mas adelante que entre
  o.marg_bat = 20;      % margen de la bateria contra la pared de la caja [mm]
  o.margen_placa = 15;  % material minimo alrededor de cada pivote en la placa [mm]
  o.esp_placa = 4;      % espesor de la placa lateral [mm]
  o.rama   = +1;        % rama de armado del cuatro barras
  % masas [g]
  o.m_servo = 60; o.m_motor_rueda = 45; o.m_rueda = 35;
  o.m_barra = 12; o.m_placa = 55; o.m_bateria = 130;
  o.m_electronica = 80; o.m_caja = 100; o.m_tornilleria = 60;
  % ---- dinamica ----
  o.tau_rueda_max = 0.35;   % par maximo por rueda [N.m]  (motorreductor)
  o.w_rueda_max   = 300;    % velocidad maxima de rueda [rpm]
  o.tau_hombro_max= 1.96;   % par maximo por servo de hombro [N.m] = 20 kg.cm
  o.w_hombro_max  = 300;    % velocidad del servo [deg/s]  (0.2 s / 60 deg)
  o.tau_servo_kp  = 40;     % ganancia P interna del servo [N.m/rad]
  o.b_rueda  = 2e-3;        % friccion viscosa en la rueda [N.m.s/rad]
  o.b_pitch  = 1e-3;        % amortiguamiento del cabeceo [N.m.s/rad]
  o.b_pata   = 8.0;         % amortiguamiento a lo largo de la pata [N.s/m]
  o.mu_piso  = 0.7;         % coeficiente de friccion rueda-piso

  % ---------- sobrescribir con los pares nombre/valor ----------
  for i = 1:2:numel(varargin)
    campo = varargin{i};
    if ~isfield(o, campo)
      error('params_robot: parametro desconocido "%s"', campo);
    end
    o.(campo) = varargin{i+1};
  end

  % ---------- relaciones adimensionales de la geometria ----------
  switch lower(o.geom)
    case 'grupo'      % la del grupo (la de la GUI de MATLAB)
      k.AD = 1.400; k.BC = 1.350; k.CD = 0.510; k.DP = 1.400;
      k.delta = 164;            % grados, medidos de D->C hacia D->P
      k.ang_AB = 45;            % grados, orientacion de la bancada
      k.th = [320 350];         % grados, recorrido del motor
    case 'hibrida'    % del segundo barrido: mas giro de manivela, menos par
      k.AD = 1.000/1.131; k.BC = 1.531/1.131; k.CD = 0.733/1.131; k.DP = 1.698/1.131;
      k.delta = 180; k.ang_AB = 0; k.th = [0 111];
    otherwise
      error('params_robot: geometria "%s" no definida', o.geom);
  end

  mm = 1e-3; g = 1e-3; d2r = pi/180;

  P.geom   = lower(o.geom);
  P.k      = k;
  P.rama   = o.rama;
  P.s      = o.s * mm;
  P.AB     = P.s;
  P.AD     = k.AD * P.s;
  P.BC     = k.BC * P.s;
  P.CD     = k.CD * P.s;
  P.DP     = k.DP * P.s;
  P.delta  = k.delta * d2r;
  P.delta_plano = (180 - k.delta) * d2r;   % el que se acota en el plano, entre DC y la prolongacion de PD
  P.ang_AB = k.ang_AB * d2r;
  P.A      = [0 0];
  P.B      = P.s * [cos(P.ang_AB) sin(P.ang_AB)];
  P.th     = k.th * d2r;

  P.Rw     = o.Dw/2 * mm;
  P.Dw     = o.Dw * mm;
  P.ancho_rueda = o.ancho_rueda * mm;

  % ---------- masas ----------
  P.m.servo  = 2 * o.m_servo * g;          % 2 servos de hombro, en A
  P.m.motorw = 2 * o.m_motor_rueda * g;    % 2 motores de rueda, en P
  P.m.rueda  = 2 * o.m_rueda * g;          % 2 ruedas, en P
  P.m.barras = 8 * o.m_barra * g;          % 4 barras x 2 patas
  P.m.placas = 2 * o.m_placa * g;          % 2 placas laterales
  P.m.torn   = o.m_tornilleria * g;
  P.m.caja   = (o.m_bateria + o.m_electronica + o.m_caja) * g;
  P.m.total  = P.m.servo + P.m.motorw + P.m.rueda + P.m.barras + ...
               P.m.placas + P.m.torn + P.m.caja;

  % ---------- placa lateral: la pieza que lleva los DOS pivotes fijos ----------
  m0 = o.margen_placa * mm;
  P.placa.x = [min(P.A(1),P.B(1))-m0, max(P.A(1),P.B(1))+m0];
  P.placa.y = [min(P.A(2),P.B(2))-m0, max(P.A(2),P.B(2))+m0];
  P.placa.largo   = diff(P.placa.x);
  P.placa.alto    = diff(P.placa.y);
  P.placa.espesor = o.esp_placa * mm;
  P.placa.margen  = m0;

  % ---------- cabina (bateria + electronica) ----------
  P.chasis.largo = o.ch_largo * mm;
  P.chasis.alto  = o.ch_alto  * mm;
  P.chasis.ancho = o.ch_ancho * mm;
  P.chasis.yc    = o.ch_yc * mm;
  if isempty(o.ch_xc)
    P.chasis.xc = xc_por_balance(P);        % lo posiciona para que el CoM caiga en x=0
  else
    P.chasis.xc = o.ch_xc * mm;
  end

  % ---------- bateria dentro de la caja y balance resultante ----------
  P.m.bateria = o.m_bateria * g;
  P.m.resto_caja = P.m.caja - P.m.bateria;     % electronica + estructura, repartida
  lim_ade = P.chasis.xc - P.chasis.largo/2 + o.marg_bat*mm;   % lo mas adelante que entra
  lim_atr = P.chasis.xc + P.chasis.largo/2 - o.marg_bat*mm;
  if isempty(o.x_bat)
    P.x_bat = lim_ade;                          % por defecto: bateria bien adelante
  else
    P.x_bat = min(max(o.x_bat*mm, lim_ade), lim_atr);
  end
  P.x_bat_lim = [lim_ade lim_atr];
  P.balance = balance_masas(P);

  % ---------- parametros dinamicos ----------
  P.g = 9.81;
  P.act.tau_w_max = o.tau_rueda_max * 2;        % las dos ruedas juntas [N.m]
  P.act.w_w_max   = o.w_rueda_max * 2*pi/60;    % [rad/s]
  P.act.tau_s_max = o.tau_hombro_max * 2;       % los dos hombros juntos [N.m]
  P.act.w_s_max   = o.w_hombro_max * pi/180;    % [rad/s]
  P.act.kp_servo  = o.tau_servo_kp * 2;
  P.b.rueda = o.b_rueda * 2;
  P.b.pitch = o.b_pitch;
  P.b.pata  = o.b_pata;
  P.mu_piso = o.mu_piso;

  P.din = inercias(P, o);

  P.unidades = 'SI (m, kg, rad). Usar mostrar_params(P) para ver en mm.';
end

% -------------------------------------------------------------------------
function D = inercias(P, o)
%INERCIAS  Reparte las masas en 'suspendido' (cuerpo que cabecea) y 'no suspendido'
%   (rueda + motor de rueda), y calcula m_b, J_b y la posicion del CoM del cuerpo.
  g = 1e-3; mm = 1e-3;
  K = barrido_pata(P, 41);
  if ~K.ok
    D = struct('m_w',0.16,'m_b',0.70,'J_w',6e-5,'J_b',2e-3,'r_com',[0 0],'l0',0.15, ...
               'l_min',0.10,'l_max',0.20,'G',0.2); return;
  end

  % --- no suspendido: ruedas + motores de rueda, en el eje P ---
  D.m_w = P.m.rueda + P.m.motorw;
  D.J_w = 0.5 * P.m.rueda * P.Rw^2 ...          % rueda como disco
        + 2 * 0.5 * (o.m_motor_rueda*g) * (0.015)^2;   % rotor del motor, aprox
  % --- suspendido: todo lo demas, en el marco del cuerpo (origen en A) ---
  [rb, Jb_rel] = centroide_barras(P, K);
  it = { P.m.servo,  [0 0],                       0.040, 0.040 ;   ...
         P.m.barras, rb,                          0.001, 0.001 ;   ...
         P.m.placas, [(P.A(1)+P.B(1))/2 (P.A(2)+P.B(2))/2], P.placa.largo, P.placa.alto ; ...
         P.m.torn,   [(P.A(1)+P.B(1))/2 (P.A(2)+P.B(2))/2], 0.060, 0.060 ; ...
         P.m.resto_caja, [P.chasis.xc P.chasis.yc], P.chasis.largo, P.chasis.alto ; ...
         P.m.bateria,[P.x_bat P.chasis.yc],       0.070, 0.035 };
  mtot = 0; r = [0 0];
  for i = 1:size(it,1), mtot = mtot + it{i,1}; r = r + it{i,1}*it{i,2}; end
  r = r / mtot;
  J = P.m.barras * Jb_rel;                      % inercia propia de las barras
  for i = 1:size(it,1)
    m = it{i,1}; d = it{i,2} - r;
    J = J + m*(it{i,3}^2 + it{i,4}^2)/12 + m*(d*d');
  end
  D.m_b = mtot; D.r_com = r; D.J_b = J;

  % --- largo del pendulo: del eje de rueda al CoM del cuerpo ---
  v = K.valido;
  prof = -K.P(v,2);                              % A por encima del eje
  D.l_min = min(prof) + r(2);
  D.l_max = max(prof) + r(2);
  D.l0    = (D.l_min + D.l_max)/2;
  D.G     = K.dzdth;                             % ganancia dl/dtheta [m/rad]

  % --- tabla theta <-> l y ganancia local G(l), para el modelo dinamico ---
  th  = K.theta(v);  ll = prof + r(2);           % l = profundidad del eje + y del CoM
  th = th(:); ll = ll(:);
  if ll(end) < ll(1), th = flipud(th); ll = flipud(ll); end   % l creciente
  [ll, iu] = unique(ll); th = th(iu);
  % theta normalizado: crece cuando la pata se ESTIRA (convencion de control)
  D.map.l  = ll;
  D.map.th = th;
  D.map.G  = abs(gradient(ll, th));               % |dl/dtheta| local [m/rad]
  D.G      = mean(D.map.G);
  % ajuste lineal G(l) = a + b*l : evita interp1 dentro de la ODE (10x mas rapido)
  Aj = [ones(numel(ll),1) ll];
  D.Gfit = Aj \ D.map.G(:);
  D.Gerr = max(abs(Aj*D.Gfit - D.map.G(:)));
  Th = Aj \ D.map.th(:);
  D.THfit = Th;
  D.prof  = [min(prof) max(prof)];
  D.theta = [P.th(1) P.th(2)];
end

% -------------------------------------------------------------------------
function [rc, Jrel] = centroide_barras(P, K)
%CENTROIDE_BARRAS  Centroide y momento de inercia de las cuatro barras,
%   promediados sobre el recorrido. Cada barra pesa en proporcion a su largo.
  v = K.valido;
  Lg = [P.AD P.BC P.CD P.DP]; Lg = Lg / sum(Lg);
  n = sum(v); A_=K.A(v,:); B_=K.B(v,:); C_=K.C(v,:); D_=K.D(v,:); W_=K.P(v,:);
  cen = Lg(1)*(A_+D_)/2 + Lg(2)*(B_+C_)/2 + Lg(3)*(C_+D_)/2 + Lg(4)*(D_+W_)/2;
  rc = mean(cen, 1);
  % inercia propia aproximada: barra delgada, l^2/12, mas el traslado al centroide
  J = 0;
  for i = 1:4
    switch i
      case 1, p1=A_; p2=D_; case 2, p1=B_; p2=C_;
      case 3, p1=C_; p2=D_; case 4, p1=D_; p2=W_;
    end
    ci = (p1+p2)/2; d = ci - repmat(rc,n,1);
    J = J + Lg(i)*(Lg(i)*sum(Lg.*0)+0) ;  %#ok<NASGU>
    J = J + mean(Lg(i)*( (norm(P.AD)*0) + (Lg(i)*0) ) );  %#ok<NASGU>
  end
  Jrel = sum(Lg .* [P.AD P.BC P.CD P.DP].^2) / 12 + mean(sum((cen-repmat(rc,n,1)).^2,2));
end

% -------------------------------------------------------------------------
function B = balance_masas(P)
%BALANCE_MASAS  Centro de masa del conjunto respecto de la vertical de contacto.
  K = barrido_pata(P, 61);
  if ~K.ok, B.x_com = NaN; B.inclinacion = NaN; B.x_barras = NaN; return; end
  rb = centroide_barras(P, K); xb = rb(1);
  xp = (P.A(1) + P.B(1)) / 2;
  Mx = P.m.barras*xb + P.m.placas*xp + P.m.torn*xp + ...
       P.m.resto_caja*P.chasis.xc + P.m.bateria*P.x_bat;
  % servos en A y motores/ruedas en P: los dos sobre x = 0, no aportan momento
  B.x_barras = xb;
  B.x_com    = Mx / P.m.total;
  h_com      = mean(K.z) + P.chasis.yc;        % altura aproximada del CoM
  B.h_com    = h_com;
  B.inclinacion = atan2(B.x_com, h_com);       % inclinacion permanente para compensar [rad]
end

% -------------------------------------------------------------------------
function xc = xc_por_balance(P)
% Ubica el centro de la caja para que el centro de masa del conjunto
% caiga sobre la vertical del punto de contacto de la rueda (x = 0).
  K = barrido_pata(P, 41);
  if ~K.ok
    xc = -0.035; return;                    % valor de respaldo si no cierra
  end
  xbar = mean([K.A(:,1) K.B(:,1) K.C(:,1) K.D(:,1) K.P(:,1)], 1);
  x_barras = mean([xbar(1) xbar(3) xbar(4) xbar(5)]);   % centroide grueso de las barras
  x_placas = (P.A(1) + P.B(1)) / 2;
  Mx = P.m.barras * x_barras + P.m.placas * x_placas + P.m.torn * x_placas;
  % servos en A, motores y ruedas en P: ambos sobre x = 0, no aportan momento
  xc = -Mx / P.m.caja;
end
