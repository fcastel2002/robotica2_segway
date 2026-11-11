// Banco de la bajada de un escalón: el código C del firmware (filtro de inclinación,
// odometría, LQR) contra la planta plana con pata de cuatro barras, contacto, vuelo y
// aterrizaje (planta_plana.c). Los parámetros salen de planta_escalon.h, que genera
// exportar_planta_escalon.py desde el modelo.
//
// Primero comprueba la planta (equilibrio estático contra la tabla medida, rueda en vacío
// contra MED-005, equilibrio en piso plano con el LQR del firmware); después corre las
// estrategias de bajada y escribe un CSV por caso en resultados/ para graficar.
//
// Compilar desde la raíz del repo (ver README.md):
//   gcc -std=c11 -O2 -Wall -Wextra -Isimulacion/escalon -Ifirmware/segway_v02/components/control/include
//       -Ifirmware/segway_v02/main simulacion/escalon/*.c firmware/segway_v02/components/control/*.c
//       -lm -o simulacion/escalon/banco_escalon

#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "attitude.h"
#include "balance.h"
#include "board_config.h"
#include "maniobra.h"
#include "movimiento.h"
#include "odometry.h"
#include "planta_elegida.h"
#include "planta_plana.h"
#include "sensor_piso.h"

#define DT_CONTROL      (CONTROL_PERIOD_MS * 1e-3)
#ifndef SUBPASOS                                    // -DSUBPASOS=25: 4 veces más rápido (para buscar)
#define SUBPASOS        100                         // planta cada 0,05 ms
#endif
#define H               (DT_CONTROL / SUBPASOS)
#define SUBPASO_COMPUTO (SUBPASOS / 5)              // el PWM nuevo sale 1 ms después de leer
#define FC_MPU          188.0                       // 11/11: el filtro de la IMU de hoy (dlpf 1, FW-028; antes 44)
#define G               9.81
#define PI              3.141592653589793
#define GRADOS          (180.0 / PI)
#define T_SERVO         0.020                       // el servo ve un pulso nuevo cada 20 ms
#define T_SHARP         0.0165                      // el Sharp renueva su salida cada 16,5 ms
#ifdef PE_ZONA_MUERTA                               // la planta ajustada (3/11) la trae medida
#define ZONA_MUERTA     PE_ZONA_MUERTA
#else
#define ZONA_MUERTA     0.17
#endif
// Lo que la maniobra sabe del robot (IMU y dónde queda el eje según la pata): los de la planta que
// se simula (board_config.h tiene los de la ajustada, que es la que sigue al robot)
#define IMU_DELTA_BANCO (PE_IMU_DELTA * GRADOS)

// Las ganancias del LQR como el firmware: con DEFAULT_LQR_POR_PATA, de LQR_TABLA según la pata
// (3/11, CTL-301); con GANANCIAS=fijas (variable de entorno), las fijas de siempre, como antes del
// 3/11 (así salieron los resultados de las estrategias A-E del modelo original); con GANANCIAS=drv,
// de LQR_TABLA_DRV (la recalculada con el DRV8871, "set lqrpata 2")
static void ganancias_por_pata(float pata, lqr_gains_t *k)
{
    if (!DEFAULT_LQR_POR_PATA || (getenv("GANANCIAS") && strcmp(getenv("GANANCIAS"), "fijas") == 0)) {
        return;
    }
    static const float patas[] = LQR_TABLA_PATAS_DEG;
    static const float tabla[][4] = LQR_TABLA;
    static const float tabla_drv[][4] = LQR_TABLA_DRV;
    // 11/11: como el firmware de hoy: la tabla de DEFAULT_LQR_POR_PATA (2 = la del DRV8871) por los
    // factores de fábrica (set lqrfac, set lqrfacx). GANANCIAS=drv | vieja elige la tabla; LQRFAC=1 y
    // LQRFACX=1, la tabla sin factores (como corría el banco hasta el 11/11)
    bool drv = DEFAULT_LQR_POR_PATA == 2;
    if (getenv("GANANCIAS") && strcmp(getenv("GANANCIAS"), "drv") == 0) drv = true;
    if (getenv("GANANCIAS") && strcmp(getenv("GANANCIAS"), "vieja") == 0) drv = false;
    balance_lqr_tabla(pata, patas, drv ? tabla_drv : tabla, sizeof patas / sizeof patas[0], k);
    float fac = getenv("LQRFAC") ? (float)atof(getenv("LQRFAC")) : DEFAULT_LQR_FACTOR;
    float fac_x = getenv("LQRFACX") ? (float)atof(getenv("LQRFACX")) : DEFAULT_LQR_FACTOR_X;
    k->kx *= fac_x;
    k->kv *= fac_x;
    k->kphi *= fac;
    k->kw *= fac;
}

// ---------------------------------------------------------------- parámetros de la planta
static planta_t planta_base(void)
{
    return (planta_t){
        .m_cuerpo = PE_M_CUERPO, .i_cuerpo = PE_I_CUERPO,
        .m_rueda = PE_M_RUEDA, .m_eslabones = PE_M_ESLABONES, .i_eslabon = PE_I_ESLABON,
        .j_rueda = PE_J_RUEDA, .j_rotor = PE_J_ROTOR, .n_reductor = PE_N_REDUCTOR,
        .j_servo = PE_J_SERVO, .r_rueda = PE_R_RUEDA,
        .beta_v = PE_BETA_V, .b_m = PE_B_M, .b_eje = PE_B_EJE, .friccion_seca = 0.0,
        .v_motor = PE_V_MOTOR,
        .servo_par_max = PE_SERVO_PAR_MAX, .servo_vel_max = PE_SERVO_VEL_MAX,
        .servo_ganancia = PE_SERVO_GANANCIA, .servo_b = PE_SERVO_B,
        .k_rueda = PE_K_RUEDA, .c_rueda = PE_C_RUEDA,
        .k_cuerpo = PE_K_CUERPO, .c_cuerpo = PE_C_CUERPO,
        .mu = PE_MU, .v_resbale = 0.01, .g = G,
#ifdef PE_K_TORSION
        .k_torsion = PE_K_TORSION, .c_torsion = PE_C_TORSION,
#endif
    };
}

// Lo que cede (11/11), para probar sin regenerar la planta: K_TORSION y C_TORSION [N m/rad, N m s/rad]
// (0 = rígido) y C_PATA [N m s/rad]: la pata cede por el plástico, elástico, y no por el servo; su
// amortiguamiento en lugar de la recta par-velocidad del servo
static void planta_del_entorno(planta_t *P)
{
    if (getenv("K_TORSION")) P->k_torsion = atof(getenv("K_TORSION"));
    if (getenv("C_TORSION")) P->c_torsion = atof(getenv("C_TORSION"));
    if (getenv("C_PATA")) { P->servo_vel_max = 1e9; P->servo_b = atof(getenv("C_PATA")); }
    if (getenv("K_PATA")) P->servo_ganancia = atof(getenv("K_PATA")) / P->servo_par_max;
    if (getenv("F_ROTOR")) P->j_rotor *= atof(getenv("F_ROTOR"));
    if (getenv("C_RUEDA")) P->c_rueda = atof(getenv("C_RUEDA"));
}

// A_EXTRA [grados]: la pata de la planta está esto más estirada que lo que pide el firmware (cuánto
// le falta al cuatro barras para su punto muerto en 30 se ajustó con la tabla de equilibrio, ±2 grados)
static double a_extra(void)
{
#ifdef PE_A_EXTRA
    return getenv("A_EXTRA") ? atof(getenv("A_EXTRA")) : PE_A_EXTRA;
#else
    return getenv("A_EXTRA") ? atof(getenv("A_EXTRA")) : 0.0;
#endif
}

// Centro de masa de todo el robot respecto del eje de la rueda, en ejes del cuerpo
static void centro_de_masa(const planta_t *P, double a, double *cx, double *cz)
{
    pata_t p;
    pata_cinematica(a, &p);
    double m = P->m_cuerpo + P->m_rueda + P->m_eslabones;
    // el cuerpo está en (0, 0) del marco; el eje en p y los eslabones en l
    *cx = (P->m_rueda * p.px + P->m_eslabones * p.lx) / m - p.px;
    *cz = (P->m_rueda * p.pz + P->m_eslabones * p.lz) / m - p.pz;
}

// Cabeceo del cuerpo en equilibrio (centro de masa sobre el eje) para la pata a
static double cabeceo_equilibrio(const planta_t *P, double a)
{
    double cx, cz;
    centro_de_masa(P, a, &cx, &cz);
    return atan2(-cx, cz);      // rotado th, el centro de masa queda en X = 0 sobre el eje
}

// Estado inicial: equilibrio estático con la rueda apoyada en el piso de arriba, con el punto
// de contacto en X = x_contacto
static void estado_apoyado(const planta_t *P, double a, double x_contacto, double q[PP_NQ],
                           double dq[PP_NQ])
{
    memset(dq, 0, sizeof(double) * PP_NQ);
    q[PP_TH] = cabeceo_equilibrio(P, a);
    q[PP_A] = a;
    q[PP_F] = 0.0;
    q[PP_S] = 0.0;
    pata_t p;
    pata_cinematica(a, &p);
    double c = cos(q[PP_TH]), s = sin(q[PP_TH]);
    double wx = p.px * c + p.pz * s, wz = -p.px * s + p.pz * c;
    double hundido = (P->m_cuerpo + P->m_rueda + P->m_eslabones) * G / P->k_rueda;
    q[PP_X] = x_contacto - wx;
    q[PP_Z] = P->r_rueda - hundido - wz;
}

