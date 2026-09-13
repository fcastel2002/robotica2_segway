function bloques_robot(mdl, u)
%BLOQUES_ROBOT  Subsistema Robot de robot_segway_bloques: la planta completa con bloques nativos.
%   Cada parte fisica es un subsistema que publica un bus con su nombre (bateria, motores, ruedas,
%   piso, contacto, pata, cuerpo, imu); los consumidores eligen con Bus Selector lo que usan.
%   Mismas ecuaciones que robot_planta.m (ver docs/manual_modelo_segway.pdf).
  s = [mdl '/Robot'];
  u.in(s, 'comandos'); u.in(s, 'perturbaciones');
  u.demux(s, 'separar comandos', '3'); u.busc(s, 'bus comandos', '3');
  u.L(s, 'comandos/1', 'separar comandos/1', '');
  nc = {'tension_izq', 'tension_der', 'angulo_servo_ref'};
  for k = 1:3, u.L(s, sprintf('separar comandos/%d', k), sprintf('bus comandos/%d', k), nc{k}); end
  u.demux(s, 'separar perturbaciones', '5'); u.busc(s, 'bus perturbaciones', '5');
  u.L(s, 'perturbaciones/1', 'separar perturbaciones/1', '');
  np = {'F_x', 'M_p', 'pendiente', 'mu', 'F_escalon'};
  for k = 1:5, u.L(s, sprintf('separar perturbaciones/%d', k), sprintf('bus perturbaciones/%d', k), np{k}); end

  bateria(s, u); motores(s, u); ruedas(s, u); piso(s, u); contacto(s, u);
  servo_pata(s, u); cuerpo(s, u); imu(s, u); colector(s, u);
  u.out(s, 'estados'); u.out(s, 'salidas');

  % ---- cableado entre partes (cada linea es un bus con nombre) ----
  B = 'Bateria y puente H'; M = 'Motores y reductores'; R = 'Ruedas'; PI = 'Piso con escalones';
  CO = 'Contacto rueda-piso'; SP = 'Servo y pata'; CU = 'Cuerpo (Lagrange)'; IM = 'IMU (fuerza especifica)';
  CL = 'Estados y salidas con nombre';
  u.L(s, 'bus comandos/1', [B '/1'], 'comandos');           u.L(s, 'bus comandos/1', [SP '/1'], '');
  u.L(s, 'bus perturbaciones/1', [CO '/4'], 'perturbaciones'); u.L(s, 'bus perturbaciones/1', [CU '/4'], ''); u.L(s, 'bus perturbaciones/1', [IM '/2'], '');
  u.L(s, [B '/1'], [M '/1'], 'bateria');                     u.L(s, [B '/1'], [CL '/5'], '');
  u.L(s, [M '/1'], [B '/2'], 'motores');  u.L(s, [M '/1'], [R '/1'], ''); u.L(s, [M '/1'], [CU '/2'], ''); u.L(s, [M '/1'], [CL '/3'], '');
  u.L(s, [R '/1'], [M '/2'], 'ruedas');   u.L(s, [R '/1'], [CO '/2'], ''); u.L(s, [R '/1'], [CL '/2'], '');
  u.L(s, [PI '/1'], [CO '/3'], 'piso');   u.L(s, [PI '/1'], [CL '/7'], '');
  u.L(s, [CO '/1'], [R '/2'], 'contacto'); u.L(s, [CO '/1'], [CU '/1'], ''); u.L(s, [CO '/1'], [CL '/6'], '');
  u.L(s, [SP '/1'], [CU '/3'], 'pata');   u.L(s, [SP '/1'], [CL '/4'], '');
  u.L(s, [CU '/1'], [PI '/1'], 'cuerpo'); u.L(s, [CU '/1'], [CO '/1'], ''); u.L(s, [CU '/1'], [SP '/2'], '');
  u.L(s, [CU '/1'], [IM '/1'], '');       u.L(s, [CU '/1'], [CL '/1'], '');
  u.L(s, [IM '/1'], [CL '/8'], 'imu');
  u.L(s, [CL '/1'], 'estados/1', 'estados'); u.L(s, [CL '/2'], 'salidas/1', 'salidas');

  % ---- distribucion a mano (flujo de izquierda a derecha: energia -> motores -> ruedas -> contacto -> cuerpo) ----
  u.pos(s, { 'comandos', [30 95 60 115]; 'separar comandos', [110 60 115 150]; 'bus comandos', [170 60 175 150]; ...
             'perturbaciones', [30 555 60 575]; 'separar perturbaciones', [110 500 115 630]; 'bus perturbaciones', [170 500 175 630]; ...
             B, [300 50 480 120]; M, [580 50 760 120]; R, [860 50 1040 120]; ...
             SP, [300 250 480 320]; PI, [580 460 760 510]; CO, [860 430 1040 540]; ...
             CU, [1160 230 1360 350]; IM, [1160 460 1360 530]; CL, [1500 150 1720 400]; ...
             'estados', [1820 230 1850 250]; 'salidas', [1820 330 1850 350] });
end

% ======================================================================================
function bateria(s0, u)
% V_bus = max(V_bat - R_bat (|i_izq| + |i_der|), 0);  V aplicada = sat(V pedida, -V_bus..V_bus)
  s = u.sub(s0, 'Bateria y puente H');
  u.in(s, 'comandos'); u.in(s, 'motores');
  u.buss(s, 'tensiones pedidas', 'tension_izq,tension_der'); u.buss(s, 'corrientes', 'corriente_izq,corriente_der');
  u.L(s, 'comandos/1', 'tensiones pedidas/1', ''); u.L(s, 'motores/1', 'corrientes/1', '');
  u.abs(s, '|i izq|'); u.abs(s, '|i der|'); u.sum(s, 'corriente total', '++');
  u.L(s, 'corrientes/1', '|i izq|/1', ''); u.L(s, 'corrientes/2', '|i der|/1', '');
  u.L(s, '|i izq|/1', 'corriente total/1', ''); u.L(s, '|i der|/1', 'corriente total/2', '');
  u.gain(s, 'caida R_bat i', 'par.bateria.R'); u.L(s, 'corriente total/1', 'caida R_bat i/1', 'corriente_total');
  u.const(s, 'V_bat', 'par.bateria.V'); u.sum(s, 'V_bat - caida', '+-');
  u.L(s, 'V_bat/1', 'V_bat - caida/1', ''); u.L(s, 'caida R_bat i/1', 'V_bat - caida/2', 'caida');
  u.const(s, 'cero', '0'); u.minmax(s, 'no menor que 0', 'max', '2');
  u.L(s, 'V_bat - caida/1', 'no menor que 0/1', ''); u.L(s, 'cero/1', 'no menor que 0/2', '');
  u.neg(s, '-V_bus'); u.L(s, 'no menor que 0/1', '-V_bus/1', 'tension_bus');
  u.satdin(s, 'limitar izq'); u.satdin(s, 'limitar der');
  u.L(s, 'no menor que 0/1', 'limitar izq/1', ''); u.L(s, 'tensiones pedidas/1', 'limitar izq/2', ''); u.L(s, '-V_bus/1', 'limitar izq/3', '-tension_bus');
  u.L(s, 'no menor que 0/1', 'limitar der/1', ''); u.L(s, 'tensiones pedidas/2', 'limitar der/2', ''); u.L(s, '-V_bus/1', 'limitar der/3', '');
  u.busc(s, 'bus bateria', '3'); u.out(s, 'bateria');
  u.L(s, 'no menor que 0/1', 'bus bateria/1', '');
  u.L(s, 'limitar izq/1', 'bus bateria/2', 'tension_aplicada_izq'); u.L(s, 'limitar der/1', 'bus bateria/3', 'tension_aplicada_der');
  u.L(s, 'bus bateria/1', 'bateria/1', '');
end

% ======================================================================================
function motores(s0, u)
  s = u.sub(s0, 'Motores y reductores');
  u.in(s, 'bateria'); u.in(s, 'ruedas');
  u.buss(s, 'tensiones aplicadas', 'tension_aplicada_izq,tension_aplicada_der');
  u.buss(s, 'velocidades de rueda', 'vel_rueda_izq,vel_rueda_der');
  u.L(s, 'bateria/1', 'tensiones aplicadas/1', ''); u.L(s, 'ruedas/1', 'velocidades de rueda/1', '');
  motor(s, u, 'Motor y reductor izquierdo', 'estados_iniciales(17)');
  motor(s, u, 'Motor y reductor derecho', 'estados_iniciales(18)');
  u.L(s, 'tensiones aplicadas/1', 'Motor y reductor izquierdo/1', ''); u.L(s, 'velocidades de rueda/1', 'Motor y reductor izquierdo/2', '');
  u.L(s, 'tensiones aplicadas/2', 'Motor y reductor derecho/1', '');   u.L(s, 'velocidades de rueda/2', 'Motor y reductor derecho/2', '');
  u.busc(s, 'bus motores', '4'); u.out(s, 'motores');
  u.L(s, 'Motor y reductor izquierdo/1', 'bus motores/1', 'par_reductor_izq'); u.L(s, 'Motor y reductor derecho/1', 'bus motores/2', 'par_reductor_der');
  u.L(s, 'Motor y reductor izquierdo/2', 'bus motores/3', 'corriente_izq');    u.L(s, 'Motor y reductor derecho/2', 'bus motores/4', 'corriente_der');
  u.L(s, 'bus motores/1', 'motores/1', '');
end

function motor(s0, u, nom, ic)
% L di/dt = V - R i - Ke w_rotor ;  w_rotor = N w_rueda (reductor rigido)
% par_reductor = N (Kt i - tau_c tanh(w_rotor/0.5) - b_rotor w_rotor)
  s = u.sub(s0, nom);
  u.in(s, 'tension'); u.in(s, 'vel_rueda');
  u.gain(s, 'relacion N', 'par.motor.relacion'); u.L(s, 'vel_rueda/1', 'relacion N/1', '');
  u.gain(s, 'fcem Ke w', 'par.motor.Ke'); u.L(s, 'relacion N/1', 'fcem Ke w/1', 'vel_rotor');
  u.gain(s, 'caida R i', 'par.motor.R'); u.sum(s, 'V - R i - fcem', '+--'); u.gain(s, '1 entre L', '1/par.motor.L');
  u.integ(s, 'integrador de corriente', ic);
  u.L(s, 'tension/1', 'V - R i - fcem/1', ''); u.L(s, 'caida R i/1', 'V - R i - fcem/2', ''); u.L(s, 'fcem Ke w/1', 'V - R i - fcem/3', 'fcem');
  u.L(s, 'V - R i - fcem/1', '1 entre L/1', ''); u.L(s, '1 entre L/1', 'integrador de corriente/1', 'di_dt');
  u.L(s, 'integrador de corriente/1', 'caida R i/1', 'corriente');
  u.gain(s, 'par electrico Kt i', 'par.motor.Kt'); u.L(s, 'integrador de corriente/1', 'par electrico Kt i/1', '');
  u.gain(s, 'w entre 0.5', '2'); u.trig(s, 'tanh', 'tanh'); u.gain(s, 'Coulomb tau_c', 'par.motor.tau_coulomb');
  u.gain(s, 'viscosa b_rotor', 'par.motor.b_rotor'); u.sum(s, 'friccion del rotor', '++');
  u.L(s, 'relacion N/1', 'w entre 0.5/1', ''); u.L(s, 'w entre 0.5/1', 'tanh/1', ''); u.L(s, 'tanh/1', 'Coulomb tau_c/1', '');
  u.L(s, 'relacion N/1', 'viscosa b_rotor/1', '');
  u.L(s, 'Coulomb tau_c/1', 'friccion del rotor/1', ''); u.L(s, 'viscosa b_rotor/1', 'friccion del rotor/2', '');
  u.sum(s, 'par neto en el rotor', '+-'); u.gain(s, 'reductor x N', 'par.motor.relacion');
  u.L(s, 'par electrico Kt i/1', 'par neto en el rotor/1', 'par_electrico'); u.L(s, 'friccion del rotor/1', 'par neto en el rotor/2', 'friccion');
  u.L(s, 'par neto en el rotor/1', 'reductor x N/1', '');
  u.out(s, 'par_reductor'); u.out(s, 'corriente');
  u.L(s, 'reductor x N/1', 'par_reductor/1', ''); u.L(s, 'integrador de corriente/1', 'corriente/1', '');
