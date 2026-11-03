function tests = test_segway_ajustado
%TEST_SEGWAY_AJUSTADO  Comprueba el modelo AJUSTADO del Segway en Simulink (3/11/2026).
%
%   1. que tenga las etapas y los cuatro motores del original, solo con bloques nativos
%   2. que use los numeros de la variante 'ajustada'
%   3. que repita la prueba del 3/11 (onda cuadrada de +-1,5 grados en la ref, patas en 20)
%      dentro de lo medido: el cabeceo llega a 3-6 grados y el robot va y viene 40-110 mm
%
%   Correr:  runtests('test_segway_ajustado')
    tests = functiontests(localfunctions);
end

function setupOnce(tc)
    aqui = fileparts(fileparts(mfilename('fullpath')));
    tc.TestData.aqui = aqui;
    tc.TestData.modelo = 'segway_ajustado';
    evalin('base', sprintf('run(''%s'')', fullfile(aqui, 'INICIAR_SEGWAY_AJUSTADO.m')));
    close all
end

function teardownOnce(tc)
    if bdIsLoaded(tc.TestData.modelo), close_system(tc.TestData.modelo, 0); end
end

function test_tiene_las_etapas_y_los_cuatro_motores(tc)
    load_system(fullfile(tc.TestData.aqui, 'segway_ajustado.slx'));
    for e = {'Consignas', 'Control', 'Actuadores', 'Planta del robot', 'Sensores'}
        tc.verifyNotEmpty(find_system(tc.TestData.modelo, 'SearchDepth', 1, 'BlockType', 'SubSystem', ...
            'Name', e{1}), sprintf('falta la etapa "%s"', e{1}));
    end
    for m = {'Motor de rueda IZQUIERDA', 'Motor de rueda DERECHA', 'Servo de pata IZQUIERDA', 'Servo de pata DERECHA'}
        tc.verifyNotEmpty(find_system([tc.TestData.modelo '/Actuadores'], 'SearchDepth', 1, ...
            'BlockType', 'SubSystem', 'Name', m{1}), sprintf('falta "%s"', m{1}));
    end
end

function test_solo_bloques_nativos(tc)
    load_system(fullfile(tc.TestData.aqui, 'segway_ajustado.slx'));
    codigo = [find_system(tc.TestData.modelo, 'LookUnderMasks', 'all', 'SFBlockType', 'MATLAB Function'); ...
              find_system(tc.TestData.modelo, 'LookUnderMasks', 'all', 'BlockType', 'S-Function'); ...
              find_system(tc.TestData.modelo, 'LookUnderMasks', 'all', 'BlockType', 'MATLABFcn')];
    tc.verifyEmpty(codigo, 'el modelo tiene bloques de codigo');
end

function test_usa_la_variante_ajustada(tc)
    f = evalin('base', 'fisicos');
    tc.verifyEqual(f.pata_cero, 20.4);
    tc.verifyEqual(evalin('base', 'V_motor'), f.V_bat - f.caida_driver, 'AbsTol', 1e-12);
    tc.verifyGreaterThan(evalin('base', 'tau_seco_motor'), 0);
end

function test_repite_la_prueba_del_3_11(tc)
    z = evalin('base', 'z_sl');  t = evalin('base', 't');  t0 = evalin('base', 't_onda');
    sel = t > t0;
    phi_max = max(abs(rad2deg(z(sel, 3))));
    x = 1e3*z(sel, 1);
    tc.verifyGreaterThan(phi_max, 3);  tc.verifyLessThan(phi_max, 6);
    tc.verifyGreaterThan(max(x) - min(x), 80);  tc.verifyLessThan(max(x) - min(x), 220);
end
