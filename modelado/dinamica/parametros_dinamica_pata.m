function p = parametros_dinamica_pata(variante, varargin)
%PARAMETROS_DINAMICA_PATA Adapta la fuente física común al modelo reducido en SI.
%   p = parametros_dinamica_pata() usa el baseline nominal 'corregido'.
%   p = parametros_dinamica_pata(variante, nombre, valor, ...) permite ensayos
%   sin modificar la fuente; los overrides conservan las unidades de ingeniería
%   declaradas en parametros_fisicos.m.
  if nargin < 1 || isempty(variante), variante = 'corregido'; end
  carpeta = fullfile(fileparts(mfilename('fullpath')), '..', 'parametros');
  carpeta = char(java.io.File(carpeta).getCanonicalPath());
  estaba = contains([path pathsep], [carpeta pathsep]);
  if ~estaba, addpath(carpeta); end
  limpieza = onCleanup(@() quitar_path_si_corresponde(carpeta, estaba));
  o = parametros_fisicos(variante);
  if mod(numel(varargin), 2) ~= 0
    error('parametros_dinamica_pata:Overrides', 'Los overrides deben ser pares nombre/valor.');
  end
  for i = 1:2:numel(varargin)
    nombre = varargin{i};
    if ~isfield(o, nombre)
      error('parametros_dinamica_pata:Parametro', 'Parámetro desconocido "%s".', nombre);
    end
    o.(nombre) = varargin{i+1};
  end

  mm = 1e-3; gr = 1e-3; d2r = pi/180;
  p.variante = lower(char(variante));
  p.fuente = 'modelado/parametros/parametros_fisicos.m';
  p.unidades = 'SI (m, kg, s, rad, N)';
  p.AB = o.AB*mm;
  p.AD = o.k_AD*o.s_barras*mm;
  p.BC = o.k_BC*o.s_barras*mm;
  p.CD = o.k_CD*o.s_barras*mm;
  p.DP = o.k_DP*o.s_barras*mm;
  p.a45 = o.ang_AB*d2r;
  p.delta = o.delta*d2r;
  p.Rw = o.Rw*mm;
  p.theta_min = (360-max(o.th))*d2r;
  p.theta_max = (360-min(o.th))*d2r;

  p.m_AD = o.m_AD*gr;
  p.AG = o.f_AD*p.AD;
  p.IG_AD = o.J_AD;
  p.m_BC = o.m_BC*gr;
  p.BG = o.f_BC*p.BC;
  p.IG_BC = o.J_BC;
  p.m_CDP = o.m_CDP*gr;
  p.dG = o.f_CDP*p.DP;
  p.IG_CDP = o.J_CDP;
  p.epsG = p.delta;
  p.m_P = (o.m_rueda + o.m_motor)*gr;
  p.m_cabina = (o.m_cabina + o.m_tapa + 2*o.m_servo + o.m_bateria + ...
                 o.m_electronica + o.m_tornilleria + o.m_carga)*gr;
  p.n_patas = o.n_servos;
  p.m_total = p.m_cabina + p.n_patas*(p.m_AD + p.m_BC + p.m_CDP + p.m_P);

  p.b = o.b_servo;
  p.tau_max = o.tau_s_max;
  p.w_nl = o.w_nl_servo;
  p.Kp = o.Kp_s;
  p.Kd = o.Kd_s;
  p.tope = struct('habilitado', true, 'k', o.k_tope_servo, 'c', o.c_tope_servo);
  p.g = o.g;
  p.paso_derivada = 1e-6;
end

function quitar_path_si_corresponde(carpeta, estaba)
  if ~estaba && contains([path pathsep], [carpeta pathsep]), rmpath(carpeta); end
end
