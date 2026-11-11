# La biblioteca SharpDistSensor de Arduino sin modificar (SharpDistSensor/), con lo mínimo de Arduino que
# necesita (arduino/Arduino.h) y la entrada desde C (sharp_lib.cpp). Sin dependencias de ESP-IDF.
idf_component_register(SRCS "sharp_lib.cpp" "SharpDistSensor/SharpDistSensor.cpp" "SharpDistSensor/MedianFilter.cpp"
                       INCLUDE_DIRS "include"
                       PRIV_INCLUDE_DIRS "SharpDistSensor" "arduino")