end

% ======================================================================================
function ruedas(s0, u)
  s = u.sub(s0, 'Ruedas');
  u.in(s, 'motores'); u.in(s, 'contacto');
  u.buss(s, 'pares de reductor', 'par_reductor_izq,par_reductor_der'); u.buss(s, 'pares de contacto', 'par_contacto_izq,par_contacto_der');
  u.L(s, 'motores/1', 'pares de reductor/1', ''); u.L(s, 'contacto/1', 'pares de contacto/1', '');
  rueda(s, u, 'Rueda izquierda', 'estados_iniciales(9)', 'estados_iniciales(10)');
  rueda(s, u, 'Rueda derecha', 'estados_iniciales(11)', 'estados_iniciales(12)');
  u.L(s, 'pares de reductor/1', 'Rueda izquierda/1', ''); u.L(s, 'pares de contacto/1', 'Rueda izquierda/2', '');
  u.L(s, 'pares de reductor/2', 'Rueda derecha/1', '');   u.L(s, 'pares de contacto/2', 'Rueda derecha/2', '');
  u.busc(s, 'bus ruedas', '4'); u.out(s, 'ruedas');
  u.L(s, 'Rueda izquierda/1', 'bus ruedas/1', 'ang_rueda_izq'); u.L(s, 'Rueda izquierda/2', 'bus ruedas/2', 'vel_rueda_izq');
  u.L(s, 'Rueda derecha/1', 'bus ruedas/3', 'ang_rueda_der');   u.L(s, 'Rueda derecha/2', 'bus ruedas/4', 'vel_rueda_der');
  u.L(s, 'bus ruedas/1', 'ruedas/1', '');
end

function rueda(s0, u, nom, ic_ang, ic_vel)
% (J_rueda + N^2 J_rotor) dw/dt = par_reductor + par_contacto - b_w w
  s = u.sub(s0, nom);
  u.in(s, 'par_reductor'); u.in(s, 'par_contacto');
  u.gain(s, 'amortiguamiento b_w', 'par.rueda.amort'); u.sum(s, 'par neto', '++-');
  u.gain(s, '1 entre J_eq (rueda + rotor reflejado)', '1/(par.rueda.inercia + par.motor.relacion^2*par.motor.J_rotor)');
  u.integ(s, 'integrador de velocidad', ic_vel); u.integ(s, 'integrador de angulo', ic_ang);
  u.L(s, 'par_reductor/1', 'par neto/1', ''); u.L(s, 'par_contacto/1', 'par neto/2', ''); u.L(s, 'amortiguamiento b_w/1', 'par neto/3', 'friccion');
  u.L(s, 'par neto/1', '1 entre J_eq (rueda + rotor reflejado)/1', '');
  u.L(s, '1 entre J_eq (rueda + rotor reflejado)/1', 'integrador de velocidad/1', 'acel_rueda');
  u.L(s, 'integrador de velocidad/1', 'integrador de angulo/1', 'vel_rueda'); u.L(s, 'integrador de velocidad/1', 'amortiguamiento b_w/1', '');
  u.out(s, 'ang_rueda'); u.out(s, 'vel_rueda');
  u.L(s, 'integrador de angulo/1', 'ang_rueda/1', 'ang_rueda'); u.L(s, 'integrador de velocidad/1', 'vel_rueda/1', '');
end

% ======================================================================================
function piso(s0, u)
% Punto mas cercano del piso al centro de la rueda, calculado sobre TODOS los tramos a la vez
% (par.piso.seg_*: descansos horizontales y contrahuellas verticales, como vectores):
%   p = (clamp(x, xmin, xmax), clamp(y, ymin, ymax)) ; d = |c - p| ; se elige el tramo con d minima
%   penetracion = R - d_min ; normal = (c - p) / d_min
  s = u.sub(s0, 'Piso con escalones');
  u.in(s, 'cuerpo'); u.buss(s, 'centro de la rueda', 'x,y_eje'); u.L(s, 'cuerpo/1', 'centro de la rueda/1', '');
  u.const(s, 'x min de cada tramo', 'par.piso.seg_xmin'); u.const(s, 'x max de cada tramo', 'par.piso.seg_xmax');
  u.const(s, 'y min de cada tramo', 'par.piso.seg_ymin'); u.const(s, 'y max de cada tramo', 'par.piso.seg_ymax');
  u.minmax(s, 'px no menor que x min', 'max', '2'); u.minmax(s, 'px no mayor que x max', 'min', '2');
  u.minmax(s, 'py no menor que y min', 'max', '2'); u.minmax(s, 'py no mayor que y max', 'min', '2');
  u.L(s, 'centro de la rueda/1', 'px no menor que x min/1', ''); u.L(s, 'x min de cada tramo/1', 'px no menor que x min/2', '');
  u.L(s, 'px no menor que x min/1', 'px no mayor que x max/1', ''); u.L(s, 'x max de cada tramo/1', 'px no mayor que x max/2', '');
  u.L(s, 'centro de la rueda/2', 'py no menor que y min/1', ''); u.L(s, 'y min de cada tramo/1', 'py no menor que y min/2', '');
  u.L(s, 'py no menor que y min/1', 'py no mayor que y max/1', ''); u.L(s, 'y max de cada tramo/1', 'py no mayor que y max/2', '');
  u.sum(s, 'x - px', '+-'); u.sum(s, 'y - py', '+-'); u.mathf(s, '(x - px)^2', 'square'); u.mathf(s, '(y - py)^2', 'square');
  u.sum(s, 'suma de cuadrados', '++'); u.sqrt(s, 'distancia a cada tramo');
  u.L(s, 'centro de la rueda/1', 'x - px/1', ''); u.L(s, 'px no mayor que x max/1', 'x - px/2', 'px_de_cada_tramo');
  u.L(s, 'centro de la rueda/2', 'y - py/1', ''); u.L(s, 'py no mayor que y max/1', 'y - py/2', 'py_de_cada_tramo');
  u.L(s, 'x - px/1', '(x - px)^2/1', ''); u.L(s, 'y - py/1', '(y - py)^2/1', '');
  u.L(s, '(x - px)^2/1', 'suma de cuadrados/1', ''); u.L(s, '(y - py)^2/1', 'suma de cuadrados/2', '');
  u.L(s, 'suma de cuadrados/1', 'distancia a cada tramo/1', '');
  u.minmax(s, 'distancia minima', 'min', '1'); u.L(s, 'distancia a cada tramo/1', 'distancia minima/1', 'distancias');
  u.rel(s, 'es el tramo mas cercano', '=='); u.dtc(s, 'peso 0 o 1');
  u.L(s, 'distancia a cada tramo/1', 'es el tramo mas cercano/1', ''); u.L(s, 'distancia minima/1', 'es el tramo mas cercano/2', 'd_min');
  u.L(s, 'es el tramo mas cercano/1', 'peso 0 o 1/1', '');
  u.dot(s, 'peso . px'); u.dot(s, 'peso . py'); u.sumel(s, 'suma de pesos'); u.div(s, 'px elegido'); u.div(s, 'py elegido');
  u.L(s, 'peso 0 o 1/1', 'peso . px/1', 'peso'); u.L(s, 'px no mayor que x max/1', 'peso . px/2', '');
  u.L(s, 'peso 0 o 1/1', 'peso . py/1', ''); u.L(s, 'py no mayor que y max/1', 'peso . py/2', '');
  u.L(s, 'peso 0 o 1/1', 'suma de pesos/1', '');
  u.L(s, 'peso . px/1', 'px elegido/1', ''); u.L(s, 'suma de pesos/1', 'px elegido/2', 'cuantos');
  u.L(s, 'peso . py/1', 'py elegido/1', ''); u.L(s, 'suma de pesos/1', 'py elegido/2', '');
  u.const(s, 'radio de rueda', 'par.rueda.radio'); u.sum(s, 'penetracion = R - d min', '+-');
  u.L(s, 'radio de rueda/1', 'penetracion = R - d min/1', ''); u.L(s, 'distancia minima/1', 'penetracion = R - d min/2', '');
  u.sum(s, 'x - px elegido', '+-'); u.sum(s, 'y - py elegido', '+-');
  u.L(s, 'centro de la rueda/1', 'x - px elegido/1', ''); u.L(s, 'px elegido/1', 'x - px elegido/2', 'contacto_x');
  u.L(s, 'centro de la rueda/2', 'y - py elegido/1', ''); u.L(s, 'py elegido/1', 'y - py elegido/2', 'contacto_y');
  u.const(s, 'minimo 1e-9', '1e-9'); u.minmax(s, 'd min (no menor que 1e-9)', 'max', '2');
  u.L(s, 'distancia minima/1', 'd min (no menor que 1e-9)/1', ''); u.L(s, 'minimo 1e-9/1', 'd min (no menor que 1e-9)/2', '');
  u.div(s, 'normal x'); u.div(s, 'normal y');
  u.L(s, 'x - px elegido/1', 'normal x/1', ''); u.L(s, 'd min (no menor que 1e-9)/1', 'normal x/2', '');
  u.L(s, 'y - py elegido/1', 'normal y/1', ''); u.L(s, 'd min (no menor que 1e-9)/1', 'normal y/2', '');
  u.busc(s, 'bus piso', '5'); u.out(s, 'piso');
  u.L(s, 'penetracion = R - d min/1', 'bus piso/1', 'penetracion');
  u.L(s, 'normal x/1', 'bus piso/2', 'normal_x'); u.L(s, 'normal y/1', 'bus piso/3', 'normal_y');
  u.L(s, 'px elegido/1', 'bus piso/4', ''); u.L(s, 'py elegido/1', 'bus piso/5', '');
  u.L(s, 'bus piso/1', 'piso/1', '');
end

