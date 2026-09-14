function archivo = construir_dinamica_pata()
%CONSTRUIR_DINAMICA_PATA Construye el banco Simulink con bloques nativos.
  carpeta = fileparts(mfilename('fullpath'));
  archivo = fullfile(carpeta, 'dinamica_pata_simulink.slx');
  modelo = 'dinamica_pata_simulink';
  if bdIsLoaded(modelo), close_system(modelo, 0); end
  if isfile(archivo), delete(archivo); end
  new_system(modelo);
  set_param(modelo, 'Solver', 'ode45', 'SolverType', 'Variable-step', ...
    'RelTol', '1e-9', 'AbsTol', '1e-11', 'MaxStep', '0.001', ...
    'StopTime', '2.5', 'ReturnWorkspaceOutputs', 'on');

  fuente(modelo, 'theta ref', 'theta_ref_ext', [30 50 150 80]);
  fuente(modelo, 'tau perturbacion', 'tau_pert_ext', [30 105 150 135]);
  fuente(modelo, 'normal', 'normal_ext', [30 245 150 275]);
  fuente(modelo, 'caso', 'caso_ext', [30 300 150 330]);
  crear_servo([modelo '/Servo PD']);
  set_param([modelo '/Servo PD'], 'Position', [235 45 400 175]);
  crear_planta([modelo '/Dinamica theta']);
  set_param([modelo '/Dinamica theta'], 'Position', [485 90 700 340]);

  add_line(modelo, 'theta ref/1', 'Servo PD/1', 'autorouting', 'on');
  add_line(modelo, 'tau perturbacion/1', 'Servo PD/4', 'autorouting', 'on');
  add_line(modelo, 'Dinamica theta/1', 'Servo PD/2', 'autorouting', 'on');
  add_line(modelo, 'Dinamica theta/2', 'Servo PD/3', 'autorouting', 'on');
  add_line(modelo, 'Servo PD/1', 'Dinamica theta/1', 'autorouting', 'on');
  add_line(modelo, 'normal/1', 'Dinamica theta/2', 'autorouting', 'on');
  add_line(modelo, 'caso/1', 'Dinamica theta/3', 'autorouting', 'on');

  nombres = {'theta','dtheta','ddtheta','tau','Ieq','Vprima','normal_estimada','contacto_valido','tau_tope'};
  puertos = {'Dinamica theta/1','Dinamica theta/2','Dinamica theta/3','Servo PD/1', ...
             'Dinamica theta/4','Dinamica theta/5','Dinamica theta/6','Dinamica theta/7','Dinamica theta/8'};
  for i = 1:numel(nombres)
    y = 25 + 38*i;
    bloque = [modelo '/log_' nombres{i}];
    add_block('simulink/Sinks/To Workspace', bloque, 'Position', [785 y 900 y+22], ...
      'VariableName', [nombres{i} '_slx'], 'SaveFormat', 'Timeseries', 'MaxDataPoints', 'inf');
    add_line(modelo, puertos{i}, ['log_' nombres{i} '/1'], 'autorouting', 'on');
  end
  add_block('simulink/Sinks/Terminator', [modelo '/terminar caso'], ...
    'Position', [735 360 755 380]);
  add_line(modelo, 'Dinamica theta/9', 'terminar caso/1', 'autorouting', 'on');

  Simulink.BlockDiagram.arrangeSystem(modelo);
  save_system(modelo, archivo);
  close_system(modelo, 0);
  fprintf('Modelo %s creado en %s\n', [modelo '.slx'], carpeta);
end

function fuente(modelo, nombre, variable, posicion)
  add_block('simulink/Sources/From Workspace', [modelo '/' nombre], ...
    'Position', posicion, 'VariableName', variable, 'Interpolate', 'on', ...
    'OutputAfterFinalValue', 'Holding final value');
end

