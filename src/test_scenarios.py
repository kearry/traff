import os
import sys
import json
import time
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.simulation.scenario_runner import ScenarioRunner

def main():
    """Run tests with different scenarios and controllers."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run traffic scenario tests')
    parser.add_argument('--scenario', type=str, default=None,
                        help='Specific scenario to run (without .rou.xml extension)')
    parser.add_argument('--controller', type=str, default=None,
                        choices=['Wired AI', 'Wireless AI', 'Traditional'],
                        help='Specific controller to use')
    parser.add_argument('--steps', type=int, default=1000,
                        help='Number of simulation steps to run')
    parser.add_argument('--gui', action='store_true',
                        help='Show SUMO GUI during simulation')
    parser.add_argument('--delay', type=int, default=0,
                        help='Delay between steps (ms)')
    parser.add_argument('--all', action='store_true',
                        help='Run all scenarios with all controllers')
    args = parser.parse_args()
    
    # Initialize the scenario runner
    runner = ScenarioRunner()
    
    # Get the list of scenarios
    scenarios_dir = os.path.join(project_root, "config", "scenarios")
    scenario_files = [f for f in os.listdir(scenarios_dir) if f.endswith('.rou.xml')]
    
    if not scenario_files:
        print("No scenario files found! Run generate_scenarios.py first.")
        return
    
    # Define the controllers to test
    controllers = ['Wired AI', 'Wireless AI', 'Traditional']
    
    # Results dictionary
    results = {}
    
    # Run the specified test or all tests
    if args.all:
        print("Running all scenarios with all controllers...")
        for scenario_file in scenario_files:
            scenario_name = os.path.splitext(scenario_file)[0]
            scenario_path = os.path.join(scenarios_dir, scenario_file)
            results[scenario_name] = {}
            
            for controller in controllers:
                print(f"\nRunning {scenario_name} with {controller}...")
                metrics = runner.run_scenario(
                    scenario_path, controller, 
                    steps=args.steps, gui=args.gui, delay=args.delay
                )
                results[scenario_name][controller] = {
                    'avg_waiting_time': metrics.get('avg_waiting_time', 0),
                    'avg_speed': metrics.get('avg_speed', 0),
                    'throughput': metrics.get('throughput', 0),
                    'avg_response_time': metrics.get('avg_response_time', 0) * 1000,  # Convert to ms
                    'avg_decision_time': metrics.get('avg_decision_time', 0) * 1000   # Convert to ms
                }
    elif args.scenario and args.controller:
        scenario_file = f"{args.scenario}.rou.xml"
        scenario_path = os.path.join(scenarios_dir, scenario_file)
        
        if not os.path.exists(scenario_path):
            print(f"Scenario file {scenario_file} not found!")
            return
        
        print(f"\nRunning {args.scenario} with {args.controller}...")
        metrics = runner.run_scenario(
            scenario_path, args.controller, 
            steps=args.steps, gui=args.gui, delay=args.delay
        )
        
        results[args.scenario] = {
            args.controller: {
                'avg_waiting_time': metrics.get('avg_waiting_time', 0),
                'avg_speed': metrics.get('avg_speed', 0),
                'throughput': metrics.get('throughput', 0),
                'avg_response_time': metrics.get('avg_response_time', 0) * 1000,  # Convert to ms
                'avg_decision_time': metrics.get('avg_decision_time', 0) * 1000   # Convert to ms
            }
        }
    else:
        print("Please specify either --all to run all tests or both --scenario and --controller for a specific test.")
        return
    
    # Save results to a JSON file
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    results_file = os.path.join(project_root, "data", "outputs", f"scenario_results_{timestamp}.json")
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=4)
    
    print(f"\nResults saved to {results_file}")
    
    # Print summary
    print("\nSummary of Results:")
    print("-" * 80)
    print(f"{'Scenario':<25} {'Controller':<15} {'Avg Wait (s)':<15} {'Avg Speed (m/s)':<15} {'Throughput':<10} {'Resp Time (ms)':<15} {'Dec Time (ms)':<15}")
    print("-" * 80)
    
    for scenario, ctrl_results in results.items():
        for controller, metrics in ctrl_results.items():
            print(f"{scenario:<25} {controller:<15} {metrics['avg_waiting_time']:<15.2f} {metrics['avg_speed']:<15.2f} {metrics['throughput']:<10} {metrics['avg_response_time']:<15.2f} {metrics['avg_decision_time']:<15.2f}")

if __name__ == "__main__":
    main()