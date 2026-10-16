function tests = test_pendulo_simulink
%TEST_PENDULO_SIMULINK Pruebas del modelo Simulink del pendulo con motor y LQR.
%   Desde la raiz del repositorio:
%       results = runtests('simulacion/pendulo_invertido/tests')
    tests = functiontests(localfunctions);
end

function setupOnce(tc)
    aqui = fileparts(mfilename('fullpath'));
    tc.TestData.banco = fileparts(aqui);
    tc.TestData.raiz = fileparts(fileparts(tc.TestData.banco));
    raiz = tc.TestData.raiz;
    addpath(tc.TestData.banco);
    addpath(fullfile(raiz, 'modelado', 'parametros'));
    addpath(fullfile(raiz, 'modelado', 'cinematica'));
    addpath(fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));

    fisicos = parametros_fisicos('segunda_iteracion');
    p = parametros_pendulo_invertido(fisicos, 25);
    [p, motor] = motor_pendulo_invertido(p, fisicos);
    tc.TestData.fisicos = fisicos;
    tc.TestData.p = p;
    tc.TestData.motor = motor;
    tc.TestData.C = disenar_lqr_pendulo_invertido(p);
    tc.TestData.modelo = 'pendulo_invertido_lqr';
    tc.TestData.tau_traccion = limite_de_traccion(p);
end

function teardownOnce(tc)
    if bdIsLoaded(tc.TestData.modelo), close_system(tc.TestData.modelo, 0); end
end

function test_sin_bloques_matlab_function(tc)
% El pedido explicito: la fisica tiene que leerse en el diagrama.
    archivo = construir_pendulo_simulink(tempdir, 'pendulo_qa_bloques');
    limpieza = onCleanup(@() borrar_modelo('pendulo_qa_bloques', archivo));
    load_system(archivo);
    prohibidos = {'MATLAB Function', 'S-Function', 'Interpreted MATLAB Fcn'};
    for i = 1:numel(prohibidos)
        encontrados = find_system('pendulo_qa_bloques', 'LookUnderMasks', 'all', ...
            'BlockType', 'SubSystem', 'SFBlockType', prohibidos{i});
        tc.verifyEmpty(encontrados, sprintf('Hay bloques "%s" en el modelo.', prohibidos{i}));
    end
    fcn = find_system('pendulo_qa_bloques', 'LookUnderMasks', 'all', 'BlockType', 'Fcn');
    tc.verifyEmpty(fcn, 'Hay bloques Fcn: la ecuacion debe estar en bloques, no en texto.');
    total = find_system('pendulo_qa_bloques', 'LookUnderMasks', 'all', 'Type', 'Block');
    tc.verifyGreaterThan(numel(total), 40, 'El modelo tiene menos bloques de los esperados.');
end

function test_construccion_reproducible(tc)
% Construir dos veces debe dar la misma lista de bloques y de lineas.
    a1 = construir_pendulo_simulink(tempdir, 'pendulo_qa_r1');
    a2 = construir_pendulo_simulink(tempdir, 'pendulo_qa_r2');
    limpieza = onCleanup(@() borrar_modelo({'pendulo_qa_r1', 'pendulo_qa_r2'}, {a1, a2}));
    load_system(a1); load_system(a2);
    b1 = sort(strrep(find_system('pendulo_qa_r1', 'LookUnderMasks', 'all', 'Type', 'Block'), 'pendulo_qa_r1', ''));
    b2 = sort(strrep(find_system('pendulo_qa_r2', 'LookUnderMasks', 'all', 'Type', 'Block'), 'pendulo_qa_r2', ''));
    tc.verifyEqual(b1, b2, 'La construccion no es reproducible.');
end

function test_simulink_igual_que_matlab(tc)
% El modelo debe reproducir planta_con_motor, incluidas las saturaciones.
    p = tc.TestData.p;  C = tc.TestData.C;  motor = tc.TestData.motor;
    for phi0_deg = [2 8 15]
        [t, z_sl] = correr(tc, phi0_deg, 3);
        ode = @(tt, z) planta_con_motor(z, -C.K*z, p);
        sol = ode45(ode, [0 3], [0; 0; deg2rad(phi0_deg); 0], ...
            odeset('RelTol', 1e-10, 'AbsTol', 1e-12));
        z_ml = deval(sol, t).';
        tc.verifyLessThan(max(abs(z_sl(:,3) - z_ml(:,3))), 1e-7, ...
            sprintf('phi no coincide arrancando de %d grados.', phi0_deg));
        tc.verifyLessThan(max(abs(z_sl(:,1) - z_ml(:,1))), 1e-7, ...
            sprintf('x no coincide arrancando de %d grados.', phi0_deg));
    end
    tc.verifyGreaterThan(motor.tau_bloqueo, 0);
