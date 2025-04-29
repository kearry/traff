import numpy as np
from pathlib import Path
import xml.etree.ElementTree as ET

class SumoNetworkParser:
    """
    Parse SUMO network XML to extract nodes (junctions) and edges (roads).
    """
    def __init__(self, net_file_path):
        """
        Initialize the parser with a SUMO .net.xml file path.
        
        Args:
            net_file_path (str): Path to the SUMO network XML file
        """
        self.net_file_path = Path(net_file_path)
        self.nodes = {}  # id -> (x, y)
        self.edges = {}  # id -> {"from": node_id, "to": node_id, "shape": [(x1, y1), (x2, y2), ...]}
        self.connections = []  # list of (from_edge, to_edge, from_lane, to_lane)
        
        # Parse the network file
        self._parse_network()
        
    def _parse_network(self):
        """Parse the SUMO network XML file."""
        if not self.net_file_path.exists():
            raise FileNotFoundError(f"Network file not found: {self.net_file_path}")

        # Parse the XML
        tree = ET.parse(self.net_file_path)
        root = tree.getroot()
        
        # Parse junctions (nodes)
        for junction in root.findall('.//junction'):
            junction_id = junction.get('id')
            # Skip internal junctions
            if junction.get('type') == 'internal':
                continue
                
            x = float(junction.get('x'))
            y = float(junction.get('y'))
            self.nodes[junction_id] = (x, y)
        
        # Parse edges
        for edge in root.findall('.//edge'):
            edge_id = edge.get('id')
            # Skip internal edges
            if edge.get('function') == 'internal':
                continue
                
            from_node = edge.get('from')
            to_node = edge.get('to')
            
            # Get shape points if available
            shape_points = []
            lanes = edge.findall('.//lane')
            if lanes:
                # Use the first lane's shape
                lane_shape = lanes[0].get('shape')
                if lane_shape:
                    # Shape format: "x1,y1 x2,y2 x3,y3 ..."
                    points = lane_shape.split()
                    for point in points:
                        x, y = map(float, point.split(','))
                        shape_points.append((x, y))
            
            # If no shape points, use from and to node coordinates
            if not shape_points and from_node in self.nodes and to_node in self.nodes:
                shape_points = [self.nodes[from_node], self.nodes[to_node]]
            
            self.edges[edge_id] = {
                "from": from_node,
                "to": to_node,
                "shape": shape_points
            }
        
        # Parse connections
        for connection in root.findall('.//connection'):
            from_edge = connection.get('from')
            to_edge = connection.get('to')
            from_lane = int(connection.get('fromLane'))
            to_lane = int(connection.get('toLane'))
            
            # Skip connections involving internal edges
            if from_edge.startswith(':') or to_edge.startswith(':'):
                continue
                
            self.connections.append((from_edge, to_edge, from_lane, to_lane))
        
        print(f"Parsed SUMO network with {len(self.nodes)} nodes and {len(self.edges)} edges")