% ======================================================================================
function contacto(s0, u)
% Por rueda: N_i = max(0, k delta + c ddelta) solo si delta > 0 ; ddelta = -(dx nx + dy ny)
% tangente (tx, ty) = (ny, -nx) ; deslizamiento v_s = R w - (dx tx + dy ty)
% f = mu N_i tanh(v_s/v0) - c_v v_s ;  fuerza sobre el eje = 2 N_i n + (f_izq + f_der) t ; par = -R f
  s = u.sub(s0, 'Contacto rueda-piso');
  u.in(s, 'cuerpo'); u.in(s, 'ruedas'); u.in(s, 'piso'); u.in(s, 'perturbaciones');
  u.buss(s, 'velocidad del eje', 'dx,dy_eje'); u.buss(s, 'giro de las ruedas', 'vel_rueda_izq,vel_rueda_der');
  u.buss(s, 'geometria del contacto', 'penetracion,normal_x,normal_y'); u.buss(s, 'mu del escenario', 'mu');
  u.L(s, 'cuerpo/1', 'velocidad del eje/1', ''); u.L(s, 'ruedas/1', 'giro de las ruedas/1', '');
  u.L(s, 'piso/1', 'geometria del contacto/1', ''); u.L(s, 'perturbaciones/1', 'mu del escenario/1', '');
  % mu efectivo: el del escenario si es > 0, si no el nominal
  u.const(s, 'mu nominal', 'par.rueda.mu'); u.sw(s, 'mu del escenario si es > 0', 'u2 > Threshold', '0');
  u.L(s, 'mu del escenario/1', 'mu del escenario si es > 0/1', ''); u.L(s, 'mu del escenario/1', 'mu del escenario si es > 0/2', '');
  u.L(s, 'mu nominal/1', 'mu del escenario si es > 0/3', '');
  % hay contacto
  u.cmp0(s, 'hay contacto (penetracion > 0)', '>'); u.dtc(s, 'contacto 0 o 1');
  u.L(s, 'geometria del contacto/1', 'hay contacto (penetracion > 0)/1', ''); u.L(s, 'hay contacto (penetracion > 0)/1', 'contacto 0 o 1/1', '');
  % velocidad de hundimiento
  u.prod(s, 'dx nx', '**'); u.prod(s, 'dy ny', '**'); u.sum(s, 'vel de hundimiento = -(dx nx + dy ny)', '--');
  u.L(s, 'velocidad del eje/1', 'dx nx/1', ''); u.L(s, 'geometria del contacto/2', 'dx nx/2', '');
  u.L(s, 'velocidad del eje/2', 'dy ny/1', ''); u.L(s, 'geometria del contacto/3', 'dy ny/2', '');
  u.L(s, 'dx nx/1', 'vel de hundimiento = -(dx nx + dy ny)/1', ''); u.L(s, 'dy ny/1', 'vel de hundimiento = -(dx nx + dy ny)/2', '');
  % normal por rueda
  u.gain(s, 'rigidez del neumatico k', 'par.contacto.k'); u.gain(s, 'amortiguacion del neumatico c', 'par.contacto.c');
  u.sum(s, 'k delta + c ddelta', '++'); u.const(s, 'cero', '0'); u.minmax(s, 'no negativa', 'max', '2');
  u.sw(s, 'solo si hay contacto', 'u2 > Threshold', '0');
  u.L(s, 'geometria del contacto/1', 'rigidez del neumatico k/1', ''); u.L(s, 'vel de hundimiento = -(dx nx + dy ny)/1', 'amortiguacion del neumatico c/1', 'vel_hundimiento');
  u.L(s, 'rigidez del neumatico k/1', 'k delta + c ddelta/1', ''); u.L(s, 'amortiguacion del neumatico c/1', 'k delta + c ddelta/2', '');
  u.L(s, 'k delta + c ddelta/1', 'no negativa/1', ''); u.L(s, 'cero/1', 'no negativa/2', '');
  u.L(s, 'no negativa/1', 'solo si hay contacto/1', ''); u.L(s, 'geometria del contacto/1', 'solo si hay contacto/2', ''); u.L(s, 'cero/1', 'solo si hay contacto/3', '');
  % tangente y velocidad tangencial
  u.neg(s, 'ty = -nx'); u.L(s, 'geometria del contacto/2', 'ty = -nx/1', '');
  u.prod(s, 'dx tx', '**'); u.prod(s, 'dy ty', '**'); u.sum(s, 'vel tangencial del eje', '++');
  u.L(s, 'velocidad del eje/1', 'dx tx/1', ''); u.L(s, 'geometria del contacto/3', 'dx tx/2', '');
  u.L(s, 'velocidad del eje/2', 'dy ty/1', ''); u.L(s, 'ty = -nx/1', 'dy ty/2', 'ty');
  u.L(s, 'dx tx/1', 'vel tangencial del eje/1', ''); u.L(s, 'dy ty/1', 'vel tangencial del eje/2', '');
  u.gain(s, 'R w izq', 'par.rueda.radio'); u.gain(s, 'R w der', 'par.rueda.radio');
  u.sum(s, 'deslizamiento izq = R w - v', '+-'); u.sum(s, 'deslizamiento der = R w - v', '+-');
  u.L(s, 'giro de las ruedas/1', 'R w izq/1', ''); u.L(s, 'giro de las ruedas/2', 'R w der/1', '');
  u.L(s, 'R w izq/1', 'deslizamiento izq = R w - v/1', ''); u.L(s, 'vel tangencial del eje/1', 'deslizamiento izq = R w - v/2', 'vel_tangencial');
  u.L(s, 'R w der/1', 'deslizamiento der = R w - v/1', ''); u.L(s, 'vel tangencial del eje/1', 'deslizamiento der = R w - v/2', '');
  % friccion de cada rueda
  friccion(s, u, 'Friccion rueda izquierda'); friccion(s, u, 'Friccion rueda derecha');
  for lado = {'izquierda', 'derecha'}
    nb = ['Friccion rueda ' lado{1}]; if strcmp(lado{1}, 'izquierda'), d = 'izq'; else, d = 'der'; end
    u.L(s, ['deslizamiento ' d ' = R w - v/1'], [nb '/1'], ['deslizamiento_' d]);
    u.L(s, 'solo si hay contacto/1', [nb '/2'], ''); u.L(s, 'mu del escenario si es > 0/1', [nb '/3'], ''); u.L(s, 'contacto 0 o 1/1', [nb '/4'], '');
  end
  % fuerzas sobre el eje y pares
  u.sum(s, 'friccion total', '++'); u.gain(s, 'dos ruedas', '2');
  u.L(s, 'Friccion rueda izquierda/1', 'friccion total/1', 'fuerza_piso_izq'); u.L(s, 'Friccion rueda derecha/1', 'friccion total/2', 'fuerza_piso_der');
  u.L(s, 'solo si hay contacto/1', 'dos ruedas/1', 'normal_por_rueda');
  u.prod(s, 'N nx', '**'); u.prod(s, 'f tx', '**'); u.sum(s, 'fuerza x sobre el eje', '++');
  u.prod(s, 'N ny', '**'); u.prod(s, 'f ty', '**'); u.sum(s, 'fuerza y sobre el eje', '++');
  u.L(s, 'dos ruedas/1', 'N nx/1', 'normal'); u.L(s, 'geometria del contacto/2', 'N nx/2', '');
  u.L(s, 'friccion total/1', 'f tx/1', 'friccion_total'); u.L(s, 'geometria del contacto/3', 'f tx/2', '');
  u.L(s, 'dos ruedas/1', 'N ny/1', ''); u.L(s, 'geometria del contacto/3', 'N ny/2', '');
  u.L(s, 'friccion total/1', 'f ty/1', ''); u.L(s, 'ty = -nx/1', 'f ty/2', '');
  u.L(s, 'N nx/1', 'fuerza x sobre el eje/1', ''); u.L(s, 'f tx/1', 'fuerza x sobre el eje/2', '');
  u.L(s, 'N ny/1', 'fuerza y sobre el eje/1', ''); u.L(s, 'f ty/1', 'fuerza y sobre el eje/2', '');
  u.gain(s, 'par izq = -R f', '-par.rueda.radio'); u.gain(s, 'par der = -R f', '-par.rueda.radio');
  u.L(s, 'Friccion rueda izquierda/1', 'par izq = -R f/1', ''); u.L(s, 'Friccion rueda derecha/1', 'par der = -R f/1', '');
  % indicador de deslizamiento
  u.abs(s, '|desl izq|'); u.abs(s, '|desl der|'); u.cmpc(s, 'izq > 2 v0', '>', '2*par.rueda.v0'); u.cmpc(s, 'der > 2 v0', '>', '2*par.rueda.v0');
  u.logic(s, 'alguna desliza', 'OR', '2'); u.logic(s, 'y hay contacto', 'AND', '2'); u.dtc(s, 'desliza 0 o 1');
  u.L(s, 'deslizamiento izq = R w - v/1', '|desl izq|/1', ''); u.L(s, 'deslizamiento der = R w - v/1', '|desl der|/1', '');
  u.L(s, '|desl izq|/1', 'izq > 2 v0/1', ''); u.L(s, '|desl der|/1', 'der > 2 v0/1', '');
  u.L(s, 'izq > 2 v0/1', 'alguna desliza/1', ''); u.L(s, 'der > 2 v0/1', 'alguna desliza/2', '');
  u.L(s, 'alguna desliza/1', 'y hay contacto/1', ''); u.L(s, 'hay contacto (penetracion > 0)/1', 'y hay contacto/2', '');
  u.L(s, 'y hay contacto/1', 'desliza 0 o 1/1', '');
  % bus de salida
  u.busc(s, 'bus contacto', '8'); u.out(s, 'contacto');
  u.L(s, 'fuerza x sobre el eje/1', 'bus contacto/1', 'fuerza_contacto_x'); u.L(s, 'fuerza y sobre el eje/1', 'bus contacto/2', 'fuerza_contacto_y');
  u.L(s, 'par izq = -R f/1', 'bus contacto/3', 'par_contacto_izq'); u.L(s, 'par der = -R f/1', 'bus contacto/4', 'par_contacto_der');
  u.L(s, 'dos ruedas/1', 'bus contacto/5', '');
  u.L(s, 'Friccion rueda izquierda/1', 'bus contacto/6', ''); u.L(s, 'Friccion rueda derecha/1', 'bus contacto/7', '');
  u.L(s, 'desliza 0 o 1/1', 'bus contacto/8', 'desliza');
  u.L(s, 'bus contacto/1', 'contacto/1', '');
end

function friccion(s0, u, nom)
% f = contacto * (mu N tanh(v_s / v0) - c_v v_s)
  s = u.sub(s0, nom);
  u.in(s, 'deslizamiento'); u.in(s, 'normal_por_rueda'); u.in(s, 'mu'); u.in(s, 'contacto');
  u.gain(s, '1 entre v0', '1/par.rueda.v0'); u.trig(s, 'tanh', 'tanh'); u.prod(s, 'mu N tanh', '***');
  u.gain(s, 'viscosa c_v', 'par.rueda.c_v'); u.sum(s, 'Coulomb - viscosa', '+-'); u.prod(s, 'solo con contacto', '**');
  u.L(s, 'deslizamiento/1', '1 entre v0/1', ''); u.L(s, '1 entre v0/1', 'tanh/1', ''); u.L(s, 'tanh/1', 'mu N tanh/3', '');
  u.L(s, 'mu/1', 'mu N tanh/1', ''); u.L(s, 'normal_por_rueda/1', 'mu N tanh/2', '');
  u.L(s, 'deslizamiento/1', 'viscosa c_v/1', '');
  u.L(s, 'mu N tanh/1', 'Coulomb - viscosa/1', ''); u.L(s, 'viscosa c_v/1', 'Coulomb - viscosa/2', '');
  u.L(s, 'Coulomb - viscosa/1', 'solo con contacto/1', ''); u.L(s, 'contacto/1', 'solo con contacto/2', '');
  u.out(s, 'fuerza'); u.L(s, 'solo con contacto/1', 'fuerza/1', '');
end

