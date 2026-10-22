function archivo = construir_segway_completo(carpeta_destino, nombre_modelo)
%CONSTRUIR_SEGWAY_COMPLETO  Arma el modelo completo del Segway en Simulink.
%
%   El modelo esta pensado para ENTENDERSE, no para ser compacto. Seis bloques
%   grandes de izquierda a derecha, cada uno una etapa fisica:
%
%     CONSIGNAS -> CONTROL -> ACTUADORES -> PLANTA -> SENSORES -+
%          ^                                                    |
%          +----------------------------------------------------+
%
%   Los CUATRO motores estan por separado, cada uno con su bloque, aunque por
%   ahora los de rueda reciban la misma tension y los servos la misma posicion.
%   Los SENSORES son bloques propios, con su entrada de ruido puesta en cero.
%
%   Dentro de la planta no hay matrices anonimas: cada senal tiene el nombre de
%   lo que es fisicamente (suma de fuerzas, suma de momentos, masa efectiva,
%   inercia del cuerpo, acople). Las dos ecuaciones de Newton-Euler se ven como
%   lo que son y despues se resuelven las dos aceleraciones a la vez, porque
%   estan acopladas.
%
%   Lo construye INICIAR_SEGWAY.m, que antes deja en el workspace todas las
%   variables que el modelo lee.
%
%   Ver tambien INICIAR_SEGWAY.

    if nargin < 1 || isempty(carpeta_destino), carpeta_destino = pwd; end
    if nargin < 2 || isempty(nombre_modelo), nombre_modelo = 'segway_completo'; end
    modelo = nombre_modelo;

    if bdIsLoaded(modelo), close_system(modelo, 0); end
    new_system(modelo);
    set_param(modelo, 'Solver', 'ode45', 'RelTol', '1e-9', 'AbsTol', '1e-11', ...
        'MaxStep', '1e-3', 'StopTime', '8');

    %% ======================= los seis bloques grandes =======================
    crear_consignas([modelo '/Consignas']);
    set_param([modelo '/Consignas'], 'Position', [150 230 300 330]);

    crear_control([modelo '/Control']);
    set_param([modelo '/Control'], 'Position', [420 230 570 330]);

    crear_actuadores([modelo '/Actuadores']);
    set_param([modelo '/Actuadores'], 'Position', [700 200 870 370]);

    crear_planta([modelo '/Planta del robot']);
    set_param([modelo '/Planta del robot'], 'Position', [1000 230 1170 330]);

    crear_sensores([modelo '/Sensores']);
    set_param([modelo '/Sensores'], 'Position', [1300 230 1470 330]);

    %% ======================= el cableado de arriba =======================
    L = @(o, d) add_line(modelo, o, d, 'autorouting', 'on');
    L('Consignas/1', 'Control/2');                 % z_ref
    L('Consignas/2', 'Actuadores/2');              % postura pedida a las patas
    L('Sensores/1',  'Control/1');                 % lo que el control CREE que pasa
    L('Control/1',   'Actuadores/1');              % tension a cada rueda
    L('Planta del robot/1', 'Actuadores/3');       % estado REAL: lo que ve el motor
    L('Actuadores/1', 'Planta del robot/1');       % par total en las ruedas
    L('Actuadores/2', 'Planta del robot/2');       % postura real de las patas
    L('Planta del robot/1', 'Sensores/1');
    L('Actuadores/2', 'Sensores/2');

    %% ======================= registro =======================
    registrar(modelo, 'Planta del robot/1', 'z real',      'sl_z',      [1560 180 1620 210]);
    registrar(modelo, 'Sensores/1',         'z medido',    'sl_z_med',  [1560 240 1620 270]);
    registrar(modelo, 'Control/1',          'tensiones',   'sl_U',      [1560 300 1620 330]);
    registrar(modelo, 'Actuadores/3',       'par de cada motor', 'sl_tau', [1560 360 1620 390]);
    registrar(modelo, 'Actuadores/1',       'par total tras el limite', 'sl_tau_total', [1560 540 1620 570]);
    registrar(modelo, 'Actuadores/2',       'postura real','sl_theta',  [1560 420 1620 450]);
    registrar(modelo, 'Consignas/1',        'consigna',    'sl_ref',    [1560 480 1620 510]);

    %% ======================= areas del nivel de arriba =======================
    area(modelo, 'a1', 'CONSIGNAS', [110 160 330 420]);
    area(modelo, 'a2', 'CONTROL   (LQR)', [390 160 600 420]);
    area(modelo, 'a3', 'ACTUADORES   (4 motores)', [660 160 910 470]);
    area(modelo, 'a4', 'PLANTA   la fisica del robot', [960 160 1210 420]);
    area(modelo, 'a5', 'SENSORES   (hoy ideales)', [1260 160 1510 420]);
    area(modelo, 'a6', 'REGISTRO', [1530 160 1660 600]);

    nota(modelo, [110 50 1660 130], sprintf([ ...
        'SEGWAY CON PATAS EXTENSIBLES  --  modelo completo\n\n' ...
        'Se lee de izquierda a derecha. Cada area es una etapa fisica, y lo que vuelve de SENSORES a CONTROL cierra el lazo.']));

    nota(modelo, [110 560 1660 820], sprintf([ ...
        'QUE HACE CADA BLOQUE\n' ...
        '   CONSIGNAS    adonde se le pide ir y en que postura poner las patas\n' ...
        '   CONTROL      un LQR: mira los cuatro estados a la vez y decide cuanta tension mandarle a cada rueda\n' ...
        '   ACTUADORES   los cuatro motores, cada uno en su bloque: dos de rueda y dos de pata\n' ...
        '   PLANTA       la fisica: suma de fuerzas, suma de momentos, y las dos aceleraciones que salen de ahi\n' ...
        '   SENSORES     lo que el robot puede medir. Hoy miden perfecto; el ruido esta puesto en cero\n\n' ...
        'DOS COSAS QUE CONVIENE MIRAR\n\n' ...
        '1) Hay DOS caminos que salen de la planta. El que va a SENSORES y de ahi al control es lo que el robot CREE que le pasa.\n' ...
        '   El que va directo a ACTUADORES es lo que de verdad le pasa, porque el motor siente la velocidad real, no la medida.\n' ...
        '   Hoy los dos coinciden porque los sensores son ideales. Cuando se les ponga ruido o retardo van a separarse,\n' ...
        '   y ahi se ve si el control aguanta.\n\n' ...
        '2) tau (par) = lo que el motor le tuerce a la rueda, en N m. Por reaccion, la rueda le devuelve -tau al cuerpo.\n' ...
        '   ESA reaccion es la unica forma que tiene el robot de inclinarse a proposito: no hay nada mas empujandolo.']));

    %% ======================= guardar =======================
    if ~exist(carpeta_destino, 'dir'), mkdir(carpeta_destino); end
    archivo = fullfile(carpeta_destino, [modelo '.slx']);
    save_system(modelo, archivo, 'OverwriteIfChangedOnDisk', true);
    close_system(modelo, 0);
end


