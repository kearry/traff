import os
import sys
import argparse
import json
import time
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.simulation.scenario_runner import ScenarioRunner

class ComparisonFramework:
    """
    Framework for comprehensive comparison of different traffic control strategies.
    """
    def __init__(self, output_dir=None):
        """Initialize the comparison framework."""
        if output_dir is None:
            output_dir = os.path.join(project_root, "data", "outputs", "comparison_results")
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize the scenario runner
        self.scenario_runner = ScenarioRunner()
        
        # Define controller types for comparison
        self.controller_types = [
            "Traditional", 
            "Wired AI", 
            "Wireless AI"
        ]
        
        # Check if RL controllers are available
        try:
            from src.ai.reinforcement_learning.wired_rl_controller import WiredRLController
            from src.ai.reinforcement_learning.wireless_rl_controller import WirelessRLController
            self.rl_available = True
            self.controller_types.extend(["Wired RL", "Wireless RL"])
        except ImportError:
            self.rl_available = False
        
        # Define scenarios to test
        self.scenarios = [
            "light_traffic",
            "moderate_traffic",
            "heavy_traffic",
            "peak_hour_morning"
        ]
        
        # Define metrics to track
        self.metrics = [
            "avg_waiting_time",
            "avg_speed",
            "throughput",
            "avg_response_time",
            "avg_decision_time"
        ]
    
    def run_comparison(self, scenarios=None, controller_types=None, steps=1000, 
                      runs_per_config=3, gui=False, model_paths=None):
        """
        Run a complete comparison across specified scenarios and controllers.
        
        Args:
            scenarios: List of scenarios to test (default: all available)
            controller_types: List of controller types to test (default: all available)
            steps: Number of simulation steps per run
            runs_per_config: Number of runs for each scenario-controller combination
            gui: Whether to show SUMO GUI
            model_paths: Dictionary mapping RL controller types to model paths
            
        Returns:
            dict: Comprehensive comparison results
        """
        # Use defaults if not specified
        if scenarios is None:
            scenarios = self.scenarios
        
        if controller_types is None:
            controller_types = self.controller_types
        
        # Validate controller types
        valid_controllers = []
        for controller in controller_types:
            if controller in self.controller_types:
                valid_controllers.append(controller)
            else:
                print(f"Warning: Unknown controller type '{controller}'. Skipping.")
        
        if not valid_controllers:
            print("Error: No valid controller types specified.")
            return {}
        
        # Initialize results structure
        comparison_results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "parameters": {
                "steps": steps,
                "runs_per_config": runs_per_config
            },
            "scenarios": {},
            "summary": {}
        }
        
        # Run comparison for each scenario
        for scenario in scenarios:
            print(f"\n{'='*80}")
            print(f"Running comparison for scenario: {scenario}")
            print(f"{'='*80}")
            
            scenario_results = {}
            
            for controller_type in valid_controllers:
                # Skip RL controllers if not available
                if controller_type in ["Wired RL", "Wireless RL"] and not self.rl_available:
                    print(f"Skipping {controller_type} (not available)")
                    continue
                
                print(f"\nTesting {controller_type} on {scenario}...")
                
                # Get model path for RL controllers if available
                model_path = None
                if model_paths and controller_type in model_paths:
                    model_path = model_paths[controller_type]
                    print(f"Using pre-trained model: {model_path}")
                
                # Initialize controller results
                controller_results = {
                    "runs": [],
                    "avg_metrics": {metric: 0 for metric in self.metrics}
                }
                
                # Run multiple times for statistical significance
                for run in range(runs_per_config):
                    print(f"  Run {run+1}/{runs_per_config}...")
                    
                    # Run the scenario
                    run_metrics = self.scenario_runner.run_scenario(
                        scenario_file=os.path.join(project_root, "config", "scenarios", f"{scenario}.rou.xml"),
                        controller_type=controller_type,
                        steps=steps,
                        gui=gui,
                        collect_metrics=True,
                        model_path=model_path if controller_type in ["Wired RL", "Wireless RL"] else None
                    )
                    
                    # Store run results
                    controller_results["runs"].append(run_metrics)
                    
                    # Print run metrics
                    print(f"    Wait Time: {run_metrics['avg_waiting_time']:.2f}s")
                    print(f"    Speed: {run_metrics['avg_speed']:.2f}m/s")
                    print(f"    Throughput: {run_metrics['throughput']} vehicles")
                
                # Calculate average metrics across runs
                for metric in self.metrics:
                    values = [run.get(metric, 0) for run in controller_results["runs"]]
                    if values:
                        controller_results["avg_metrics"][metric] = sum(values) / len(values)
                
                # Store controller results
                scenario_results[controller_type] = controller_results
                
                # Print average metrics
                print(f"  Average metrics for {controller_type} on {scenario}:")
                for metric, value in controller_results["avg_metrics"].items():
                    print(f"    {metric}: {value:.4f}")
            
            # Store scenario results
            comparison_results["scenarios"][scenario] = scenario_results
        
        # Calculate summary metrics across all scenarios
        summary = {}
        for controller_type in valid_controllers:
            controller_summary = {metric: [] for metric in self.metrics}
            
            for scenario in scenarios:
                if scenario in comparison_results["scenarios"] and controller_type in comparison_results["scenarios"][scenario]:
                    for metric in self.metrics:
                        value = comparison_results["scenarios"][scenario][controller_type]["avg_metrics"].get(metric, 0)
                        controller_summary[metric].append(value)
            
            # Calculate average of averages
            summary[controller_type] = {
                metric: sum(values) / len(values) if values else 0
                for metric, values in controller_summary.items()
            }
        
        comparison_results["summary"] = summary
        
        # Save comparison results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = os.path.join(self.output_dir, f"comparison_results_{timestamp}.json")
        
        with open(results_file, 'w') as f:
            json.dump(comparison_results, f, indent=2)
        
        print(f"\nComparison results saved to: {results_file}")
        
        # Generate visualization
        self.visualize_comparison(comparison_results, timestamp)
        
        return comparison_results
    
    def visualize_comparison(self, results, timestamp=None):
        """
        Generate visualizations from comparison results.
        
        Args:
            results: Comparison results dictionary
            timestamp: Optional timestamp for file naming
        """
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract controllers and scenarios
        controllers = list(results["summary"].keys())
        scenarios = list(results["scenarios"].keys())
        
        if not controllers or not scenarios:
            print("No data to visualize.")
            return
        
        # Create directory for visualizations
        vis_dir = os.path.join(self.output_dir, "visualizations")
        os.makedirs(vis_dir, exist_ok=True)
        
        # 1. Summary comparison across all scenarios
        self._plot_summary_comparison(results, controllers, vis_dir, timestamp)
        
        # 2. Detailed comparison by scenario
        self._plot_scenario_comparison(results, controllers, scenarios, vis_dir, timestamp)
        
        # 3. Controller performance profile
        self._plot_controller_profiles(results, controllers, scenarios, vis_dir, timestamp)
    
    def _plot_summary_comparison(self, results, controllers, output_dir, timestamp):
        """Plot summary comparison across all scenarios."""
        # Set up the figure
        fig, axs = plt.subplots(len(self.metrics), 1, figsize=(12, 4 * len(self.metrics)))
        fig.suptitle('Summary Comparison Across All Scenarios', fontsize=16)
        
        # Colors for controllers
        colors = plt.cm.tab10(np.linspace(0, 1, len(controllers)))
        
        # Plot each metric
        for i, metric in enumerate(self.metrics):
            ax = axs[i] if len(self.metrics) > 1 else axs
            
            # Get values for each controller
            values = [results["summary"][controller].get(metric, 0) for controller in controllers]
            
            # Create bar chart
            bars = ax.bar(range(len(controllers)), values, color=colors)
            
            # Add values on top of bars
            for j, bar in enumerate(bars):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.02 * max(values),
                        f'{values[j]:.2f}', ha='center', va='bottom')
            
            # Set labels and title
            ax.set_xlabel('Controller Type')
            ax.set_ylabel(metric.replace('_', ' ').title())
            ax.set_title(f'Average {metric.replace("_", " ").title()} Across All Scenarios')
            ax.set_xticks(range(len(controllers)))
            ax.set_xticklabels(controllers, rotation=45, ha='right')
            ax.grid(True, axis='y', linestyle='--', alpha=0.7)
        
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        plt.savefig(os.path.join(output_dir, f'summary_comparison_{timestamp}.png'), dpi=300)
        plt.close()
    
    def _plot_scenario_comparison(self, results, controllers, scenarios, output_dir, timestamp):
        """Plot detailed comparison by scenario."""
        # For each metric, create a grouped bar chart comparing controllers across scenarios
        for metric in self.metrics:
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # Set up the plot
            bar_width = 0.15
            index = np.arange(len(scenarios))
            
            # Colors for controllers
            colors = plt.cm.tab10(np.linspace(0, 1, len(controllers)))
            
            # Plot bars for each controller
            for i, controller in enumerate(controllers):
                values = []
                for scenario in scenarios:
                    if scenario in results["scenarios"] and controller in results["scenarios"][scenario]:
                        values.append(results["scenarios"][scenario][controller]["avg_metrics"].get(metric, 0))
                    else:
                        values.append(0)
                
                # Create bars
                bars = ax.bar(index + i * bar_width, values, bar_width,
                             label=controller, color=colors[i])
                
                # Add values on top of bars
                for j, bar in enumerate(bars):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.02 * max(values),
                           f'{values[j]:.2f}', ha='center', va='bottom', fontsize=8)
            
            # Set labels and title
            ax.set_xlabel('Scenario')
            ax.set_ylabel(metric.replace('_', ' ').title())
            ax.set_title(f'Comparison of {metric.replace("_", " ").title()} Across Scenarios and Controllers')
            ax.set_xticks(index + bar_width * (len(controllers) - 1) / 2)
            ax.set_xticklabels([s.replace('_', ' ').title() for s in scenarios])
            ax.legend()
            ax.grid(True, axis='y', linestyle='--', alpha=0.7)
            
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f'{metric}_comparison_{timestamp}.png'), dpi=300)
            plt.close()
    
    def _plot_controller_profiles(self, results, controllers, scenarios, output_dir, timestamp):
        """Plot performance profile for each controller."""
        # For each controller, create a radar chart showing performance across metrics and scenarios
        metrics_for_radar = ['avg_waiting_time', 'avg_speed', 'throughput']
        
        for controller in controllers:
            # Create a figure with subplots for each scenario
            fig, axs = plt.subplots(1, len(scenarios), figsize=(5 * len(scenarios), 5), 
                                    subplot_kw=dict(polar=True))
            
            if len(scenarios) == 1:
                axs = [axs]
                
            fig.suptitle(f'Performance Profile: {controller}', fontsize=16)
            
            # Process each scenario
            for i, scenario in enumerate(scenarios):
                ax = axs[i]
                
                # Check if data exists
                if scenario not in results["scenarios"] or controller not in results["scenarios"][scenario]:
                    continue
                
                # Get data for this controller and scenario
                data = results["scenarios"][scenario][controller]["avg_metrics"]
                
                # Normalize the data for radar chart
                # For waiting time, lower is better, so invert the scale
                normalized_data = {
                    'avg_waiting_time': 1 - min(1, data.get('avg_waiting_time', 0) / 60),  # assume 60s is max
                    'avg_speed': min(1, data.get('avg_speed', 0) / 15),  # assume 15 m/s is max
                    'throughput': min(1, data.get('throughput', 0) / 500)  # assume 500 vehicles is max
                }
                
                # Plot the radar chart
                angles = np.linspace(0, 2*np.pi, len(metrics_for_radar), endpoint=False).tolist()
                values = [normalized_data[m] for m in metrics_for_radar]
                values += values[:1]  # close the loop
                angles += angles[:1]  # close the loop
                
                ax.plot(angles, values, 'o-', linewidth=2)
                ax.fill(angles, values, alpha=0.25)
                ax.set_thetagrids(np.degrees(angles[:-1]), metrics_for_radar)
                ax.set_ylim(0, 1)
                ax.set_title(scenario.replace('_', ' ').title())
                
                # Add raw values as text
                for j, metric in enumerate(metrics_for_radar):
                    angle = angles[j]
                    value = values[j]
                    raw_value = data.get(metric, 0)
                    ha = 'left' if np.sin(angle) > 0 else 'right'
                    va = 'bottom' if np.cos(angle) > 0 else 'top'
                    offset_x = 0.1 * np.sin(angle)
                    offset_y = 0.1 * np.cos(angle)
                    ax.text(angle, value + 0.05, f'{raw_value:.2f}', 
                           ha=ha, va=va, fontsize=8)
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            plt.savefig(os.path.join(output_dir, f'{controller}_profile_{timestamp}.png'), dpi=300)
            plt.close()

