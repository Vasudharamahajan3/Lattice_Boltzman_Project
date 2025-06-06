import jax
import jax.numpy as jnp
import matplotlib.pyplot as plt
import cmasher as cmr
from tqdm import tqdm

# Simulation parameters
N_ITERATIONS = 15_000
REYNOLDS_NUMBER = 80
N_POINTS_X = 300
N_POINTS_Y = 50
CYLINDER_CENTER_INDEX_X = N_POINTS_X // 5
CYLINDER_CENTER_INDEX_Y = N_POINTS_Y // 2
CYLINDER_RADIUS_INDICES = N_POINTS_Y // 9
MAX_HORIZONTAL_INFLOW_VELOCITY = 0.04
VISUALIZE = True
PLOT_EVERY_N_STEPS = 100
SKIP_FIRST_N_ITERATIONS = 5000

# LBM parameters
N_DISCRETE_VELOCITIES = 9
LATTICE_VELOCITIES = jnp.array([[0, 1, 0, -1, 0, 1, -1, -1, 1],
                                [0, 0, 1, 0, -1, 1, 1, -1, -1]])
LATTICE_INDICES = jnp.arange(9)
OPPOSITE_LATTICE_INDICES = jnp.array([0, 3, 4, 1, 2, 7, 8, 5, 6])
LATTICE_WEIGHTS = jnp.array([4/9, 1/9, 1/9, 1/9, 1/9, 1/36, 1/36, 1/36, 1/36])
RIGHT_VELOCITIES = jnp.array([1, 5, 8])
UP_VELOCITIES = jnp.array([2, 5, 6])
LEFT_VELOCITIES = jnp.array([3, 6, 7])
DOWN_VELOCITIES = jnp.array([4, 7, 8])
PURE_VERTICAL_VELOCITIES = jnp.array([0, 2, 4])
PURE_HORIZONTAL_VELOCITIES = jnp.array([0, 1, 3])

def get_density(f):
    return jnp.sum(f, axis=-1)

def get_macroscopic_velocities(f, rho):
    return jnp.einsum("NMQ,dQ->NMd", f, LATTICE_VELOCITIES) / rho[..., None]

def get_equilibrium_discrete_velocities(u, rho):
    cu = jnp.einsum("dQ,NMd->NMQ", LATTICE_VELOCITIES, u)
    u_sq = jnp.sum(u ** 2, axis=-1)
    return rho[..., None] * LATTICE_WEIGHTS[None, None, :] * (
        1 + 3 * cu + 4.5 * cu**2 - 1.5 * u_sq[..., None])

def main():
    jax.config.update("jax_enable_x64", True)

    nu = MAX_HORIZONTAL_INFLOW_VELOCITY * CYLINDER_RADIUS_INDICES / REYNOLDS_NUMBER
    omega = 1 / (3 * nu + 0.5)

    x = jnp.arange(N_POINTS_X)
    y = jnp.arange(N_POINTS_Y)
    X, Y = jnp.meshgrid(x, y, indexing="ij")

    obstacle_mask = jnp.sqrt((X - CYLINDER_CENTER_INDEX_X)**2 +
                             (Y - CYLINDER_CENTER_INDEX_Y)**2) < CYLINDER_RADIUS_INDICES

    velocity_profile = jnp.zeros((N_POINTS_X, N_POINTS_Y, 2))
    velocity_profile = velocity_profile.at[:, :, 0].set(MAX_HORIZONTAL_INFLOW_VELOCITY)

    @jax.jit
    def update(f_prev):
        f_prev = f_prev.at[-1, :, LEFT_VELOCITIES].set(f_prev[-2, :, LEFT_VELOCITIES])
        rho = get_density(f_prev)
        u = get_macroscopic_velocities(f_prev, rho)

        u = u.at[0, 1:-1, :].set(velocity_profile[0, 1:-1, :])
        rho = rho.at[0, :].set(
            (get_density(f_prev[0, :, PURE_VERTICAL_VELOCITIES].T) +
             2 * get_density(f_prev[0, :, LEFT_VELOCITIES].T)) / (1 - u[0, :, 0])
        )

        feq = get_equilibrium_discrete_velocities(u, rho)
        f_prev = f_prev.at[0, :, RIGHT_VELOCITIES].set(feq[0, :, RIGHT_VELOCITIES])

        f_post = f_prev - omega * (f_prev - feq)

        for i in range(N_DISCRETE_VELOCITIES):
            f_post = f_post.at[obstacle_mask, LATTICE_INDICES[i]].set(
                f_prev[obstacle_mask, OPPOSITE_LATTICE_INDICES[i]]
            )

        f_streamed = f_post
        for i in range(N_DISCRETE_VELOCITIES):
            f_streamed = f_streamed.at[:, :, i].set(
                jnp.roll(
                    jnp.roll(f_post[:, :, i], LATTICE_VELOCITIES[0, i], axis=0),
                    LATTICE_VELOCITIES[1, i], axis=1,
                )
            )
        return f_streamed

    f_prev = get_equilibrium_discrete_velocities(
        velocity_profile, jnp.ones((N_POINTS_X, N_POINTS_Y)))

    plt.style.use("dark_background")
    plt.figure(figsize=(15, 6), dpi=100)

    for iteration_index in tqdm(range(N_ITERATIONS)):
        f_prev = update(f_prev)

        if iteration_index % PLOT_EVERY_N_STEPS == 0 and VISUALIZE and iteration_index > SKIP_FIRST_N_ITERATIONS:
            rho = get_density(f_prev)
            u = get_macroscopic_velocities(f_prev, rho)
            mag = jnp.linalg.norm(u, axis=-1)
            du_dx, du_dy = jnp.gradient(u[..., 0])
            dv_dx, dv_dy = jnp.gradient(u[..., 1])
            curl = du_dy - dv_dx

            # Velocity plot
            plt.subplot(211)
            plt.contourf(X, Y, mag, levels=50, cmap=cmr.amber)
            plt.colorbar().set_label("Velocity Magnitude")
            plt.gca().add_patch(plt.Circle(
                (CYLINDER_CENTER_INDEX_X, CYLINDER_CENTER_INDEX_Y),
                CYLINDER_RADIUS_INDICES,
                color="darkgreen"))

            # Vorticity plot
            plt.subplot(212)
            plt.contourf(X, Y, curl, levels=50, cmap=cmr.redshift, vmin=-0.02, vmax=0.02)
            plt.colorbar().set_label("Vorticity Magnitude")
            plt.gca().add_patch(plt.Circle(
                (CYLINDER_CENTER_INDEX_X, CYLINDER_CENTER_INDEX_Y),
                CYLINDER_RADIUS_INDICES,
                color="darkgreen"))

            # Save to results/
            plt.tight_layout()
            plt.savefig(f"results/frame_{iteration_index:05d}.png", dpi=150)
            plt.clf()

    if VISUALIZE:
        plt.show()

if __name__ == "__main__":
    main()
