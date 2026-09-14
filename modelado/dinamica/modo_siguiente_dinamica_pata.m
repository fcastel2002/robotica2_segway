function siguiente = modo_siguiente_dinamica_pata(actual, normal_estimada)
%MODO_SIGUIENTE_DINAMICA_PATA Transición explícita apoyo-vuelo del banco.
  actual = lower(char(actual));
  if strcmp(actual, 'parado') && normal_estimada <= 0
    siguiente = 'aire';
  else
    siguiente = actual;
  end
end
