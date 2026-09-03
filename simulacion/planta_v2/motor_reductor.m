function [tau_g, dwm, di, i_ef, J_extra] = motor_reductor(V, i, wm, thm, ww, thw, par)
%MOTOR_REDUCTOR  Motor DC + reductor de un lado: par sobre la rueda y derivadas del rotor y la corriente.
%   V tension aplicada [V]; i corriente [A]; wm, thm velocidad y angulo del rotor (lado motor);
%   ww, thw velocidad y angulo de la rueda. Con par.motor.rigido = 1 el rotor va unido a la rueda y su
%   inercia reflejada relacion^2 * J_rotor se devuelve en J_extra para sumarla a la rueda. Con 0 hay
%   eje elastico con juego y el rotor tiene su propia ecuacion (dwm). Las perdidas del reductor se
%   representan como friccion de Coulomb y viscosa del lado del rotor.
%#codegen
  m = par.motor; n = m.relacion;
  if m.rigido > 0.5, wm = n*ww; end
  if m.L <= 0
    i_ef = (V - m.Ke*wm)/m.R; di = 0;
  else
    i_ef = i; di = (V - m.R*i - m.Ke*wm)/m.L;
  end
  tau_e = m.Kt*i_ef;
  tau_fr = m.tau_coulomb*tanh(wm/0.5) + m.b_rotor*wm;
  if m.rigido > 0.5
    tau_g = n*(tau_e - tau_fr); dwm = 0; J_extra = n^2*m.J_rotor;
  else
    e = thm/n - thw;
    dz = sign(e)*max(0, abs(e) - m.juego/2);
    tau_g = m.k_eje*dz + m.c_eje*(wm/n - ww);
    dwm = (tau_e - tau_fr - tau_g/n)/m.J_rotor; J_extra = 0;
  end
end
