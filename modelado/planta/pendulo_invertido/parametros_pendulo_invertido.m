function p = parametros_pendulo_invertido(fisicos, theta_pata_deg)
%PARAMETROS_PENDULO_INVERTIDO Cuerpo equivalente con las patas inmovilizadas.
%   fisicos se obtiene con parametros_fisicos('segunda_iteracion').
%   theta_pata_deg: angulo AD bajo la horizontal, en GRADOS (10 a 40).
%   Salida p: SI. Requiere cinematica_directa en el path.
%   El eje horizontal de esta planta apunta HACIA ADELANTE: se invierte
%   el signo horizontal de los datos de la pata, que apuntan hacia atras.

    validateattributes(theta_pata_deg, {'numeric'}, ...
        {'real', 'finite', 'scalar'}, mfilename, 'theta_pata_deg');
    theta_min_deg = 360 - max(fisicos.th);
    theta_max_deg = 360 - min(fisicos.th);
    assert(theta_pata_deg >= theta_min_deg && theta_pata_deg <= theta_max_deg, ...
        'La postura debe estar dentro del recorrido declarado del servo.');
    assert(fisicos.rama == 1, 'La cinematica disponible usa la rama de armado +1.');
    assert(fisicos.n_servos == 2, 'Esta reduccion representa dos patas simetricas.');

    %% 1. Resolver la postura usando la cinematica existente (mm y grados).
    geometria.AB = fisicos.AB;
    geometria.beta = fisicos.ang_AB;
    geometria.AD = fisicos.k_AD * fisicos.s_barras;
    geometria.BC = fisicos.k_BC * fisicos.s_barras;
    geometria.CD = fisicos.k_CD * fisicos.s_barras;
    geometria.DP = fisicos.k_DP * fisicos.s_barras;
    geometria.delta = fisicos.delta;

    angulo_servo_deg = 360 - theta_pata_deg;
    K = cinematica_directa(angulo_servo_deg, geometria);
    assert(K.valido, 'El cuatro barras no cierra en la postura solicitada.');

    centro_AD = K.A + fisicos.f_AD * (K.D - K.A);
    centro_BC = K.B + fisicos.f_BC * (K.C - K.B);
    centro_CDP = K.D + fisicos.f_CDP * (K.P - K.D);

    %% 2. Reunir las piezas que giran con el cuerpo, excluyendo las ruedas.
    % Las dos patas coinciden en su proyeccion sagital. Agrupar las piezas
    % simetricas equivale a sumar sus masas e inercias en esta vista.
    n = fisicos.n_servos;
    nombre = {'cabina'; 'tapa'; 'servos'; 'bateria'; 'electronica'; ...
              'tornilleria'; 'carga'; 'manivelas AD'; 'balancines BC'; ...
              'acopladores CDP'; 'carcasas de motores'};

    masa_kg = 1e-3 * [fisicos.m_cabina; fisicos.m_tapa; n * fisicos.m_servo; ...
        fisicos.m_bateria; fisicos.m_electronica; fisicos.m_tornilleria; ...
        fisicos.m_carga; n * fisicos.m_AD; n * fisicos.m_BC; ...
        n * fisicos.m_CDP; n * fisicos.m_motor];

    posicion_A_mm = [fisicos.r_cabina; fisicos.r_tapa; fisicos.r_servo; ...
        fisicos.r_bateria; fisicos.r_electronica; fisicos.r_tornilleria; ...
        fisicos.r_carga; centro_AD; centro_BC; centro_CDP; K.P];
    posicion_A_m = 1e-3 * posicion_A_mm;
    posicion_A_m(:, 1) = -posicion_A_m(:, 1);

    % Cero = pieza tratada como masa puntual en su CoM porque falta su
    % inercia propia. El termino de Steiner SI se conserva para todas.
    inercia_propia_kgm2 = [fisicos.J_cabina; fisicos.J_tapa; 0; 0; 0; 0; 0; ...
        n * fisicos.J_AD; n * fisicos.J_BC; n * fisicos.J_CDP; 0];
    assert(all(isfinite(masa_kg)) && all(masa_kg >= 0), ...
        'Las masas deben ser finitas y no negativas.');
    assert(all(isfinite(posicion_A_m(:))), 'Las posiciones deben ser finitas.');
    assert(all(isfinite(inercia_propia_kgm2)) && all(inercia_propia_kgm2 >= 0), ...
        'Las inercias propias deben ser finitas y no negativas.');

    %% 3. Centro de masa e inercia por el teorema de ejes paralelos.
    p.m_cuerpo = sum(masa_kg);
    assert(p.m_cuerpo > 0, 'La masa del cuerpo debe ser positiva.');
    p.r_G_A = sum(masa_kg .* posicion_A_m, 1) / p.m_cuerpo;
    p.r_P_A = 1e-3 * [-K.P(1), K.P(2)];
    desplazamiento = posicion_A_m - p.r_G_A;
    termino_Steiner = masa_kg .* sum(desplazamiento.^2, 2);
    p.J_cuerpo_estimado = sum(inercia_propia_kgm2 + termino_Steiner);

    if isempty(fisicos.J_cuerpo)
        p.J_cuerpo = p.J_cuerpo_estimado;
        p.fuente_inercia = 'Piezas + Steiner; faltan algunas inercias propias';
    else
        p.J_cuerpo = fisicos.J_cuerpo;
        p.fuente_inercia = 'J_cuerpo indicado en parametros_fisicos';
    end

    vector_PG = p.r_G_A - p.r_P_A;
    p.l = hypot(vector_PG(1), vector_PG(2));
    % phi = beta_chasis + delta_G. El equilibrio de gravedad es phi = 0,
    % por lo que el chasis debe estar en beta_chasis = -delta_G.
    p.delta_G = atan2(vector_PG(1), vector_PG(2));
    p.beta_equilibrio = -p.delta_G;
    assert(vector_PG(2) > 0, 'El CoM debe estar encima del eje en esta postura.');

    %% 4. Ruedas: masa e inercia TOTALES de las dos ruedas.
    p.n_motores = n;
    p.r = 1e-3 * fisicos.Rw;
    p.m_ruedas = n * 1e-3 * fisicos.m_rueda;
    if isempty(fisicos.J_rueda)
        J_una_rueda = 0.5 * (1e-3 * fisicos.m_rueda) * p.r^2;
    else
        J_una_rueda = fisicos.J_rueda;
    end
    p.J_ruedas = n * J_una_rueda;
    p.m_total = p.m_cuerpo + p.m_ruedas;

    %% 5. Gravedad, disipacion y criterio de rodadura.
    p.g = fisicos.g;
    p.mu = fisicos.mu;
    p.b_eje = n * fisicos.b_w;    % [N m s/rad], velocidad relativa rueda/cuerpo
    p.b_phi = fisicos.b_pitch;   % [N m s/rad], arrastre externo de cabeceo
    p.b_x = 0;                  % [N s/m], arrastre externo horizontal opcional
    % No se usa c_v: corresponde al contacto con deslizamiento de otra planta.
    % La inercia del rotor y la dinamica electrica NO estan en esta reduccion.

    %% 6. Coeficientes de las ecuaciones (ver desarrollo_matematico.md).
    validateattributes(p.r, {'numeric'}, {'scalar', 'real', 'finite', 'positive'});
    validateattributes(p.J_cuerpo, {'numeric'}, {'scalar', 'real', 'finite', 'positive'});
    validateattributes(p.m_ruedas, {'numeric'}, {'scalar', 'real', 'finite', 'positive'});
    validateattributes(p.J_ruedas, {'numeric'}, {'scalar', 'real', 'finite', 'nonnegative'});
    validateattributes(p.g, {'numeric'}, {'scalar', 'real', 'finite', 'positive'});
    validateattributes(p.mu, {'numeric'}, {'scalar', 'real', 'finite', 'nonnegative'});
    validateattributes(p.b_eje, {'numeric'}, {'scalar', 'real', 'finite', 'nonnegative'});
    validateattributes(p.b_phi, {'numeric'}, {'scalar', 'real', 'finite', 'nonnegative'});
    p.a = p.m_total + p.J_ruedas / p.r^2;
    p.h = p.m_cuerpo * p.l;
    p.j = p.J_cuerpo + p.m_cuerpo * p.l^2;
    p.k = p.m_cuerpo * p.g * p.l;
    p.theta_pata_deg = theta_pata_deg;
    p.fuente = 'modelado/parametros/parametros_fisicos.m';

    x_A_m = posicion_A_m(:, 1);
    y_A_m = posicion_A_m(:, 2);
    p.piezas = table(nombre, masa_kg, x_A_m, y_A_m, ...
        inercia_propia_kgm2, termino_Steiner);
end
