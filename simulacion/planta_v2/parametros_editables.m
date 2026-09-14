function o = parametros_editables(variante)
%PARAMETROS_EDITABLES  Adaptador legado hacia la fuente común de parámetros físicos.
%   Los valores se editan en modelado/parametros/parametros_fisicos.m.
  if nargin < 1 || isempty(variante), variante = 'corregido'; end
  carpeta = fullfile(fileparts(mfilename('fullpath')), '..', '..', 'modelado', 'parametros');
  carpeta = char(java.io.File(carpeta).getCanonicalPath());
  estaba = contains([path pathsep], [carpeta pathsep]);
  if ~estaba, addpath(carpeta); end
  limpieza = onCleanup(@() quitar_path_si_corresponde(carpeta, estaba));
  o = parametros_fisicos(variante);
end

function quitar_path_si_corresponde(carpeta, estaba)
  if ~estaba && contains([path pathsep], [carpeta pathsep]), rmpath(carpeta); end
end
