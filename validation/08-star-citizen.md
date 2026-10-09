# Test 08: spacecraft (Star Citizen / D-BOX)

Star Citizen ships an **official D-BOX haptic integration** — but it is
vendor-encapsulated. Reviewed source: `sc-telemetry-hub` (community bridge,
kept out of this repo; evidence captured in the knowledge base).

## What is observable

| Surface | Documented? | Content |
|---|---|---|
| D-BOX Monitoring Service (TCP 40001, CRLF-framed XML) | yes | hardware topology, operating state, measurements, alarms — **no game or haptic-effect events** |
| HaptiSync REST (42010 / 42011 + API key) | yes | haptic-code and profile settings, intensity/modes — control plane |
| Game → D-BOX traffic (UDP, hub research port 33740) | **no** | format unknown; the hub's binary parser is a declared placeholder |

The hub's `Telemetry` model (gforce x/y/z, roll/pitch/heave, impact
detected/magnitude/direction) is its own aspirational schema over the
undecoded traffic — not verified Star Citizen output.

## Mapping (decoded-traffic scenario)

If the game→D-BOX traffic is ever decoded, it maps without schema changes:

| Hub field | OGSA-TS destination | Class |
|---|---|---|
| `gforce.x/y/z` (body-frame G) | `bodyDynamics.specificForce` (×9.80665 → m/s²) | direct |
| `roll`/`pitch` (+ `heave`, which is linear not angular) | partial `orientation` at best — degraded-mode pose like test 07 if yaw/position are absent | recipe |
| `impact.detected` / `.magnitude` / `.direction` | `impact.*` channels (event data at tick rate rides channels) | custom channel |
| D-BOX hardware state / alarms | — | out of scope (rig-side, not game telemetry) |
| HaptiSync haptic codes / profiles / intensity | — | out of scope (control plane; OGSA-TS is read-only game → software) |

## Notes

- Star Citizen is evidence for OGSA-TS's existence, not just a test case: a AAA
  studio ships an official motion-rig integration — vendor-locked to one
  hardware ecosystem with a closed game→rig protocol. OGSA-TS is the open
  alternative for the same demand.
- The hub itself (Python daemon + custom JSON-over-UDP egress on port 5555 +
  per-language client examples) is the bespoke-bridge pattern OGSA-TS
  standardizes away: one daemon, one wire format, one client story.
- No schema gaps found: the gforce class is already covered by
  `bodyDynamics` (test 07), and impacts ride channels.

## Verdict

**Out of reach today — no documented game-side telemetry to map.** The
decoded-traffic scenario covers cleanly via existing schema; the observable
D-BOX APIs are hardware and control surfaces outside OGSA-TS's read-only
game→software scope. Third distinct source class after documented formats
(01–06) and community memory offsets (07).