% ======================================================================================
function servo_pata(s0, u)
% El servo actua sobre el largo que impone el cuatro barras: l (sin flexor) o l_mec (con flexor).
% Sin flexor:  fuerza sobre l = F_servo + F_topes - b_pata dl
% Con flexor:  fuerza sobre l = F_flexor ;  m_mec ddl_mec = F_servo - F_flexor + F_topes - b_pata dl_mec
  s = u.sub(s0, 'Servo y pata');
  u.in(s, 'comandos'); u.in(s, 'cuerpo');
  u.buss(s, 'consigna', 'angulo_servo_ref'); u.buss(s, 'largo de pata', 'largo_pata,d_largo_pata');
  u.L(s, 'comandos/1', 'consigna/1', ''); u.L(s, 'cuerpo/1', 'largo de pata/1', '');
  u.const(s, 'flexor activo', 'par.pata.flexor_activo'); u.const(s, 'cero', '0');
  u.integ(s, 'integrador largo mecanismo', 'estados_iniciales(19)'); u.integ(s, 'integrador vel mecanismo', 'estados_iniciales(20)');
  u.sw(s, 'd largo mec (si flexor)', 'u2 > Threshold', '0.5'); u.sw(s, 'acel mec (si flexor)', 'u2 > Threshold', '0.5');
  u.sw(s, 'largo que mueve el servo', 'u2 > Threshold', '0.5'); u.sw(s, 'velocidad que ve el servo', 'u2 > Threshold', '0.5');
  u.L(s, 'integrador vel mecanismo/1', 'd largo mec (si flexor)/1', 'd_largo_mecanismo'); u.L(s, 'flexor activo/1', 'd largo mec (si flexor)/2', ''); u.L(s, 'cero/1', 'd largo mec (si flexor)/3', '');
  u.L(s, 'd largo mec (si flexor)/1', 'integrador largo mecanismo/1', '');
  u.L(s, 'flexor activo/1', 'acel mec (si flexor)/2', ''); u.L(s, 'cero/1', 'acel mec (si flexor)/3', '');
  u.L(s, 'acel mec (si flexor)/1', 'integrador vel mecanismo/1', '');
  u.L(s, 'integrador largo mecanismo/1', 'largo que mueve el servo/1', 'largo_mecanismo'); u.L(s, 'flexor activo/1', 'largo que mueve el servo/2', ''); u.L(s, 'largo de pata/1', 'largo que mueve el servo/3', '');
  u.L(s, 'integrador vel mecanismo/1', 'velocidad que ve el servo/1', ''); u.L(s, 'flexor activo/1', 'velocidad que ve el servo/2', ''); u.L(s, 'largo de pata/2', 'velocidad que ve el servo/3', '');
  servo(s, u); topes(s, u); flexor(s, u);
  SV = 'Servo (PD con limite par-velocidad)'; TP = 'Topes de carrera'; FL = 'Flexor (resorte en serie)';
  u.L(s, 'consigna/1', [SV '/1'], '');
  u.L(s, 'largo que mueve el servo/1', [SV '/2'], 'largo_q'); u.L(s, 'velocidad que ve el servo/1', [SV '/3'], 'd_largo_q');
  u.L(s, 'largo que mueve el servo/1', [TP '/1'], ''); u.L(s, 'velocidad que ve el servo/1', [TP '/2'], '');
  u.L(s, 'integrador largo mecanismo/1', [FL '/1'], ''); u.L(s, 'largo de pata/1', [FL '/2'], '');
  u.L(s, 'integrador vel mecanismo/1', [FL '/3'], ''); u.L(s, 'largo de pata/2', [FL '/4'], '');
  % sin flexor
  u.gain(s, 'amortiguamiento de pata b_pata', 'par.cuerpo.amort_pata'); u.sum(s, 'servo + topes - amort', '++-');
  u.L(s, 'largo de pata/2', 'amortiguamiento de pata b_pata/1', '');
  u.L(s, [SV '/3'], 'servo + topes - amort/1', 'fuerza_servo'); u.L(s, [TP '/1'], 'servo + topes - amort/2', 'fuerza_topes');
  u.L(s, 'amortiguamiento de pata b_pata/1', 'servo + topes - amort/3', '');
  u.sw(s, 'fuerza sobre l', 'u2 > Threshold', '0.5');
  u.L(s, [FL '/1'], 'fuerza sobre l/1', 'fuerza_flexor'); u.L(s, 'flexor activo/1', 'fuerza sobre l/2', ''); u.L(s, 'servo + topes - amort/1', 'fuerza sobre l/3', '');
  % con flexor: ecuacion del mecanismo
  u.gain(s, 'amortiguamiento del mecanismo', 'par.cuerpo.amort_pata'); u.sum(s, 'servo - flexor + topes - amort', '+-+-'); u.gain(s, '1 entre m mecanismo', '1/par.pata.masa_mecanismo');
  u.L(s, 'integrador vel mecanismo/1', 'amortiguamiento del mecanismo/1', '');
  u.L(s, [SV '/3'], 'servo - flexor + topes - amort/1', ''); u.L(s, [FL '/1'], 'servo - flexor + topes - amort/2', '');
  u.L(s, [TP '/1'], 'servo - flexor + topes - amort/3', ''); u.L(s, 'amortiguamiento del mecanismo/1', 'servo - flexor + topes - amort/4', '');
  u.L(s, 'servo - flexor + topes - amort/1', '1 entre m mecanismo/1', ''); u.L(s, '1 entre m mecanismo/1', 'acel mec (si flexor)/1', '');
  % bus de salida
  u.busc(s, 'bus pata', '5'); u.out(s, 'pata');
  u.L(s, 'fuerza sobre l/1', 'bus pata/1', 'fuerza_pata');
  u.L(s, [SV '/1'], 'bus pata/2', 'par_servo'); u.L(s, [SV '/2'], 'bus pata/3', 'angulo_servo');
  u.L(s, 'integrador largo mecanismo/1', 'bus pata/4', ''); u.L(s, 'integrador vel mecanismo/1', 'bus pata/5', '');
  u.L(s, 'bus pata/1', 'pata/1', '');
  % ---- distribucion a mano ----
  u.pos(s, { 'comandos', [30 420 60 440]; 'consigna', [110 420 115 440]; 'cuerpo', [30 200 60 220]; 'largo de pata', [110 190 115 230]; ...
             'flexor activo', [110 300 160 320]; 'cero', [110 350 140 370]; ...
             'largo que mueve el servo', [250 160 280 200]; 'velocidad que ve el servo', [250 240 280 280]; ...
             FL, [400 40 580 130]; TP, [400 250 580 300]; SV, [400 380 580 460]; ...
             'amortiguamiento de pata b_pata', [400 330 440 360]; 'servo + topes - amort', [700 320 730 380]; 'fuerza sobre l', [820 300 850 340]; ...
             'servo - flexor + topes - amort', [400 600 430 660]; '1 entre m mecanismo', [470 610 510 650]; 'acel mec (si flexor)', [560 600 590 640]; ...
             'integrador vel mecanismo', [640 605 670 635]; 'd largo mec (si flexor)', [720 600 750 640]; 'integrador largo mecanismo', [800 605 830 635]; ...
             'amortiguamiento del mecanismo', [560 680 600 720]; 'bus pata', [950 280 955 420]; 'pata', [1030 340 1060 360] });
end

function servo(s0, u)
% theta = tabla(l) ; dtheta = dtheta_dl(l) * dl ; par pedido = Kp (ref - theta) - Kd dtheta
% limite: si el par acompana al giro, tau_max (1 - |dtheta| / w_vacio) ; si frena, tau_max
% fuerza sobre l = n_servos * par * dtheta_dl
  s = u.sub(s0, 'Servo (PD con limite par-velocidad)');
  u.in(s, 'angulo_ref'); u.in(s, 'largo'); u.in(s, 'd_largo');
  u.lut(s, 'angulo del servo theta(l)', 'par.pata.tabla_l', 'par.pata.tabla_theta');
  u.lut(s, 'dtheta_dl (l)', 'par.pata.tabla_l', 'par.pata.tabla_dtheta_dl');
  u.prod(s, 'vel del servo = dtheta_dl dl', '**');
  u.L(s, 'largo/1', 'angulo del servo theta(l)/1', ''); u.L(s, 'largo/1', 'dtheta_dl (l)/1', '');
  u.L(s, 'dtheta_dl (l)/1', 'vel del servo = dtheta_dl dl/1', 'dtheta_dl'); u.L(s, 'd_largo/1', 'vel del servo = dtheta_dl dl/2', '');
  u.sum(s, 'error de angulo', '+-'); u.gain(s, 'Kp', 'par.servo.Kp'); u.gain(s, 'Kd', 'par.servo.Kd'); u.sum(s, 'par pedido', '+-');
  u.L(s, 'angulo_ref/1', 'error de angulo/1', ''); u.L(s, 'angulo del servo theta(l)/1', 'error de angulo/2', 'angulo_servo');
  u.L(s, 'error de angulo/1', 'Kp/1', ''); u.L(s, 'vel del servo = dtheta_dl dl/1', 'Kd/1', 'vel_servo');
  u.L(s, 'Kp/1', 'par pedido/1', ''); u.L(s, 'Kd/1', 'par pedido/2', '');
  u.prod(s, 'par x velocidad', '**'); u.abs(s, '|vel servo|'); u.gain(s, '1 entre w vacio', '1/par.servo.w_vacio');
  u.const(s, 'uno', '1'); u.sum(s, '1 - |w| entre w vacio', '+-'); u.const(s, 'cero', '0'); u.minmax(s, 'no negativo', 'max', '2');
  u.gain(s, 'x tau max', 'par.servo.tau_max'); u.const(s, 'tau max', 'par.servo.tau_max');
  u.sw(s, 'acompana al giro?', 'u2 > Threshold', '0'); u.neg(s, '-limite'); u.satdin(s, 'saturar par');
  u.L(s, 'par pedido/1', 'par x velocidad/1', 'par_pedido'); u.L(s, 'vel del servo = dtheta_dl dl/1', 'par x velocidad/2', '');
  u.L(s, 'vel del servo = dtheta_dl dl/1', '|vel servo|/1', ''); u.L(s, '|vel servo|/1', '1 entre w vacio/1', '');
  u.L(s, 'uno/1', '1 - |w| entre w vacio/1', ''); u.L(s, '1 entre w vacio/1', '1 - |w| entre w vacio/2', '');
  u.L(s, '1 - |w| entre w vacio/1', 'no negativo/1', ''); u.L(s, 'cero/1', 'no negativo/2', '');
  u.L(s, 'no negativo/1', 'x tau max/1', '');
  u.L(s, 'x tau max/1', 'acompana al giro?/1', 'limite_reducido'); u.L(s, 'par x velocidad/1', 'acompana al giro?/2', ''); u.L(s, 'tau max/1', 'acompana al giro?/3', '');
  u.L(s, 'acompana al giro?/1', 'saturar par/1', 'limite'); u.L(s, 'par pedido/1', 'saturar par/2', ''); u.L(s, 'acompana al giro?/1', '-limite/1', ''); u.L(s, '-limite/1', 'saturar par/3', '');
  u.gain(s, 'n servos', 'par.servo.cantidad'); u.prod(s, 'fuerza = n tau dtheta_dl', '**');
  u.L(s, 'saturar par/1', 'n servos/1', 'par_servo'); u.L(s, 'n servos/1', 'fuerza = n tau dtheta_dl/1', ''); u.L(s, 'dtheta_dl (l)/1', 'fuerza = n tau dtheta_dl/2', '');
  u.out(s, 'par_servo'); u.out(s, 'angulo_servo'); u.out(s, 'fuerza_servo');
  u.L(s, 'saturar par/1', 'par_servo/1', ''); u.L(s, 'angulo del servo theta(l)/1', 'angulo_servo/1', ''); u.L(s, 'fuerza = n tau dtheta_dl/1', 'fuerza_servo/1', '');
