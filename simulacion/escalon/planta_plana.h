// Planta plana del robot para bajar escalones: cuerpo + pata de cuatro barras (un grado de
// libertad, movida por los servos) + rueda con motor, con contacto contra un piso escalonado,
// vuelo y aterrizaje. Las dos patas y las dos ruedas van juntas (sin rolido ni guiñada).
//
// Coordenadas generalizadas q = [X, Z, th, a, f]:
//   X, Z  centro de masa del cuerpo en el mundo [m] (X adelante, Z arriba)
//   th    cabeceo del cuerpo [rad], positivo hacia adelante (la cabeza va hacia +X)
//   a     ángulo de la pata, el que se le pide al servo [rad] (0 = agachado)
//   f     giro de la rueda respecto del eslabón que lleva el motor [rad], + rodando hacia adelante
// Los giros son positivos en sentido horario mirando el robot desde su derecha (X a la derecha,
// Z arriba): un punto en (dx, dz) respecto del centro de giro va a w·(dz, -dx).
#pragma once

#include <stdbool.h>

#define PP_NQ 5
enum { PP_X = 0, PP_Z, PP_TH, PP_A, PP_F };

// Piso: escalones que bajan hacia -X. El borde del primero está en X = 0 (arriba, Z = 0, para
// X >= 0); cada escalón baja `alto` y tiene `pisada` de largo. n_escalones = 0: piso plano.
typedef struct {
    double alto, pisada;
    int    n_escalones;
    double alto_ultimo;         // [m] el último escalón, si es de otra altura (0 = alto)
} piso_t;

typedef struct {
    // masas e inercias
    double m_cuerpo, i_cuerpo;          // [kg], [kg m2] alrededor de su centro de masa
    double m_rueda;                     // [kg] las dos ruedas con su motor, en el eje
    double m_eslabones;                 // [kg] manivelas, balancines y acopladores, en su centro
                                        // de masa conjunto (se mueve con la pata)
    double i_eslabon;                   // [kg m2] lo que gira con el eslabón del motor
    double j_rueda, j_rotor, n_reductor;// [kg m2] las dos ruedas, los dos rotores; relación
    double j_servo;                     // [kg m2] inercia de los servos vista desde la pata
    double r_rueda;                     // [m]
    // motores de rueda (los dos juntos, del lado de la rueda)
    double beta_v, b_m, b_eje, friccion_seca;   // [N m/V], [N m s/rad], [N m s/rad], [N m]
    double v_motor;                     // [V] lo que llega al motor con PWM 1
    // servos (los dos juntos)
    double servo_par_max, servo_vel_max;// [N m] de calado, [rad/s] en vacío
    double servo_ganancia;              // [1/rad]: error que lleva el servo a fondo
    double servo_b;                     // [N m s/rad] fricción viscosa del reductor
    // contacto
    double k_rueda, c_rueda;            // [N/m], [N s/m] de las dos ruedas contra el piso
    double k_cuerpo, c_cuerpo;          // [N/m], [N s/m] de un golpe del cuerpo
    double mu, v_resbale;               // fricción de Coulomb y velocidad de regularización [m/s]
    double mu_cuerpo;                   // fricción de la cabina contra el escalón (0 = mu)
    double recorte;                     // [m] la cabina recortada adelante (la masa queda igual)
    double g;
} planta_t;

typedef struct {
    double tension;     // [V] a los motores de rueda (los dos)
    double a_pedido;    // [rad] al servo
} entrada_planta_t;

// Lo que pasa en el instante (para medir y para los sensores)
typedef struct {
    double ddq[PP_NQ];
    double n_rueda;             // [N] fuerza normal total piso-rueda
    double n_cuerpo;            // [N] fuerza total de golpes del cuerpo
    double par_servo;           // [N m] de los dos servos
    double par_motor;           // [N m] en la rueda
    bool   rueda_apoyada, cuerpo_toca;
} salida_planta_t;

// Cinemática de la pata: eje de la rueda (p) y centro de masa de los eslabones (l) respecto
// del centro de masa del cuerpo, en ejes del cuerpo, y ángulo del eslabón que lleva el motor (g),
// con sus derivadas respecto de a. La provee quien arma la planta (tabla generada desde el
// modelo de cuatro barras).
typedef struct {
    double px, pz, g;           // [m], [m], [rad]
    double dpx, dpz, dg;        // d/da
    double ddpx, ddpz, ddg;     // d2/da2
    double lx, lz, dlx, dlz, ddlx, ddlz;
} pata_t;
void pata_cinematica(double a, pata_t *p);

// Puntos del cuerpo que pueden golpear el piso (ejes del cuerpo, respecto de su centro de masa)
extern const int PP_N_PUNTOS;
extern const double PP_PUNTOS[][2];

void planta_derivada(const planta_t *P, const piso_t *piso, const double q[PP_NQ],
                     const double dq[PP_NQ], const entrada_planta_t *e, salida_planta_t *s);
void planta_rk4(const planta_t *P, const piso_t *piso, double q[PP_NQ], double dq[PP_NQ],
                const entrada_planta_t *e, double h, salida_planta_t *s);

// Altura del piso en X y distancia a lo largo de un rayo desde (x0, z0) en la dirección
// (ux, uz) unitaria hasta el piso; devuelve < 0 si no lo corta antes de max_m.
double piso_altura(const piso_t *piso, double x);
double piso_nivel(const piso_t *piso, int k);
double piso_distancia(const piso_t *piso, double x, double z);
double piso_distancia_caja(const piso_t *piso, const double q[PP_NQ], double x0, double x1, double z0, double z1);
double piso_rayo(const piso_t *piso, double x0, double z0, double ux, double uz, double max_m);

// Posición en el mundo de un punto del cuerpo (ejes del cuerpo, respecto del centro de masa)
void cuerpo_a_mundo(const double q[PP_NQ], double bx, double bz, double *wx, double *wz);
// Eje de la rueda en el mundo
void eje_rueda(const double q[PP_NQ], double *wx, double *wz);
