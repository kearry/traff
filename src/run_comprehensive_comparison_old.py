import os
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.comparison_framework import ComparisonFramework

def main():
    """Run a comprehensive comparison of all controllers across all scenarios."""
    parser = argparse.ArgumentParser(description='Run comprehensive traffic controller comparison')
    parser.add_argument('--include-rl', action='store_true',
                        help='Include reinforcement learning controllers in comparison')
    parser.add_argument('--steps', type=int, default=1000,
                        help='Number of simulation steps per run')
    parser.add_argument('--runs', type=int, default=3,
                        help='Number of runs per configuration')
    parser.add_argument('--gui', action='store_true',
                        help='Show SUMO GUI during simulation')
    args = parser.parse_args()
    
    # Initialize the comparison framework
    comparison = ComparisonFramework()
    
    # Select controller types
    controller_types = ["Traditional", "Wired AI", "Wireless AI"]
    
    if args.include_rl:
        controller_types.extend(["Wired RL", "Wireless RL"])
        
        # Find RL model paths
        model_paths = {}
        models_dir = os.path.join(project_root, "data", "models")
        
        if os.path.exists(models_dir):
            # Look for the most recent model for each RL controller type
            for controller_type in ["wired_rl", "wireless_rl"]:
                model_files = [f for f in os.listdir(models_dir) 
                             if f.startswith(controller_type) and f.endswith('.pkl')]
                if model_files:
                    # Sort by episode number to get the most recent
                    model_files.sort(key=lambda x: int(x.split('_episode_')[1].split('.')[0]))
                    newest_model = os.path.join(models_dir, model_files[-1])
                    
                    # Map to controller type
                    if controller_type == "wired_rl":
                        model_paths["Wired RL"] = newest_model
                    elif controller_type == "wireless_rl":
                        model_paths["Wireless RL"] = newest_model
        
    else:
        model_paths = None
    
    # Define scenarios to test
    scenarios = [
        "light_traffic",
        "moderate_traffic", 
        "heavy_traffic",
        "peak_hour_morning"
    ]
    
    print(f"Running comprehensive comparison with controllers: {controller_types}")
    print(f"Testing scenarios: {scenarios}")
    print(f"Using {args.runs} runs per configuration, {args.steps} steps per run")
    
    # Run the comparison
    results = comparison.run_comparison(
        scenarios=scenarios,
        controller_types=controller_types,
        steps=args.steps,
        runs_per_config=args.runs,
        gui=args.gui,
        model_paths=model_paths
    )
    
    # Print overall summary
    print("\nOverall Performance Summary:")
    print("=" * 80)
    
    for controller in controller_types:
        if controller in results["summary"]:
            print(f"\n{controller}:")
            for metric, value in results["summary"][controller].items():
                print(f"  {metric}: {value:.4f}")

if __name__ == "__main__":
    main()