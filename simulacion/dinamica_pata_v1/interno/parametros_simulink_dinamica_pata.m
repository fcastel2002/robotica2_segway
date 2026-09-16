function [par_pata, p] = parametros_simulink_dinamica_pata(variante, n)
%PARAMETROS_SIMULINK_DINAMICA_PATA Tablas y escalares numéricos del banco.
  if nargin < 1 || isempty(variante), variante = 'corregido'; end
  if nargin < 2 || isempty(n), n = 4001; end
  carpeta_banco = fileparts(fileparts(mfilename('fullpath')));
  raiz = fileparts(fileparts(carpeta_banco));
  addpath(fullfile(raiz, 'modelado', 'dinamica'));
  p = parametros_dinamica_pata(variante);
  T = generar_tablas_dinamica_pata(p, n);
  casos = {'banco','parado','aire'};
  campos = {'Ieq','dIeq','dV','d2V','wP','cCoM','dcCoM','xP','yP'};
  par_pata.theta = T.theta;
  par_pata.casos = [1 2 3];
  for j = 1:numel(campos)
    nombre = campos{j};
    par_pata.(nombre) = zeros(n, numel(casos));
    for i = 1:numel(casos)
      par_pata.(nombre)(:,i) = T.(casos{i}).(nombre);
    end
  end
  par_pata.b = p.b;
  par_pata.g = p.g;
  par_pata.masa_por_pata = p.m_total/p.n_patas;
  par_pata.theta_min = p.theta_min;
  par_pata.theta_max = p.theta_max;
  par_pata.k_tope = p.tope.k;
  par_pata.c_tope = p.tope.c;
  par_pata.tau_max = p.tau_max;
  par_pata.Kp = p.Kp;
  par_pata.Kd = p.Kd;
  par_pata.w_nl = p.w_nl;
end
