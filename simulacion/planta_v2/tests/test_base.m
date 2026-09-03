function tests = test_base
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_parametros_y_struct(tc)
  P = parametros_robot('corregido'); par = parametros_simulink(P);
  tc.verifyEqual(par.cuerpo.masa, P.din.m_b); tc.verifyEqual(par.rueda.radio, 0.033, 'AbsTol', 1e-12);
  tc.verifyEqual(par.motor.relacion, 21.3); tc.verifyEqual(numel(par.pata.tabla_l), 21);
  tc.verifyEqual(par.piso.n, 0); tc.verifyEqual(par.pata.flexor_activo, 0);
  P2 = parametros_robot('cad', 'piso_n', 3, 'flexor', true, 'k_flexor', 900); par2 = parametros_simulink(P2);
  tc.verifyEqual(par2.piso.n, 3); tc.verifyEqual(par2.pata.flexor_activo, 1); tc.verifyEqual(par2.pata.k_flexor, 900);
  tc.verifyEqual(par.control.K1, zeros(1,4));
  % la estructura no debe tener strings ni celdas (Simulink no las admite como parametro)
  tc.verifyTrue(solo_numerico(par));
end
function test_perfil_plano_y_escalones(tc)
  piso = struct('x0', 0.5, 'alto', 0.16, 'ancho', 0.30, 'n', 2); R = 0.033;
  [delta, nx, ny, px, py] = perfil_piso(0.2, R - 0.001, R, piso);            % sobre el primer descanso
  tc.verifyEqual(delta, 0.001, 'AbsTol', 1e-12); tc.verifyEqual([nx ny], [0 1], 'AbsTol', 1e-12); tc.verifyEqual([px py], [0.2 0], 'AbsTol', 1e-12);
  [delta, ~, ny] = perfil_piso(0.65, -0.16 + R, R, piso);                      % sobre el segundo descanso, justo apoyado
  tc.verifyEqual(delta, 0, 'AbsTol', 1e-12); tc.verifyEqual(ny, 1, 'AbsTol', 1e-12);
  [delta, ~, ~, px, py] = perfil_piso(5, -0.32 + R/2, R, piso);                % ultimo descanso, infinito
  tc.verifyEqual(delta, R/2, 'AbsTol', 1e-12); tc.verifyEqual([px py], [5 -0.32], 'AbsTol', 1e-12);
  [delta, nx, ny, px, py] = perfil_piso(0.5 + R*cos(pi/4), 0 + R*sin(pi/4), R, piso);   % sobre el borde: normal radial
  tc.verifyEqual(delta, 0, 'AbsTol', 1e-9); tc.verifyEqual([nx ny], [cos(pi/4) sin(pi/4)], 'AbsTol', 1e-9); tc.verifyEqual([px py], [0.5 0], 'AbsTol', 1e-9);
  [delta, nx, ny] = perfil_piso(0.5 + 0.02, -0.08, R, piso);                   % contra la contrahuella: normal horizontal
  tc.verifyEqual(delta, R - 0.02, 'AbsTol', 1e-12); tc.verifyEqual([nx ny], [1 0], 'AbsTol', 1e-12);
  delta = perfil_piso(0.3, 0.2, R, piso);                                      % en el aire
  tc.verifyLessThan(delta, 0);
  piso0 = struct('x0', 0.5, 'alto', 0.16, 'ancho', 0.30, 'n', 0);
  [delta, nx, ny] = perfil_piso(3, R - 0.002, R, piso0); tc.verifyEqual(delta, 0.002, 'AbsTol', 1e-12); tc.verifyEqual([nx ny], [0 1]);
