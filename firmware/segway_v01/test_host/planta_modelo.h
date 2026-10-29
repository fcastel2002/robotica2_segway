// GENERADO por simulacion/pendulo_invertido/exportar_planta_al_banco.m el 2026-10-29 11:02.
// No editar a mano: cambiar modelado/parametros/parametros_fisicos.m y volver a correrlo.
// Planta de planta_con_motor.m en la postura de 25 grados, robot de 961.9 g.
#pragma once

#define PLANTA_A             1.3119    // masa efectiva de avance [kg]
#define PLANTA_H             0.0702424653    // masa por brazo [kg m]
#define PLANTA_J             0.0100179494    // inercia de cabeceo [kg m2]
#define PLANTA_K             0.689078585    // par de gravedad [N m/rad]
#define PLANTA_E_ACOPLE      -0.0114    // acople del rotor [kg m]
#define PLANTA_R             0.04    // radio de rueda [m]
#define PLANTA_B_EJE         0.0002    // friccion del eje, sin el motor [N m s/rad]
#define PLANTA_B_X           0    // arrastre de avance [N s/m]
#define PLANTA_B_PHI         0.001    // amortiguamiento de cabeceo [N m s/rad]
#define PLANTA_BETA_V        0.0528704051    // par de los dos motores por voltio [N m/V]
#define PLANTA_B_M           0.0191569838    // contraelectromotriz de los dos motores [N m s/rad]
#define PLANTA_V_BAT         11.1    // tension de la bateria en el modelo [V]
#define PLANTA_TAU_TRACCION  0.564043702    // par maximo antes de patinar [N m]
#define PLANTA_DELTA_G       -0.0624922583    // phi = inclinacion del cuerpo + DELTA_G [rad]
#define PLANTA_IMU_ADELANTE  0.018612085    // IMU respecto del eje, hacia adelante [m]
#define PLANTA_IMU_ARRIBA    0.115906118    // IMU respecto del eje, hacia arriba [m]
#define PLANTA_G             9.81    // gravedad [m/s2]
#define PLANTA_GYRO_BIAS     0.00872664626    // sesgo del giroscopo [rad/s]
#define PLANTA_GYRO_RMS      0.00174532925    // ruido del giroscopo [rad/s rms]
#define PLANTA_ACC_RMS       0.1962    // ruido del acelerometro [m/s2 rms]

// LQR del modelo en voltios, V = -K z con z = [x v phi omega] (solo para la referencia)
#define PLANTA_K_LQR { -55.5, -53.1163005, -90.1706408, -11.4361376 }
