function G = parametros_geometria()
%PARAMETROS_GEOMETRIA  Cotas del cuatro barras de la pata segun el CAD (mm y grados).
%   Unica fuente de los valores: si cambia el CAD, se cambia aca.
%   A es el eje del servo (origen), B el pivote del balancin en la cabina, D el extremo de la
%   manivela, C la union acoplador-balancin, P el eje de la rueda. Ver ../geometria/geometria_robot.png.
  G.AB    = 100;    % bancada A-B [mm]                     (cabeza_v31)
  G.beta  = 45;     % angulo de A->B desde +x [grados]     (cabeza_v31)
  G.AD    = 140;    % manivela, la mueve el servo [mm]     (eslabon_AD)
  G.BC    = 135;    % balancin [mm]                        (eslabon_BC)
  G.CD    = 51;     % acoplador, tramo C-D [mm]            (eslabon_CDP)
  G.DP    = 140;    % acoplador, tramo D-P [mm]            (eslabon_CDP)
  G.delta = 164;    % angulo en D, de D->C a D->P, antihorario [grados] (el plano acota el suplementario, 16)
  G.theta = [320 350];   % recorrido del servo [grados]: 320 = pata estirada, 350 = plegada
  G.Rw    = 33;     % radio de rueda [mm]                  (wheel, diametro 66)
end
