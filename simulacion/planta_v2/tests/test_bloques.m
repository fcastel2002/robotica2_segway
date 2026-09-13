function tests = test_bloques
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..'));
end
function test_construye_sin_matlab_function(tc)
  P = parametros_robot('corregido'); C = disenar_lqr_robot(P); E = escenarios_robot('equilibrio_8', P); E.tf = 3;
  mdl = construir_robot_bloques(P, C, E);
  tc.verifyTrue(bdIsLoaded(mdl));
  tc.verifyEqual(numel(find_system(mdl, 'SearchDepth', 1, 'BlockType', 'SubSystem')), 6);
  emf = find_system(mdl, 'LookUnderMasks', 'all', 'BlockType', 'SubSystem', 'SFBlockType', 'MATLAB Function');
  tc.verifyEmpty(emf, 'no debe haber bloques MATLAB Function');
  tc.verifyEmpty(find_system(mdl, 'BlockType', 'Fcn'));
  for nom = {'comandos','medidas','estados','referencias','perturbaciones','estimaciones'}
    tc.verifyNotEmpty(find_system(mdl, 'FindAll', 'on', 'SearchDepth', 1, 'Type', 'line', 'Name', nom{1}), ['falta la senal ' nom{1}]);
  end
end
function test_equilibrio_igual_al_modelo_de_referencia(tc)
  % con ruido y encoder real: mismas trayectorias salvo el "chatter" de la cuantizacion del encoder
  P = parametros_robot('corregido'); C = disenar_lqr_robot(P); E = escenarios_robot('equilibrio_8', P); E.tf = 3;
  Sb = simular_slx(P, C, E, 'robot_segway_bloques'); Sr = simular_slx(P, C, E, 'robot_segway');
  tc.verifyFalse(Sb.resumen.cayo);
  tc.verifyLessThan(max(abs(Sb.X(:,3) - Sr.X(:,3)))*180/pi, 0.3);        % misma inclinacion (grados)
  tc.verifyLessThan(max(abs(Sb.X(:,1) - Sr.X(:,1))), 0.005);              % misma posicion (m)
  tc.verifyEqual(size(Sb.X, 2), 20); tc.verifyEqual(size(Sb.y, 2), 18); tc.verifyEqual(size(Sb.est, 2), 7);
  % sin ruido ni cuantizacion los dos modelos son la misma ecuacion: coinciden al nivel del solver
  P = parametros_robot('corregido', 'gyro_rms_dps', 0, 'acc_rms_g', 0, 'gyro_bias_dps', 0, 'CPR_motor', 1e5); C = disenar_lqr_robot(P);
  Sb = simular_slx(P, C, E, 'robot_segway_bloques'); Sr = simular_slx(P, C, E, 'robot_segway');
  tc.verifyLessThan(max(abs(Sb.X(:,3) - Sr.X(:,3))), 1e-3);               % rad
  tc.verifyLessThan(max(abs(Sb.X(:,1) - Sr.X(:,1))), 1e-3);               % m
  tc.verifyLessThan(max(abs(Sb.u(:,1) - Sr.u(:,1))), 0.05);               % V
  tc.verifyLessThan(max(max(abs(Sb.est - Sr.est))), 5e-3);
end
function test_escalera_y_flexor(tc)
  % Los impactos son sensibles al paso del solver (el modelo por bloques detecta cruces por cero y el
  % de referencia no), asi que se comparan resultados globales, no los picos de la normal.
  for esc = {'escalera', 'escalera_flexor'}
    P0 = parametros_robot('corregido'); E = escenarios_robot(esc{1}, P0);
    P = parametros_robot('corregido', E.overrides{:}); C = disenar_lqr_robot(P); E = escenarios_robot(esc{1}, P);
    Sb = simular_slx(P, C, E, 'robot_segway_bloques'); Sr = simular_slx(P, C, E, 'robot_segway');
    tc.verifyFalse(Sb.resumen.cayo, esc{1}); tc.verifyEqual(Sb.resumen.escalones_bajados, 3, esc{1});
    tc.verifyEqual(Sb.resumen.phi_max_deg, Sr.resumen.phi_max_deg, 'RelTol', 0.10, esc{1});
    tc.verifyEqual(Sb.resumen.x_fin, Sr.resumen.x_fin, 'AbsTol', 0.05, esc{1});
    tc.verifyEqual(Sb.resumen.t_vuelo, Sr.resumen.t_vuelo, 'AbsTol', 0.05, esc{1});
    tc.verifyEqual(Sb.resumen.a_cuerpo_max_g, Sr.resumen.a_cuerpo_max_g, 'RelTol', 0.25, esc{1});
    tc.verifyGreaterThan(Sb.resumen.N_max_g, 5, esc{1});                   % hubo impactos en los dos
    if P.flexor.activo
      tc.verifyGreaterThan(Sb.resumen.flexor_max_mm, 5);
      tc.verifyEqual(Sb.resumen.flexor_max_mm, Sr.resumen.flexor_max_mm, 'RelTol', 0.25);
    end
  end
end
function test_flexor_sin_impactos_coincide(tc)
  % agachar y pararse con el flexor activo, sin ruido: ejercita el flexor y los topes sin impactos
  P = parametros_robot('corregido', 'flexor', true, 'gyro_rms_dps', 0, 'acc_rms_g', 0, 'gyro_bias_dps', 0, 'CPR_motor', 1e5); C = disenar_lqr_robot(P);
  E = escenarios_robot('agachar', P);
  Sb = simular_slx(P, C, E, 'robot_segway_bloques'); Sr = simular_slx(P, C, E, 'robot_segway');
  tc.verifyFalse(Sb.resumen.cayo);
  tc.verifyLessThan(max(abs(Sb.X(:,3) - Sr.X(:,3))), 2e-3);
  tc.verifyLessThan(max(abs(Sb.X(:,4) - Sr.X(:,4))), 1e-3);               % largo de pata
  tc.verifyLessThan(max(abs(Sb.X(:,19) - Sr.X(:,19))), 1e-3);             % largo del mecanismo (flexor)
end
function test_pendiente_y_sin_encoder(tc)
  P = parametros_robot('corregido'); C = disenar_lqr_robot(P);
  E = escenarios_robot('pendiente_5', P); E.tf = 3;
  Sb = simular_slx(P, C, E, 'robot_segway_bloques'); Sr = simular_slx(P, C, E, 'robot_segway');
  tc.verifyFalse(Sb.resumen.cayo); tc.verifyLessThan(max(abs(Sb.X(:,3) - Sr.X(:,3)))*180/pi, 0.3);
  E = escenarios_robot('sin_encoder', P); P2 = parametros_robot('corregido', E.overrides{:}); C2 = disenar_lqr_robot(P2); E = escenarios_robot('sin_encoder', P2);
  Sb = simular_slx(P2, C2, E, 'robot_segway_bloques'); Sr = simular_slx(P2, C2, E, 'robot_segway');
  tc.verifyEqual(Sb.resumen.cayo, Sr.resumen.cayo);
end