class SumoPygameMapper:
    """
    Maps SUMO coordinates to Pygame screen coordinates.
    """
    def __init__(self, net_parser, screen_width, screen_height, margin=50):
        """
        Initialize the coordinate mapper.
        
        Args:
            net_parser (SumoNetworkParser): Parsed SUMO network
            screen_width (int): Width of the Pygame screen
            screen_height (int): Height of the Pygame screen
            margin (int): Margin around the network in pixels
        """
        self.net_parser = net_parser
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.margin = margin
        
        # Calculate network bounds
        self._calculate_bounds()
        
        # Calculate scaling factors
        self._calculate_scaling()
        
    def _calculate_bounds(self):
        """Calculate the bounding box of the SUMO network."""
        # Initialize with extreme values
        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.min_y = float('inf')
        self.max_y = float('-inf')
        
        # Check node coordinates
        for _, (x, y) in self.net_parser.nodes.items():
            self.min_x = min(self.min_x, x)
            self.max_x = max(self.max_x, x)
            self.min_y = min(self.min_y, y)
            self.max_y = max(self.max_y, y)
        
        # Check edge shape points
        for _, edge_data in self.net_parser.edges.items():
            for x, y in edge_data["shape"]:
                self.min_x = min(self.min_x, x)
                self.max_x = max(self.max_x, x)
                self.min_y = min(self.min_y, y)
                self.max_y = max(self.max_y, y)
        
        # If no valid coordinates found, use defaults
        if self.min_x == float('inf'):
            self.min_x, self.max_x = 0, 100
            self.min_y, self.max_y = 0, 100
        
        # Network dimensions
        self.net_width = self.max_x - self.min_x
        self.net_height = self.max_y - self.min_y
        
        print(f"Network bounds: ({self.min_x}, {self.min_y}) to ({self.max_x}, {self.max_y})")
    
    def _calculate_scaling(self):
        """Calculate scaling factors to fit the network in the screen."""
        # Available screen dimensions (accounting for margin)
        available_width = self.screen_width - 2 * self.margin
        available_height = self.screen_height - 2 * self.margin
        
        # Calculate scaling factors
        self.scale_x = available_width / self.net_width if self.net_width > 0 else 1
        self.scale_y = available_height / self.net_height if self.net_height > 0 else 1
        
        # Use the smaller scaling factor to maintain aspect ratio
        self.scale = min(self.scale_x, self.scale_y)
        
        # Recalculate to center the network
        self.offset_x = self.margin + (available_width - self.net_width * self.scale) / 2
        self.offset_y = self.margin + (available_height - self.net_height * self.scale) / 2
        
        print(f"Scaling factor: {self.scale}, Offsets: ({self.offset_x}, {self.offset_y})")
    
    def sumo_to_pygame(self, sumo_x, sumo_y):
        """
        Convert SUMO coordinates to Pygame screen coordinates.
        
        Args:
            sumo_x (float): X coordinate in SUMO
            sumo_y (float): Y coordinate in SUMO
            
        Returns:
            tuple: (pygame_x, pygame_y) coordinates
        """
        # Scale and translate
        pygame_x = self.offset_x + (sumo_x - self.min_x) * self.scale
        # Flip Y-axis (SUMO's Y increases upward, Pygame's Y increases downward)
        pygame_y = self.screen_height - (self.offset_y + (sumo_y - self.min_y) * self.scale)
        
        return int(pygame_x), int(pygame_y)
    
    def get_node_position(self, node_id):
        """
        Get the Pygame screen position of a SUMO node.
        
        Args:
            node_id (str): ID of the SUMO node
            
        Returns:
            tuple or None: (pygame_x, pygame_y) if node exists, None otherwise
        """
        if node_id in self.net_parser.nodes:
            sumo_x, sumo_y = self.net_parser.nodes[node_id]
            return self.sumo_to_pygame(sumo_x, sumo_y)
        return None
    
    def get_edge_shape(self, edge_id):
        """
        Get the Pygame screen coordinates for an edge's shape.
        
        Args:
            edge_id (str): ID of the SUMO edge
            
        Returns:
            list or None: List of (pygame_x, pygame_y) points if edge exists, None otherwise
        """
        if edge_id in self.net_parser.edges:
            shape = self.net_parser.edges[edge_id]["shape"]
            return [self.sumo_to_pygame(x, y) for x, y in shape]
        return None

# Test the mapper
if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path
    
    # Add project root to Python path
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.append(str(project_root))
    
    # Path to the SUMO network file
    net_file_path = os.path.join(project_root, "config", "maps", "grid_network.net.xml")
    
    # Parse the network
    parser = SumoNetworkParser(net_file_path)
    
    # Create a mapper
    mapper = SumoPygameMapper(parser, 800, 600)
    
    # Print some mapped coordinates
    for node_id, (x, y) in list(parser.nodes.items())[:5]:
        pygame_x, pygame_y = mapper.sumo_to_pygame(x, y)
        print(f"Node {node_id}: SUMO ({x}, {y}) -> Pygame ({pygame_x}, {pygame_y})")
    
    # Print some edge shapes
    for edge_id, edge_data in list(parser.edges.items())[:2]:
        print(f"Edge {edge_id} shape:")
        for i, (x, y) in enumerate(edge_data["shape"]):
            pygame_x, pygame_y = mapper.sumo_to_pygame(x, y)
            print(f"  Point {i}: SUMO ({x}, {y}) -> Pygame ({pygame_x}, {pygame_y})")