end

function topes(s0, u)
% fuera de [l_min, l_max]: F = -k_tope (l - tope) - c_tope dl
  s = u.sub(s0, 'Topes de carrera');
  u.in(s, 'largo'); u.in(s, 'd_largo');
  u.deadzone(s, 'cuanto se pasa del tope', 'par.pata.l_min', 'par.pata.l_max'); u.gain(s, '-k tope', '-par.cuerpo.k_tope');
  u.cmp0(s, 'toca el tope', '~='); u.dtc(s, 'tope 0 o 1'); u.prod(s, 'vel si toca', '**'); u.gain(s, '-c tope', '-par.cuerpo.c_tope');
  u.sum(s, 'fuerza de tope', '++');
  u.L(s, 'largo/1', 'cuanto se pasa del tope/1', ''); u.L(s, 'cuanto se pasa del tope/1', '-k tope/1', 'exceso');
  u.L(s, 'cuanto se pasa del tope/1', 'toca el tope/1', ''); u.L(s, 'toca el tope/1', 'tope 0 o 1/1', '');
  u.L(s, 'tope 0 o 1/1', 'vel si toca/1', ''); u.L(s, 'd_largo/1', 'vel si toca/2', ''); u.L(s, 'vel si toca/1', '-c tope/1', '');
  u.L(s, '-k tope/1', 'fuerza de tope/1', ''); u.L(s, '-c tope/1', 'fuerza de tope/2', '');
  u.out(s, 'fuerza_tope'); u.L(s, 'fuerza de tope/1', 'fuerza_tope/1', '');
end

function flexor(s0, u)
% compresion s = l_mec - l ; F = k_f s + c_f ds + (tope si s < 0 o s > carrera)
  s = u.sub(s0, 'Flexor (resorte en serie)');
  u.in(s, 'largo_mecanismo'); u.in(s, 'largo_pata'); u.in(s, 'd_largo_mecanismo'); u.in(s, 'd_largo_pata');
  u.sum(s, 'compresion = l mec - l', '+-'); u.sum(s, 'd compresion', '+-');
  u.gain(s, 'k flexor', 'par.pata.k_flexor'); u.gain(s, 'c flexor', 'par.pata.c_flexor');
  u.deadzone(s, 'fuera de la carrera', '0', 'par.pata.carrera_flexor'); u.gain(s, 'k tope', 'par.cuerpo.k_tope');
  u.cmp0(s, 'toca el tope', '~='); u.dtc(s, 'tope 0 o 1'); u.prod(s, 'vel si toca', '**'); u.gain(s, 'c tope', 'par.cuerpo.c_tope');
  u.sum(s, 'fuerza del flexor', '++++');
  u.L(s, 'largo_mecanismo/1', 'compresion = l mec - l/1', ''); u.L(s, 'largo_pata/1', 'compresion = l mec - l/2', '');
  u.L(s, 'd_largo_mecanismo/1', 'd compresion/1', ''); u.L(s, 'd_largo_pata/1', 'd compresion/2', '');
  u.L(s, 'compresion = l mec - l/1', 'k flexor/1', 'compresion'); u.L(s, 'd compresion/1', 'c flexor/1', 'd_compresion');
  u.L(s, 'compresion = l mec - l/1', 'fuera de la carrera/1', ''); u.L(s, 'fuera de la carrera/1', 'k tope/1', 'exceso');
  u.L(s, 'fuera de la carrera/1', 'toca el tope/1', ''); u.L(s, 'toca el tope/1', 'tope 0 o 1/1', '');
  u.L(s, 'tope 0 o 1/1', 'vel si toca/1', ''); u.L(s, 'd compresion/1', 'vel si toca/2', ''); u.L(s, 'vel si toca/1', 'c tope/1', '');
  u.L(s, 'k flexor/1', 'fuerza del flexor/1', ''); u.L(s, 'c flexor/1', 'fuerza del flexor/2', '');
  u.L(s, 'k tope/1', 'fuerza del flexor/3', ''); u.L(s, 'c tope/1', 'fuerza del flexor/4', '');
  u.out(s, 'fuerza_flexor'); u.L(s, 'fuerza del flexor/1', 'fuerza_flexor/1', '');
end

% ======================================================================================
function cuerpo(s0, u)
% M(q) qdd = Q - C(q, qd) qd - G(q),  q = [x, y, phi, l]  (manual, seccion 4)
  s = u.sub(s0, 'Cuerpo (Lagrange)');
  u.in(s, 'contacto'); u.in(s, 'motores'); u.in(s, 'pata'); u.in(s, 'perturbaciones');
  u.buss(s, 'fuerzas de contacto', 'fuerza_contacto_x,fuerza_contacto_y'); u.buss(s, 'pares de reductor', 'par_reductor_izq,par_reductor_der');
  u.buss(s, 'fuerza de la pata', 'fuerza_pata'); u.buss(s, 'perturbaciones externas', 'F_x,M_p,pendiente,F_escalon');
  u.L(s, 'contacto/1', 'fuerzas de contacto/1', ''); u.L(s, 'motores/1', 'pares de reductor/1', '');
  u.L(s, 'pata/1', 'fuerza de la pata/1', ''); u.L(s, 'perturbaciones/1', 'perturbaciones externas/1', '');
  % integradores: aceleracion -> velocidad -> posicion
  nomq = {'x', 'y_eje', 'inclinacion', 'largo_pata'}; nomv = {'dx', 'dy_eje', 'd_inclinacion', 'd_largo_pata'};
  for k = 1:4
    u.integ(s, ['integrador ' nomv{k}], sprintf('estados_iniciales(%d)', 4 + k));
    u.integ(s, ['integrador ' nomq{k}], sprintf('estados_iniciales(%d)', k));
    u.L(s, ['integrador ' nomv{k} '/1'], ['integrador ' nomq{k} '/1'], nomv{k});
  end
  u.const(s, 'l minimo 1 mm', '1e-3'); u.minmax(s, 'largo (no menor que 1 mm)', 'max', '2');
  u.L(s, 'integrador largo_pata/1', 'largo (no menor que 1 mm)/1', 'largo_pata_integrado'); u.L(s, 'l minimo 1 mm/1', 'largo (no menor que 1 mm)/2', '');
  fuerzas_Q(s, u); masa_M(s, u); coriolis_C(s, u); gravedad_G(s, u);
  Q = 'Fuerzas generalizadas Q'; MM = 'Matriz de masa M(q)'; CC = 'Coriolis y centrifugos C(q,dq) dq'; GG = 'Gravedad G(q)';
  u.L(s, 'fuerzas de contacto/1', [Q '/1'], ''); u.L(s, 'fuerzas de contacto/2', [Q '/2'], '');
  u.L(s, 'pares de reductor/1', [Q '/3'], ''); u.L(s, 'pares de reductor/2', [Q '/4'], ''); u.L(s, 'fuerza de la pata/1', [Q '/5'], '');
  u.L(s, 'perturbaciones externas/1', [Q '/6'], ''); u.L(s, 'perturbaciones externas/2', [Q '/7'], ''); u.L(s, 'perturbaciones externas/4', [Q '/8'], '');
  u.L(s, 'integrador inclinacion/1', [Q '/9'], 'inclinacion'); u.L(s, 'largo (no menor que 1 mm)/1', [Q '/10'], 'largo_pata'); u.L(s, 'integrador d_inclinacion/1', [Q '/11'], '');
  u.L(s, 'integrador inclinacion/1', [MM '/1'], ''); u.L(s, 'largo (no menor que 1 mm)/1', [MM '/2'], '');
  u.L(s, 'integrador inclinacion/1', [CC '/1'], ''); u.L(s, 'largo (no menor que 1 mm)/1', [CC '/2'], '');
  u.L(s, 'integrador d_inclinacion/1', [CC '/3'], ''); u.L(s, 'integrador d_largo_pata/1', [CC '/4'], '');
  u.L(s, 'integrador inclinacion/1', [GG '/1'], ''); u.L(s, 'largo (no menor que 1 mm)/1', [GG '/2'], ''); u.L(s, 'perturbaciones externas/3', [GG '/3'], '');
  u.sum(s, 'Q - C dq - G', '+--'); u.mprod(s, 'aceleraciones = inv(M) (Q - C dq - G)', '/*'); u.demux(s, 'separar aceleraciones', '4');
  u.L(s, [Q '/1'], 'Q - C dq - G/1', 'Q'); u.L(s, [CC '/1'], 'Q - C dq - G/2', 'C_dq'); u.L(s, [GG '/1'], 'Q - C dq - G/3', 'G');
  u.L(s, [MM '/1'], 'aceleraciones = inv(M) (Q - C dq - G)/1', 'M'); u.L(s, 'Q - C dq - G/1', 'aceleraciones = inv(M) (Q - C dq - G)/2', '');
  u.L(s, 'aceleraciones = inv(M) (Q - C dq - G)/1', 'separar aceleraciones/1', 'aceleraciones');
  noma = {'acel_x', 'acel_y_eje', 'acel_inclinacion', 'acel_largo'};
  for k = 1:4, u.L(s, sprintf('separar aceleraciones/%d', k), ['integrador ' nomv{k} '/1'], noma{k}); end
  % bus de salida
  u.busc(s, 'bus cuerpo', '12'); u.out(s, 'cuerpo');
  u.L(s, 'integrador x/1', 'bus cuerpo/1', 'x'); u.L(s, 'integrador y_eje/1', 'bus cuerpo/2', 'y_eje');
  u.L(s, 'integrador inclinacion/1', 'bus cuerpo/3', ''); u.L(s, 'largo (no menor que 1 mm)/1', 'bus cuerpo/4', '');
  for k = 1:4, u.L(s, ['integrador ' nomv{k} '/1'], sprintf('bus cuerpo/%d', 4 + k), ''); end
  for k = 1:4, u.L(s, sprintf('separar aceleraciones/%d', k), sprintf('bus cuerpo/%d', 8 + k), ''); end
  u.L(s, 'bus cuerpo/1', 'cuerpo/1', '');
  % ---- distribucion a mano: fuerzas y matrices a la izquierda, resolucion en el medio, integradores a la derecha ----
  u.pos(s, { 'contacto', [30 60 60 80]; 'motores', [30 140 60 160]; 'pata', [30 220 60 240]; 'perturbaciones', [30 300 60 320]; ...
             'fuerzas de contacto', [120 50 125 90]; 'pares de reductor', [120 130 125 170]; 'fuerza de la pata', [120 215 125 245]; 'perturbaciones externas', [120 290 125 350]; ...
             Q, [300 40 480 320]; MM, [300 400 480 450]; CC, [300 500 480 590]; GG, [300 640 480 710]; ...
             'Q - C dq - G', [600 480 630 560]; 'aceleraciones = inv(M) (Q - C dq - G)', [720 400 760 560]; 'separar aceleraciones', [840 420 845 540]; ...
             'integrador dx', [960 420 990 450]; 'integrador dy_eje', [960 470 990 500]; 'integrador d_inclinacion', [960 520 990 550]; 'integrador d_largo_pata', [960 570 990 600]; ...
             'integrador x', [1060 420 1090 450]; 'integrador y_eje', [1060 470 1090 500]; 'integrador inclinacion', [1060 520 1090 550]; 'integrador largo_pata', [1060 570 1090 600]; ...
             'l minimo 1 mm', [1060 640 1090 660]; 'largo (no menor que 1 mm)', [1160 600 1190 640]; ...
             'bus cuerpo', [1300 380 1305 700]; 'cuerpo', [1400 530 1430 550] });