// ---------------------------------------------------------------- sensores
static double gauss(void)
{
    double u1 = (rand() + 1.0) / (RAND_MAX + 2.0), u2 = (rand() + 1.0) / (RAND_MAX + 2.0);
    return sqrt(-2.0 * log(u1)) * cos(2.0 * PI * u2);
}

// Fuerza específica en la IMU en sus ejes (adelante, arriba): lo que mide el acelerómetro.
// La IMU está girada PE_IMU_DELTA respecto del cuerpo (hacia adelante).
static void acelerometro(const double q[PP_NQ], const double dq[PP_NQ], const double ddq[PP_NQ],
                         double *fwd, double *up)
{
    double th = q[PP_TH], c = cos(th), s = sin(th);
    double rx = PE_IMU_X * c + PE_IMU_Z * s, rz = -PE_IMU_X * s + PE_IMU_Z * c;
    double w = dq[PP_TH], al = ddq[PP_TH];
    double ax = ddq[PP_X] + al * rz - w * w * rx;
    double az = ddq[PP_Z] - al * rx - w * w * rz + G;
    double ti = th + PE_IMU_DELTA, ci = cos(ti), si = sin(ti);
    *fwd = ax * ci - az * si;
    *up = ax * si + az * ci;
}

// Distancia que mide el Sharp: rayo desde el sensor hasta el piso [m] (NAN fuera de rango)
static double sharp(const piso_t *piso, const double q[PP_NQ])
{
    double sx, sz;
    cuerpo_a_mundo(q, PE_SENSOR_X, PE_SENSOR_Z, &sx, &sz);
    double b = PE_SENSOR_ANG + q[PP_TH];
    double d = piso_rayo(piso, sx, sz, -sin(b), -cos(b), 2.0);
    return (d >= SHARP_D_MIN_M && d <= SHARP_D_MAX_M) ? d : NAN;
}

// ---------------------------------------------------------------- un caso
typedef struct {
    const char *nombre;
    man_params_t man;           // la estrategia
    double alto, pisada;        // escalón [m]
    int    n_escalones;
    double x_contacto0;         // rueda al empezar, respecto del borde [m]
    double factor_servo;        // par de los servos por esto
    double v_motor;             // [V] al motor con PWM 1 si > 0 (si no, el de la planta)
    double zona_muerta;         // fracción de PWM que no mueve la rueda (la real)
    double mu;
    double d_ref;               // [grados] la referencia de equilibrio corrida (la IMU se movió)
    double f_rotor, f_inercia;  // inercia de los rotores y del cuerpo por esto (si > 0)
    int    semilla;             // del ruido de los sensores
    int    repetir;             // escalera frenando en cada escalón: al terminar, otra vez (△)
    double alto_ultimo;         // [m] el último escalón, si es de otra altura (0 = alto)
    double f_masa;              // masa (e inercia) del cuerpo por esto (si > 0)
    double mu_cabina;           // fricción de la cabina contra el escalón (0 = la de la rueda)
    int    apoyo;               // 1: que la cabina toque el escalón no cuenta como choque
    double recorte;             // [m] la cabina recortada adelante
    double k_rueda, c_rueda;    // [N/m], [N s/m] de las dos ruedas contra el piso (0 = los del modelo)
    bool   ruido;
    double ir_x_real;           // [m] dónde miran de verdad los infrarrojos del borde, detrás del apoyo de
                                // la rueda (0 = donde cree la maniobra, man.ir_x). Con alinear=1; el banco
                                // es plano, así que los dos ven el borde a la vez (llega derecho)
} caso_t;

typedef struct {
    bool   cayo, choco, se_paso, aborto, toco;
    const char *motivo;
    double t_toque;             // [s] desde que arrancó la maniobra
    double x_final;             // contacto de la rueda respecto del borde de arriba [m]
    double desvio_max_deg;      // cabeceo respecto del equilibrio, después de tocar
    double par_servo_max;       // [N m] de los dos servos
    double n_rueda_max;         // [N]
    double acc_max_g;           // en la IMU
    double v_toque;             // [m/s] vertical del cuerpo al tocar
    double x_toque, x_min;      // eje al tocar y lo más cerca del borde siguiente [m]
    double v_salida;            // [m/s] del eje al pasar el borde
    double pata_min;            // [grados] lo más que se plegó la pata al tocar
    double borde_error;         // [m] borde estimado menos el real
    int    toques;              // aterrizajes (uno por escalón bajado con la maniobra)
    int    bajados, escalones;  // escalones bajados al final, de cuántos
    double cabina_max, cabina_t;    // [N] golpe más fuerte de la cabina, [s] tiempo apoyada
    double holgura;             // [m] lo más cerca que pasó la cabina de la escalera desde que largó
    double holgura_t, holgura_x;    // [s] cuándo y [m] con el eje dónde
    const char *holgura_en;         // en qué estado de la maniobra
    double x_min_arriba;            // [m] lo más cerca del borde que estuvo la rueda antes de largar
    double d_largada;               // [m] rueda-borde de verdad cuando largó (NAN: no largó)
} resultado_t;