def main():
    """Run the comparison framework as a script."""
    parser = argparse.ArgumentParser(description='Run traffic controller comparison framework')
    parser.add_argument('--scenarios', type=str, nargs='+',
                        help='Specific scenarios to test')
    parser.add_argument('--controllers', type=str, nargs='+',
                        choices=["Traditional", "Wired AI", "Wireless AI", "Wired RL", "Wireless RL"],
                        help='Specific controller types to test')
    parser.add_argument('--steps', type=int, default=1000,
                        help='Number of simulation steps per run')
    parser.add_argument('--runs', type=int, default=3,
                        help='Number of runs per configuration')
    parser.add_argument('--gui', action='store_true',
                        help='Show SUMO GUI during simulation')
    parser.add_argument('--output', type=str, default=None,
                        help='Directory to save results')
    parser.add_argument('--summary-only', action='store_true',
                        help='Only show summary results, not detailed visualizations')
    args = parser.parse_args()
    
    # Initialize the comparison framework
    comparison = ComparisonFramework(output_dir=args.output)
    
    # Find RL model paths if available
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
    
    # Run the comparison
    results = comparison.run_comparison(
        scenarios=args.scenarios,
        controller_types=args.controllers,
        steps=args.steps,
        runs_per_config=args.runs,
        gui=args.gui,
        model_paths=model_paths
    )
    
    # Print summary only if requested
    if args.summary_only and results:
        print("\nOverall Performance Summary:")
        print("=" * 80)
        
        controllers = list(results["summary"].keys())
        for controller in controllers:
            print(f"\n{controller}:")
            for metric, value in results["summary"][controller].items():
                print(f"  {metric}: {value:.4f}")

if __name__ == "__main__":
    main()