end

function fuerzas_Q(s0, u)
% Q_x = F_cx + F_x + F_esc ; Q_y = F_cy ; Q_phi = -(tau_izq + tau_der) + M_p + F_x l cos(phi) - b_pitch dphi
% Q_l = fuerza_pata + F_x sin(phi)     (trabajo virtual, manual seccion 5)
  s = u.sub(s0, 'Fuerzas generalizadas Q');
  for n = {'fuerza_contacto_x', 'fuerza_contacto_y', 'par_reductor_izq', 'par_reductor_der', 'fuerza_pata', 'F_x', 'M_p', 'F_escalon', 'inclinacion', 'largo_pata', 'd_inclinacion'}
    u.in(s, n{1});
  end
  u.sum(s, 'Q_x = F_cx + F_x + F_esc', '+++');
  u.L(s, 'fuerza_contacto_x/1', 'Q_x = F_cx + F_x + F_esc/1', ''); u.L(s, 'F_x/1', 'Q_x = F_cx + F_x + F_esc/2', ''); u.L(s, 'F_escalon/1', 'Q_x = F_cx + F_x + F_esc/3', '');
  u.trig(s, 'cos phi', 'cos'); u.trig(s, 'sin phi', 'sin'); u.L(s, 'inclinacion/1', 'cos phi/1', ''); u.L(s, 'inclinacion/1', 'sin phi/1', '');
  u.prod(s, 'F_x l cos phi', '***'); u.gain(s, 'amortiguamiento de cabeceo', 'par.cuerpo.amort_cabeceo');
  QP = 'Q_phi = -tau_izq - tau_der + M_p + F_x l cos - b dphi';
  u.sum(s, QP, '--++-');
  u.L(s, 'F_x/1', 'F_x l cos phi/1', ''); u.L(s, 'largo_pata/1', 'F_x l cos phi/2', ''); u.L(s, 'cos phi/1', 'F_x l cos phi/3', '');
  u.L(s, 'd_inclinacion/1', 'amortiguamiento de cabeceo/1', '');
  u.L(s, 'par_reductor_izq/1', [QP '/1'], ''); u.L(s, 'par_reductor_der/1', [QP '/2'], '');
  u.L(s, 'M_p/1', [QP '/3'], ''); u.L(s, 'F_x l cos phi/1', [QP '/4'], ''); u.L(s, 'amortiguamiento de cabeceo/1', [QP '/5'], '');
  u.prod(s, 'F_x sin phi', '**'); u.sum(s, 'Q_l = fuerza_pata + F_x sin', '++');
  u.L(s, 'F_x/1', 'F_x sin phi/1', ''); u.L(s, 'sin phi/1', 'F_x sin phi/2', '');
  u.L(s, 'fuerza_pata/1', 'Q_l = fuerza_pata + F_x sin/1', ''); u.L(s, 'F_x sin phi/1', 'Q_l = fuerza_pata + F_x sin/2', '');
  u.mux(s, 'Q = [Q_x; Q_y; Q_phi; Q_l]', '4'); u.out(s, 'Q');
  u.L(s, 'Q_x = F_cx + F_x + F_esc/1', 'Q = [Q_x; Q_y; Q_phi; Q_l]/1', 'Q_x'); u.L(s, 'fuerza_contacto_y/1', 'Q = [Q_x; Q_y; Q_phi; Q_l]/2', 'Q_y');
  u.L(s, [QP '/1'], 'Q = [Q_x; Q_y; Q_phi; Q_l]/3', 'Q_phi');
  u.L(s, 'Q_l = fuerza_pata + F_x sin/1', 'Q = [Q_x; Q_y; Q_phi; Q_l]/4', 'Q_l');
  u.L(s, 'Q = [Q_x; Q_y; Q_phi; Q_l]/1', 'Q/1', '');
end

function masa_M(s0, u)
% M = [m_t 0 m_b l cos  m_b sin ; 0 m_t -m_b l sin  m_b cos ; (sim) J_b + m_b l^2  0 ; (sim) 0 m_b]
  s = u.sub(s0, 'Matriz de masa M(q)');
  u.in(s, 'inclinacion'); u.in(s, 'largo_pata');
  u.trig(s, 'cos phi', 'cos'); u.trig(s, 'sin phi', 'sin'); u.L(s, 'inclinacion/1', 'cos phi/1', ''); u.L(s, 'inclinacion/1', 'sin phi/1', '');
  u.const(s, 'm_t = m_b + m_w', 'par.cuerpo.masa + par.rueda.masa_eje'); u.const(s, 'm_b', 'par.cuerpo.masa'); u.const(s, 'cero', '0');
  u.prod(s, 'l cos phi', '**'); u.prod(s, 'l sin phi', '**');
  u.L(s, 'largo_pata/1', 'l cos phi/1', ''); u.L(s, 'cos phi/1', 'l cos phi/2', ''); u.L(s, 'largo_pata/1', 'l sin phi/1', ''); u.L(s, 'sin phi/1', 'l sin phi/2', '');
  u.gain(s, 'M13 = m_b l cos', 'par.cuerpo.masa'); u.gain(s, 'M14 = m_b sin', 'par.cuerpo.masa');
  u.gain(s, 'M23 = -m_b l sin', '-par.cuerpo.masa'); u.gain(s, 'M24 = m_b cos', 'par.cuerpo.masa');
  u.L(s, 'l cos phi/1', 'M13 = m_b l cos/1', ''); u.L(s, 'sin phi/1', 'M14 = m_b sin/1', ''); u.L(s, 'l sin phi/1', 'M23 = -m_b l sin/1', ''); u.L(s, 'cos phi/1', 'M24 = m_b cos/1', '');
  u.mathf(s, 'l^2', 'square'); u.gain(s, 'm_b l^2', 'par.cuerpo.masa'); u.const(s, 'J_b', 'par.cuerpo.inercia'); u.sum(s, 'M33 = J_b + m_b l^2', '++');
  u.L(s, 'largo_pata/1', 'l^2/1', ''); u.L(s, 'l^2/1', 'm_b l^2/1', ''); u.L(s, 'J_b/1', 'M33 = J_b + m_b l^2/1', ''); u.L(s, 'm_b l^2/1', 'M33 = J_b + m_b l^2/2', '');
  for k = 1:4, u.mux(s, sprintf('columna %d', k), '4'); end
  u.mux(s, '16 elementos (por columnas)', '4'); u.reshape(s, 'M 4x4', '[4 4]'); u.out(s, 'M');
  % columna 1 = [m_t; 0; M13; M14]   columna 2 = [0; m_t; M23; M24]   columna 3 = [M13; M23; M33; 0]   columna 4 = [M14; M24; 0; m_b]
  u.L(s, 'm_t = m_b + m_w/1', 'columna 1/1', ''); u.L(s, 'cero/1', 'columna 1/2', ''); u.L(s, 'M13 = m_b l cos/1', 'columna 1/3', 'M13'); u.L(s, 'M14 = m_b sin/1', 'columna 1/4', 'M14');
  u.L(s, 'cero/1', 'columna 2/1', ''); u.L(s, 'm_t = m_b + m_w/1', 'columna 2/2', ''); u.L(s, 'M23 = -m_b l sin/1', 'columna 2/3', 'M23'); u.L(s, 'M24 = m_b cos/1', 'columna 2/4', 'M24');
  u.L(s, 'M13 = m_b l cos/1', 'columna 3/1', ''); u.L(s, 'M23 = -m_b l sin/1', 'columna 3/2', ''); u.L(s, 'M33 = J_b + m_b l^2/1', 'columna 3/3', 'M33'); u.L(s, 'cero/1', 'columna 3/4', '');
  u.L(s, 'M14 = m_b sin/1', 'columna 4/1', ''); u.L(s, 'M24 = m_b cos/1', 'columna 4/2', ''); u.L(s, 'cero/1', 'columna 4/3', ''); u.L(s, 'm_b/1', 'columna 4/4', '');
  for k = 1:4, u.L(s, sprintf('columna %d/1', k), sprintf('16 elementos (por columnas)/%d', k), ''); end
  u.L(s, '16 elementos (por columnas)/1', 'M 4x4/1', ''); u.L(s, 'M 4x4/1', 'M/1', '');
end

function coriolis_C(s0, u)
% C dq = m_b [ dphi (2 dl cos - dphi l sin) ; -dphi (2 dl sin + dphi l cos) ; 2 l dl dphi ; -l dphi^2 ]
  s = u.sub(s0, 'Coriolis y centrifugos C(q,dq) dq');
  u.in(s, 'inclinacion'); u.in(s, 'largo_pata'); u.in(s, 'd_inclinacion'); u.in(s, 'd_largo_pata');
  u.trig(s, 'cos phi', 'cos'); u.trig(s, 'sin phi', 'sin'); u.L(s, 'inclinacion/1', 'cos phi/1', ''); u.L(s, 'inclinacion/1', 'sin phi/1', '');
  u.gain(s, '2 dl', '2'); u.L(s, 'd_largo_pata/1', '2 dl/1', '');
  u.prod(s, '2 dl cos', '**'); u.prod(s, '2 dl sin', '**'); u.prod(s, 'dphi l sin', '***'); u.prod(s, 'dphi l cos', '***');
  u.L(s, '2 dl/1', '2 dl cos/1', ''); u.L(s, 'cos phi/1', '2 dl cos/2', ''); u.L(s, '2 dl/1', '2 dl sin/1', ''); u.L(s, 'sin phi/1', '2 dl sin/2', '');
  u.L(s, 'd_inclinacion/1', 'dphi l sin/1', ''); u.L(s, 'largo_pata/1', 'dphi l sin/2', ''); u.L(s, 'sin phi/1', 'dphi l sin/3', '');
  u.L(s, 'd_inclinacion/1', 'dphi l cos/1', ''); u.L(s, 'largo_pata/1', 'dphi l cos/2', ''); u.L(s, 'cos phi/1', 'dphi l cos/3', '');
  u.sum(s, '2 dl cos - dphi l sin', '+-'); u.sum(s, '2 dl sin + dphi l cos', '++');
  u.L(s, '2 dl cos/1', '2 dl cos - dphi l sin/1', ''); u.L(s, 'dphi l sin/1', '2 dl cos - dphi l sin/2', '');
  u.L(s, '2 dl sin/1', '2 dl sin + dphi l cos/1', ''); u.L(s, 'dphi l cos/1', '2 dl sin + dphi l cos/2', '');
  u.prod(s, 'x dphi (fila x)', '**'); u.prod(s, 'x dphi (fila y)', '**'); u.gain(s, 'C_x = m_b (.)', 'par.cuerpo.masa'); u.gain(s, 'C_y = -m_b (.)', '-par.cuerpo.masa');
  u.L(s, '2 dl cos - dphi l sin/1', 'x dphi (fila x)/1', ''); u.L(s, 'd_inclinacion/1', 'x dphi (fila x)/2', '');
  u.L(s, '2 dl sin + dphi l cos/1', 'x dphi (fila y)/1', ''); u.L(s, 'd_inclinacion/1', 'x dphi (fila y)/2', '');
  u.L(s, 'x dphi (fila x)/1', 'C_x = m_b (.)/1', ''); u.L(s, 'x dphi (fila y)/1', 'C_y = -m_b (.)/1', '');
  u.prod(s, 'l dl dphi', '***'); u.gain(s, 'C_phi = 2 m_b l dl dphi', '2*par.cuerpo.masa');
  u.L(s, 'largo_pata/1', 'l dl dphi/1', ''); u.L(s, 'd_largo_pata/1', 'l dl dphi/2', ''); u.L(s, 'd_inclinacion/1', 'l dl dphi/3', ''); u.L(s, 'l dl dphi/1', 'C_phi = 2 m_b l dl dphi/1', '');
  u.mathf(s, 'dphi^2', 'square'); u.prod(s, 'l dphi^2', '**'); u.gain(s, 'C_l = -m_b l dphi^2', '-par.cuerpo.masa');
  u.L(s, 'd_inclinacion/1', 'dphi^2/1', ''); u.L(s, 'largo_pata/1', 'l dphi^2/1', ''); u.L(s, 'dphi^2/1', 'l dphi^2/2', ''); u.L(s, 'l dphi^2/1', 'C_l = -m_b l dphi^2/1', '');
  u.mux(s, 'C dq (4)', '4'); u.out(s, 'C_dq');
  u.L(s, 'C_x = m_b (.)/1', 'C dq (4)/1', 'C_x'); u.L(s, 'C_y = -m_b (.)/1', 'C dq (4)/2', 'C_y');
  u.L(s, 'C_phi = 2 m_b l dl dphi/1', 'C dq (4)/3', 'C_phi'); u.L(s, 'C_l = -m_b l dphi^2/1', 'C dq (4)/4', 'C_l');
  u.L(s, 'C dq (4)/1', 'C_dq/1', '');
