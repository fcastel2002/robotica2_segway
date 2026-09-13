function u = bloques_util()
%BLOQUES_UTIL  Atajos para armar modelos Simulink por codigo con bloques nativos.
%   u = bloques_util();  u.gain(sys, 'nombre', 'par.cuerpo.masa');  u.L(sys, 'a/1', 'b/2', 'senal')
%   Cada campo agrega un bloque llamado sys/nombre y devuelve su ruta. La posicion no importa: al final
%   construir_robot_bloques ordena cada subsistema con Simulink.BlockDiagram.arrangeSystem.
%   Numeracion de puertos que conviene recordar:
%     Switch: 1 = si la condicion es cierta, 2 = control, 3 = si no
%     Saturation Dynamic: 1 = limite superior, 2 = senal, 3 = limite inferior
%     Product '*/': 1 = numerador, 2 = denominador     atan2: 1 = y, 2 = x
  u.ab      = @(src, sys, nom, varargin) agregar(src, sys, nom, varargin{:});
  u.in      = @(sys, nom) agregar('simulink/Sources/In1', sys, nom);
  u.out     = @(sys, nom) agregar('simulink/Sinks/Out1', sys, nom);
  u.const   = @(sys, nom, v) agregar('simulink/Sources/Constant', sys, nom, 'Value', v);
  u.gain    = @(sys, nom, k) agregar('simulink/Math Operations/Gain', sys, nom, 'Gain', k);
  u.sum     = @(sys, nom, s) agregar('simulink/Math Operations/Sum', sys, nom, 'Inputs', s, 'IconShape', 'rectangular');
  u.prod    = @(sys, nom, s) agregar('simulink/Math Operations/Product', sys, nom, 'Inputs', s);
  u.mprod   = @(sys, nom, s) agregar('simulink/Math Operations/Product', sys, nom, 'Inputs', s, 'Multiplication', 'Matrix(*)');
  u.div     = @(sys, nom) agregar('simulink/Math Operations/Divide', sys, nom, 'Inputs', '*/');
  u.integ   = @(sys, nom, ic) agregar('simulink/Continuous/Integrator', sys, nom, 'InitialCondition', ic);
  u.trig    = @(sys, nom, op) agregar('simulink/Math Operations/Trigonometric Function', sys, nom, 'Operator', op);
  u.mathf   = @(sys, nom, op) agregar('simulink/Math Operations/Math Function', sys, nom, 'Operator', op);
  u.sqrt    = @(sys, nom) agregar('simulink/Math Operations/Sqrt', sys, nom, 'Operator', 'sqrt');
  u.abs     = @(sys, nom) agregar('simulink/Math Operations/Abs', sys, nom);
  u.neg     = @(sys, nom) agregar('simulink/Math Operations/Unary Minus', sys, nom);
  u.lut     = @(sys, nom, bp, tab) agregar('simulink/Lookup Tables/1-D Lookup Table', sys, nom, ...
                'BreakpointsForDimension1', bp, 'Table', tab, 'InterpMethod', 'Linear point-slope', 'ExtrapMethod', 'Linear');
  u.sat     = @(sys, nom, lo, hi) agregar('simulink/Discontinuities/Saturation', sys, nom, 'LowerLimit', lo, 'UpperLimit', hi);
  u.satdin  = @(sys, nom) agregar('simulink/Discontinuities/Saturation Dynamic', sys, nom);
  u.deadzone= @(sys, nom, lo, hi) agregar('simulink/Discontinuities/Dead Zone', sys, nom, 'LowerValue', lo, 'UpperValue', hi);
  u.ratelim = @(sys, nom, r, ic) agregar('simulink/Discontinuities/Rate Limiter', sys, nom, ...
                'RisingSlewLimit', r, 'FallingSlewLimit', ['-(' r ')'], 'InitialCondition', ic);
  u.minmax  = @(sys, nom, f, n) agregar('simulink/Math Operations/MinMax', sys, nom, 'Function', f, 'Inputs', n);
  u.sw      = @(sys, nom, crit, umb) agregar('simulink/Signal Routing/Switch', sys, nom, 'Criteria', crit, 'Threshold', umb);
  u.cmp0    = @(sys, nom, op) agregar('simulink/Logic and Bit Operations/Compare To Zero', sys, nom, 'relop', op);
  u.cmpc    = @(sys, nom, op, c) agregar('simulink/Logic and Bit Operations/Compare To Constant', sys, nom, 'relop', op, 'const', c);
  u.rel     = @(sys, nom, op) agregar('simulink/Logic and Bit Operations/Relational Operator', sys, nom, 'Operator', op);
  u.logic   = @(sys, nom, op, n) agregar('simulink/Logic and Bit Operations/Logical Operator', sys, nom, 'Operator', op, 'Inputs', n);
  u.dtc     = @(sys, nom) agregar('simulink/Signal Attributes/Data Type Conversion', sys, nom, 'OutDataTypeStr', 'double');
  u.round   = @(sys, nom, op) agregar('simulink/Math Operations/Rounding Function', sys, nom, 'Operator', op);
  u.dot     = @(sys, nom) agregar('simulink/Math Operations/Dot Product', sys, nom);
  u.sumel   = @(sys, nom) agregar('simulink/Math Operations/Sum of Elements', sys, nom);
  u.reshape = @(sys, nom, dims) agregar('simulink/Math Operations/Reshape', sys, nom, 'OutputDimensionality', 'Customize', 'OutputDimensions', dims);
  u.mux     = @(sys, nom, n) agregar('simulink/Signal Routing/Mux', sys, nom, 'Inputs', n);
  u.demux   = @(sys, nom, n) agregar('simulink/Signal Routing/Demux', sys, nom, 'Outputs', n);
  u.busc    = @(sys, nom, n) agregar('simulink/Signal Routing/Bus Creator', sys, nom, 'Inputs', n);
  u.buss    = @(sys, nom, s) agregar('simulink/Signal Routing/Bus Selector', sys, nom, 'OutputSignals', s);
  u.term    = @(sys, nom) agregar('simulink/Sinks/Terminator', sys, nom);
  u.zoh     = @(sys, nom) agregar('simulink/Discrete/Zero-Order Hold', sys, nom, 'SampleTime', 'Ts');
  u.ud      = @(sys, nom, ic) agregar('simulink/Discrete/Unit Delay', sys, nom, 'InitialCondition', ic, 'SampleTime', 'Ts');
  u.dtf     = @(sys, nom, num, den) agregar('simulink/Discrete/Discrete Transfer Fcn', sys, nom, 'Numerator', num, 'Denominator', den, 'SampleTime', 'Ts');
  u.rand    = @(sys, nom, seed) agregar('simulink/Sources/Random Number', sys, nom, 'Mean', '0', 'Variance', '1', 'Seed', seed, 'SampleTime', 'Ts');
  u.scope   = @(sys, nom) agregar('simulink/Sinks/Scope', sys, nom);
  u.sub     = @(sys, nom) subsistema(sys, nom);
  u.L       = @(sys, a, b, nom) unir(sys, a, b, nom);
  u.nota    = @(sys, txt) nota(sys, txt);
  u.pos     = @(sys, tabla) posiciones(sys, tabla);