static resultado_t correr(const caso_t *C, FILE *csv)
{
    const double T_CAL = 2.5, T_EQ = 1.5, ESPERA_REPETIR = 1.0;
    const double T_MAX = C->repetir ? 15.0 + 14.0 * C->n_escalones : 30.0;
    srand(1234 + (unsigned)C->semilla);
    planta_t P = planta_base();
    planta_del_entorno(&P);
    P.servo_par_max *= C->factor_servo;
    if (C->f_rotor > 0) P.j_rotor *= C->f_rotor;
    if (C->f_inercia > 0) P.i_cuerpo *= C->f_inercia;
    if (C->f_masa > 0) { P.m_cuerpo *= C->f_masa; P.i_cuerpo *= C->f_masa; }
    P.mu_cuerpo = C->mu_cabina;
    if (C->k_rueda > 0) P.k_rueda = C->k_rueda;
    if (C->c_rueda > 0) P.c_rueda = C->c_rueda;
    P.recorte = C->recorte;
    P.mu = C->mu;
    // El roce seco es del reductor: la zona muerta se midió con la batería de la planta, y con
    // otra batería el roce es el mismo (es otra fracción del PWM)
    P.friccion_seca = P.beta_v * C->zona_muerta * P.v_motor;
    if (C->v_motor > 0) P.v_motor = C->v_motor;
    piso_t piso = { C->alto, C->pisada, C->n_escalones, C->alto_ultimo };

    // Firmware: los mismos parámetros y el mismo orden que control_task.c
    balance_params_t p = {
        .lqr = { DEFAULT_LQR_KX, DEFAULT_LQR_KV, DEFAULT_LQR_KPHI, DEFAULT_LQR_KW },
        .u_max = DEFAULT_U_MAX, .deadband = DEFAULT_DEADBAND, .notch_hz = DEFAULT_NOTCH_HZ,
        .notch2_hz = DEFAULT_NOTCH2_HZ, .lowpass_hz = DEFAULT_LOWPASS_HZ,
    };
    static const float tabla_patas[] = REF_TABLA_PATAS_DEG, tabla_ref[] = REF_TABLA_THETA_DEG;
    const int n_tabla = sizeof tabla_patas / sizeof tabla_patas[0];
    static const float eje_patas[] = PATA_TABLA_DEG;
    float eje_x[] = PATA_EJE_X_M, eje_z[] = PATA_EJE_Z_M;
    const int n_eje = sizeof eje_patas / sizeof eje_patas[0];
    for (int i = 0; i < n_eje; i++) {       // el eje respecto de A, de la cinemática de la planta
        pata_t pe;
        pata_cinematica(eje_patas[i] / GRADOS, &pe);
        eje_x[i] = (float)(pe.px - PE_A_X);
        eje_z[i] = (float)(pe.pz - PE_A_Z);
    }
    float ref_vuelo = 0.0f;         // la referencia al despegar (como el firmware, 4/11)
    attitude_t att;  attitude_reset(&att);
    odometry_t odo;  odometry_reset(&odo);
    balance_t bal;   balance_reset(&bal);
    maniobra_t man = { 0 };
    man_salida_t ms = { 0 };
    const float tau_vel = 1.0f / (6.2831853f * VEL_FILTER_HZ);
    const int cal_n = (int)(GYRO_CAL_TIME_S * 1000 / CONTROL_PERIOD_MS);
    bool calibrado = false, armado = false, lanzada = false;
    double rampa = 0, u = 0, u_nuevo = 0;
    float pata_pos = C->man.pata_busqueda_deg, pata_obj = pata_pos;
    float v_ref = 0, x_ref = 0;

    // Planta: equilibrio con las patas de búsqueda y la rueda a x_contacto0 del borde
    double q[PP_NQ], dq[PP_NQ];
    const double extra = a_extra();
    estado_apoyado(&P, (pata_pos + extra) / GRADOS, C->x_contacto0, q, dq);
    entrada_planta_t ent = { 0.0, (pata_pos + extra) / GRADOS };
    salida_planta_t sal = { 0 };
    double f_fwd = 0, f_up = G, f_gyro = 0, a_mpu = 1.0 - exp(-H * 2 * PI * FC_MPU);
    double t_servo = 0, t_sharp = 0, d_sharp = NAN;

    resultado_t R = { .x_final = NAN, .borde_error = NAN,      // NAN: no vio el borde
                      .escalones = C->n_escalones, .holgura = 1e9, .x_min_arriba = 1e9, .d_largada = NAN };
    bool largo = false;             // ya largó alguna vez (desde ahí cuenta la holgura)
    double caja[4] = { 1e9, -1e9, 1e9, -1e9 };      // la cabina: x0, x1 (el frente, recortado), z0, z1
    for (int i = 0; i < PP_N_PUNTOS; i++) {
        caja[0] = fmin(caja[0], PP_PUNTOS[i][0]);
        caja[1] = fmax(caja[1], PP_PUNTOS[i][0]);
        caja[2] = fmin(caja[2], PP_PUNTOS[i][1]);
        caja[3] = fmax(caja[3], PP_PUNTOS[i][1]);
    }
    caja[1] -= C->recorte;
    double t_man = -1, t_terminada = -1;

    for (int k = 0; k * DT_CONTROL < T_MAX; k++) {
        double t = k * DT_CONTROL;
        bool en_la_mano = t < T_CAL;

        // --- planta durante el período
        for (int i = 0; i < SUBPASOS; i++) {
            if (i == SUBPASO_COMPUTO) u = u_nuevo;
            double ts = t + i * H;
            ent.tension = u * P.v_motor;
            if (ts >= t_servo) {                    // el servo toma el pulso nuevo cada 20 ms
                ent.a_pedido = (pata_pos + extra) / GRADOS;
                t_servo += T_SERVO;
            }
            if (ts >= t_sharp) {                    // el Sharp renueva su salida cada 16,5 ms
                d_sharp = sharp(&piso, q);
                t_sharp += T_SHARP;
            }
            if (en_la_mano) {
                planta_derivada(&P, &piso, q, dq, &ent, &sal);
                memset(sal.ddq, 0, sizeof sal.ddq);
            } else {
                planta_rk4(&P, &piso, q, dq, &ent, H, &sal);
            }
            double fa, ua;
            acelerometro(q, dq, sal.ddq, &fa, &ua);
            f_fwd += a_mpu * (fa - f_fwd);
            f_up += a_mpu * (ua - f_up);
            f_gyro += a_mpu * (dq[PP_TH] - f_gyro);
            if (!en_la_mano && t_man >= 0) {
                R.par_servo_max = fmax(R.par_servo_max, fabs(sal.par_servo));
                R.n_rueda_max = fmax(R.n_rueda_max, sal.n_rueda);
                R.acc_max_g = fmax(R.acc_max_g, hypot(fa, ua) / G);
                if (sal.cuerpo_toca && !C->apoyo) R.choco = true;
                R.cabina_max = fmax(R.cabina_max, sal.n_cuerpo);
                if (sal.cuerpo_toca) R.cabina_t += H;
            }
        }
        if (fabs(q[PP_TH]) > 1.3) { R.cayo = true; R.motivo = "volco"; break; }

        // --- lo que lee el firmware (con la saturación de la MPU: 16 g y 2000 grados/s desde el 7/11)
        double ruido = C->ruido ? 1.0 : 0.0, lim_a = 16 * G, lim_w = 2000 / GRADOS;
        float acc_fwd = (float)fmin(fmax(f_fwd + ruido * 0.2 * gauss(), -lim_a), lim_a);
        float acc_up = (float)fmin(fmax(f_up + ruido * 0.2 * gauss(), -lim_a), lim_a);
        float gyro = (float)fmin(fmax(f_gyro + 0.0087 + ruido * 0.0017 * gauss(), -lim_w), lim_w);
        float cuentas = (float)floor(ENC_COUNTS_PER_REV * q[PP_F] / (2 * PI));
        float d_medida = (float)(d_sharp * (1.0 + ruido * 0.01 * gauss()));

        // --- el firmware
        if (!calibrado) {
            calibrado = attitude_calibrate(&att, gyro, cal_n, GYRO_CAL_MAX_RATE);
        } else if (ms.activa && ms.solo_giroscopo) {
            attitude_update_gyro(&att, gyro, (float)DT_CONTROL);
        } else {
            attitude_update(&att, acc_fwd, acc_up, gyro, (float)DT_CONTROL, ATTITUDE_TAU_S);
        }
        p.theta_ref = (balance_ref_tabla(pata_pos, tabla_patas, tabla_ref, n_tabla) + (float)C->d_ref)
                      / (float)GRADOS;
        if (man.estado == MAN_VUELO) p.theta_ref = ref_vuelo;
        else ref_vuelo = p.theta_ref;
        if (!armado && !en_la_mano && calibrado
            && fabsf(att.theta - p.theta_ref) < ARM_WINDOW_DEG / GRADOS) {
            armado = true;  odometry_reset(&odo);  balance_reset(&bal);  rampa = 0;
            v_ref = x_ref = 0;
        }
        odometry_update(&odo, cuentas, att.theta, ENC_COUNTS_PER_REV, WHEEL_RADIUS_M,
                        (float)DT_CONTROL, tau_vel);

        if (armado && !lanzada && t > T_CAL + T_EQ) {
            maniobra_iniciar(&man, odo.x);
            lanzada = true;
            t_man = 0;
        }
        if (t_man >= 0) t_man += DT_CONTROL;

        // Dónde pega el haz del sensor de distancia
        haz_t haz = haz_para_pata(pata_pos, eje_patas, eje_x, eje_z, n_eje, SENSOR_PISO_X_M,
                                  SENSOR_PISO_Z_M, SENSOR_PISO_ANG_DEG / (float)GRADOS);
        float th_cuerpo = att.theta - (float)(IMU_DELTA_BANCO / GRADOS);
        man_entrada_t me = {
            .dt = (float)DT_CONTROL, .x = odo.x, .v = odo.v, .rate = att.rate,
            .acc = sqrtf(acc_fwd * acc_fwd + acc_up * acc_up), .pata_deg = pata_pos,
            .haz_valido = !isnan(d_medida),
        };
        {
            // Infrarrojos del borde: miran el piso ir_x detrás del apoyo de la rueda (el borde está en X = 0)
            double exi, ezi;
            eje_rueda(q, &exi, &ezi);
            double ir = C->ir_x_real > 0.0 ? C->ir_x_real : C->man.ir_x;
            me.ir_valido = true;
            me.ir_izq = me.ir_der = exi - ir < 0.0;
            if (lanzada && !largo) R.x_min_arriba = fmin(R.x_min_arriba, exi);
            if (man.estado == MAN_LARGAR && isnan(R.d_largada)) R.d_largada = exi;
        }
        if (me.haz_valido) {
            float x_atras, z0;
            haz_punto(&haz, th_cuerpo, WHEEL_RADIUS_M, d_medida, &x_atras, &me.haz_z);
            float d_plano = haz_distancia_plano(&haz, th_cuerpo, WHEEL_RADIUS_M);
            haz_punto(&haz, th_cuerpo, WHEEL_RADIUS_M, d_plano, &me.haz_x_piso, &z0);
        }
        man_estado_t antes = man.estado;
        if (lanzada) maniobra_paso(&man, &C->man, &me, &ms);
        if (getenv("DEPURAR") && lanzada && k % 10 == 0) {
            printf("  t %6.2f %-9s x %7.3f xref %7.3f v %6.3f vref %6.3f borde %7.3f a %5.2f haz_z %6.3f x_piso %6.3f acc %5.1f\n",
                   t - T_CAL, maniobra_nombre(man.estado), odo.x, ms.x_ref, odo.v, ms.v_ref, man.borde_x,
                   man.a_salida, me.haz_z, me.haz_x_piso, me.acc);
        }
        if (antes == MAN_BUSCAR && man.estado == MAN_PREPARAR && isnan(R.borde_error)) {
            // borde real en coordenadas de la odometría: la rueda apoya en X = ex del mundo
            double ex, ez;
            eje_rueda(q, &ex, &ez);
            R.borde_error = man.borde_x - (odo.x - ex);
        }
        if (antes == MAN_VUELO && man.estado == MAN_ATERRIZAR) R.toques++;
        if (antes == MAN_VUELO && man.estado == MAN_ATERRIZAR && !R.toco) {
            R.toco = true;
            R.t_toque = t_man;
            R.v_toque = dq[PP_Z];
            double exx, ezz;  eje_rueda(q, &exx, &ezz);
            R.x_toque = exx;  R.x_min = exx;  R.pata_min = q[PP_A] * GRADOS;
        }
        if (man.estado == MAN_ABORTADA && !R.aborto) { R.aborto = true; R.motivo = man.motivo; }

        if (ms.activa) {
            v_ref = ms.v_ref;
            x_ref = ms.x_ref;
            pata_obj = ms.pata_deg;
        }
        float vel_pata = (ms.activa && ms.vel_pata_dps > 0) ? ms.vel_pata_dps : SERVO_MAX_SPEED_DPS;
        float paso = vel_pata * (float)DT_CONTROL;
        pata_pos += fminf(fmaxf(pata_obj - pata_pos, -paso), paso);

        if (armado) {
            bool en_el_aire = ms.activa && man.estado == MAN_VUELO;
            double lim_tilt = getenv("TILT") ? atof(getenv("TILT")) : TILT_LIMIT_DEG;
            if (fabsf(att.theta - p.theta_ref) > lim_tilt / GRADOS && !en_el_aire) {
                R.cayo = true;  R.motivo = "supervisor: inclinacion";
                break;
            }
            rampa = fmin(rampa + DT_CONTROL / ARM_RAMP_S, 1.0);
            balance_params_t pm = p;
            ganancias_por_pata(pata_pos, &pm.lqr);
            if (ms.activa) { pm.lqr.kx *= ms.kx_factor; pm.u_ff = ms.u_ff; }
            if (ms.activa && man.estado == MAN_ATERRIZAR && getenv("DURO")) {
                // prueba: ganancias del LQR de factor_R 4 (las de antes del 29/10) al aterrizar
                pm.lqr.kv = 5.84f; pm.lqr.kphi = 9.91f; pm.lqr.kw = 1.26f;
            }
            u_nuevo = balance_lqr_step(&bal, &pm, odo.x - x_ref, odo.v - v_ref, att.theta,
                                       att.rate, (float)DT_CONTROL, (float)(rampa * p.u_max));
            if (ms.activa && ms.u_directo_activo) {
                u_nuevo = balance_compensar(&p, ms.u_directo, (float)(rampa * p.u_max));
            }
        }

        // --- medidas
        double ex, ez;
        eje_rueda(q, &ex, &ez);
        if (man.estado == MAN_LARGAR) largo = true;
        if (largo) {
            double d = piso_distancia_caja(&piso, q, caja[0], caja[1], caja[2], caja[3]);
            if (d < R.holgura) {
                R.holgura = d;
                R.holgura_t = t - T_CAL;
                R.holgura_x = ex;
                R.holgura_en = maniobra_nombre(man.estado);
            }
        }
        if (ex < 0.0 && R.v_salida == 0.0 && t_man > 0) R.v_salida = dq[PP_X];
        if (R.toco) {
            double th_eq = cabeceo_equilibrio(&P, q[PP_A]);
            R.desvio_max_deg = fmax(R.desvio_max_deg, fabs(q[PP_TH] - th_eq) * GRADOS);
            // Frenando en cada escalón: después del aterrizaje j, pasar el borde siguiente sin la
            // maniobra (fuera de largar y volar) es pasarse. Con uno solo, abajo hay piso de sobra
            // (un escalón chico, como el último de 3 cm, se puede bajar rodando)
            if (C->n_escalones > 1 && C->man.t_continuo == 0.0f && R.toques < C->n_escalones
                && man.estado != MAN_LARGAR && man.estado != MAN_VUELO
                && ex < -R.toques * C->pisada + 0.005
                && piso_nivel(&piso, R.toques) - piso_nivel(&piso, R.toques + 1) > 0.05) {
                R.se_paso = true;
            }
            R.x_min = fmin(R.x_min, ex);
            R.pata_min = fmin(R.pata_min, q[PP_A] * GRADOS);
        }
        if (csv && !en_la_mano) {
            pata_t pk;
            pata_cinematica(q[PP_A], &pk);
            fprintf(csv, "%.4f,%s,%.5f,%.5f,%.3f,%.3f,%.4f,%.4f,%.3f,%.3f,%.3f,%.3f,%.4f,%.2f,%.3f,%.4f,%.4f,%.5f,%.5f,%.4f,%.4f,%.1f,%.1f,%.2f\n",
                    t - T_CAL, maniobra_nombre(man.estado), ex, ez, q[PP_TH] * GRADOS,
                    q[PP_A] * GRADOS, odo.x, odo.v, att.theta * GRADOS, p.theta_ref * GRADOS,
                    u_nuevo, pata_pos, d_medida, sal.n_rueda, sal.par_servo, dq[PP_X], dq[PP_Z],
                    q[PP_X], q[PP_Z], x_ref, v_ref, (q[PP_TH] + pk.g + q[PP_F] + q[PP_S]) * GRADOS, sal.n_cuerpo,
                    hypot(acc_fwd, acc_up));
        }
        if (man.estado == MAN_INACTIVA && (R.toco || R.aborto)) {
            // Terminó la maniobra. Frenando en cada escalón: quieto un rato y otra vez (△)
            if (!C->repetir || R.aborto || R.se_paso || R.toques >= C->n_escalones) break;
            if (t_terminada < 0) t_terminada = t;
            if (t - t_terminada >= ESPERA_REPETIR) {
                maniobra_iniciar(&man, odo.x);
                t_terminada = -1;
            }
        }
    }
    double ex, ez;
    eje_rueda(q, &ex, &ez);
    R.x_final = ex;
    // Escalones bajados: el nivel de piso más cerca de donde quedó la rueda
    for (int k = 1; k <= C->n_escalones; k++) {
        if (fabs(ez - PE_R_RUEDA - piso_nivel(&piso, k)) < fabs(ez - PE_R_RUEDA - piso_nivel(&piso, R.bajados))) {
            R.bajados = k;
        }
    }
    return R;
}

