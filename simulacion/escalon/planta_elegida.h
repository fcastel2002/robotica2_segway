// La planta que usan los bancos: la del modelo original (planta_escalon.h, de
// exportar_planta_escalon.m) o, compilando con -DPLANTA_AJUSTADA, la ajustada con lo medido el 3/11
// (planta_escalon_ajustada.h, de exportar_planta_ajustada.m; ver modelado/ajuste/).
#pragma once

#ifdef PLANTA_AJUSTADA
#include "planta_escalon_ajustada.h"
#else
#include "planta_escalon.h"
#endif