% =========================================================================
%                              C O N S I G N A S
% =========================================================================
function crear_consignas(ruta)
%CREAR_CONSIGNAS  Lo que se le pide al robot: adonde ir y en que postura.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    delete_block([ruta '/In1']);
    set_param([ruta '/Out1'], 'Name', 'z ref', 'Position', [560 193 590 207]);
    add_block('simulink/Sinks/Out1', [ruta '/postura ref'], 'Port', '2', ...
        'Position', [560 383 590 397]);

    add_block('simulink/Sources/Step', [ruta '/adonde ir'], ...
        'Time', 't_consigna', 'Before', '0', 'After', 'x_destino', ...
        'Position', [120 170 190 230]);
    add_block('simulink/Sources/Constant', [ruta '/velocidad, angulo y giro pedidos'], ...
        'Value', '[0; 0; 0]', 'Position', [120 260 330 310]);
    add_block('simulink/Signal Routing/Mux', [ruta '/armar z ref'], 'Inputs', '2', ...
        'DisplayOption', 'bar', 'Position', [420 170 425 310]);

    add_block('simulink/Sources/Step', [ruta '/postura de las patas'], ...
        'Time', 't_patas', 'Before', 'theta_pata_0', 'After', 'theta_pata_fin', ...
        'Position', [120 355 190 425]);

    add_line(ruta, 'adonde ir/1', 'armar z ref/1', 'autorouting', 'on');
    add_line(ruta, 'velocidad, angulo y giro pedidos/1', 'armar z ref/2', 'autorouting', 'on');
    add_line(ruta, 'armar z ref/1', 'z ref/1', 'autorouting', 'on');
    add_line(ruta, 'postura de las patas/1', 'postura ref/1', 'autorouting', 'on');

    area(ruta, 'c1', 'EQUILIBRIO Y POSICION:  z_ref = [x deseado ; 0 ; 0 ; 0]', [90 140 620 330]);
    area(ruta, 'c2', 'PATAS:  angulo pedido al servo, en radianes (10 grados = plegada, 40 = estirada)', [90 340 620 450]);
    nota(ruta, [90 470 620 560], sprintf([ ...
        'Por defecto la postura es constante, asi que el robot se comporta como el modelo verificado.\n' ...
        'Si se le pone un escalon (theta_pata_fin distinto de theta_pata_0) las patas se mueven y\n' ...
        'cambian la altura del cuerpo: ver el capitulo 9 del PDF del modelo.']));
end


% =========================================================================
%                                C O N T R O L
% =========================================================================
function crear_control(ruta)
%CREAR_CONTROL  U = -K (z_medido - z_ref), y reparto a las dos ruedas.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'z medido', 'Position', [60 193 90 207]);
    add_block('simulink/Sources/In1', [ruta '/z ref'], 'Port', '2', ...
        'Position', [60 253 90 267]);
    set_param([ruta '/Out1'], 'Name', 'tension a cada rueda', 'Position', [860 263 890 277]);

    add_block('simulink/Math Operations/Sum', [ruta '/error de estado'], ...
        'Inputs', '+-', 'IconShape', 'rectangular', 'Position', [180 185 230 275]);
    add_block('simulink/Math Operations/Gain', [ruta '/ganancia K del LQR'], ...
        'Gain', '-K', 'Multiplication', 'Matrix(K*u)', 'Position', [300 200 420 260]);

    add_block('simulink/Math Operations/Gain', [ruta '/las dos ruedas igual'], ...
        'Gain', '[1; 1]', 'Multiplication', 'Matrix(K*u)', 'Position', [540 185 660 225]);
    add_block('simulink/Sources/Constant', [ruta '/giro pedido'], ...
        'Value', 'giro_ref', 'Position', [300 320 420 360]);
    add_block('simulink/Math Operations/Gain', [ruta '/una rueda mas que la otra'], ...
        'Gain', '[1; -1]', 'Multiplication', 'Matrix(K*u)', 'Position', [540 315 660 355]);
    add_block('simulink/Math Operations/Sum', [ruta '/sumar'], ...
        'Inputs', '++', 'IconShape', 'rectangular', 'Position', [740 230 790 310]);

    add_line(ruta, 'z medido/1', 'error de estado/1', 'autorouting', 'on');
    add_line(ruta, 'z ref/1', 'error de estado/2', 'autorouting', 'on');
    add_line(ruta, 'error de estado/1', 'ganancia K del LQR/1', 'autorouting', 'on');
    add_line(ruta, 'ganancia K del LQR/1', 'las dos ruedas igual/1', 'autorouting', 'on');
    add_line(ruta, 'giro pedido/1', 'una rueda mas que la otra/1', 'autorouting', 'on');
    add_line(ruta, 'las dos ruedas igual/1', 'sumar/1', 'autorouting', 'on');
    add_line(ruta, 'una rueda mas que la otra/1', 'sumar/2', 'autorouting', 'on');
    add_line(ruta, 'sumar/1', 'tension a cada rueda/1', 'autorouting', 'on');

    area(ruta, 'k1', 'EQUILIBRIO:  U = -K (z_medido - z_ref)', [150 160 500 290]);
    area(ruta, 'k2', 'REPARTO A LAS DOS RUEDAS', [510 160 820 390]);
    nota(ruta, [150 420 820 540], sprintf([ ...
        'Por que una sola ganancia K y no cuatro PID: el robot tiene DOS coordenadas que importan\n' ...
        '(avance x e inclinacion phi) y UN solo actuador. Realimentando solo el angulo se equilibra\n' ...
        'pero se va caminando. K mira los cuatro estados a la vez y los pesa. Ver el capitulo 7 del PDF.\n\n' ...
        'El bloque del giro ya esta puesto para cuando se quiera doblar: hoy giro_ref = 0.']));
end


