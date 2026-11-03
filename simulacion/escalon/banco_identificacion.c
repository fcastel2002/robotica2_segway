// Réplica de la prueba "sesion_placa.py identificar" del 3/11 (FW-017): el robot quieto con las patas
// en una altura, la ref en el equilibrio y después una onda cuadrada de ±amp en la ref. Corre el código
// C del firmware (filtro, odometría, LQR con rechaza banda y zona muerta) contra la planta plana, para
// compararlo con lo medido y ajustar el modelo (modelado/ajuste/).
//
//   banco_identificacion <pata> [nombre=valor ...] [csv=archivo]
//
// Cambios de la planta en tiempo de ejecución (para el ajuste): dp (la pata real = la pedida + dp,
// grados), km (par del motor por este factor), vm (tensión al motor con PWM 1 [V]), zm (zona muerta
// real del motor, fracción de PWM), bm (contraelectromotriz por este factor), ic (inercia del cuerpo
// por este factor). Del firmware: db (zona muerta compensada), notch [Hz], kx kv kphi kw. De la
// prueba: amp [grados], nivel [s], ciclos, ruido (0/1), golpe [grados/s] (patada de cabeceo al empezar).
//
// Compilar desde la raíz (con -DPLANTA_AJUSTADA usa planta_escalon_ajustada.h):
//   gcc -std=c11 -O2 -Isimulacion/escalon -Ifirmware/segway_v01/components/control/include
//       -Ifirmware/segway_v01/main simulacion/escalon/banco_identificacion.c simulacion/escalon/planta_plana.c
//       simulacion/escalon/pata_tabla.c firmware/segway_v01/components/control/*.c -lm -o simulacion/escalon/banco_identificacion

#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "attitude.h"
#include "balance.h"
#include "board_config.h"
#include "odometry.h"
#include "planta_elegida.h"
#include "planta_plana.h"

#define DT_CONTROL      (CONTROL_PERIOD_MS * 1e-3)
#define SUBPASOS        100
#define H               (DT_CONTROL / SUBPASOS)
#define SUBPASO_COMPUTO 20
#define FC_MPU          44.0
#define G               9.81
#define PI              3.141592653589793
#define GRADOS          (180.0 / PI)
#ifdef PE_ZONA_MUERTA                               // la planta ajustada la trae medida
#define ZONA_MUERTA     PE_ZONA_MUERTA
#else
#define ZONA_MUERTA     0.17
#endif

static double param(int argc, char **argv, const char *nombre, double defecto)
{
    size_t n = strlen(nombre);
    for (int i = 2; i < argc; i++) {
        if (strncmp(argv[i], nombre, n) == 0 && argv[i][n] == '=') return atof(argv[i] + n + 1);
    }
    return defecto;
}

static const char *texto(int argc, char **argv, const char *nombre)
{
    size_t n = strlen(nombre);
    for (int i = 2; i < argc; i++) {
        if (strncmp(argv[i], nombre, n) == 0 && argv[i][n] == '=') return argv[i] + n + 1;
    }
    return NULL;
}

// Lo mismo que banco_escalon.c
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
    };
}

static double cabeceo_equilibrio(const planta_t *P, double a)
{
    pata_t p;
    pata_cinematica(a, &p);
    double m = P->m_cuerpo + P->m_rueda + P->m_eslabones;
    double cx = (P->m_rueda * p.px + P->m_eslabones * p.lx) / m - p.px;
    double cz = (P->m_rueda * p.pz + P->m_eslabones * p.lz) / m - p.pz;
    return atan2(-cx, cz);
}

static void estado_apoyado(const planta_t *P, double a, double q[PP_NQ], double dq[PP_NQ])
{
    memset(dq, 0, sizeof(double) * PP_NQ);
    q[PP_TH] = cabeceo_equilibrio(P, a);
    q[PP_A] = a;
    q[PP_F] = 0.0;
    pata_t p;
    pata_cinematica(a, &p);
    double c = cos(q[PP_TH]), s = sin(q[PP_TH]);
    double wx = p.px * c + p.pz * s, wz = -p.px * s + p.pz * c;
    q[PP_X] = -wx;
    q[PP_Z] = P->r_rueda - (P->m_cuerpo + P->m_rueda + P->m_eslabones) * G / P->k_rueda - wz;
}

