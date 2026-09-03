function mdl = construir_robot_slx(P, C, E, nombre)
%CONSTRUIR_ROBOT_SLX  Arma robot_segway.slx por codigo, con subsistemas y senales con nombre.
%   mdl = construir_robot_slx(P, C, E)
%
%   Nivel superior:   Escenario --> Controlador --> Robot --> Sensores --> (vuelve al Controlador)
%                     Registro (To Workspace con nombres)   Graficos (scopes)
%   Los bloques MATLAB Function llaman a robot_controlador, robot_planta y robot_sensores, y leen
%   los parametros de la estructura 'par' del workspace (ver parametros_simulink).
  if nargin < 4 || isempty(nombre), nombre = 'robot_segway'; end
  mdl = nombre; aqui = fileparts(mfilename('fullpath'));
  cargar_workspace(P, C, E);
  if bdIsLoaded(mdl), close_system(mdl, 0); end
  archivo = fullfile(aqui, [mdl '.slx']); if isfile(archivo), delete(archivo); end
  new_system(mdl); open_system(mdl);
  ab = @(src, nom, pos, varargin) add_block(src, nom, 'Position', pos, varargin{:});
  L = @(sys, a, b, nom) nombrar(add_line(sys, a, b, 'autorouting', 'on'), nom);

  nombres_estados = {'x','y_eje','inclinacion','largo_pata','dx','dy_eje','d_inclinacion','d_largo_pata', ...
    'ang_rueda_izq','vel_rueda_izq','ang_rueda_der','vel_rueda_der','ang_rotor_izq','vel_rotor_izq', ...
    'ang_rotor_der','vel_rotor_der','corriente_izq','corriente_der','largo_mecanismo','d_largo_mecanismo'};
  nombres_salidas = {'acel_x','acel_y_eje','acel_inclinacion','acel_largo','normal','fuerza_piso_izq', ...
    'fuerza_piso_der','desliza','par_reductor_izq','par_reductor_der','par_servo','angulo_servo', ...
    'corriente_izq','corriente_der','tension_bus','imu_fx','imu_fy','penetracion'};
  nombres_estim = {'inclinacion_est','x_est','dx_est','largo_pata_est','par_rueda_cmd','tension_saturada','en_vuelo'};
  nombres_medidas = {'giroscopo','acel_x','acel_y','encoder_izq','encoder_der'};
  nombres_comandos = {'tension_izq','tension_der','angulo_servo_ref'};

  % ================= nivel superior =================
  ab('simulink/Ports & Subsystems/Subsystem', [mdl '/Escenario'],   [40 120 150 200]);
  ab('simulink/Ports & Subsystems/Subsystem', [mdl '/Controlador'], [240 110 370 210]);
  ab('simulink/Ports & Subsystems/Subsystem', [mdl '/Robot'],       [470 100 600 220]);
  ab('simulink/Ports & Subsystems/Subsystem', [mdl '/Sensores'],    [470 300 600 380]);
  ab('simulink/Ports & Subsystems/Subsystem', [mdl '/Registro'],    [720 90 850 250]);
  ab('simulink/Ports & Subsystems/Subsystem', [mdl '/Graficos'],    [720 300 850 400]);
  for s = {'Escenario','Controlador','Robot','Sensores','Registro','Graficos'}
    delete_line([mdl '/' s{1}], 'In1/1', 'Out1/1'); delete_block([mdl '/' s{1} '/In1']); delete_block([mdl '/' s{1} '/Out1']);
  end

  % ---------- Escenario ----------
  s = [mdl '/Escenario'];
  ab('simulink/Sources/From Workspace', [s '/referencias (x_ref, l_ref)'], [40 40 200 70], 'VariableName', 'referencias_ts', 'SampleTime', 'Ts', 'Interpolate', 'off', 'OutputAfterFinalValue', 'Holding final value');
  ab('simulink/Sources/From Workspace', [s '/perturbaciones (F_x, M_p, pendiente, mu, F_escalon)'], [40 120 200 150], 'VariableName', 'perturbaciones_ts', 'SampleTime', '0', 'Interpolate', 'off', 'OutputAfterFinalValue', 'Holding final value');
  ab('simulink/Sinks/Out1', [s '/referencias'], [280 45 310 65]); ab('simulink/Sinks/Out1', [s '/perturbaciones'], [280 125 310 145]);
  L(s, 'referencias (x_ref, l_ref)/1', 'referencias/1', 'referencias');
  L(s, 'perturbaciones (F_x, M_p, pendiente, mu, F_escalon)/1', 'perturbaciones/1', 'perturbaciones');

  % ---------- Controlador ----------
  s = [mdl '/Controlador'];
  ab('simulink/Sources/In1', [s '/medidas'], [40 40 70 60]); ab('simulink/Sources/In1', [s '/referencias'], [40 100 70 120]);
  ab('simulink/Sources/Constant', [s '/reset'], [40 160 70 190], 'Value', '0', 'SampleTime', 'Ts');
  ab('simulink/User-Defined Functions/MATLAB Function', [s '/ley de control'], [160 40 300 190]);
  ab('simulink/Sinks/Out1', [s '/comandos'], [380 60 410 80]); ab('simulink/Sinks/Out1', [s '/estimaciones'], [380 140 410 160]);
  poner_codigo([s '/ley de control'], ['function [comandos, estimaciones] = fcn(medidas, referencias, reset)\n%%#codegen\n' ...
    '%% medidas = [giroscopo; acel_x; acel_y; encoder_izq; encoder_der]   referencias = [x_ref; l_ref]\n' ...
    '[comandos, estimaciones] = robot_controlador(medidas, referencias, par, reset);\n']);
  L(s, 'medidas/1', 'ley de control/1', 'medidas'); L(s, 'referencias/1', 'ley de control/2', 'referencias'); L(s, 'reset/1', 'ley de control/3', 'reset');
  L(s, 'ley de control/1', 'comandos/1', 'comandos'); L(s, 'ley de control/2', 'estimaciones/1', 'estimaciones');

  % ---------- Robot ----------
  s = [mdl '/Robot'];
  ab('simulink/Sources/In1', [s '/comandos'], [40 60 70 80]); ab('simulink/Sources/In1', [s '/perturbaciones'], [40 120 70 140]);
  ab('simulink/User-Defined Functions/MATLAB Function', [s '/dinamica'], [180 40 320 170]);
  ab('simulink/Continuous/Integrator', [s '/integrador'], [400 60 440 100], 'InitialCondition', 'estados_iniciales');
  ab('simulink/Sinks/Out1', [s '/estados'], [560 70 590 90]); ab('simulink/Sinks/Out1', [s '/salidas'], [560 150 590 170]);
  ab('simulink/Signal Routing/Demux', [s '/demux estados'], [640 40 645 400], 'Outputs', '20');
  ab('simulink/Signal Routing/Bus Creator', [s '/estados con nombre'], [740 40 745 400], 'Inputs', '20');
  ab('simulink/Sinks/Out1', [s '/estados_bus'], [820 210 850 230]);
  ab('simulink/Signal Routing/Demux', [s '/demux salidas'], [640 450 645 800], 'Outputs', '18');
  ab('simulink/Signal Routing/Bus Creator', [s '/salidas con nombre'], [740 450 745 800], 'Inputs', '18');
  ab('simulink/Sinks/Out1', [s '/salidas_bus'], [820 615 850 635]);
  poner_codigo([s '/dinamica'], ['function [derivada_estados, salidas] = fcn(estados, comandos, perturbaciones)\n%%#codegen\n' ...
    '%% estados (20): [x y_eje inclinacion largo_pata dx dy d_inclinacion d_largo ang/vel rueda izq-der ang/vel rotor izq-der corrientes largo_mecanismo d_largo_mecanismo]\n' ...
    '%% comandos = [tension_izq; tension_der; angulo_servo_ref]   perturbaciones = [F_x; M_p; pendiente; mu; F_escalon]\n' ...
    '[derivada_estados, salidas] = robot_planta(estados, comandos, perturbaciones, par);\n']);
  L(s, 'comandos/1', 'dinamica/2', 'comandos'); L(s, 'perturbaciones/1', 'dinamica/3', 'perturbaciones');
  L(s, 'dinamica/1', 'integrador/1', 'derivada_estados'); L(s, 'integrador/1', 'dinamica/1', 'estados');
  L(s, 'integrador/1', 'estados/1', ''); L(s, 'dinamica/2', 'salidas/1', 'salidas');
  L(s, 'integrador/1', 'demux estados/1', ''); L(s, 'dinamica/2', 'demux salidas/1', '');
  for k = 1:20, L(s, sprintf('demux estados/%d', k), sprintf('estados con nombre/%d', k), nombres_estados{k}); end
  for k = 1:18, L(s, sprintf('demux salidas/%d', k), sprintf('salidas con nombre/%d', k), nombres_salidas{k}); end
  L(s, 'estados con nombre/1', 'estados_bus/1', 'estados_bus'); L(s, 'salidas con nombre/1', 'salidas_bus/1', 'salidas_bus');

  % ---------- Sensores ----------
  s = [mdl '/Sensores'];
  ab('simulink/Sources/In1', [s '/estados'], [40 40 70 60]); ab('simulink/Sources/In1', [s '/salidas'], [40 110 70 130]);
  ab('simulink/Discrete/Zero-Order Hold', [s '/muestreo estados'], [130 40 170 60], 'SampleTime', 'Ts');
  ab('simulink/Discrete/Zero-Order Hold', [s '/muestreo salidas'], [130 110 170 130], 'SampleTime', 'Ts');
  ab('simulink/Sources/Random Number', [s '/ruido'], [130 180 170 210], 'Mean', '0', 'Variance', '1', 'Seed', 'semilla+[0 1 2]', 'SampleTime', 'Ts');
  ab('simulink/User-Defined Functions/MATLAB Function', [s '/IMU y encoders'], [260 40 400 210]);
  ab('simulink/Discrete/Delay', [s '/retardo'], [470 110 510 140], 'DelayLength', 'retardo_muestras', 'InitialCondition', 'medidas_iniciales', 'SampleTime', 'Ts');
  ab('simulink/Sinks/Out1', [s '/medidas'], [580 115 610 135]);
  poner_codigo([s '/IMU y encoders'], ['function medidas = fcn(estados, salidas, ruido)\n%%#codegen\n' ...
    '%% medidas = [giroscopo; acel_x; acel_y; encoder_izq; encoder_der]\n' ...
    'medidas = robot_sensores(estados, salidas, ruido, par);\n']);
  L(s, 'estados/1', 'muestreo estados/1', ''); L(s, 'salidas/1', 'muestreo salidas/1', '');
  L(s, 'muestreo estados/1', 'IMU y encoders/1', 'estados'); L(s, 'muestreo salidas/1', 'IMU y encoders/2', 'salidas'); L(s, 'ruido/1', 'IMU y encoders/3', 'ruido');
  L(s, 'IMU y encoders/1', 'retardo/1', 'medidas sin retardo'); L(s, 'retardo/1', 'medidas/1', 'medidas');

  % ---------- Registro ----------
  s = [mdl '/Registro'];
  entradas = {'estados_bus','salidas_bus','comandos','estimaciones','medidas','estados','salidas'};
  for k = 1:numel(entradas)
    ab('simulink/Sources/In1', [s '/' entradas{k}], [40 40+60*(k-1) 70 60+60*(k-1)]);
  end
  ab('simulink/Sinks/To Workspace', [s '/a workspace: estados'],      [200 40 320 60],  'VariableName', 'estados',      'SaveFormat', 'Timeseries');
  ab('simulink/Sinks/To Workspace', [s '/a workspace: salidas'],      [200 100 320 120], 'VariableName', 'salidas',      'SaveFormat', 'Timeseries');
  ab('simulink/Sinks/To Workspace', [s '/a workspace: comandos'],     [200 160 320 180], 'VariableName', 'comandos',     'SaveFormat', 'Timeseries');
  ab('simulink/Sinks/To Workspace', [s '/a workspace: estimaciones'], [200 220 320 240], 'VariableName', 'estimaciones', 'SaveFormat', 'Timeseries');
  ab('simulink/Sinks/To Workspace', [s '/a workspace: medidas'],      [200 280 320 300], 'VariableName', 'medidas',      'SaveFormat', 'Timeseries');
  ab('simulink/Sinks/To Workspace', [s '/vector estados'],            [200 340 320 360], 'VariableName', 'estados_vec',  'SaveFormat', 'Structure With Time');
  ab('simulink/Sinks/To Workspace', [s '/vector salidas'],            [200 400 320 420], 'VariableName', 'salidas_vec',  'SaveFormat', 'Structure With Time');
  L(s, 'estados_bus/1', 'a workspace: estados/1', ''); L(s, 'salidas_bus/1', 'a workspace: salidas/1', '');
  L(s, 'comandos/1', 'a workspace: comandos/1', ''); L(s, 'estimaciones/1', 'a workspace: estimaciones/1', '');
  L(s, 'medidas/1', 'a workspace: medidas/1', ''); L(s, 'estados/1', 'vector estados/1', ''); L(s, 'salidas/1', 'vector salidas/1', '');

  % ---------- Graficos ----------
  s = [mdl '/Graficos'];
  ab('simulink/Sources/In1', [s '/estados_bus'], [40 40 70 60]); ab('simulink/Sources/In1', [s '/estimaciones'], [40 120 70 140]);
  ab('simulink/Sources/In1', [s '/comandos'], [40 200 70 220]); ab('simulink/Sources/In1', [s '/referencias'], [40 280 70 300]);
  ab('simulink/Signal Routing/Bus Selector', [s '/selector estados'], [150 30 155 120], 'OutputSignals', 'inclinacion,y_eje,largo_pata,x');
  ab('simulink/Signal Routing/Demux', [s '/demux estimaciones'], [150 120 155 160], 'Outputs', '7');
  ab('simulink/Signal Routing/Demux', [s '/demux referencias'], [150 280 155 300], 'Outputs', '2');
  ab('simulink/Signal Routing/Mux', [s '/inclinacion real y estimada'], [260 30 265 70], 'Inputs', '2');
  ab('simulink/Signal Routing/Mux', [s '/altura del eje y largo de pata'], [260 90 265 130], 'Inputs', '2');
  ab('simulink/Signal Routing/Mux', [s '/posicion real y consigna'], [260 250 265 290], 'Inputs', '2');
  ab('simulink/Sinks/Scope', [s '/Inclinacion'], [360 35 400 65]); ab('simulink/Sinks/Scope', [s '/Altura y pata'], [360 95 400 125]);
  ab('simulink/Sinks/Scope', [s '/Tensiones de motor'], [360 195 400 225]); ab('simulink/Sinks/Scope', [s '/Posicion'], [360 255 400 285]);
  L(s, 'estados_bus/1', 'selector estados/1', ''); L(s, 'estimaciones/1', 'demux estimaciones/1', ''); L(s, 'referencias/1', 'demux referencias/1', '');
  % (las lineas que salen de un Bus Selector ya llevan el nombre del elemento; no se pueden renombrar)
  L(s, 'selector estados/1', 'inclinacion real y estimada/1', ''); L(s, 'demux estimaciones/1', 'inclinacion real y estimada/2', 'inclinacion_est');
  L(s, 'selector estados/2', 'altura del eje y largo de pata/1', ''); L(s, 'selector estados/3', 'altura del eje y largo de pata/2', '');
  L(s, 'selector estados/4', 'posicion real y consigna/1', ''); L(s, 'demux referencias/1', 'posicion real y consigna/2', 'x_ref');
  L(s, 'inclinacion real y estimada/1', 'Inclinacion/1', ''); L(s, 'altura del eje y largo de pata/1', 'Altura y pata/1', '');
  L(s, 'comandos/1', 'Tensiones de motor/1', ''); L(s, 'posicion real y consigna/1', 'Posicion/1', '');
  for k = 2:7, ab('simulink/Sinks/Terminator', sprintf('%s/sin uso %d', s, k), [200 120+15*k 215 130+15*k]); L(s, sprintf('demux estimaciones/%d', k), sprintf('sin uso %d/1', k), ''); end
  ab('simulink/Sinks/Terminator', [s '/sin uso l_ref'], [200 300 215 310]); L(s, 'demux referencias/2', 'sin uso l_ref/1', '');

  % ---------- conexiones del nivel superior ----------
  L(mdl, 'Escenario/1', 'Controlador/2', 'referencias'); L(mdl, 'Escenario/2', 'Robot/2', 'perturbaciones');
  L(mdl, 'Controlador/1', 'Robot/1', 'comandos'); L(mdl, 'Robot/1', 'Sensores/1', 'estados'); L(mdl, 'Robot/2', 'Sensores/2', 'salidas');
  L(mdl, 'Sensores/1', 'Controlador/1', 'medidas');
  L(mdl, 'Robot/3', 'Registro/1', 'estados_bus'); L(mdl, 'Robot/4', 'Registro/2', 'salidas_bus'); L(mdl, 'Controlador/1', 'Registro/3', '');
  L(mdl, 'Controlador/2', 'Registro/4', 'estimaciones'); L(mdl, 'Sensores/1', 'Registro/5', ''); L(mdl, 'Robot/1', 'Registro/6', ''); L(mdl, 'Robot/2', 'Registro/7', '');
  L(mdl, 'Robot/3', 'Graficos/1', ''); L(mdl, 'Controlador/2', 'Graficos/2', ''); L(mdl, 'Controlador/1', 'Graficos/3', ''); L(mdl, 'Escenario/1', 'Graficos/4', '');

  % ---------- parametros 'par' en los tres bloques MATLAB Function ----------
  for ruta = {[mdl '/Controlador/ley de control'], [mdl '/Robot/dinamica'], [mdl '/Sensores/IMU y encoders']}
    ch = find(sfroot, '-isa', 'Stateflow.EMChart', 'Path', ruta{1});
    dat = Stateflow.Data(ch); dat.Name = 'par'; dat.Scope = 'Parameter';
  end

  % ---------- solver y orden ----------
  set_param(mdl, 'Solver', 'ode15s', 'RelTol', '1e-5', 'AbsTol', '1e-7', 'MaxStep', '1e-3', 'StopTime', 'tiempo_final', 'ReturnWorkspaceOutputs', 'on');
  % el nivel superior conserva el orden Escenario -> Controlador -> Robot -> Sensores; los subsistemas se ordenan solos
  for s = {[mdl '/Escenario'], [mdl '/Controlador'], [mdl '/Robot'], [mdl '/Sensores'], [mdl '/Registro'], [mdl '/Graficos']}
    Simulink.BlockDiagram.arrangeSystem(s{1});
  end
  save_system(mdl, archivo);
  fprintf('Modelo %s.slx creado en %s\n', mdl, aqui);
end

function h = nombrar(h, nom)
  if ~isempty(nom), set_param(h, 'Name', nom); end
end
function poner_codigo(ruta, txt)
  txt = sprintf(txt);
  ch = find(sfroot, '-isa', 'Stateflow.EMChart', 'Path', ruta); ch.Script = txt;
end