% =========================================================================
%                             A C T U A D O R E S
% =========================================================================
function crear_actuadores(ruta)
%CREAR_ACTUADORES  Los cuatro motores, uno por uno.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'tension a cada rueda', 'Position', [60 193 90 207]);
    add_block('simulink/Sources/In1', [ruta '/postura ref'], 'Port', '2', ...
        'Position', [60 603 90 617]);
    add_block('simulink/Sources/In1', [ruta '/estado real'], 'Port', '3', ...
        'Position', [60 383 90 397]);
    set_param([ruta '/Out1'], 'Name', 'par total en las ruedas', 'Position', [1140 213 1170 227]);
    add_block('simulink/Sinks/Out1', [ruta '/postura real'], 'Port', '2', ...
        'Position', [1140 643 1170 657]);
    add_block('simulink/Sinks/Out1', [ruta '/par de cada motor'], 'Port', '3', ...
        'Position', [1140 323 1170 337]);

    % --- la velocidad relativa del eje rueda-cuerpo: w_rel = v/r - omega
    add_block('simulink/Math Operations/Gain', [ruta '/velocidad relativa rueda-cuerpo'], ...
        'Gain', '[0  1/r  0  -1]', 'Multiplication', 'Matrix(K*u)', ...
        'Position', [160 365 330 415]);

    add_block('simulink/Signal Routing/Demux', [ruta '/separar las dos tensiones'], ...
        'Outputs', '2', 'Position', [160 185 165 265]);

    crear_motor_rueda([ruta '/Motor de rueda IZQUIERDA']);
    set_param([ruta '/Motor de rueda IZQUIERDA'], 'Position', [420 150 600 230]);
    crear_motor_rueda([ruta '/Motor de rueda DERECHA']);
    set_param([ruta '/Motor de rueda DERECHA'], 'Position', [420 260 600 340]);

    add_block('simulink/Signal Routing/Mux', [ruta '/juntar los dos pares'], 'Inputs', '2', ...
        'DisplayOption', 'bar', 'Position', [690 185 695 305]);
    add_block('simulink/Math Operations/Sum', [ruta '/par de las dos ruedas'], ...
        'Inputs', '++', 'IconShape', 'rectangular', 'Position', [760 180 810 310]);
    add_block('simulink/Discontinuities/Saturation', [ruta '/lo que el piso aguanta'], ...
        'UpperLimit', 'tau_traccion', 'LowerLimit', '-tau_traccion', ...
        'Position', [900 195 1010 245]);

    crear_servo_pata([ruta '/Servo de pata IZQUIERDA']);
    set_param([ruta '/Servo de pata IZQUIERDA'], 'Position', [420 560 600 640]);
    crear_servo_pata([ruta '/Servo de pata DERECHA']);
    set_param([ruta '/Servo de pata DERECHA'], 'Position', [420 670 600 750]);

    add_block('simulink/Math Operations/Sum', [ruta '/promedio de las dos patas'], ...
        'Inputs', '++', 'IconShape', 'rectangular', 'Position', [760 580 810 710]);
    add_block('simulink/Math Operations/Gain', [ruta '/dividir por dos'], ...
        'Gain', '0.5', 'Position', [900 620 1010 670]);

    L = @(o, d) add_line(ruta, o, d, 'autorouting', 'on');
    L('tension a cada rueda/1', 'separar las dos tensiones/1');
    L('estado real/1', 'velocidad relativa rueda-cuerpo/1');
    L('separar las dos tensiones/1', 'Motor de rueda IZQUIERDA/1');
    L('separar las dos tensiones/2', 'Motor de rueda DERECHA/1');
    L('velocidad relativa rueda-cuerpo/1', 'Motor de rueda IZQUIERDA/2');
    L('velocidad relativa rueda-cuerpo/1', 'Motor de rueda DERECHA/2');
    L('Motor de rueda IZQUIERDA/1', 'par de las dos ruedas/1');
    L('Motor de rueda DERECHA/1', 'par de las dos ruedas/2');
    L('Motor de rueda IZQUIERDA/1', 'juntar los dos pares/1');
    L('Motor de rueda DERECHA/1', 'juntar los dos pares/2');
    L('juntar los dos pares/1', 'par de cada motor/1');
    L('par de las dos ruedas/1', 'lo que el piso aguanta/1');
    L('lo que el piso aguanta/1', 'par total en las ruedas/1');

    L('postura ref/1', 'Servo de pata IZQUIERDA/1');
    L('postura ref/1', 'Servo de pata DERECHA/1');
    L('Servo de pata IZQUIERDA/1', 'promedio de las dos patas/1');
    L('Servo de pata DERECHA/1', 'promedio de las dos patas/2');
    L('promedio de las dos patas/1', 'dividir por dos/1');
    L('dividir por dos/1', 'postura real/1');

    area(ruta, 'm1', 'LOS DOS MOTORES DE RUEDA   son los que equilibran el robot', [140 120 1060 360]);
    area(ruta, 'm2', 'LOS DOS SERVOS DE PATA   suben y bajan el cuerpo; no equilibran', [140 530 1060 780]);
    nota(ruta, [140 440 1060 520], sprintf([ ...
        'Los dos motores de rueda reciben hoy la MISMA tension, pero estan separados a proposito: el dia que se\n' ...
        'quiera doblar, cada uno va a recibir la suya y aca no hay que tocar nada.\n\n' ...
        'La velocidad relativa rueda-cuerpo, v/r - omega, es la que genera la fuerza contraelectromotriz: cuanto mas\n' ...
        'rapido gira la rueda respecto del cuerpo, menos par entrega el motor. Es la realimentacion interna del motor.']));
    nota(ruta, [140 800 1060 890], sprintf([ ...
        'Las dos patas reciben la misma consigna, asi que se mueven juntas y el robot no se inclina de costado.\n' ...
        'Si alguna vez reciben consignas distintas, este modelo NO lo representa: haria falta agregar el balanceo lateral.']));
end


% =========================================================================
function crear_motor_rueda(ruta)
%CREAR_MOTOR_RUEDA  Un motor de corriente continua con reductora.
%   tau = beta_V*U - b_m*w_rel, que es la ecuacion del motor con la inductancia
%   despreciada (su constante de tiempo es microsegundos; el robot se cae en 94 ms).
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'tension U', 'Position', [60 113 90 127]);
    add_block('simulink/Sources/In1', [ruta '/velocidad relativa'], 'Port', '2', ...
        'Position', [60 283 90 297]);
    set_param([ruta '/Out1'], 'Name', 'par tau', 'Position', [760 193 790 207]);

    add_block('simulink/Discontinuities/Saturation', [ruta '/lo que da la bateria'], ...
        'UpperLimit', 'V_bat', 'LowerLimit', '-V_bat', 'Position', [170 95 300 145]);
    add_block('simulink/Math Operations/Gain', [ruta '/constante de par'], ...
        'Gain', 'beta_V_motor', 'Position', [390 95 540 145]);
    add_block('simulink/Math Operations/Gain', [ruta '/freno de la contraelectromotriz'], ...
        'Gain', 'b_m_motor', 'Position', [390 265 540 315]);
    add_block('simulink/Math Operations/Sum', [ruta '/par entregado'], ...
        'Inputs', '+-', 'IconShape', 'rectangular', 'Position', [620 110 670 290]);

    add_line(ruta, 'tension U/1', 'lo que da la bateria/1', 'autorouting', 'on');
    add_line(ruta, 'lo que da la bateria/1', 'constante de par/1', 'autorouting', 'on');
    add_line(ruta, 'velocidad relativa/1', 'freno de la contraelectromotriz/1', 'autorouting', 'on');
    add_line(ruta, 'constante de par/1', 'par entregado/1', 'autorouting', 'on');
    add_line(ruta, 'freno de la contraelectromotriz/1', 'par entregado/2', 'autorouting', 'on');
    add_line(ruta, 'par entregado/1', 'par tau/1', 'autorouting', 'on');

    area(ruta, 'r1', 'GA25-370 12 V, reductora 1:20', [140 60 710 350]);
    nota(ruta, [140 380 710 500], sprintf([ ...
        'beta_V = eta * n_g * Kt / R_m   [N m por voltio]        cuanto par da por cada voltio\n' ...
        'b_m    = eta * n_g^2 * Kt * Ke / R_m   [N m s/rad]      cuanto par PIERDE por cada rad/s\n\n' ...
        'Sin el segundo termino el motor daria par infinito a cualquier velocidad. Es el que le pone\n' ...
        'un techo a la velocidad del robot: 1,01 m/s con la bateria a fondo.']));
end


% =========================================================================
function crear_servo_pata(ruta)
%CREAR_SERVO_PATA  Un servo de posicion: lazo P con tope de velocidad.
%   Es lo que hace un servo por dentro: compara la posicion pedida con la que
%   tiene, y mueve a una velocidad proporcional al error, hasta su velocidad
%   maxima. Los topes mecanicos son los limites del integrador.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'posicion pedida', 'Position', [60 193 90 207]);
    set_param([ruta '/Out1'], 'Name', 'posicion real', 'Position', [820 193 850 207]);

    add_block('simulink/Math Operations/Sum', [ruta '/error de posicion'], ...
        'Inputs', '+-', 'IconShape', 'rectangular', 'Position', [170 170 220 230]);
    add_block('simulink/Math Operations/Gain', [ruta '/ganancia del servo'], ...
        'Gain', 'Kp_servo', 'Position', [290 175 400 225]);
    add_block('simulink/Discontinuities/Saturation', [ruta '/velocidad maxima'], ...
        'UpperLimit', 'w_servo_max', 'LowerLimit', '-w_servo_max', ...
        'Position', [450 175 580 225]);
    add_block('simulink/Continuous/Integrator', [ruta '/angulo de la pata'], ...
        'InitialCondition', 'theta_pata_0', 'LimitOutput', 'on', ...
        'UpperSaturationLimit', 'theta_pata_max', 'LowerSaturationLimit', 'theta_pata_min', ...
        'Position', [640 175 700 225]);

    add_line(ruta, 'posicion pedida/1', 'error de posicion/1', 'autorouting', 'on');
    add_line(ruta, 'ganancia del servo/1', 'velocidad maxima/1', 'autorouting', 'on');
    add_line(ruta, 'error de posicion/1', 'ganancia del servo/1', 'autorouting', 'on');
    add_line(ruta, 'velocidad maxima/1', 'angulo de la pata/1', 'autorouting', 'on');
    add_line(ruta, 'angulo de la pata/1', 'posicion real/1', 'autorouting', 'on');
    add_line(ruta, 'angulo de la pata/1', 'error de posicion/2', 'autorouting', 'on');

    area(ruta, 's1', 'DS3240 40 kg cm: lazo de posicion', [140 140 760 260]);
    nota(ruta, [140 300 760 420], sprintf([ ...
        'Un servo de posicion ya trae su propio control adentro: por eso aca no hay que disenarle nada,\n' ...
        'solo decirle a que angulo ir. El lazo que se ve es el que el servo tiene de fabrica.\n\n' ...
        'Los topes del integrador son los topes MECANICOS de la pata: 10 grados plegada, 40 estirada.\n' ...
        'Que esten en el integrador y no en una saturacion aparte evita que el angulo se pase y despues vuelva.']));