// ---------------------------------------------------------------- manejo con el joystick
// Piso plano, patas en 15: quieto 2 s, stick a fondo hacia adelante t_stick segundos y se suelta.
// Mismo código que control_task.c para las consignas (movimiento.c). Devuelve dónde estaba al
// soltar, cuánto siguió, si volvió hacia atrás y cuánto se inclinó.
typedef struct {
    double x_suelta, x_max, x_final, vuelve, t_frena, v_max_real, desvio_max_deg;
    bool cayo;
} manejo_t;

static double g_golpe_ts = -1.0, g_golpe_dps = 0.0;   // patada de cabeceo (prueba de robustez)
static double g_lomo = 0.0;        // [m] escalón hacia ARRIBA en el camino (borde de baldosa, cable)
static double g_v_motor = 0.0;     // [V] si > 0, tensión al motor (batería más baja)
static double g_mu = 0.0;          // si > 0, fricción rueda-piso
static manejo_t correr_manejo(const mov_params_t *mp, double avance, double t_stick, FILE *csv)
{
    const double T_CAL = 2.5, T_QUIETO = 2.0, T_FIN = T_CAL + T_QUIETO + t_stick + 5.0;
    srand(1234);
    planta_t P = planta_base();
    P.friccion_seca = P.beta_v * ZONA_MUERTA * P.v_motor;
    // Con lomo: el robot arranca abajo, 1,2 m antes de un escalón de g_lomo hacia arriba en X = 0
    piso_t piso = { g_lomo, 5.0, g_lomo > 0 ? 1 : 0, 0.0 };
    if (g_v_motor > 0) P.v_motor = g_v_motor;
    if (g_mu > 0) P.mu = g_mu;
    balance_params_t p = {
        .lqr = { DEFAULT_LQR_KX, DEFAULT_LQR_KV, DEFAULT_LQR_KPHI, DEFAULT_LQR_KW },
        .u_max = DEFAULT_U_MAX, .deadband = DEFAULT_DEADBAND, .notch_hz = DEFAULT_NOTCH_HZ,
    };
    static const float tabla_patas[] = REF_TABLA_PATAS_DEG, tabla_ref[] = REF_TABLA_THETA_DEG;
    const int n_tabla = sizeof tabla_patas / sizeof tabla_patas[0];
    attitude_t att;  attitude_reset(&att);
    odometry_t odo;  odometry_reset(&odo);
    balance_t bal;   balance_reset(&bal);
    mov_t mov;       mov_reset(&mov, 0.0f);
    const float tau_vel = 1.0f / (6.2831853f * VEL_FILTER_HZ);
    const int cal_n = (int)(GYRO_CAL_TIME_S * 1000 / CONTROL_PERIOD_MS);
    bool calibrado = false, armado = false;
    double rampa = 0, u = 0, u_nuevo = 0, f_fwd = 0, f_up = G, f_gyro = 0;
    double a_mpu = 1.0 - exp(-H * 2 * PI * FC_MPU);
    const float pata = 15.0f;
    double q[PP_NQ], dq[PP_NQ];
    estado_apoyado(&P, pata / GRADOS, g_lomo > 0 ? -1.2 : 0.0, q, dq);
    q[PP_Z] -= g_lomo;
    entrada_planta_t ent = { 0.0, pata / GRADOS };
    salida_planta_t sal;
    manejo_t M = { .x_max = -1e9 };
    double x0 = 0, ex, ez;
    bool soltado = false;
    for (int k = 0; k * DT_CONTROL < T_FIN; k++) {
        double t = k * DT_CONTROL;
        bool en_la_mano = t < T_CAL;
        for (int i = 0; i < SUBPASOS; i++) {
            if (i == SUBPASO_COMPUTO) u = u_nuevo;
            ent.tension = u * P.v_motor;
            if (en_la_mano) { planta_derivada(&P, &piso, q, dq, &ent, &sal); memset(sal.ddq, 0, sizeof sal.ddq); }
            else planta_rk4(&P, &piso, q, dq, &ent, H, &sal);
            double fa, ua;
            acelerometro(q, dq, sal.ddq, &fa, &ua);
            f_fwd += a_mpu * (fa - f_fwd);  f_up += a_mpu * (ua - f_up);  f_gyro += a_mpu * (dq[PP_TH] - f_gyro);
        }
        if (fabs(q[PP_TH]) > 1.0) { M.cayo = true; break; }
        float acc_fwd = (float)(f_fwd + 0.2 * gauss()), acc_up = (float)(f_up + 0.2 * gauss());
        float gyro = (float)(f_gyro + 0.0087 + 0.0017 * gauss());
        float cuentas = (float)floor(ENC_COUNTS_PER_REV * q[PP_F] / (2 * PI));
        if (!calibrado) calibrado = attitude_calibrate(&att, gyro, cal_n, GYRO_CAL_MAX_RATE);
        else attitude_update(&att, acc_fwd, acc_up, gyro, (float)DT_CONTROL, ATTITUDE_TAU_S);
        p.theta_ref = balance_ref_tabla(pata, tabla_patas, tabla_ref, n_tabla) / (float)GRADOS;
        if (!armado && !en_la_mano && calibrado && fabsf(att.theta - p.theta_ref) < ARM_WINDOW_DEG / GRADOS) {
            armado = true;  odometry_reset(&odo);  balance_reset(&bal);  rampa = 0;
            mov_reset(&mov, 0.0f);
            eje_rueda(q, &x0, &ez);
        }
        odometry_update(&odo, cuentas, att.theta, ENC_COUNTS_PER_REV, WHEEL_RADIUS_M, (float)DT_CONTROL, tau_vel);
        double ts = t - T_CAL - T_QUIETO;           // desde que se mueve el stick
        if (g_golpe_ts >= 0 && ts >= g_golpe_ts && ts - DT_CONTROL < g_golpe_ts) {
            dq[PP_TH] += g_golpe_dps / GRADOS;   // como un empujón corto en la cabina
        }
        float a = (armado && ts >= 0 && ts < t_stick) ? (float)avance : 0.0f;
        eje_rueda(q, &ex, &ez);
        if (armado && ts >= t_stick && !soltado) { soltado = true; M.x_suelta = ex - x0; }
        if (armado) {
            if (fabsf(att.theta - p.theta_ref) > TILT_LIMIT_DEG / GRADOS) { M.cayo = true; break; }
            rampa = fmin(rampa + DT_CONTROL / ARM_RAMP_S, 1.0);
            mov_entrada_t me = { .avance = a, .x = odo.x, .v = odo.v,
                                 .tilt_err = att.theta - p.theta_ref, .rate = att.rate,
                                 .u = (float)u_nuevo };
            p.u_ff = mov_paso(&mov, mp, &me, (float)DT_CONTROL);
            u_nuevo = balance_lqr_step(&bal, &p, odo.x - mov.x_ref, odo.v - mov.v_ref, att.theta,
                                       att.rate, (float)DT_CONTROL, (float)(rampa * p.u_max));
        }
        double xr = ex - x0;
        if (ts > 0) M.v_max_real = fmax(M.v_max_real, dq[PP_X]);
        if (ts > (g_golpe_ts >= 0 ? g_golpe_ts : 0)) {  // con patada, desde la patada
            M.desvio_max_deg = fmax(M.desvio_max_deg, fabs(q[PP_TH] - cabeceo_equilibrio(&P, pata / GRADOS)) * GRADOS);
        }
        if (soltado) {
            M.x_max = fmax(M.x_max, xr);
            if (M.t_frena == 0 && fabs(dq[PP_X]) < 0.02 && xr > M.x_suelta) M.t_frena = ts - t_stick;
        }
        if (csv && ts > -0.5) {
            fprintf(csv, "%.3f,%.4f,%.4f,%.4f,%.4f,%.3f,%.3f\n", ts, xr, dq[PP_X], mov.v_ref,
                    mov.x_ref, (q[PP_TH] - cabeceo_equilibrio(&P, pata / GRADOS)) * GRADOS, u_nuevo);
        }
        M.x_final = xr;
    }
    M.vuelve = M.x_max - M.x_final;
    return M;
}

