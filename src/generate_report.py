import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def load_results(results_file):
    """Load comparison results from a JSON file."""
    with open(results_file, 'r') as f:
        return json.load(f)

def generate_report(results, output_file=None):
    """
    Generate a comprehensive report from comparison results.
    
    Args:
        results: Comparison results dictionary
        output_file: Path to save the report
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(project_root, "data", "outputs", f"comparison_report_{timestamp}.md")
    
    # Create the report directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Extract basic info
    timestamp = results.get("timestamp", "Unknown")
    controllers = list(results["summary"].keys())
    scenarios = list(results["scenarios"].keys())
    metrics = ["avg_waiting_time", "avg_speed", "throughput", "avg_response_time", "avg_decision_time"]
    
    # Start generating the report
    report = []
    
    # Title
    report.append("# Traffic Control System Comparison Report")
    report.append(f"*Generated on: {timestamp}*\n")
    
    # Introduction
    report.append("## Introduction")
    report.append("This report presents a comparative analysis of different traffic control systems, evaluating their performance across various traffic scenarios. The comparison focuses on the effectiveness of AI-based controllers in both wired and wireless configurations, relative to traditional control methods.\n")
    
    # Summary of Controllers
    report.append("## Controllers Evaluated")
    for controller in controllers:
        if controller == "Traditional":
            report.append(f"- **{controller}**: Fixed-timing traffic light controller using predetermined phase sequences and durations.")
        elif controller == "Wired AI":
            report.append(f"- **{controller}**: AI-based controller operating over a simulated wired network with fixed latency.")
        elif controller == "Wireless AI":
            report.append(f"- **{controller}**: AI-based controller operating over a simulated wireless network with variable latency and potential packet loss.")
        elif controller == "Wired RL":
            report.append(f"- **{controller}**: Reinforcement learning controller operating over a simulated wired network.")
        elif controller == "Wireless RL":
            report.append(f"- **{controller}**: Reinforcement learning controller operating over a simulated wireless network with variable latency and potential packet loss.")
    report.append("")
    
    # Scenarios Tested
    report.append("## Scenarios Tested")
    for scenario in scenarios:
        report.append(f"- **{scenario.replace('_', ' ').title()}**: Traffic conditions simulating {scenario.replace('_', ' ')}.")
    report.append("")
    
    # Performance Metrics
    report.append("## Performance Metrics")
    report.append("- **Average Waiting Time (s)**: Average time vehicles spend waiting at intersections. Lower values indicate better traffic flow.")
    report.append("- **Average Speed (m/s)**: Average speed of vehicles in the network. Higher values indicate better traffic flow.")
    report.append("- **Throughput (vehicles)**: Number of vehicles that successfully completed their routes. Higher values indicate better system capacity.")
    report.append("- **Average Response Time (ms)**: Time taken for the controller to respond to traffic conditions. Lower values indicate better responsiveness.")
    report.append("- **Average Decision Time (ms)**: Time taken for the controller to make a decision. Lower values indicate more efficient computation.\n")
    
    # Overall Performance Summary
    report.append("## Overall Performance Summary")
    report.append("The following table summarizes the overall performance of each controller across all scenarios:\n")
    
    # Create summary table
    report.append("| Controller | Avg Waiting Time (s) | Avg Speed (m/s) | Throughput | Avg Response Time (ms) | Avg Decision Time (ms) |")
    report.append("|------------|---------------------|-----------------|------------|------------------------|------------------------|")
    
    for controller in controllers:
        summary = results["summary"][controller]
        report.append(f"| {controller} | {summary['avg_waiting_time']:.2f} | {summary['avg_speed']:.2f} | {int(summary['throughput'])} | {summary['avg_response_time']:.2f} | {summary['avg_decision_time']:.2f} |")
    report.append("")
    
    # Performance by Scenario
    report.append("## Performance by Scenario")
    
    for scenario in scenarios:
        report.append(f"### {scenario.replace('_', ' ').title()}")
        report.append("| Controller | Avg Waiting Time (s) | Avg Speed (m/s) | Throughput | Avg Response Time (ms) | Avg Decision Time (ms) |")
        report.append("|------------|---------------------|-----------------|------------|------------------------|------------------------|")
        
        for controller in controllers:
            if controller in results["scenarios"][scenario]:
                metrics_data = results["scenarios"][scenario][controller]["avg_metrics"]
                report.append(f"| {controller} | {metrics_data['avg_waiting_time']:.2f} | {metrics_data['avg_speed']:.2f} | {int(metrics_data['throughput'])} | {metrics_data['avg_response_time']:.2f} | {metrics_data['avg_decision_time']:.2f} |")
        report.append("")
    
    # Key Findings
    report.append("## Key Findings")
    
    # 1. Wired vs Wireless Comparison
    if "Wired AI" in controllers and "Wireless AI" in controllers:
        report.append("### Wired vs. Wireless AI Comparison")
        
        wired_summary = results["summary"]["Wired AI"]
        wireless_summary = results["summary"]["Wireless AI"]
        
        # Calculate percentage differences
        wait_diff_pct = (wired_summary["avg_waiting_time"] - wireless_summary["avg_waiting_time"]) / wired_summary["avg_waiting_time"] * 100
        speed_diff_pct = (wireless_summary["avg_speed"] - wired_summary["avg_speed"]) / wired_summary["avg_speed"] * 100
        throughput_diff_pct = (wireless_summary["throughput"] - wired_summary["throughput"]) / wired_summary["throughput"] * 100
        
        # Determine which is better overall
        metrics_better = [
            wait_diff_pct > 0,  # Wireless better if waiting time is lower
            speed_diff_pct > 0,  # Wireless better if speed is higher
            throughput_diff_pct > 0  # Wireless better if throughput is higher
        ]
        
        wireless_better_count = sum(metrics_better)
        wired_better_count = len(metrics_better) - wireless_better_count
        
        if wireless_better_count > wired_better_count:
            overall_better = "wireless"
        elif wired_better_count > wireless_better_count:
            overall_better = "wired"
        else:
            overall_better = "neither"
        
        # Write findings
        report.append(f"Overall, the **{overall_better}** AI controller performed better across the tested scenarios.")
        report.append("")
        report.append("Performance differences:")
        report.append(f"- **Waiting Time**: {'Wireless' if wait_diff_pct > 0 else 'Wired'} AI performed better by {abs(wait_diff_pct):.1f}%")
        report.append(f"- **Average Speed**: {'Wireless' if speed_diff_pct > 0 else 'Wired'} AI performed better by {abs(speed_diff_pct):.1f}%")
        report.append(f"- **Throughput**: {'Wireless' if throughput_diff_pct > 0 else 'Wired'} AI performed better by {abs(throughput_diff_pct):.1f}%")
        report.append("")
        
        # Response and decision time comparison
        report.append("Network characteristics comparison:")
        report.append(f"- **Response Time**: Wired AI: {wired_summary['avg_response_time']:.2f}ms, Wireless AI: {wireless_summary['avg_response_time']:.2f}ms")
        report.append(f"- **Decision Time**: Wired AI: {wired_summary['avg_decision_time']:.2f}ms, Wireless AI: {wireless_summary['avg_decision_time']:.2f}ms")
        report.append("")
    
    # 2. Traditional vs. AI Comparison
    if "Traditional" in controllers and ("Wired AI" in controllers or "Wireless AI" in controllers):
        report.append("### Traditional vs. AI-based Controllers")
        
        trad_summary = results["summary"]["Traditional"]
        ai_controllers = [c for c in controllers if "AI" in c and "RL" not in c]
        
        # Calculate averages for AI controllers
        ai_wait = sum(results["summary"][c]["avg_waiting_time"] for c in ai_controllers) / len(ai_controllers)
        ai_speed = sum(results["summary"][c]["avg_speed"] for c in ai_controllers) / len(ai_controllers)
        ai_throughput = sum(results["summary"][c]["throughput"] for c in ai_controllers) / len(ai_controllers)
        
        # Calculate percentage differences
        wait_diff_pct = (trad_summary["avg_waiting_time"] - ai_wait) / trad_summary["avg_waiting_time"] * 100
        speed_diff_pct = (ai_speed - trad_summary["avg_speed"]) / trad_summary["avg_speed"] * 100
        throughput_diff_pct = (ai_throughput - trad_summary["throughput"]) / trad_summary["throughput"] * 100
        
        # Determine which is better overall
        metrics_better = [
            wait_diff_pct > 0,  # AI better if waiting time is lower
            speed_diff_pct > 0,  # AI better if speed is higher
            throughput_diff_pct > 0  # AI better if throughput is higher
        ]
        
        ai_better_count = sum(metrics_better)
        trad_better_count = len(metrics_better) - ai_better_count
        
        if ai_better_count > trad_better_count:
            overall_better = "AI-based"
        elif trad_better_count > ai_better_count:
            overall_better = "traditional"
        else:
            overall_better = "neither"
        
        # Write findings
        report.append(f"Overall, the **{overall_better}** controller performed better across the tested scenarios.")
        report.append("")
        report.append("Performance differences:")
        report.append(f"- **Waiting Time**: {'AI-based' if wait_diff_pct > 0 else 'Traditional'} controllers performed better by {abs(wait_diff_pct):.1f}%")
        report.append(f"- **Average Speed**: {'AI-based' if speed_diff_pct > 0 else 'Traditional'} controllers performed better by {abs(speed_diff_pct):.1f}%")
        report.append(f"- **Throughput**: {'AI-based' if throughput_diff_pct > 0 else 'Traditional'} controllers performed better by {abs(throughput_diff_pct):.1f}%")
        report.append("")
    
    # 3. RL vs. Basic AI Comparison
    ai_controllers = [c for c in controllers if "AI" in c and "RL" not in c]
    rl_controllers = [c for c in controllers if "RL" in c]
    
    if ai_controllers and rl_controllers:
        report.append("### Reinforcement Learning vs. Basic AI Controllers")
        
        # Calculate averages
        ai_wait = sum(results["summary"][c]["avg_waiting_time"] for c in ai_controllers) / len(ai_controllers)
        ai_speed = sum(results["summary"][c]["avg_speed"] for c in ai_controllers) / len(ai_controllers)
        ai_throughput = sum(results["summary"][c]["throughput"] for c in ai_controllers) / len(ai_controllers)
        
        rl_wait = sum(results["summary"][c]["avg_waiting_time"] for c in rl_controllers) / len(rl_controllers)
        rl_speed = sum(results["summary"][c]["avg_speed"] for c in rl_controllers) / len(rl_controllers)
        rl_throughput = sum(results["summary"][c]["throughput"] for c in rl_controllers) / len(rl_controllers)
        
        # Calculate percentage differences
        wait_diff_pct = (ai_wait - rl_wait) / ai_wait * 100
        speed_diff_pct = (rl_speed - ai_speed) / ai_speed * 100
        throughput_diff_pct = (rl_throughput - ai_throughput) / ai_throughput * 100
        
        # Determine which is better overall
        metrics_better = [
            wait_diff_pct > 0,  # RL better if waiting time is lower
            speed_diff_pct > 0,  # RL better if speed is higher
            throughput_diff_pct > 0  # RL better if throughput is higher
        ]
        
        rl_better_count = sum(metrics_better)
        ai_better_count = len(metrics_better) - rl_better_count
        
        if rl_better_count > ai_better_count:
            overall_better = "reinforcement learning"
        elif ai_better_count > rl_better_count:
            overall_better = "basic AI"
        else:
            overall_better = "neither"
        
        # Write findings
        report.append(f"Overall, the **{overall_better}** controller performed better across the tested scenarios.")
        report.append("")
        report.append("Performance differences:")
        report.append(f"- **Waiting Time**: {'Reinforcement Learning' if wait_diff_pct > 0 else 'Basic AI'} controllers performed better by {abs(wait_diff_pct):.1f}%")
        report.append(f"- **Average Speed**: {'Reinforcement Learning' if speed_diff_pct > 0 else 'Basic AI'} controllers performed better by {abs(speed_diff_pct):.1f}%")
        report.append(f"- **Throughput**: {'Reinforcement Learning' if throughput_diff_pct > 0 else 'Basic AI'} controllers performed better by {abs(throughput_diff_pct):.1f}%")
        report.append("")
    
    # Scenario-specific observations
    report.append("### Scenario-specific Observations")
    
    for scenario in scenarios:
        report.append(f"#### {scenario.replace('_', ' ').title()}")
        
        # Find best controller for this scenario based on waiting time
        best_controller = None
        best_wait_time = float('inf')
        
        for controller in controllers:
            if controller in results["scenarios"][scenario]:
                wait_time = results["scenarios"][scenario][controller]["avg_metrics"].get("avg_waiting_time", float('inf'))
                if wait_time < best_wait_time:
                    best_wait_time = wait_time
                    best_controller = controller
        
        report.append(f"- Best performing controller: **{best_controller}** (Avg. waiting time: {best_wait_time:.2f}s)")
        
        # Add more scenario-specific observations
        # For example, compare wireless vs. wired in this scenario if both exist
        if "Wired AI" in results["scenarios"][scenario] and "Wireless AI" in results["scenarios"][scenario]:
            wired_wait = results["scenarios"][scenario]["Wired AI"]["avg_metrics"]["avg_waiting_time"]
            wireless_wait = results["scenarios"][scenario]["Wireless AI"]["avg_metrics"]["avg_waiting_time"]
            
            if wired_wait < wireless_wait:
                report.append(f"- In this scenario, wired communication performed {(wireless_wait/wired_wait - 1)*100:.1f}% better than wireless in terms of waiting time.")
            else:
                report.append(f"- In this scenario, wireless communication performed {(wired_wait/wireless_wait - 1)*100:.1f}% better than wired in terms of waiting time.")
        
        report.append("")
    
    # Conclusions
    report.append("## Conclusions")
    report.append("Based on the comprehensive comparison of different traffic control systems across various scenarios, the following conclusions can be drawn:")
    
    # Determine overall best controller
    best_controller = None
    best_wait_time = float('inf')
    
    for controller in controllers:
        wait_time = results["summary"][controller].get("avg_waiting_time", float('inf'))
        if wait_time < best_wait_time:
            best_wait_time = wait_time
            best_controller = controller
    
    report.append(f"1. **{best_controller}** showed the best overall performance across all scenarios, with the lowest average waiting time ({best_wait_time:.2f}s).")
    
    # Add conclusion about wireless vs. wired if both exist
    if "Wired AI" in controllers and "Wireless AI" in controllers:
        wired_wait = results["summary"]["Wired AI"]["avg_waiting_time"]
        wireless_wait = results["summary"]["Wireless AI"]["avg_waiting_time"]
        
        if abs(wired_wait - wireless_wait) / min(wired_wait, wireless_wait) < 0.1:  # Less than 10% difference
            report.append("2. Wireless AI control systems performed comparably to wired systems, suggesting that wireless communication is a viable alternative for traffic control despite potential network limitations.")
        elif wired_wait < wireless_wait:
            report.append(f"2. Wired AI control systems outperformed wireless systems by {(wireless_wait/wired_wait - 1)*100:.1f}% in terms of waiting time, indicating that network reliability remains an important factor in traffic control efficiency.")
        else:
            report.append(f"2. Wireless AI control systems outperformed wired systems by {(wired_wait/wireless_wait - 1)*100:.1f}% in terms of waiting time, suggesting that the adaptability of wireless systems can overcome their network limitations.")
    
    # Add conclusion about AI vs. traditional if both exist
    if "Traditional" in controllers and any(c for c in controllers if "AI" in c):
        trad_wait = results["summary"]["Traditional"]["avg_waiting_time"]
        ai_controllers = [c for c in controllers if "AI" in c or "RL" in c]
        ai_wait = sum(results["summary"][c]["avg_waiting_time"] for c in ai_controllers) / len(ai_controllers)
        
        if ai_wait < trad_wait:
            report.append(f"3. AI-based controllers demonstrated superior performance compared to traditional fixed-timing controllers, reducing average waiting time by {(1 - ai_wait/trad_wait)*100:.1f}%.")
        else:
            report.append(f"3. Traditional fixed-timing controllers still performed well compared to AI-based solutions, highlighting the effectiveness of well-tuned conventional systems.")
    
    # Add final dissertation-relevant conclusion
    report.append("4. The comparison results provide valuable insights into the question of whether AI can effectively control traffic systems wirelessly, and how this approach compares to traditional wired systems.")
    report.append("")
    
    # Write the report to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(report))
    
    print(f"Report generated and saved to: {output_file}")
    return output_file

def main():
    """Run the report generation as a script."""
    parser = argparse.ArgumentParser(description='Generate comprehensive report from comparison results')
    parser.add_argument('--results', type=str, required=True,
                        help='Path to the comparison results JSON file')
    parser.add_argument('--output', type=str, default=None,
                        help='Path to save the generated report')
    args = parser.parse_args()
    
    # Check if results file exists
    if not os.path.exists(args.results):
        print(f"Error: Results file not found: {args.results}")
        return
    
    # Load results
    results = load_results(args.results)
    
    # Generate report
    report_file = generate_report(results, args.output)

if __name__ == "__main__":
    main()