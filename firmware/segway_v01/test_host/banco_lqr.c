// Banco del control en la PC: el código C del firmware contra la planta del modelo.
//
// Corre attitude.c, odometry.c y balance.c (los mismos archivos que van a la placa) cada
// 5 ms contra una copia en C de planta_con_motor.m, con sensores simulados:
//   IMU       acelerómetro en su posición real (ve las aceleraciones del robot, no solo la
//             gravedad), giróscopo con sesgo, ruido de los dos y el filtro de 44 Hz del MPU
//   encoders  cuentas enteras del giro de la rueda RESPECTO DEL CUERPO, 880 por vuelta
//   motor     PWM por la tensión que deja el L298N, aplicado 1 ms después de leer (cómputo),
//             y opcionalmente una fricción seca que hace la zona muerta
// Los valores de la planta salen de planta_modelo.h, que genera
// simulacion/pendulo_invertido/exportar_planta_al_banco.m: una sola fuente, parametros_fisicos.m.
//
// Primero comprueba la copia de la planta contra MATLAB (referencia_planta.csv); después
// corre los escenarios y escribe banco_lqr.csv para graficar. Desde firmware/segway_v01/:
//   gcc -std=c11 -O2 -Wall -Wextra -Icomponents/control/include -Imain test_host/banco_lqr.c
//       components/control/*.c -lm -o test_host/banco_lqr && test_host/banco_lqr

#include <math.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "attitude.h"
#include "balance.h"
#include "board_config.h"
#include "odometry.h"
#include "planta_modelo.h"

#define DT_CONTROL      (CONTROL_PERIOD_MS * 1e-3)
#define SUBPASOS        20                          // integración cada 0,25 ms
#define H               (DT_CONTROL / SUBPASOS)
#define SUBPASO_COMPUTO 4                           // el PWM nuevo sale 1 ms después de leer
#define FC_MPU          44.0                        // filtro interno del MPU-6050 [Hz]
#define DOS_PI          6.283185307179586
#define GRADOS          (180.0 / 3.141592653589793)

typedef struct { double x, v, phi, w; } estado_t;

typedef struct {
    double tension;         // [V] aplicada a los dos motores
    double friccion_seca;   // [N m] de los dos motores juntos: hace la zona muerta
    double fuerza_extra;    // [N] empujón horizontal en el eje
    double v_max;           // [V] lo máximo que puede llegar al motor
} entrada_t;

// ---------------------------------------------------------------- planta (planta_con_motor.m)
static estado_t derivada(const estado_t *z, const entrada_t *e)
{
    double w_rel = z->v / PLANTA_R - z->w;                  // rueda vista desde el cuerpo
    double V = fmin(fmax(e->tension, -e->v_max), e->v_max);
    double par = PLANTA_BETA_V * V - PLANTA_B_M * w_rel - e->friccion_seca * tanh(w_rel / 0.3);
    par = fmin(fmax(par, -PLANTA_TAU_TRACCION), PLANTA_TAU_TRACCION);

    double acople = PLANTA_H * cos(z->phi) + PLANTA_E_ACOPLE;
    double par_ef = par - PLANTA_B_EJE * w_rel;
    double qx = par_ef / PLANTA_R - PLANTA_B_X * z->v + e->fuerza_extra
              + PLANTA_H * sin(z->phi) * z->w * z->w;
    double qphi = -par_ef - PLANTA_B_PHI * z->w + PLANTA_K * sin(z->phi);
    double det = PLANTA_A * PLANTA_J - acople * acople;
    return (estado_t){ z->v, (PLANTA_J * qx - acople * qphi) / det,
                       z->w, (PLANTA_A * qphi - acople * qx) / det };
}