static double gauss(void)
{
    double u1 = (rand() + 1.0) / (RAND_MAX + 2.0), u2 = (rand() + 1.0) / (RAND_MAX + 2.0);
    return sqrt(-2.0 * log(u1)) * cos(2.0 * PI * u2);
}

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

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "uso: banco_identificacion <pata> [dp= km= vm= zm= bm= ic= db= notch= amp= nivel= ciclos= ruido= csv=]\n");
        return 1;
    }
    const double pata = atof(argv[1]);
    const double dp = param(argc, argv, "dp", 0.0);
    const double amp = param(argc, argv, "amp", 1.5), nivel = param(argc, argv, "nivel", 2.084);
    const int ciclos = (int)param(argc, argv, "ciclos", 5);
    const bool ruido = param(argc, argv, "ruido", 1) != 0;
    const double golpe = param(argc, argv, "golpe", 0.0);    // [grados/s] patada de cabeceo al empezar la onda
    srand((unsigned)param(argc, argv, "semilla", 1));

    planta_t P = planta_base();
    P.beta_v *= param(argc, argv, "km", 1.0);
    P.v_motor = param(argc, argv, "vm", P.v_motor);
    P.b_m *= param(argc, argv, "bm", 1.0);
    P.i_cuerpo *= param(argc, argv, "ic", 1.0);
    P.friccion_seca = P.beta_v * param(argc, argv, "zm", ZONA_MUERTA) * P.v_motor;
    piso_t piso = { 0.0, 1.0, 0 };

    // El firmware como estaba en la prueba del 3/11 (get de las 13:43)
    balance_params_t p = {
        .lqr = { (float)param(argc, argv, "kx", 1.52), (float)param(argc, argv, "kv", 2.73),
                 (float)param(argc, argv, "kphi", 4.14), (float)param(argc, argv, "kw", 0.478) },
        .u_max = 1.0f, .deadband = (float)param(argc, argv, "db", 0.15),
        .notch_hz = (float)param(argc, argv, "notch", 7.0),
    };
    attitude_t att;  attitude_reset(&att);
    odometry_t odo;  odometry_reset(&odo);
    balance_t bal;   balance_reset(&bal);
    const float tau_vel = 1.0f / (6.2831853f * VEL_FILTER_HZ);
    const int cal_n = (int)(GYRO_CAL_TIME_S * 1000 / CONTROL_PERIOD_MS);
    bool calibrado = false, armado = false;
    double rampa = 0, u = 0, u_nuevo = 0, f_fwd = 0, f_up = G, f_gyro = 0;
    double a_mpu = 1.0 - exp(-H * 2 * PI * FC_MPU);
    const double a_planta = (pata + dp) / GRADOS;

    double q[PP_NQ], dq[PP_NQ];
    estado_apoyado(&P, a_planta, q, dq);
    entrada_planta_t ent = { 0.0, a_planta };
    salida_planta_t sal;

    // Como la prueba: 2,5 s en la mano (calibra), arma, 3,5 s quieto, 6 s midiendo el equilibrio
    // (la ref es el promedio), 3 s y la onda cuadrada
    const double T_CAL = 2.5, T_MIDE0 = 6.0, T_MIDE1 = 12.0, T_ONDA = 15.0;
    const double T_FIN = T_ONDA + 2 * ciclos * nivel + 4.0;
    double suma_eq = 0, eq = NAN;
    int n_eq = 0;
    const char *archivo = texto(argc, argv, "csv");
    FILE *csv = archivo ? fopen(archivo, "w") : NULL;
    if (csv) fprintf(csv, "t,th_rel,x_mm,u,v_mms,ref_rel,th_cuerpo_deg\n");
    double x_onda = 0;
    bool cayo = false;
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
        if (fabs(q[PP_TH]) > 1.0) { cayo = true; break; }
        double rn = ruido ? 1.0 : 0.0;
        float acc_fwd = (float)(f_fwd + rn * 0.2 * gauss()), acc_up = (float)(f_up + rn * 0.2 * gauss());
        float gyro = (float)(f_gyro + 0.0087 + rn * 0.0017 * gauss());
        float cuentas = (float)floor(ENC_COUNTS_PER_REV * q[PP_F] / (2 * PI));
        if (!calibrado) calibrado = attitude_calibrate(&att, gyro, cal_n, GYRO_CAL_MAX_RATE);
        else attitude_update(&att, acc_fwd, acc_up, gyro, (float)DT_CONTROL, ATTITUDE_TAU_S);
        if (!armado && !en_la_mano && calibrado) {
            // arma en el equilibrio del modelo (como el equipo, sostenido derecho)
            p.theta_ref = (float)(cabeceo_equilibrio(&P, a_planta) + PE_IMU_DELTA);
            armado = true;  odometry_reset(&odo);  balance_reset(&bal);  rampa = 0;
        }
        odometry_update(&odo, cuentas, att.theta, ENC_COUNTS_PER_REV, WHEEL_RADIUS_M, (float)DT_CONTROL, tau_vel);
        if (t >= T_MIDE0 && t < T_MIDE1) { suma_eq += att.theta; n_eq++; }
        if (t >= T_MIDE1 && isnan(eq)) { eq = suma_eq / n_eq; p.theta_ref = (float)eq; }
        double ref_rel = 0;
        if (t >= T_ONDA) {
            int j = (int)floor((t - T_ONDA) / nivel);
            ref_rel = j < 2 * ciclos ? (j % 2 == 0 ? amp : -amp) : 0.0;
            p.theta_ref = (float)(eq + ref_rel / GRADOS);
            if (x_onda == 0) {
                x_onda = odo.x;
                dq[PP_TH] += golpe / GRADOS;     // como un empujón corto en la cabina
            }
        }
        if (armado) {
            if (fabsf(att.theta - p.theta_ref) > TILT_LIMIT_DEG / GRADOS) { cayo = true; break; }
            rampa = fmin(rampa + DT_CONTROL / ARM_RAMP_S, 1.0);
            u_nuevo = balance_lqr_step(&bal, &p, odo.x, odo.v, att.theta, att.rate, (float)DT_CONTROL,
                                       (float)(rampa * p.u_max));
        }
        if (csv && t >= T_ONDA - 1.0 && k % 4 == 0) {      // cada 20 ms, como la telemetría
            fprintf(csv, "%.3f,%.4f,%.2f,%.4f,%.1f,%.2f,%.4f\n", t - T_ONDA,
                    isnan(eq) ? 0.0 : (att.theta - eq) * GRADOS, (odo.x - x_onda) * 1e3, u_nuevo,
                    odo.v * 1e3, ref_rel, q[PP_TH] * GRADOS);
        }
    }
    if (csv) fclose(csv);
    printf("pata %.1f (planta %.1f): equilibrio IMU %.2f grados (cuerpo %.2f)%s\n", pata, pata + dp,
           eq * GRADOS, cabeceo_equilibrio(&P, a_planta) * GRADOS, cayo ? "  SE CAYO" : "");
    return cayo ? 2 : 0;
}
