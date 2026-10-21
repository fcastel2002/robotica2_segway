%EXPORTAR_DIAGRAMAS  Saca una imagen de cada nivel del modelo, para la guia.
%
%   Deja los PNG en diagramas/. Los usa docs/modelo/guia_simulink.tex, asi que
%   si se cambia el modelo conviene volver a correr esto y recompilar la guia.
%
%   Correr:  exportar_diagramas
%
%   Ver tambien CONSTRUIR_SEGWAY_COMPLETO, INICIAR_SEGWAY.

aqui = fileparts(mfilename('fullpath'));
if isempty(aqui), aqui = pwd; end
destino = fullfile(aqui, 'diagramas');
if ~exist(destino, 'dir'), mkdir(destino); end
addpath(aqui);

modelo = 'segway_completo';
archivo = fullfile(aqui, [modelo '.slx']);
if ~exist(archivo, 'file')
    construir_segway_completo(aqui, modelo);
end
if bdIsLoaded(modelo), close_system(modelo, 0); end
load_system(archivo);

% Las notas del diagrama estiran mucho el recuadro y hacen que los bloques salgan
% diminutos en el PDF. Se borran SOLO en esta copia en memoria (el .slx no se guarda),
% porque el texto de las notas ya esta en la guia.
% OJO: las AREAS tambien son anotaciones y esas hay que CONSERVARLAS, porque son
% las que agrupan el diagrama. Se distinguen porque el titulo de un area es una
% sola linea corta, mientras que las notas son varios parrafos.
todas = find_system(modelo, 'LookUnderMasks', 'all', 'FollowLinks', 'on', ...
    'FindAll', 'on', 'Type', 'annotation');
borradas = 0;
for i = 1:numel(todas)
    texto = get_param(todas(i), 'Name');
    if contains(texto, newline) || numel(texto) > 80
        try
            delete(todas(i));
            borradas = borradas + 1;
        catch
        end
    end
end
fprintf('se ocultaron %d notas de texto; quedan %d areas\n', borradas, numel(todas) - borradas);

% Los diagramas de Simulink son anchos, asi que en el PDF se achican mucho y las
% etiquetas quedan ilegibles. Se agranda la letra ANTES de exportar: al escalar,
% el texto queda proporcionalmente mas grande. Tampoco se guarda.
bloques = find_system(modelo, 'LookUnderMasks', 'all', 'FollowLinks', 'on', ...
    'Type', 'Block');
for i = 1:numel(bloques)
    try, set_param(bloques{i}, 'FontSize', 16); catch, end  %#ok<CTCH,NOCOM>
end
areas = find_system(modelo, 'LookUnderMasks', 'all', 'FollowLinks', 'on', ...
    'FindAll', 'on', 'Type', 'annotation');
for i = 1:numel(areas)
    try, set_param(areas(i), 'FontSize', 13); catch, end  %#ok<CTCH,NOCOM>
end

niveles = { ...
    modelo,                                                       'arriba';
    [modelo '/Consignas'],                                        'consignas';
    [modelo '/Control'],                                          'control';
    [modelo '/Actuadores'],                                       'actuadores';
    [modelo '/Actuadores/Motor de rueda IZQUIERDA'],              'motor_rueda';
    [modelo '/Actuadores/Servo de pata IZQUIERDA'],               'servo_pata';
    [modelo '/Planta del robot'],                                 'planta';
    [modelo '/Planta del robot/Cuanto pesa y cuanta inercia tiene'], 'postura';
    [modelo '/Planta del robot/Suma de FUERZAS horizontales'],    'fuerzas';
    [modelo '/Planta del robot/Suma de MOMENTOS sobre el cuerpo'],'momentos';
    [modelo '/Planta del robot/Resolver las dos aceleraciones'],  'resolver';
    [modelo '/Planta del robot/Integrar hasta el estado'],        'integrar';
    [modelo '/Sensores'],                                         'sensores';
    [modelo '/Sensores/Encoders de las ruedas'],                  'encoders';
    [modelo '/Sensores/IMU MPU-6050'],                            'imu'};

for i = 1:size(niveles, 1)
    salida = fullfile(destino, [niveles{i,2} '.png']);
    try
        print(['-s' niveles{i,1}], '-dpng', '-r140', salida);
        fprintf('  %s\n', salida);
    catch ME
        warning('exportar_diagramas:nivel', '%s: %s', niveles{i,2}, ME.message);
    end
end
close_system(modelo, 0);   % sin guardar: el .slx conserva sus notas
fprintf('\n%d diagramas en %s\n', size(niveles,1), destino);
