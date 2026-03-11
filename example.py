import time
import numpy as np
import random
from oure.core.models import StateVector
from oure.conjunction.assessor import KDTreeScreener

def generate_mock_catalog(num_objects: int = 27000):
    """Generates a catalog of randomly distributed satellites in LEO."""
    # Approximate Earth radius + LEO altitude (6371 + 400 to 2000 km)
    states = []
    for _ in range(num_objects):
        r = random.uniform(6700, 8000) 
        theta = random.uniform(0, np.pi)
        phi = random.uniform(0, 2 * np.pi)
        
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        
        # Velocity is roughly orbital velocity, mostly in XY plane, simplified
        # Not physically accurate, just for benchmarking KDTree
        
        states.append(StateVector(
            x=x, y=y, z=z,
            vx=random.uniform(-7, 7), 
            vy=random.uniform(-7, 7), 
            vz=random.uniform(-7, 7)
        ))
    return states

def benchmark_screening():
    print("Generating mock catalog of 27,000 satellites...")
    start_time = time.time()
    catalog = generate_mock_catalog(27000)
    print(f"Generation took: {time.time() - start_time:.2f} seconds\n")
    
    print("Building KD-Tree and querying pairs within 5km radius...")
    start_time = time.time()
    
    screener = KDTreeScreener(screening_radius_km=5.0)
    pairs = screener.find_potential_conjunctions(catalog)
    
    elapsed = time.time() - start_time
    print(f"Screening complete! Found {len(pairs)} potential conjunction pairs.")
    print(f"Screening took: {elapsed:.4f} seconds.")
    
    if elapsed < 2.0:
        print("Performance metric passed (O(N log N) scaling is fast).")
    else:
        print("Performance metric failed (took too long).")

if __name__ == "__main__":
    benchmark_screening()
