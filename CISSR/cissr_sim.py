"""
CISSR Simulation Module
Bridges BioGrid2.0 symbolic logic with Nuclear Donut physical simulation

Key Features:
- Material self-healing kinetics
- Microbial activity modeling
- Sensor fusion and decision logic
- Integration with harmonic_sim.py and water_sim.py
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class CISSRConfig:
    """Configuration parameters for CISSR simulation"""
    healing_agent_volume: float = 10.0  # liters
    microbial_growth_rate: float = 0.1  # per hour
    sensor_interval: int = 60  # seconds
    radiation_tolerance: float = 1000.0  # Grays

# Published crystalline-admixture performance: cracks up to ~0.4 mm close
# completely, 150 um in 28 days under water, 400 um in 28 days with 10% CSA
# plus 1.5% CA. 0.4 mm over 28 days is 5.95e-4 mm/hour. The previous value of
# 0.2 mm/hour implied 134 mm in 28 days — 336x the best documented rate, and
# 300x wider than any crack the literature reports sealing. See
# legacy/run-log.md entry 11.
LITERATURE_HEALING_RATE_MM_PER_HOUR = 0.4 / (28 * 24)   # 5.95e-4
MAX_HEALABLE_CRACK_MM = 0.4


class MaterialHealingEngine:
    """Simulates self-healing of crystalline materials"""

    def __init__(self, crack_threshold: float = 0.5,
                 healing_rate_mm_per_hour: float = LITERATURE_HEALING_RATE_MM_PER_HOUR,
                 max_healable_mm: float = MAX_HEALABLE_CRACK_MM):
        self.crack_threshold = crack_threshold
        self.healing_rate = healing_rate_mm_per_hour
        self.max_healable_mm = max_healable_mm

    def detect_cracks(self, stress_data: np.ndarray) -> List[Dict]:
        """
        Identify cracks from stress data.

        Returns dicts carrying BOTH position and width. The previous version
        returned bare array indices, which heal_crack() then multiplied as if
        they were widths — a crack at index 97 "healed" to 77.6 of nothing.
        Position and width are different quantities and are now kept apart.
        """
        cracks = []
        for i, stress in enumerate(stress_data):
            if stress > self.crack_threshold:
                # width scales with stress above threshold; 1 mm per unit
                width_mm = float(stress - self.crack_threshold)
                cracks.append({"index": i, "width_mm": width_mm})
        return cracks

    def heal_crack(self, crack: Dict, hours: float = 28 * 24) -> Dict:
        """
        Close a crack over `hours` of healing, at the literature rate.

        Returns the crack with its residual width. Cracks wider than
        `max_healable_mm` do not fully close no matter how long they are given —
        that ceiling is the main finding of the self-healing concrete work, and
        a kinetics model without it will always over-promise.
        """
        width = crack["width_mm"]
        closed = min(width, self.healing_rate * hours)
        residual = width - closed
        return {
            "index": crack["index"],
            "initial_width_mm": width,
            "residual_width_mm": residual,
            "fully_healed": residual <= 0.0 and width <= self.max_healable_mm,
            "exceeds_healable_width": width > self.max_healable_mm,
        }

class MicrobialSystem:
    """Simulates engineered microbes for bio-remediation"""
    
    def __init__(self, population: float = 1e6):
        self.population = population
        self.metabolic_rate = 0.05
    
    def grow(self, nutrients: float, temperature: float):
        """Microbial growth model"""
        growth_factor = nutrients / (nutrients + 1.0)
        temp_factor = np.exp(-((temperature - 30.0) / 10.0) ** 2)
        self.population *= (1 + self.metabolic_rate * growth_factor * temp_factor)
    
    def precipitate_minerals(self) -> float:
        """
        Mineral precipitation for crack sealing.

        STILL A PLACEHOLDER — units are arbitrary and there is no published
        benchmark wired in yet. Do not quote this number.
        """
        return self.population * 1e-6

class CISSRController:
    """Main decision engine for self-healing"""
    
    def __init__(self, config: CISSRConfig):
        self.config = config
        self.healing_engine = MaterialHealingEngine()
        self.microbes = MicrobialSystem()
        self.healing_history = []
    
    def sense_and_respond(self, sensor_data: Dict, hours: float = 28 * 24):
        """Main decision loop"""
        # 1. Detect damage
        cracks = self.healing_engine.detect_cracks(sensor_data.get('stress', []))

        # 2. Assess severity
        if cracks:
            widths = [c["width_mm"] for c in cracks]
            print(f"Detected {len(cracks)} cracks, "
                  f"widths {min(widths):.3f}-{max(widths):.3f} mm")

            # 3. Choose response
            for crack in cracks:
                self.healing_history.append(
                    self.healing_engine.heal_crack(crack, hours=hours))
            
            # 4. Trigger biological if needed
            if len(cracks) > 5:
                self.microbes.grow(10.0, sensor_data.get('temperature', 25.0))
                mineral = self.microbes.precipitate_minerals()
                print(f"Microbes precipitated {mineral:.2f} units of mineral")
        
        return self.healing_history

# Integration with existing Nuclear Donut modules
def integrate_with_harmonic_sim(harmonic_output: np.ndarray) -> Dict:
    """Connect harmonic_sim.py resonance data to CISSR"""
    stress_map = np.abs(harmonic_output)  # Placeholder conversion
    return {'stress': stress_map}

def integrate_with_water_sim(water_flow: np.ndarray) -> Dict:
    """Connect water_sim.py flow data to CISSR"""
    # Check for flow anomalies (potential leaks)
    anomalies = np.where(water_flow < 0.5)[0]
    return {'flow_anomalies': anomalies}

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="CISSR self-healing simulation")
    parser.add_argument("--seed", type=int, default=42,
                        help="RNG seed. Unseeded runs cannot be regression "
                             "tested — see legacy/run-log.md entry 11")
    parser.add_argument("--healing-hours", type=float, default=28 * 24,
                        help="Healing window in hours (default: 28 days, the "
                             "standard test period in the literature)")
    parser.add_argument("--samples", type=int, default=100,
                        help="Number of stress sensor samples")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)

    config = CISSRConfig()
    controller = CISSRController(config)

    test_sensor_data = {
        'stress': rng.normal(0.3, 0.2, args.samples),
        'temperature': 30.0,
    }

    result = controller.sense_and_respond(test_sensor_data,
                                          hours=args.healing_hours)

    healed = [r for r in result if r["fully_healed"]]
    too_wide = [r for r in result if r["exceeds_healable_width"]]
    print(f"\nHealing actions:      {len(result)}")
    print(f"  fully closed:       {len(healed)}")
    print(f"  exceed 0.4mm limit: {len(too_wide)} (cannot fully close)")
    print(f"  healing rate used:  {LITERATURE_HEALING_RATE_MM_PER_HOUR:.2e} mm/hour")
    print(f"  window:             {args.healing_hours:.0f} h "
          f"({args.healing_hours/24:.0f} days), seed {args.seed}")
