function [p, motor] = motor_pendulo_invertido(p, fisicos, varargin)
%MOTOR_PENDULO_INVERTIDO Agrega el motor DC y la inercia del rotor a la planta.
%   [p, motor] = motor_pendulo_invertido(p, fisicos) toma la planta de
%   parametros_pendulo_invertido y devuelve:
%     p      la misma planta con TRES correcciones incorporadas, de modo que
%            ecuaciones_pendulo_invertido y linealizar_pendulo_invertido
%            siguen sirviendo sin cambiar su estructura (ver abajo);
%     motor  las constantes electricas y los limites, para la entrada de tension.
%
%   La entrada del modelo ampliado es la TENSION comun a los dos motores:
%       tau_total = motor.beta_V * V
%   y el efecto de la contraelectromotriz ya quedo dentro de p.b_eje.
%
%   Opciones nombre/valor:
%     'incluir_rotor'  true  agrega la inercia del rotor reflejada (ec. 54)
%     'eta'            []    rendimiento del reductor; por defecto toma
%                            fisicos.eta_reductor. Baja beta_V y b_m por igual.
%                            Con eta = 1 se recupera la convencion de la
%                            ec. (46) del capitulo de espacio de estados.
%
%   --- Las tres correcciones ---
%   1) Contraelectromotriz. Despreciando la inductancia, cada motor cumple
%        i = (V - Ke*n*w_rel)/Rm,   tau_motor = eta*n*Kt*i,
%      y para los dos motores juntos (ec. 46 del capitulo de estados)
%        tau_total = beta_V*V - b_m*w_rel.
%      El segundo termino depende de w_rel igual que la friccion del eje, asi
%      que sumar b_m a p.b_eje lo representa exactamente. Es amortiguacion
%      real: un motor DC con sus bornes cerrados frena.
%   2) Inercia del rotor, terminos diagonales. La velocidad ABSOLUTA del rotor es
%        alpha_m' = -n*x'/r + (1-n)*phi',
%      de donde sale la correccion de masa de rango uno de la ec. (54). Sus
%      terminos (1,1) y (2,2) se suman a los coeficientes a y j.
%   3) Inercia del rotor, termino cruzado. Este NO se puede meter dentro de h.
%      El acople del cuerpo vale -h*cos(phi), que depende de la inclinacion
%      porque nace de la velocidad del centro de masa; el del rotor es
%      CONSTANTE, porque alpha_m' es lineal en x' y phi' con coeficientes fijos.
%      Por eso el modelo ampliado usa
%        M(1,2) = M(2,1) = -h*cos(phi) + e_acople,
%      con e_acople = delta_M(1,2) >= 0, que es un campo nuevo de p. Con
%      e_acople = 0 se recupera exactamente el modelo de patas fijas sin motor.
%      Al no depender de phi, este termino no agrega fuerza centrifuga.
%
%   --- Advertencia sobre los numeros ---
%   El motor es el GA25-370 1:20 comprado (300 rpm en vacio a 12 V). Sus constantes
%   se DEDUJERON de la parte electrica de la ficha, que es coherente consigo misma
%   (vacio, carga y corriente de bloqueo cierran entre si). La columna de TORSION de
%   esa misma ficha NO cierra: el punto de carga exigiria 18 % de rendimiento y el de
%   bloqueo 146 %, que es imposible. Por eso el par NO se toma de la ficha sino que se
%   calcula, y da unos 3.1 kg cm por motor al bloqueo contra los 5.6 anunciados.
%   Nada de esto esta medido (ELE-002). Los dos efectos que agrega este archivo son de
%   primer orden sobre el control: la inercia del rotor sube el coeficiente de avance
%   cerca de un 40 % y la contraelectromotriz supera unas cien veces a la friccion
%   mecanica supuesta. Conviene medirlos antes de confiar en un controlador.

    opciones = inputParser;
    opciones.addParameter('incluir_rotor', true, @(x) islogical(x) && isscalar(x));
    opciones.addParameter('eta', [], @(x) isempty(x) || (isnumeric(x) && isscalar(x) && x > 0 && x <= 1));
    opciones.parse(varargin{:});
    incluir_rotor = opciones.Results.incluir_rotor;
    eta = opciones.Results.eta;
    if isempty(eta)
        if isfield(fisicos, 'eta_reductor'), eta = fisicos.eta_reductor; else, eta = 1; end
    end

    validateattributes(fisicos.N, {'numeric'}, {'scalar', 'real', 'finite', 'positive'});
    validateattributes(fisicos.R_m, {'numeric'}, {'scalar', 'real', 'finite', 'positive'});
    validateattributes(fisicos.w_nl_motor_rpm, {'numeric'}, {'scalar', 'real', 'finite', 'positive'});
    validateattributes(fisicos.J_r, {'numeric'}, {'scalar', 'real', 'finite', 'nonnegative'});
    validateattributes(fisicos.V_bat, {'numeric'}, {'scalar', 'real', 'finite', 'positive'});

    %% 1. Constantes del motor a partir de la velocidad en vacio.
    % Un motor DC ideal cumple Kt [N m/A] = Ke [V s/rad]. La velocidad en vacio
    % declarada es la del rotor SIN reductor, a la tension de ensayo.
    motor.V_ensayo = 12;                                  % [V] tension de la hoja de datos
    if isfield(fisicos, 'i_vacio'), motor.i_vacio = fisicos.i_vacio; else, motor.i_vacio = 0; end
    motor.nombre = fisicos.nombre_motor;
    motor.w_nl_rotor = fisicos.w_nl_motor_rpm*2*pi/60;    % [rad/s] rotor en vacio
    % En vacio la tension se reparte entre la caida resistiva y la contraelectromotriz:
    %   V = R*i_vacio + Ke*w_nl.  Despreciar el primer termino sobreestima Ke un 5 %.
    motor.Ke = (motor.V_ensayo - fisicos.R_m*motor.i_vacio)/motor.w_nl_rotor;  % [V s/rad]
    motor.Kt = motor.Ke;                                  % [N m/A]
    motor.R_m = fisicos.R_m;
    motor.L_m = fisicos.L_m;
    motor.n_g = fisicos.N;
    motor.eta = eta;
    motor.n_motores = fisicos.n_servos;                   % un motor por rueda

    %% 2. Reduccion a dos coeficientes: tau_total = beta_V*V - b_m*w_rel.
    motor.beta_V = motor.n_motores*eta*motor.n_g*motor.Kt/motor.R_m;            % [N m/V]
    motor.b_m    = motor.n_motores*eta*motor.n_g^2*motor.Kt*motor.Ke/motor.R_m; % [N m s/rad]

    %% 3. Limites fisicos, para saturar la consigna y leer los resultados.
    motor.V_bat = fisicos.V_bat;
    motor.tau_bloqueo = motor.beta_V*motor.V_bat;                 % [N m] las dos ruedas, a rueda parada
    motor.w_rel_vacio = motor.V_bat/(motor.Ke*motor.n_g);         % [rad/s] rueda en vacio
    motor.v_max = motor.w_rel_vacio*p.r;                          % [m/s] velocidad maxima de avance
    motor.i_bloqueo_por_motor = motor.V_bat/motor.R_m;            % [A]
    % Par real al bloqueo: la corriente en vacio no produce par util (es la friccion
    % del conjunto), asi que se descuenta. beta_V*V la ignora, por eso es optimista
    % cerca del bloqueo en la medida de esa corriente.
    motor.tau_bloqueo_util = motor.n_motores*eta*motor.n_g*motor.Kt* ...
        max(motor.i_bloqueo_por_motor - motor.i_vacio, 0);
    motor.tau_electrica = motor.L_m/motor.R_m;                    % [s] constante electrica despreciada

    %% 4. Inercia del rotor reflejada (ec. 54 del desarrollo matematico).
    % Correccion de rango uno y CONSTANTE sobre la matriz de masa.
    motor.incluir_rotor = incluir_rotor;
    motor.J_r = fisicos.J_r;
    vector_rotor = [-motor.n_g/p.r; 1 - motor.n_g];
    motor.delta_M = motor.n_motores*motor.J_r*(vector_rotor*vector_rotor.');
    motor.a_sin_rotor = p.a;
    motor.h_sin_rotor = p.h;
    motor.j_sin_rotor = p.j;

    %% 5. Incorporar a la planta.
    if ~isfield(p, 'e_acople'), p.e_acople = 0; end
    if incluir_rotor
        p.a = p.a + motor.delta_M(1, 1);
        p.j = p.j + motor.delta_M(2, 2);
        p.e_acople = p.e_acople + motor.delta_M(1, 2);
        % h NO cambia: el acople del rotor no tiene la forma -h*cos(phi).
    end
    p.b_eje_mecanico = p.b_eje;
    p.b_eje = p.b_eje + motor.b_m;     % la contraelectromotriz amortigua el eje relativo
    p.motor = motor;
    p.entrada = 'tension comun a los dos motores [V]';

    %% 6. La matriz de masa debe seguir siendo definida positiva en toda la carrera.
    % El peor caso del acople es cos(phi) = 1 (su magnitud maxima si e_acople < h).
    for cphi = [-1, 0, 1]
        M12 = -p.h*cphi + p.e_acople;
        determinante = p.a*p.j - M12^2;
        assert(p.a > 0 && p.j > 0 && determinante > 0, ...
            'La correccion del rotor rompio la matriz de masa (cos phi = %g, det = %.3e).', ...
            cphi, determinante);
    end
end
