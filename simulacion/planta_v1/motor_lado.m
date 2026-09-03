function [tau_g, dwm, di, i_eff, J_add] = motor_lado(V, i, wm, thm, ww, thw, pv)
%MOTOR_LADO  Motor DC + reductor de un lado: par sobre la rueda y derivadas del rotor y la corriente.
%   V tension aplicada [V], i corriente [A], wm/thm velocidad y angulo del rotor (lado motor),
%   ww/thw velocidad y angulo de la rueda. Con pv(22)=1 el reductor es rigido (rotor unido a la
%   rueda; la inercia N^2*J_r se devuelve en J_add para sumarla a la rueda); con 0 hay eje elastico
%   con juego (dwm es la derivada de la velocidad del rotor). Las perdidas del reductor se
%   representan con friccion de Coulomb (tau_c) y viscosa (b_m) del lado del rotor.
%#codegen
  R_m=pv(14); L_m=pv(15); Kt=pv(16); Ke=pv(17); N=pv(18); J_r=pv(19); b_m=pv(20); tau_c=pv(21);
  rigido = pv(22) > 0.5; k_g=pv(23); c_g=pv(24); juego=pv(25);
  if rigido, wm = N*ww; end
  if L_m <= 0
    i_eff = (V - Ke*wm)/R_m; di = 0;
  else
    i_eff = i; di = (V - R_m*i - Ke*wm)/L_m;
  end
  tau_e = Kt*i_eff;
  tau_fr = tau_c*tanh(wm/0.5) + b_m*wm;
  if rigido
    tau_g = N*(tau_e - tau_fr); dwm = 0; J_add = N^2*J_r;
  else
    e = thm/N - thw;
    dz = sign(e)*max(0, abs(e) - juego/2);
    tau_g = k_g*dz + c_g*(wm/N - ww);
    dwm = (tau_e - tau_fr - tau_g/N)/J_r; J_add = 0;
  end
end