function crear_servo(ruta)
  add_block('simulink/Ports & Subsystems/Subsystem', ruta);
  limpiar_subsistema(ruta);
  inport(ruta, 'theta_ref', 1, [25 30 55 44]);
  inport(ruta, 'theta', 2, [25 75 55 89]);
  inport(ruta, 'dtheta', 3, [25 120 55 134]);
  inport(ruta, 'tau_pert', 4, [25 165 55 179]);
  add_block('simulink/Math Operations/Sum', [ruta '/error'], ...
    'Inputs', '+-', 'Position', [90 37 115 82]);
  add_block('simulink/Math Operations/Gain', [ruta '/Kp'], ...
    'Gain', 'par_pata.Kp', 'Position', [145 42 205 77]);
  add_block('simulink/Math Operations/Gain', [ruta '/menos Kd'], ...
    'Gain', '-par_pata.Kd', 'Position', [145 112 205 147]);
  add_block('simulink/Math Operations/Sum', [ruta '/PD'], ...
    'Inputs', '++', 'Position', [240 65 265 115]);
  add_block('simulink/Math Operations/Abs', [ruta '/velocidad absoluta'], ...
    'Position', [230 130 260 160]);
  add_block('simulink/Math Operations/Gain', [ruta '/fraccion velocidad'], ...
    'Gain', '1/par_pata.w_nl', 'Position', [285 130 345 160]);
  add_block('simulink/Sources/Constant', [ruta '/uno'], 'Value', '1', ...
    'Position', [285 175 315 195]);
  add_block('simulink/Math Operations/Sum', [ruta '/margen velocidad'], ...
    'Inputs', '+-', 'Position', [375 135 400 180]);
  add_block('simulink/Discontinuities/Saturation', [ruta '/margen positivo'], ...
    'LowerLimit', '0', 'UpperLimit', '1', 'Position', [430 140 480 175]);
  add_block('simulink/Math Operations/Gain', [ruta '/limite motriz'], ...
    'Gain', 'par_pata.tau_max', 'Position', [510 140 575 175]);
  add_block('simulink/Math Operations/Product', [ruta '/potencia mecanica'], ...
    'Inputs', '**', 'Position', [300 220 330 250]);
  add_block('simulink/Logic and Bit Operations/Compare To Zero', [ruta '/acompanha giro'], ...
    'relop', '>', 'Position', [365 220 435 250]);
  add_block('simulink/Sources/Constant', [ruta '/tau max'], ...
    'Value', 'par_pata.tau_max', 'Position', [505 220 565 240]);
  add_block('simulink/Signal Routing/Switch', [ruta '/seleccionar limite'], ...
    'Criteria', 'u2 ~= 0', 'Position', [610 145 660 225]);
  add_block('simulink/Math Operations/Gain', [ruta '/limite negativo'], ...
    'Gain', '-1', 'Position', [690 205 735 235]);
  add_block('simulink/Discontinuities/Saturation Dynamic', [ruta '/saturacion par'], ...
    'Position', [770 80 835 145]);
  add_block('simulink/Math Operations/Sum', [ruta '/mas perturbacion'], ...
    'Inputs', '++', 'Position', [870 90 895 135]);
  outport(ruta, 'tau', 1, [935 100 965 114]);
  add_line(ruta, 'theta_ref/1', 'error/1'); add_line(ruta, 'theta/1', 'error/2');
  add_line(ruta, 'error/1', 'Kp/1'); add_line(ruta, 'Kp/1', 'PD/1');
  add_line(ruta, 'dtheta/1', 'menos Kd/1'); add_line(ruta, 'menos Kd/1', 'PD/2');
  add_line(ruta, 'dtheta/1', 'velocidad absoluta/1');
  add_line(ruta, 'velocidad absoluta/1', 'fraccion velocidad/1');
  add_line(ruta, 'uno/1', 'margen velocidad/1'); add_line(ruta, 'fraccion velocidad/1', 'margen velocidad/2');
  add_line(ruta, 'margen velocidad/1', 'margen positivo/1'); add_line(ruta, 'margen positivo/1', 'limite motriz/1');
  add_line(ruta, 'PD/1', 'potencia mecanica/1'); add_line(ruta, 'dtheta/1', 'potencia mecanica/2');
  add_line(ruta, 'potencia mecanica/1', 'acompanha giro/1');
  add_line(ruta, 'limite motriz/1', 'seleccionar limite/1');
  add_line(ruta, 'acompanha giro/1', 'seleccionar limite/2');
  add_line(ruta, 'tau max/1', 'seleccionar limite/3');
  add_line(ruta, 'seleccionar limite/1', 'limite negativo/1');
  add_line(ruta, 'PD/1', 'saturacion par/1');
  add_line(ruta, 'seleccionar limite/1', 'saturacion par/2');
  add_line(ruta, 'limite negativo/1', 'saturacion par/3');
  add_line(ruta, 'saturacion par/1', 'mas perturbacion/1');
  add_line(ruta, 'tau_pert/1', 'mas perturbacion/2'); add_line(ruta, 'mas perturbacion/1', 'tau/1');
