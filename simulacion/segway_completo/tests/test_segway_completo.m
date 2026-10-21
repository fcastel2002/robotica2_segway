function tests = test_segway_completo
%TEST_SEGWAY_COMPLETO  Comprueba el modelo completo del Segway en Simulink.
%
%   Lo que se verifica, en orden de importancia:
%     1. que el diagrama reproduzca el modelo matematico de referencia
%     2. que los cuatro motores hagan lo que tienen que hacer
%     3. que los sensores ideales sean transparentes
%     4. que la compensacion de la postura cambie lo que tiene que cambiar
%
%   Correr:  runtests('test_segway_completo')
    tests = functiontests(localfunctions);
end

% =====================================================================
function setupOnce(tc)
    aqui = fileparts(fileparts(mfilename('fullpath')));
    raiz = fileparts(fileparts(aqui));
    addpath(fullfile(raiz, 'modelado', 'parametros'));
    addpath(fullfile(raiz, 'modelado', 'cinematica'));
    addpath(fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
    addpath(aqui);
    tc.TestData.aqui = aqui;
    tc.TestData.modelo = 'segway_completo';
    tc.TestData.archivo = fullfile(aqui, 'segway_completo.slx');
    % Se reconstruye si falta o si el constructor es mas nuevo que el .slx, para
    % no probar nunca un modelo viejo contra un constructor cambiado.
    constructor = fullfile(aqui, 'construir_segway_completo.m');
    d_slx = dir(tc.TestData.archivo);
    d_m   = dir(constructor);
    if isempty(d_slx) || d_m.datenum > d_slx.datenum
        if bdIsLoaded(tc.TestData.modelo), close_system(tc.TestData.modelo, 0); end
        construir_segway_completo(aqui, tc.TestData.modelo);
    end
end

function teardownOnce(tc)
    if bdIsLoaded(tc.TestData.modelo), close_system(tc.TestData.modelo, 0); end
end

% =====================================================================
function test_el_modelo_existe_y_tiene_las_seis_etapas(tc)
    load_system(tc.TestData.archivo);
    esperados = {'Consignas', 'Control', 'Actuadores', 'Planta del robot', 'Sensores'};
    for i = 1:numel(esperados)
        tc.verifyTrue(bdIsLoaded(tc.TestData.modelo));
        tc.verifyNotEmpty(find_system(tc.TestData.modelo, 'SearchDepth', 1, ...
            'BlockType', 'SubSystem', 'Name', esperados{i}), ...
            sprintf('falta la etapa "%s"', esperados{i}));
    end
end

function test_estan_los_cuatro_motores_por_separado(tc)
    load_system(tc.TestData.archivo);
    cuatro = {'Motor de rueda IZQUIERDA', 'Motor de rueda DERECHA', ...
              'Servo de pata IZQUIERDA',  'Servo de pata DERECHA'};
    for i = 1:numel(cuatro)
        tc.verifyNotEmpty(find_system([tc.TestData.modelo '/Actuadores'], ...
            'SearchDepth', 1, 'BlockType', 'SubSystem', 'Name', cuatro{i}), ...
            sprintf('falta el bloque "%s"', cuatro{i}));
    end
end

function test_estan_los_sensores_con_su_ruido(tc)
    load_system(tc.TestData.archivo);
    ruta = [tc.TestData.modelo '/Sensores'];
    tc.verifyNotEmpty(find_system(ruta, 'SearchDepth', 1, 'Name', 'IMU MPU-6050'));
    tc.verifyNotEmpty(find_system(ruta, 'SearchDepth', 1, 'Name', 'Encoders de las ruedas'));
    % cada sensor tiene que tener su fuente de ruido, aunque hoy valga cero
    ruidos = find_system(ruta, 'LookUnderMasks', 'all', 'FollowLinks', 'on', ...
        'MaskType', 'Band-Limited White Noise.');
    tc.verifyGreaterThanOrEqual(numel(ruidos), 2, ...
        'cada sensor deberia tener su entrada de ruido preparada');
end

% =====================================================================
function test_reproduce_el_modelo_de_referencia(tc)
% La prueba que importa: el diagrama tiene que dar lo mismo que planta_con_motor,
% que es una implementacion independiente escrita a mano.
    e = correr(tc, struct());
    tc.verifyLessThan(e.error_estado(1), 1e-8, 'x no coincide con la referencia');
    tc.verifyLessThan(e.error_estado(3), 1e-8, 'phi no coincide con la referencia');
    tc.verifyLessThan(max(e.error_estado), 1e-6, 'el diagrama no reproduce el modelo');
end

function test_los_sensores_ideales_no_alteran_nada(tc)
    e = correr(tc, struct());
    tc.verifyLessThan(max(max(abs(e.z_med - e.z))), 1e-12, ...
        'con sensores ideales lo medido tiene que ser identico a lo real');
end

function test_los_dos_motores_de_rueda_dan_lo_mismo(tc)
% Hoy reciben la misma tension, asi que tienen que entregar el mismo par.
    e = correr(tc, struct());
    tc.verifyLessThan(max(abs(e.tau(:,1) - e.tau(:,2))), 1e-12, ...
        'los dos motores de rueda deberian entregar el mismo par');
end

function test_el_par_respeta_el_limite_del_piso(tc)
    e = correr(tc, struct());
    % sl_tau es el par de cada motor ANTES del limite; sl_tau_total es el de despues
    tc.verifyLessThanOrEqual(max(abs(e.tau_total)), e.tau_traccion + 1e-9, ...
        'el par que llega a la planta se paso del limite de agarre');
    tc.verifyGreaterThan(max(abs(sum(e.tau, 2))), max(abs(e.tau_total)) - 1e-9, ...
        'el limite de agarre deberia estar recortando algo en esta maniobra');
end

function test_la_tension_de_cada_motor_respeta_la_bateria(tc)
% El control puede PEDIR mas, pero lo que entra al motor se satura.
    e = correr(tc, struct());
    par_max_teorico = e.beta_V_motor*e.V_bat + e.b_m_motor*max(abs(e.z(:,2))/e.r + abs(e.z(:,4)));
    tc.verifyLessThanOrEqual(max(abs(e.tau(:))), par_max_teorico + 1e-9, ...
        'un motor entrego mas par del que puede con la bateria saturada');
end

% =====================================================================
function test_los_servos_llegan_a_la_postura_pedida(tc)
    e = correr(tc, struct('theta_fin_deg', 40, 't_patas', 1, 'duracion', 10));
    tc.verifyEqual(rad2deg(e.theta(end)), 40, 'AbsTol', 0.5, ...
        'los servos no llegaron a la postura pedida');
end

function test_los_servos_respetan_los_topes(tc)
% Se pide una postura imposible: el integrador tiene que frenarla en el tope.
    e = correr(tc, struct('theta_fin_deg', 70, 't_patas', 1, 'duracion', 10));
    tc.verifyLessThanOrEqual(rad2deg(max(e.theta)), 40 + 1e-6, ...
        'el servo se paso del tope mecanico de 40 grados');
end

function test_compensar_la_postura_evita_que_se_corra(tc)
% Con las patas moviendose: compensando delta_G el robot se queda; sin compensar, no.
    base = struct('theta_0_deg', 10, 'theta_fin_deg', 40, 't_patas', 1, ...
                  'duracion', 12, 'phi0_deg', 0, 'x_destino', 0, 'verificar', false);
    con = correr(tc, setfield(base, 'compensar', 1));  %#ok<SFLD>
    sin_ = correr(tc, setfield(base, 'compensar', 0)); %#ok<SFLD>
    tc.verifyLessThan(1e3*max(abs(con.z(:,1))), 1, ...
        'compensando delta_G el robot no deberia moverse del lugar');
    tc.verifyGreaterThan(1e3*max(abs(sin_.z(:,1))), 100, ...
        'sin compensar delta_G el robot deberia correrse mas de 10 cm');
end

% =====================================================================
function e = correr(tc, opc)
%CORRER  Prepara el workspace, simula y devuelve lo que hace falta comprobar.
    d = @(c, v) campo(opc, c, v);
    postura_deg = d('postura_deg', 25);

    fisicos = parametros_fisicos('segunda_iteracion');
    p = parametros_pendulo_invertido(fisicos, postura_deg);
    [p, motor] = motor_pendulo_invertido(p, fisicos);
    C = disenar_lqr_pendulo_invertido(p, 'max_phi_deg', 8);

    v = struct();
    v.K = C.K;
    v.V_bat = motor.V_bat;
    v.beta_V_motor = motor.beta_V/motor.n_motores;
    v.b_m_motor = motor.b_m/motor.n_motores;
    v.tau_traccion = limite_de_traccion(p);
    v.r = p.r;  v.b_x = p.b_x;  v.b_phi = p.b_phi;
    v.b_eje_mecanico = p.b_eje_mecanico;  v.acople_rotor = p.e_acople;
    v.theta_pata_min = (360 - max(fisicos.th))*pi/180;
    v.theta_pata_max = (360 - min(fisicos.th))*pi/180;
    v.theta_pata_0   = deg2rad(d('theta_0_deg', postura_deg));
    v.theta_pata_fin = deg2rad(d('theta_fin_deg', postura_deg));
    v.t_patas = d('t_patas', 4);
    v.Kp_servo = 12;  v.w_servo_max = deg2rad(300);
    v.x0 = 0;  v.v0 = 0;  v.phi0 = deg2rad(d('phi0_deg', 5));  v.omega0 = 0;
    v.x_destino = d('x_destino', 0.30);  v.t_consigna = 2.0;  v.giro_ref = 0;
    v.ruido_imu_angulo = 0;  v.ruido_imu_giro = 0;
    v.ruido_encoder_x = 0;   v.ruido_encoder_v = 0;
    v.sesgo_imu = 0;  v.Ts_sensores = 0.005;
    v.compensar_delta_G = d('compensar', 1);

    grados = unique([10:1:40, postura_deg]);
    v.tabla_theta = deg2rad(grados(:));
    n = numel(grados);
    [v.tabla_a, v.tabla_h, v.tabla_j, v.tabla_k, v.tabla_delta_G] = deal(zeros(n, 1));
    for i = 1:n
        pi_ = motor_pendulo_invertido(parametros_pendulo_invertido(fisicos, grados(i)), fisicos);
        v.tabla_a(i) = pi_.a;  v.tabla_h(i) = pi_.h;  v.tabla_j(i) = pi_.j;
        v.tabla_k(i) = pi_.k;  v.tabla_delta_G(i) = pi_.delta_G;
    end

    campos = fieldnames(v);
    for i = 1:numel(campos), assignin('base', campos{i}, v.(campos{i})); end

    duracion = d('duracion', 6);
    s = sim(tc.TestData.modelo, 'StopTime', num2str(duracion));

    e = v;
    e.t     = s.sl_z.time;
    e.z     = s.sl_z.signals.values;
    e.z_med = s.sl_z_med.signals.values;
    e.U     = s.sl_U.signals.values;
    e.tau   = s.sl_tau.signals.values;
    e.theta = s.sl_theta.signals.values;
    e.tau_total = s.sl_tau_total.signals.values;

    if d('verificar', true) && abs(v.theta_pata_fin - v.theta_pata_0) < 1e-9
        ref = @(tt) [v.x_destino*(tt >= v.t_consigna); 0; 0; 0];
        ode = @(tt, z) planta_con_motor(z, -C.K*(z - ref(tt)), p);
        sol = ode45(ode, [0 duracion], [v.x0; v.v0; v.phi0; v.omega0], ...
            odeset('RelTol', 1e-10, 'AbsTol', 1e-12, 'MaxStep', 1e-3));
        e.error_estado = max(abs(e.z - deval(sol, e.t).'), [], 1);
    else
        e.error_estado = nan(1, 4);
    end
end

function valor = campo(opc, nombre, por_defecto)
    if isfield(opc, nombre), valor = opc.(nombre); else, valor = por_defecto; end
end