end


% =========================================================================
%                                 P L A N T A
% =========================================================================
function crear_planta(ruta)
%CREAR_PLANTA  La fisica del robot, en el orden en que se piensa.
%   1. que postura tienen las patas -> cuanto pesa y cuanta inercia tiene el cuerpo
%   2. suma de fuerzas horizontales  y  suma de momentos
%   3. resolver las dos aceleraciones, que estan acopladas
%   4. integrar dos veces
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'par en las ruedas', 'Position', [60 193 90 207]);
    add_block('simulink/Sources/In1', [ruta '/postura de las patas'], 'Port', '2', ...
        'Position', [60 563 90 577]);
    set_param([ruta '/Out1'], 'Name', 'estado z', 'Position', [1640 393 1670 407]);

    crear_postura([ruta '/Cuanto pesa y cuanta inercia tiene']);
    set_param([ruta '/Cuanto pesa y cuanta inercia tiene'], 'Position', [180 520 420 620]);

    add_block('simulink/Signal Routing/Demux', [ruta '/separar los coeficientes'], ...
        'Outputs', '4', 'Position', [480 520 485 620]);

    % --- el par que realmente llega a la rueda, descontando el roce del eje
    add_block('simulink/Math Operations/Gain', [ruta '/velocidad relativa del eje'], ...
        'Gain', '[0  1/r  0  -1]', 'Multiplication', 'Matrix(K*u)', ...
        'Position', [160 60 340 110]);
    add_block('simulink/Math Operations/Gain', [ruta '/roce del eje'], ...
        'Gain', 'b_eje_mecanico', 'Position', [160 -20 340 30]);
    add_block('simulink/Math Operations/Sum', [ruta '/par que llega a la rueda'], ...
        'Inputs', '+-', 'IconShape', 'rectangular', 'Position', [420 -10 470 110]);

    crear_fuerzas([ruta '/Suma de FUERZAS horizontales']);
    set_param([ruta '/Suma de FUERZAS horizontales'], 'Position', [620 150 860 270]);

    crear_momentos([ruta '/Suma de MOMENTOS sobre el cuerpo']);
    set_param([ruta '/Suma de MOMENTOS sobre el cuerpo'], 'Position', [620 310 860 430]);

    crear_resolver([ruta '/Resolver las dos aceleraciones']);
    set_param([ruta '/Resolver las dos aceleraciones'], 'Position', [980 180 1220 400]);

    crear_estado([ruta '/Integrar hasta el estado']);
    set_param([ruta '/Integrar hasta el estado'], 'Position', [1340 290 1540 400]);

    % el estado vuelve a alimentar las dos sumas (velocidades y angulo)
    L = @(o, d) add_line(ruta, o, d, 'autorouting', 'on');
    L('postura de las patas/1', 'Cuanto pesa y cuanta inercia tiene/1');
    L('Cuanto pesa y cuanta inercia tiene/1', 'separar los coeficientes/1');

    L('Integrar hasta el estado/1', 'velocidad relativa del eje/1');
    L('velocidad relativa del eje/1', 'roce del eje/1');
    L('par en las ruedas/1', 'par que llega a la rueda/1');
    L('roce del eje/1', 'par que llega a la rueda/2');

    L('par que llega a la rueda/1', 'Suma de FUERZAS horizontales/1');
    L('Integrar hasta el estado/1', 'Suma de FUERZAS horizontales/2');
    L('separar los coeficientes/2', 'Suma de FUERZAS horizontales/3');   % h

    L('par que llega a la rueda/1', 'Suma de MOMENTOS sobre el cuerpo/1');
    L('Integrar hasta el estado/1', 'Suma de MOMENTOS sobre el cuerpo/2');
    L('separar los coeficientes/4', 'Suma de MOMENTOS sobre el cuerpo/3');  % k

    L('Suma de FUERZAS horizontales/1', 'Resolver las dos aceleraciones/1');
    L('Suma de MOMENTOS sobre el cuerpo/1', 'Resolver las dos aceleraciones/2');
    L('separar los coeficientes/1', 'Resolver las dos aceleraciones/3');  % a
    L('separar los coeficientes/2', 'Resolver las dos aceleraciones/4');  % h
    L('separar los coeficientes/3', 'Resolver las dos aceleraciones/5');  % j
    L('Integrar hasta el estado/1', 'Resolver las dos aceleraciones/6');

    L('Resolver las dos aceleraciones/1', 'Integrar hasta el estado/1');
    L('Integrar hasta el estado/1', 'estado z/1');

    area(ruta, 'p0', '1.  LA POSTURA DE LAS PATAS', [150 490 520 650]);
    area(ruta, 'pA', '0.  EL PAR QUE LLEGA A LA RUEDA', [140 -60 510 140]);
    area(ruta, 'p1', '2.  LAS DOS ECUACIONES', [590 120 890 460]);
    area(ruta, 'p2', '3.  RESOLVER LAS DOS JUNTAS', [950 150 1250 430]);
    area(ruta, 'p3', '4.  INTEGRAR', [1310 250 1580 440]);

    nota(ruta, [150 690 1570 860], sprintf([ ...
        'POR QUE NO SE PUEDE HACER UNA CADENA DE INTEGRADORES Y LISTO\n\n' ...
        'En un cuerpo suelto, suma de fuerzas sobre masa da la aceleracion y se integra. Aca no, porque el robot son DOS cuerpos\n' ...
        'pegados: cuando la rueda acelera hacia adelante, el cuerpo se inclina hacia atras, y cuando el cuerpo se inclina, empuja\n' ...
        'la rueda. Las dos aceleraciones aparecen en las DOS ecuaciones. Por eso primero se arma cada suma por separado (etapa 2)\n' ...
        'y despues se despejan las dos juntas (etapa 3). Ese despeje es una cuenta de dos por dos, nada mas.\n\n' ...
        'El estado es  z = [ x ; v ; phi ; omega ]:  posicion de avance, velocidad de avance, inclinacion y velocidad de inclinacion.']));
end


