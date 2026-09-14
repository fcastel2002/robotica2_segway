function G = parametros_geometria()
%PARAMETROS_GEOMETRIA  Adaptador de geometría nominal (mm y grados).
%   La fuente numérica común es ../parametros/parametros_fisicos.m.
%   A es el eje del servo (origen), B el pivote del balancin en la cabina, D el extremo de la
%   manivela, C la union acoplador-balancin, P el eje de la rueda. Ver ../geometria/geometria_robot.png.
  carpeta = fullfile(fileparts(mfilename('fullpath')), '..', 'parametros');
  carpeta = char(java.io.File(carpeta).getCanonicalPath());
  estaba = contains([path pathsep], [carpeta pathsep]);
  if ~estaba, addpath(carpeta); end
  limpieza = onCleanup(@() quitar_path_si_corresponde(carpeta, estaba));
  o = parametros_fisicos('corregido');
  G.AB = o.AB;
  G.beta = o.ang_AB;
  G.AD = o.k_AD*o.s_barras;
  G.BC = o.k_BC*o.s_barras;
  G.CD = o.k_CD*o.s_barras;
  G.DP = o.k_DP*o.s_barras;
  G.delta = o.delta;
  G.theta = o.th;
  G.Rw = o.Rw;
end

function quitar_path_si_corresponde(carpeta, estaba)
  if ~estaba && contains([path pathsep], [carpeta pathsep]), rmpath(carpeta); end
end
