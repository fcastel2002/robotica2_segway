function bloques_controlador(mdl, u)
%BLOQUES_CONTROLADOR  Subsistema Controlador de robot_segway_bloques: la misma ley discreta que
%   robot_controlador.m pero con bloques nativos (Unit Delay, Discrete Transfer Fcn, Rate Limiter,
%   1-D Lookup Table, Dot Product...). Todo corre a Ts.
%   medidas = [giroscopo; acel_x; acel_y; encoder_izq; encoder_der]   referencias = [x_ref; l_ref]
%   comandos = [tension_izq; tension_der; angulo_servo_ref]
%   estimaciones = [inclinacion_est; x_est; dx_est; largo_pata_est; par_rueda_cmd; tension_saturada; en_vuelo]
  s = [mdl '/Controlador'];
  u.in(s, 'medidas'); u.in(s, 'referencias');
  u.demux(s, 'separar medidas', '5'); u.demux(s, 'separar referencias', '2');
  u.L(s, 'medidas/1', 'separar medidas/1', ''); u.L(s, 'referencias/1', 'separar referencias/1', '');
  odometria(s, u); inclinacion(s, u); lqr_programado(s, u); tension(s, u); consigna_servo(s, u);
  OD = 'Odometria (encoders)'; IN = 'Inclinacion (filtro complementario)'; LQ = 'LQR programado por largo de pata';
  TE = 'Par de rueda a tension de motores'; CS = 'Consigna del servo';
  u.L(s, 'separar medidas/4', [OD '/1'], 'encoder_izq'); u.L(s, 'separar medidas/5', [OD '/2'], 'encoder_der');
  u.L(s, 'separar medidas/1', [IN '/1'], 'giroscopo'); u.L(s, 'separar medidas/2', [IN '/2'], 'acel_x'); u.L(s, 'separar medidas/3', [IN '/3'], 'acel_y');
  u.L(s, [OD '/3'], [IN '/4'], 'acel_base_est');
  u.L(s, [OD '/1'], [LQ '/1'], 'x_est'); u.L(s, 'separar referencias/1', [LQ '/2'], 'x_ref'); u.L(s, [IN '/1'], [LQ '/3'], 'inclinacion_est');
  u.L(s, [OD '/2'], [LQ '/4'], 'dx_est'); u.L(s, 'separar medidas/1', [LQ '/5'], ''); u.L(s, [CS '/2'], [LQ '/6'], 'angulo_servo_anterior');
  u.L(s, [LQ '/1'], [TE '/1'], 'par_rueda_cmd'); u.L(s, [OD '/4'], [TE '/2'], 'vel_ruedas_est');
  u.L(s, 'separar referencias/2', [CS '/1'], 'l_ref');
  u.mux(s, 'comandos (3)', '3'); u.mux(s, 'estimaciones (7)', '7'); u.out(s, 'comandos'); u.out(s, 'estimaciones');
  u.L(s, [TE '/1'], 'comandos (3)/1', 'tension_izq'); u.L(s, [TE '/2'], 'comandos (3)/2', 'tension_der'); u.L(s, [CS '/1'], 'comandos (3)/3', 'angulo_servo_ref');
  u.L(s, [IN '/1'], 'estimaciones (7)/1', ''); u.L(s, [OD '/1'], 'estimaciones (7)/2', ''); u.L(s, [OD '/2'], 'estimaciones (7)/3', '');
  u.L(s, [LQ '/2'], 'estimaciones (7)/4', 'largo_pata_est'); u.L(s, [LQ '/1'], 'estimaciones (7)/5', '');
  u.L(s, [TE '/3'], 'estimaciones (7)/6', 'tension_saturada'); u.L(s, [IN '/2'], 'estimaciones (7)/7', 'en_vuelo');
  u.L(s, 'comandos (3)/1', 'comandos/1', ''); u.L(s, 'estimaciones (7)/1', 'estimaciones/1', '');
  % ---- distribucion a mano: medidas -> estimadores -> LQR -> tension ----
  u.pos(s, { 'medidas', [30 95 60 115]; 'separar medidas', [120 40 125 170]; 'referencias', [30 300 60 320]; 'separar referencias', [120 280 125 340]; ...
             OD, [260 40 440 110]; IN, [260 200 440 300]; CS, [260 380 440 420]; LQ, [600 150 800 300]; TE, [920 180 1100 240]; ...
             'comandos (3)', [1220 160 1225 260]; 'comandos', [1300 200 1330 220]; 'estimaciones (7)', [1220 340 1225 500]; 'estimaciones', [1300 410 1330 430] });
