# Test 07: spacecraft (Elite Dangerous community offsets)

Source: [`EliteDangerous64_Offsets.xml`](EliteDangerous64_Offsets.xml) —
community-maintained memory offsets (Wagnard, 2026-07-09; Horizons and
Odyssey layouts). Elite Dangerous has **no official telemetry**, so this is
the reverse-engineering path: patch-fragile by nature, and senders built on
it inherit that maintenance burden.

The offsets expose, per game build, for ship and SRV (Surface Recon
Vehicle): `Speed`, body-frame accelerations `Sway`/`Heave`/`Surge`, and
angular rates `Pitch`/`Yaw`/`Roll`. **No position, no orientation** — this
is an accelerometer-class source.

## Setup

- Ship: `ObjectDescriptor` `type = spacecraft`, `primary = true`, 1 × `jet`
  drive point (main thruster), 2 × `leg` (landing legs) — or `generic` for
  legs
- SRV: second object `type = vehicle`, `generic` drive points (no per-wheel
  offsets exist)
- Entering/leaving the SRV re-sends discovery with a new primary object —
  the same within-game switching flow as open-world cars

## Core mapping

| Offset | OGSA-TS destination | Class |
|---|---|---|
| `Sway`/`Heave`/`Surge` | `bodyDynamics.specificForce` (x/y/z, body frame) | direct |
| `Pitch`/`Yaw`/`Roll` | `bodyDynamics.angularVelocity` (rad/s conversion) | direct |
| `Speed` | `vehicle.speed` (m/s) | annex |
| SRV `*` | same fields on the second object | direct |
| (no pose in source) | `position`/`orientation` fused from Status.json — heading, and lat/lon/alt near planets — updated ~1 Hz and held between updates | degraded-mode recipe |

Everything else an Elite dashboard wants — pips, heat, shields, hull,
cargo, FSD state, silent running, flight assist — is not in the offsets
file and rides `ship.*` / annex channels sourced from Journal/Status.json
(`fuel.level`, `lights.headlights`, `gear.down`, …).

## Notes

- `BodyDynamics` is the native representation of accelerometer-class
  sources and the direct input of motion-cueing washout filters; senders
  choose whichever dynamics representation they measure natively (world
  `kinematics` or body `bodyDynamics`) — receivers convert via orientation.
- Verify units and gravity semantics of `Sway`/`Heave`/`Surge`
  (accelerometer-style specific force vs. coordinate acceleration) against
  packet captures before building a rig-facing sender.
- The pose core cannot be filled from this source at telemetry rate; a
  fused low-rate pose keeps the stream compliant while motion cueing runs
  entirely from `bodyDynamics` — which is what a rig needs anyway.

## Verdict

**Covers, with a source limitation (not a schema gap).** Elite Dangerous
exercises the `spacecraft` type, multi-object streaming with primary
switching (ship ↔ SRV), and — via `bodyDynamics` — the accelerometer-class
source pattern no official-docs game had shown yet.
