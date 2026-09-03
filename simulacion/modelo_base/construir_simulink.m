function mdl = construir_simulink(P, C, nombre)
%CONSTRUIR_SIMULINK  Arma el modelo de Simulink por codigo y lo deja abierto.
%
%   mdl = construir_simulink(P, C)
%   mdl = construir_simulink(P, C, 'segway_pata')
%
%   El modelo queda FINO a proposito: toda la fisica vive en dinamica_sl.m y
%   toda la ley de control en control_sl.m. Los bloques de Simulink solo los
%   llaman. Si cambias las ecuaciones, cambias el .m y el modelo se entera solo.
%
%   Diagrama:
%
%     [x_ref]--\
%               >[Mux]--> ref --> [Controlador] --u--> [Planta] --qdd--> [1/s] --qd--> [1/s] --q
%     [l_ref]--/                       ^                                   |             |
%                                      |                                   |             |
%                                      +---------------- X <--[Mux]--------+-------------+
%
%   Variables que deja en el workspace base: pv, q0, qd0, x_ref, l_ref, Ts_fin

  if nargin < 3 || isempty(nombre), nombre = 'segway_pata'; end
  mdl = nombre;

  % --- parametros al workspace base ---
  pv  = empaquetar(P, C);
  q0  = [0; 0; P.din.l0];
  qd0 = [0; 0; 0];
  assignin('base','pv',pv);       assignin('base','q0',q0);
  assignin('base','qd0',qd0);     assignin('base','x_ref',0);
  assignin('base','l_ref',P.din.l0);  assignin('base','Ts_fin',6);
  assignin('base','P',P);         assignin('base','C',C);

  % --- crear el modelo de cero ---
  if bdIsLoaded(mdl), close_system(mdl, 0); end
  new_system(mdl);
  open_system(mdl);

  ab = @(src, nom, pos, varargin) add_block(src, [mdl '/' nom], ...
        'Position', pos, varargin{:});

  ab('simulink/Sources/Constant',        'x_ref', [30  60 90  90],  'Value','x_ref');
  ab('simulink/Sources/Constant',        'l_ref', [30 120 90 150],  'Value','l_ref');
  ab('simulink/Signal Routing/Mux',      'ref',   [120 65 125 145], 'Inputs','2');
  ab('simulink/Sources/Constant',        'pv',    [30 320 90 350],  'Value','pv');

  ab('simulink/User-Defined Functions/MATLAB Function', 'Controlador', [180  60 280 150]);
  ab('simulink/User-Defined Functions/MATLAB Function', 'Planta',      [340  60 450 170]);

  ab('simulink/Continuous/Integrator',   'int_qd', [500  75 530 105], ...
     'InitialCondition','qd0');
  ab('simulink/Continuous/Integrator',   'int_q',  [570  75 600 105], ...
     'InitialCondition','q0');
  ab('simulink/Signal Routing/Mux',      'X',      [650  70 655 150], 'Inputs','2');

  ab('simulink/Sinks/Scope',             'Estados', [720  60 760  90]);
  ab('simulink/Sinks/Scope',             'Pares',   [720 130 760 160]);
  ab('simulink/Sinks/Scope',             'Diag',    [720 200 760 230]);
  ab('simulink/Sinks/To Workspace',      'Xout',    [720 260 780 290], ...
     'VariableName','Xout','SaveFormat','Structure With Time');
  ab('simulink/Sinks/To Workspace',      'Uout',    [720 310 780 340], ...
     'VariableName','Uout','SaveFormat','Structure With Time');
  ab('simulink/Signal Routing/Mux',      'diag',    [660 195 665 265], 'Inputs','3');

  % --- codigo de los bloques MATLAB Function ---
  poner_codigo([mdl '/Controlador'], [ ...
    'function u = fcn(X, ref, pv)\n' ...
    '%#codegen\n' ...
    'u = control_sl(X, ref, pv);\n']);

  poner_codigo([mdl '/Planta'], [ ...
    'function [qdd, N, roce, desliza, theta] = fcn(X, u, pv)\n' ...
    '%#codegen\n' ...
    'q  = X(1:3);\n' ...
    'qd = X(4:6);\n' ...
    '[qdd, N, roce, desliza, theta] = dinamica_sl(q, qd, u, pv);\n']);

  % --- conexiones ---
  L = @(a,b) add_line(mdl, a, b, 'autorouting','on');
  L('x_ref/1','ref/1');           L('l_ref/1','ref/2');
  L('ref/1','Controlador/2');     L('pv/1','Controlador/3');
  L('pv/1','Planta/3');
  L('Controlador/1','Planta/2');
  L('Planta/1','int_qd/1');
  L('int_qd/1','int_q/1');
  L('int_q/1','X/2');             L('int_qd/1','X/1');
  L('X/1','Controlador/1');       L('X/1','Planta/1');
  L('X/1','Estados/1');           L('X/1','Xout/1');
  L('Controlador/1','Pares/1');   L('Controlador/1','Uout/1');
  L('Planta/2','diag/1');  L('Planta/3','diag/2');  L('Planta/4','diag/3');
  L('diag/1','Diag/1');

  % --- ajustes de simulacion ---
  set_param(mdl, 'Solver','ode45', 'StopTime','Ts_fin', ...
                 'RelTol','1e-6', 'AbsTol','1e-8', 'MaxStep','0.005');
  set_param(mdl, 'SignalLoggingName','logsout', 'SignalLogging','on');

  Simulink.BlockDiagram.arrangeSystem(mdl);
  save_system(mdl);
  fprintf('\nModelo "%s.slx" creado y guardado.\n', mdl);
  fprintf('Para correrlo:  sim(''%s'')\n', mdl);
  fprintf('Para cambiar la consigna, edita x_ref y l_ref en el workspace.\n\n');
end

% -------------------------------------------------------------------------
function poner_codigo(ruta, txt)
%PONER_CODIGO  Escribe el cuerpo de un bloque MATLAB Function.
  txt = sprintf(strrep(txt, '%', '%%'));
  try
    S = sfroot;
    blk = S.find('-isa','Stateflow.EMChart','Path',ruta);
    blk.Script = txt;
  catch err
    warning('construir_simulink:codigo', ...
      ['No se pudo escribir el codigo del bloque %s automaticamente (%s).\n' ...
       'Abri el bloque y pega esto:\n\n%s'], ruta, err.message, txt);
  end
end
