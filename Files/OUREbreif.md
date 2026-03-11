# Project: OURE (Orbital Uncertainty & Risk Engine)

## Project Vision
OURE is a high-performance CLI tool designed to calculate the Probability of Collision ($P_c$) between satellites in Low Earth Orbit (LEO). It focuses on space situational awareness and financial risk modeling.

## Tech Stack & Architecture
- **Language:** Python (with NumPy/SciPy) or Rust (for high-speed simulation).
- **Core Algorithms:** SGP4 Propagation, J2 Perturbations, Monte Carlo Simulations, and B-Plane risk methods.
- **Hardware:** Optimized for Apple Silicon M4 (use Accelerate framework or Metal if needed).

## Operational Rules
- **Mathematical Rigor:** Always use LaTeX for formulas (e.g., $$P_c = \iint_A f(x, y) \, dA$$).
- **Performance First:** Since this involves heavy simulations, suggest vectorized operations over loops.
- **Tone:** Technical yet simple. Use analogies involving "highway traffic" or "financial volatility" to explain orbital mechanics.

## Development Priorities
1. **Accuracy:** Validating SGP4 against TLE (Two-Line Element) sets.
2. **Speed:** Efficiently running 10,000+ Monte Carlo iterations.
3. **CLI UX:** A clean, intuitive interface for space engineers.

## User Context (Hrishi)
- I am a 22-year-old M.Tech CS student at SPPU.