% =========================================================================
function crear_postura(ruta)
%CREAR_POSTURA  De la postura de las patas a los coeficientes del cuerpo.
%   Al plegarse la pata el cuerpo baja, asi que cambian su brazo y su inercia.
%   Las tablas se calculan en INICIAR_SEGWAY a partir de la fuente unica de
%   parametros, resolviendo el cuerpo equivalente en cada postura.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'postura', 'Position', [60 293 90 307]);
    set_param([ruta '/Out1'], 'Name', 'coeficientes', 'Position', [760 293 790 307]);

    tablas = { ...
        'masa efectiva de avance  a  en kg',         'tabla_a',       95;
        'masa por brazo  h  en kg m',                'tabla_h',       195;
        'inercia del cuerpo  j  en kg m2',           'tabla_j',       295;
        'par de gravedad  k  en N m por rad',            'tabla_k',       395};
    for i = 1:size(tablas, 1)
        nb = [ruta '/' tablas{i,1}];
        add_block('simulink/Lookup Tables/1-D Lookup Table', nb, ...
            'BreakpointsForDimension1', 'tabla_theta', ...
            'Table', tablas{i,2}, ...
            'Position', [220 tablas{i,3} 500 tablas{i,3}+60]);
        add_line(ruta, 'postura/1', [tablas{i,1} '/1'], 'autorouting', 'on');
    end

    add_block('simulink/Signal Routing/Mux', [ruta '/juntar'], 'Inputs', '4', ...
        'DisplayOption', 'bar', 'Position', [620 95 625 455]);
    for i = 1:size(tablas, 1)
        add_line(ruta, [tablas{i,1} '/1'], sprintf('juntar/%d', i), 'autorouting', 'on');
    end
    add_line(ruta, 'juntar/1', 'coeficientes/1', 'autorouting', 'on');

    area(ruta, 'q1', 'CADA COEFICIENTE EN FUNCION DE LA POSTURA', [190 60 660 490]);
    nota(ruta, [190 520 900 680], sprintf([ ...
        'a  masa efectiva de avance: la masa del robot MAS la inercia de las ruedas y de los rotores vista desde el avance.\n' ...
        '   Por eso vale 1,39 kg y no 0,92: la reductora 1:20 hace que el rotor pese, visto desde la rueda, casi medio kilo.\n\n' ...
        'h  masa por brazo (m_cuerpo * distancia al centro de masa): es el acople. Si valiera cero, inclinarse y avanzar\n' ...
        '   serian dos cosas independientes y el robot no se podria equilibrar con las ruedas.\n\n' ...
        'j  inercia del cuerpo alrededor del eje de la rueda.      k  par que hace la gravedad por radian de inclinacion.\n\n' ...
        'Con la postura constante las tablas devuelven siempre el mismo numero y la planta es la verificada.']));
end


% =========================================================================
function crear_fuerzas(ruta)
%CREAR_FUERZAS  Suma de fuerzas horizontales sobre el robot entero.
%   El par del motor empuja la rueda contra el piso; el piso devuelve una fuerza
%   hacia adelante. Ademas, un cuerpo que gira inclinado tira hacia afuera.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'par tau', 'Position', [60 113 90 127]);
    add_block('simulink/Sources/In1', [ruta '/estado z'], 'Port', '2', ...
        'Position', [60 283 90 297]);
    add_block('simulink/Sources/In1', [ruta '/coeficiente h'], 'Port', '3', ...
        'Position', [60 503 90 517]);
    set_param([ruta '/Out1'], 'Name', 'suma de fuerzas', 'Position', [1120 293 1150 307]);

    add_block('simulink/Math Operations/Gain', [ruta '/el motor empuja (par sobre radio)'], ...
        'Gain', '1/r', 'Position', [220 95 420 145]);

    add_block('simulink/Math Operations/Gain', [ruta '/rozamiento de avance'], ...
        'Gain', '[0  -b_x  0  0]', 'Multiplication', 'Matrix(K*u)', ...
        'Position', [220 195 420 245]);

    % termino centrifugo: -h sin(phi) omega^2
    add_block('simulink/Math Operations/Gain', [ruta '/sacar phi'], ...
        'Gain', '[0 0 1 0]', 'Multiplication', 'Matrix(K*u)', 'Position', [160 320 290 360]);
    add_block('simulink/Math Operations/Gain', [ruta '/sacar omega'], ...
        'Gain', '[0 0 0 1]', 'Multiplication', 'Matrix(K*u)', 'Position', [160 390 290 430]);
    add_block('simulink/Math Operations/Trigonometric Function', [ruta '/seno'], ...
        'Operator', 'sin', 'Position', [350 320 430 360]);
    add_block('simulink/Math Operations/Math Function', [ruta '/al cuadrado'], ...
        'Operator', 'square', 'Position', [350 390 430 430]);
    add_block('simulink/Math Operations/Product', [ruta '/fuerza centrifuga'], ...
        'Inputs', '3', 'Position', [540 330 600 470]);
    add_block('simulink/Math Operations/Gain', [ruta '/la centrifuga tira hacia afuera'], ...
        'Gain', '1', 'Position', [660 375 760 425]);

    add_block('simulink/Math Operations/Sum', [ruta '/sumar las tres'], ...
        'Inputs', '+++', 'IconShape', 'rectangular', 'Position', [900 110 960 490]);

    L = @(o, d) add_line(ruta, o, d, 'autorouting', 'on');
    L('par tau/1', 'el motor empuja (par sobre radio)/1');
    L('estado z/1', 'rozamiento de avance/1');
    L('estado z/1', 'sacar phi/1');
    L('estado z/1', 'sacar omega/1');
    L('sacar phi/1', 'seno/1');
    L('sacar omega/1', 'al cuadrado/1');
    L('coeficiente h/1', 'fuerza centrifuga/1');
    L('seno/1', 'fuerza centrifuga/2');
    L('al cuadrado/1', 'fuerza centrifuga/3');
    L('fuerza centrifuga/1', 'la centrifuga tira hacia afuera/1');
    L('el motor empuja (par sobre radio)/1', 'sumar las tres/1');
    L('rozamiento de avance/1', 'sumar las tres/2');
    L('la centrifuga tira hacia afuera/1', 'sumar las tres/3');
    L('sumar las tres/1', 'suma de fuerzas/1');

    area(ruta, 'f1', 'SUMA DE FUERZAS HORIZONTALES  [N]', [140 60 1000 520]);
    nota(ruta, [140 560 1100 700], sprintf([ ...
        'Son tres terminos:\n\n' ...
        '  +tau/r             el par del motor, visto como fuerza en el contacto con el piso\n' ...
        '  -b_x * v           rozamiento de rodadura (hoy vale cero: no esta medido)\n' ...
        '  +h sin(phi) omega2 la fuerza centrifuga del cuerpo girando inclinado. Es el UNICO termino no lineal\n' ...
        '                     del modelo, y solo importa cuando el robot se inclina mucho y rapido.']));
end


% =========================================================================
function crear_momentos(ruta)
%CREAR_MOMENTOS  Suma de momentos sobre el cuerpo, alrededor del eje de la rueda.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'par tau', 'Position', [60 113 90 127]);
    add_block('simulink/Sources/In1', [ruta '/estado z'], 'Port', '2', ...
        'Position', [60 283 90 297]);
    add_block('simulink/Sources/In1', [ruta '/coeficiente k'], 'Port', '3', ...
        'Position', [60 443 90 457]);
    set_param([ruta '/Out1'], 'Name', 'suma de momentos', 'Position', [1000 273 1030 307]);

    add_block('simulink/Math Operations/Gain', [ruta '/reaccion del motor  -tau'], ...
        'Gain', '-1', 'Position', [220 95 420 145]);
    add_block('simulink/Math Operations/Gain', [ruta '/rozamiento del pivote'], ...
        'Gain', '[0  0  0  -b_phi]', 'Multiplication', 'Matrix(K*u)', ...
        'Position', [220 195 420 245]);

    add_block('simulink/Math Operations/Gain', [ruta '/sacar phi'], ...
        'Gain', '[0 0 1 0]', 'Multiplication', 'Matrix(K*u)', 'Position', [160 320 290 360]);
    add_block('simulink/Math Operations/Trigonometric Function', [ruta '/seno'], ...
        'Operator', 'sin', 'Position', [360 320 440 360]);
    add_block('simulink/Math Operations/Product', [ruta '/la gravedad lo voltea'], ...
        'Inputs', '2', 'Position', [540 330 600 440]);

    add_block('simulink/Math Operations/Sum', [ruta '/sumar los tres'], ...
        'Inputs', '+++', 'IconShape', 'rectangular', 'Position', [800 110 860 460]);

    L = @(o, d) add_line(ruta, o, d, 'autorouting', 'on');
    L('par tau/1', 'reaccion del motor  -tau/1');
    L('estado z/1', 'rozamiento del pivote/1');
    L('estado z/1', 'sacar phi/1');
    L('sacar phi/1', 'seno/1');
    L('seno/1', 'la gravedad lo voltea/1');
    L('coeficiente k/1', 'la gravedad lo voltea/2');
    L('reaccion del motor  -tau/1', 'sumar los tres/1');
    L('rozamiento del pivote/1', 'sumar los tres/2');
    L('la gravedad lo voltea/1', 'sumar los tres/3');
    L('sumar los tres/1', 'suma de momentos/1');

    area(ruta, 'n1', 'SUMA DE MOMENTOS SOBRE EL CUERPO  [N m]', [140 60 900 490]);
    nota(ruta, [140 530 1100 680], sprintf([ ...
        'Son tres terminos:\n\n' ...
        '  -tau          la REACCION del motor. Si la rueda recibe +tau, el cuerpo recibe -tau. Es la unica\n' ...
        '                manija que tiene el control para inclinar el robot a proposito.\n' ...
        '  -b_phi*omega  rozamiento del pivote (chiquito)\n' ...
        '  +k*sin(phi)   la gravedad. El signo es POSITIVO: cuanto mas inclinado esta, mas lo voltea.\n' ...
        '                Ese signo es la razon de que el robot sea inestable y haya que controlarlo.']));