end

function test_motor_adentro_o_afuera_dan_lo_mismo(tc)
% Sin saturar, meter la contraelectromotriz en b_eje (lo que se usa para
% linealizar) debe dar la misma derivada que el motor explicito.
    p = tc.TestData.p;  motor = tc.TestData.motor;
    rng(7);
    peor = 0;  comparados = 0;
    for ensayo = 1:300
        z = [0.002*randn; 0.004*randn; deg2rad(0.05)*randn; 0.01*randn];
        V = 0.05*randn;
        [d1, R] = planta_con_motor(z, V, p);
        if R.patina || R.satura_bateria, continue; end
        d2 = ecuaciones_pendulo_invertido(z, motor.beta_V*V, p);
        peor = max(peor, max(abs(d1 - d2)));
        comparados = comparados + 1;
    end
    tc.verifyGreaterThan(comparados, 50, 'Casi todos los ensayos saturaron.');
    tc.verifyLessThan(peor, 1e-12, 'Las dos formas del motor no coinciden.');
end

function test_lqr_estabiliza_y_los_signos_son_los_previstos(tc)
    C = tc.TestData.C;
    tc.verifyEqual(C.rango_controlabilidad, 4);
    tc.verifyTrue(all(real(C.polos) < 0), 'El lazo cerrado no es estable.');
    tc.verifyGreaterThan(max(real(C.autovalores_lazo_abierto)), 0, ...
        'Sin control el equilibrio superior deberia ser inestable.');
    % Signos previstos en el capitulo de espacio de estados, seccion 12.2.
    tc.verifyGreaterThan(C.K(1), 0, 'K_x deberia ser positiva.');
    tc.verifyGreaterThan(C.K(2), 0, 'K_v deberia ser positiva.');
    tc.verifyLessThan(C.K(3), 0, 'K_phi deberia ser negativa.');
    tc.verifyLessThan(C.K(4), 0, 'K_omega deberia ser negativa.');
end

function test_se_recupera_de_una_inclinacion(tc)
% El limite lo pone la adherencia, no el motor. Se busca donde esta.
    limite = 0;
    for phi0_deg = [2 5 10 15 20 25 30]
        [~, z] = correr(tc, phi0_deg, 8);
        if abs(rad2deg(z(end,3))) < 0.5, limite = phi0_deg; else, break; end
    end
    tc.verifyGreaterThanOrEqual(limite, 10, ...
        sprintf('Solo se recupera hasta %d grados: muy poco.', limite));
    tc.TestData.limite_recuperacion = limite;
end

function test_llega_a_la_consigna_de_posicion(tc)
% Lo que hace falta para "ir a otra posicion": seguir un escalon en x.
    destino = 0.30;
    [t, z] = correr(tc, 0, 10, destino, 1.0);
    tc.verifyLessThan(abs(z(end,1) - destino), 0.005, ...
        'No llega a la consigna de posicion.');
    tc.verifyLessThan(abs(rad2deg(z(end,3))), 0.5, ...
        'Llega a la posicion pero no queda derecho.');
    % Fase no minima: antes de avanzar tiene que retroceder.
    despues = t >= 1.0;
    arranque = z(find(despues, 1), 1);
    tc.verifyLessThan(min(z(despues, 1)) - arranque, -1e-3, ...
        'Deberia retroceder antes de avanzar (cero en el semiplano derecho).');
end