end

function crear_planta(ruta)
  add_block('simulink/Ports & Subsystems/Subsystem', ruta);
  limpiar_subsistema(ruta);
  inport(ruta, 'tau', 1, [20 45 50 59]);
  inport(ruta, 'N', 2, [20 90 50 104]);
  inport(ruta, 'caso', 3, [20 300 50 314]);
  add_block('simulink/Continuous/Integrator', [ruta '/integrador velocidad'], ...
    'InitialCondition', 'sim_pata.dtheta0', 'Position', [690 90 720 120]);
  add_block('simulink/Continuous/Integrator', [ruta '/integrador theta'], ...
    'InitialCondition', 'sim_pata.theta0', 'Position', [760 90 790 120]);
  add_line(ruta, 'integrador velocidad/1', 'integrador theta/1');

  campos = {'Ieq','dIeq','dV','wP','cCoM','dcCoM'};
  ys = [35 85 135 185 235 285];
  for i = 1:numel(campos)
    agregar_lut(ruta, campos{i}, ys(i));
    add_line(ruta, 'integrador theta/1', [campos{i} '/1'], 'autorouting', 'on');
    add_line(ruta, 'caso/1', [campos{i} '/2'], 'autorouting', 'on');
  end

  add_block('simulink/Math Operations/Product', [ruta '/dtheta cuadrado'], ...
    'Inputs', '**', 'Position', [250 500 280 530]);
  add_line(ruta, 'integrador velocidad/1', 'dtheta cuadrado/1', 'autorouting', 'on');
  add_line(ruta, 'integrador velocidad/1', 'dtheta cuadrado/2', 'autorouting', 'on');
  add_block('simulink/Math Operations/Product', [ruta '/termino inercial'], ...
    'Inputs', '**', 'Position', [400 500 430 530]);
  add_line(ruta, 'dIeq/1', 'termino inercial/1');
  add_line(ruta, 'dtheta cuadrado/1', 'termino inercial/2', 'autorouting', 'on');
  add_block('simulink/Math Operations/Gain', [ruta '/menos medio'], ...
    'Gain', '-0.5', 'Position', [500 500 545 530]);
  add_line(ruta, 'termino inercial/1', 'menos medio/1');
  add_block('simulink/Math Operations/Gain', [ruta '/amortiguamiento'], ...
    'Gain', '-par_pata.b', 'Position', [400 550 510 580]);
  add_line(ruta, 'integrador velocidad/1', 'amortiguamiento/1', 'autorouting', 'on');
  add_block('simulink/Math Operations/Product', [ruta '/trabajo normal'], ...
    'Inputs', '**', 'Position', [400 600 430 630]);
  add_line(ruta, 'N/1', 'trabajo normal/1', 'autorouting', 'on');
  add_line(ruta, 'wP/1', 'trabajo normal/2');
  add_block('simulink/Math Operations/Gain', [ruta '/menos gravedad'], ...
    'Gain', '-1', 'Position', [500 650 545 680]);
  add_line(ruta, 'dV/1', 'menos gravedad/1');
  crear_topes([ruta '/Topes']); set_param([ruta '/Topes'], 'Position', [350 700 500 770]);
  add_line(ruta, 'integrador theta/1', 'Topes/1', 'autorouting', 'on');
  add_line(ruta, 'integrador velocidad/1', 'Topes/2', 'autorouting', 'on');

  add_block('simulink/Math Operations/Sum', [ruta '/suma pares'], ...
    'Inputs', '++++++', 'Position', [650 530 675 680]);
  add_line(ruta, 'tau/1', 'suma pares/1', 'autorouting', 'on');
  add_line(ruta, 'Topes/1', 'suma pares/2');
  add_line(ruta, 'amortiguamiento/1', 'suma pares/3');
  add_line(ruta, 'trabajo normal/1', 'suma pares/4');
  add_line(ruta, 'menos medio/1', 'suma pares/5');
  add_line(ruta, 'menos gravedad/1', 'suma pares/6');
  add_block('simulink/Math Operations/Product', [ruta '/dividir por Ieq'], ...
    'Inputs', '*/', 'Position', [750 565 785 605]);
  add_line(ruta, 'suma pares/1', 'dividir por Ieq/1');
  add_line(ruta, 'Ieq/1', 'dividir por Ieq/2', 'autorouting', 'on');
  add_line(ruta, 'dividir por Ieq/1', 'integrador velocidad/1');

  add_block('simulink/Math Operations/Product', [ruta '/cCoM ddtheta'], ...
    'Inputs', '**', 'Position', [520 850 550 880]);
  add_line(ruta, 'cCoM/1', 'cCoM ddtheta/1');
  add_line(ruta, 'dividir por Ieq/1', 'cCoM ddtheta/2', 'autorouting', 'on');
  add_block('simulink/Math Operations/Product', [ruta '/dcCoM dtheta2'], ...
    'Inputs', '**', 'Position', [520 900 550 930]);
  add_line(ruta, 'dcCoM/1', 'dcCoM dtheta2/1');
  add_line(ruta, 'dtheta cuadrado/1', 'dcCoM dtheta2/2', 'autorouting', 'on');
  add_block('simulink/Sources/Constant', [ruta '/g'], 'Value', 'par_pata.g', ...
    'Position', [520 950 550 970]);
  add_block('simulink/Math Operations/Sum', [ruta '/aceleracion CoM'], ...
    'Inputs', '+++', 'Position', [620 870 645 940]);
  add_line(ruta, 'cCoM ddtheta/1', 'aceleracion CoM/1');
  add_line(ruta, 'dcCoM dtheta2/1', 'aceleracion CoM/2');
  add_line(ruta, 'g/1', 'aceleracion CoM/3');
  add_block('simulink/Math Operations/Gain', [ruta '/masa por pata'], ...
    'Gain', 'par_pata.masa_por_pata', 'Position', [700 885 785 925]);
  add_line(ruta, 'aceleracion CoM/1', 'masa por pata/1');
  add_block('simulink/Logic and Bit Operations/Compare To Zero', [ruta '/N positiva'], ...
    'relop', '>', 'Position', [830 890 900 920]);
  add_line(ruta, 'masa por pata/1', 'N positiva/1');
  add_block('simulink/Logic and Bit Operations/Compare To Constant', [ruta '/caso parado'], ...
    'const', '2', 'relop', '==', 'Position', [700 960 785 990]);
  add_line(ruta, 'caso/1', 'caso parado/1', 'autorouting', 'on');
  add_block('simulink/Logic and Bit Operations/Logical Operator', [ruta '/contacto valido'], ...
    'Operator', 'AND', 'Inputs', '2', 'Position', [940 915 975 955]);
  add_block('simulink/Sources/Constant', [ruta '/normal no aplicable'], ...
    'Value', 'NaN', 'Position', [830 970 880 990]);
  add_block('simulink/Signal Routing/Switch', [ruta '/normal solo parado'], ...
    'Criteria', 'u2 ~= 0', 'Position', [940 970 990 1030]);
  add_line(ruta, 'N positiva/1', 'contacto valido/1');
  add_line(ruta, 'caso parado/1', 'contacto valido/2');
  add_line(ruta, 'masa por pata/1', 'normal solo parado/1', 'autorouting', 'on');
  add_line(ruta, 'caso parado/1', 'normal solo parado/2', 'autorouting', 'on');
  add_line(ruta, 'normal no aplicable/1', 'normal solo parado/3');

  outport(ruta, 'theta', 1, [1200 1020 1230 1034]);
  outport(ruta, 'dtheta', 2, [1200 1060 1230 1074]);
  outport(ruta, 'ddtheta', 3, [1200 1100 1230 1114]);
  outport(ruta, 'Ieq out', 4, [1200 1140 1230 1154]);
  outport(ruta, 'Vprima', 5, [1200 1180 1230 1194]);
  outport(ruta, 'normal estimada', 6, [1200 1220 1230 1234]);
  outport(ruta, 'contacto valido out', 7, [1200 1260 1230 1274]);
  outport(ruta, 'tau tope', 8, [1200 1300 1230 1314]);
  outport(ruta, 'caso out', 9, [1200 1340 1230 1354]);
  add_line(ruta, 'integrador theta/1', 'theta/1', 'autorouting', 'on');
  add_line(ruta, 'integrador velocidad/1', 'dtheta/1', 'autorouting', 'on');
  add_line(ruta, 'dividir por Ieq/1', 'ddtheta/1', 'autorouting', 'on');
  add_line(ruta, 'Ieq/1', 'Ieq out/1', 'autorouting', 'on');
  add_line(ruta, 'dV/1', 'Vprima/1', 'autorouting', 'on');
  add_line(ruta, 'normal solo parado/1', 'normal estimada/1', 'autorouting', 'on');
  add_line(ruta, 'contacto valido/1', 'contacto valido out/1');
  add_line(ruta, 'Topes/1', 'tau tope/1', 'autorouting', 'on');
  add_line(ruta, 'caso/1', 'caso out/1', 'autorouting', 'on');
