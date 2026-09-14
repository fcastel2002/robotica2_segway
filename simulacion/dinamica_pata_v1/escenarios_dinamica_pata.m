function E = escenarios_dinamica_pata(nombre, p)
%ESCENARIOS_DINAMICA_PATA Entradas reproducibles del banco reducido.
  if nargin < 1 || isempty(nombre), nombre = 'parado_nominal'; end
  if nargin < 2 || isempty(p), p = parametros_dinamica_pata(); end
  E.nombre = lower(char(nombre));
  E.t = (0:0.005:2.5)';
  suave = @(s) 0.5-0.5*cos(pi*min(max(s,0),1));
  perfil = p.theta_max + (p.theta_min-p.theta_max)*suave((E.t-0.2)/0.6) ...
    + (p.theta_max-p.theta_min)*suave((E.t-1.2)/0.6);
  E.theta0 = p.theta_max;
  E.dtheta0 = 0;
  E.tau_perturbacion = zeros(size(E.t));
  switch E.nombre
    case 'banco_nominal'
      E.caso = 1;
      E.normal = (p.m_total*p.g/p.n_patas)*ones(size(E.t));
      E.theta_ref = perfil;
    case 'parado_nominal'
      E.caso = 2;
      E.normal = zeros(size(E.t));
      E.theta_ref = perfil;
    case 'aire_nominal'
      E.caso = 3;
      E.normal = zeros(size(E.t));
      E.theta_ref = perfil;
    case 'estatico_25'
      E.caso = 2;
      E.theta0 = deg2rad(25);
      E.theta_ref = E.theta0*ones(size(E.t));
      E.normal = zeros(size(E.t));
    case {'banco_validacion','parado_validacion','aire_validacion'}
      E.theta0 = deg2rad(25);
      E.theta_ref = E.theta0 + deg2rad(3)*sin(2*pi*0.5*E.t);
      E.caso = find(strcmp(E.nombre, ...
        {'banco_validacion','parado_validacion','aire_validacion'}));
      E.normal = zeros(size(E.t));
      if E.caso == 1
        E.normal = (p.m_total*p.g/p.n_patas)*ones(size(E.t));
      end
    otherwise
      error('escenarios_dinamica_pata:Nombre', 'Escenario "%s" desconocido.', E.nombre);
  end
  E.caso_serie = E.caso*ones(size(E.t));
  E.t_final = E.t(end);
end