end

function odometria(s0, u)
% d_ang = (cuentas - cuentas anteriores) 2 pi / CPR   (0 si no hay encoder)
% w_est = pasabajos(d_ang / Ts) a fc_vel ; x_est = x_est + R media(d_ang) ; dx_est = R media(w_est)
% a_est = pasabajos((dx_est - dx anterior) / Ts) a fc_acel
  s = u.sub(s0, 'Odometria (encoders)');
  u.in(s, 'encoder_izq'); u.in(s, 'encoder_der');
  u.mux(s, 'cuentas (izq, der)', '2'); u.L(s, 'encoder_izq/1', 'cuentas (izq, der)/1', ''); u.L(s, 'encoder_der/1', 'cuentas (izq, der)/2', '');
  u.ud(s, 'cuentas anteriores', 'encoders_iniciales'); u.sum(s, 'incremento de cuentas', '+-'); u.gain(s, 'radianes por cuenta', '2*pi/par.sensores.CPR');
  u.L(s, 'cuentas (izq, der)/1', 'cuentas anteriores/1', 'cuentas'); u.L(s, 'cuentas (izq, der)/1', 'incremento de cuentas/1', '');
  u.L(s, 'cuentas anteriores/1', 'incremento de cuentas/2', ''); u.L(s, 'incremento de cuentas/1', 'radianes por cuenta/1', '');
  u.const(s, 'encoder habilitado', 'par.sensores.encoder'); u.const(s, 'cero (2)', '[0;0]'); u.sw(s, 'si hay encoder', 'u2 > Threshold', '0.5');
  u.L(s, 'radianes por cuenta/1', 'si hay encoder/1', ''); u.L(s, 'encoder habilitado/1', 'si hay encoder/2', ''); u.L(s, 'cero (2)/1', 'si hay encoder/3', '');
  u.dtf(s, 'pasabajos de velocidad (fc_vel)', '[(1-par.control.a_vel)/Ts 0]', '[1 -par.control.a_vel]');   % y = a y_ant + (1-a) u  (sin retardo)
  u.L(s, 'si hay encoder/1', 'pasabajos de velocidad (fc_vel)/1', 'd_angulo_ruedas');
  u.sumel(s, 'suma izq + der'); u.gain(s, 'R entre 2 (promedio por radio)', 'par.rueda.radio/2'); u.ud(s, 'x anterior', '0'); u.sum(s, 'x_est = x anterior + avance', '++');
  u.L(s, 'si hay encoder/1', 'suma izq + der/1', ''); u.L(s, 'suma izq + der/1', 'R entre 2 (promedio por radio)/1', '');
  u.L(s, 'R entre 2 (promedio por radio)/1', 'x_est = x anterior + avance/1', 'avance'); u.L(s, 'x anterior/1', 'x_est = x anterior + avance/2', '');
  u.L(s, 'x_est = x anterior + avance/1', 'x anterior/1', 'x_est');
  u.sumel(s, 'suma de velocidades'); u.gain(s, 'R entre 2', 'par.rueda.radio/2');
  u.L(s, 'pasabajos de velocidad (fc_vel)/1', 'suma de velocidades/1', 'vel_ruedas_est'); u.L(s, 'suma de velocidades/1', 'R entre 2/1', '');
  u.ud(s, 'dx anterior', '0'); u.sum(s, 'dx - dx anterior', '+-'); u.dtf(s, 'derivada filtrada (fc_acel)', '[(1-par.control.a_acel)/Ts 0]', '[1 -par.control.a_acel]');
  u.L(s, 'R entre 2/1', 'dx anterior/1', 'dx_est'); u.L(s, 'R entre 2/1', 'dx - dx anterior/1', ''); u.L(s, 'dx anterior/1', 'dx - dx anterior/2', '');
  u.L(s, 'dx - dx anterior/1', 'derivada filtrada (fc_acel)/1', '');
  u.out(s, 'x_est'); u.out(s, 'dx_est'); u.out(s, 'acel_est'); u.out(s, 'vel_ruedas_est');
  u.L(s, 'x_est = x anterior + avance/1', 'x_est/1', ''); u.L(s, 'R entre 2/1', 'dx_est/1', '');
  u.L(s, 'derivada filtrada (fc_acel)/1', 'acel_est/1', 'acel_est'); u.L(s, 'pasabajos de velocidad (fc_vel)/1', 'vel_ruedas_est/1', '');