#define CSV_ENCABEZADO "t_s,estado,eje_x_m,eje_z_m,th_deg,pata_real_deg,odo_x_m,odo_v_ms," \
                       "theta_medido_deg,ref_deg,u,pata_pedida_deg,dist_m,n_rueda_N,par_servo_Nm," \
                       "vx_ms,vz_ms,cm_x_m,cm_z_m,x_ref_m,v_ref_ms,rueda_deg,n_cuerpo_N,acc_ms2\n"

static const char *final_de(const resultado_t *R)
{
    // Abajo de todo y parado: bien, aunque la última maniobra no haya encontrado otro borde
    if (!R->choco && !R->cayo && !R->se_paso && R->escalones > 1 && R->bajados >= R->escalones) return "PARADO";
    return R->choco ? "CHOCA" : R->cayo ? "SE CAE" : R->se_paso ? "SE PASA" : R->aborto ? "ABORTA" :
           !R->toco ? "NO BAJO" : R->escalones > 1 && R->bajados < R->escalones ? "A MEDIAS" : "PARADO";
}

static void imprimir(const caso_t *C, const resultado_t *R)
{
    printf("%-46s %-8s", C->nombre, final_de(R));
    if (R->toco) {
        printf(" sale %4.2f  toca %4.0f  min %4.0f  fin %4.0f mm  desvio %4.1f  pata min %5.1f  servo %4.1f N m  rueda %4.0f N  %4.1f g",
               -R->v_salida, R->x_toque * 1e3, R->x_min * 1e3, R->x_final * 1e3, R->desvio_max_deg,
               R->pata_min, R->par_servo_max, R->n_rueda_max, R->acc_max_g);
    }
    if (R->motivo) printf("  (%s)", R->motivo);
    printf("\n");
}

// Lo mismo en una línea "json {...}", para el visor y un_escalon.py (null si no es un número)
static void json_num(const char *nombre, double v, int decimales)
{
    if (isfinite(v)) printf(", \"%s\": %.*f", nombre, decimales, v);
    else printf(", \"%s\": null", nombre);
}

static void imprimir_json(const resultado_t *R)
{
    printf("json {\"final\": \"%s\", \"motivo\": \"%s\", \"toco\": %s, \"toques\": %d, \"bajados\": %d,"
           " \"escalones\": %d", final_de(R), R->motivo ? R->motivo : "", R->toco ? "true" : "false", R->toques,
           R->bajados, R->escalones);
    if (R->toco) {
        json_num("sale", -R->v_salida, 3);
        json_num("toca", R->x_toque * 1e3, 0);
        json_num("min", R->x_min * 1e3, 0);
        json_num("fin", R->x_final * 1e3, 0);
        json_num("desvio", R->desvio_max_deg, 2);
        json_num("pata_min", R->pata_min, 1);
        json_num("servo", R->par_servo_max, 2);
        json_num("rueda", R->n_rueda_max, 0);
        json_num("golpe", R->acc_max_g, 2);
        json_num("t_toque", R->t_toque, 3);
    }
    json_num("borde_error", R->borde_error * 1e3, 1);
    json_num("rueda_min_arriba", R->x_min_arriba < 1e8 ? R->x_min_arriba * 1e3 : NAN, 1);
    json_num("d_largada", R->d_largada * 1e3, 0);
    json_num("cabina_max", R->cabina_max, 0);
    json_num("cabina_t", R->cabina_t, 3);
    json_num("holgura", R->holgura < 1e8 ? R->holgura * 1e3 : NAN, 1);
    if (R->holgura_en) {
        json_num("holgura_t", R->holgura_t, 3);
        json_num("holgura_x", R->holgura_x * 1e3, 0);
        printf(", \"holgura_en\": \"%s\"", R->holgura_en);
    }
    printf("}\n");
}

static resultado_t correr_y_guardar(const caso_t *C, const char *archivo)
{
    char ruta[256];
    snprintf(ruta, sizeof ruta, "simulacion/escalon/resultados/%s.csv", archivo);
    FILE *csv = fopen(ruta, "w");
    if (csv) fputs(CSV_ENCABEZADO, csv);
    resultado_t R = correr(C, csv);
    if (csv) fclose(csv);
    imprimir(C, &R);
    return R;
}

// Un programa de la maniobra, "evento:valor:objetivo:ritmo/..." (eventos larga, borde, despega,
// toca; ver man_accion_t): cuántas acciones, o -1 si no se entiende
static int leer_acciones(const char *texto, man_accion_t *a)
{
    static const char *eventos[MAN_N_EVENTOS] = { "larga", "borde", "despega", "toca" };
    int n = 0;
    const char *s = texto;
    while (*s) {
        char ev[16];
        float valor, objetivo, ritmo;
        int usados = 0;
        if (n >= MAN_MAX_ACCIONES
            || sscanf(s, "%15[a-z]:%f:%f:%f%n", ev, &valor, &objetivo, &ritmo, &usados) != 4) {
            return -1;
        }
        int k = 0;
        while (k < MAN_N_EVENTOS && strcmp(ev, eventos[k]) != 0) k++;
        if (k == MAN_N_EVENTOS) return -1;
        a[n++] = (man_accion_t){ (man_evento_t)k, valor, objetivo, ritmo };
        s += usados;
        if (*s == '/') s++;
        else if (*s) return -1;
    }
    return n;
}

