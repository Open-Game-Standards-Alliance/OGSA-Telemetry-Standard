# Test 09: watercraft (WhitewaterVR, YawVR plugin evidence)

WhitewaterVR (Steam 2360340) is a whitewater **rafting** game. Reviewed
source: the official-style YawVR motion-software plugin (`WhitewaterPlugin`,
built on YawGLAPI) that reads the game's native UDP output on port 33001.
Plugin code is not kept in this repo; evidence is captured in the knowledge
base.

## The packet

The plugin skips a 160-byte prefix and unpacks a flat struct:

`Speed, Rpm, MaxRpm, Gear, Roll, Pitch, Yaw, LatVel, LatAccel, VertAccel,
LongAccel, SuspensionFL/FR/RL/RR, WheelTerrainFL/FR/RL/RR`

A raft game emitting **car-shaped telemetry** — rpm, gear, four suspension
corners, four wheel-terrain ints — is the compatibility-fakery pattern:
games bend their telemetry into the shape existing motion software expects.
That fakery is the tax a generic standard removes.

## Setup

- `ObjectDescriptor`: `type = watercraft`, `primary = true`, 4 × `wheel`
  drive points used as *buoyancy corners* (suspension semantics: per-corner
  compression + contact surface — an honest fit, the point type is just a
  label)

## Core mapping

| Packet field | OGSA-TS destination | Class |
|---|---|---|
| `Roll`/`Pitch`/`Yaw` | `orientation` (Euler→quaternion) | direct |
| (no position in packet) | degraded-mode pose (held/derived), like tests 07–08 | recipe |
| `Speed` + `LatVel` | body velocity (forward, lateral, 0) → world via orientation → `kinematics.velocity` | recipe |
| `LatAccel`/`VertAccel`/`LongAccel` | `bodyDynamics.specificForce` (x/y/z) | direct |
| `SuspensionFL/FR/RL/RR` | `WheelState.compression` ×4 (buoyancy deflection) | direct |
| `WheelTerrain*` | `ContactMedium` ×4 (game-value→enum mapping table) | recipe |
| `Rpm`/`MaxRpm`/`Gear` | car-shaped fakery — if they carry meaning (e.g. paddle cadence), custom channels; otherwise unused | note |

## Notes

- Third independent confirmation of `bodyDynamics`: body-frame acceleration
  triples are what games actually expose (ED offsets, the SC decoded-traffic
  scenario, now WhitewaterVR).
- Units and gravity semantics of the accel triple need capture
  verification; the 160-byte packet prefix is unexamined by the plugin.
- The plugin itself is bespoke-parser evidence: it marshals a struct, frees
  the unmanaged buffer, then reads it (`FreeHGlobal` before
  `PtrToStructure`), and can underflow on short packets — the kind of bug a
  standard wire format and a shared client library remove.

## Verdict

**Covers** — no schema gaps. The raft maps honestly (buoyancy corners as
suspension drive points; contact surface per corner), and the car-shaped
fields are exactly the compatibility fakery OGSA-TS makes unnecessary.
