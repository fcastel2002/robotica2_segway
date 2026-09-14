function R = energia_dinamica_pata(theta, dtheta, p, caso)
%ENERGIA_DINAMICA_PATA Energía mecánica por servo del modelo reducido.
%   El cero de potencial es arbitrario. Las posiciones absolutas respetan
%   la restricción cinemática de cada caso: A fijo, P fijo o CoM fijo.
  forma = size(theta);
  theta = theta(:)';
  if isscalar(dtheta)
    dtheta = repmat(dtheta, size(theta));
  else
    dtheta = dtheta(:)';
  end
  if numel(theta) ~= numel(dtheta)
    error('energia_dinamica_pata:Dimensiones', ...
      'theta y dtheta deben ser escalares o tener la misma cantidad de elementos.');
  end

  T = terminos_dinamica_pata(theta, p, caso);
  suma_masas_y = p.m_AD*T.GAD(2,:) + p.m_BC*T.GBC(2,:) ...
    + p.m_CDP*T.GCDP(2,:) + p.m_P*T.P(2,:);
  switch lower(char(caso))
    case 'banco'
      yA = zeros(size(theta));
    case 'parado'
      yA = -T.P(2,:);
    case 'aire'
      yA = -p.n_patas*suma_masas_y/p.m_total;
    otherwise
      error('energia_dinamica_pata:Caso', ...
        'Caso "%s" desconocido; usar banco, parado o aire.', char(caso));
  end

  masa_por_servo = p.m_total/p.n_patas;
  potencial = p.g*(masa_por_servo*yA + suma_masas_y);
  cinetica = 0.5*T.Ieq.*dtheta.^2;
  R.cinetica = reshape(cinetica, forma);
  R.potencial = reshape(potencial, forma);
  R.total = reshape(cinetica + potencial, forma);
end