function test_el_motor_no_rompe_la_adherencia(tc)
% El motor NO llega a hacer patinar la rueda: usa alrededor del 87 % del agarre.
%
% Esto corrige una conclusion anterior equivocada. Se habia comparado el par de
% bloqueo contra mu*N*r y daba que el motor superaba al piso varias veces. Era
% falso: tau/r NO es la fuerza en el contacto, porque parte del par acelera la
% inercia reflejada del rotor (0.44 kg sobre un robot de 1.0 kg). La fuerza real
% sale de Newton sobre todo el robot y es casi tres veces menor que tau/r.
    p = tc.TestData.p;  motor = tc.TestData.motor;
    [tau_traccion, F_max, c1] = limite_de_traccion(p);
    F_motor = abs(c1)*motor.tau_bloqueo;
    tc.verifyLessThan(F_motor, F_max/0.9, ...
        'El motor estaria rompiendo la adherencia: revisar el limite de traccion.');
    tc.verifyGreaterThan(F_motor/(F_max/0.9), 0.5, ...
        'El motor quedaria muy sobrado de margen: revisar beta_V o mu.');
    % Y tau/r sobreestima la fuerza real: ese era justo el error.
    tc.verifyGreaterThan((motor.tau_bloqueo/p.r)/F_motor, 2, ...
        'tau/r deberia sobreestimar bastante la fuerza real en el contacto.');
    tc.verifyGreaterThan(tau_traccion, 0.5*motor.tau_bloqueo, ...
        'El limite de traccion quedo absurdamente bajo frente al motor.');
    % Y el contacto debe seguir siendo valido en toda la maniobra nominal.
    C = tc.TestData.C;
    ode = @(tt, z) planta_con_motor(z, -C.K*z, p);
    sol = ode45(ode, [0 5], [0; 0; deg2rad(10); 0], odeset('RelTol', 1e-9, 'AbsTol', 1e-11));
    for i = 1:numel(sol.x)
        [~, R] = planta_con_motor(sol.y(:,i), -C.K*sol.y(:,i), p);
        tc.verifyTrue(R.contacto_valido, ...
            sprintf('Se pierde la rodadura en t = %.3f s.', sol.x(i)));
    end
end

function test_fuerza_tangencial_igual_a_newton(tc)
% La fuerza en el contacto tiene que ser la de Newton sobre TODO el robot,
% m_total*x'' - h cos(phi) phi'' + h sin(phi) phi'^2, tambien con rotor.
% Antes se calculaba como -tau_ef/r - J_ruedas*x''/r^2, que omite la inercia
% del rotor y daba errores de hasta 200 %.
    p = tc.TestData.p;
    rng(11);  peor = 0;
    for ensayo = 1:200
        z = [0; 0.3*randn; 0.3*randn; 2*randn];
        [dz, R] = planta_con_motor(z, 3*randn, p);
        F_newton = p.m_total*dz(2) - p.h*cos(z(3))*dz(4) + p.h*sin(z(3))*z(4)^2;
        peor = max(peor, abs(R.fuerza_tangencial - F_newton));
    end
    tc.verifyLessThan(peor, 1e-12, ...
        'La fuerza tangencial no coincide con el balance horizontal global.');
end

function test_sobrevive_a_la_implementacion_real(tc)
% El diseno es CONTINUO y con el estado exacto, pero el robot va a muestrear, va a
% tener retardo de computo y va a necesitar filtrar la velocidad del encoder.
% Este test comprueba que el lazo sigue estable con las tres cosas juntas.
%
% Existe porque el diseno anterior NO pasaba: con la regla de Bryson pura el radio
% espectral daba 1.178 (inestable) al agregar el filtro. Se repeso R por 4.
    p = tc.TestData.p;  C = tc.TestData.C;  o = tc.TestData.fisicos;
    Ts = o.Ts;

    % (a) muestreo con retencion de orden cero y un paso de retardo de computo.
    %     El estado aumentado es [z; u_anterior].
    d = c2d(ss(C.A, C.B, eye(4), 0), Ts, 'zoh');
    radio_muestreo = max(abs(eig([d.A, d.B; -C.K, 0])));
    tc.verifyLessThan(radio_muestreo, 1, ...
        sprintf('El lazo muestreado a %g ms con un retardo es inestable.', Ts*1e3));

    % (b) margen sobre el periodo: cuanto se puede alargar Ts antes de perder estabilidad.
    lo = 1e-4;  hi = 100e-3;
    for it = 1:40
        T = 0.5*(lo + hi);  dd = c2d(ss(C.A, C.B, eye(4), 0), T, 'zoh');
        if max(abs(eig([dd.A, dd.B; -C.K, 0]))) < 1, lo = T; else, hi = T; end
    end
    tc.verifyGreaterThan(lo/Ts, 2, ...
        sprintf('Margen de muestreo de solo %.1fx: muy ajustado para implementar.', lo/Ts));

    % (c) con el filtro de velocidad que la cuantizacion del encoder obliga a poner.
    wf = 2*pi*o.fc_vel;
    Af = [C.A, zeros(4,1); wf*[0 1 0 0], -wf];   Bf = [C.B; 0];
    Kf = [C.K(1), 0, C.K(3), C.K(4), C.K(2)];    % se realimenta la v FILTRADA
    df = c2d(ss(Af, Bf, eye(5), 0), Ts, 'zoh');
    radio_filtro = max(abs(eig([df.A, df.B; -Kf, 0])));
    tc.verifyLessThan(radio_filtro, 1, ...
        sprintf('Con el filtro de %g Hz el lazo se vuelve inestable (radio %.3f).', ...
        o.fc_vel, radio_filtro));
