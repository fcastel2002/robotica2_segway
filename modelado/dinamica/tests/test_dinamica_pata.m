function tests = test_dinamica_pata
  tests = functiontests(localfunctions);
end

function setupOnce(tc)
  carpeta = fileparts(mfilename('fullpath'));
  tc.TestData.dinamica = fileparts(carpeta);
  tc.TestData.repo = fileparts(fileparts(tc.TestData.dinamica));
  addpath(tc.TestData.dinamica);
  addpath(fullfile(tc.TestData.repo, 'modelado', 'cinematica'));
  addpath(fullfile(tc.TestData.repo, 'simulacion', 'planta_v2'));
end

function test_fuente_comun_de_parametros(tc)
  p = parametros_dinamica_pata('corregido');
  P = parametros_robot('corregido');
  G = parametros_geometria();
  tc.verifyEqual(p.m_total, P.m.total, 'AbsTol', 1e-12);
  tc.verifyEqual(p.tau_max, P.servo.tau_max, 'AbsTol', 1e-12);
  tc.verifyEqual([p.AB p.AD p.BC p.CD p.DP]*1e3, ...
    [G.AB G.AD G.BC G.CD G.DP], 'AbsTol', 1e-12);
  tc.verifyEqual(rad2deg(p.a45), G.beta, 'AbsTol', 1e-12);
  tc.verifyEqual(p.m_total, 1.032, 'AbsTol', 1e-12);
end

function test_cierre_y_cinematica_independiente(tc)
  p = parametros_dinamica_pata();
  theta = linspace(p.theta_min, p.theta_max, 101);
  R = terminos_dinamica_pata(theta, p, 'parado');
  K = cinematica_directa(360-rad2deg(theta));
  errorP = vecnorm(R.P' - K.P*1e-3, 2, 2);
  tc.verifyLessThan(max(errorP), 1e-12);
  tc.verifyGreaterThan(min(R.Ieq), 0);
end

function test_reducciones_estaticas(tc)
  p = parametros_dinamica_pata();
  theta = linspace(p.theta_min, p.theta_max, 101);
  Rb = terminos_dinamica_pata(theta, p, 'banco');
  Rp = terminos_dinamica_pata(theta, p, 'parado');
  Ra = terminos_dinamica_pata(theta, p, 'aire');
  N = p.m_total*p.g/p.n_patas;
  tc.verifyEqual(Rb.dV-N*Rb.wP, Rp.dV, 'AbsTol', 1e-9);
  tc.verifyEqual(Ra.dV, zeros(size(theta)), 'AbsTol', 1e-9);
end

function test_numero_de_patas_no_codificado(tc)
  p = parametros_dinamica_pata();
  p.n_patas = 3;
  p.m_total = p.m_cabina + p.n_patas*(p.m_AD+p.m_BC+p.m_CDP+p.m_P);
  R = terminos_dinamica_pata(deg2rad([10 25 40]), p, 'parado');
  esperado = p.n_patas*R.dV/(p.g*p.m_total);
  tc.verifyEqual(R.cCoM, esperado, 'AbsTol', 1e-14);
  tc.verifyGreaterThan(max(abs(R.cCoM-2*R.dV/(p.g*p.m_total))), 1e-4);
end

function test_ecuacion_de_estado_y_topes(tc)
  p = parametros_dinamica_pata();
  p.tope.habilitado = false;
  x = [deg2rad(25); 0.2]; tau = 0.7;
  [dx, salida] = estado_dinamica_pata(0, x, tau, 0, p, 'parado');
  R = terminos_dinamica_pata(x(1), p, 'parado');
  esperado = (tau-p.b*x(2)-0.5*R.dIeq*x(2)^2-R.dV)/R.Ieq;
  tc.verifyEqual(dx, [x(2); esperado], 'AbsTol', 1e-12);
  tc.verifyEqual(salida.ddtheta, esperado, 'AbsTol', 1e-12);

  p.tope.habilitado = true;
  [~, bajo] = estado_dinamica_pata(0, [p.theta_min-0.01; -0.1], 0, 0, p, 'parado');
  [~, alto] = estado_dinamica_pata(0, [p.theta_max+0.01; 0.1], 0, 0, p, 'parado');
  tc.verifyGreaterThan(bajo.tau_tope, 0);
  tc.verifyLessThan(alto.tau_tope, 0);
  tc.verifyFalse(bajo.en_carrera);
  tc.verifyFalse(alto.en_carrera);
end

function test_supervisor_contacto_vuelo(tc)
  tc.verifyEqual(modo_siguiente_dinamica_pata('parado', 0.1), 'parado');
  tc.verifyEqual(modo_siguiente_dinamica_pata('parado', 0), 'aire');
  tc.verifyEqual(modo_siguiente_dinamica_pata('aire', 5), 'aire');
end

function test_tablas_con_error_controlado(tc)
  p = parametros_dinamica_pata();
  tablas = generar_tablas_dinamica_pata(p, 401);
  consulta = linspace(p.theta_min, p.theta_max, 1601);
  campos = {'Ieq','dIeq','dV','d2V','wP','cCoM','dcCoM','xP','yP'};
  casos = {'banco','parado','aire'};
  for i = 1:numel(casos)
    R = terminos_dinamica_pata(consulta, p, casos{i});
    for j = 1:numel(campos)
      nombre = campos{j};
      aproximado = interp1(tablas.theta, tablas.(casos{i}).(nombre), consulta, 'pchip');
      directo = R.(nombre);
      escala = max(abs(directo));
      errorAbs = max(abs(aproximado-directo));
      if escala < 1e-7
        tc.verifyLessThan(errorAbs, 1e-8, sprintf('%s/%s absoluto', casos{i}, nombre));
      else
        tc.verifyLessThan(errorAbs/escala, 1e-3, sprintf('%s/%s relativo', casos{i}, nombre));
      end
    end
  end
end

function test_derivada_del_potencial(tc)
  p = parametros_dinamica_pata();
  theta = deg2rad(25);
  h = 1e-6;
  casos = {'banco','parado','aire'};
  for i = 1:numel(casos)
    Ep = energia_dinamica_pata(theta+h, 0, p, casos{i});
    Em = energia_dinamica_pata(theta-h, 0, p, casos{i});
    T = terminos_dinamica_pata(theta, p, casos{i});
    derivada = (Ep.potencial-Em.potencial)/(2*h);
    tc.verifyEqual(derivada, T.dV, 'AbsTol', 1e-8, casos{i});
  end
end
