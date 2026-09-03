function pv = empaquetar_v1(P, C)
%EMPAQUETAR_V1  Aplana P (y las ganancias C) en un vector de 124 doubles para los bloques MATLAB Function.
%    1 m_b   2 m_w   3 J_b   4 J_w   5 Rw   6 g   7 l_min   8 l_max
%    9 b_pitch  10 b_pata  11 b_w  12 k_tope  13 c_tope
%   14 R_m  15 L_m  16 Kt  17 Ke  18 N  19 J_r  20 b_m  21 tau_c
%   22 gear_rigido  23 k_g  24 c_g  25 juego  26 mu_defecto  27 v_s  28 c_v
%   29 V_bat  30 R_bat
%   31 tau_s_max  32 w_nl_servo  33 Kp_s  34 Kd_s  35 n_servos  36 th_min  37 th_max
%   38 d_imu_x  39 d_imu_y  40 Ts  41 encoder  42 CPR  43 gyro_bias  44 gyro_sat  45 gyro_rms  46 acc_rms
%   47 k_comp  48 fc_vel  49 eta  50 n_delay
%   51:54 K1  55:58 K2  59 lA  60 lB        K(l) = K1 + K2*l  (ceros si no hay C)
%   61 n_tab  62:82 l_tab  83:103 th_tab  104:124 dthdl_tab
  if nargin < 2, C = []; end
  pv = zeros(124,1);
  pv(1)=P.din.m_b; pv(2)=P.din.m_w; pv(3)=P.din.J_b; pv(4)=P.din.J_w; pv(5)=P.Rw; pv(6)=P.g;
  pv(7)=P.din.l_min; pv(8)=P.din.l_max;
  pv(9)=P.cuerpo.b_pitch; pv(10)=P.cuerpo.b_pata; pv(11)=P.rueda.b_w; pv(12)=P.cuerpo.k_tope; pv(13)=P.cuerpo.c_tope;
  pv(14)=P.motor.R; pv(15)=P.motor.L; pv(16)=P.motor.Kt; pv(17)=P.motor.Ke; pv(18)=P.motor.N;
  pv(19)=P.motor.J_r; pv(20)=P.motor.b_m; pv(21)=P.motor.tau_c;
  pv(22)=double(P.motor.gear_rigido); pv(23)=P.motor.k_g; pv(24)=P.motor.c_g; pv(25)=P.motor.juego;
  pv(26)=P.rueda.mu; pv(27)=P.rueda.v_s; pv(28)=P.rueda.c_v;
  pv(29)=P.bat.V; pv(30)=P.bat.R;
  pv(31)=P.servo.tau_max; pv(32)=P.servo.w_nl; pv(33)=P.servo.Kp; pv(34)=P.servo.Kd; pv(35)=P.servo.n;
  pv(36)=P.servo.th_min; pv(37)=P.servo.th_max;
  pv(38)=P.sens.d_imu(1); pv(39)=P.sens.d_imu(2); pv(40)=P.sens.Ts; pv(41)=double(P.sens.encoder); pv(42)=P.sens.CPR;
  pv(43)=P.sens.gyro_bias; pv(44)=P.sens.gyro_sat; pv(45)=P.sens.gyro_rms; pv(46)=P.sens.acc_rms;
  pv(47)=P.ctrl.k_comp; pv(48)=P.ctrl.fc_vel; pv(49)=P.motor.eta; pv(50)=P.sens.n_delay;
  if ~isempty(C)
    pv(51:54)=C.Kfit(1,:).'; pv(55:58)=C.Kfit(2,:).'; pv(59)=C.l_lim(1); pv(60)=C.l_lim(2);
  end
  n = numel(P.tab.l); pv(61)=n;
  pv(62:62+n-1)=P.tab.l; pv(83:83+n-1)=P.tab.th; pv(104:104+n-1)=P.tab.dthdl;
end
