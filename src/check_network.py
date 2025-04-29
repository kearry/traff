import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def check_traffic_lights():
    """Check if the network has traffic lights defined"""
    # Path to the SUMO network file
    net_file_path = os.path.join(project_root, "config", "maps", "traffic_grid.net.xml")
    
    print(f"Checking network file: {net_file_path}")
    print(f"File exists: {os.path.exists(net_file_path)}")
    
    if not os.path.exists(net_file_path):
        return
    
    # Parse the XML
    tree = ET.parse(net_file_path)
    root = tree.getroot()
    
    # Find traffic light junctions
    tl_junctions = root.findall(".//junction[@type='traffic_light']")
    print(f"Found {len(tl_junctions)} traffic light junctions:")
    
    for junction in tl_junctions:
        print(f"  Junction ID: {junction.get('id')}, Type: {junction.get('type')}")
    
    # Find traffic light elements
    traffic_lights = root.findall(".//tlLogic")
    print(f"Found {len(traffic_lights)} traffic light logic definitions:")
    
    for tl in traffic_lights:
        tl_id = tl.get('id')
        tl_type = tl.get('type')
        tl_program = tl.get('programID')
        phases = tl.findall(".//phase")
        
        print(f"  Traffic Light ID: {tl_id}, Type: {tl_type}, Program: {tl_program}")
        print(f"    Number of phases: {len(phases)}")
        
        for i, phase in enumerate(phases):
            duration = phase.get('duration')
            state = phase.get('state')
            print(f"    Phase {i}: Duration={duration}s, State={state}")

def main():
    check_traffic_lights()

if __name__ == "__main__":
    main()