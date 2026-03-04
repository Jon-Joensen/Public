#!/usr/bin/env python3
"""
Faroese Keyboard Layout Optimizer
Uses simulated annealing to find optimal keyboard layouts
while minimizing key position changes from Danish QWERTY
"""

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set


@dataclass
class LayoutMetrics:
    """Container for keyboard layout evaluation metrics"""
    total_score: float
    frequency_score: float
    bigram_score: float
    ergonomics_score: float
    change_penalty: float
    change_count: int


class FaroeseKeyboardOptimizer:
    """Optimizes keyboard layouts for the Faroese language"""
    
    # Danish QWERTY layout (base layout)
    BASE_LAYOUT = [
        ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', 'å'],
        ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'æ', 'ø'],
        ['z', 'x', 'c', 'v', 'b', 'n', 'm']
    ]
    
    # Faroese letters (including special characters)
    FAROESE_LETTERS = set("ertyuiopasdfghjklæøvbnmáóíúýð")
    
    def __init__(self, letter_freq: Dict[str, int], bigram_freq: Dict[Tuple[str, str], int]):
        self.letter_freq = letter_freq
        self.bigram_freq = bigram_freq
        self.base_layout_flat = []
        for row in self.BASE_LAYOUT:
            self.base_layout_flat.extend(row)
        
        # Calculate total frequency for normalization
        self.total_freq = sum(self.letter_freq.values())
        
        # Define finger positions and hand assignments
        self.finger_assignments = self._define_finger_positions()
        
        # Define ergonomic penalties
        self.ergonomic_penalties = self._define_ergonomic_penalties()

    def _define_finger_positions(self) -> Dict[str, Tuple[int, int]]:
        """Define finger positions for each key on the keyboard"""
        positions = {}
        
        # Left hand fingers: pinky(0), ring(1), middle(2), index(3)
        # Right hand fingers: index(4), middle(5), ring(6), pinky(7)
        
        # Top row (q-row)
        left_top = [(0, 'q'), (1, 'w'), (2, 'e'), (3, 'r')]
        right_top = [(4, 'y'), (5, 'u'), (6, 'i'), (7, 'o')]
        positions.update({char: (0, finger_idx) for finger_idx, char in left_top})
        positions.update({char: (0, finger_idx + 4) for finger_idx, char in right_top})
        positions['t'] = (0, 3)  # index finger
        positions['p'] = (0, 6)  # ring finger
        positions['å'] = (0, 7)  # pinky
        
        # Home row (a-row) 
        left_home = [(0, 'a'), (1, 's'), (2, 'd'), (3, 'f')]
        right_home = [(4, 'h'), (5, 'j'), (6, 'k'), (7, 'l')]
        positions.update({char: (1, finger_idx) for finger_idx, char in left_home})
        positions.update({char: (1, finger_idx + 4) for finger_idx, char in right_home})
        positions['g'] = (1, 3)  # index finger
        positions['æ'] = (1, 6)  # ring finger
        positions['ø'] = (1, 7)  # pinky
        
        # Bottom row (z-row)
        left_bottom = [(0, 'z'), (1, 'x'), (2, 'c')]
        right_bottom = [(4, 'v'), (5, 'b'), (6, 'n'), (7, 'm')]
        positions.update({char: (2, finger_idx) for finger_idx, char in left_bottom})
        positions.update({char: (2, finger_idx + 4) for finger_idx, char in right_bottom})
        
        return positions

    def _define_ergonomic_penalties(self) -> Dict[Tuple[str, str], float]:
        """Define penalties for transitions between keys"""
        penalties = {}
        
        for i, char1 in enumerate(self.base_layout_flat):
            for j, char2 in enumerate(self.base_layout_flat):
                if i != j:
                    row1, col1 = self._get_position(char1)
                    row2, col2 = self._get_position(char2)
                    
                    # Calculate distance penalty
                    distance = abs(row1 - row2) + abs(col1 - col2)
                    
                    # Same finger penalty
                    finger1 = self.finger_assignments.get(char1, (0, 0))[1]
                    finger2 = self.finger_assignments.get(char2, (0, 0))[1]
                    
                    penalty = distance * 0.5  # Base distance penalty
                    
                    # Add same finger penalty
                    if finger1 == finger2 and distance < 2:
                        penalty += 5.0  # High penalty for same finger
                    elif finger1 // 4 == finger2 // 4:  # Same hand
                        penalty += 1.0  # Medium penalty for same hand
                    else:
                        penalty -= 0.5  # Bonus for alternating hands
                        
                    penalties[(char1, char2)] = penalty
        
        return penalties

    def _get_position(self, char: str) -> Tuple[int, int]:
        """Get (row, col) position of a character in the base layout"""
        for r, row in enumerate(self.BASE_LAYOUT):
            if char in row:
                return r, row.index(char)
        return (-1, -1)  # Not found

    def evaluate_layout(self, layout: List[str]) -> LayoutMetrics:
        """Evaluate a keyboard layout based on multiple criteria"""
        freq_score = 0.0
        bigram_score = 0.0
        ergo_score = 0.0
        change_penalty = 0.0
        change_count = 0
        
        # Define high-frequency letters that should stay in place
        high_freq_letters = {'a', 'r', 'i', 'n', 'e', 't', 's', 'u', 'l', 'm'}
        
        # Count changes from base layout
        for i, char in enumerate(layout):
            if char != self.base_layout_flat[i]:
                change_count += 1
                # Higher penalty for changing high-frequency letters
                if self.base_layout_flat[i] in high_freq_letters:
                    change_penalty += 50.0  # Very high penalty for moving high-frequency letters
                else:
                    change_penalty += 10.0  # Standard penalty for other changes
        
        # Evaluate letter frequencies
        for char, freq in self.letter_freq.items():
            if char in layout:
                pos = layout.index(char)
                # Higher scores for more frequent letters in better positions
                # Better positions are closer to home row and center
                row, col = pos // 11, pos % 11
                pos_penalty = abs(row - 1) + abs(col - 5)  # Penalize distance from home row center
                freq_score += (freq / self.total_freq) * (10 - min(pos_penalty, 10))
        
        # Evaluate bigrams
        for (char1, char2), freq in self.bigram_freq.items():
            if char1 in layout and char2 in layout:
                pos1 = layout.index(char1)
                pos2 = layout.index(char2)
                
                row1, col1 = pos1 // 11, pos1 % 11
                row2, col2 = pos2 // 11, pos2 % 11
                
                # Distance penalty
                distance = abs(row1 - row2) + abs(col1 - col2)
                
                # Finger assignment check
                finger1 = self.finger_assignments.get(char1, (0, 0))[1]
                finger2 = self.finger_assignments.get(char2, (0, 0))[1]
                
                if finger1 == finger2:
                    bigram_score -= freq * 0.1  # Penalty for same finger
                else:
                    bigram_score += freq * 0.05  # Bonus for alternating hands
                
                bigram_score -= distance * freq * 0.01  # Distance penalty
        
        # Total score calculation - adjusted weights to favor frequency and minimize changes
        total_score = freq_score * 0.6 + bigram_score * 0.2 + (100 - change_penalty * 0.2) * 0.2
        
        return LayoutMetrics(
            total_score=total_score,
            frequency_score=freq_score,
            bigram_score=bigram_score,
            ergonomics_score=ergo_score,
            change_penalty=change_penalty,
            change_count=change_count
        )

    def generate_neighbor(self, layout: List[str]) -> List[str]:
        """Generate a neighboring layout by swapping two positions"""
        new_layout = layout[:]
        
        # Define high-frequency letters that should stay in place
        high_freq_letters = {'a', 'r', 'i', 'n', 'e', 't', 's', 'u', 'l', 'm'}
        
        # Randomly decide whether to swap positions or swap with unused letters
        if random.random() < 0.8:  # 80% chance to swap existing positions
            # Only select positions that don't contain high-frequency letters
            valid_indices = [i for i, char in enumerate(layout) if self.base_layout_flat[i] not in high_freq_letters]
            if len(valid_indices) >= 2:
                i, j = random.sample(valid_indices, 2)
                new_layout[i], new_layout[j] = new_layout[j], new_layout[i]
            else:
                # If we don't have enough valid indices, just do a regular swap
                i, j = random.sample(range(len(layout)), 2)
                new_layout[i], new_layout[j] = new_layout[j], new_layout[i]
        else:  # 20% chance to replace a position with a Faroese letter
            # Select a position that doesn't contain a high-frequency letter
            valid_indices = [i for i, char in enumerate(layout) if self.base_layout_flat[i] not in high_freq_letters]
            if valid_indices:
                pos = random.choice(valid_indices)
                # Get a random Faroese letter that's not already in the layout
                available_letters = self.FAROESE_LETTERS - set(new_layout)
                if available_letters:
                    new_char = random.choice(list(available_letters))
                    old_char = new_layout[pos]
                    new_layout[pos] = new_char
        
        return new_layout

    def simulated_annealing(self, max_iterations: int = 10000, initial_temp: float = 100.0, cooling_rate: float = 0.995) -> Tuple[List[str], LayoutMetrics]:
        """Perform simulated annealing optimization"""
        # Start with base layout
        current_layout = self.base_layout_flat[:]
        current_metrics = self.evaluate_layout(current_layout)
        
        best_layout = current_layout[:]
        best_metrics = current_metrics
        
        temperature = initial_temp
        
        for iteration in range(max_iterations):
            # Generate neighbor
            neighbor_layout = self.generate_neighbor(current_layout)
            neighbor_metrics = self.evaluate_layout(neighbor_layout)
            
            # Calculate energy difference
            delta = neighbor_metrics.total_score - current_metrics.total_score
            
            # Accept or reject the neighbor
            if delta > 0 or random.random() < math.exp(delta / temperature):
                current_layout = neighbor_layout
                current_metrics = neighbor_metrics
                
                # Update best solution if better
                if neighbor_metrics.total_score > best_metrics.total_score:
                    best_layout = neighbor_layout[:]
                    best_metrics = neighbor_metrics
            
            # Cool down
            temperature *= cooling_rate
            
            # Print progress occasionally
            if iteration % 1000 == 0:
                print(f"Iteration {iteration}: Best score = {best_metrics.total_score:.2f}, Changes = {best_metrics.change_count}")
        
        return best_layout, best_metrics

    def layout_to_string(self, layout: List[str]) -> str:
        """Convert layout list to formatted string"""
        rows = []
        rows.append(''.join(layout[0:11]))  # First row (11 chars)
        rows.append(''.join(layout[11:22]))  # Second row (11 chars)  
        rows.append(''.join(layout[22:29]))  # Third row (7 chars)
        return '\n'.join(rows)