end

function gravedad_G(s0, u)
% G = [ g m_t sin(alpha) ; g m_t cos(alpha) ; g m_b l sin(alpha - phi) ; g m_b cos(alpha - phi) ]
  s = u.sub(s0, 'Gravedad G(q)');
  u.in(s, 'inclinacion'); u.in(s, 'largo_pata'); u.in(s, 'pendiente');
  u.trig(s, 'sin alpha', 'sin'); u.trig(s, 'cos alpha', 'cos'); u.L(s, 'pendiente/1', 'sin alpha/1', ''); u.L(s, 'pendiente/1', 'cos alpha/1', '');
  u.gain(s, 'G_x = g m_t sin alpha', 'par.g*(par.cuerpo.masa + par.rueda.masa_eje)'); u.gain(s, 'G_y = g m_t cos alpha', 'par.g*(par.cuerpo.masa + par.rueda.masa_eje)');
  u.L(s, 'sin alpha/1', 'G_x = g m_t sin alpha/1', ''); u.L(s, 'cos alpha/1', 'G_y = g m_t cos alpha/1', '');
  u.sum(s, 'alpha - phi', '+-'); u.trig(s, 'sin(alpha - phi)', 'sin'); u.trig(s, 'cos(alpha - phi)', 'cos');
  u.L(s, 'pendiente/1', 'alpha - phi/1', ''); u.L(s, 'inclinacion/1', 'alpha - phi/2', '');
  u.L(s, 'alpha - phi/1', 'sin(alpha - phi)/1', ''); u.L(s, 'alpha - phi/1', 'cos(alpha - phi)/1', '');
  u.prod(s, 'l sin(alpha - phi)', '**'); u.gain(s, 'G_phi = g m_b l sin(alpha - phi)', 'par.g*par.cuerpo.masa'); u.gain(s, 'G_l = g m_b cos(alpha - phi)', 'par.g*par.cuerpo.masa');
  u.L(s, 'largo_pata/1', 'l sin(alpha - phi)/1', ''); u.L(s, 'sin(alpha - phi)/1', 'l sin(alpha - phi)/2', '');
  u.L(s, 'l sin(alpha - phi)/1', 'G_phi = g m_b l sin(alpha - phi)/1', ''); u.L(s, 'cos(alpha - phi)/1', 'G_l = g m_b cos(alpha - phi)/1', '');
  u.mux(s, 'G (4)', '4'); u.out(s, 'G');
  u.L(s, 'G_x = g m_t sin alpha/1', 'G (4)/1', 'G_x'); u.L(s, 'G_y = g m_t cos alpha/1', 'G (4)/2', 'G_y');
  u.L(s, 'G_phi = g m_b l sin(alpha - phi)/1', 'G (4)/3', 'G_phi'); u.L(s, 'G_l = g m_b cos(alpha - phi)/1', 'G (4)/4', 'G_l');
  u.L(s, 'G (4)/1', 'G/1', '');
end

% ======================================================================================
function imu(s0, u)
% Fuerza especifica que mide el acelerometro (marco cuerpo): aceleracion del CoM -> punto de la IMU
% -> menos gravedad -> rotada al cuerpo (manual, seccion 9)
  s = u.sub(s0, 'IMU (fuerza especifica)');
  u.in(s, 'cuerpo'); u.in(s, 'perturbaciones');
  u.buss(s, 'movimiento del cuerpo', 'inclinacion,largo_pata,d_inclinacion,d_largo_pata,acel_x,acel_y_eje,acel_inclinacion,acel_largo');
  u.buss(s, 'pendiente del piso', 'pendiente');
  u.L(s, 'cuerpo/1', 'movimiento del cuerpo/1', ''); u.L(s, 'perturbaciones/1', 'pendiente del piso/1', '');
  acel_com(s, u); acel_imu(s, u); fuerza_especifica(s, u);
  A = 'Aceleracion del CoM'; B = 'Aceleracion en el punto de la IMU'; F = 'Fuerza especifica en marco cuerpo';
  u.L(s, 'movimiento del cuerpo/5', [A '/1'], ''); u.L(s, 'movimiento del cuerpo/6', [A '/2'], ''); u.L(s, 'movimiento del cuerpo/7', [A '/3'], ''); u.L(s, 'movimiento del cuerpo/8', [A '/4'], '');
  u.L(s, 'movimiento del cuerpo/1', [A '/5'], ''); u.L(s, 'movimiento del cuerpo/2', [A '/6'], ''); u.L(s, 'movimiento del cuerpo/3', [A '/7'], ''); u.L(s, 'movimiento del cuerpo/4', [A '/8'], '');
  u.L(s, [A '/1'], [B '/1'], 'acel_com_x'); u.L(s, [A '/2'], [B '/2'], 'acel_com_y');
  u.L(s, 'movimiento del cuerpo/1', [B '/3'], ''); u.L(s, 'movimiento del cuerpo/3', [B '/4'], ''); u.L(s, 'movimiento del cuerpo/7', [B '/5'], '');
  u.L(s, [B '/1'], [F '/1'], 'acel_imu_x'); u.L(s, [B '/2'], [F '/2'], 'acel_imu_y');
  u.L(s, 'movimiento del cuerpo/1', [F '/3'], ''); u.L(s, 'pendiente del piso/1', [F '/4'], '');
  u.busc(s, 'bus imu', '2'); u.out(s, 'imu');
  u.L(s, [F '/1'], 'bus imu/1', 'imu_fx'); u.L(s, [F '/2'], 'bus imu/2', 'imu_fy'); u.L(s, 'bus imu/1', 'imu/1', '');
end

function acel_com(s0, u)
% a_x = ddx + ddl sin + 2 dl dphi cos + l ddphi cos - l dphi^2 sin
% a_y = ddy + ddl cos - 2 dl dphi sin - l ddphi sin - l dphi^2 cos
  s = u.sub(s0, 'Aceleracion del CoM');
  for n = {'acel_x_eje', 'acel_y_eje', 'acel_inclinacion', 'acel_largo', 'inclinacion', 'largo_pata', 'd_inclinacion', 'd_largo_pata'}, u.in(s, n{1}); end
  u.trig(s, 'cos phi', 'cos'); u.trig(s, 'sin phi', 'sin'); u.L(s, 'inclinacion/1', 'cos phi/1', ''); u.L(s, 'inclinacion/1', 'sin phi/1', '');
  u.prod(s, 'ddl sin', '**'); u.prod(s, 'ddl cos', '**');
  u.L(s, 'acel_largo/1', 'ddl sin/1', ''); u.L(s, 'sin phi/1', 'ddl sin/2', ''); u.L(s, 'acel_largo/1', 'ddl cos/1', ''); u.L(s, 'cos phi/1', 'ddl cos/2', '');
  u.gain(s, '2 dl', '2'); u.L(s, 'd_largo_pata/1', '2 dl/1', '');
  u.prod(s, '2 dl dphi cos', '***'); u.prod(s, '2 dl dphi sin', '***');
  u.L(s, '2 dl/1', '2 dl dphi cos/1', ''); u.L(s, 'd_inclinacion/1', '2 dl dphi cos/2', ''); u.L(s, 'cos phi/1', '2 dl dphi cos/3', '');
  u.L(s, '2 dl/1', '2 dl dphi sin/1', ''); u.L(s, 'd_inclinacion/1', '2 dl dphi sin/2', ''); u.L(s, 'sin phi/1', '2 dl dphi sin/3', '');
  u.prod(s, 'l ddphi cos', '***'); u.prod(s, 'l ddphi sin', '***');
  u.L(s, 'largo_pata/1', 'l ddphi cos/1', ''); u.L(s, 'acel_inclinacion/1', 'l ddphi cos/2', ''); u.L(s, 'cos phi/1', 'l ddphi cos/3', '');
  u.L(s, 'largo_pata/1', 'l ddphi sin/1', ''); u.L(s, 'acel_inclinacion/1', 'l ddphi sin/2', ''); u.L(s, 'sin phi/1', 'l ddphi sin/3', '');
  u.mathf(s, 'dphi^2', 'square'); u.L(s, 'd_inclinacion/1', 'dphi^2/1', '');
  u.prod(s, 'l dphi^2 sin', '***'); u.prod(s, 'l dphi^2 cos', '***');
  u.L(s, 'largo_pata/1', 'l dphi^2 sin/1', ''); u.L(s, 'dphi^2/1', 'l dphi^2 sin/2', ''); u.L(s, 'sin phi/1', 'l dphi^2 sin/3', '');
  u.L(s, 'largo_pata/1', 'l dphi^2 cos/1', ''); u.L(s, 'dphi^2/1', 'l dphi^2 cos/2', ''); u.L(s, 'cos phi/1', 'l dphi^2 cos/3', '');
  u.sum(s, 'a_x del CoM', '++++-'); u.sum(s, 'a_y del CoM', '++---');
  u.L(s, 'acel_x_eje/1', 'a_x del CoM/1', ''); u.L(s, 'ddl sin/1', 'a_x del CoM/2', ''); u.L(s, '2 dl dphi cos/1', 'a_x del CoM/3', ''); u.L(s, 'l ddphi cos/1', 'a_x del CoM/4', ''); u.L(s, 'l dphi^2 sin/1', 'a_x del CoM/5', '');
  u.L(s, 'acel_y_eje/1', 'a_y del CoM/1', ''); u.L(s, 'ddl cos/1', 'a_y del CoM/2', ''); u.L(s, '2 dl dphi sin/1', 'a_y del CoM/3', ''); u.L(s, 'l ddphi sin/1', 'a_y del CoM/4', ''); u.L(s, 'l dphi^2 cos/1', 'a_y del CoM/5', '');
  u.out(s, 'a_x'); u.out(s, 'a_y'); u.L(s, 'a_x del CoM/1', 'a_x/1', ''); u.L(s, 'a_y del CoM/1', 'a_y/1', '');
