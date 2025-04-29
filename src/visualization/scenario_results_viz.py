import os
import sys
import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

def plot_scenario_comparison(results_file):
    """
    Create comparison plots from scenario test results.
    
    Args:
        results_file: Path to the JSON file with test results
    """
    # Load results
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    if not results:
        print("No results found in the file.")
        return
    
    # Extract data for plotting
    scenarios = list(results.keys())
    controllers = list(results[scenarios[0]].keys())
    
    # Set up figure
    fig, axes = plt.subplots(3, 2, figsize=(15, 15))
    fig.suptitle('Traffic Controller Comparison Across Scenarios', fontsize=16)
    
    # Metrics to plot
    metrics = [
        ('avg_waiting_time', 'Average Waiting Time (s)'),
        ('avg_speed', 'Average Speed (m/s)'),
        ('throughput', 'Total Throughput (vehicles)'),
        ('avg_response_time', 'Average Response Time (ms)'),
        ('avg_decision_time', 'Average Decision Time (ms)')
    ]
    
    # Colors for controllers
    colors = ['blue', 'green', 'red']
    
    # Plot each metric in a separate subplot
    for i, (metric, title) in enumerate(metrics):
        ax = axes[i//2, i%2] if i < 4 else axes[2, 0]
        
        # Group data by scenario
        x = np.arange(len(scenarios))
        width = 0.25
        
        for j, controller in enumerate(controllers):
            values = [results[scenario][controller][metric] for scenario in scenarios]
            ax.bar(x + j*width - width, values, width, label=controller, color=colors[j])
        
        ax.set_xlabel('Scenario')
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace('_', ' ').title() for s in scenarios], rotation=45, ha='right')
        ax.legend()
        
        # Add value labels on top of bars
        for j, controller in enumerate(controllers):
            values = [results[scenario][controller][metric] for scenario in scenarios]
            for k, v in enumerate(values):
                ax.text(k + j*width - width, v, f'{v:.1f}', ha='center', va='bottom', fontsize=8)
    
    # Empty last subplot
    if len(metrics) < 6:
        axes[2, 1].axis('off')
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    # Save figure
    output_dir = os.path.join(project_root, "data", "outputs")
    output_file = os.path.join(output_dir, f"scenario_comparison_{os.path.basename(results_file).split('.')[0]}.png")
    plt.savefig(output_file, dpi=300)
    print(f"Comparison plot saved to {output_file}")
    
    # Show the figure
    plt.show()

def main():
    """Create visualizations of scenario test results."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Visualize traffic scenario test results')
    parser.add_argument('--results', type=str, required=True,
                        help='Path to the JSON file with test results')
    args = parser.parse_args()
    
    # Check if the results file exists
    if not os.path.exists(args.results):
        print(f"Results file {args.results} not found!")
        return
    
    # Plot the comparison
    plot_scenario_comparison(args.results)

if __name__ == "__main__":
    main()