static void rk4(estado_t *z, const entrada_t *e, double h)
{
    estado_t k1 = derivada(z, e);
    estado_t a = { z->x + 0.5*h*k1.x, z->v + 0.5*h*k1.v, z->phi + 0.5*h*k1.phi, z->w + 0.5*h*k1.w };
    estado_t k2 = derivada(&a, e);
    estado_t b = { z->x + 0.5*h*k2.x, z->v + 0.5*h*k2.v, z->phi + 0.5*h*k2.phi, z->w + 0.5*h*k2.w };
    estado_t k3 = derivada(&b, e);
    estado_t c = { z->x + h*k3.x, z->v + h*k3.v, z->phi + h*k3.phi, z->w + h*k3.w };
    estado_t k4 = derivada(&c, e);
    z->x   += h/6 * (k1.x   + 2*k2.x   + 2*k3.x   + k4.x);
    z->v   += h/6 * (k1.v   + 2*k2.v   + 2*k3.v   + k4.v);
    z->phi += h/6 * (k1.phi + 2*k2.phi + 2*k3.phi + k4.phi);
    z->w   += h/6 * (k1.w   + 2*k2.w   + 2*k3.w   + k4.w);
}

// ---------------------------------------------------------------- sensores
static double gauss(void)
{
    double u1 = (rand() + 1.0) / (RAND_MAX + 2.0), u2 = (rand() + 1.0) / (RAND_MAX + 2.0);
    return sqrt(-2.0 * log(u1)) * cos(DOS_PI * u2);
}

// Fuerza específica en la IMU, en los ejes del cuerpo (adelante, arriba): lo que mide el
// acelerómetro. Incluye la aceleración del eje y la del cabeceo en ese punto.
static void acelerometro(const estado_t *z, const estado_t *dz, double *fwd, double *up)
{
    double th = z->phi - PLANTA_DELTA_G;                    // inclinación del cuerpo
    double s = sin(th), c = cos(th), sf = PLANTA_IMU_ADELANTE, su = PLANTA_IMU_ARRIBA;
    double w2 = z->w * z->w, al = dz->w;
    double ax = dz->v + sf * (-s*al - c*w2) + su * (c*al - s*w2);
    double ay =         sf * (-c*al + s*w2) + su * (-s*al - c*w2) + PLANTA_G;
    *fwd = ax * c - ay * s;
    *up  = ax * s + ay * c;
}

// ---------------------------------------------------------------- escenarios
typedef struct {
    const char *nombre;
    double phi0_deg;            // inclinación al soltarlo (sobre el equilibrio)
    double v_motor;             // [V] tensión real a fondo
    double zona_muerta_real;    // fracción de PWM que no mueve la rueda
    double deadband_firmware;   // lo que se carga con "set deadband"
    double error_ref_deg;       // ref cargada menos la verdadera
    double empujon_N;           // a los 5 s de soltarlo, durante 0,1 s
    bool   ruido;
    double notch_hz;            // rechaza banda del firmware (0 = sin filtro)
} escenario_t;

typedef struct {
    bool cayo;
    double t_caida, phi_max_deg, x_max_mm, x_final_mm, phi_rms_deg, x_pp_mm, satura_pct;
} resultado_t;