end
function test_contacto_plano_como_v1(tc)
  P = parametros_robot('corregido'); par = parametros_simulink(P); R = P.Rw;
  % en reposo, hundida lo justo: N = peso total
  d0 = P.m.total*P.g/(2*par.contacto.k);
  [Fx, Fy, tL, tR, N] = contacto_rueda(0, R - d0, 0, 0, 0, 0, par);
  tc.verifyEqual(N, P.m.total*P.g, 'RelTol', 1e-9); tc.verifyEqual(Fy, N, 'RelTol', 1e-9); tc.verifyEqual([Fx tL tR], [0 0 0], 'AbsTol', 1e-12);
  % rueda que gira mas rapido que lo que avanza: empuja hacia adelante y frena la rueda
  [Fx, ~, tL, ~, N, fL] = contacto_rueda(0, R - d0, 0.1, 0, 0.1/R + 1, 0.1/R, par);
  tc.verifyGreaterThan(fL, 0); tc.verifyEqual(tL, -R*fL, 'AbsTol', 1e-12); tc.verifyGreaterThan(Fx, 0);
  tc.verifyEqual(fL, par.rueda.mu*N/2*tanh(R/par.rueda.v0) - par.rueda.c_v*R, 'RelTol', 1e-9);
  % en el aire: nada
  [Fx, Fy, tL, tR, N] = contacto_rueda(0, R + 0.05, 0, -1, 0, 0, par);
  tc.verifyEqual([Fx Fy tL tR N], zeros(1,5));
end
function test_motor(tc)
  P = parametros_robot('cad'); par = parametros_simulink(P); par.motor.L = 0;
  [tau_g, dwm, di, i, J_extra] = motor_reductor(12, 0, 0, 0, 0, 0, par);
  tc.verifyEqual(i, 12/P.motor.R, 'RelTol', 1e-9);
  tc.verifyEqual(tau_g, P.motor.N*P.motor.Kt*12/P.motor.R, 'RelTol', 1e-9);
  tc.verifyEqual([dwm di], [0 0]); tc.verifyEqual(J_extra, P.motor.N^2*P.motor.J_r, 'RelTol', 1e-12);
end
function test_dinamica_cuerpo(tc)
  m_b = 0.78; m_w = 0.25; J_b = 2.8e-3; g = 9.81;
  [M, C, Gv] = dinamica_cuerpo_gen(0.1, 0.15, 0.3, 0.05, m_b, m_w, J_b, g, 0);
  tc.verifyEqual(size(M), [4 4]); tc.verifyEqual(M, M', 'AbsTol', 1e-12);
  tc.verifyEqual(M(1,1), m_b + m_w, 'AbsTol', 1e-12); tc.verifyEqual(M(2,2), m_b + m_w, 'AbsTol', 1e-12);
  tc.verifyEqual(M(1,2), 0, 'AbsTol', 1e-12);
  tc.verifyEqual(Gv(2), (m_b + m_w)*g, 'RelTol', 1e-12);                     % el peso total cae sobre y
  tc.verifyEqual(Gv(3), -m_b*g*0.15*sin(0.1), 'RelTol', 1e-9);              % vuelco del pendulo
  tc.verifyEqual(Gv(4), m_b*g*cos(0.1), 'RelTol', 1e-9);
  % las filas x y phi coinciden con la version plana (v1) en alpha = 0
  addpath(fullfile(fileparts(mfilename('fullpath')),'..','..','planta_v1'));
  [M1, C1, G1] = dinamica_v1_gen(0.1, 0.15, 0.3, 0.05, m_b, m_w, J_b, g, 0);
  tc.verifyEqual(M([1 3 4],[1 3 4]), M1, 'AbsTol', 1e-12); tc.verifyEqual(C([1 3 4]), C1, 'AbsTol', 1e-12); tc.verifyEqual(Gv([1 3 4]), G1, 'AbsTol', 1e-12);
end
function ok = solo_numerico(s)
  ok = true; f = fieldnames(s);
  for i = 1:numel(f)
    v = s.(f{i});
    if isstruct(v), ok = ok && solo_numerico(v);
    elseif ~(isnumeric(v) || islogical(v)), ok = false; end
  end
end
