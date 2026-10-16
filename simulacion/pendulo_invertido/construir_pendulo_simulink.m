function archivo = construir_pendulo_simulink(carpeta_destino, nombre_modelo)
%CONSTRUIR_PENDULO_SIMULINK Arma el modelo Simulink del pendulo invertido con LQR.
%   archivo = construir_pendulo_simulink() lo deja en esta carpeta.
%
%   SOLO BLOQUES NATIVOS: ni un MATLAB Function, ni Fcn, ni S-Function. Cada
%   termino se lee en el diagrama. El test test_pendulo_simulink lo verifica.
%
%   La ecuacion va en forma MATRICIAL, no desarmada en escalares:
%
%       M(phi) q'' = H tau - D q' + sin(phi) [-h omega^2 ; k]
%
%   con q = [x; phi],  M(phi) = [a, M12 ; M12, j],  M12 = -h cos(phi) + e,
%   H = [-1/r; -1] y D la matriz de perdidas. Un solo bloque Divide en modo
%   matricial resuelve M\rhs, y dos integradores VECTORIALES llevan q'' a q.
%   Asi la planta se lee de corrido en vez de quedar desarmada en escalares.
%
%   NOMBRES: la tension se llama U y la velocidad de avance v, para que no se
%   confundan (antes las dos se llamaban V).
%
%   Nivel superior, cinco areas en fila:
%     Consigna   z_ref = [x_destino; 0; 0; 0]   adonde se le pide ir
%     Control    U = -K (z - z_ref)             realimentacion de estado
%     Actuador   bateria -> motor -> agarre     los dos limites reales
%     Planta     M q'' = ...                    mecanica de dos grados de libertad
%     Registro   To Workspace
%
%   Variables que lee del workspace: K, V_bat, beta_V, b_m, tau_traccion,
%   a, h, j, k, e_acople, r, b_eje, b_x, b_phi, q0, q_punto0, x_destino,
%   t_consigna, duracion. Las prepara INICIAR_PENDULO_SIMULINK.

    if nargin < 1 || isempty(carpeta_destino)
        carpeta_destino = fileparts(mfilename('fullpath'));
    end
    if nargin < 2 || isempty(nombre_modelo)
        nombre_modelo = 'pendulo_invertido_lqr';
    end

    if bdIsLoaded(nombre_modelo), close_system(nombre_modelo, 0); end
    modelo = nombre_modelo;
    new_system(modelo);
    set_param(modelo, 'Solver', 'ode45', 'SolverType', 'Variable-step', ...
        'RelTol', '1e-8', 'AbsTol', '1e-10', 'MaxStep', '1e-3', 'StopTime', 'duracion');

    %% ======================= 1. CONSIGNA =======================
    add_block('simulink/Sources/Step', [modelo '/consigna x'], ...
        'Time', 't_consigna', 'Before', '0', 'After', 'x_destino', ...
        'Position', [80 100 130 150]);
    add_block('simulink/Sources/Constant', [modelo '/resto en cero'], ...
        'Value', '[0; 0; 0]', 'Position', [80 190 130 225]);
    add_block('simulink/Signal Routing/Mux', [modelo '/z ref'], 'Inputs', '2', ...
        'Position', [200 105 205 220]);
    add_line(modelo, 'consigna x/1', 'z ref/1', 'autorouting', 'on');
    add_line(modelo, 'resto en cero/1', 'z ref/2', 'autorouting', 'on');

    %% ======================= 2. CONTROL ========================
    add_block('simulink/Math Operations/Sum', [modelo '/error'], ...
        'IconShape', 'rectangular', 'Inputs', '+-', 'Position', [350 125 400 200]);
    crear_lqr([modelo '/LQR']);
    set_param([modelo '/LQR'], 'Position', [460 130 570 195]);
    add_line(modelo, 'z ref/1', 'error/2', 'autorouting', 'on');
    add_line(modelo, 'error/1', 'LQR/1', 'autorouting', 'on');

    %% ======================= 3. ACTUADOR =======================
    add_block('simulink/Discontinuities/Saturation', [modelo '/bateria'], ...
        'UpperLimit', 'V_bat', 'LowerLimit', '-V_bat', 'Position', [680 140 730 185]);
    crear_motor([modelo '/motor']);
    set_param([modelo '/motor'], 'Position', [800 125 910 200]);
    add_block('simulink/Discontinuities/Saturation', [modelo '/agarre'], ...
        'UpperLimit', 'tau_traccion', 'LowerLimit', '-tau_traccion', ...
        'Position', [980 140 1030 185]);
    add_line(modelo, 'LQR/1', 'bateria/1', 'autorouting', 'on');
    add_line(modelo, 'bateria/1', 'motor/1', 'autorouting', 'on');
    add_line(modelo, 'motor/1', 'agarre/1', 'autorouting', 'on');

    %% ======================= 4. PLANTA =========================
    crear_planta([modelo '/planta']);
    set_param([modelo '/planta'], 'Position', [1090 125 1230 200]);
    add_line(modelo, 'agarre/1', 'planta/1', 'autorouting', 'on');
    add_line(modelo, 'planta/1', 'error/1', 'autorouting', 'on');     % z realimentado
    add_line(modelo, 'planta/2', 'motor/2', 'autorouting', 'on');     % q' al motor

    %% ======================= 5. REGISTRO =======================
    registrar(modelo, 'planta/1',  'log estado',   'sl_z',       [1330 100 1430 135]);
    registrar(modelo, 'bateria/1', 'log tension',  'sl_tension', [1330 165 1430 200]);
    registrar(modelo, 'agarre/1',  'log par',      'sl_par',     [1330 230 1430 265]);
    registrar(modelo, 'z ref/1',   'log consigna', 'sl_ref',     [1330 295 1430 330]);

    %% ======================= areas =============================
    % El ancho de cada area alcanza para que no se corte su titulo.
    area(modelo, 'areaConsigna', 'Consigna: adonde se le pide ir',    [  50 60  260 290]);
    area(modelo, 'areaControl',  'Control: U = -K (z - z_ref)',       [ 300 60  600 290]);
    area(modelo, 'areaActuador', 'Actuador: bateria, motor y agarre', [ 640 60 1050 290]);
    area(modelo, 'areaPlanta',   'Planta mecanica',                   [1070 60 1290 290]);
    area(modelo, 'areaRegistro', 'Registro',                          [1310 60 1460 360]);

    archivo = fullfile(carpeta_destino, [nombre_modelo '.slx']);
    if exist(archivo, 'file'), delete(archivo); end
    save_system(modelo, archivo);
    close_system(modelo, 0);