end

function inclinacion(s0, u)
% en_vuelo = | |f| - g | > umbral  ->  k = 0 (solo giroscopo) ; si no k = k_comp
% f corregida = f - R(phi) a_base ; phi_acel = atan2(-f_x, f_y)
% phi_est = (1 - k) (phi anterior + giro Ts) + k phi_acel
  s = u.sub(s0, 'Inclinacion (filtro complementario)');
  u.in(s, 'giroscopo'); u.in(s, 'acel_x'); u.in(s, 'acel_y'); u.in(s, 'acel_base_est');
  u.mathf(s, 'modulo de f', 'hypot'); u.L(s, 'acel_x/1', 'modulo de f/1', ''); u.L(s, 'acel_y/1', 'modulo de f/2', '');
  u.const(s, 'g', 'par.g'); u.sum(s, '|f| - g', '+-'); u.abs(s, 'valor absoluto'); u.cmpc(s, 'en vuelo si supera el umbral', '>', 'par.control.umbral_vuelo'); u.dtc(s, 'vuelo 0 o 1');
  u.L(s, 'modulo de f/1', '|f| - g/1', ''); u.L(s, 'g/1', '|f| - g/2', ''); u.L(s, '|f| - g/1', 'valor absoluto/1', '');
  u.L(s, 'valor absoluto/1', 'en vuelo si supera el umbral/1', ''); u.L(s, 'en vuelo si supera el umbral/1', 'vuelo 0 o 1/1', '');
  u.const(s, 'k comp', 'par.control.k_comp'); u.const(s, 'cero', '0'); u.sw(s, 'k = 0 en vuelo', 'u2 > Threshold', '0.5');
  u.L(s, 'cero/1', 'k = 0 en vuelo/1', ''); u.L(s, 'vuelo 0 o 1/1', 'k = 0 en vuelo/2', 'en_vuelo'); u.L(s, 'k comp/1', 'k = 0 en vuelo/3', '');
  u.ud(s, 'inclinacion anterior', 'inclinacion_inicial_est');
  u.trig(s, 'cos phi', 'cos'); u.trig(s, 'sin phi', 'sin'); u.L(s, 'inclinacion anterior/1', 'cos phi/1', 'phi_anterior'); u.L(s, 'inclinacion anterior/1', 'sin phi/1', '');
  u.prod(s, 'cos phi a_base', '**'); u.prod(s, 'sin phi a_base', '**'); u.sum(s, 'f_x corregida', '+-'); u.sum(s, 'f_y corregida', '+-');
  u.L(s, 'cos phi/1', 'cos phi a_base/1', ''); u.L(s, 'acel_base_est/1', 'cos phi a_base/2', ''); u.L(s, 'sin phi/1', 'sin phi a_base/1', ''); u.L(s, 'acel_base_est/1', 'sin phi a_base/2', '');
  u.L(s, 'acel_x/1', 'f_x corregida/1', ''); u.L(s, 'cos phi a_base/1', 'f_x corregida/2', ''); u.L(s, 'acel_y/1', 'f_y corregida/1', ''); u.L(s, 'sin phi a_base/1', 'f_y corregida/2', '');
  u.neg(s, '-f_x'); u.trig(s, 'atan2(-f_x, f_y)', 'atan2');
  u.L(s, 'f_x corregida/1', '-f_x/1', ''); u.L(s, '-f_x/1', 'atan2(-f_x, f_y)/1', ''); u.L(s, 'f_y corregida/1', 'atan2(-f_x, f_y)/2', '');
  u.gain(s, 'giro x Ts', 'Ts'); u.sum(s, 'phi anterior + giro Ts', '++');
  u.L(s, 'giroscopo/1', 'giro x Ts/1', ''); u.L(s, 'inclinacion anterior/1', 'phi anterior + giro Ts/1', ''); u.L(s, 'giro x Ts/1', 'phi anterior + giro Ts/2', '');
  u.const(s, 'uno', '1'); u.sum(s, '1 - k', '+-'); u.prod(s, '(1 - k) x integracion del giro', '**'); u.prod(s, 'k x acelerometro', '**'); u.sum(s, 'inclinacion estimada', '++');
  u.L(s, 'uno/1', '1 - k/1', ''); u.L(s, 'k = 0 en vuelo/1', '1 - k/2', 'k');
  u.L(s, '1 - k/1', '(1 - k) x integracion del giro/1', ''); u.L(s, 'phi anterior + giro Ts/1', '(1 - k) x integracion del giro/2', '');
  u.L(s, 'k = 0 en vuelo/1', 'k x acelerometro/1', ''); u.L(s, 'atan2(-f_x, f_y)/1', 'k x acelerometro/2', 'inclinacion_acel');
  u.L(s, '(1 - k) x integracion del giro/1', 'inclinacion estimada/1', ''); u.L(s, 'k x acelerometro/1', 'inclinacion estimada/2', '');
  u.L(s, 'inclinacion estimada/1', 'inclinacion anterior/1', 'inclinacion_est');
  u.out(s, 'inclinacion_est'); u.out(s, 'en_vuelo');
  u.L(s, 'inclinacion estimada/1', 'inclinacion_est/1', ''); u.L(s, 'vuelo 0 o 1/1', 'en_vuelo/1', '');
