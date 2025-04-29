import os
import sys
import time
import random
import numpy as np
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(project_root))

from src.ai.reinforcement_learning.q_learning_controller import QLearningController

class WirelessRLController(QLearningController):
    """
    Wireless Reinforcement Learning Controller.
    
    This controller extends the Q-Learning controller and simulates
    wireless network conditions (variable latency, potential packet loss).
    """
    def __init__(self, junction_ids, learning_rate=0.1, discount_factor=0.9, 
                exploration_rate=0.3, state_bins=3, model_path=None,
                base_latency=0.05, computation_factor=0.1, packet_loss_prob=0.01):
        """
        Initialize the Wireless RL controller.
        
        Args:
            junction_ids (list): List of junction IDs to control
            learning_rate (float): Alpha parameter for Q-learning updates (0-1)
            discount_factor (float): Gamma parameter for future reward discounting (0-1)
            exploration_rate (float): Epsilon parameter for exploration vs. exploitation (0-1)
            state_bins (int): Number of bins to discretize continuous state variables
            model_path (str): Path to load a pre-trained Q-table (optional)
            base_latency (float): Base network latency in seconds
            computation_factor (float): Factor for additional computation time
            packet_loss_prob (float): Probability of packet loss (0-1)
        """
        # Call the parent constructor with the correct number of arguments
        super().__init__(junction_ids, learning_rate, discount_factor, 
                        exploration_rate, state_bins, model_path)
        
        # Wireless network simulation parameters
        self.base_latency = base_latency
        self.computation_factor = computation_factor
        self.packet_loss_prob = packet_loss_prob
        
        # Statistics for network conditions
        self.total_latency = 0
        self.packet_losses = 0
        self.decision_count = 0
        
        print(f"Initialized Wireless RL Controller with base_latency={base_latency}, " 
                f"computation_factor={computation_factor}, packet_loss_prob={packet_loss_prob}")
    
    def _calculate_dynamic_latency(self, traffic_complexity):
        """
        Calculate dynamic latency based on traffic complexity and random factors
        (simulating wireless interference, computation time, etc.)
        
        Args:
            traffic_complexity (float): Measure of traffic complexity (0.0-1.0)
            
        Returns:
            float: Total latency time in seconds
        """
        # Base latency - reduced for training purposes
        latency = self.base_latency * 0.5
        
        # Add computation time based on traffic complexity - more reasonable scaling
        computation_time = traffic_complexity * self.computation_factor * 0.5
        
        # Add random fluctuation to simulate wireless interference
        # Keep this minimal during training to allow learning
        interference = random.uniform(0, 0.05) * traffic_complexity
        
        total_latency = latency + computation_time + interference
        
        # Cap maximum latency for training purposes
        return min(total_latency, 0.1)  # Max 100ms latency during training
    
    def _simulate_packet_loss(self):
        """
        Simulate packet loss in wireless network.
        
        Returns:
            bool: True if packet was lost, False otherwise
        """
        # During training, use much lower packet loss probability
        training_packet_loss_prob = min(0.001, self.packet_loss_prob)
        
        if random.random() < training_packet_loss_prob:
            self.packet_losses += 1
            return True
        return False
    
    def decide_phase(self, junction_id, current_time):
        """
        Decide the next traffic light phase using RL with simulated wireless conditions.
        
        Args:
            junction_id (str): The ID of the junction to control
            current_time (float): Current simulation time
            
        Returns:
            str: The traffic light state to set
        """
        # Get the current traffic state for complexity calculation
        if junction_id in self.traffic_state:
            traffic_state = self.traffic_state[junction_id]
            
            # Calculate traffic complexity based on total vehicles and balance
            north_count = traffic_state.get('north_count', 0)
            south_count = traffic_state.get('south_count', 0)
            east_count = traffic_state.get('east_count', 0)
            west_count = traffic_state.get('west_count', 0)
            
            total_vehicles = north_count + south_count + east_count + west_count
            
            if total_vehicles > 0:
                ns_total = north_count + south_count
                ew_total = east_count + west_count
                
                # Improved balance calculation
                balance = abs(ns_total - ew_total) / total_vehicles
                
                # Normalize total vehicles (assuming max of 50 is high complexity)
                volume_factor = min(1.0, total_vehicles / 50.0)
                
                # Calculate traffic complexity with more weight on volume
                traffic_complexity = (volume_factor * 0.8) + (balance * 0.2)
            else:
                traffic_complexity = 0.0
        else:
            traffic_complexity = 0.3  # Default medium-low complexity
        
        # Store the current state before applying network effects
        # This ensures we have the state for learning regardless of network conditions
        current_state = self._get_state(junction_id)
        self.current_states[junction_id] = current_state
        
        # Simulate wireless network conditions
        dynamic_latency = self._calculate_dynamic_latency(traffic_complexity)
        
        # Use reduced latency during training
        actual_latency = dynamic_latency * 0.1 if self.exploration_rate > 0.1 else dynamic_latency
        time.sleep(actual_latency)
        
        self.total_latency += dynamic_latency
        self.decision_count += 1
        
        # Simulate potential packet loss
        packet_lost = self._simulate_packet_loss()
        
        # Get reward for the previous action - always compute this
        # to ensure learning happens even with packet loss
        reward = self._get_reward(junction_id)
        
        # Always record rewards for tracking learning progress
        self.total_rewards += reward
        self.reward_history.append(reward)
        
        # Only update Q-values if we have previous state and action
        prev_state = self.current_states.get(junction_id)
        prev_action = self.last_actions.get(junction_id)
        
        if prev_state is not None and prev_action is not None:
            # Update Q-value
            self._update_q_value(prev_state, prev_action, current_state, reward, junction_id)
        
        # If packet loss, return the last action but still learn
        if packet_lost and junction_id in self.last_actions and self.last_actions[junction_id] is not None:
            return self.last_actions[junction_id]
        
        # Record start time for response time measurement
        response_start = time.time()
        
        # Select next action
        action = self._select_action(current_state, junction_id)
        
        # Ensure action is a valid phase string
        if not isinstance(action, str) or action not in self.phase_sequence:
            print(f"Warning: Invalid action type {type(action)} or value {action}. Using default phase.")
            action = self.phase_sequence[0]
        
        # Store the action
        self.last_actions[junction_id] = action
        
        # Record response time
        self.response_times.append(time.time() - response_start)
        
        # Ensure the phase matches the expected length for this junction
        if hasattr(self, 'tl_state_lengths') and junction_id in self.tl_state_lengths:
            expected_length = self.tl_state_lengths[junction_id]
            if len(action) != expected_length:
                # Adjust phase length to match expected length
                if len(action) < expected_length:
                    action = action * (expected_length // len(action)) + action[:expected_length % len(action)]
                else:
                    action = action[:expected_length]
        
        # Print debug info occasionally during training
        if self.decision_count % 100 == 0:
            print(f"Junction {junction_id} - Traffic complexity: {traffic_complexity:.2f}, "
                  f"Latency: {dynamic_latency*1000:.2f}ms, Reward: {reward:.2f}")
            
            if junction_id in self.q_tables and self.q_tables[junction_id]:
                q_entries = len(self.q_tables[junction_id])
                print(f"  Q-table entries: {q_entries}, "
                      f"Exploration rate: {self.exploration_rate:.3f}")
        
        return action
    
    def reset_metrics(self):
        """Reset accumulated metrics for a new episode"""
        self.total_rewards = 0
        self.reward_history = []
        self.response_times = []
        self.decision_times = []
        self.total_latency = 0
        self.packet_losses = 0
        self.decision_count = 0
        
        # Don't reset the Q-tables as those need to persist between episodes
    
    def get_network_stats(self):
        """Get statistics about the simulated wireless network."""
        if self.decision_count == 0:
            return {
                "avg_latency": 0,
                "packet_loss_rate": 0,
                "decision_count": 0
            }
        
        return {
            "avg_latency": self.total_latency / self.decision_count,
            "packet_loss_rate": self.packet_losses / self.decision_count,
            "decision_count": self.decision_count
        }