end

% ===================================================================
function crear_lqr(ruta)
%CREAR_LQR  U = -K e, con K en un unico bloque de ganancia matricial.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'error de estado', 'Position', [60 113 90 127]);
    set_param([ruta '/Out1'], 'Name', 'U', 'Position', [400 113 430 127]);
    add_block('simulink/Math Operations/Gain', [ruta '/menos K'], ...
        'Gain', '-K', 'Multiplication', 'Matrix(K*u)', 'Position', [220 95 300 145]);
    add_line(ruta, 'error de estado/1', 'menos K/1');
    add_line(ruta, 'menos K/1', 'U/1');
    area(ruta, 'areaLQR', 'U = -K (z - z_ref)   con K = [Kx  Kv  Kphi  Komega] en voltios', ...
        [40 60 470 190]);
end

% ===================================================================
function crear_motor(ruta)
%CREAR_MOTOR  tau = beta_V*U - b_m*w_rel,  con w_rel = [-1/r  -1] q'.
%   La contraelectromotriz es el camino visible de realimentacion: cuanto mas
%   rapido gira la rueda respecto del cuerpo, menos par entrega el motor.
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'U', 'Position', [60 113 90 127]);
    add_block('simulink/Sources/In1', [ruta '/q punto'], 'Port', '2', ...
        'Position', [60 303 90 317]);
    set_param([ruta '/Out1'], 'Name', 'tau', 'Position', [620 193 650 207]);

    add_block('simulink/Math Operations/Gain', [ruta '/beta_V'], 'Gain', 'beta_V', ...
        'Position', [200 95 290 145]);
    add_block('simulink/Math Operations/Gain', [ruta '/w rel'], ...
        'Gain', '[-1/r  -1]', 'Multiplication', 'Matrix(K*u)', ...
        'Position', [200 285 310 335]);
    add_block('simulink/Math Operations/Gain', [ruta '/b_m'], 'Gain', 'b_m', ...
        'Position', [370 285 460 335]);
    add_block('simulink/Math Operations/Sum', [ruta '/par'], ...
        'IconShape', 'rectangular', 'Inputs', '+-', 'Position', [530 130 570 270]);

    add_line(ruta, 'U/1', 'beta_V/1');
    add_line(ruta, 'q punto/1', 'w rel/1');
    add_line(ruta, 'w rel/1', 'b_m/1');
    add_line(ruta, 'beta_V/1', 'par/1');
    add_line(ruta, 'b_m/1', 'par/2');
    add_line(ruta, 'par/1', 'tau/1');
    area(ruta, 'areaMotorPar',  'par que entrega el motor:  beta_V * U', [180 60 490 190]);
    area(ruta, 'areaMotorFcem', 'contraelectromotriz: frena proporcional a w_rel = -v/r - omega', ...
        [180 250 490 380]);
