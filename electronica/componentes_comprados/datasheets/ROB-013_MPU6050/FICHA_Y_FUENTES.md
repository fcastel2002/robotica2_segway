# ROB-013 — MPU6050

Confirmado por Matías el 15/10/2026. Una unidad registrada para el robot; repuestos adicionales no informados.

**Alcance:** Datasheet original del integrado. La alimentación, regulación y pinout del módulo comprado requieren identificación.

- [Datasheet guardado](MPU6000_MPU6050_InvenSense_datasheet.pdf).
- [Fuente de descarga](https://cdn.sparkfun.com/assets/a/4/6/8/e/MPU_6050.pdf).
- Publicación: InvenSense; copia original alojada por SparkFun. Revisión: PS-MPU-6000A-00, Rev. 3.4, 19/08/2013.

- [Ficha oficial TDK](https://product.tdk.com/en/search/sensor/mortion-inertial/imu/info?part_no=MPU-6050).
- [Enlace histórico oficial del datasheet](https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf).
- El servidor oficial redirige a su búsqueda y la nueva dirección devolvió HTTP 403; se guardó una copia del documento original, sin atribuir el hosting a TDK.

Pendiente: modelo del módulo, regulación y pull-ups de I²C, orientación y montaje. No se supone GY-521.


## Formato del módulo indicado por Matías (17/10/2026)

Matías confirmó que usará el MPU6050 en versión módulo y aportó [esta imagen de referencia](referencia_modulo_matias_2026-10-17.png). Es una foto de catálogo con fondo blanco: identifica el formato, no el ejemplar físico.

Lectura de la imagen [V], a confirmar sobre el ejemplar:

- Serigrafía "ITG/MPU", placa azul con dos agujeros de montaje y dibujo de ejes X e Y. Es el formato comercial conocido como GY-521 [H por apariencia].
- Ocho pines en una hilera, de izquierda a derecha con la serigrafía hacia arriba: INT, AD0, XCL, XDA, SDA, SCL, GND, VCC.
- Regulador de tres o cinco terminales junto a VCC, un LED junto a AD0 y resistencias con marcado que parece "222", posible 2,2 kΩ.

Pendiente de medir en el ejemplar (E-01): paso y orden real de pines, contorno, posición y diámetro de los agujeros, valor y destino de las pull-ups de SDA y SCL, tensión de salida del regulador y rango de VCC admitido, estado de AD0 (dirección 0x68 o 0x69 [D MPU6050 p. 15]) y orientación de los ejes respecto de la serigrafía. El símbolo de KiCad puede crearse con este orden de pines marcado como [V]; la huella espera la medida.
