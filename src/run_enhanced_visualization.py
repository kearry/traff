# src/run_enhanced_visualization.py
import os
import sys
import argparse
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.ui.enhanced_traffic_visualizer import run_enhanced_visualization

def main():
    """Run the enhanced visualization with command line arguments."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run enhanced traffic visualization')
    parser.add_argument('--scenario', type=str, default=None,
                        help='Scenario file to run (without .rou.xml extension)')
    parser.add_argument('--controller', type=str, default="Wired AI",
                        choices=["Wired AI", "Wireless AI", "Traditional"],
                        help='Controller type to use')
    parser.add_argument('--steps', type=int, default=1000,
                        help='Number of simulation steps to run')
    parser.add_argument('--delay', type=int, default=50,
                        help='Delay in milliseconds between steps')
    args = parser.parse_args()
    
    # Define path to scenario directory
    scenarios_dir = os.path.join(project_root, "config", "scenarios")
    
    # Determine which configuration file to use
    if args.scenario:
        # First check if a temp config file for this scenario already exists
        temp_config = os.path.join(scenarios_dir, f"temp_{args.scenario}.sumocfg")
        if os.path.exists(temp_config):
            config_path = temp_config
        else:
            # Otherwise, check for the scenario .rou.xml file
            route_file = os.path.join(scenarios_dir, f"{args.scenario}.rou.xml")
            if os.path.exists(route_file):
                # Create a temporary config file
                config_path = create_temp_config(route_file)
            else:
                print(f"Scenario file not found: {route_file}")
                print(f"Available scenarios:")
                route_files = [f[:-8] for f in os.listdir(scenarios_dir) if f.endswith('.rou.xml')]
                for scenario in route_files:
                    print(f"  - {scenario}")
                return
    else:
        # Use the default configuration
        config_path = os.path.join(project_root, "config", "maps", "traffic_grid.sumocfg")
    
    print(f"Using configuration file: {config_path}")
    
    # Run the visualization
    run_enhanced_visualization(config_path, args.controller, args.steps, args.delay)

def create_temp_config(route_file):
    """
    Create a temporary SUMO configuration file.
    
    Args:
        route_file: Path to the route file
        
    Returns:
        Path to the created config file
    """
    # Get base name without extension
    base_name = os.path.basename(route_file).split('.')[0]
    
    # Network file
    network_file = os.path.join(project_root, "config", "maps", "traffic_grid.net.xml")
    
    # Create a unique config file name
    config_name = f"temp_{base_name}.sumocfg"
    config_path = os.path.join(project_root, "config", "scenarios", config_name)
    
    # Write the config file
    with open(config_path, 'w') as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    <input>
        <net-file value="{network_file}"/>
        <route-files value="{route_file}"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
        <step-length value="1.0"/>
    </time>
    <processing>
        <time-to-teleport value="-1"/>
    </processing>
    <report>
        <verbose value="false"/>
        <no-step-log value="true"/>
    </report>
</configuration>""")
    
    print(f"Generated temporary SUMO config file: {config_path}")
    return config_path

if __name__ == "__main__":
    main()