end


% =========================================================================
function crear_resolver(ruta)
%CREAR_RESOLVER  Despeja las dos aceleraciones del sistema de dos por dos.
%
%      [ a       acople ] [ aceleracion de avance     ]   [ suma de fuerzas  ]
%      [ acople  j      ] [ aceleracion de inclinacion] = [ suma de momentos ]
%
%   con acople = -h cos(phi) + acople_rotor. Se resuelve por Cramer, que para
%   dos por dos son cuatro multiplicaciones y una division.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'suma de fuerzas', 'Position', [60 113 90 127]);
    add_block('simulink/Sources/In1', [ruta '/suma de momentos'], 'Port', '2', ...
        'Position', [60 183 90 197]);
    add_block('simulink/Sources/In1', [ruta '/masa efectiva a'], 'Port', '3', ...
        'Position', [60 283 90 297]);
    add_block('simulink/Sources/In1', [ruta '/masa por brazo h'], 'Port', '4', ...
        'Position', [60 353 90 367]);
    add_block('simulink/Sources/In1', [ruta '/inercia j'], 'Port', '5', ...
        'Position', [60 423 90 437]);
    add_block('simulink/Sources/In1', [ruta '/estado z'], 'Port', '6', ...
        'Position', [60 493 90 507]);
    set_param([ruta '/Out1'], 'Name', 'las dos aceleraciones', 'Position', [1500 273 1530 307]);

    % ---- el acople: -h cos(phi) + acople del rotor
    add_block('simulink/Math Operations/Gain', [ruta '/sacar phi'], ...
        'Gain', '[0 0 1 0]', 'Multiplication', 'Matrix(K*u)', 'Position', [160 480 290 520]);
    add_block('simulink/Math Operations/Trigonometric Function', [ruta '/coseno'], ...
        'Operator', 'cos', 'Position', [340 480 410 520]);
    add_block('simulink/Math Operations/Product', [ruta '/h por coseno'], ...
        'Inputs', '2', 'Position', [470 350 510 520]);
    add_block('simulink/Sources/Constant', [ruta '/acople del rotor'], ...
        'Value', 'acople_rotor', 'Position', [470 570 650 610]);
    add_block('simulink/Math Operations/Sum', [ruta '/acople'], ...
        'Inputs', '++', 'IconShape', 'rectangular', 'Position', [720 400 770 580]);

    % ---- determinante
    add_block('simulink/Math Operations/Product', [ruta '/a por j'], ...
        'Inputs', '2', 'Position', [880 270 930 350]);
    add_block('simulink/Math Operations/Math Function', [ruta '/acople al cuadrado'], ...
        'Operator', 'square', 'Position', [880 420 930 470]);
    add_block('simulink/Math Operations/Sum', [ruta '/determinante'], ...
        'Inputs', '+-', 'IconShape', 'rectangular', 'Position', [1000 280 1050 460]);

    % ---- numeradores
    add_block('simulink/Math Operations/Product', [ruta '/j por fuerzas'], ...
        'Inputs', '2', 'Position', [880 90 930 150]);
    add_block('simulink/Math Operations/Product', [ruta '/acople por momentos'], ...
        'Inputs', '2', 'Position', [880 170 930 230]);
    add_block('simulink/Math Operations/Sum', [ruta '/arriba de avance'], ...
        'Inputs', '+-', 'IconShape', 'rectangular', 'Position', [1000 100 1050 220]);

    add_block('simulink/Math Operations/Product', [ruta '/a por momentos'], ...
        'Inputs', '2', 'Position', [880 620 930 680]);
    add_block('simulink/Math Operations/Product', [ruta '/acople por fuerzas'], ...
        'Inputs', '2', 'Position', [880 700 930 760]);
    add_block('simulink/Math Operations/Sum', [ruta '/arriba de inclinacion'], ...
        'Inputs', '+-', 'IconShape', 'rectangular', 'Position', [1000 630 1050 750]);

    % ---- dividir
    add_block('simulink/Math Operations/Divide', [ruta '/aceleracion de avance'], ...
        'Inputs', '*/', 'Position', [1160 110 1220 190]);
    add_block('simulink/Math Operations/Divide', [ruta '/aceleracion de inclinacion'], ...
        'Inputs', '*/', 'Position', [1160 640 1220 720]);
    add_block('simulink/Signal Routing/Mux', [ruta '/las dos juntas'], 'Inputs', '2', ...
        'DisplayOption', 'bar', 'Position', [1360 110 1365 720]);

    L = @(o, d) add_line(ruta, o, d, 'autorouting', 'on');
    L('estado z/1', 'sacar phi/1');
    L('sacar phi/1', 'coseno/1');
    L('masa por brazo h/1', 'h por coseno/1');
    L('coseno/1', 'h por coseno/2');
    L('h por coseno/1', 'acople/1');
    L('acople del rotor/1', 'acople/2');

    L('masa efectiva a/1', 'a por j/1');
    L('inercia j/1', 'a por j/2');
    L('acople/1', 'acople al cuadrado/1');
    L('a por j/1', 'determinante/1');
    L('acople al cuadrado/1', 'determinante/2');

    L('inercia j/1', 'j por fuerzas/1');
    L('suma de fuerzas/1', 'j por fuerzas/2');
    L('acople/1', 'acople por momentos/1');
    L('suma de momentos/1', 'acople por momentos/2');
    L('j por fuerzas/1', 'arriba de avance/1');
    L('acople por momentos/1', 'arriba de avance/2');

    L('masa efectiva a/1', 'a por momentos/1');
    L('suma de momentos/1', 'a por momentos/2');
    L('acople/1', 'acople por fuerzas/1');
    L('suma de fuerzas/1', 'acople por fuerzas/2');
    L('a por momentos/1', 'arriba de inclinacion/1');
    L('acople por fuerzas/1', 'arriba de inclinacion/2');

    L('arriba de avance/1', 'aceleracion de avance/1');
    L('determinante/1', 'aceleracion de avance/2');
    L('arriba de inclinacion/1', 'aceleracion de inclinacion/1');
    L('determinante/1', 'aceleracion de inclinacion/2');
    L('aceleracion de avance/1', 'las dos juntas/1');
    L('aceleracion de inclinacion/1', 'las dos juntas/2');
    L('las dos juntas/1', 'las dos aceleraciones/1');

    area(ruta, 'v0', 'EL ACOPLE   h cos(phi) + acople del rotor', [450 330 800 630]);
    area(ruta, 'v1', 'ACELERACION DE AVANCE', [860 70 1250 240]);
    area(ruta, 'v2', 'DIVISOR COMUN (determinante)', [860 250 1080 480]);
    area(ruta, 'v3', 'ACELERACION DE INCLINACION', [860 600 1250 770]);

    nota(ruta, [140 800 1560 980], sprintf([ ...
        'QUE ES ESTO, EN CRISTIANO\n\n' ...
        'Hay que despejar dos incognitas de dos ecuaciones. Con dos por dos se hace por Cramer, que es la regla\n' ...
        'de siempre: cada incognita es un determinante dividido por el determinante comun.\n\n' ...
        '  aceleracion de avance      = ( j * fuerzas  -  acople * momentos ) / ( a*j - acople^2 )\n' ...
        '  aceleracion de inclinacion = ( a * momentos -  acople * fuerzas  ) / ( a*j - acople^2 )\n\n' ...
        'EL ACOPLE es el numero que dice cuanto se afectan entre si avanzar e inclinarse. Vale h cos(phi) mas una\n' ...
        'constante del rotor. Si fuera cero las dos ecuaciones se separarian y el robot no se podria equilibrar\n' ...
        'moviendo las ruedas, porque empujar la rueda no inclinaria el cuerpo.']));
