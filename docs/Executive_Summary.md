# Executive Summary

Team Omega is enhancing an autonomous vehicle prototype for orchard environments. The upgraded platform integrates precise navigation (RTK GPS), robust perception (LiDAR and camera), and a cloud-hosted dashboard for live monitoring. This phase focuses on reliable sensing, centimeter-level positioning, real-time data, and a future-proof image capture pipeline.

## Problem
- Existing prototype lacks centimetre-level positioning and 360° obstacle awareness.
- No reliable channel for remote monitoring and operational visibility.
- Minimal UI and no structured data pipeline for later AI analysis.

## Solution (This Phase)
- RTK GPS: Integrate simpleRTK2B (u-blox ZED-F9P) for cm-level accuracy. Reference: [simpleRTK2B Budget](https://www.ardusimple.com/product/simplertk2b/)
- LiDAR: Add SLAMTEC RPLIDAR for robust obstacle detection. SDK: `https://github.com/slamtec/rplidar_sdk`
- Cloud Dashboard: Flask API + DynamoDB backend; web UI shows live GPS, status, and stream hooks.
- Image Capture: Establish high-quality image acquisition for future AI (analysis out of scope this phase).

## Expected Outcomes
- Safer, more precise navigation in orchard rows.
- Real-time telemetry available remotely via dashboard.
- Dataset foundation for downstream AI on fruit ripeness/yield.

## Scope (In/Out)
- In: LiDAR + camera integration; RTK GPS; AWS dashboard; image capture.
- Out: AI model training/inference; new robot chassis; waterproofing.

## Risks & Mitigations
- GNSS multipath/occlusion in orchards → Mitigate via RTK base station placement, antenna quality, and sensor fusion.
- Network reliability → Local buffering with periodic sync; clear offline modes.
- Field integration delays → Stage-gated testing; modular interfaces; fallbacks.

## High-Level Timeline (Aug–Oct 2025)
- Aug: Kickoff, requirements, hardware integration
- Early Sep: Cloud dashboard + data flow
- Mid Sep: Image capture feature
- Late Sep–Oct: Field testing, refinements, handover

## Key Metrics (examples)
- RTK fix ratio ≥ 85% during field runs
- Position error (RMSE) ≤ 5 cm in test plots
- Telemetry end-to-end latency ≤ 2 s (p95)
- Uptime during field day ≥ 95%

## References
- ArduSimple simpleRTK2B: [simpleRTK2B Budget](https://www.ardusimple.com/product/simplertk2b/)
- SLAMTEC RPLIDAR SDK: `https://github.com/slamtec/rplidar_sdk` 