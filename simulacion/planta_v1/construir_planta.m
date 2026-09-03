function mdl = construir_planta(P, C, E, nombre)
%CONSTRUIR_PLANTA  Arma planta_segway_v1.slx por codigo y lo guarda junto a este archivo.
%   mdl = construir_planta(P, C, E)
%   Diagrama:  ref --ZOH--> [Controlador] --u--> [Planta] --Xdot--> 1/s --X--+--> Xout
%                                ^                  ^  pert            |
%                                |                  |                  v
%                             [Delay] <-- [Sensores] <-- ZOH <---------+ (X, y)
%   Toda la fisica esta en planta_sl.m, las medidas en sensores_sl.m y la ley en control_v1.m.
  if nargin < 4 || isempty(nombre), nombre = 'planta_segway_v1'; end
  mdl = nombre;
  cargar_workspace_v1(P, C, E);
  if bdIsLoaded(mdl), close_system(mdl, 0); end
  archivo = fullfile(fileparts(mfilename('fullpath')), [mdl '.slx']);
  if isfile(archivo), delete(archivo); end          % evita el aviso de nombre duplicado al recrearlo
  new_system(mdl); open_system(mdl);
  ab = @(src, nom, pos, varargin) add_block(src, [mdl '/' nom], 'Position', pos, varargin{:});

  ab('simulink/Sources/From Workspace', 'ref',   [30 40 110 70],   'VariableName','ref_ts',  'SampleTime','Ts', 'Interpolate','off', 'OutputAfterFinalValue','Holding final value');
  ab('simulink/Discrete/Zero-Order Hold', 'zoh_ref', [140 40 170 70], 'SampleTime','Ts');
  ab('simulink/Sources/Constant', 'reset',        [30 110 110 140], 'Value','0', 'SampleTime','Ts');
  ab('simulink/Sources/From Workspace', 'pert',  [30 200 110 230],  'VariableName','pert_ts', 'SampleTime','0',  'Interpolate','off', 'OutputAfterFinalValue','Holding final value');
  ab('simulink/Sources/Constant', 'pv',           [30 300 110 330], 'Value','pv');

  ab('simulink/User-Defined Functions/MATLAB Function', 'Controlador', [200 40 320 150]);
  ab('simulink/User-Defined Functions/MATLAB Function', 'Planta',      [420 160 540 280]);
  ab('simulink/Continuous/Integrator', 'int_X',   [600 200 630 230], 'InitialCondition','X0');
  ab('simulink/Discrete/Zero-Order Hold', 'zoh_X', [300 340 340 370], 'SampleTime','Ts');
  ab('simulink/Discrete/Zero-Order Hold', 'zoh_y', [300 390 340 420], 'SampleTime','Ts');
  ab('simulink/Sources/Random Number', 'ruido',    [300 440 340 470], 'Mean','0', 'Variance','1', 'Seed','semilla+[0 1 2]', 'SampleTime','Ts');
  ab('simulink/User-Defined Functions/MATLAB Function', 'Sensores',    [420 340 540 470]);
  ab('simulink/Discrete/Delay', 'retardo',         [600 390 640 420], 'DelayLength','n_delay', 'InitialCondition','meas0', 'SampleTime','Ts');

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