end


% =========================================================================
function crear_estado(ruta)
%CREAR_ESTADO  Dos cadenas de integradores: aceleracion -> velocidad -> posicion.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'las dos aceleraciones', 'Position', [60 293 90 307]);
    set_param([ruta '/Out1'], 'Name', 'estado z', 'Position', [900 293 930 307]);

    add_block('simulink/Signal Routing/Demux', [ruta '/separar'], ...
        'Outputs', '2', 'Position', [160 170 165 430]);

    add_block('simulink/Continuous/Integrator', [ruta '/velocidad de avance  v'], ...
        'InitialCondition', 'v0', 'Position', [280 140 350 200]);
    add_block('simulink/Continuous/Integrator', [ruta '/posicion de avance  x'], ...
        'InitialCondition', 'x0', 'Position', [470 140 540 200]);
    add_block('simulink/Continuous/Integrator', [ruta '/velocidad de inclinacion  omega'], ...
        'InitialCondition', 'omega0', 'Position', [280 400 350 460]);
    add_block('simulink/Continuous/Integrator', [ruta '/inclinacion  phi'], ...
        'InitialCondition', 'phi0', 'Position', [470 400 540 460]);

    add_block('simulink/Signal Routing/Mux', [ruta '/armar z'], 'Inputs', '4', ...
        'DisplayOption', 'bar', 'Position', [700 140 705 460]);

    L = @(o, d) add_line(ruta, o, d, 'autorouting', 'on');
    L('las dos aceleraciones/1', 'separar/1');
    L('separar/1', 'velocidad de avance  v/1');
    L('velocidad de avance  v/1', 'posicion de avance  x/1');
    L('separar/2', 'velocidad de inclinacion  omega/1');
    L('velocidad de inclinacion  omega/1', 'inclinacion  phi/1');
    L('posicion de avance  x/1', 'armar z/1');
    L('velocidad de avance  v/1', 'armar z/2');
    L('inclinacion  phi/1', 'armar z/3');
    L('velocidad de inclinacion  omega/1', 'armar z/4');
    L('armar z/1', 'estado z/1');

    area(ruta, 'i1', 'AVANCE', [240 100 580 230]);
    area(ruta, 'i2', 'INCLINACION', [240 360 580 490]);
    nota(ruta, [240 560 900 650], sprintf([ ...
        'Las condiciones iniciales de los cuatro integradores son el estado de arranque del robot:\n' ...
        'x0, v0, phi0 y omega0, que se editan en la seccion 2 de INICIAR_SEGWAY.\n' ...
        'El estado sale ordenado como z = [x ; v ; phi ; omega].']));
end


% =========================================================================
%                               S E N S O R E S
% =========================================================================
function crear_sensores(ruta)
%CREAR_SENSORES  Lo que el robot puede medir. Hoy ideales y sin ruido.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'estado real', 'Position', [60 193 90 207]);
    add_block('simulink/Sources/In1', [ruta '/postura de las patas'], 'Port', '2', ...
        'Position', [60 503 90 517]);
    set_param([ruta '/Out1'], 'Name', 'estado medido', 'Position', [1240 293 1270 307]);

    crear_encoders([ruta '/Encoders de las ruedas']);
    set_param([ruta '/Encoders de las ruedas'], 'Position', [320 140 560 220]);

    crear_imu([ruta '/IMU MPU-6050']);
    set_param([ruta '/IMU MPU-6050'], 'Position', [320 400 560 520]);

    add_block('simulink/Signal Routing/Mux', [ruta '/armar el estado medido'], 'Inputs', '2', ...
        'DisplayOption', 'bar', 'Position', [1080 160 1085 460]);

    L = @(o, d) add_line(ruta, o, d, 'autorouting', 'on');
    L('estado real/1', 'Encoders de las ruedas/1');
    L('estado real/1', 'IMU MPU-6050/1');
    L('postura de las patas/1', 'IMU MPU-6050/2');
    L('Encoders de las ruedas/1', 'armar el estado medido/1');
    L('IMU MPU-6050/1', 'armar el estado medido/2');
    L('armar el estado medido/1', 'estado medido/1');

    area(ruta, 'e1', 'ENCODERS:  x y v', [280 100 620 250]);
    area(ruta, 'e2', 'IMU:  phi y omega', [280 360 620 550]);
    nota(ruta, [280 620 1300 790], sprintf([ ...
        'HOY LOS SENSORES SON IDEALES: miden exactamente lo que pasa y el ruido esta en cero. Por eso la senal que\n' ...
        'entra al control es identica a la real, y el resultado coincide con el modelo matematico.\n\n' ...
        'Los lugares donde meter la realidad ya estan puestos:\n' ...
        '  - ruido: las variables ruido_* valen cero; poniendoles un numero aparece el ruido de medicion\n' ...
        '  - sesgo de la IMU: sesgo_imu, en radianes\n' ...
        '  - compensacion de la postura: compensar_delta_G vale 1; poniendolo en 0 se ve el error de no corregirla\n\n' ...
        'Lo que TODAVIA no esta y hay que agregar antes de pasar a firmware: periodo de muestreo, retardo de calculo\n' ...
        'y cuantizacion del encoder. Con esos tres el LQR hubo que repesarlo (capitulo 7 del PDF).']));
end


% =========================================================================
function crear_encoders(ruta)
%CREAR_ENCODERS  Posicion y velocidad de avance, a partir del giro de las ruedas.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'estado real', 'Position', [60 293 90 307]);
    set_param([ruta '/Out1'], 'Name', 'x y v medidos', 'Position', [860 293 890 307]);

    add_block('simulink/Math Operations/Gain', [ruta '/sacar x y v de verdad'], ...
        'Gain', '[1 0 0 0; 0 1 0 0]', 'Multiplication', 'Matrix(K*u)', ...
        'Position', [180 270 390 330]);
    add_block('simulink/Sources/Band-Limited White Noise', [ruta '/ruido del encoder'], ...
        'Cov', '[ruido_encoder_x  ruido_encoder_v]', 'Ts', 'Ts_sensores', ...
        'seed', '[41 43]', 'Position', [180 420 390 490]);
    add_block('simulink/Math Operations/Sum', [ruta '/medicion'], ...
        'Inputs', '++', 'IconShape', 'rectangular', 'Position', [600 280 650 450]);

    add_line(ruta, 'estado real/1', 'sacar x y v de verdad/1', 'autorouting', 'on');
    add_line(ruta, 'sacar x y v de verdad/1', 'medicion/1', 'autorouting', 'on');
    add_line(ruta, 'ruido del encoder/1', 'medicion/2', 'autorouting', 'on');
    add_line(ruta, 'medicion/1', 'x y v medidos/1', 'autorouting', 'on');

    area(ruta, 'g1', 'ENCODER DE CUADRATURA', [150 240 700 360]);
    area(ruta, 'g2', 'RUIDO   hoy en cero', [150 390 700 520]);
    nota(ruta, [150 560 900 680], sprintf([ ...
        'El encoder cuenta pulsos del eje del motor. Con la reductora 1:20 y la rueda de 33 mm, cada cuenta\n' ...
        'son 0,24 mm de avance: de sobra para la posicion.\n\n' ...
        'El problema es la VELOCIDAD: a 0,1 m/s entran solo 2 cuentas por cada muestra de 5 ms. Por eso el\n' ...
        'diseno del LQR ya tiene en cuenta un filtro de 20 Hz sobre la velocidad.']));
