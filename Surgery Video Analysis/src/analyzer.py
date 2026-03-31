"""
Surgery Video Analyzer — OpenCV-only backend
Detects patients and surgeons using background subtraction + contour analysis.
No PyTorch, no YOLO, no MediaPipe required.

Architecture:
    Video → Background Subtractor (MOG2) → Contours → Aspect Ratio Classification
          → Centroid Tracker → Role Assignment → State Machine → Events
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import json
import csv
from pathlib import Path
from datetime import timedelta


class PersonRole(Enum):
    UNKNOWN = "unknown"
    PATIENT = "patient"
    SURGEON = "surgeon"


class EventType(Enum):
    PATIENT_IN = "patient_in"
    PATIENT_OUT = "patient_out"
    PROCEDURE_START = "procedure_start"
    PROCEDURE_END = "procedure_end"


@dataclass
class DetectedPerson:
    track_id: int
    bbox: tuple          # (x1, y1, x2, y2)
    confidence: float    # contour area normalized — proxy for confidence
    role: PersonRole
    is_horizontal: bool
    center: tuple        # (x, y)


@dataclass
class TimestampedEvent:
    event_type: EventType
    frame_number: int
    timestamp_seconds: float
    timestamp_formatted: str
    details: dict = field(default_factory=dict)


class CentroidTracker:
    """
    Assigns consistent IDs to detected blobs across frames using nearest-centroid matching.
    No external dependencies — pure distance math.
    """
    def __init__(self, max_disappeared: int = 10):
        self.next_id = 0
        self.objects = {}          # id -> centroid
        self.disappeared = {}      # id -> frames missing
        self.max_disappeared = max_disappeared

    def update(self, centroids: list) -> dict:
        """Returns {track_id: centroid} for all currently tracked objects."""
        if not centroids:
            for oid in list(self.disappeared):
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    del self.objects[oid]
                    del self.disappeared[oid]
            return self.objects

        if not self.objects:
            for c in centroids:
                self.objects[self.next_id] = c
                self.disappeared[self.next_id] = 0
                self.next_id += 1
            return self.objects

        # Match new centroids to existing tracks by minimum distance
        object_ids = list(self.objects.keys())
        object_centroids = list(self.objects.values())

        used_rows = set()
        used_cols = set()

        # Build distance matrix
        D = np.zeros((len(object_centroids), len(centroids)))
        for i, oc in enumerate(object_centroids):
            for j, nc in enumerate(centroids):
                D[i, j] = np.sqrt((oc[0] - nc[0])**2 + (oc[1] - nc[1])**2)

        # Greedy match: sort by distance, assign closest pairs first
        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]

        for r, c in zip(rows, cols):
            if r in used_rows or c in used_cols:
                continue
            oid = object_ids[r]
            self.objects[oid] = centroids[c]
            self.disappeared[oid] = 0
            used_rows.add(r)
            used_cols.add(c)

        # Register unmatched new centroids
        for c in range(len(centroids)):
            if c not in used_cols:
                self.objects[self.next_id] = centroids[c]
                self.disappeared[self.next_id] = 0
                self.next_id += 1

        # Deregister missing tracks
        for r in range(len(object_ids)):
            if r not in used_rows:
                oid = object_ids[r]
                self.disappeared[oid] += 1
                if self.disappeared[oid] > self.max_disappeared:
                    del self.objects[oid]
                    del self.disappeared[oid]

        return self.objects


class SurgeryAnalyzer:
    """
    Main analyzer. Drop-in replacement for the YOLO-based version.

    Usage:
        analyzer = SurgeryAnalyzer()
        events = analyzer.process_video("surgery.mp4")
        analyzer.export_events(events, "output.csv")
    """

    def __init__(
        self,
        confidence_threshold: float = 0.5,   # kept for API compatibility (unused)
        table_region: Optional[tuple] = None, # (x1, y1, x2, y2) normalized 0-1
        horizontal_threshold: float = 0.7,   # aspect ratio cutoff for "lying down"
        cluster_distance: int = 150,
        min_surgeons_for_procedure: int = 2,
        debounce_seconds: float = 5.0,
        min_contour_area: int = 800,          # ignore tiny noise blobs
        bg_history: int = 200,               # MOG2 history frames
        bg_threshold: float = 40.0,          # MOG2 sensitivity
    ):
        print("Loading background subtractor (OpenCV MOG2)...")
        self.bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=bg_history,
            varThreshold=bg_threshold,
            detectShadows=False,
        )

        self.confidence_threshold  = confidence_threshold
        self.table_region          = table_region
        self.horizontal_threshold  = horizontal_threshold
        self.cluster_distance      = cluster_distance
        self.min_surgeons_for_procedure = min_surgeons_for_procedure
        self.debounce_seconds      = debounce_seconds
        self.min_contour_area      = min_contour_area

        self.tracker = CentroidTracker(max_disappeared=15)

        # State
        self.patient_present       = False
        self.procedure_active      = False
        self.last_state_change_frame = -999999

    def _classify_orientation(self, bbox: tuple) -> bool:
        """True = horizontal (patient), False = vertical (surgeon)."""
        x1, y1, x2, y2 = bbox
        width  = x2 - x1
        height = y2 - y1
        aspect = width / max(height, 1)
        return aspect > self.horizontal_threshold

    def _is_in_table_region(self, center: tuple, frame_shape: tuple) -> bool:
        if self.table_region is None:
            self.table_region = (0.2, 0.2, 0.8, 0.8)
        h, w = frame_shape[:2]
        xn = center[0] / w
        yn = center[1] / h
        x1, y1, x2, y2 = self.table_region
        return x1 <= xn <= x2 and y1 <= yn <= y2

    def _classify_role(self, bbox: tuple, is_horizontal: bool, frame_shape: tuple) -> PersonRole:
        x1, y1, x2, y2 = bbox
        center = ((x1 + x2) / 2, (y1 + y2) / 2)
        if is_horizontal and self._is_in_table_region(center, frame_shape):
            return PersonRole.PATIENT
        elif not is_horizontal:
            return PersonRole.SURGEON
        return PersonRole.UNKNOWN

    def _detect_persons(self, frame: np.ndarray) -> list:
        """
        Background subtraction → contours → aspect ratio → role classification.
        Replaces the YOLO + MediaPipe pipeline.
        """
        fg_mask = self.bg_sub.apply(frame)

        # Morphological cleanup: close small holes, remove isolated noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        centroids = []
        raw_blobs = []  # (bbox, is_horizontal, area)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_contour_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            bbox = (x, y, x + w, y + h)
            is_horizontal = self._classify_orientation(bbox)
            cx, cy = x + w // 2, y + h // 2

            centroids.append((cx, cy))
            raw_blobs.append((bbox, is_horizontal, area))

        # Update tracker
        tracked = self.tracker.update(centroids)
        id_map = {}  # centroid -> track_id
        for tid, tc in tracked.items():
            best_dist = float("inf")
            for c in centroids:
                d = np.sqrt((tc[0] - c[0])**2 + (tc[1] - c[1])**2)
                if d < best_dist:
                    best_dist = d
                    id_map[c] = tid

        persons = []
        for (bbox, is_horizontal, area), centroid in zip(raw_blobs, centroids):
            track_id = id_map.get(centroid, self.tracker.next_id)
            role = self._classify_role(bbox, is_horizontal, frame.shape)
            conf = min(area / 5000.0, 1.0)  # normalize area as proxy confidence
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            persons.append(DetectedPerson(
                track_id=track_id,
                bbox=bbox,
                confidence=conf,
                role=role,
                is_horizontal=is_horizontal,
                center=(cx, cy),
            ))

        return persons

    def _check_surgeon_cluster(self, patient: DetectedPerson, surgeons: list) -> bool:
        if len(surgeons) < self.min_surgeons_for_procedure:
            return False
        px, py = patient.center
        close = sum(
            1 for s in surgeons
            if np.sqrt((px - s.center[0])**2 + (py - s.center[1])**2) < self.cluster_distance
        )
        return close >= self.min_surgeons_for_procedure

    def _format_timestamp(self, seconds: float) -> str:
        td = timedelta(seconds=seconds)
        h, rem = divmod(td.seconds, 3600)
        m, s   = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}.{int(td.microseconds/1000):03d}"

    def _can_change_state(self, current_frame: int, fps: float) -> bool:
        return (current_frame - self.last_state_change_frame) / fps >= self.debounce_seconds

    def process_video(
        self,
        video_path: str,
        sample_rate: int = 5,
        max_frames: Optional[int] = None,
        progress_callback: Optional[callable] = None,
    ) -> list:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        fps          = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"Video: {video_path}")
        print(f"FPS: {fps}, Total frames: {total_frames}")
        print(f"Duration: {self._format_timestamp(total_frames / fps)}")
        print(f"Sample rate: every {sample_rate} frames ({fps/sample_rate:.1f} checks/sec)")
        print(f"Detection: OpenCV MOG2 background subtraction + contour analysis")
        print("-" * 50)

        events = []
        frame_number = 0
        self.patient_present       = False
        self.procedure_active      = False
        self.last_state_change_frame = -999999
        self.tracker               = CentroidTracker(max_disappeared=15)

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if max_frames and frame_number >= max_frames:
                break

            if frame_number % sample_rate == 0:
                persons  = self._detect_persons(frame)
                patients = [p for p in persons if p.role == PersonRole.PATIENT]
                surgeons = [p for p in persons if p.role == PersonRole.SURGEON]

                ts_sec = frame_number / fps
                ts_fmt = self._format_timestamp(ts_sec)
                patient_detected = len(patients) > 0

                # Patient enters
                if patient_detected and not self.patient_present:
                    if self._can_change_state(frame_number, fps):
                        self.patient_present = True
                        self.last_state_change_frame = frame_number
                        events.append(TimestampedEvent(
                            EventType.PATIENT_IN, frame_number, ts_sec, ts_fmt,
                            {"num_surgeons": len(surgeons)}
                        ))
                        print(f"[{ts_fmt}] PATIENT IN")

                # Patient leaves
                elif not patient_detected and self.patient_present:
                    if self._can_change_state(frame_number, fps):
                        self.patient_present = False
                        self.procedure_active = False
                        self.last_state_change_frame = frame_number
                        events.append(TimestampedEvent(
                            EventType.PATIENT_OUT, frame_number, ts_sec, ts_fmt
                        ))
                        print(f"[{ts_fmt}] PATIENT OUT")

                # Procedure start
                if self.patient_present and not self.procedure_active and patients:
                    if self._check_surgeon_cluster(patients[0], surgeons):
                        if self._can_change_state(frame_number, fps):
                            self.procedure_active = True
                            self.last_state_change_frame = frame_number
                            events.append(TimestampedEvent(
                                EventType.PROCEDURE_START, frame_number, ts_sec, ts_fmt,
                                {"num_surgeons": len(surgeons)}
                            ))
                            print(f"[{ts_fmt}] PROCEDURE START ({len(surgeons)} surgeons)")

                # Procedure end
                elif self.patient_present and self.procedure_active and patients:
                    if not self._check_surgeon_cluster(patients[0], surgeons):
                        if self._can_change_state(frame_number, fps):
                            self.procedure_active = False
                            self.last_state_change_frame = frame_number
                            events.append(TimestampedEvent(
                                EventType.PROCEDURE_END, frame_number, ts_sec, ts_fmt
                            ))
                            print(f"[{ts_fmt}] PROCEDURE END")

                if progress_callback:
                    progress_callback(frame_number, total_frames)

            frame_number += 1

        cap.release()
        print("-" * 50)
        print(f"Processing complete. {len(events)} events detected.")
        return events

    def export_events(self, events: list, output_path: str, format: str = "csv"):
        output_path = Path(output_path)
        if format == "csv":
            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["event_type", "frame_number", "timestamp_seconds",
                                  "timestamp_formatted", "details"])
                for e in events:
                    writer.writerow([e.event_type.value, e.frame_number,
                                     f"{e.timestamp_seconds:.3f}",
                                     e.timestamp_formatted, json.dumps(e.details)])
        elif format == "json":
            data = [{"event_type": e.event_type.value, "frame_number": e.frame_number,
                     "timestamp_seconds": e.timestamp_seconds,
                     "timestamp_formatted": e.timestamp_formatted,
                     "details": e.details} for e in events]
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
        print(f"Exported {len(events)} events to {output_path}")

    def compute_metrics(self, events: list) -> dict:
        metrics = {"total_events": len(events), "procedures": []}
        patient_in_time = procedure_start_time = procedure_end_time = None

        for event in events:
            if event.event_type == EventType.PATIENT_IN:
                patient_in_time = event.timestamp_seconds
            elif event.event_type == EventType.PROCEDURE_START:
                procedure_start_time = event.timestamp_seconds
            elif event.event_type == EventType.PROCEDURE_END:
                procedure_end_time = event.timestamp_seconds
            elif event.event_type == EventType.PATIENT_OUT:
                if patient_in_time is not None:
                    proc = {"patient_in": patient_in_time,
                            "patient_out": event.timestamp_seconds,
                            "cycle_time": event.timestamp_seconds - patient_in_time}
                    if procedure_start_time:
                        proc["procedure_start"] = procedure_start_time
                        proc["prep_time"] = procedure_start_time - patient_in_time
                    if procedure_end_time:
                        proc["procedure_end"] = procedure_end_time
                        proc["post_procedure_time"] = event.timestamp_seconds - procedure_end_time
                    if procedure_start_time and procedure_end_time:
                        proc["procedure_duration"] = procedure_end_time - procedure_start_time
                    metrics["procedures"].append(proc)
                patient_in_time = procedure_start_time = procedure_end_time = None

        turnovers = []
        for i, e in enumerate(events):
            if e.event_type == EventType.PATIENT_OUT:
                for ne in events[i+1:]:
                    if ne.event_type == EventType.PATIENT_IN:
                        turnovers.append(ne.timestamp_seconds - e.timestamp_seconds)
                        break

        metrics["turnovers"] = turnovers
        if metrics["procedures"]:
            ct = [p["cycle_time"] for p in metrics["procedures"]]
            metrics["avg_cycle_time"] = np.mean(ct)
            metrics["std_cycle_time"] = np.std(ct)
        if turnovers:
            metrics["avg_turnover"] = np.mean(turnovers)
            metrics["std_turnover"] = np.std(turnovers)

        return metrics


if __name__ == "__main__":
    analyzer = SurgeryAnalyzer()
    print("SurgeryAnalyzer (OpenCV backend) initialized successfully!")
