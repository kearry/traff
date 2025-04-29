import os
import sys
import subprocess
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

def generate_network():
    """Generate the SUMO network from the configuration files"""
    # Path to the SUMO configuration file
    netccfg_path = os.path.join(project_root, "config", "maps", "traffic_grid.netccfg")
    
    print(f"Generating network from: {netccfg_path}")
    print(f"File exists: {os.path.exists(netccfg_path)}")
    
    if not os.path.exists(netccfg_path):
        print("Network configuration file not found!")
        return False
    
    # Run NETCONVERT to generate the network
    try:
        cmd = ["netconvert", "-c", netccfg_path]
        print(f"Running command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Network generation successful!")
            print(result.stdout)
            return True
        else:
            print("Network generation failed!")
            print("Error output:")
            print(result.stderr)
            return False
    
    except Exception as e:
        print(f"Error running NETCONVERT: {e}")
        return False

def main():
    if generate_network():
        print("Network generated successfully. You can now run the simulation with traffic lights.")
    else:
        print("Failed to generate the network. Please check the error messages above.")

if __name__ == "__main__":
    main()