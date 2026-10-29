// Asignación de pines del prototipo v0.1 (ESP32-S3 N16R8, clon DevKitC-1).
// Valores por defecto: cambiarlos acá cuando se defina el cableado real.
//
// No usar:
//   19, 20     USB nativo (sin uso: consola y flasheo van por UART0)
//   26-37      flash y PSRAM octal del módulo N16R8
//   3, 45, 46  pines de arranque (el 0 solo como entrada de botón)
//   43, 44     UART0: consola y comandos (conector UART de la placa)
#pragma once

// Bus I2C compartido: MPU-6050 ahora, INA226 más adelante
#define PIN_I2C_SDA         8
#define PIN_I2C_SCL         9
#define PIN_IMU_INT         10      // reservado: temporizar el lazo con la IMU

// L298N: PWM en IN1/IN2 (IN3/IN4 para el derecho) y habilitación en ENA/ENB.
// Quitar los puentes ENA/ENB del módulo para conectarlos al ESP32. Si se dejan puestos,
// poner el EN en -1: funciona igual, pero al desarmar las ruedas quedan frenadas, no libres.
// Para el DRV8871 (sin EN) también va -1.
#define PIN_MOTOR_L_IN1     4
#define PIN_MOTOR_L_IN2     5
#define PIN_MOTOR_L_EN      6
#define PIN_MOTOR_R_IN1     7
#define PIN_MOTOR_R_IN2     17
#define PIN_MOTOR_R_EN      18
// Reservado: entrada de falla del MCPWM (parada de emergencia o comparador de sobrecorriente).
// Cortaría los dos motores por hardware, sin pasar por la CPU. Aún no se configura.
#define PIN_MOTOR_FAULT     21

// Servos de las patas (señal; la alimentación va por el UBEC, con GND común)
#define PIN_SERVO_L         15
#define PIN_SERVO_R         16

// Encoders de cuadratura de las ruedas (hall del motor, alimentados a 3,3 V: las salidas
// no pueden subir a 5 V, los GPIO del ESP32 no lo toleran)
#define PIN_ENC_L_A         11
#define PIN_ENC_L_B         12
#define PIN_ENC_R_A         13
#define PIN_ENC_R_B         14

// Reservados para versiones posteriores (no se configuran en la v0.1)
#define PIN_BATT_ADC        1       // debe ser ADC1 (GPIO1-10) para convivir con WiFi
#define PIN_ARM_BUTTON      0       // botón BOOT de la placa
#define PIN_LED_RGB         48      // 38 en la versión 1.1 de la DevKitC