end

function posiciones(sys, tabla)
% Distribucion a mano: tabla = {nombre, [izq arriba der abajo]; ...}. Despues re-enruta las lineas.
  for k = 1:size(tabla, 1), set_param([sys '/' tabla{k, 1}], 'Position', tabla{k, 2}); end
  h = find_system(sys, 'SearchDepth', 1, 'FindAll', 'on', 'Type', 'line');
  if ~isempty(h), Simulink.BlockDiagram.routeLine(h); end
end

function p = agregar(src, sys, nom, varargin)
  p = [sys '/' nom];
  add_block(src, p, varargin{:});
end

function p = subsistema(sys, nom)
% Subsistema vacio (sin el In1/Out1 que trae por defecto).
  p = [sys '/' nom];
  add_block('simulink/Ports & Subsystems/Subsystem', p);
  delete_line(p, 'In1/1', 'Out1/1'); delete_block([p '/In1']); delete_block([p '/Out1']);
end

function h = unir(sys, a, b, nom)
  h = add_line(sys, a, b, 'autorouting', 'on');
  if nargin >= 4 && ~isempty(nom), set_param(h, 'Name', nom); end
end

function a = nota(sys, txt)
% Nota de texto arriba a la izquierda de los bloques del subsistema (llamar despues de ordenarlo).
  bl = find_system(sys, 'SearchDepth', 1, 'Type', 'block');
  x0 = 1e9; y0 = 1e9;
  for k = 1:numel(bl)
    if strcmp(bl{k}, sys), continue; end
    p = get_param(bl{k}, 'Position'); x0 = min(x0, p(1)); y0 = min(y0, p(2));
  end
  if x0 == 1e9, x0 = 20; y0 = 60; end
  a = Simulink.Annotation(sys, txt);
  a.Position = [x0, y0 - 45];
  a.FontSize = 11; a.FontWeight = 'bold';
end
