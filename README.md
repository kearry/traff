# AI Traffic Control Comparison

This project simulates and compares AI-controlled traffic systems operating over wireless and wired networks. The simulation environment uses SUMO (Simulation of Urban MObility) for traffic simulation and Pygame for visualization.

## Project Overview

The goal of this project is to investigate whether AI-driven traffic management using wireless systems can provide a more efficient alternative to traditional wired traffic control. The simulation allows for direct comparison between different control methods:

1. **Wired AI Controller**: Simulates fixed-network communication with consistent latency
2. **Wireless AI Controller**: Simulates wireless communication with dynamic computation delays
3. **Traditional Controller**: Uses fixed timing for traffic lights without adaptive behavior

## Features

- Realistic traffic simulation with multiple vehicle types (cars, trucks, buses, emergency vehicles)
- Visual representation of traffic flow with customizable views
- Multiple AI controllers with different network characteristics
- Comparative analysis using metrics like waiting time, speed, and throughput
- Various traffic scenarios to test controller performance under different conditions
- Enhanced visualization with realistic vehicle graphics and traffic light displays

## Installation

### Prerequisites

- Python 3.8 or higher
- SUMO (Simulation of Urban MObility) 1.18.0 or higher
- Pygame 2.5.0 or higher
- NumPy, Matplotlib, and other dependencies

### Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd traffic_ai_comparison
   ```

2. Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Make sure SUMO is properly installed and accessible in your PATH.

4. Create an assets directory for vehicle sprites:
   ```
   mkdir -p assets/vehicles
   ```

5. Place vehicle sprite images in the assets/vehicles directory (optional):
   - car.png
   - bus.png
   - truck.png
   - emergency.png

## Usage

### Running a Simulation

To run a simulation with default settings:

```
python src/run_enhanced_visualization.py
```

To run a specific scenario with a chosen controller:

```
python src/run_enhanced_visualization.py --scenario light_traffic --controller "Wired AI" --delay 50
```

Available options:
- `--scenario`: Name of the scenario to run (light_traffic, moderate_traffic, heavy_traffic, peak_hour_morning)
- `--controller`: Controller type ("Wired AI", "Wireless AI", "Traditional")
- `--steps`: Number of simulation steps to run
- `--delay`: Delay in milliseconds between steps

### Controls

During the simulation, you can use the following controls:
- **Mouse drag**: Pan the view
- **Mouse wheel**: Zoom in and out
- **I key**: Toggle vehicle IDs display
- **S key**: Toggle speed display
- **W key**: Toggle waiting time display
- **ESC key**: Quit

### Running Comparisons

To run a comparison between different controllers:

```
python src/test_scenarios.py --all
```

This will run all scenarios with all controllers and save the results to the `data/outputs` directory.

## Project Structure

```
traffic_ai_comparison/
├── assets/
│   └── vehicles/           # Vehicle sprite images
├── config/
│   ├── maps/               # SUMO network definitions
│   └── scenarios/          # Traffic scenarios
├── data/
│   └── outputs/            # Simulation results and metrics
├── src/
│   ├── ai/                 # AI controller implementations
│   │   ├── controller.py   # Base controller class
│   │   ├── wired_controller.py
│   │   ├── wireless_controller.py
│   │   └── traditional_controller.py
│   ├── simulation/         # Simulation components
│   ├── ui/                 # Visualization components
│   │   ├── enhanced_renderer.py
│   │   ├── enhanced_sumo_visualization.py
│   │   └── traffic_renderer.py
│   └── utils/              # Utility functions
├── README.md
└── requirements.txt
```

## Customization

### Modifying the Road Network

The road network is defined in the SUMO configuration files in the `config/maps` directory. You can use SUMO's NetEdit tool to create custom networks.

### Changing the Vehicle Appearance

To customize vehicle appearance:
1. Place new sprite images in the `assets/vehicles` directory
2. Modify the `_load_vehicle_sprites` method in `src/ui/enhanced_renderer.py`

### Adjusting the Simulation Parameters

You can modify various simulation parameters:
- Road width: Change the `road_width` value in the `render_network` method in `src/ui/enhanced_renderer.py`
- Vehicle sizes: Adjust the `base_width` and `base_height` values in the `render_vehicle` method
- Traffic light appearance: Modify the `render_traffic_light` method

## Academic Purpose

This project was developed as part of a BSc Computer Science dissertation to investigate the effectiveness of AI in controlling traffic systems wirelessly compared to traditional wired traffic systems.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- SUMO Team for the traffic simulation framework
- Pygame Community for the visualization library
- [Your University/Supervisor Name] for guidance and support