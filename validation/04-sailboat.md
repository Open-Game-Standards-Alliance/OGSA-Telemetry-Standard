# Test 04: sailboat (Sailaway-style)

## Setup

- `ObjectDescriptor`: `type = watercraft`, `primary = true`, 2–3 × `sail`
  drive points (`main`, `jib` — role carried by point name), optional `wheel`
  rudder? no — rudder is a control surface, see below

## Core mapping

| Game field | OGSA-TS destination | Class |
|---|---|---|
| lat/lon | `position` (geodetic→local tangent at sender) | direct |
| heading + heel + trim | `orientation` (Euler→quat; heel = roll) | direct |
| SOG / COG | `kinematics.velocity` (sender builds world vector) | direct |
| speed over ground | `vehicle.speed` (m/s — concept matches; boat = `watercraft` vehicle) | annex |
| TWS / TWD / AWS / AWA | `wind.*` channels (m/s, rad) — per-gust data, never discovery-static `environment` | convention channel |
| main/jib sheet % + boom angle | `SailState.sheet` + `SailState.angle` per sail point | direct |
| rudder angle | `ctrl.rudder` (−1..1) | convention channel |
| VMG / depth / water temp | `vmg`, `water.depth`, `water.temperature` | custom channel |
| hull immersion contact | `ContactMedium::water` (e.g. on a hull drive point) | direct |

## Notes

- Sail role rides the drive-point name (`main` / `jib` / `spinnaker`); sail
  geometry (area, hoist) is not modeled by the `sail` descriptor variant.
- Wind rides `wind.*` channels consistently with aviation — same mechanism,
  both domains.

## Verdict

**Covers.** Multi-sail objects work via the drive-point list; wind rides
channels consistently with aviation.