end

function lqr_programado(s0, u)
% l_est = tabla theta -> l (consigna anterior del servo) ; K(l) = K1 + K2 l
% par de rueda = -K(l) . [x_est - x_ref ; phi_est ; dx_est ; dphi_est]
  s = u.sub(s0, 'LQR programado por largo de pata');
  for n = {'x_est', 'x_ref', 'inclinacion_est', 'dx_est', 'giroscopo', 'angulo_servo_anterior'}, u.in(s, n{1}); end
  u.lut(s, 'largo de pata segun angulo del servo', 'par.pata.tabla_theta_inv', 'par.pata.tabla_l_inv');
  u.L(s, 'angulo_servo_anterior/1', 'largo de pata segun angulo del servo/1', '');
  u.sat(s, 'dentro del rango del ajuste', 'par.control.l_min', 'par.control.l_max');
  u.L(s, 'largo de pata segun angulo del servo/1', 'dentro del rango del ajuste/1', 'largo_pata_est');
  u.gain(s, 'K2 x l', 'par.control.K2(:)'); u.const(s, 'K1', 'par.control.K1(:)'); u.sum(s, 'K(l) = K1 + K2 l', '++');   % K como columnas, para el Dot Product
  u.L(s, 'dentro del rango del ajuste/1', 'K2 x l/1', ''); u.L(s, 'K1/1', 'K(l) = K1 + K2 l/1', ''); u.L(s, 'K2 x l/1', 'K(l) = K1 + K2 l/2', '');
  u.sum(s, 'error de posicion', '+-'); u.mux(s, 'error = [x - x_ref; phi; dx; dphi]', '4');
  u.L(s, 'x_est/1', 'error de posicion/1', ''); u.L(s, 'x_ref/1', 'error de posicion/2', '');
  u.L(s, 'error de posicion/1', 'error = [x - x_ref; phi; dx; dphi]/1', ''); u.L(s, 'inclinacion_est/1', 'error = [x - x_ref; phi; dx; dphi]/2', '');
  u.L(s, 'dx_est/1', 'error = [x - x_ref; phi; dx; dphi]/3', ''); u.L(s, 'giroscopo/1', 'error = [x - x_ref; phi; dx; dphi]/4', '');
  u.dot(s, 'K . error'); u.neg(s, 'par = -K . error');
  u.L(s, 'K(l) = K1 + K2 l/1', 'K . error/1', 'K'); u.L(s, 'error = [x - x_ref; phi; dx; dphi]/1', 'K . error/2', 'error');
  u.L(s, 'K . error/1', 'par = -K . error/1', '');
  u.out(s, 'par_rueda'); u.out(s, 'largo_pata_est');
  u.L(s, 'par = -K . error/1', 'par_rueda/1', ''); u.L(s, 'largo de pata segun angulo del servo/1', 'largo_pata_est/1', '');