end


% =========================================================================
function crear_imu(ruta)
%CREAR_IMU  La IMU mide el angulo del CHASIS, no phi.
%   phi se mide desde la direccion del centro de masa. Entre el chasis y esa
%   direccion hay un angulo delta_G que CAMBIA con la postura de las patas:
%   9,09 grados plegada y 1,78 estirada. El firmware tiene que sumarlo.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'estado real', 'Position', [60 193 90 207]);
    add_block('simulink/Sources/In1', [ruta '/postura de las patas'], 'Port', '2', ...
        'Position', [60 543 90 557]);
    set_param([ruta '/Out1'], 'Name', 'phi y omega medidos', 'Position', [1300 293 1330 307]);

    add_block('simulink/Math Operations/Gain', [ruta '/sacar phi y omega de verdad'], ...
        'Gain', '[0 0 1 0; 0 0 0 1]', 'Multiplication', 'Matrix(K*u)', ...
        'Position', [180 170 400 230]);

    % delta_G segun la postura
    add_block('simulink/Lookup Tables/1-D Lookup Table', [ruta '/delta_G segun la postura'], ...
        'BreakpointsForDimension1', 'tabla_theta', 'Table', 'tabla_delta_G', ...
        'Position', [180 520 400 580]);
    add_block('simulink/Math Operations/Gain', [ruta '/solo al angulo'], ...
        'Gain', '[1; 0]', 'Multiplication', 'Matrix(K*u)', 'Position', [460 525 590 575]);

    % el chasis = phi - delta_G
    add_block('simulink/Math Operations/Sum', [ruta '/lo que ve el chasis'], ...
        'Inputs', '+-', 'IconShape', 'rectangular', 'Position', [660 180 710 570]);

    add_block('simulink/Sources/Band-Limited White Noise', [ruta '/ruido de la IMU'], ...
        'Cov', '[ruido_imu_angulo  ruido_imu_giro]', 'Ts', 'Ts_sensores', ...
        'seed', '[23 29]', 'Position', [180 300 400 370]);
    add_block('simulink/Sources/Constant', [ruta '/sesgo de la IMU'], ...
        'Value', '[sesgo_imu; 0]', 'Position', [180 400 400 460]);
    add_block('simulink/Math Operations/Sum', [ruta '/lo que la IMU informa'], ...
        'Inputs', '+++', 'IconShape', 'rectangular', 'Position', [800 190 850 450]);

    % el firmware reconstruye phi
    add_block('simulink/Math Operations/Gain', [ruta '/compensar la postura'], ...
        'Gain', 'compensar_delta_G', 'Position', [800 525 920 575]);
    add_block('simulink/Math Operations/Sum', [ruta '/phi reconstruido'], ...
        'Inputs', '++', 'IconShape', 'rectangular', 'Position', [1080 215 1130 470]);

    L = @(o, d) add_line(ruta, o, d, 'autorouting', 'on');
    L('estado real/1', 'sacar phi y omega de verdad/1');
    L('postura de las patas/1', 'delta_G segun la postura/1');
    L('delta_G segun la postura/1', 'solo al angulo/1');
    L('sacar phi y omega de verdad/1', 'lo que ve el chasis/1');
    L('solo al angulo/1', 'lo que ve el chasis/2');
    L('lo que ve el chasis/1', 'lo que la IMU informa/1');
    L('ruido de la IMU/1', 'lo que la IMU informa/2');
    L('sesgo de la IMU/1', 'lo que la IMU informa/3');
    L('solo al angulo/1', 'compensar la postura/1');
    L('lo que la IMU informa/1', 'phi reconstruido/1');
    L('compensar la postura/1', 'phi reconstruido/2');
    L('phi reconstruido/1', 'phi y omega medidos/1');

    area(ruta, 'u1', 'LO QUE REALMENTE PASA', [150 140 430 250]);
    area(ruta, 'u2', 'LO QUE AGREGA EL SENSOR', [150 280 430 480]);
    area(ruta, 'u3', 'EL ANGULO QUE VE EL CHASIS', [150 500 620 600]);
    area(ruta, 'u4', 'LO QUE HACE EL FIRMWARE', [770 500 1180 600]);

    nota(ruta, [150 660 1400 850], sprintf([ ...
        'ESTA ES LA PARTE MAS FACIL DE EQUIVOCAR DE TODO EL MODELO.\n\n' ...
        'phi NO es el angulo del chasis. phi se mide desde la direccion del centro de masa, y entre el chasis y esa\n' ...
        'direccion hay un angulo delta_G. El problema es que delta_G CAMBIA con la postura de las patas: vale 9,09\n' ...
        'grados con la pata plegada y 1,78 con la pata estirada. O sea que al mover las patas, el cero del angulo\n' ...
        'se corre mas de 7 grados.\n\n' ...
        'Si el firmware no lo compensa, el control cree que el robot esta inclinado cuando no lo esta y sale a\n' ...
        'corregir: el robot se va 21 cm de donde estaba. Compensando, se queda en cero.\n\n' ...
        'Para verlo: poner compensar_delta_G = 0 y mover las patas con un escalon en la consigna de postura.']));
end


% =========================================================================
%                              H E R R A M I E N T A S
% =========================================================================
function area(ruta, etiqueta, texto, posicion)
%AREA  Recuadro con titulo. Es decorativo: si la version de Simulink no lo
%   tuviera, el modelo funciona igual.
    try
        nombre = [ruta '/' etiqueta];
        add_block('built-in/Area', nombre, 'Position', posicion);
        set_param(nombre, 'Name', texto);
    catch ME
        warning('construir_segway_completo:area', 'area "%s": %s', etiqueta, ME.message);
    end
end

function nota(ruta, posicion, texto)
%NOTA  Texto explicativo pegado al diagrama. Cada uno lleva un nombre distinto
%   porque puede haber varios en el mismo nivel.
    persistent n_nota
    if isempty(n_nota), n_nota = 0; end
    n_nota = n_nota + 1;
    try
        h = Simulink.Annotation(sprintf('%s/nota %d', ruta, n_nota));
        h.Text = texto;
        h.Position = posicion;
        h.HorizontalAlignment = 'left';
        h.VerticalAlignment = 'top';
        h.FontSize = 11;
    catch ME
        warning('construir_segway_completo:nota', 'nota: %s', ME.message);
    end
end

function registrar(modelo, origen, nombre, variable, posicion)
    bloque = [modelo '/' nombre];
    add_block('simulink/Sinks/To Workspace', bloque, 'VariableName', variable, ...
        'SaveFormat', 'Structure With Time', 'Position', posicion);
    add_line(modelo, origen, [nombre '/1'], 'autorouting', 'on');
end