static resultado_t correr(const escenario_t *E, FILE *csv, int id)
{
    const double T_CAL = 2.5, T_FIN = 20.0;     // en la mano hasta T_CAL, después suelto
    srand(1234);
    estado_t z = { 0, 0, E->phi0_deg / GRADOS, 0 };
    entrada_t ent = { 0 };
    ent.friccion_seca = PLANTA_BETA_V * E->zona_muerta_real * E->v_motor;
    ent.v_max = E->v_motor;

    balance_params_t p = {
        .lqr = { DEFAULT_LQR_KX, DEFAULT_LQR_KV, DEFAULT_LQR_KPHI, DEFAULT_LQR_KW },
        .use_lqr = true, .theta_ref = -PLANTA_DELTA_G + E->error_ref_deg / GRADOS,
        .u_max = DEFAULT_U_MAX, .deadband = E->deadband_firmware, .notch_hz = E->notch_hz,
    };
    attitude_t att;  attitude_reset(&att);
    odometry_t odo;  odometry_reset(&odo);
    balance_t bal;   balance_reset(&bal);
    const float tau_vel = 1.0f / (6.2831853f * VEL_FILTER_HZ);
    const int cal_n = (int)(GYRO_CAL_TIME_S * 1000 / CONTROL_PERIOD_MS);
    bool calibrado = false, armado = false;
    double rampa = 0, u = 0, u_nuevo = 0;
    double f_fwd = 0, f_up = PLANTA_G, f_gyro = 0;          // salida del filtro del MPU
    double a_mpu = 1.0 - exp(-H * DOS_PI * FC_MPU);

    resultado_t R = { 0 };
    double suma_phi2 = 0, x_min_fin = 1e9, x_max_fin = -1e9;
    int n_fin = 0, n_sat = 0, n_lazo = 0;

    for (int k = 0; k * DT_CONTROL < T_FIN; k++) {
        double t = k * DT_CONTROL;
        bool en_la_mano = t < T_CAL;

        // --- planta y sensores durante el período (en la mano, la planta no se mueve)
        for (int i = 0; i < SUBPASOS; i++) {
            if (i == SUBPASO_COMPUTO) u = u_nuevo;
            ent.tension = u * E->v_motor;
            double ts = t + i * H - T_CAL;          // desde que se suelta
            ent.fuerza_extra = (ts >= 5.0 && ts < 5.1) ? E->empujon_N : 0;
            if (!en_la_mano) rk4(&z, &ent, H);
            estado_t dz = en_la_mano ? (estado_t){ 0 } : derivada(&z, &ent);
            if (en_la_mano) z.w = 0;
            double fa, ua;
            acelerometro(&z, &dz, &fa, &ua);
            f_fwd += a_mpu * (fa - f_fwd);
            f_up  += a_mpu * (ua - f_up);
            f_gyro += a_mpu * (z.w - f_gyro);
        }
        if (fabs(z.phi) > 1.2) { R.cayo = true; R.t_caida = t - T_CAL; break; }

        // --- lo que lee el firmware
        double ruido = E->ruido ? 1.0 : 0.0;
        float acc_fwd = (float)(f_fwd + ruido * PLANTA_ACC_RMS * gauss());
        float acc_up  = (float)(f_up  + ruido * PLANTA_ACC_RMS * gauss());
        float gyro    = (float)(f_gyro + PLANTA_GYRO_BIAS + ruido * PLANTA_GYRO_RMS * gauss());
        double th_cuerpo = z.phi - PLANTA_DELTA_G;
        float cuentas = (float)floor(ENC_COUNTS_PER_REV * (z.x / PLANTA_R - th_cuerpo) / DOS_PI);

        // --- el firmware (mismo orden que control_task.c)
        if (!calibrado) {
            calibrado = attitude_calibrate(&att, gyro, cal_n, GYRO_CAL_MAX_RATE);
        } else {
            attitude_update(&att, acc_fwd, acc_up, gyro, (float)DT_CONTROL, ATTITUDE_TAU_S);
        }
        bool armar = !armado && !en_la_mano && calibrado
                     && fabsf(att.theta - p.theta_ref) < ARM_WINDOW_DEG / GRADOS;
        if (armar) { armado = true; odometry_reset(&odo); balance_reset(&bal); rampa = 0; }
        odometry_update(&odo, cuentas, att.theta, ENC_COUNTS_PER_REV, WHEEL_RADIUS_M,
                        (float)DT_CONTROL, tau_vel);
        if (armado) {
            if (fabsf(att.theta - p.theta_ref) > TILT_LIMIT_DEG / GRADOS) {
                R.cayo = true; R.t_caida = t - T_CAL; break;     // el supervisor corta
            }
            rampa = fmin(rampa + DT_CONTROL / ARM_RAMP_S, 1.0);
            u_nuevo = balance_lqr_step(&bal, &p, odo.x, odo.v, att.theta, att.rate,
                                       (float)DT_CONTROL, (float)(rampa * p.u_max));
            n_lazo++;
            if (fabs(u_nuevo) >= p.u_max - 1e-6) n_sat++;
        }

        // --- medidas
        double phi_deg = z.phi * GRADOS;
        if (!en_la_mano) {
            R.phi_max_deg = fmax(R.phi_max_deg, fabs(phi_deg));
            R.x_max_mm = fmax(R.x_max_mm, fabs(z.x) * 1e3);
        }
        if (t >= T_FIN - 5.0) {
            suma_phi2 += phi_deg * phi_deg;  n_fin++;
            x_min_fin = fmin(x_min_fin, z.x);  x_max_fin = fmax(x_max_fin, z.x);
        }
        if (csv) {
            fprintf(csv, "%d,%.3f,%.5f,%.4f,%.4f,%.4f,%.4f\n", id, t - T_CAL, z.x * 1e3, phi_deg,
                    (att.theta - p.theta_ref) * GRADOS, odo.x * 1e3, u_nuevo);
        }
    }
    if (!R.cayo) {
        R.x_final_mm = 0.5 * (x_min_fin + x_max_fin) * 1e3;
        R.x_pp_mm = (x_max_fin - x_min_fin) * 1e3;
        R.phi_rms_deg = sqrt(suma_phi2 / n_fin);
    }
    R.satura_pct = n_lazo ? 100.0 * n_sat / n_lazo : 0;
    return R;
}