end

function agregar_lut(ruta, campo, y)
  add_block('simulink/Lookup Tables/n-D Lookup Table', [ruta '/' campo], ...
    'NumberOfTableDimensions', '2', ...
    'BreakpointsForDimension1', 'par_pata.theta', ...
    'BreakpointsForDimension2', 'par_pata.casos', ...
    'Table', ['par_pata.' campo], 'InterpMethod', 'Linear point-slope', ...
    'ExtrapMethod', 'Clip', 'Position', [150 y 225 y+40]);
end

function crear_topes(ruta)
  add_block('simulink/Ports & Subsystems/Subsystem', ruta);
  limpiar_subsistema(ruta);
  inport(ruta, 'theta', 1, [20 35 50 49]); inport(ruta, 'dtheta', 2, [20 125 50 139]);
  add_block('simulink/Sources/Constant', [ruta '/theta min'], 'Value', 'par_pata.theta_min', 'Position', [20 75 70 95]);
  add_block('simulink/Sources/Constant', [ruta '/theta max'], 'Value', 'par_pata.theta_max', 'Position', [20 175 70 195]);
  add_block('simulink/Math Operations/Sum', [ruta '/penetracion baja'], 'Inputs', '+-', 'Position', [105 55 130 90]);
  add_block('simulink/Math Operations/Sum', [ruta '/penetracion alta'], 'Inputs', '+-', 'Position', [105 165 130 200]);
  add_block('simulink/Discontinuities/Saturation', [ruta '/solo baja'], 'LowerLimit', '0', 'UpperLimit', 'inf', 'Position', [155 55 205 90]);
  add_block('simulink/Discontinuities/Saturation', [ruta '/solo alta'], 'LowerLimit', '0', 'UpperLimit', 'inf', 'Position', [155 165 205 200]);
  add_block('simulink/Discontinuities/Saturation', [ruta '/vel baja'], 'LowerLimit', '-inf', 'UpperLimit', '0', 'Position', [155 105 205 135]);
  add_block('simulink/Discontinuities/Saturation', [ruta '/vel alta'], 'LowerLimit', '0', 'UpperLimit', 'inf', 'Position', [155 215 205 245]);
  add_block('simulink/Math Operations/Gain', [ruta '/k baja'], 'Gain', 'par_pata.k_tope', 'Position', [235 55 295 85]);
  add_block('simulink/Math Operations/Gain', [ruta '/c baja'], 'Gain', '-par_pata.c_tope', 'Position', [235 105 295 135]);
  add_block('simulink/Math Operations/Gain', [ruta '/k alta'], 'Gain', '-par_pata.k_tope', 'Position', [235 165 295 195]);
  add_block('simulink/Math Operations/Gain', [ruta '/c alta'], 'Gain', '-par_pata.c_tope', 'Position', [235 215 295 245]);
  add_block('simulink/Logic and Bit Operations/Compare To Zero', [ruta '/bajo activo'], ...
    'relop', '>', 'Position', [225 25 295 50]);
  add_block('simulink/Logic and Bit Operations/Compare To Zero', [ruta '/alto activo'], ...
    'relop', '>', 'Position', [225 260 295 285]);
  add_block('simulink/Math Operations/Product', [ruta '/vel baja activa'], ...
    'Inputs', '**', 'Position', [315 90 345 120]);
  add_block('simulink/Math Operations/Product', [ruta '/vel alta activa'], ...
    'Inputs', '**', 'Position', [315 220 345 250]);
  add_block('simulink/Math Operations/Sum', [ruta '/suma'], 'Inputs', '++++', 'Position', [335 105 360 195]);
  outport(ruta, 'tau_tope', 1, [405 143 435 157]);
  add_line(ruta, 'theta min/1', 'penetracion baja/1'); add_line(ruta, 'theta/1', 'penetracion baja/2');
  add_line(ruta, 'theta/1', 'penetracion alta/1'); add_line(ruta, 'theta max/1', 'penetracion alta/2');
  add_line(ruta, 'penetracion baja/1', 'solo baja/1'); add_line(ruta, 'penetracion alta/1', 'solo alta/1');
  add_line(ruta, 'dtheta/1', 'vel baja/1'); add_line(ruta, 'dtheta/1', 'vel alta/1');
  add_line(ruta, 'solo baja/1', 'k baja/1'); add_line(ruta, 'solo baja/1', 'bajo activo/1');
  add_line(ruta, 'solo alta/1', 'k alta/1'); add_line(ruta, 'solo alta/1', 'alto activo/1');
  add_line(ruta, 'vel baja/1', 'vel baja activa/1'); add_line(ruta, 'bajo activo/1', 'vel baja activa/2');
  add_line(ruta, 'vel alta/1', 'vel alta activa/1'); add_line(ruta, 'alto activo/1', 'vel alta activa/2');
  add_line(ruta, 'vel baja activa/1', 'c baja/1'); add_line(ruta, 'vel alta activa/1', 'c alta/1');
  add_line(ruta, 'k baja/1', 'suma/1'); add_line(ruta, 'c baja/1', 'suma/2');
  add_line(ruta, 'k alta/1', 'suma/3'); add_line(ruta, 'c alta/1', 'suma/4'); add_line(ruta, 'suma/1', 'tau_tope/1');
end

function limpiar_subsistema(ruta)
  lineas = find_system(ruta, 'FindAll', 'on', 'SearchDepth', 1, 'Type', 'line');
  for i = 1:numel(lineas), delete_line(lineas(i)); end
  bloques = find_system(ruta, 'SearchDepth', 1, 'Type', 'Block');
  for i = 2:numel(bloques), delete_block(bloques{i}); end
end

function inport(ruta, nombre, puerto, posicion)
  add_block('simulink/Ports & Subsystems/In1', [ruta '/' nombre], ...
    'Port', num2str(puerto), 'Position', posicion);
end

function outport(ruta, nombre, puerto, posicion)
  add_block('simulink/Ports & Subsystems/Out1', [ruta '/' nombre], ...
    'Port', num2str(puerto), 'Position', posicion);
end