end

% ===================================================================
function crear_planta(ruta)
%CREAR_PLANTA  M(phi) q'' = H tau - D q' + sin(phi) [-h omega^2 ; k]
%
%   Todo va en vectores de dos componentes, q = [x; phi], asi que la ecuacion
%   se lee entera. Cuatro bandas horizontales que no se superponen:
%     1. lado derecho          el par del motor y las perdidas
%     2. matriz de masa        M(phi), armada por filas
%     3. centrifugo y gravedad el unico termino no lineal
%     4. resolver y estado     un Divide matricial y dos integradores
    add_block('simulink/Ports & Subsystems/Subsystem', ruta);
    delete_line(ruta, 'In1/1', 'Out1/1');
    set_param([ruta '/In1'], 'Name', 'tau', 'Position', [40 148 70 162]);
    set_param([ruta '/Out1'], 'Name', 'z');
    add_block('simulink/Sinks/Out1', [ruta '/q punto'], 'Port', '2');
    set_param([ruta '/z'], 'Position', [1420 148 1450 162]);
    set_param([ruta '/q punto'], 'Position', [1420 328 1450 342]);

    % ---------- banda 1: lado derecho ----------
    add_block('simulink/Math Operations/Gain', [ruta '/H'], 'Gain', '[-1/r; -1]', ...
        'Multiplication', 'Matrix(K*u)', 'Position', [170 125 280 185]);
    add_block('simulink/Math Operations/Gain', [ruta '/D perdidas'], ...
        'Gain', '[b_x + b_eje/r^2,  b_eje/r;  b_eje/r,  b_eje + b_phi]', ...
        'Multiplication', 'Matrix(K*u)', 'Position', [170 210 420 280]);
    add_block('simulink/Math Operations/Sum', [ruta '/lado derecho'], ...
        'IconShape', 'rectangular', 'Inputs', '+-+', 'Position', [820 115 880 285]);

    % ---------- banda 2: matriz de masa ----------
    add_block('simulink/Math Operations/Trigonometric Function', [ruta '/coseno'], ...
        'Operator', 'cos', 'Position', [170 440 220 490]);
    add_block('simulink/Math Operations/Gain', [ruta '/menos h'], 'Gain', '-h', ...
        'Position', [270 440 340 490]);
    add_block('simulink/Sources/Constant', [ruta '/e acople'], 'Value', 'e_acople', ...
        'Position', [270 370 340 405]);
    add_block('simulink/Math Operations/Sum', [ruta '/M12'], ...
        'IconShape', 'rectangular', 'Inputs', '++', 'Position', [400 390 450 480]);
    add_block('simulink/Sources/Constant', [ruta '/coef a'], 'Value', 'a', ...
        'Position', [400 320 450 355]);
    add_block('simulink/Sources/Constant', [ruta '/coef j'], 'Value', 'j', ...
        'Position', [400 520 450 555]);
    add_block('simulink/Math Operations/Matrix Concatenate', [ruta '/fila 1'], ...
        'NumInputs', '2', 'Mode', 'Multidimensional array', 'ConcatenateDimension', '2', ...
        'Position', [540 325 565 400]);
    add_block('simulink/Math Operations/Matrix Concatenate', [ruta '/fila 2'], ...
        'NumInputs', '2', 'Mode', 'Multidimensional array', 'ConcatenateDimension', '2', ...
        'Position', [540 465 565 540]);
    add_block('simulink/Math Operations/Matrix Concatenate', [ruta '/M'], ...
        'NumInputs', '2', 'Mode', 'Multidimensional array', 'ConcatenateDimension', '1', ...
        'Position', [660 350 685 520]);

    % ---------- banda 3: centrifugo y gravedad ----------
    add_block('simulink/Math Operations/Trigonometric Function', [ruta '/seno'], ...
        'Operator', 'sin', 'Position', [170 650 220 700]);
    add_block('simulink/Math Operations/Math Function', [ruta '/omega al cuadrado'], ...
        'Operator', 'square', 'Position', [170 740 220 790]);
    add_block('simulink/Math Operations/Gain', [ruta '/menos h omega2'], 'Gain', '-h', ...
        'Position', [270 740 340 790]);
    add_block('simulink/Sources/Constant', [ruta '/coef k'], 'Value', 'k', ...
        'Position', [270 815 340 850]);
    add_block('simulink/Signal Routing/Mux', [ruta '/vector no lineal'], 'Inputs', '2', ...
        'Position', [410 745 415 845]);
    add_block('simulink/Math Operations/Product', [ruta '/por seno'], 'Inputs', '2', ...
        'Position', [520 670 570 750]);

    % ---------- banda 4: resolver y estado ----------
    add_block('simulink/Math Operations/Divide', [ruta '/resolver M'], ...
        'Multiplication', 'Matrix(*)', 'Inputs', '/*', 'Position', [960 160 1030 250]);
    add_block('simulink/Continuous/Integrator', [ruta '/integrar q punto'], ...
        'InitialCondition', 'q_punto0', 'Position', [1090 135 1135 180]);
    add_block('simulink/Continuous/Integrator', [ruta '/integrar q'], ...
        'InitialCondition', 'q0', 'Position', [1180 135 1225 180]);
    add_block('simulink/Signal Routing/Demux', [ruta '/separar q'], 'Outputs', '2', ...
        'Position', [1270 135 1275 180]);
    add_block('simulink/Signal Routing/Demux', [ruta '/separar q punto'], 'Outputs', '2', ...
        'Position', [1090 320 1095 365]);
    add_block('simulink/Signal Routing/Mux', [ruta '/armar z'], 'Inputs', '4', ...
        'Position', [1340 120 1345 190]);

    %% ---------------- conexiones ----------------
    % banda 4: estado
    add_line(ruta, 'resolver M/1', 'integrar q punto/1', 'autorouting', 'on');
    add_line(ruta, 'integrar q punto/1', 'integrar q/1', 'autorouting', 'on');
    add_line(ruta, 'integrar q/1', 'separar q/1', 'autorouting', 'on');
    add_line(ruta, 'integrar q punto/1', 'separar q punto/1', 'autorouting', 'on');
    add_line(ruta, 'integrar q punto/1', 'q punto/1', 'autorouting', 'on');
    add_line(ruta, 'separar q/1', 'armar z/1', 'autorouting', 'on');        % x
    add_line(ruta, 'separar q punto/1', 'armar z/2', 'autorouting', 'on');  % v
    add_line(ruta, 'separar q/2', 'armar z/3', 'autorouting', 'on');        % phi
    add_line(ruta, 'separar q punto/2', 'armar z/4', 'autorouting', 'on');  % omega
    add_line(ruta, 'armar z/1', 'z/1', 'autorouting', 'on');
    % banda 1: lado derecho
    add_line(ruta, 'tau/1', 'H/1', 'autorouting', 'on');
    add_line(ruta, 'integrar q punto/1', 'D perdidas/1', 'autorouting', 'on');
    add_line(ruta, 'H/1', 'lado derecho/1', 'autorouting', 'on');
    add_line(ruta, 'D perdidas/1', 'lado derecho/2', 'autorouting', 'on');
    add_line(ruta, 'por seno/1', 'lado derecho/3', 'autorouting', 'on');
    % banda 2: matriz de masa
    add_line(ruta, 'separar q/2', 'coseno/1', 'autorouting', 'on');
    add_line(ruta, 'coseno/1', 'menos h/1', 'autorouting', 'on');
    add_line(ruta, 'menos h/1', 'M12/2', 'autorouting', 'on');
    add_line(ruta, 'e acople/1', 'M12/1', 'autorouting', 'on');
    add_line(ruta, 'coef a/1', 'fila 1/1', 'autorouting', 'on');
    add_line(ruta, 'M12/1', 'fila 1/2', 'autorouting', 'on');
    add_line(ruta, 'M12/1', 'fila 2/1', 'autorouting', 'on');
    add_line(ruta, 'coef j/1', 'fila 2/2', 'autorouting', 'on');
    add_line(ruta, 'fila 1/1', 'M/1', 'autorouting', 'on');
    add_line(ruta, 'fila 2/1', 'M/2', 'autorouting', 'on');
    % banda 3: centrifugo y gravedad
    add_line(ruta, 'separar q/2', 'seno/1', 'autorouting', 'on');
    add_line(ruta, 'separar q punto/2', 'omega al cuadrado/1', 'autorouting', 'on');
    add_line(ruta, 'omega al cuadrado/1', 'menos h omega2/1', 'autorouting', 'on');
    add_line(ruta, 'menos h omega2/1', 'vector no lineal/1', 'autorouting', 'on');
    add_line(ruta, 'coef k/1', 'vector no lineal/2', 'autorouting', 'on');
    add_line(ruta, 'seno/1', 'por seno/1', 'autorouting', 'on');
    add_line(ruta, 'vector no lineal/1', 'por seno/2', 'autorouting', 'on');
    % resolver
    add_line(ruta, 'M/1', 'resolver M/1', 'autorouting', 'on');
    add_line(ruta, 'lado derecho/1', 'resolver M/2', 'autorouting', 'on');

    %% ---------------- areas, una por banda, sin superponerse ----------------
    area(ruta, 'areaLadoDerecho', '1.  lado derecho:  H tau  -  D q''', ...
        [140 90 910 300]);
    area(ruta, 'areaMasa', '2.  matriz de masa  M(phi) = [a, M12 ; M12, j]   con M12 = -h cos(phi) + e_acople', ...
        [140 310 910 580]);
    area(ruta, 'areaNoLineal', '3.  centrifugo y gravedad:  sin(phi) [-h omega^2 ; k]   el unico termino no lineal', ...
        [140 610 910 880]);
    area(ruta, 'areaResolver', '4.  resolver  M q'''' = lado derecho,  e integrar hasta q', ...
        [930 90 1400 390]);
end

% ===================================================================
function area(ruta, etiqueta, texto, posicion)
%AREA Recuadro con titulo para agrupar visualmente. Es decorativo: si la version
%   de Simulink no tuviera el bloque Area, el modelo funciona igual.
    try
        nombre = [ruta '/' etiqueta];
        add_block('built-in/Area', nombre, 'Position', posicion);
        set_param(nombre, 'Name', texto);
    catch ME
        warning('construir_pendulo_simulink:area', ...
            'No se pudo crear el area "%s": %s', etiqueta, ME.message);
    end
end

function registrar(modelo, origen, nombre, variable, posicion)
    bloque = [modelo '/' nombre];
    add_block('simulink/Sinks/To Workspace', bloque, 'VariableName', variable, ...
        'SaveFormat', 'Structure With Time', 'Position', posicion);
    add_line(modelo, origen, [nombre '/1'], 'autorouting', 'on');
end
