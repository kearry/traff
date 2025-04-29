import os
import sys
import json
import argparse
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

def load_results(results_file):
    """Load comparison results from a JSON file."""
    with open(results_file, 'r') as f:
        return json.load(f)

def plot_comparative_analysis(results, output_dir=None):
    """Generate comparative analysis visualizations."""
    if output_dir is None:
        output_dir = os.path.join(project_root, "data", "outputs", "visualizations")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract controllers and scenarios
    controllers = list(results["summary"].keys())
    scenarios = list(results["scenarios"].keys())
    metrics = ["avg_waiting_time", "avg_speed", "throughput", "avg_response_time", "avg_decision_time"]
    
    # Create a figure showing the relative performance of controllers
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Normalize data for comparison
    # Lower waiting time is better, higher speed and throughput are better
    normalized_data = {}
    
    for controller in controllers:
        normalized_data[controller] = {
            "avg_waiting_time": 0,
            "avg_speed": 0,
            "throughput": 0
        }
    
    # Find max values for normalization
    max_wait = max(results["summary"][c]["avg_waiting_time"] for c in controllers)
    max_speed = max(results["summary"][c]["avg_speed"] for c in controllers)
    max_throughput = max(results["summary"][c]["throughput"] for c in controllers)
    
    # Calculate normalized values (0-1 scale)
    for controller in controllers:
        summary = results["summary"][controller]
        # For waiting time, lower is better, so invert
        normalized_data[controller]["avg_waiting_time"] = 1 - (summary["avg_waiting_time"] / max_wait) if max_wait > 0 else 0
        normalized_data[controller]["avg_speed"] = summary["avg_speed"] / max_speed if max_speed > 0 else 0
        normalized_data[controller]["throughput"] = summary["throughput"] / max_throughput if max_throughput > 0 else 0
    
    # Calculate overall performance score (simple average across normalized metrics)
    for controller in controllers:
        data = normalized_data[controller]
        data["overall_score"] = (data["avg_waiting_time"] + data["avg_speed"] + data["throughput"]) / 3
    
    # Sort controllers by overall score
    sorted_controllers = sorted(controllers, key=lambda c: normalized_data[c]["overall_score"], reverse=True)
    
    # Plot overall performance scores
    y_pos = np.arange(len(sorted_controllers))
    overall_scores = [normalized_data[c]["overall_score"] for c in sorted_controllers]
    
    bars = ax.barh(y_pos, overall_scores, align='center')
    
    # Color bars differently for different controller types
    colors = {
        "Traditional": "gray",
        "Wired AI": "blue",
        "Wireless AI": "green",
        "Wired RL": "purple",
        "Wireless RL": "orange"
    }
    
    for i, controller in enumerate(sorted_controllers):
        bars[i].set_color(colors.get(controller, "blue"))
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sorted_controllers)
    ax.invert_yaxis()  # labels read top-to-bottom
    ax.set_xlabel('Overall Performance Score (higher is better)')
    ax.set_title('Controller Performance Comparison')
    
    # Add raw metric values as text
    for i, controller in enumerate(sorted_controllers):
        summary = results["summary"][controller]
        ax.text(normalized_data[controller]["overall_score"] + 0.01, i, 
               f"Wait: {summary['avg_waiting_time']:.2f}s, Speed: {summary['avg_speed']:.2f}m/s, Throughput: {int(summary['throughput'])}")
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "overall_performance_comparison.png"), dpi=300)
    
    # Generate scenario-specific comparisons
    for scenario in scenarios:
        # Create radar chart comparing controllers on this scenario
        plot_radar_comparison(results, scenario, controllers, output_dir)
        
        # Create metric-specific bar charts
        for metric in metrics:
            plot_metric_comparison(results, scenario, controllers, metric, output_dir)
    
    # Create wireless vs. wired comparison chart
    if "Wired AI" in controllers and "Wireless AI" in controllers:
        plot_wired_vs_wireless(results, scenarios, output_dir)
    
    # If RL controllers are included, create comparison with traditional approaches
    rl_controllers = [c for c in controllers if "RL" in c]
    traditional_controllers = [c for c in controllers if "RL" not in c]
    
    if rl_controllers and traditional_controllers:
        plot_rl_vs_traditional(results, scenarios, rl_controllers, traditional_controllers, output_dir)
    
    return output_dir

