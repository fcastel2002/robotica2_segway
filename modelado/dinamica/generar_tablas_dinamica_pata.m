function tablas = generar_tablas_dinamica_pata(p, n)
%GENERAR_TABLAS_DINAMICA_PATA Genera tablas 1-D trazables para Simulink.
  if nargin < 1 || isempty(p), p = parametros_dinamica_pata(); end
  if nargin < 2 || isempty(n), n = 401; end
  if n < 3 || fix(n) ~= n
    error('generar_tablas_dinamica_pata:Muestras', 'n debe ser un entero mayor o igual que 3.');
  end
  tablas.version = 1;
  tablas.variante = p.variante;
  tablas.fuente_parametros = p.fuente;
  tablas.theta = linspace(p.theta_min, p.theta_max, n)';
  casos = {'banco','parado','aire'};
  for i = 1:numel(casos)
    nombre = casos{i};
    R = terminos_dinamica_pata(tablas.theta', p, nombre);
    tablas.(nombre) = struct('Ieq', R.Ieq', 'dIeq', R.dIeq', ...
      'dV', R.dV', 'd2V', R.d2V', 'wP', R.wP', 'cCoM', R.cCoM', ...
      'dcCoM', R.dcCoM', 'xP', R.xP', 'yP', R.yP');
  end
end
