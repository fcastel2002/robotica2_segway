function tests = test_dinamica_v1
  tests = functiontests(localfunctions);
end
function setupOnce(~)
  aqui = fileparts(mfilename('fullpath'));
  addpath(fullfile(aqui,'..')); addpath(fullfile(aqui,'..','..','modelo_base'));
end
function test_coincide_con_modelo_base(tc)
  Pz = params_robot('s', 80, 'Dw', 80); pvz = empaquetar(Pz);
  rng(3);
  for k = 1:50
    q = [randn; 0.3*randn; Pz.din.l0 + 0.02*randn]; qd = 0.5*randn(3,1); u = [0.2*randn; 0.5*randn];
    qdd_z = dinamica_sl(q, qd, u, pvz);
    [M, C, Gv] = dinamica_v1_gen(q(2), q(3), qd(2), qd(3), Pz.din.m_b, Pz.din.m_w, Pz.din.J_b, Pz.g, 0);
    G = Pz.din.Gfit(1) + Pz.din.Gfit(2)*q(3);
    M(1,1) = M(1,1) + Pz.din.J_w/Pz.Rw^2;
    DD = [Pz.b.rueda/Pz.Rw^2*qd(1); Pz.b.pitch*qd(2); Pz.b.pata*qd(3)];
    QQ = [u(1)/Pz.Rw; -u(1); u(2)/G];
    qdd = M \ (QQ - C - Gv - DD);
    tc.verifyEqual(qdd, qdd_z, 'RelTol', 1e-9, 'AbsTol', 1e-9);
  end
end
function test_pendiente(tc)
  m_b = 0.75; m_w = 0.25; g = 9.81; alpha = 0.1;
  [~, ~, Gv] = dinamica_v1_gen(0, 0.15, 0, 0, m_b, m_w, 3e-3, g, alpha);
  tc.verifyEqual(Gv(1), (m_b + m_w)*g*sin(alpha), 'RelTol', 1e-12);
  tc.verifyEqual(Gv(2), m_b*g*0.15*sin(alpha), 'RelTol', 1e-12);
  tc.verifyEqual(Gv(3), m_b*g*cos(alpha), 'RelTol', 1e-12);
end