def plot_radar_comparison(results, scenario, controllers, output_dir):
    """Create radar chart comparing controllers on a specific scenario."""
    # Metrics for radar chart (use normalized values)
    metrics = ["avg_waiting_time", "avg_speed", "throughput"]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(polar=True))
    
    # Find max values for normalization
    max_values = {}
    for metric in metrics:
        values = []
        for controller in controllers:
            if controller in results["scenarios"][scenario]:
                values.append(results["scenarios"][scenario][controller]["avg_metrics"].get(metric, 0))
        max_values[metric] = max(values) if values else 1
    
    # Calculate angles for radar chart
    angles = np.linspace(0, 2*np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]  # close the loop
    
    # Set colors for controllers
    colors = plt.cm.tab10(np.linspace(0, 1, len(controllers)))
    
    # Plot each controller
    for i, controller in enumerate(controllers):
        if controller not in results["scenarios"][scenario]:
            continue
        
        controller_data = results["scenarios"][scenario][controller]["avg_metrics"]
        
        # Normalize data
        values = []
        for metric in metrics:
            # For waiting time, lower is better, so invert
            if metric == "avg_waiting_time":
                if max_values[metric] > 0:
                    value = 1 - (controller_data.get(metric, 0) / max_values[metric])
                else:
                    value = 1
            else:
                if max_values[metric] > 0:
                    value = controller_data.get(metric, 0) / max_values[metric]
                else:
                    value = 0
            values.append(value)
        
        # Close the loop
        values += values[:1]
        
        # Plot radar chart
        ax.plot(angles, values, 'o-', linewidth=2, label=controller, color=colors[i])
        ax.fill(angles, values, alpha=0.1, color=colors[i])
    
    # Set radar chart labels
    ax.set_thetagrids(np.degrees(angles[:-1]), metrics)
    ax.set_ylim(0, 1)
    ax.set_title(f"Controller Comparison: {scenario.replace('_', ' ').title()}")
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"radar_comparison_{scenario}.png"), dpi=300)
    plt.close()

