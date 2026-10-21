function o = parametros_fisicos(variante)
%PARAMETROS_FISICOS  Fuente comun de valores físicos editables del proyecto.
%
%   Unidades de entrada: mm, g, grados (comodas para CAD y balanza); donde se indica, SI.
%   Cada linea dice de donde salio el valor y que afecta. Los adaptadores de cinemática,
%   dinámica y simulación leen este archivo, convierten a SI y calculan lo derivado.
%
%   Dos formas de cambiar un valor:
%     1) editar aca y volver a correr (queda para todos);
%     2) sin editar, para probar:   p = parametros_dinamica_pata('segunda_iteracion', 'mu', 0.4, 'm_AD', 35);
%
%   Variantes:
%     'segunda_iteracion' (DEFAULT) = el CAD actual, diseño_mecanico/segunda_iteracion (STEP del 14/9/2026):
%                         barras a escala 80 (AD 112, BC 108, CD 40.8, DP 112), bancada 80 mm a 45 grados,
%                         servo de 40 kg cm, motor de rueda GA25-370 1:20 con encoder (COMPRADO).
%     'corregido'         = baseline histórico a escala 100 (AD 140, BC 135, CD 51, DP 140, bancada 100 a 45),
%                         servo DS3225MG y motor JGA25-371. Es lo que usan los resultados del 14/9 en
%                         simulacion/dinamica_pata_v1/resultados. No corresponde a ningún CAD construido.

  if nargin < 1 || isempty(variante), variante = 'segunda_iteracion'; end

  % =========================== 1. GEOMETRIA DEL CUATRO BARRAS (mm, grados) ===========================
  % Las barras son una familia a escala s: AD = 1.40 s, BC = 1.35 s, CD = 0.51 s, DP = 1.40 s, y la bancada
  % AB = s a 45 grados. Cotas medidas sobre los STEP (agujeros de cada eslabon y posicion de cada pieza en el
  % ensamble; ver docs/gestion/2026-09-19-auditoria-limpieza.md, seccion 1.2). Cambiar si se reimprimen barras.
  o.k_AD = 1.400;        % manivela (la mueve el servo)
  o.k_BC = 1.350;        % balancin
  o.k_CD = 0.510;        % acoplador, tramo C-D
  o.k_DP = 1.400;        % acoplador, tramo D-P (eje de rueda)
  o.delta = 164;         % angulo de D->C a D->P en el acoplador [grados] (el plano acota 16, que es el suplementario)
  o.th = [320 350];      % recorrido del servo [grados]: 320 = pata estirada (de pie), 350 = plegada
  o.rama = +1;           % rama de armado del cuatro barras (+1 = como esta el CAD)
  switch lower(variante)
    case 'segunda_iteracion'
      o.s_barras = 80;                  % escala de las barras [mm] -> AD 112, BC 108, CD 40.8, DP 112 (STEP del 14/9)
      o.AB = 80;   o.ang_AB = 45;       % bancada A-B [mm, grados]: la intencion del diseño. OJO: en el STEP B esta a 77.9 mm
                                        % y 46.6 grados de A (altura justa, 3 mm corto en horizontal). Corregir en cabeza_v31.
      o.N = 20;    o.encoder = true;    % GA25-370 COMPRADO: reductor 1:20, 300 rpm en vacio a 12 V
      o.nombre_motor = 'GA25-370 12V 1:20 (300 rpm en vacio) con encoder de cuadratura, 11 PPR en el rotor';
      o.m_motor = 95;                   % cada motorreductor GA25-370 [g] (cuerpo 25 mm, caja 21 mm; estimado). PESAR.
      o.m_servo = 47.1;                   % parte de los 542 g medidos. OJO: la ficha del DS3240 da ~60 g y un servo
                                        % pesa lo que pesa, no se escala. Es un relleno hasta tener el desglose: PESARLO SUELTO.
      o.tau_s_max = 40*0.0981;          % par maximo del servo [N m] = 40 kg cm. Verificar a que tension lo da la publicacion
      o.w_nl_servo = 7.0;               % velocidad en vacio [rad/s] (0.15 s por 60 grados, tipico de esta clase; verificar)
      o.nombre_servo = 'servo digital 40 kg cm (tipo DS3240)';
    case 'corregido'
      o.s_barras = 100;                 % escala 100 -> AD 140, BC 135, CD 51, DP 140
      o.AB = 100;  o.ang_AB = 45;       % bancada a escala con las barras
      o.N = 21.3;  o.encoder = true;    % motor JGA25-371 12 V 280 rpm, reductor 1:21.3, con encoder
      o.nombre_motor = 'JGA25-371 12V 280rpm (1:21.3, con encoder)';
      o.m_motor = 95;                   % catalogo JGA25
      o.m_servo = 60;                   % DS3225MG (hoja de datos)
      o.tau_s_max = 2.4;                % DS3225MG a 6.8 V: 24.5 kg cm
      o.w_nl_servo = 7.7;               % 0.13 s por 60 grados
      o.nombre_servo = 'DS3225MG';
    otherwise
      error('parametros_fisicos: variante "%s" no definida (usar ''segunda_iteracion'' o ''corregido'')', variante);
  end
  e = o.s_barras/100;    % escala de las barras respecto de la primera iteracion, de donde salieron masas e inercias

  % ======================================== 2. RUEDA ========================================
  o.Rw = 33;             % radio de rueda [mm] (rueda comercial de 65 mm del CAD). Afecta velocidad, par y altura.
  o.m_rueda = 30;        % masa de cada rueda [g] (estimada: goma + nucleo). PESAR.
  o.J_rueda = [];        % inercia de cada rueda [kg m2]; [] = disco macizo 0.5*m*R^2. Poner un numero si se mide.
  o.b_w = 1e-4;          % friccion viscosa en el eje de rueda [N m s/rad] (rodamientos; supuesto)

  % ============================ 3. MASAS DE LAS PIEZAS (g) y su posicion ============================
  % --- 21/10/2026: PRIMERA TANDA DE MEDICIONES ---
  % Las tres barras se pesaron una por una. El resto de la caja se obtuvo pesando el robot entero
  % SIN ruedas ni motores de rueda (670 g) y restando las seis barras: quedan 542 g de caja.
  % Como no hay desglose de esos 542 g, los seis items de la caja se escalan parejo por 542/667.
  % Se comprobo que el reparto no importa: repartiendo parejo o sacandole todo a las piezas
  % impresas, el brazo l cambia de 8.17 a 8.10 cm y el polo inestable de 7.44 a 7.52 1/s.
  % SIGUEN SIN PESAR: la rueda y el motor de rueda, que no estan todavia.
  % Posiciones del CoM respecto de A [mm] (x hacia atras, y arriba).
  % Los seis items de abajo suman 542 g, que es lo medido. El reparto entre ellos sigue siendo
  % el estimado, escalado por 542/667; sus posiciones de CoM no cambiaron.
  o.m_cabina = 168.2;     o.r_cabina = [13.1 5.0];       % parte de los 542 g medidos (se estimaba 207)
  o.m_tapa = 92.6;       o.r_tapa = [-28.1 47.2];       % parte de los 542 g medidos (se estimaba 114)
  o.r_servo = [-9.7 0];                                 % cada servo, en A (la masa esta en la seccion 1)
  o.m_bateria = 97.5;     o.r_bateria = [-18.5 21.0];    % LiPo 3S ~1000 mAh (estimada), centro de la cabina
  o.m_electronica = 48.8;  o.r_electronica = [-18.5 21.0];% ESP32 + driver + IMU + BEC + cables (estimada)
  o.m_tornilleria = 40.6;  o.r_tornilleria = [0 0];       % pernos, ejes, rodamientos (estimada)
  o.m_carga = 0;         o.r_carga = [-18.5 21.0];      % carga extra en la cabina (por defecto nada)
  o.m_AD = 30;           o.f_AD = 0.428;                % MEDIDO 21/10 (se estimaba 23.2: -23 %). f = CoM, fraccion de A hacia D
  o.m_BC = 23;           o.f_BC = 0.5;                  % MEDIDO 21/10. Se estimaba 5.6 g: el modelo lo tenia CUATRO veces mas liviano
  o.m_CDP = 11;          o.f_CDP = 0.3145;              % MEDIDO 21/10 (se estimaba 15.6: +42 %). f desde D hacia P
  o.m_mecanismo = 110*e; % masa que mueve el servo cuando hay flexor (las barras) [g]
  % Inercias propias de cada pieza respecto de su CoM, eje de cabeceo [kg m2]. Del mallado del STEP de la primera iteracion.
  o.J_cabina = 4.8477e8*1.2e-12;  o.J_tapa = 2.7331e8*1.2e-12;
  % Inercias de las barras: la forma sale del mallado del STEP, pero la masa es la medida, asi
  % que se escalan por masa_medida/masa_estimada. La geometria no cambio, solo la densidad real.
  o.J_AD  = 6.4467e7*1.1e-12*e^3 * (30/(29*e));
  o.J_BC  = 1.5631e7*1.1e-12*e^3 * (23/(7*e));
  o.J_CDP = 5.8125e7*1.1e-12*e^3 * (11/(19.5*e));
  o.J_cuerpo = [];       % inercia total del cuerpo suspendido respecto de su CoM [kg m2]; [] = calcularla de las piezas

  % ================================ 4. CONTACTO RUEDA-PISO ================================
  o.mu = 0.7;            % coeficiente de friccion rueda-piso (goma sobre madera/ceramica ~0.7; baldosa lisa ~0.4; supuesto)
  o.v_s = 0.005;         % velocidad de deslizamiento a la que la friccion satura [m/s] (suaviza Coulomb; numerico)
  o.c_v = 0.5;           % amortiguacion viscosa del contacto tangencial [N s/m] (numerico, chico)
  o.k_contacto = 30e3;   % rigidez del neumatico por rueda [N/m] (goma 65 mm; SUPUESTO: medir apretando la rueda)
  o.c_contacto = 60;     % amortiguacion del neumatico por rueda [N s/m] (~30 % de amortiguamiento critico; supuesto)

  % ================================ 5. PISO CON ESCALONES ================================
  o.piso_x0 = 0.5;       % donde termina el primer descanso, ahi baja el primer escalon [m]
  o.piso_alto = 0.16;    % alto de cada escalon [m]
  o.piso_ancho = 0.30;   % ancho de cada descanso [m]
  o.piso_n = 0;          % cantidad de escalones que bajan (0 = piso plano; los escenarios lo fijan)

  % =============================== 6. FLEXOR DE LA PATA (opcional) ===============================
  o.flexor = false;      % true = resorte en serie en la pata. El CAD actual no lo tiene (barras rigidas)
  o.k_flexor = 1080;     % rigidez por pata [N/m] (40 mm de carrera para 0.7 J, del dimensionamiento original)
  o.c_flexor = 8;        % amortiguacion por pata [N s/m] (supuesto; el TPU de la rueda no esta incluido)
  o.carrera_flexor = 40; % carrera maxima [mm]

  % ================================ 7. MOTOR DC + REDUCTOR ================================
  % Parametros del GA25-370 COMPRADO, deducidos de su ficha (ver eta_reductor abajo). La columna
  % de torsion de esa ficha es inconsistente y NO se usa; la electrica si, y cierra consigo misma.
  o.R_m = 10.28;         % resistencia de armadura [ohm]. DEDUCIDA de la ficha: resolviendo
                         %   12 = R*i + Ke*N*w  en los puntos de vacio (300 rpm, 60 mA) y de carga
                         %   (235 rpm, 300 mA). Predice 1.17 A de bloqueo contra los <=1.1 A de la
                         %   ficha: la parte electrica de la tabla es coherente consigo misma.
  o.i_vacio = 0.060;     % corriente en vacio [A] (ficha). Representa la friccion del conjunto.
  o.L_m = 1.5e-3;        % inductancia [H] (tipica; su constante L/R = 0.15 ms se desprecia)
  o.w_nl_motor_rpm = 6000; % velocidad en vacio del ROTOR a 12 V [rpm] = 300 rpm de salida x 20 -> Ke = Kt
  o.J_r = 6e-7;          % inercia del rotor [kg m2] (tipica de un 370; NO medida). Reflejada vale N^2*J_r
  o.tau_c = 0.0015;      % friccion de Coulomb del rotor [N m] (da la corriente en vacio ~0.1 A)
  o.b_m = 1e-6;          % friccion viscosa del rotor [N m s/rad]
  o.gear_rigido = true;  % true = rotor solidario a la rueda; false = eje elastico con juego (mas lento)
  o.k_g = 50;            % rigidez del eje/reductor [N m/rad] (solo si gear_rigido = false; supuesto)
  o.c_g = 0.05;          % amortiguacion del eje [N m s/rad]
  o.juego_deg = 1.5;     % juego total del reductor en la salida [grados] (tipico de reductores rectos)
  o.eta = 0.7;           % rendimiento que asume el CONTROLADOR para convertir par en tension
  o.eta_reductor = 0.75; % rendimiento mecanico del reductor [-]. SUPUESTO tipico de engranajes rectos.
                         % OJO: la columna de TORSION de la ficha no cierra con la electrica. El punto de
                         % carga (160 g cm a 300 mA) exigiria 18 % de rendimiento y el de bloqueo
                         % (5.6 kg cm a 1.1 A) exigiria 146 %, que es imposible. Ademas 160 g cm figura
                         % identico para 1:44 y 1:20. Se le cree a la parte electrica, que SI es coherente,
                         % y el par se calcula: eta*N*Kt*(i - i_vacio) = 3.1 kg cm por motor al bloqueo,
                         % no los 5.6 que anuncia. MEDIR con un brazo y una balanza antes de confiar.

  % ===================================== 8. BATERIA =====================================
  o.V_bat = 11.1;        % tension [V] (LiPo 3S: 12.6 llena, 11.1 nominal, 9.6 baja)
  o.R_bat = 0.05;        % resistencia interna + cables [ohm]

  % ================================ 9. SERVO DE HOMBRO ================================
  % Masa, par maximo y velocidad en vacio estan en la seccion 1 (dependen de la variante).
  o.Kp_s = 45;           % ganancia del lazo interno del servo [N m/rad] (par maximo con ~5 grados de error; SUPUESTO: medir)
  o.Kd_s = 1.0;          % amortiguacion del lazo interno [N m s/rad] (supuesto)
  o.n_servos = 2;        % un servo por pata
  o.b_servo = 0;         % friccion viscosa equivalente del eje [N m s/rad]; pendiente de identificar
  o.k_tope_servo = 50;   % rigidez angular del tope [N m/rad]; parametro numerico provisional
  o.c_tope_servo = 1;    % amortiguamiento angular del tope [N m s/rad]; parametro numerico provisional

  % ============================ 10. CUERPO: amortiguamientos y topes ============================
  o.b_pitch = 1e-3;      % amortiguamiento del cabeceo [N m s/rad] (aire, cables; supuesto chico)
  o.b_pata = 8.0;        % amortiguamiento a lo largo de la pata [N s/m] (friccion de los pivotes; supuesto)
  o.k_tope = 2e4;        % rigidez de los topes de fin de carrera [N/m] (numerico, rigido)
  o.c_tope = 60;         % amortiguacion de los topes [N s/m]

  % =============================== 11. SENSORES Y CONTROL ===============================
  o.Ts = 5e-3;           % periodo de control [s] (200 Hz)
  o.n_delay = 1;         % retardo de las medidas [muestras] (1 = 5 ms)
  o.d_imu = [-18.5 21.0];% posicion de la IMU respecto de A [mm] (centro de la cabina)
  o.gyro_bias_dps = 0.5; % sesgo del giroscopo [grados/s] (MPU6050 tipico)
  o.gyro_rms_dps = 0.1;  % ruido del giroscopo [grados/s rms]
  o.gyro_sat_dps = 2000; % fondo de escala del giroscopo [grados/s]
  o.acc_rms_g = 0.02;    % ruido del acelerometro [g rms]
  o.CPR_motor = 11;      % pulsos por vuelta del encoder en el eje del motor (x4 por cuadratura, x N por el reductor)
  o.k_comp = 0.005;      % ganancia del filtro complementario (tau = Ts/k = 1 s)
  o.fc_vel = 20;         % filtro de la velocidad de rueda [Hz]
  o.umbral_vuelo = 3;    % si | |f| - g | supera esto [m/s2], la IMU se considera en vuelo y no corrige el angulo
  o.semilla = 1;         % semilla del ruido (reproducibilidad)
  o.g = 9.81;            % gravedad [m/s2]
end