end

function acel_imu(s0, u)
% brazo de la IMU en el marco del piso: dw = R(phi) [d_ix; d_iy]
% a_imu = a_com + ddphi [dw_y; -dw_x] - dphi^2 [dw_x; dw_y]
  s = u.sub(s0, 'Aceleracion en el punto de la IMU');
  for n = {'a_com_x', 'a_com_y', 'inclinacion', 'd_inclinacion', 'acel_inclinacion'}, u.in(s, n{1}); end
  u.trig(s, 'cos phi', 'cos'); u.trig(s, 'sin phi', 'sin'); u.L(s, 'inclinacion/1', 'cos phi/1', ''); u.L(s, 'inclinacion/1', 'sin phi/1', '');
  u.gain(s, 'd_ix cos', 'par.sensores.imu_dx'); u.gain(s, 'd_iy sin', 'par.sensores.imu_dy'); u.gain(s, 'd_ix sin', 'par.sensores.imu_dx'); u.gain(s, 'd_iy cos', 'par.sensores.imu_dy');
  u.L(s, 'cos phi/1', 'd_ix cos/1', ''); u.L(s, 'sin phi/1', 'd_iy sin/1', ''); u.L(s, 'sin phi/1', 'd_ix sin/1', ''); u.L(s, 'cos phi/1', 'd_iy cos/1', '');
  u.sum(s, 'dw_x = d_ix cos + d_iy sin', '++'); u.sum(s, 'dw_y = -d_ix sin + d_iy cos', '-+');
  u.L(s, 'd_ix cos/1', 'dw_x = d_ix cos + d_iy sin/1', ''); u.L(s, 'd_iy sin/1', 'dw_x = d_ix cos + d_iy sin/2', '');
  u.L(s, 'd_ix sin/1', 'dw_y = -d_ix sin + d_iy cos/1', ''); u.L(s, 'd_iy cos/1', 'dw_y = -d_ix sin + d_iy cos/2', '');
  u.mathf(s, 'dphi^2', 'square'); u.L(s, 'd_inclinacion/1', 'dphi^2/1', '');
  u.prod(s, 'ddphi dw_y', '**'); u.prod(s, 'ddphi dw_x', '**'); u.prod(s, 'dphi^2 dw_x', '**'); u.prod(s, 'dphi^2 dw_y', '**');
  u.L(s, 'acel_inclinacion/1', 'ddphi dw_y/1', ''); u.L(s, 'dw_y = -d_ix sin + d_iy cos/1', 'ddphi dw_y/2', 'dw_y');
  u.L(s, 'acel_inclinacion/1', 'ddphi dw_x/1', ''); u.L(s, 'dw_x = d_ix cos + d_iy sin/1', 'ddphi dw_x/2', 'dw_x');
  u.L(s, 'dphi^2/1', 'dphi^2 dw_x/1', ''); u.L(s, 'dw_x = d_ix cos + d_iy sin/1', 'dphi^2 dw_x/2', '');
  u.L(s, 'dphi^2/1', 'dphi^2 dw_y/1', ''); u.L(s, 'dw_y = -d_ix sin + d_iy cos/1', 'dphi^2 dw_y/2', '');
  AX = 'a_imu_x = a_x + ddphi dw_y - dphi^2 dw_x'; AY = 'a_imu_y = a_y - ddphi dw_x - dphi^2 dw_y';
  u.sum(s, AX, '++-'); u.sum(s, AY, '+--');
  u.L(s, 'a_com_x/1', [AX '/1'], ''); u.L(s, 'ddphi dw_y/1', [AX '/2'], ''); u.L(s, 'dphi^2 dw_x/1', [AX '/3'], '');
  u.L(s, 'a_com_y/1', [AY '/1'], ''); u.L(s, 'ddphi dw_x/1', [AY '/2'], ''); u.L(s, 'dphi^2 dw_y/1', [AY '/3'], '');
  u.out(s, 'a_imu_x'); u.out(s, 'a_imu_y');
  u.L(s, [AX '/1'], 'a_imu_x/1', ''); u.L(s, [AY '/1'], 'a_imu_y/1', '');
end

function fuerza_especifica(s0, u)
% f = a_imu - g_vec,  g_vec = g [-sin alpha; -cos alpha] ;  f_cuerpo = R(-phi) f
  s = u.sub(s0, 'Fuerza especifica en marco cuerpo');
  for n = {'a_imu_x', 'a_imu_y', 'inclinacion', 'pendiente'}, u.in(s, n{1}); end
  u.trig(s, 'sin alpha', 'sin'); u.trig(s, 'cos alpha', 'cos'); u.L(s, 'pendiente/1', 'sin alpha/1', ''); u.L(s, 'pendiente/1', 'cos alpha/1', '');
  u.gain(s, 'g sin alpha', 'par.g'); u.gain(s, 'g cos alpha', 'par.g'); u.L(s, 'sin alpha/1', 'g sin alpha/1', ''); u.L(s, 'cos alpha/1', 'g cos alpha/1', '');
  FX = 'f_x piso = a_x + g sin alpha'; FY = 'f_y piso = a_y + g cos alpha';
  u.sum(s, FX, '++'); u.sum(s, FY, '++');
  u.L(s, 'a_imu_x/1', [FX '/1'], ''); u.L(s, 'g sin alpha/1', [FX '/2'], '');
  u.L(s, 'a_imu_y/1', [FY '/1'], ''); u.L(s, 'g cos alpha/1', [FY '/2'], '');
  u.trig(s, 'cos phi', 'cos'); u.trig(s, 'sin phi', 'sin'); u.L(s, 'inclinacion/1', 'cos phi/1', ''); u.L(s, 'inclinacion/1', 'sin phi/1', '');
  u.prod(s, 'cos f_x', '**'); u.prod(s, 'sin f_y', '**'); u.prod(s, 'sin f_x', '**'); u.prod(s, 'cos f_y', '**');
  u.L(s, 'cos phi/1', 'cos f_x/1', ''); u.L(s, [FX '/1'], 'cos f_x/2', 'f_x_piso');
  u.L(s, 'sin phi/1', 'sin f_y/1', ''); u.L(s, [FY '/1'], 'sin f_y/2', 'f_y_piso');
  u.L(s, 'sin phi/1', 'sin f_x/1', ''); u.L(s, [FX '/1'], 'sin f_x/2', '');
  u.L(s, 'cos phi/1', 'cos f_y/1', ''); u.L(s, [FY '/1'], 'cos f_y/2', '');
  u.sum(s, 'fb_x = cos f_x - sin f_y', '+-'); u.sum(s, 'fb_y = sin f_x + cos f_y', '++');
  u.L(s, 'cos f_x/1', 'fb_x = cos f_x - sin f_y/1', ''); u.L(s, 'sin f_y/1', 'fb_x = cos f_x - sin f_y/2', '');
  u.L(s, 'sin f_x/1', 'fb_y = sin f_x + cos f_y/1', ''); u.L(s, 'cos f_y/1', 'fb_y = sin f_x + cos f_y/2', '');
  u.out(s, 'fb_x'); u.out(s, 'fb_y'); u.L(s, 'fb_x = cos f_x - sin f_y/1', 'fb_x/1', ''); u.L(s, 'fb_y = sin f_x + cos f_y/1', 'fb_y/1', '');
end

% ======================================================================================
function colector(s0, u)
% Junta los 20 estados y las 18 salidas en buses con nombre, en el mismo orden que robot_planta.m
  s = u.sub(s0, 'Estados y salidas con nombre');
  for n = {'cuerpo', 'ruedas', 'motores', 'pata', 'bateria', 'contacto', 'piso', 'imu'}, u.in(s, n{1}); end
  u.buss(s, 'del cuerpo', 'x,y_eje,inclinacion,largo_pata,dx,dy_eje,d_inclinacion,d_largo_pata,acel_x,acel_y_eje,acel_inclinacion,acel_largo');
  u.buss(s, 'de las ruedas', 'ang_rueda_izq,vel_rueda_izq,ang_rueda_der,vel_rueda_der');
  u.buss(s, 'de los motores', 'par_reductor_izq,par_reductor_der,corriente_izq,corriente_der');
  u.buss(s, 'de la pata', 'par_servo,angulo_servo,largo_mecanismo,d_largo_mecanismo');
  u.buss(s, 'de la bateria', 'tension_bus');
  u.buss(s, 'del contacto', 'normal,fuerza_piso_izq,fuerza_piso_der,desliza');
  u.buss(s, 'del piso', 'penetracion');
  u.buss(s, 'de la IMU', 'imu_fx,imu_fy');
  u.L(s, 'cuerpo/1', 'del cuerpo/1', ''); u.L(s, 'ruedas/1', 'de las ruedas/1', ''); u.L(s, 'motores/1', 'de los motores/1', ''); u.L(s, 'pata/1', 'de la pata/1', '');
  u.L(s, 'bateria/1', 'de la bateria/1', ''); u.L(s, 'contacto/1', 'del contacto/1', ''); u.L(s, 'piso/1', 'del piso/1', ''); u.L(s, 'imu/1', 'de la IMU/1', '');
  % rotor = N x rueda (reductor rigido)
  nr = {'ang_rotor_izq', 'vel_rotor_izq', 'ang_rotor_der', 'vel_rotor_der'};
  for k = 1:4, u.gain(s, [nr{k} ' = N x rueda'], 'par.motor.relacion'); u.L(s, sprintf('de las ruedas/%d', k), [nr{k} ' = N x rueda/1'], ''); end
  u.busc(s, 'estados (20)', '20'); u.busc(s, 'salidas (18)', '18'); u.out(s, 'estados'); u.out(s, 'salidas');
  for k = 1:8, u.L(s, sprintf('del cuerpo/%d', k), sprintf('estados (20)/%d', k), ''); end
  for k = 1:4, u.L(s, sprintf('de las ruedas/%d', k), sprintf('estados (20)/%d', 8 + k), ''); end
  for k = 1:4, u.L(s, [nr{k} ' = N x rueda/1'], sprintf('estados (20)/%d', 12 + k), nr{k}); end
  u.L(s, 'de los motores/3', 'estados (20)/17', ''); u.L(s, 'de los motores/4', 'estados (20)/18', '');
  u.L(s, 'de la pata/3', 'estados (20)/19', ''); u.L(s, 'de la pata/4', 'estados (20)/20', '');
  for k = 1:4, u.L(s, sprintf('del cuerpo/%d', 8 + k), sprintf('salidas (18)/%d', k), ''); end
  for k = 1:4, u.L(s, sprintf('del contacto/%d', k), sprintf('salidas (18)/%d', 4 + k), ''); end
  u.L(s, 'de los motores/1', 'salidas (18)/9', ''); u.L(s, 'de los motores/2', 'salidas (18)/10', '');
  u.L(s, 'de la pata/1', 'salidas (18)/11', ''); u.L(s, 'de la pata/2', 'salidas (18)/12', '');
  u.L(s, 'de los motores/3', 'salidas (18)/13', ''); u.L(s, 'de los motores/4', 'salidas (18)/14', '');
  u.L(s, 'de la bateria/1', 'salidas (18)/15', ''); u.L(s, 'de la IMU/1', 'salidas (18)/16', ''); u.L(s, 'de la IMU/2', 'salidas (18)/17', '');
  u.L(s, 'del piso/1', 'salidas (18)/18', '');
  u.L(s, 'estados (20)/1', 'estados/1', ''); u.L(s, 'salidas (18)/1', 'salidas/1', '');
end