def load_sample_data():
    """Load sample frequency and bigram data for testing"""
    # Sample letter frequencies based on provided data
    letter_freq = {
        'a': 909915, 'r': 897171, 'i': 865729, 'n': 782959, 
        'e': 584544, 't': 578155, 's': 549022, 'u': 474494,
        'l': 450664, 'm': 359361, 'g': 342334, 'k': 331340,
        'o': 326081, 'v': 286603, 'd': 243607, 'ð': 237263,
        'f': 217039, 'h': 188555, 'í': 149856, 'b': 130294,
        'á': 122803, 'y': 122209, 'p': 112011, 'ø': 103529,
        'j': 103347, 'ó': 95083, 'c': 46939, 'ú': 44811,
        'æ': 34971, 'ý': 25198, 'w': 16295, 'z': 6321,
        'x': 5076
    }
    
    # Sample bigram frequencies (simplified)
    bigram_freq = {
        ('i', 'ð'): 5000, ('a', 'ð'): 4500, ('ð', 'i'): 4000,
        ('e', 'r'): 10000, ('r', 't'): 8000, ('t', 'i'): 7000,
        ('i', 'n'): 9000, ('n', 'g'): 6000, ('g', 'i'): 5500
    }
    
    return letter_freq, bigram_freq


def main():
    """Main function to run the optimization"""
    print("Loading Faroese keyboard optimization data...")
    
    # Load frequency data
    letter_freq, bigram_freq = load_sample_data()
    
    print("Initializing optimizer...")
    optimizer = FaroeseKeyboardOptimizer(letter_freq, bigram_freq)
    
    print("Starting simulated annealing optimization...")
    print("Initial layout:")
    print(optimizer.layout_to_string(optimizer.base_layout_flat))
    print()
    
    best_layout, best_metrics = optimizer.simulated_annealing(max_iterations=20000)
    
    print("\nOptimization completed!")
    print(f"Best layout score: {best_metrics.total_score:.2f}")
    print(f"Changes from base: {best_metrics.change_count}")
    print(f"Frequency score: {best_metrics.frequency_score:.2f}")
    print(f"Bigram score: {best_metrics.bigram_score:.2f}")
    print(f"Change penalty: {best_metrics.change_penalty:.2f}")
    
    print("\nOptimized layout:")
    print(optimizer.layout_to_string(best_layout))
    
    print("\nBase layout comparison:")
    print(optimizer.layout_to_string(optimizer.base_layout_flat))
    
    # Show differences
    print("\nChanges made:")
    for i, (base_char, opt_char) in enumerate(zip(optimizer.base_layout_flat, best_layout)):
        if base_char != opt_char:
            row, col = i // 11, i % 11
            print(f"Position ({row},{col}): '{base_char}' → '{opt_char}'")


if __name__ == "__main__":
    main()