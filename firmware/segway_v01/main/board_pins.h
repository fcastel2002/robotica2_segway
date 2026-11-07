// Asignación de pines del prototipo v0.1 (ESP32-S3 N16R8, clon DevKitC-1).
// Valores por defecto: cambiarlos acá cuando se defina el cableado real.
//
// No usar:
//   19, 20     USB nativo (sin uso: consola y flasheo van por UART0)
//   26-37      flash y PSRAM octal del módulo N16R8
//   45, 46     pines de arranque (el 0 solo como entrada de botón; el 3 también es de arranque,
//              pero solo para JTAG si se graba el eFuse STRAP_JTAG_SEL: no grabarlo)
//   43, 44     UART0: consola y comandos (conector UART de la placa)
#pragma once

// Bus I2C compartido: MPU-6050 ahora, INA226 más adelante
#define PIN_I2C_SDA         17
#define PIN_I2C_SCL         16
#define PIN_IMU_INT         18      // reservado: temporizar el lazo con la IMU
#define PIN_INA_ALERT       8       // INA226


// L298N: PWM en IN1/IN2 (IN3/IN4 para el derecho) y habilitación en ENA/ENB.
// Quitar los puentes ENA/ENB del módulo para conectarlos al ESP32. Si se dejan puestos,
// poner el EN en -1: funciona igual, pero al desarmar las ruedas quedan frenadas, no libres.
// Para el DRV8871 (sin EN) también va -1.
#define PIN_MOTOR_L_IN1     14
#define PIN_MOTOR_L_IN2     13
#define PIN_MOTOR_L_EN      1
#define PIN_MOTOR_R_IN1     12
#define PIN_MOTOR_R_IN2     11
#define PIN_MOTOR_R_EN      -1
// Reservado: entrada de falla del MCPWM (parada de emergencia o comparador de sobrecorriente).
// Cortaría los dos motores por hardware, sin pasar por la CPU. Aún no se configura.
#define PIN_MOTOR_FAULT     21

// Servos de las patas (señal; la alimentación va por el UBEC, con GND común)
#define PIN_SERVO_L         9       // sobre el motor izquierdo (J13 de la PCB)
#define PIN_SERVO_R         10      // sobre el motor derecho (J14 de la PCB)

// Encoders de cuadratura de las ruedas (hall del motor, alimentados a 3,3 V: las salidas
// no pueden subir a 5 V, los GPIO del ESP32 no lo toleran)
// 29/10: medido con los motores (el motor izquierdo movía las cuentas de 13/14 y el derecho las
// de 11/12): el encoder izquierdo está cableado en 13/14 y el derecho en 11/12
#define PIN_ENC_L_A         4
#define PIN_ENC_L_B         5
#define PIN_ENC_R_A         7
#define PIN_ENC_R_B         15

// Sensor de distancia al piso para el escalón (Sharp GP2Y0A60SZLF en J27, SUP-82): su salida
// entra por un divisor 10k/15k (x 0,6). ADC1_CH2, convive con el WiFi.
#define PIN_DIST_SUELO      3

// LED RGB integrado (WS2812), indica el estado del robot
#define PIN_LED_RGB         48      // 38 en la versión 1.1 de la DevKitC

// Reservados para versiones posteriores (no se configuran en la v0.1)
#define PIN_BATT_ADC        1       // debe ser ADC1 (GPIO1-10) para convivir con WiFi
#define PIN_ARM_BUTTON      0       // botón BOOT de la placa
