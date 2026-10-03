function informe = verificar_pendulo_invertido()
%VERIFICAR_PENDULO_INVERTIDO Comprobaciones fisicas del modelo nuevo.
%   Ejecutar verificar_pendulo_invertido desde esta carpeta.
%   Usa assert y MATLAB base; no depende de un framework de pruebas.

    carpeta = fileparts(mfilename('fullpath'));
    raiz = fileparts(fileparts(carpeta));
    addpath(fullfile(raiz, 'modelado', 'parametros'));
    addpath(fullfile(raiz, 'modelado', 'cinematica'));
    addpath(fullfile(raiz, 'modelado', 'planta', 'pendulo_invertido'));
    fisicos = parametros_fisicos('segunda_iteracion');

    %% 1. Composicion y matriz de masa en tres posturas y todo el angulo.
    posturas = [10, 25, 40];
    masa_esperada = 1e-3 * (fisicos.m_cabina + fisicos.m_tapa ...
        + 2*fisicos.m_servo + fisicos.m_bateria + fisicos.m_electronica ...
        + fisicos.m_tornilleria + fisicos.m_carga ...
        + 2*(fisicos.m_AD + fisicos.m_BC + fisicos.m_CDP + fisicos.m_motor + fisicos.m_rueda));
    determinante_minimo = inf;
    for theta = posturas
        p = parametros_pendulo_invertido(fisicos, theta);
        assert(abs(p.m_total - masa_esperada) < 1e-12, 'Conteo incorrecto de masas.');
        for phi = linspace(-pi, pi, 101)
            [~, R] = ecuaciones_pendulo_invertido([0; 0; phi; 0], 0, p);
            [~, fallo_cholesky] = chol(R.matriz_masa);
            assert(fallo_cholesky == 0, 'La matriz de masa no es definida positiva.');
            determinante_minimo = min(determinante_minimo, R.determinante);
        end
    end
    informe.posturas_verificadas_deg = posturas;
    informe.determinante_minimo = determinante_minimo;

    %% 2. Equilibrio, peso y respuesta a gravedad/par con signos fisicos.
    p = parametros_pendulo_invertido(fisicos, 25);
    [dz, R] = ecuaciones_pendulo_invertido(zeros(4, 1), 0, p);
    assert(norm(dz, inf) < 1e-13, 'La vertical no es un equilibrio.');
    assert(abs(R.normal-p.m_total*p.g) < 1e-12, 'La normal estatica no coincide con el peso.');
    dz_par = ecuaciones_pendulo_invertido(zeros(4, 1), 0.01, p);
    assert(dz_par(2) < 0 && dz_par(4) < 0, 'Signo incorrecto de accion/reaccion del motor.');
    dz_gravedad = ecuaciones_pendulo_invertido([0; 0; 0.01; 0], 0, p);
    assert(dz_gravedad(4) > 0 && dz_gravedad(2) > 0, 'La gravedad debe desestabilizar el cuerpo.');

    %% 3. Linealizacion analitica contra el Jacobiano numerico de la ODE.
    L = linealizar_pendulo_invertido(p);
    paso = 1e-7;
    A_numerica = zeros(4, 4);
    for columna = 1:4
        desplazamiento = zeros(4, 1);
        desplazamiento(columna) = paso;
        f_mas = ecuaciones_pendulo_invertido(desplazamiento, 0, p);
        f_menos = ecuaciones_pendulo_invertido(-desplazamiento, 0, p);
        A_numerica(:, columna) = (f_mas-f_menos)/(2*paso);
    end
    B_numerica = (ecuaciones_pendulo_invertido(zeros(4, 1), paso, p) ...
        - ecuaciones_pendulo_invertido(zeros(4, 1), -paso, p))/(2*paso);
    informe.error_A = norm(L.A-A_numerica, inf);
    informe.error_B = norm(L.B-B_numerica, inf);
    assert(informe.error_A < 1e-7 && informe.error_B < 1e-7, ...
        'El modelo lineal no coincide con el Jacobiano del no lineal.');
    assert(L.rango_controlabilidad == 4, 'La planta nominal no tiene rango de controlabilidad cuatro.');

    %% 4. Potencia y Newton: balances independientes en un estado en movimiento.
    z = [0.07; 0.12; 0.08; -0.3];
    tau = 0.015;
    [dz, R] = ecuaciones_pendulo_invertido(z, tau, p);
    gradiente_E = [0; p.a*z(2)-p.h*cos(z(3))*z(4); ...
        p.h*sin(z(3))*z(2)*z(4)-p.k*sin(z(3)); ...
        -p.h*cos(z(3))*z(2)+p.j*z(4)];
    informe.error_potencia = abs(gradiente_E.'*dz-R.potencia_neta);
    assert(informe.error_potencia < 1e-11, 'Se incumple el balance de potencia.');
    aceleracion_Gx = dz(2)-p.l*cos(z(3))*dz(4)+p.l*sin(z(3))*z(4)^2;
    informe.error_balance_horizontal = abs(p.m_ruedas*dz(2)+p.m_cuerpo*aceleracion_Gx ...
        - R.fuerza_tangencial + p.b_x*z(2));
    assert(informe.error_balance_horizontal < 1e-11, 'Se incumple el balance horizontal de Newton.');
    assert(R.potencia_disipada >= 0, 'La friccion no puede generar energia.');

    %% 5. Integracion conservativa: la energia debe permanecer constante.
    p_ideal = p;
    p_ideal.b_eje = 0;
    p_ideal.b_phi = 0;
    p_ideal.b_x = 0;
    z0 = [0; 0; deg2rad(0.5); 0];
    opciones = odeset('RelTol', 1e-10, 'AbsTol', 1e-12, 'MaxStep', 1e-3);
    [~, estados] = ode45(@(~, estado) ecuaciones_pendulo_invertido(estado, 0, p_ideal), ...
        [0, 0.1], z0, opciones);
    energias = zeros(size(estados, 1), 1);
    for i = 1:size(estados, 1)
        [~, R] = ecuaciones_pendulo_invertido(estados(i, :).', 0, p_ideal);
        energias(i) = R.energia;
        assert(R.contacto_valido, 'La comprobacion conservativa salio del dominio de contacto.');
    end
    informe.deriva_energia_J = max(abs(energias-energias(1)));
    assert(informe.deriva_energia_J < 1e-9, 'La energia conservativa deriva demasiado.');

    %% 6. Reparametrizar una carga debe actualizar masa, CoM e inercia.
    fisicos_carga = fisicos;
    fisicos_carga.m_carga = 100;
    fisicos_carga.r_carga = [-18.5, 80];
    p_carga = parametros_pendulo_invertido(fisicos_carga, 25);
    assert(abs(p_carga.m_total-p.m_total-0.1) < 1e-12, 'La carga no actualizo la masa total.');
    assert(abs(p_carga.l-p.l) > 1e-5 && abs(p_carga.J_cuerpo-p.J_cuerpo) > 1e-6, ...
        'La carga debe actualizar tambien la geometria del CoM y la inercia.');
    informe.grupos_aprobados = 6;
    informe.fecha = char(datetime('now', 'TimeZone', 'America/Argentina/Buenos_Aires', ...
        'Format', 'yyyy-MM-dd HH:mm:ss Z'));
    informe.matlab = version;
    fprintf('\nVERIFICACION: 6/6 grupos aprobados.\n');
    disp(informe);

    carpeta_resultados = fullfile(carpeta, 'resultados');
    if ~isfolder(carpeta_resultados)
        mkdir(carpeta_resultados);
    end
    fid = fopen(fullfile(carpeta_resultados, 'verificacion.json'), 'w', 'n', 'UTF-8');
    assert(fid >= 0, 'No se pudo guardar la evidencia de verificacion.');
    cerrar_archivo = onCleanup(@() fclose(fid));
    fprintf(fid, '%s\n', jsonencode(informe, 'PrettyPrint', true));
end
