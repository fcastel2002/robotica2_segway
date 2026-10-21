function C = disenar_lqr_pendulo_invertido(p, varargin)
%DISENAR_LQR_PENDULO_INVERTIDO Realimentacion de estado con entrada de TENSION.
%   C = disenar_lqr_pendulo_invertido(p) con p salido de
%   motor_pendulo_invertido. Devuelve la ganancia C.K de la ley
%
%       V = -C.K * z,      z = [x; v; phi; omega],
%
%   donde V es la tension comun a los dos motores. Por motor es la misma
%   tension; el par diferencial (giro) pertenece a otro modelo.
%
%   Opciones nombre/valor (regla de Bryson: se pesa cada estado por el inverso
%   del cuadrado de su maximo aceptable, de modo que todos pesen parecido
%   cuando estan en su limite):
%     'max_x'        0.10   [m]     error de posicion tolerable
%     'max_v'        0.30   [m/s]   velocidad de avance tolerable
%     'max_phi_deg'  8      [grados] inclinacion tolerable; es el que manda.
%                            Barrido de 2 a 20 grados: todos recuperan de mas de
%                            30 grados, y 8 da el mejor asentamiento sin ganancia
%                            excesiva. Bajarlo endurece el lazo y amplifica el
%                            ruido del giroscopo; subirlo lo ablanda.
%     'max_omega'    1.0    [rad/s] velocidad de cabeceo tolerable
%     'max_tension'        []     [V]     por defecto la tension de bateria
%     'factor_R'     4      multiplica el R de Bryson. NO es un numero arbitrario:
%                            la regla pura (factor 1) da un lazo que NO sobrevive a la
%                            implementacion. Ver la nota de abajo.
%     'Q','R'        []     si se dan, reemplazan a la regla de Bryson
%
%   Requiere Control System Toolbox (lqr). Si no esta, resuelve la ecuacion de
%   Riccati por el metodo del hamiltoniano, que solo necesita eig.
%
%   --- Por que R se multiplica por 4 ---
%   La regla de Bryson fija R = 1/V_bat^2, que es coherente con Q pero mira solo el
%   problema continuo e ideal. Con ese R el LQR pone un polo en -189 1/s que no tiene
%   nada que ver con la fisica del robot (el mas rapido de la planta es -7,6) y es puro
%   costo de implementacion. Medido sobre el lazo realista (muestreo de 5 ms, un paso de
%   retardo y el filtro de 20 Hz que la cuantizacion del encoder obliga a poner):
%
%     factor_R   polo caro   Ts que aguanta   ruido del encoder   con filtro de 20 Hz
%        1        -189 1/s       5,9 ms            4,4 V            INESTABLE (1,178)
%        2        -135           8,7 ms            3,3 V            al limite  (0,993)
%        4         -98          13,0 ms            2,6 V            estable    (0,985)
%        8         -72          19,5 ms            2,0 V            estable    (0,988)
%
%   O sea que el diseno de libro no anda en el robot. El costo de repesar es chico: el
%   escalon de 30 cm pasa de 1,69 s a 1,83 s, un 8 %%. Se elige 4 porque deja el margen
%   de muestreo en 2,6 veces el periodo en vez de 1,2, que es el riesgo real.
%   En LQR solo importa el cociente Q/R, asi que multiplicar R por 4 equivale a declarar
%   tolerancias 2 veces mas grandes; se deja explicito en vez de disimularlo en Q.
%
%   Lo que SI dice este diseno: con el modelo lineal, parametros estimados y
%   medida perfecta del estado, existe una realimentacion que estabiliza y
%   cuanta tension pide. Lo que NO dice: que el robot real se mantenga parado.
%   Faltan identificar el motor y la friccion, el retardo y el ruido de los
%   sensores, la cuantizacion del encoder y el periodo de muestreo.

    opciones = inputParser;
    opciones.addParameter('max_x', 0.10, @(x) isnumeric(x) && isscalar(x) && x > 0);
    opciones.addParameter('max_v', 0.30, @(x) isnumeric(x) && isscalar(x) && x > 0);
    opciones.addParameter('max_phi_deg', 8, @(x) isnumeric(x) && isscalar(x) && x > 0);
    opciones.addParameter('max_omega', 1.0, @(x) isnumeric(x) && isscalar(x) && x > 0);
    opciones.addParameter('max_tension', [], @(x) isempty(x) || (isnumeric(x) && isscalar(x) && x > 0));
    opciones.addParameter('factor_R', 4, @(x) isnumeric(x) && isscalar(x) && x > 0);
    opciones.addParameter('Q', [], @(x) isempty(x) || isequal(size(x), [4 4]));
    opciones.addParameter('R', [], @(x) isempty(x) || (isnumeric(x) && isscalar(x) && x > 0));
    opciones.parse(varargin{:});
    op = opciones.Results;

    assert(isfield(p, 'motor'), ...
        'La planta debe venir de motor_pendulo_invertido: la entrada es tension.');
    if isempty(op.max_tension), op.max_tension = p.motor.V_bat; end

    %% 1. Modelo lineal con la tension como entrada.
    % B del par se escala por beta_V (ec. 47 del capitulo de espacio de estados).
    % La contraelectromotriz ya esta dentro de p.b_eje, asi que A no se retoca.
    L = linealizar_pendulo_invertido(p);
    C.A = L.A;
    C.B = p.motor.beta_V * L.B;
    C.B_par = L.B;
    C.estados = {'x [m]', 'v [m/s]', 'phi [rad]', 'omega [rad/s]'};
    C.entrada = 'tension comun [V]';
    C.autovalores_lazo_abierto = L.autovalores;
    C.rango_controlabilidad = rank([C.B, C.A*C.B, C.A^2*C.B, C.A^3*C.B]);
    assert(C.rango_controlabilidad == 4, ...
        'El modelo lineal no es controlable (rango %d): revisar la planta.', ...
        C.rango_controlabilidad);

    %% 2. Pesos.
    C.max_phi = deg2rad(op.max_phi_deg);
    if isempty(op.Q)
        C.Q = diag([1/op.max_x^2, 1/op.max_v^2, 1/C.max_phi^2, 1/op.max_omega^2]);
        C.regla = 'Bryson';
    else
        C.Q = op.Q;  C.regla = 'Q dado por el usuario';
    end
    if isempty(op.R)
        C.R = op.factor_R/op.max_tension^2;   % Bryson x factor_R; ver la nota del encabezado
        C.regla = sprintf('%s, R x%g por implementacion', C.regla, op.factor_R);
    else
        C.R = op.R;  C.regla = [C.regla ', R dado'];
    end
    C.limites = op;

    %% 3. Resolver.
    if exist('lqr', 'file') == 2
        C.K = lqr(C.A, C.B, C.Q, C.R);
        C.metodo = 'lqr (Control System Toolbox)';
    else
        C.K = lqr_por_hamiltoniano(C.A, C.B, C.Q, C.R);
        C.metodo = 'Riccati por hamiltoniano (sin toolbox)';
    end
    C.A_lazo_cerrado = C.A - C.B*C.K;
    C.polos = eig(C.A_lazo_cerrado);
    assert(all(real(C.polos) < 0), 'El lazo cerrado no quedo estable.');

    %% 4. Lectura fisica del resultado.
    % Cuanta tension pide cada desviacion por separado, estando el resto en cero.
    C.tension_por_estado = -C.K .* [op.max_x, op.max_v, C.max_phi, op.max_omega];
    C.tension_por_grado_de_inclinacion = -C.K(3)*deg2rad(1);
    C.inclinacion_que_satura_deg = rad2deg(abs(op.max_tension/C.K(3)));
    C.polo_mas_lento = max(real(C.polos));
    C.polo_mas_rapido = min(real(C.polos));
    C.tiempo_de_asentamiento = 4/abs(C.polo_mas_lento);     % criterio del 2 %
    C.margen_sobre_gravedad = abs(C.K(3))*p.motor.beta_V/(p.a*p.k/(p.a + p.h/p.r));
    C.V_max = op.max_tension;
end

function K = lqr_por_hamiltoniano(A, B, Q, R)
%LQR_POR_HAMILTONIANO Riccati continua por el subespacio estable del hamiltoniano.
%   Alternativa a lqr cuando no hay Control System Toolbox. Solo usa eig.
    n = size(A, 1);
    H = [A, -B*(R\B.'); -Q, -A.'];
    [V, D] = eig(H);
    estables = real(diag(D)) < 0;
    assert(sum(estables) == n, ...
        'El hamiltoniano no tiene %d autovalores estables: revisar Q y R.', n);
    U = V(:, estables);
    P = real(U(n+1:end, :)/U(1:n, :));
    P = (P + P.')/2;
    K = R\(B.'*P);
end
