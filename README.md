# Navier-Stokes Solver using Lattice-Boltzmann Method (LBM)

This project simulates 2D incompressible flow around a cylinder using the Lattice-Boltzmann Method (D2Q9) with a focus on vortex shedding (Kármán vortex street).

## Features

- LBM-based solver for 2D incompressible Navier-Stokes
- Obstacle modeled as a cylinder using bounce-back boundary conditions
- Visualization of velocity and vorticity fields
- Periodic boundary on top and bottom
- Inflow (Zou/He Dirichlet) and outflow boundary handling

## Technologies

- Python
- JAX (for fast numerical computation)
- Matplotlib
- cmasher (color maps)
- tqdm (progress bar)

## How to Run

```bash
pip install -r requirements.txt
python lbm_solver.py