// ---------------------------------------------------------------- copia de la planta
static double verificar_planta(void)
{
    FILE *f = fopen("test_host/referencia_planta.csv", "r");
    if (!f) { printf("falta test_host/referencia_planta.csv\n"); return 1e9; }
    const double K[4] = PLANTA_K_LQR;
    estado_t z;  double t_ref, peor = 0, t = 0;
    entrada_t e = { .v_max = PLANTA_V_BAT };
    bool primero = true;
    estado_t r;
    while (fscanf(f, "%lf,%lf,%lf,%lf,%lf", &t_ref, &r.x, &r.v, &r.phi, &r.w) == 5) {
        if (primero) { z = r; primero = false; continue; }
        while (t < t_ref - 1e-9) {          // LQR continuo, como en la referencia
            e.tension = -(K[0]*z.x + K[1]*z.v + K[2]*z.phi + K[3]*z.w);
            rk4(&z, &e, 1e-5);
            t += 1e-5;
        }
        peor = fmax(peor, fmax(fabs(z.phi - r.phi), fabs(z.x - r.x)));
    }
    fclose(f);
    return peor;
}

int main(void)
{
    int fallas = 0;
    double err = verificar_planta();
    printf("Copia de la planta contra MATLAB (LQR continuo desde 5 grados, 3 s): error max %.2e\n", err);
    // ~4e-6 es la interpolación de ode45 (deval); un término mal copiado da más de 1e-3
    if (!(err < 1e-5)) { printf("FALLA: la planta en C no coincide con planta_con_motor.m\n"); fallas++; }

    const double V = PLANTA_V_BAT - 2.0;    // L298N
    const escenario_t E[] = {
        //  nombre                               phi0  V_motor  zm_real deadband err_ref empujon ruido
        { "nominal, suelto a 2 grados",           2.0, V,       0.00,   0.00,    0.0,    0.0,  true, 0.0 },
        { "sin ruido (para comparar)",            2.0, V,       0.00,   0.00,    0.0,    0.0,  false, 0.0 },
        { "empujon de 3 N durante 0,1 s",         2.0, V,       0.00,   0.00,    0.0,    3.0,  true, 0.0 },
        { "zona muerta 20 %, sin compensar",      2.0, V,       0.20,   0.00,    0.0,    0.0,  true, 0.0 },
        { "zona muerta 20 %, deadband 0,15",      2.0, V,       0.20,   0.15,    0.0,    0.0,  true, 0.0 },
        { "zona muerta 20 %, deadband 0,20",      2.0, V,       0.20,   0.20,    0.0,    0.0,  true, 0.0 },
        { "ref mal medida por 1 grado",           2.0, V,       0.00,   0.00,    1.0,    0.0,  true, 0.0 },
        { "bateria baja (7,6 V al motor)",        2.0, 7.6,     0.00,   0.00,    0.0,    0.0,  true, 0.0 },
        { "bateria llena (10,6 V al motor)",      2.0, 10.6,    0.00,   0.00,    0.0,    0.0,  true, 0.0 },
        // Ensayo del 29/10 en el aire: zona muerta de ~18 %, y la rueda gira más rápido por PWM
        // que lo que da el modelo; si es porque llega más tensión, el motor es hasta 1,37 veces
        // más fuerte que lo supuesto (si es porque el motor es más rápido, no cambia nada)
        { "medido: zona muerta 18 %, deadband 0,18", 2.0, V,    0.18,   0.18,    0.0,    0.0,  true, 0.0 },
        { "medido y motor 1,37 veces mas fuerte",  2.0, 1.37*V, 0.18,   0.18,    0.0,    0.0,  true, 0.0 },
        // 29/10 en el piso el cuerpo vibraba a ~7 Hz: el rechaza banda no tiene que empeorar el lazo
        { "medido, con rechaza banda en 7 Hz",    2.0, V,       0.18,   0.18,    0.0,    0.0,  true, 7.0 },
        { "empujon, con rechaza banda en 7 Hz",   2.0, V,       0.18,   0.18,    0.0,    3.0,  true, 7.0 },
    };
    const int n = (int)(sizeof E / sizeof E[0]);
    FILE *csv = fopen("test_host/banco_lqr.csv", "w");
    if (csv) fprintf(csv, "escenario,t_s,x_mm,phi_deg,theta_medido_deg,x_medido_mm,u\n");

    printf("\nLQR del firmware: kx %.2f kv %.2f kphi %.2f kw %.2f; %d cuentas/vuelta; IMU tau %.1f s\n",
           DEFAULT_LQR_KX, DEFAULT_LQR_KV, DEFAULT_LQR_KPHI, DEFAULT_LQR_KW,
           (int)ENC_COUNTS_PER_REV, ATTITUDE_TAU_S);
    printf("%-38s %8s %8s %9s %9s %9s %8s\n", "escenario (20 s)", "cae?", "phi max", "x max",
           "x final", "x p-p", "phi rms");
    printf("%-38s %8s %8s %9s %9s %9s %8s\n", "", "", "[grados]", "[mm]", "[mm]", "[mm]", "[grados]");
    resultado_t R[16];
    for (int i = 0; i < n; i++) {
        R[i] = correr(&E[i], csv, i);
        if (R[i].cayo) {
            printf("%-38s %5s %4.1fs\n", E[i].nombre, "CAE", R[i].t_caida);
        } else {
            printf("%-38s %8s %8.2f %9.1f %9.1f %9.1f %8.3f\n", E[i].nombre, "no",
                   R[i].phi_max_deg, R[i].x_max_mm, R[i].x_final_mm, R[i].x_pp_mm, R[i].phi_rms_deg);
        }
    }
    if (csv) fclose(csv);

    // Criterios: lo que tiene que cumplir el firmware antes de probarlo en el robot
    for (int i = 0; i < n; i++) {
        if (R[i].cayo && i != 3) { printf("FALLA: se cae en \"%s\"\n", E[i].nombre); fallas++; }
    }
    if (!R[0].cayo && (fabs(R[0].x_final_mm) > 10 || R[0].phi_rms_deg > 0.5)) {
        printf("FALLA: el nominal no se queda quieto en el lugar\n"); fallas++;
    }
    printf("\n%s\n", fallas ? "HAY FALLAS" : "OK: el banco pasa");
    printf("serie temporal -> test_host/banco_lqr.csv\n");
    return fallas ? 1 : 0;
}
