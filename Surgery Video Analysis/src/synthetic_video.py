"""
Synthetic Surgery Video Generator
Creates test videos with simulated patients and surgeons for testing the analyzer.

This generates a ~40 minute synthetic video that simulates:
- Patient entering and being positioned on table
- Surgical team gathering
- Procedure (team clustered around patient)
- Team dispersing
- Patient leaving
- Turnover period
- Next patient cycle

Output: MP4 video with simple geometric representations of people.
"""

import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import random


@dataclass
class SimulatedPerson:
    """A simulated person in the synthetic video."""
    id: int
    x: float  # Center X (0-1 normalized)
    y: float  # Center Y (0-1 normalized)
    width: float
    height: float
    color: tuple  # BGR
    is_patient: bool
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    speed: float = 0.002  # Movement speed per frame


class SyntheticVideoGenerator:
    """
    Generates synthetic surgery room footage for testing.
    
    The video shows:
    - A rectangular "operating table" in the center
    - A horizontal ellipse for "patient" (lying down)
    - Vertical ellipses for "surgeons" (standing)
    - Simulated workflow: patient in → procedure → patient out
    """
    
    def __init__(
        self,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        background_color: tuple = (40, 40, 40),  # Dark gray OR floor
        table_color: tuple = (80, 80, 80),  # Lighter gray table
        patient_color: tuple = (200, 200, 220),  # Light blue/white gown
        surgeon_color: tuple = (50, 120, 50),  # Green scrubs
    ):
        self.width = width
        self.height = height
        self.fps = fps
        self.background_color = background_color
        self.table_color = table_color
        self.patient_color = patient_color
        self.surgeon_color = surgeon_color
        
        # Operating table bounds (normalized)
        self.table_bounds = (0.3, 0.35, 0.7, 0.65)  # x1, y1, x2, y2
        
    def _draw_background(self, frame: np.ndarray):
        """Draw OR background with table."""
        frame[:] = self.background_color
        
        # Draw operating table
        x1 = int(self.table_bounds[0] * self.width)
        y1 = int(self.table_bounds[1] * self.height)
        x2 = int(self.table_bounds[2] * self.width)
        y2 = int(self.table_bounds[3] * self.height)
        
        cv2.rectangle(frame, (x1, y1), (x2, y2), self.table_color, -1)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (100, 100, 100), 2)
        
    def _draw_person(self, frame: np.ndarray, person: SimulatedPerson):
        """Draw a person as an ellipse."""
        cx = int(person.x * self.width)
        cy = int(person.y * self.height)
        w = int(person.width * self.width)
        h = int(person.height * self.height)
        
        # Patient is horizontal ellipse, surgeon is vertical
        if person.is_patient:
            axes = (w, h)  # Wide and short
        else:
            axes = (h // 2, w)  # Narrow and tall
        
        cv2.ellipse(frame, (cx, cy), axes, 0, 0, 360, person.color, -1)
        cv2.ellipse(frame, (cx, cy), axes, 0, 0, 360, (0, 0, 0), 2)
        
        # Add "head" indicator
        if person.is_patient:
            head_x = cx - w
            cv2.circle(frame, (head_x, cy), h // 2, person.color, -1)
            cv2.circle(frame, (head_x, cy), h // 2, (0, 0, 0), 2)
        else:
            head_y = cy - w
            cv2.circle(frame, (cx, head_y), h // 3, person.color, -1)
            cv2.circle(frame, (cx, head_y), h // 3, (0, 0, 0), 2)
    
    def _move_person(self, person: SimulatedPerson):
        """Move person toward target."""
        if person.target_x is None or person.target_y is None:
            return
        
        dx = person.target_x - person.x
        dy = person.target_y - person.y
        dist = np.sqrt(dx**2 + dy**2)
        
        if dist < person.speed:
            person.x = person.target_x
            person.y = person.target_y
            person.target_x = None
            person.target_y = None
        else:
            person.x += (dx / dist) * person.speed
            person.y += (dy / dist) * person.speed
    
    def _add_timestamp_overlay(self, frame: np.ndarray, timestamp: str):
        """Add timestamp to frame corner."""
        cv2.putText(
            frame, timestamp, (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2
        )
    
    def _add_state_overlay(self, frame: np.ndarray, state: str):
        """Add current state label."""
        cv2.putText(
            frame, f"State: {state}", (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1
        )
    
    def generate_video(
        self,
        output_path: str,
        num_procedures: int = 2,
        procedure_duration_sec: float = 600,  # 10 min per procedure (for shorter test)
        turnover_duration_sec: float = 180,   # 3 min turnover
        prep_duration_sec: float = 60,        # 1 min prep
        post_duration_sec: float = 60,        # 1 min post-procedure
        num_surgeons: int = 3,
        fast_mode: bool = False,  # Skip frames for faster generation
    ) -> dict:
        """
        Generate a synthetic surgery video.
        
        Returns:
            dict with ground truth events and timestamps
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            str(output_path), fourcc, self.fps, (self.width, self.height)
        )
        
        ground_truth = {
            "fps": self.fps,
            "procedures": [],
            "events": []
        }
        
        frame_number = 0
        
        # Initial surgeon positions (around the room edges)
        surgeon_home_positions = [
            (0.1, 0.3 + i * 0.15) for i in range(num_surgeons)
        ]
        
        # Table center for clustering
        table_center = (
            (self.table_bounds[0] + self.table_bounds[2]) / 2,
            (self.table_bounds[1] + self.table_bounds[3]) / 2,
        )
        
        for proc_idx in range(num_procedures):
            procedure_data = {"index": proc_idx}
            
            # Create surgeons at home positions
            surgeons = [
                SimulatedPerson(
                    id=i,
                    x=pos[0], y=pos[1],
                    width=0.08, height=0.04,
                    color=self.surgeon_color,
                    is_patient=False,
                    speed=0.003,
                )
                for i, pos in enumerate(surgeon_home_positions)
            ]
            
            patient = None
            current_state = "idle"
            
            # === PHASE 1: Patient enters ===
            patient_in_frame = frame_number
            patient_in_time = frame_number / self.fps
            ground_truth["events"].append({
                "type": "patient_in",
                "frame": patient_in_frame,
                "timestamp": patient_in_time
            })
            procedure_data["patient_in"] = patient_in_time
            
            # Patient enters from bottom
            patient = SimulatedPerson(
                id=100 + proc_idx,
                x=0.5, y=1.1,  # Start below frame
                width=0.15, height=0.04,
                color=self.patient_color,
                is_patient=True,
                speed=0.005,
            )
            patient.target_x = table_center[0]
            patient.target_y = table_center[1]
            
            current_state = "patient_entering"
            
            # Animate patient entering
            entry_frames = int(prep_duration_sec * self.fps * 0.5)
            for _ in range(entry_frames):
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                self._draw_background(frame)
                
                self._move_person(patient)
                self._draw_person(frame, patient)
                
                for surgeon in surgeons:
                    self._draw_person(frame, surgeon)
                
                timestamp = f"{int(frame_number/self.fps//60):02d}:{int(frame_number/self.fps%60):02d}"
                self._add_timestamp_overlay(frame, timestamp)
                self._add_state_overlay(frame, current_state)
                
                if not fast_mode or frame_number % 3 == 0:
                    out.write(frame)
                frame_number += 1
            
            # === PHASE 2: Surgeons gather (procedure start) ===
            procedure_start_frame = frame_number
            procedure_start_time = frame_number / self.fps
            ground_truth["events"].append({
                "type": "procedure_start",
                "frame": procedure_start_frame,
                "timestamp": procedure_start_time
            })
            procedure_data["procedure_start"] = procedure_start_time
            
            # Move surgeons toward patient
            cluster_offsets = [
                (-0.12, 0), (0.12, 0), (0, -0.12)  # Left, right, top of table
            ]
            for i, surgeon in enumerate(surgeons):
                offset = cluster_offsets[i % len(cluster_offsets)]
                surgeon.target_x = table_center[0] + offset[0]
                surgeon.target_y = table_center[1] + offset[1]
            
            current_state = "surgeons_gathering"
            
            gather_frames = int(prep_duration_sec * self.fps * 0.5)
            for _ in range(gather_frames):
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                self._draw_background(frame)
                
                self._draw_person(frame, patient)
                
                for surgeon in surgeons:
                    self._move_person(surgeon)
                    self._draw_person(frame, surgeon)
                
                timestamp = f"{int(frame_number/self.fps//60):02d}:{int(frame_number/self.fps%60):02d}"
                self._add_timestamp_overlay(frame, timestamp)
                self._add_state_overlay(frame, current_state)
                
                if not fast_mode or frame_number % 3 == 0:
                    out.write(frame)
                frame_number += 1
            
            # === PHASE 3: Procedure (surgeons clustered) ===
            current_state = "procedure_active"
            
            procedure_frames = int(procedure_duration_sec * self.fps)
            for f in range(procedure_frames):
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                self._draw_background(frame)
                
                self._draw_person(frame, patient)
                
                # Small random movements during procedure
                for surgeon in surgeons:
                    surgeon.x += random.uniform(-0.001, 0.001)
                    surgeon.y += random.uniform(-0.001, 0.001)
                    self._draw_person(frame, surgeon)
                
                timestamp = f"{int(frame_number/self.fps//60):02d}:{int(frame_number/self.fps%60):02d}"
                self._add_timestamp_overlay(frame, timestamp)
                self._add_state_overlay(frame, current_state)
                
                if not fast_mode or frame_number % 3 == 0:
                    out.write(frame)
                frame_number += 1
                
                # Progress indicator
                if f % (self.fps * 60) == 0:
                    print(f"  Procedure {proc_idx+1}: {f // (self.fps * 60)} min rendered...")
            
            # === PHASE 4: Procedure end (surgeons disperse) ===
            procedure_end_frame = frame_number
            procedure_end_time = frame_number / self.fps
            ground_truth["events"].append({
                "type": "procedure_end",
                "frame": procedure_end_frame,
                "timestamp": procedure_end_time
            })
            procedure_data["procedure_end"] = procedure_end_time
            
            # Move surgeons back to home
            for i, surgeon in enumerate(surgeons):
                surgeon.target_x = surgeon_home_positions[i][0]
                surgeon.target_y = surgeon_home_positions[i][1]
            
            current_state = "surgeons_dispersing"
            
            disperse_frames = int(post_duration_sec * self.fps * 0.5)
            for _ in range(disperse_frames):
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                self._draw_background(frame)
                
                self._draw_person(frame, patient)
                
                for surgeon in surgeons:
                    self._move_person(surgeon)
                    self._draw_person(frame, surgeon)
                
                timestamp = f"{int(frame_number/self.fps//60):02d}:{int(frame_number/self.fps%60):02d}"
                self._add_timestamp_overlay(frame, timestamp)
                self._add_state_overlay(frame, current_state)
                
                if not fast_mode or frame_number % 3 == 0:
                    out.write(frame)
                frame_number += 1
            
            # === PHASE 5: Patient exits ===
            patient.target_x = 0.5
            patient.target_y = 1.1  # Exit below frame
            
            current_state = "patient_exiting"
            
            exit_frames = int(post_duration_sec * self.fps * 0.5)
            for _ in range(exit_frames):
                frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                self._draw_background(frame)
                
                self._move_person(patient)
                if patient.y < 1.0:  # Still visible
                    self._draw_person(frame, patient)
                
                for surgeon in surgeons:
                    self._draw_person(frame, surgeon)
                
                timestamp = f"{int(frame_number/self.fps//60):02d}:{int(frame_number/self.fps%60):02d}"
                self._add_timestamp_overlay(frame, timestamp)
                self._add_state_overlay(frame, current_state)
                
                if not fast_mode or frame_number % 3 == 0:
                    out.write(frame)
                frame_number += 1
            
            patient_out_frame = frame_number
            patient_out_time = frame_number / self.fps
            ground_truth["events"].append({
                "type": "patient_out",
                "frame": patient_out_frame,
                "timestamp": patient_out_time
            })
            procedure_data["patient_out"] = patient_out_time
            
            ground_truth["procedures"].append(procedure_data)
            
            # === PHASE 6: Turnover (if not last procedure) ===
            if proc_idx < num_procedures - 1:
                current_state = "turnover"
                
                turnover_frames = int(turnover_duration_sec * self.fps)
                for _ in range(turnover_frames):
                    frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                    self._draw_background(frame)
                    
                    for surgeon in surgeons:
                        # Random movement during turnover
                        surgeon.x += random.uniform(-0.002, 0.002)
                        surgeon.y += random.uniform(-0.002, 0.002)
                        # Keep in bounds
                        surgeon.x = np.clip(surgeon.x, 0.05, 0.95)
                        surgeon.y = np.clip(surgeon.y, 0.05, 0.95)
                        self._draw_person(frame, surgeon)
                    
                    timestamp = f"{int(frame_number/self.fps//60):02d}:{int(frame_number/self.fps%60):02d}"
                    self._add_timestamp_overlay(frame, timestamp)
                    self._add_state_overlay(frame, current_state)
                    
                    if not fast_mode or frame_number % 3 == 0:
                        out.write(frame)
                    frame_number += 1
            
            print(f"Procedure {proc_idx + 1}/{num_procedures} complete")
        
        out.release()
        
        ground_truth["total_frames"] = frame_number
        ground_truth["total_duration_sec"] = frame_number / self.fps
        
        # Save ground truth
        import json
        gt_path = output_path.with_suffix('.ground_truth.json')
        with open(gt_path, 'w') as f:
            json.dump(ground_truth, f, indent=2)
        
        print(f"\nVideo saved: {output_path}")
        print(f"Ground truth: {gt_path}")
        print(f"Total duration: {frame_number / self.fps / 60:.1f} minutes")
        print(f"Total frames: {frame_number}")
        
        return ground_truth


def generate_quick_test_video(output_dir: str = "data") -> str:
    """Generate a quick 5-minute test video."""
    output_path = Path(output_dir) / "synthetic_surgery_quick.mp4"
    
    generator = SyntheticVideoGenerator()
    generator.generate_video(
        output_path=str(output_path),
        num_procedures=1,
        procedure_duration_sec=120,  # 2 min procedure
        turnover_duration_sec=30,
        prep_duration_sec=30,
        post_duration_sec=30,
        fast_mode=True,
    )
    
    return str(output_path)


def generate_full_test_video(output_dir: str = "data") -> str:
    """Generate a 40-minute realistic test video."""
    output_path = Path(output_dir) / "synthetic_surgery_full.mp4"
    
    generator = SyntheticVideoGenerator()
    generator.generate_video(
        output_path=str(output_path),
        num_procedures=2,
        procedure_duration_sec=900,   # 15 min each procedure
        turnover_duration_sec=300,    # 5 min turnover
        prep_duration_sec=120,        # 2 min prep
        post_duration_sec=120,        # 2 min post
        fast_mode=False,
    )
    
    return str(output_path)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--full":
        generate_full_test_video()
    else:
        generate_quick_test_video()