end

function test_margenes_del_lqr_cumplen_el_teorema(tc)
% El LQR de una entrada con estado completo garantiza |1 + L(jw)| >= 1 en toda
% frecuencia (desigualdad de Kalman), de donde salen margen de fase >= 60 grados y
% margen de ganancia infinito hacia arriba. Es el argumento central de por que se
% usa LQR y no una asignacion de polos a mano, asi que conviene tenerlo verificado.
    C = tc.TestData.C;
    L = ss(C.A, C.B, C.K, 0);          % lazo cortado en la ENTRADA de la planta
    w = logspace(-2, 4, 4000);
    Lw = squeeze(freqresp(L, w));
    tc.verifyGreaterThan(min(abs(1 + Lw)), 0.999, ...
        'No se cumple la desigualdad de Kalman: revisar que el LQR este bien resuelto.');
    [~, Pm] = margin(L);
    tc.verifyGreaterThan(Pm, 60, 'El margen de fase deberia superar los 60 grados.');
    % Y una asignacion de polos de aspecto razonable NO tiene esa garantia: es el
    % contraejemplo que justifica usar LQR.  No se verifica un valor, solo que la
    % diferencia exista, para que el argumento quede registrado en el codigo.
    Kmano = place(C.A, C.B, [-3 -4 -5 -6]);
    Lmano = ss(C.A, C.B, Kmano, 0);
    [~, Pm_mano] = margin(Lmano);
    tc.verifyLessThan(Pm_mano, Pm, ...
        'Se esperaba que una asignacion de polos a mano tuviera menos margen que el LQR.');
end

function test_el_modelo_de_patas_fijas_sigue_valido(tc)
% La generalizacion con e_acople no debe cambiar el modelo sin motor.
    informe = verificar_pendulo_invertido();
    tc.verifyEqual(informe.grupos_aprobados, 6, ...
        'La verificacion original del pendulo dejo de pasar.');
    p0 = parametros_pendulo_invertido(tc.TestData.fisicos, 25);
    tc.verifyFalse(isfield(p0, 'e_acople'), ...
        'La planta sin motor no deberia traer e_acople.');
end

% ------------------------------------------------------------------
function [t, z, extra] = correr(tc, phi0_deg, duracion, x_destino, t_consigna)
    if nargin < 4, x_destino = 0; end
    if nargin < 5, t_consigna = 0; end
    p = tc.TestData.p;  motor = tc.TestData.motor;  C = tc.TestData.C;
    archivo = fullfile(tc.TestData.banco, [tc.TestData.modelo '.slx']);
    if ~exist(archivo, 'file')
        construir_pendulo_simulink(tc.TestData.banco, tc.TestData.modelo);
    end
    entrada = Simulink.SimulationInput(tc.TestData.modelo);
    valores = {'K', C.K; 'V_bat', motor.V_bat; 'beta_V', motor.beta_V; ...
        'b_m', motor.b_m; 'tau_traccion', tc.TestData.tau_traccion; ...
        'a', p.a; 'h', p.h; 'j', p.j; 'k', p.k; 'e_acople', p.e_acople; ...
        'r', p.r; 'b_eje', p.b_eje_mecanico; 'b_x', p.b_x; 'b_phi', p.b_phi; ...
        'q0', [0; deg2rad(phi0_deg)]; 'q_punto0', [0; 0]; ...
        'x_destino', x_destino; 't_consigna', t_consigna; 'duracion', duracion};
    for i = 1:size(valores, 1)
        entrada = entrada.setVariable(valores{i,1}, valores{i,2});
    end
    entrada = entrada.setModelParameter('StopTime', num2str(duracion));
    salida = sim(entrada);
    t = salida.sl_z.time;
    z = salida.sl_z.signals.values;
    extra = struct('U', salida.sl_tension.signals.values, ...
                   'tau', salida.sl_par.signals.values, ...
                   'ref', salida.sl_ref.signals.values);
end

function borrar_modelo(nombres, archivos)
    nombres = cellstr(nombres);
    archivos = cellstr(archivos);
    for i = 1:numel(nombres)
        if bdIsLoaded(nombres{i}), close_system(nombres{i}, 0); end
        if exist(archivos{i}, 'file'), delete(archivos{i}); end
    end
end
