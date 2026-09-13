function mdl = construir_robot_bloques(P, C, E)
%CONSTRUIR_ROBOT_BLOQUES  Arma robot_segway_bloques.slx: el mismo robot que robot_segway.slx pero
%   SOLO con bloques nativos de Simulink (sin MATLAB Function), para ver cada ecuacion como diagrama.
%   mdl = construir_robot_bloques(P, C, E)
%
%   Nivel superior:   Escenario --> Controlador --> Robot --> Sensores --> (vuelve al Controlador)
%                     Registro (To Workspace)   Graficos (scopes)
%   Robot:        Bateria, Motores y reductores, Ruedas, Piso con escalones, Contacto rueda-piso,
%                 Servo y pata, Cuerpo (Lagrange: M, C, G, Q), IMU. Cada parte publica un bus.
%   Controlador:  Odometria, Inclinacion (filtro complementario), LQR programado, Par a tension,
%                 Consigna del servo.
%   Los bloques leen 'par' (parametros_simulink) y las condiciones iniciales de cargar_workspace.
%   Diseno: docs/superpowers/specs/2026-09-03-simulink-bloques-design.md
  mdl = 'robot_segway_bloques'; aqui = fileparts(mfilename('fullpath'));
  cargar_workspace(P, C, E);
  if bdIsLoaded(mdl), close_system(mdl, 0); end
  archivo = fullfile(aqui, [mdl '.slx']); if isfile(archivo), delete(archivo); end
  new_system(mdl); open_system(mdl);
  u = bloques_util();

  pos = {'Escenario', [40 120 150 200]; 'Controlador', [240 110 370 210]; 'Robot', [470 100 600 220]; ...
         'Sensores', [470 300 600 380]; 'Registro', [720 90 850 250]; 'Graficos', [720 300 850 400]};
  for k = 1:size(pos, 1), u.sub(mdl, pos{k, 1}); set_param([mdl '/' pos{k, 1}], 'Position', pos{k, 2}); end

  escenario(mdl, u); bloques_controlador(mdl, u); bloques_robot(mdl, u); bloques_sensores(mdl, u);
  registro(mdl, u); graficos(mdl, u);

  % ---------- conexiones del nivel superior ----------
  u.L(mdl, 'Escenario/1', 'Controlador/2', 'referencias'); u.L(mdl, 'Escenario/2', 'Robot/2', 'perturbaciones');
  u.L(mdl, 'Controlador/1', 'Robot/1', 'comandos'); u.L(mdl, 'Robot/1', 'Sensores/1', 'estados'); u.L(mdl, 'Robot/2', 'Sensores/2', 'salidas');
  u.L(mdl, 'Sensores/1', 'Controlador/1', 'medidas');
  u.L(mdl, 'Robot/1', 'Registro/1', ''); u.L(mdl, 'Robot/2', 'Registro/2', ''); u.L(mdl, 'Controlador/1', 'Registro/3', '');
  u.L(mdl, 'Controlador/2', 'Registro/4', 'estimaciones'); u.L(mdl, 'Sensores/1', 'Registro/5', '');
  u.L(mdl, 'Robot/1', 'Graficos/1', ''); u.L(mdl, 'Robot/2', 'Graficos/2', ''); u.L(mdl, 'Controlador/2', 'Graficos/3', '');
  u.L(mdl, 'Controlador/1', 'Graficos/4', ''); u.L(mdl, 'Escenario/1', 'Graficos/5', '');

  % ---------- solver ----------
  set_param(mdl, 'Solver', 'ode15s', 'RelTol', '1e-5', 'AbsTol', '1e-7', 'MaxStep', '1e-3', 'StopTime', 'tiempo_final', 'ReturnWorkspaceOutputs', 'on');

  % ---------- orden automatico de cada subsistema (de adentro hacia afuera) y notas ----------
  subs = find_system(mdl, 'BlockType', 'SubSystem');
  subs = subs(cellfun(@(b) isempty(get_param(b, 'ReferenceBlock')), subs));   % sin los enmascarados de libreria
  a_mano = {[mdl '/Robot'], [mdl '/Robot/Cuerpo (Lagrange)'], [mdl '/Robot/Servo y pata'], [mdl '/Controlador']};   % estos ya tienen distribucion fija
  subs = subs(~ismember(subs, a_mano));
  prof = cellfun(@(x) sum(x == '/'), subs); [~, o] = sort(prof, 'descend');
  for k = o', Simulink.BlockDiagram.arrangeSystem(subs{k}); end
  notas(mdl, u);
  save_system(mdl, archivo);
  fprintf('Modelo %s.slx creado en %s (solo bloques nativos)\n', mdl, aqui);