// Los parámetros que se cambian con "caso nombre=valor" ("parametros" los lista con sus valores
// por defecto). motor_vuelo va aparte (es un enum) y también patas=... y vel=... (programa)
typedef struct { const char *nombre; float *f; double *d; int *i; } campo_t;

static int campos_del_caso(caso_t *c, campo_t *k)
{
    int n = 0;
#define F(nom, x) k[n++] = (campo_t){ nom, &c->x, NULL, NULL }
#define D(nom, x) k[n++] = (campo_t){ nom, NULL, &c->x, NULL }
#define I(nom, x) k[n++] = (campo_t){ nom, NULL, NULL, &c->x }
    F("pata_busqueda", man.pata_busqueda_deg);   F("v_busqueda", man.v_busqueda);
    F("desnivel", man.desnivel);                 F("d_min", man.d_min);
    F("avance", man.avance);
    F("pata_largada", man.pata_largada_deg);     F("v_salida", man.v_salida);
    F("a_salida_max", man.a_salida_max);         F("kx_largada", man.kx_largada);
    F("ff", man.ff);                             F("d_salto", man.d_salto);
    F("pata_vuelo", man.pata_vuelo_deg);         F("vel_pata", man.vel_pata_dps);
    F("pata_final", man.pata_final_deg);         F("vel_pata_final", man.vel_pata_final_dps);
    F("t_mantener", man.t_mantener);             F("t_sin_acel", man.t_sin_acel);
    F("kx_aterrizaje", man.kx_aterrizaje);       F("a_frenado", man.a_frenado);
    F("t_continuo", man.t_continuo);             F("d_borde", man.d_borde);
    F("ir_x", man.ir_x);                         F("d_carrera", man.d_carrera);
    F("v_alejar", man.v_alejar);                 D("ir_x_real", ir_x_real);
    F("v_buscar_ir", man.v_buscar_ir);
    D("alto", alto);                             D("pisada", pisada);
    I("escalones", n_escalones);                 D("x0", x_contacto0);
    D("v_motor", v_motor);                       D("zona_muerta", zona_muerta);
    D("mu", mu);                                 D("servo", factor_servo);
    D("d_ref", d_ref);                           D("f_rotor", f_rotor);
    D("f_inercia", f_inercia);                   I("semilla", semilla);
    I("repetir", repetir);                       D("ultimo", alto_ultimo);
    D("f_masa", f_masa);                         D("mu_cabina", mu_cabina);
    I("apoyo", apoyo);                           D("recorte", recorte);
    D("k_rueda", k_rueda);                       D("c_rueda", c_rueda);
#undef F
#undef D
#undef I
    return n;
}

