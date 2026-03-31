#!/usr/bin/env python3
"""
Surgery Video Analyzer - Main Entry Point

Usage:
    # Generate synthetic test video
    python main.py generate [--full]
    
    # Analyze a video
    python main.py analyze <video_path> [--output results.csv]
    
    # Full pipeline: generate + analyze
    python main.py demo
"""

import argparse
import sys
from pathlib import Path


def cmd_generate(args):
    """Generate synthetic test video."""
    from src.synthetic_video import generate_quick_test_video, generate_full_test_video
    
    if args.full:
        print("Generating full 40-minute test video...")
        path = generate_full_test_video(args.output_dir)
    else:
        print("Generating quick 5-minute test video...")
        path = generate_quick_test_video(args.output_dir)
    
    print(f"\nVideo generated: {path}")
    print(f"Run analysis with: python main.py analyze {path}")


def cmd_analyze(args):
    """Analyze a video file."""
    from src.analyzer import SurgeryAnalyzer
    
    print(f"Analyzing video: {args.video_path}")
    print("-" * 50)
    
    analyzer = SurgeryAnalyzer(
        confidence_threshold=args.confidence,
        debounce_seconds=args.debounce,
    )
    
    events = analyzer.process_video(
        args.video_path,
        sample_rate=args.sample_rate,
        max_frames=args.max_frames,
    )
    
    # Export results
    output_path = args.output or f"{Path(args.video_path).stem}_events.csv"
    analyzer.export_events(events, output_path, format="csv")
    
    # Also export JSON
    json_path = Path(output_path).with_suffix('.json')
    analyzer.export_events(events, str(json_path), format="json")
    
    # Compute and display metrics
    print("\n" + "=" * 50)
    print("METRICS SUMMARY")
    print("=" * 50)
    
    metrics = analyzer.compute_metrics(events)
    
    print(f"Total events detected: {metrics['total_events']}")
    print(f"Procedures detected: {len(metrics['procedures'])}")
    
    for i, proc in enumerate(metrics['procedures']):
        print(f"\n  Procedure {i+1}:")
        print(f"    Cycle time: {proc['cycle_time']:.1f} sec ({proc['cycle_time']/60:.1f} min)")
        if 'prep_time' in proc:
            print(f"    Prep time: {proc['prep_time']:.1f} sec")
        if 'procedure_duration' in proc:
            print(f"    Procedure duration: {proc['procedure_duration']:.1f} sec ({proc['procedure_duration']/60:.1f} min)")
        if 'post_procedure_time' in proc:
            print(f"    Post-procedure: {proc['post_procedure_time']:.1f} sec")
    
    if metrics.get('turnovers'):
        print(f"\nTurnovers: {len(metrics['turnovers'])}")
        print(f"  Average turnover: {metrics['avg_turnover']:.1f} sec ({metrics['avg_turnover']/60:.1f} min)")
    
    if metrics.get('avg_cycle_time'):
        print(f"\nOverall:")
        print(f"  Average cycle time: {metrics['avg_cycle_time']:.1f} sec ({metrics['avg_cycle_time']/60:.1f} min)")
    
    print(f"\nResults saved to: {output_path}")


def cmd_demo(args):
    """Run full demo: generate synthetic video and analyze it."""
    from src.synthetic_video import generate_quick_test_video
    from src.analyzer import SurgeryAnalyzer
    
    print("=" * 60)
    print("SURGERY ANALYZER DEMO")
    print("=" * 60)
    
    # Step 1: Generate
    print("\n[1/2] Generating synthetic test video...")
    video_path = generate_quick_test_video("data")
    
    # Step 2: Analyze
    print("\n[2/2] Analyzing video...")
    print("-" * 50)
    
    analyzer = SurgeryAnalyzer()
    events = analyzer.process_video(video_path, sample_rate=10)
    
    # Export
    analyzer.export_events(events, "data/demo_results.csv")
    analyzer.export_events(events, "data/demo_results.json", format="json")
    
    # Metrics
    metrics = analyzer.compute_metrics(events)
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print(f"\nGenerated video: {video_path}")
    print(f"Events CSV: data/demo_results.csv")
    print(f"Events JSON: data/demo_results.json")
    print(f"\nDetected {len(events)} events across {len(metrics['procedures'])} procedure(s)")
    
    # Compare with ground truth
    import json
    gt_path = Path(video_path).with_suffix('.ground_truth.json')
    if gt_path.exists():
        with open(gt_path) as f:
            ground_truth = json.load(f)
        
        print("\n" + "-" * 40)
        print("GROUND TRUTH COMPARISON")
        print("-" * 40)
        print(f"Ground truth events: {len(ground_truth['events'])}")
        print(f"Detected events: {len(events)}")
        
        # Simple accuracy check
        gt_event_types = [e['type'] for e in ground_truth['events']]
        detected_types = [e.event_type.value for e in events]
        
        matches = sum(1 for gt, det in zip(gt_event_types, detected_types) if gt == det)
        if gt_event_types:
            print(f"Event type accuracy: {matches}/{len(gt_event_types)} ({100*matches/len(gt_event_types):.0f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Surgery Video Analyzer - Detect patients/surgeons and extract timestamps"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate synthetic test video")
    gen_parser.add_argument("--full", action="store_true", help="Generate full 40-min video")
    gen_parser.add_argument("--output-dir", default="data", help="Output directory")
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a video file")
    analyze_parser.add_argument("video_path", help="Path to video file")
    analyze_parser.add_argument("--output", "-o", help="Output CSV path")
    analyze_parser.add_argument("--sample-rate", type=int, default=5, 
                                help="Process every Nth frame (default: 5)")
    analyze_parser.add_argument("--confidence", type=float, default=0.5,
                                help="Detection confidence threshold (default: 0.5)")
    analyze_parser.add_argument("--debounce", type=float, default=5.0,
                                help="Minimum seconds between state changes (default: 5.0)")
    analyze_parser.add_argument("--max-frames", type=int, default=None,
                                help="Stop after N frames (for testing)")
    
    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run full demo with synthetic video")
    
    args = parser.parse_args()
    
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "demo":
        cmd_demo(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
