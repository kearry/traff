import os
import sys
from pathlib import Path
import time
import subprocess
import matplotlib.pyplot as plt
import numpy as np

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def run_simulation(mode, steps=500, delay=50, gui=False):
    """Run a simulation with the specified mode and parameters"""
    cmd = [
        sys.executable,
        os.path.join(project_root, "src", "test_visualization.py"),
        "--mode", mode,
        "--steps", str(steps),
        "--delay", str(delay)
    ]
    
    if gui:
        cmd.append("--gui")
    
    print(f"Running {mode} simulation...")
    start_time = time.time()
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    
    elapsed_time = time.time() - start_time
    print(f"{mode} simulation completed in {elapsed_time:.2f} seconds")
    
    # Extract performance metrics from output
    metrics = {
        "avg_wait_time": 0,
        "avg_speed": 0,
        "throughput": 0
    }
    
    for line in stdout.split('\n'):
        if "Average wait time:" in line:
            metrics["avg_wait_time"] = float(line.split(':')[1].strip().split()[0])
        elif "Average speed:" in line:
            metrics["avg_speed"] = float(line.split(':')[1].strip().split()[0])
        elif "Total throughput:" in line:
            metrics["throughput"] = int(line.split(':')[1].strip().split()[0])
    
    return metrics

def plot_comparison(wired_metrics, wireless_metrics):
    """Plot a comparison of the wired and wireless simulation results"""
    # Create the data directory if it doesn't exist
    data_dir = os.path.join(project_root, "data", "outputs")
    os.makedirs(data_dir, exist_ok=True)
    
    # Set up the metrics for comparison
    metrics = ["avg_wait_time", "avg_speed", "throughput"]
    labels = ["Average Wait Time (s)", "Average Speed (m/s)", "Throughput (vehicles)"]
    
    # Create the figure
    fig, axs = plt.subplots(1, 3, figsize=(15, 5))
    
    for i, (metric, label) in enumerate(zip(metrics, labels)):
        wired_value = wired_metrics[metric]
        wireless_value = wireless_metrics[metric]
        
        # Plot the bars
        bars = axs[i].bar(["Wired AI", "Wireless AI"], [wired_value, wireless_value])
        bars[0].set_color('blue')
        bars[1].set_color('green')
        
        # Add labels and title
        axs[i].set_ylabel(label)
        axs[i].set_title(f"Comparison of {label}")
        
        # Add the values on top of the bars
        for j, v in enumerate([wired_value, wireless_value]):
            axs[i].text(j, v, f"{v:.2f}", ha='center', va='bottom')
    
    # Adjust layout and save
    plt.tight_layout()
    plt.savefig(os.path.join(data_dir, "comparison_results.png"))
    plt.close()
    
    print(f"Comparison plot saved to {os.path.join(data_dir, 'comparison_results.png')}")

def main():
    # Run the simulations
    wired_metrics = run_simulation("Wired AI", steps=300, delay=20)
    wireless_metrics = run_simulation("Wireless AI", steps=300, delay=20)
    
    # Print the results
    print("\nResults Summary:")
    print("==================")
    print(f"Wired AI - Wait Time: {wired_metrics['avg_wait_time']:.2f}s, "
          f"Speed: {wired_metrics['avg_speed']:.2f}m/s, "
          f"Throughput: {wired_metrics['throughput']}")
    print(f"Wireless AI - Wait Time: {wireless_metrics['avg_wait_time']:.2f}s, "
          f"Speed: {wireless_metrics['avg_speed']:.2f}m/s, "
          f"Throughput: {wireless_metrics['throughput']}")
    
    # Plot the comparison
    plot_comparison(wired_metrics, wireless_metrics)

if __name__ == "__main__":
    main()