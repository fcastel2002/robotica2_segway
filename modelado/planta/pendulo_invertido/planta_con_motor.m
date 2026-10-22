function [derivada, R] = planta_con_motor(estado, tension, p)
%PLANTA_CON_MOTOR Planta completa con el motor explicito y los dos limites reales.
%   [derivada, R] = planta_con_motor(estado, tension, p), con p salido de
%   motor_pendulo_invertido. La entrada es la TENSION comun a los dos motores.
%
%   Es el modelo de referencia que reproduce el Simulink. Encadena:
%
%     1. tension        saturada por la BATERIA           |V| <= V_bat
%     2. motor          tau = beta_V*V - b_m*w_rel        (contraelectromotriz)
%     3. agarre         saturado por la ADHERENCIA        |tau| <= tau_traccion
%     4. mecanica       ecuaciones_pendulo_invertido
%
%   --- Por que el motor va afuera y no dentro de b_eje ---
%   Para el modelo LINEAL da igual: la contraelectromotriz tiene la misma forma
%   que la friccion del eje y por eso motor_pendulo_invertido la suma a b_eje, lo
%   que permite linealizar sin tocar nada. Pero para simular con limites NO da
%   igual, porque hay que saturar el PAR entre el motor y la mecanica. Por eso
%   aca se usa p.b_eje_mecanico (solo la friccion) y el motor aparece explicito.
%   Sin saturacion los dos caminos dan exactamente lo mismo; el test lo verifica.
%
%   --- Sobre el limite de agarre: el motor NO llega a romperlo, pero por poco ---
%   Con los parametros vigentes el motor a tension plena pone 6.19 N en el piso
%   contra 6.61 N de friccion disponible: usa el 94 % del agarre y no lo supera.
%   El margen es de un 6 % y descansa en mu = 0.7, que esta SUPUESTO y no medido
%   (ensayo M-1). La saturacion queda igual como red de seguridad, por si cambian
%   la rueda, el piso o el motor; mientras no se active, no altera nada.
%
%   ATENCION a una trampa que ya costo una conclusion equivocada: tau/r NO es la
%   fuerza en el contacto. Daria 17.8 N y haria creer que el motor supera al piso
%   casi tres veces. Es falso: parte del par acelera la inercia reflejada del
%   rotor, que con el reductor 1:20 equivale a 0.44 kg sobre un robot de 1.0 kg.
%   La fuerza real sale de Newton sobre todo el robot. Ver limite_de_traccion.
%
%   El limite de adherencia usa la normal ESTATICA por un factor de seguridad,
%   no la normal instantanea: esta ultima depende de la aceleracion, que depende
%   del par, lo que cerraria un lazo algebraico. R.margen_adherencia informa la
%   comprobacion con la normal real, y R.contacto_valido avisa si aun asi se paso.

    V_bat = p.motor.V_bat;
    tension_aplicada = max(min(tension, V_bat), -V_bat);

    velocidad_relativa = estado(2)/p.r - estado(4);
    par_motor = p.motor.beta_V*tension_aplicada - p.motor.b_m*velocidad_relativa;

    tau_traccion = limite_de_traccion(p);
    par_aplicado = max(min(par_motor, tau_traccion), -tau_traccion);

    p_mecanica = p;
    p_mecanica.b_eje = p.b_eje_mecanico;   % el motor ya no esta adentro
    [derivada, R] = ecuaciones_pendulo_invertido(estado, par_aplicado, p_mecanica);

    R.tension_pedida = tension;
    R.tension_aplicada = tension_aplicada;
    R.satura_bateria = abs(tension - tension_aplicada) > eps(max(1, abs(tension)));
    R.par_motor = par_motor;
    R.par_aplicado = par_aplicado;
    R.tau_traccion = tau_traccion;
    R.patina = abs(par_motor) > tau_traccion;
    R.corriente_por_motor = (tension_aplicada - p.motor.Ke*p.motor.n_g*velocidad_relativa)/p.motor.R_m;
end