end

function escenario(mdl, u)
  s = [mdl '/Escenario'];
  u.ab('simulink/Sources/From Workspace', s, 'referencias (x_ref, l_ref)', 'VariableName', 'referencias_ts', 'SampleTime', 'Ts', 'Interpolate', 'off', 'OutputAfterFinalValue', 'Holding final value');
  u.ab('simulink/Sources/From Workspace', s, 'perturbaciones (F_x, M_p, pendiente, mu, F_escalon)', 'VariableName', 'perturbaciones_ts', 'SampleTime', '0', 'Interpolate', 'off', 'OutputAfterFinalValue', 'Holding final value');
  u.out(s, 'referencias'); u.out(s, 'perturbaciones');
  u.L(s, 'referencias (x_ref, l_ref)/1', 'referencias/1', 'referencias');
  u.L(s, 'perturbaciones (F_x, M_p, pendiente, mu, F_escalon)/1', 'perturbaciones/1', 'perturbaciones');
end

function registro(mdl, u)
  s = [mdl '/Registro'];
  v = {'estados', 'salidas', 'comandos', 'estimaciones', 'medidas'};
  for k = 1:numel(v)
    u.in(s, v{k});
    u.ab('simulink/Sinks/To Workspace', s, ['a workspace: ' v{k}], 'VariableName', v{k}, 'SaveFormat', 'Timeseries');
    u.L(s, [v{k} '/1'], ['a workspace: ' v{k} '/1'], '');
  end
end

function graficos(mdl, u)
  s = [mdl '/Graficos'];
  u.in(s, 'estados'); u.in(s, 'salidas'); u.in(s, 'estimaciones'); u.in(s, 'comandos'); u.in(s, 'referencias');
  u.buss(s, 'del robot', 'inclinacion,y_eje,largo_pata,x'); u.buss(s, 'fuerzas', 'normal,par_servo');
  u.demux(s, 'separar estimaciones', '7'); u.demux(s, 'separar referencias', '2');
  u.L(s, 'estados/1', 'del robot/1', ''); u.L(s, 'salidas/1', 'fuerzas/1', ''); u.L(s, 'estimaciones/1', 'separar estimaciones/1', ''); u.L(s, 'referencias/1', 'separar referencias/1', '');
  u.mux(s, 'inclinacion real y estimada', '2'); u.mux(s, 'altura del eje y largo de pata', '2'); u.mux(s, 'posicion real y consigna', '2');
  u.scope(s, 'Inclinacion'); u.scope(s, 'Altura y pata'); u.scope(s, 'Tensiones de motor'); u.scope(s, 'Posicion'); u.scope(s, 'Normal'); u.scope(s, 'Par de servo');
  u.L(s, 'del robot/1', 'inclinacion real y estimada/1', ''); u.L(s, 'separar estimaciones/1', 'inclinacion real y estimada/2', 'inclinacion_est');
  u.L(s, 'del robot/2', 'altura del eje y largo de pata/1', ''); u.L(s, 'del robot/3', 'altura del eje y largo de pata/2', '');
  u.L(s, 'del robot/4', 'posicion real y consigna/1', ''); u.L(s, 'separar referencias/1', 'posicion real y consigna/2', 'x_ref');
  u.L(s, 'inclinacion real y estimada/1', 'Inclinacion/1', ''); u.L(s, 'altura del eje y largo de pata/1', 'Altura y pata/1', '');
  u.L(s, 'comandos/1', 'Tensiones de motor/1', ''); u.L(s, 'posicion real y consigna/1', 'Posicion/1', '');
  u.L(s, 'fuerzas/1', 'Normal/1', ''); u.L(s, 'fuerzas/2', 'Par de servo/1', '');
  for k = 2:7, u.term(s, sprintf('sin uso %d', k)); u.L(s, sprintf('separar estimaciones/%d', k), sprintf('sin uso %d/1', k), ''); end
  u.term(s, 'sin uso l_ref'); u.L(s, 'separar referencias/2', 'sin uso l_ref/1', '');
end

