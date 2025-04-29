import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# Make sure lxml is installed
try:
    from lxml import etree
    print("lxml is installed and imported successfully.")
except ImportError:
    print("ERROR: lxml is not installed. Please install it using 'pip install lxml'")
    sys.exit(1)

from src.simulation.traffic_generator import TrafficGenerator

def main():
    """Generate a set of traffic scenarios for testing."""
    print("Starting traffic scenario generation...")
    
    # Create template file first if it doesn't exist
    template_file_path = os.path.join(project_root, "config", "scenarios", "scenario_template.rou.xml")
    
    if not os.path.exists(os.path.dirname(template_file_path)):
        print(f"Creating directory: {os.path.dirname(template_file_path)}")
        os.makedirs(os.path.dirname(template_file_path), exist_ok=True)
    
    if not os.path.exists(template_file_path):
        print(f"Template file not found, creating it: {template_file_path}")
        create_template_file(template_file_path)
    else:
        print(f"Template file exists at: {template_file_path}")
    
    # Initialize the traffic generator
    print("Initializing TrafficGenerator...")
    generator = TrafficGenerator(template_file_path)
    
    # 1. Light Traffic Scenario
    print("Generating light traffic scenario...")
    light_flows = {
        "route_north_south": 300,
        "route_south_north": 300,
        "route_east_west": 200,
        "route_west_east": 200,
        "route_clockwise": 100,
        "route_counterclockwise": 100
    }
    generator.generate_constant_traffic("light_traffic.rou.xml", light_flows)
    
    # 2. Moderate Traffic Scenario
    print("Generating moderate traffic scenario...")
    moderate_flows = {
        "route_north_south": 600,
        "route_south_north": 600,
        "route_east_west": 400,
        "route_west_east": 400,
        "route_clockwise": 200,
        "route_counterclockwise": 200
    }
    generator.generate_constant_traffic("moderate_traffic.rou.xml", moderate_flows)
    
    # Continue with other scenarios...
    print("Generating heavy traffic scenario...")
    heavy_flows = {
        "route_north_south": 1200,
        "route_south_north": 1200,
        "route_east_west": 800,
        "route_west_east": 800,
        "route_clockwise": 400,
        "route_counterclockwise": 400
    }
    generator.generate_constant_traffic("heavy_traffic.rou.xml", heavy_flows)
    
    print("Generating peak hour morning scenario...")
    base_flows = {
        "route_north_south": 400,
        "route_south_north": 800,
        "route_east_west": 300,
        "route_west_east": 600,
        "route_clockwise": 200,
        "route_counterclockwise": 200
    }
    peak_flows = {
        "route_north_south": 600,
        "route_south_north": 1600,
        "route_east_west": 500,
        "route_west_east": 1200,
        "route_clockwise": 300,
        "route_counterclockwise": 300
    }
    generator.generate_variable_traffic("peak_hour_morning.rou.xml", 
                                       base_flows, peak_flows, 
                                       peak_start=600, peak_end=1800)
    
    print("All scenarios generated successfully!")
    print(f"Scenario files should be in: {os.path.join(project_root, 'config', 'scenarios')}")
    # List the files in the directory to confirm
    scenario_dir = os.path.join(project_root, "config", "scenarios")
    print(f"Files in {scenario_dir}:")
    for file in os.listdir(scenario_dir):
        print(f"  - {file}")

def create_template_file(filepath):
    """Create the template route file."""
    template_content = """<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
    <!-- Vehicle type definitions -->
    <vType id="car" accel="2.9" decel="7.5" sigma="0.5" length="5" minGap="2.5" maxSpeed="16.67" guiShape="passenger"/>
    <vType id="bus" accel="1.2" decel="5.0" sigma="0.5" length="12" minGap="3.0" maxSpeed="12.5" guiShape="bus"/>
    <vType id="truck" accel="1.0" decel="5.0" sigma="0.5" length="15" minGap="3.0" maxSpeed="13.89" guiShape="truck"/>
    <vType id="emergency" accel="3.5" decel="9.0" sigma="0.5" length="5" minGap="2.5" maxSpeed="22.22" guiShape="emergency" vClass="emergency"/>
    
    <!-- Route definitions using the grid network -->
    <route id="route_north_south" edges="A1A0 A0B0"/>
    <route id="route_south_north" edges="B0A0 A0A1"/>
    <route id="route_east_west" edges="B1B0 B0A0"/>
    <route id="route_west_east" edges="A0B0 B0B1"/>
    <route id="route_clockwise" edges="A0A1 A1B1 B1B0 B0A0"/>
    <route id="route_counterclockwise" edges="A0B0 B0B1 B1A1 A1A0"/>
    
    <!-- Flow definitions will be added by specific scenarios -->
</routes>"""
    
    with open(filepath, 'w') as f:
        f.write(template_content)
    
    print(f"Created template file at: {filepath}")

if __name__ == "__main__":
    main()