def plot_metric_comparison(results, scenario, controllers, metric, output_dir):
    """Create bar chart comparing controllers on a specific metric and scenario."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Get values for each controller
    values = []
    controller_list = []
    
    for controller in controllers:
        if controller in results["scenarios"][scenario]:
            controller_list.append(controller)
            values.append(results["scenarios"][scenario][controller]["avg_metrics"].get(metric, 0))
    
    # Set colors for controllers
    colors = {
        "Traditional": "gray",
        "Wired AI": "blue",
        "Wireless AI": "green",
        "Wired RL": "purple",
        "Wireless RL": "orange"
    }
    bar_colors = [colors.get(c, "blue") for c in controller_list]
    
    # Create bar chart
    bars = ax.bar(controller_list, values, color=bar_colors)
    
    # Add values on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.02 * max(values),
               f'{height:.2f}', ha='center', va='bottom')
    
    # Set labels and title
    metric_name = metric.replace('_', ' ').title()
    ax.set_xlabel('Controller Type')
    ax.set_ylabel(metric_name)
    ax.set_title(f'{metric_name} Comparison: {scenario.replace("_", " ").title()}')
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{metric}_{scenario}_comparison.png"), dpi=300)
    plt.close()

def plot_wired_vs_wireless(results, scenarios, output_dir):
    """Create chart comparing wired vs. wireless AI approaches."""
    # Metrics to compare
    metrics = ["avg_waiting_time", "avg_speed", "throughput", "avg_response_time", "avg_decision_time"]
    
    # Create figure with subplots for each metric
    fig, axs = plt.subplots(len(metrics), 1, figsize=(12, 4 * len(metrics)))
    fig.suptitle('Wired AI vs. Wireless AI Comparison', fontsize=16)
    
    # Process each metric
    for i, metric in enumerate(metrics):
        ax = axs[i]
        
        # Set up X-axis for scenarios
        x = np.arange(len(scenarios))
        width = 0.35
        
        # Get values for wired and wireless
        wired_values = []
        wireless_values = []
        
        for scenario in scenarios:
            if "Wired AI" in results["scenarios"][scenario]:
                wired_values.append(results["scenarios"][scenario]["Wired AI"]["avg_metrics"].get(metric, 0))
            else:
                wired_values.append(0)
                
            if "Wireless AI" in results["scenarios"][scenario]:
                wireless_values.append(results["scenarios"][scenario]["Wireless AI"]["avg_metrics"].get(metric, 0))
            else:
                wireless_values.append(0)
        
        # Plot bars
        bars1 = ax.bar(x - width/2, wired_values, width, label='Wired AI', color='blue')
        bars2 = ax.bar(x + width/2, wireless_values, width, label='Wireless AI', color='green')
        
        # Add percentage difference text
        for j in range(len(scenarios)):
            if wired_values[j] > 0 and wireless_values[j] > 0:
                if metric == "avg_waiting_time":
                    # For waiting time, lower is better
                    pct_diff = (wired_values[j] - wireless_values[j]) / wired_values[j] * 100
                    better = "Wireless better" if pct_diff > 0 else "Wired better"
                else:
                    # For other metrics, higher is better
                    pct_diff = (wireless_values[j] - wired_values[j]) / wired_values[j] * 100
                    better = "Wireless better" if pct_diff > 0 else "Wired better"
                
                ax.text(j, max(wired_values[j], wireless_values[j]) * 1.05,
                       f"{abs(pct_diff):.1f}% ({better})", ha='center', fontsize=8)
        
        # Add value labels on bars
        for bar in bars1:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height * 0.5,
                   f'{height:.2f}', ha='center', va='bottom', color='white', fontsize=8)
        
        for bar in bars2:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height * 0.5,
                   f'{height:.2f}', ha='center', va='bottom', color='white', fontsize=8)
        
        # Set labels and title
        ax.set_xlabel('Scenario')
        ax.set_ylabel(metric.replace('_', ' ').title())
        ax.set_title(f'{metric.replace("_", " ").title()} Comparison')
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace('_', ' ').title() for s in scenarios])
        ax.legend()
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(os.path.join(output_dir, "wired_vs_wireless_comparison.png"), dpi=300)
    plt.close()

def plot_rl_vs_traditional(results, scenarios, rl_controllers, traditional_controllers, output_dir):
    """Create chart comparing RL vs traditional approaches."""
    # Metrics to compare
    metrics = ["avg_waiting_time", "avg_speed", "throughput"]
    
    # Create figure with subplots for each metric
    fig, axs = plt.subplots(len(metrics), 1, figsize=(14, 4 * len(metrics)))
    fig.suptitle('RL vs. Traditional Controllers Comparison', fontsize=16)
    
    # Process each metric
    for i, metric in enumerate(metrics):
        ax = axs[i]
        
        # Set up X-axis for scenarios
        x = np.arange(len(scenarios))
        width = 0.8 / (len(rl_controllers) + len(traditional_controllers))
        
        # Plot bars for all controllers
        all_controllers = traditional_controllers + rl_controllers
        
        for j, controller in enumerate(all_controllers):
            values = []
            
            for scenario in scenarios:
                if controller in results["scenarios"][scenario]:
                    values.append(results["scenarios"][scenario][controller]["avg_metrics"].get(metric, 0))
                else:
                    values.append(0)
            
            # Select color based on controller type
            color = 'blue' if controller in traditional_controllers else 'purple'
            if controller == "Wireless AI":
                color = 'green'
            elif controller == "Wireless RL":
                color = 'orange'
            
            # Adjust bar position
            bar_pos = x + (j - len(all_controllers)/2 + 0.5) * width
            
            # Plot bars
            bars = ax.bar(bar_pos, values, width, label=controller, color=color)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height * 0.5,
                       f'{height:.2f}', ha='center', va='bottom', color='white', fontsize=8)
        
        # Set labels and title
        ax.set_xlabel('Scenario')
        ax.set_ylabel(metric.replace('_', ' ').title())
        ax.set_title(f'{metric.replace("_", " ").title()} Comparison')
        ax.set_xticks(x)
        ax.set_xticklabels([s.replace('_', ' ').title() for s in scenarios], rotation=45, ha='right')
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=len(all_controllers))
        ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(os.path.join(output_dir, "rl_vs_traditional_comparison.png"), dpi=300)
    plt.close()

def main():
    """Run the comparison visualization as a script."""
    parser = argparse.ArgumentParser(description='Visualize traffic controller comparison results')
    parser.add_argument('--results', type=str, required=True,
                        help='Path to the comparison results JSON file')
    parser.add_argument('--output', type=str, default=None,
                        help='Directory to save visualization outputs')
    args = parser.parse_args()
    
    # Check if results file exists
    if not os.path.exists(args.results):
        print(f"Error: Results file not found: {args.results}")
        return
    
    # Load results
    results = load_results(args.results)
    
    # Generate visualizations
    output_dir = plot_comparative_analysis(results, args.output)
    
    print(f"Visualizations saved to: {output_dir}")

if __name__ == "__main__":
    main()  