int main(int argc, char **argv)
{
    (void)argc; (void)argv;
    planta_t P = planta_base();
    printf("Planta: cuerpo %.0f g + eslabones %.0f g + eje %.0f g; IMU %.1f grados de mas\n",
           P.m_cuerpo * 1e3, P.m_eslabones * 1e3, P.m_rueda * 1e3, PE_IMU_DELTA * GRADOS);
    printf("Equilibrio del cuerpo (modelo) / tabla del firmware menos IMU_DELTA [grados]:\n");
    static const float tp[] = REF_TABLA_PATAS_DEG, tr[] = REF_TABLA_THETA_DEG;
    for (int i = 0; i < (int)(sizeof tp / sizeof tp[0]); i++) {
        printf("  pata %4.1f: %5.2f / %5.2f\n", tp[i], cabeceo_equilibrio(&P, tp[i] / GRADOS) * GRADOS,
               tr[i] - IMU_DELTA_BANCO);
    }

    man_params_t base;
    maniobra_params_por_defecto(&base);
    caso_t C0 = {
        .nombre = "", .man = base, .alto = 0.166, .pisada = 0.29, .n_escalones = 7, .alto_ultimo = 0.03,
        .x_contacto0 = 0.45, .factor_servo = 1.0, .v_motor = P.v_motor, .zona_muerta = ZONA_MUERTA,
        .mu = PE_MU, .f_rotor = 1.0, .f_inercia = 1.0, .f_masa = 1.0, .ruido = true,
    };

    if (argc > 1 && strcmp(argv[1], "parametros") == 0) {
        // Los parámetros de "caso" con sus valores por defecto, en una línea "json {...}"
        caso_t c = C0;
        campo_t k[64];
        int n = campos_del_caso(&c, k);
        printf("json {\"motor_vuelo\": %d, \"patas\": \"\", \"vel\": \"\"", (int)c.man.motor_vuelo);
        for (int i = 0; i < n; i++) {
            printf(", \"%s\": %g", k[i].nombre, k[i].f ? (double)*k[i].f : k[i].d ? *k[i].d : (double)*k[i].i);
        }
        printf("}\n");
        return 0;
    }

    if (argc > 1 && strcmp(argv[1], "barrido") == 0) {
        // Patas al largar x velocidad de salida, patas a 30 en el aire y 15 al tocar
        printf("\nBarrido: patas al largar (filas) x velocidad de salida (columnas)\n%8s", "");
        const double vs[] = { 0.3, 0.4, 0.5, 0.6, 0.7 };
        const double patas[] = { 0, 10, 20, 30 };
        for (int j = 0; j < 5; j++) printf("   %4.2f m/s          ", vs[j]);
        printf("\n");
        for (int i = 0; i < 4; i++) {
            printf("pata %2.0f", patas[i]);
            for (int j = 0; j < 5; j++) {
                caso_t c = C0;
                c.man.pata_largada_deg = (float)patas[i];
                c.man.v_salida = (float)vs[j];
                resultado_t R = correr(&c, NULL);
                printf("  %-7s %4.0f/%4.0f", final_de(&R), R.x_toque * 1e3, R.x_min * 1e3);
                fflush(stdout);
            }
            printf("\n");
        }
        printf("(final, eje al tocar / lo más atrás que llegó, en mm desde el borde de arriba; el\n"
               " borde del escalón siguiente está en %.0f mm)\n", -C0.pisada * 1e3);
        return 0;
    }

    if (argc > 1 && strcmp(argv[1], "lomo") == 0) {
        // A fondo contra un escalón chico hacia arriba (borde de baldosa, cable): ¿se cae?
        double vm = argc > 2 ? atof(argv[2]) : 0.0, mu = argc > 3 ? atof(argv[3]) : 0.0;
        g_v_motor = vm;  g_mu = mu;
        struct { const char *nombre; mov_params_t p; } casos[] = {
            { "como hoy (0,4, ff 0,8)",            { 0.40f, 0.5f, 0.5f, 0.8f, true, 0.3f, 20, 0, 0, 0, 0 } },
            { "0,4, ff 1,0",                       { 0.40f, 0.5f, 0.5f, 1.0f, true, 0.3f, 20, 0, 0, 0, 0 } },
            { "0,4, ff 1,2",                       { 0.40f, 0.5f, 0.5f, 1.2f, true, 0.3f, 20, 0, 0, 0, 0 } },
            { "0,4, ff 1,0, margen 0,7",           { 0.40f, 0.5f, 0.5f, 1.0f, true, 0.3f, 20, 0, 0, 0, 0.7f } },
            { "0,35, ff 1,0",                      { 0.35f, 0.5f, 0.5f, 1.0f, true, 0.3f, 20, 0, 0, 0, 0 } },
            { "0,35, ff 1,0, margen 0,7",          { 0.35f, 0.5f, 0.5f, 1.0f, true, 0.3f, 20, 0, 0, 0, 0.7f } },
            { "0,3, ff 0,8",                       { 0.30f, 0.5f, 0.5f, 0.8f, true, 0.3f, 20, 0, 0, 0, 0 } },
            { "0,3, ff 1,0, margen 0,7",           { 0.30f, 0.5f, 0.5f, 1.0f, true, 0.3f, 20, 0, 0, 0, 0.7f } },
        };
        const double lomos[] = { 0.0, 0.003, 0.006, 0.010, 0.015 };
        printf("\nA fondo contra un escalón hacia arriba (mm). Motor %.1f V, mu %.2f. Inclinación máxima o CAE\n%-36s",
               vm > 0 ? vm : PE_V_MOTOR, mu > 0 ? mu : PE_MU, "");
        for (int j = 0; j < 5; j++) printf(" %6.0f", lomos[j] * 1e3);
        printf("\n");
        for (size_t i = 0; i < sizeof casos / sizeof casos[0]; i++) {
            printf("%-36s", casos[i].nombre);
            for (int j = 0; j < 5; j++) {
                g_lomo = lomos[j];
                manejo_t M = correr_manejo(&casos[i].p, 1.0, 6.0, NULL);
                if (M.cayo) printf(" %6s", "CAE"); else printf(" %5.1f°", M.desvio_max_deg);
                fflush(stdout);
            }
            printf("\n");
        }
        g_lomo = 0;  g_v_motor = 0;  g_mu = 0;
        return 0;
    }

    if (argc > 1 && strcmp(argv[1], "golpes") == 0) {
        // Robustez: a fondo (o quieto), a los 2 s una patada de cabeceo de +-N grados/s
        if (argc > 2) g_v_motor = atof(argv[2]);
        if (argc > 3) g_mu = atof(argv[3]);
        struct { const char *nombre; mov_params_t p; double avance; } casos[] = {
            { "quieto (referencia)",               { 0.40f, 0.5f, 0.5f, 0.8f, true, 0.3f, 20, 0, 0, 0, 0 }, 0.0 },
            { "a fondo, como hoy (ff 0,8)",        { 0.40f, 0.5f, 0.5f, 0.8f, true, 0.3f, 20, 0, 0, 0, 0 }, 1.0 },
            { "a fondo, ff 1,2",                   { 0.40f, 0.5f, 0.5f, 1.2f, true, 0.3f, 20, 0, 0, 0, 0 }, 1.0 },
            { "a fondo, ff 1,2, margen 0,85",      { 0.40f, 0.5f, 0.5f, 1.2f, true, 0.3f, 20, 0, 0, 0, 0.85f }, 1.0 },
            { "a fondo, ff 1,2, prioridad 8/70",   { 0.40f, 0.5f, 0.5f, 1.2f, true, 0.3f, 20, 8.0f / 57.3f, 70.0f / 57.3f, 0.3f, 0 }, 1.0 },
        };
        const double golpes[] = { -250, -150, -80, 80, 150, 250 };
        printf("\nPatada de cabeceo a los 2 s (grados/s; + = hacia adelante). Inclinación máxima o SE CAE\n%-40s", "");
        for (int j = 0; j < 6; j++) printf(" %7.0f", golpes[j]);
        printf("\n");
        for (size_t i = 0; i < sizeof casos / sizeof casos[0]; i++) {
            printf("%-40s", casos[i].nombre);
            for (int j = 0; j < 6; j++) {
                g_golpe_ts = 2.0;  g_golpe_dps = golpes[j];
                manejo_t M = correr_manejo(&casos[i].p, casos[i].avance, 4.0, NULL);
                if (M.cayo) printf(" %7s", "CAE"); else printf(" %6.1f°", M.desvio_max_deg);
                fflush(stdout);
            }
            printf("\n");
        }
        g_golpe_ts = -1.0;  g_v_motor = 0;  g_mu = 0;
        return 0;
    }

    if (argc > 1 && strcmp(argv[1], "manejo") == 0) {
        // Stick a fondo 3 s y se suelta: el esquema viejo contra el nuevo (rampas y x libre)
        struct { const char *nombre, *archivo; mov_params_t p; } casos[] = {
            { "viejo: x integral, rampa 0,6/0,6, sin ff", "manejo_viejo",
              { 0.40f, 0.6f, 0.6f, 0.0f, false, 0.30f } },
            { "nuevo: x libre, rampa 0,5/0,4, ff 0,9", "manejo_nuevo",
              { 0.40f, 0.5f, 0.4f, 0.9f, true, 0.30f } },
            { "nuevo sin ff", "manejo_nuevo_sin_ff",
              { 0.40f, 0.5f, 0.4f, 0.0f, true, 0.30f } },
            { "nuevo, frenado 0,25", "manejo_frenado_suave",
              { 0.40f, 0.5f, 0.25f, 0.9f, true, 0.30f } },
            { "nuevo, frenado 0,8", "manejo_frenado_fuerte",
              { 0.40f, 0.5f, 0.8f, 0.9f, true, 0.30f } },
        };
        printf("\n%-42s %8s %8s %8s %8s %8s %8s %7s\n", "stick a fondo 3 s y se suelta", "al soltar",
               "sigue", "vuelve", "final", "frena en", "v max", "incl.");
        printf("%-42s %8s %8s %8s %8s %8s %8s %7s\n", "", "[mm]", "[mm]", "[mm]", "[mm]", "[s]", "[m/s]", "[grad]");
        for (size_t i = 0; i < sizeof casos / sizeof casos[0]; i++) {
            char ruta[256];
            snprintf(ruta, sizeof ruta, "simulacion/escalon/resultados/%s.csv", casos[i].archivo);
            FILE *csv = fopen(ruta, "w");
            if (csv) fputs("t_s,x_m,v_ms,v_ref_ms,x_ref_m,inclinacion_deg,u\n", csv);
            manejo_t M = correr_manejo(&casos[i].p, 1.0, 3.0, csv);
            if (csv) fclose(csv);
            printf("%-42s %8.0f %8.0f %8.0f %8.0f %8.2f %8.2f %7.1f%s\n", casos[i].nombre,
                   M.x_suelta * 1e3, (M.x_max - M.x_suelta) * 1e3, M.vuelve * 1e3, M.x_final * 1e3,
                   M.t_frena, M.v_max_real, M.desvio_max_deg, M.cayo ? "  SE CAE" : "");
        }
        return 0;
    }

    if (argc > 1 && strcmp(argv[1], "rebote") == 0) {
        // rebote [alto=0.03] [pata=15] [k_rueda=] [c_rueda=] [servo=1] [csv=nombre]: el robot
        // desarmado (sin motor) y sostenido derecho, en su equilibrio, con las ruedas a alto [m] del
        // piso, se suelta: cuánto rebota (la goma y las patas). Como lo ve el robot con "grabar": |a|
        // de la IMU cada 5 ms (cada eje recortado a ±tope g, 16 por defecto: 4 para las caídas del 7/11, y
        // con el filtro del MPU6050), y los tramos en el aire (|a| < UMBRAL_AIRE). Para comparar con el
        // robot (rebote.py)
        const double UMBRAL_AIRE = 3.0;
        double TOPE = 16.0 * G;     // [m/s2]
        double alto = 0.03, pata = 15.0, k = 0.0, c = 0.0, f_servo = 1.0, inclinacion = 0.0, c_pata = -1.0;
        const char *archivo = NULL;
        for (int i = 2; i < argc; i++) {
            if (strncmp(argv[i], "alto=", 5) == 0) alto = atof(argv[i] + 5);
            else if (strncmp(argv[i], "pata=", 5) == 0) pata = atof(argv[i] + 5);
            else if (strncmp(argv[i], "k_rueda=", 8) == 0) k = atof(argv[i] + 8);
            else if (strncmp(argv[i], "c_rueda=", 8) == 0) c = atof(argv[i] + 8);
            else if (strncmp(argv[i], "servo=", 6) == 0) f_servo = atof(argv[i] + 6);
            else if (strncmp(argv[i], "tope=", 5) == 0) TOPE = atof(argv[i] + 5) * G;
            // 11/11: soltado inclinado respecto del equilibrio [grados, + adelante], como lo sostienen
            else if (strncmp(argv[i], "inclinacion=", 12) == 0) inclinacion = atof(argv[i] + 12);
            // 11/11: la pata cede por el plástico (elástico), no por el servo: su amortiguamiento [N m s/rad]
            // en lugar de la recta par-velocidad del servo
            else if (strncmp(argv[i], "c_pata=", 7) == 0) c_pata = atof(argv[i] + 7);
            else if (strncmp(argv[i], "csv=", 4) == 0) archivo = argv[i] + 4;
        }
        planta_t Pr = planta_base();
        planta_del_entorno(&Pr);
        Pr.servo_par_max *= f_servo;
        if (c_pata >= 0.0) { Pr.servo_vel_max = 1e9; Pr.servo_b = c_pata; }
        if (k > 0) Pr.k_rueda = k;
        if (c > 0) Pr.c_rueda = c;
        piso_t plano = { 0.18, 0.25, 0, 0.0 };
        double q[PP_NQ], dq[PP_NQ];
        pata += a_extra();
        estado_apoyado(&Pr, pata / GRADOS, 0.0, q, dq);
        if (inclinacion != 0.0) {                       // se gira alrededor del contacto de la rueda
            pata_t pc;
            pata_cinematica(pata / GRADOS, &pc);
            double c0 = cos(q[PP_TH]), s0 = sin(q[PP_TH]);
            double cx = q[PP_X] + pc.px * c0 + pc.pz * s0, cz = q[PP_Z] - pc.px * s0 + pc.pz * c0;
            q[PP_TH] += inclinacion / GRADOS;
            double c1 = cos(q[PP_TH]), s1 = sin(q[PP_TH]);
            q[PP_X] = cx - (pc.px * c1 + pc.pz * s1);
            q[PP_Z] = cz - (-pc.px * s1 + pc.pz * c1);
        }
        q[PP_Z] += alto;
        entrada_planta_t e = { 0.0, pata / GRADOS };    // sin tensión al motor; los servos sostienen
        salida_planta_t sal;
        FILE *csv = NULL;
        if (archivo) {
            char r[256];
            snprintf(r, sizeof r, "simulacion/escalon/resultados/%s.csv", archivo);
            csv = fopen(r, "w");
            if (csv) fprintf(csv, "t_s,eje_z_mm,n_rueda_N,acc_ms2,acc_sin_tope_ms2,en_el_aire,th_deg,pata_deg,"
                              "par_servo_Nm\n");
        }
        double a_mpu = 1.0 - exp(-H * 2 * PI * FC_MPU), f_fwd = 0.0, f_up = G, g_fwd = 0.0, g_up = G;
        double a_max = 0.0, par_max = 0.0, pata_min = pata;
        // tramos en el aire, de verdad (la rueda sin tocar) y como los ve la IMU [s]
        double vuelos[16], vuelos_imu[16], t_desde = 0.0, t_imu = -1.0;
        int nv = 0, nvi = 0;
        bool apoyada = false;
        const int pasos = (int)(1.5 / H);
        for (int i = 0; i < pasos; i++) {
            double t = i * H;
            planta_rk4(&Pr, &plano, q, dq, &e, H, &sal);
            double fa, ua;
            acelerometro(q, dq, sal.ddq, &fa, &ua);
            par_max = fmax(par_max, fabs(sal.par_servo));
            pata_min = fmin(pata_min, q[PP_A] * GRADOS);
            f_fwd += a_mpu * (fmin(fmax(fa, -TOPE), TOPE) - f_fwd);     // lo que da el MPU6050
            f_up += a_mpu * (fmin(fmax(ua, -TOPE), TOPE) - f_up);
            g_fwd += a_mpu * (fa - g_fwd);                              // sin el tope
            g_up += a_mpu * (ua - g_up);
            if (sal.rueda_apoyada != apoyada) {
                if (sal.rueda_apoyada && nv < 16) vuelos[nv++] = t - t_desde;
                else t_desde = t;
                apoyada = sal.rueda_apoyada;
            }
            if (i % SUBPASOS == SUBPASOS - 1) {             // una muestra cada 5 ms, como el registro
                double ts = (i + 1) * H, n = sqrt(f_fwd * f_fwd + f_up * f_up);
                double n_sin = sqrt(g_fwd * g_fwd + g_up * g_up);
                a_max = fmax(a_max, n_sin);
                bool aire = n < UMBRAL_AIRE;
                if (aire && t_imu < 0) t_imu = ts;
                if (!aire && t_imu >= 0) {
                    if (nvi < 16) vuelos_imu[nvi++] = ts - t_imu;
                    t_imu = -1.0;
                }
                if (csv) {
                    pata_t p;
                    pata_cinematica(q[PP_A], &p);
                    double ce = cos(q[PP_TH]), se = sin(q[PP_TH]);
                    double eje_z = q[PP_Z] - p.px * se + p.pz * ce;
                    fprintf(csv, "%.3f,%.2f,%.1f,%.2f,%.2f,%d,%.2f,%.2f,%.2f\n", ts, (eje_z - Pr.r_rueda) * 1e3,
                            sal.n_rueda, n, n_sin, aire, q[PP_TH] * GRADOS, q[PP_A] * GRADOS, sal.par_servo);
                }
            }
        }
        if (csv) fclose(csv);
        printf("rebote: suelto a %.0f mm, patas %.0f, goma %.0f N/m y %.0f N s/m, servos x %.2f\n", alto * 1e3,
               pata, Pr.k_rueda, Pr.c_rueda, f_servo);
        printf("  en el aire (de verdad) [ms]:");
        for (int i = 0; i < nv; i++) printf(" %.0f", vuelos[i] * 1e3);
        printf("\n  en el aire (IMU, |a| < %.0f m/s2) [ms]:", UMBRAL_AIRE);
        for (int i = 0; i < nvi; i++) printf(" %.0f", vuelos_imu[i] * 1e3);
        printf("\n  |a| máxima %.1f g (el MPU6050 está en ±4 g); par de los dos servos hasta %.1f N m; pata"
               " hasta %.1f\n", a_max / G, par_max, pata_min);
        printf("json {\"vuelos_ms\": [");
        for (int i = 0; i < nv; i++) printf("%s%.1f", i ? ", " : "", vuelos[i] * 1e3);
        printf("], \"vuelos_imu_ms\": [");
        for (int i = 0; i < nvi; i++) printf("%s%.0f", i ? ", " : "", vuelos_imu[i] * 1e3);
        printf("], \"a_max_g\": %.2f, \"par_servo_max\": %.2f, \"pata_min\": %.2f}\n", a_max / G, par_max, pata_min);
        return 0;
    }

    if (argc > 1 && strcmp(argv[1], "caida") == 0) {
        // caida <pata> <alto_m> <vx> [pata_al_tocar] [factor_servo]: suelta el robot en el aire
        // sobre piso plano, sin control, para ver el golpe y cuánto lo hace cabecear
        double a = (argc > 2 ? atof(argv[2]) : 30) / GRADOS, alto = argc > 3 ? atof(argv[3]) : 0.18;
        double vx = argc > 4 ? atof(argv[4]) : 0.0, a_toca = argc > 5 ? atof(argv[5]) / GRADOS : a;
        planta_t Pc = planta_base();
        if (argc > 6) Pc.servo_par_max *= atof(argv[6]);
        piso_t plano = { 0.18, 0.25, 0, 0.0 };
        double q[PP_NQ], dq[PP_NQ];
        estado_apoyado(&Pc, a, 0.0, q, dq);
        q[PP_Z] += alto;
        dq[PP_X] = vx;
        dq[PP_F] = vx / Pc.r_rueda;             // la rueda girando a la velocidad del piso
        entrada_planta_t e = { 0.0, a };
        salida_planta_t s;
        double th0 = q[PP_TH], w_min = 0, w_max = 0, t_toque = -1, par_max = 0, a_min = 1e9;
        for (int k = 0; k < 20000; k++) {           // 1 s
            double t = k * 5e-5;
            if (t_toque >= 0 && t > t_toque) e.a_pedido = a_toca;
            // el motor sostiene la velocidad de la rueda (no la frena en el aire)
            e.tension = Pc.b_m * dq[PP_F] / Pc.beta_v;
            planta_rk4(&Pc, &plano, q, dq, &e, 5e-5, &s);
            if (t_toque < 0 && s.rueda_apoyada) t_toque = t;
            if (t_toque >= 0 && t < t_toque + 0.3) {
                w_min = fmin(w_min, dq[PP_TH]);  w_max = fmax(w_max, dq[PP_TH]);
                par_max = fmax(par_max, fabs(s.par_servo));  a_min = fmin(a_min, q[PP_A]);
            }
            if (t_toque >= 0 && fabs(t - (t_toque + 0.1)) < 2.5e-5) {
                printf("a los 0,1 s de tocar: cabeceo %+.1f grados (al soltarlo %+.1f), pata %.1f\n",
                       q[PP_TH] * GRADOS, th0 * GRADOS, q[PP_A] * GRADOS);
            }
        }
        printf("toca a %.3f s; en 0,3 s: velocidad de cabeceo %+.0f..%+.0f grados/s, pata mínima %.1f,"
               " par de servos %.1f N m\n", t_toque, w_min * GRADOS, w_max * GRADOS, a_min * GRADOS, par_max);
        return 0;
    }

    if (argc > 1 && strcmp(argv[1], "caso") == 0) {
        // caso nombre=valor ...: cambia parámetros de la maniobra o del escenario
        caso_t c = C0;
        c.nombre = "caso a mano";
        const char *archivo = "caso";
        for (int i = 2; i < argc; i++) {
            char nombre[64];
            double v;
            if (strncmp(argv[i], "patas=", 6) == 0 || strncmp(argv[i], "vel=", 4) == 0) {
                bool patas = argv[i][0] == 'p';
                int n = leer_acciones(strchr(argv[i], '=') + 1, patas ? c.man.patas : c.man.vel);
                if (n < 0) { fprintf(stderr, "no entiendo %s\n", argv[i]); return 2; }
                if (patas) c.man.n_patas = n; else c.man.n_vel = n;
                continue;
            }
            if (sscanf(argv[i], "%63[^=]=%lf", nombre, &v) != 2) {
                if (strncmp(argv[i], "csv=", 4) == 0) archivo = argv[i] + 4;
                continue;
            }
            campo_t k[64];
            int n = campos_del_caso(&c, k);
            bool ok = false;
            for (int j = 0; j < n; j++) {
                if (strcmp(nombre, k[j].nombre) != 0) continue;
                if (k[j].f) *k[j].f = (float)v;
                if (k[j].d) *k[j].d = v;
                if (k[j].i) *k[j].i = (int)v;
                ok = true;
            }
            if (strcmp(nombre, "motor_vuelo") == 0) { c.man.motor_vuelo = (man_motor_vuelo_t)v; ok = true; }
            if (strcmp(nombre, "alinear") == 0) { c.man.alinear = v != 0.0; ok = true; }
            if (!ok) { fprintf(stderr, "no conozco %s\n", nombre); return 2; }
        }
        resultado_t R = correr_y_guardar(&c, archivo);
        imprimir_json(&R);
        return 0;
    }

    printf("\n%-46s %-8s\n", "caso", "final");
    caso_t c = C0;
    c.nombre = "la de por defecto, un escalon";
    c.n_escalones = 1;
    correr_y_guardar(&c, "por_defecto");
    return 0;
}
