# Test 06: drone and mech (generic + legs + multi-propeller)

## Drone (FPV-sim / MAVLink-style)

- `ObjectDescriptor`: `type = aircraft`, 4 × `propeller` drive points
  (`PropellerSpec` from the model's prop geometry)
- position/attitude/velocity → pose + kinematics (MAVLink's local NED frame
  → OGSA-TS axis remap at sender)
- per-motor rpm → `PropellerState.rpm` ×4
- per-motor thrust (rarely measured in sims) → optional
  `PropellerExtended.thrust`; the `core` variant otherwise
- battery → `fuel.level` (concept match)
- mode flags (angle/acro) → `flight.mode` text channel

## Mech (legged)

- `ObjectDescriptor`: `type = humanoid` or `other`, N × `leg` drive points
- pose → pose; footsteps → `LegState.contact` + `phase` (gait cycle 0..1)
- per-leg ground force → `LegState.force` (optional, world-space N,
  mirroring `GenericState`)
- hover fans / jump jets → `generic` points with `force`
- heat/reactor → `mech.*` channels

## Verdict

**Covers.** The drive-point union plus the generic escape hatch absorbs both
exotic domains; nothing required a new dedicated variant.