function notas(mdl, u)
% Una nota por subsistema con la ecuacion que implementa y la seccion del manual.
  R = [mdl '/Robot']; CU = [R '/Cuerpo (Lagrange)']; SP = [R '/Servo y pata']; IM = [R '/IMU (fuerza especifica)']; CO = [mdl '/Controlador'];
  N = { ...
    mdl, 'SEGWAY CON PATAS - modelo solo con bloques nativos. Escenario -> Controlador -> Robot -> Sensores. Parametros: par (parametros_editables.m). Manual: docs/manual_modelo_segway.pdf';
    R, 'PLANTA: cada parte publica un bus con su nombre y los demas eligen lo que usan (Bus Selector). Estados y salidas en el mismo orden que robot_planta.m';
    [R '/Bateria y puente H'], 'V_bus = max(V_bat - R_bat (|i_izq| + |i_der|), 0) ;  V aplicada = sat(V pedida, -V_bus .. V_bus)';
    [R '/Motores y reductores'], 'Motor DC + reductor rigido (manual sec. 6): L di/dt = V - R i - Ke N w_rueda ;  par_reductor = N (Kt i - tau_c tanh(w/0.5) - b w)';
    [R '/Ruedas'], '(J_rueda + N^2 J_rotor) dw/dt = par_reductor + par_contacto - b_w w   (manual sec. 6: inercia reflejada del rotor)';
    [R '/Piso con escalones'], 'Punto mas cercano del piso al centro de la rueda, sobre todos los tramos (descansos y contrahuellas) a la vez ; penetracion = R - d_min ; normal = (c - p)/d_min   (manual sec. 7)';
    [R '/Contacto rueda-piso'], 'Por rueda: N = max(0, k delta + c d_delta) solo si delta > 0 ;  f = mu N tanh(v_s/v0) - c_v v_s ;  fuerza sobre el eje = 2 N n + (f_izq + f_der) t ;  par = -R f   (manual sec. 7)';
    SP, 'Servo PD sobre theta(l) con limite par-velocidad, F_l = n_servos tau dtheta/dl ; topes de carrera ; flexor opcional en serie (l_mec)   (manual sec. 5 y 8)';
    CU, 'M(q) q'''' = Q - C(q,q'') q'' - G(q),   q = [x, y_eje, inclinacion, largo_pata]   (manual sec. 4, deduccion de Lagrange fila por fila)';
    [CU '/Matriz de masa M(q)'], 'M(q) simetrica 4x4: se arma por columnas y se convierte en matriz. m_t = m_b + m_w';
    [CU '/Coriolis y centrifugos C(q,dq) dq'], 'C(q,dq) dq: terminos de Coriolis (2 dl dphi) y centrifugos (l dphi^2), todos proporcionales a m_b';
    [CU '/Gravedad G(q)'], 'G(q): gravedad rotada por la pendiente alpha del piso (alpha = 0 en piso horizontal)';
    [CU '/Fuerzas generalizadas Q'], 'Q por trabajo virtual (manual sec. 5): contacto, empuje F_x, pares de rueda con reaccion sobre el cuerpo, momento M_p, fuerza de la pata';
    IM, 'Fuerza especifica en la IMU: aceleracion del CoM -> punto de la IMU (brazo d_i) -> menos gravedad -> rotada al marco cuerpo   (manual sec. 9)';
    CO, 'CONTROL discreto a Ts: odometria -> filtro complementario -> LQR programado por l -> tension por motor ; consigna del servo con limite de velocidad';
    [CO '/Odometria (encoders)'], 'x, dx y aceleracion de la base desde las cuentas de los encoders (pasabajos a fc_vel y fc_acel)';
    [CO '/Inclinacion (filtro complementario)'], 'phi_est = (1 - k)(phi anterior + giro Ts) + k atan2(-f_x, f_y) ; f corregida por la aceleracion de la base ; k = 0 en vuelo';
    [CO '/LQR programado por largo de pata'], 'par de rueda = -K(l) [x - x_ref ; phi ; dx ; dphi],   K(l) = K1 + K2 l   (manual sec. 10)';
    [CO '/Par de rueda a tension de motores'], 'V = R (tau/2)/(Kt N eta) + Ke N w_est por motor, saturada a +-V_bat';
    [CO '/Consigna del servo'], 'theta_ref = theta(l_ref) con limite de velocidad 0.8 w_vacio y acotada al rango del servo';
    [mdl '/Sensores'], 'IMU y encoders muestreados a Ts: giroscopo con sesgo, ruido y saturacion ; acelerometro con ruido ; encoders en cuentas enteras ; retardo de retardo_muestras';
    [mdl '/Escenario'], 'Referencias y perturbaciones del escenario (escenarios_robot.m), desde el workspace';
    [mdl '/Registro'], 'Se guardan en el workspace: estados, salidas, comandos, estimaciones, medidas (simular_slx los convierte en matrices)';
  };
  for k = 1:size(N, 1), u.nota(N{k, 1}, N{k, 2}); end
end