end

function tension(s0, u)
% por motor: V = R (tau/2) / (Kt N eta) + Ke N w_est ; saturada a +-V_bat
  s = u.sub(s0, 'Par de rueda a tension de motores');
  u.in(s, 'par_rueda'); u.in(s, 'vel_ruedas_est');
  u.gain(s, 'R entre (2 Kt N eta)', 'par.motor.R/(2*par.motor.Kt*par.motor.relacion*par.motor.eta)');
  u.gain(s, 'fcem Ke N w', 'par.motor.Ke*par.motor.relacion'); u.sum(s, 'tension pedida (izq, der)', '++');
  u.L(s, 'par_rueda/1', 'R entre (2 Kt N eta)/1', ''); u.L(s, 'vel_ruedas_est/1', 'fcem Ke N w/1', '');
  u.L(s, 'R entre (2 Kt N eta)/1', 'tension pedida (izq, der)/1', 'por_el_par'); u.L(s, 'fcem Ke N w/1', 'tension pedida (izq, der)/2', 'por_la_fcem');
  u.abs(s, '|V|'); u.cmpc(s, 'supera V_bat', '>', 'par.bateria.V'); u.logic(s, 'alguna satura', 'OR', '1'); u.dtc(s, 'saturado 0 o 1');
  u.L(s, 'tension pedida (izq, der)/1', '|V|/1', 'tension_pedida'); u.L(s, '|V|/1', 'supera V_bat/1', ''); u.L(s, 'supera V_bat/1', 'alguna satura/1', ''); u.L(s, 'alguna satura/1', 'saturado 0 o 1/1', '');
  u.sat(s, 'limitar a la bateria', '-par.bateria.V', 'par.bateria.V'); u.demux(s, 'izq y der', '2');
  u.L(s, 'tension pedida (izq, der)/1', 'limitar a la bateria/1', ''); u.L(s, 'limitar a la bateria/1', 'izq y der/1', 'tension');
  u.out(s, 'tension_izq'); u.out(s, 'tension_der'); u.out(s, 'saturado');
  u.L(s, 'izq y der/1', 'tension_izq/1', ''); u.L(s, 'izq y der/2', 'tension_der/1', ''); u.L(s, 'saturado 0 o 1/1', 'saturado/1', '');
end

function consigna_servo(s0, u)
% theta objetivo = tabla l -> theta (l_ref acotado) ; consigna con limite de velocidad 0.8 w_vacio ; acotada al rango del servo
  s = u.sub(s0, 'Consigna del servo');
  u.in(s, 'l_ref');
  u.sat(s, 'largo dentro de la carrera', 'par.pata.l_min', 'par.pata.l_max');
  u.lut(s, 'angulo objetivo theta(l_ref)', 'par.pata.tabla_l', 'par.pata.tabla_theta');
  u.ratelim(s, 'limitador de velocidad del servo', '0.8*par.servo.w_vacio', 'angulo_servo_inicial');
  u.sat(s, 'rango del servo', 'par.servo.theta_min', 'par.servo.theta_max');
  u.ud(s, 'consigna anterior', 'angulo_servo_inicial');
  u.L(s, 'l_ref/1', 'largo dentro de la carrera/1', ''); u.L(s, 'largo dentro de la carrera/1', 'angulo objetivo theta(l_ref)/1', 'l_ref_acotado');
  u.L(s, 'angulo objetivo theta(l_ref)/1', 'limitador de velocidad del servo/1', 'angulo_objetivo');
  u.L(s, 'limitador de velocidad del servo/1', 'rango del servo/1', ''); u.L(s, 'rango del servo/1', 'consigna anterior/1', 'angulo_servo_ref');
  u.out(s, 'angulo_servo_ref'); u.out(s, 'angulo_servo_anterior');
  u.L(s, 'rango del servo/1', 'angulo_servo_ref/1', ''); u.L(s, 'consigna anterior/1', 'angulo_servo_anterior/1', '');
end
