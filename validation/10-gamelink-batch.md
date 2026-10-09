# Test 10: batch survey (YawVR GameLink plugin collection, 72 games)

Reviewed source: the complete YawVR GameLink plugin collection (72 C#
plugins, YawGLAPI). Plugin code is not kept in this org; evidence is
captured in the knowledge base. This is a survey-class test: instead of one
game, the entire cross-section of a motion-software vendor's game support,
grouped by domain with deep dives where a game exposes something structurally
new.

## Read mechanisms (fragmentation census)

| Mechanism | Examples | OGSA-TS class |
|---|---|---|
| Game-native UDP | F1 2020–24 (116), GTA5 (20777), WhitewaterVR, Condor2, AeroFS2, FlyDangerous, AMS2 | documented game formats (tests 01–06) |
| Shared memory (MMF) | iRacing SDK, AC/ACC `Local\\acpmf_physics`, ManiaPlanet, RedOut, Subnautica (mod-written `yawmmfsn`) | documented formats; Subnautica needs a game-side mod — the sender-side plugin OGSA-TS generalizes |
| `ReadProcessMemory` | EliteDangerousPlugin | community memory offsets (test 07) |
| Game TCP API | NoLimits2 scripting telemetry | documented formats |

Seventy-two games, four transports, one consumer. Every plugin re-solves the
same problem with a different wire — the fragmentation OGSA-TS exists to end.

## Ecosystem findings

1. **The consumer API is indexed floats.** YawVR maps games via
   `SetInput(i, value)` over reflection field order — positional, semantic-free.
   The NoLimits2 game API emits a **native quaternion**; the plugin degrades it
   to Euler because the consumer API cannot accept one. OGSA-TS's
   `orientation: Quaternion` matches what games actually produce (NoLimits2,
   RedOut, VRaceHoverBike all ship quaternions) and what motion math consumes.
2. **Body-frame accel triples are the lingua franca**: F1
   (`gForceLateral/Longitudinal/Vertical`), NoLimits2 (`gforce xyz`), RedOut
   (`AccXYZ`). GravitreX ships accel **with and without gravity** — confirming
   specific force (accelerometer reading, gravity reaction included) and
   coordinate acceleration are genuinely distinct quantities; OGSA-TS keeps both
   (`bodyDynamics.specificForce` vs `kinematics.acceleration`).
3. **RedOut ships both frames** — `AccX/Y/Z` (body) *and* `AccWorldX/Y/Z`
   (world) — an existence proof that both OGSA-TS dynamics representations have
   real senders.
4. **Car-shaped fakery is systemic**: rpm/gear appear even in raft, hover and
   kart packets; F1 adds `onAsphalt` per wheel (a `ContactMedium` need) and
   `wheelSlip`.
5. **Event states are booleans in the wild**: IronRebellion
   `isHit/weaponFired/stomped/landed/jumped`, FlyDangerous boost states —
   event-rate data that rides OGSA-TS channels.

## Deep-dive mappings (structurally novel sources)

### NoLimits2 — roller coaster
- native quaternion → `orientation` (direct)
- `gforce x/y/z` → `bodyDynamics.specificForce` (direct)
- `speed` → `vehicle.speed`
- `type = other`, `typeLabel = "coaster"` (passenger ride, no drive points)
- **Verdict: covers.**

### IronRebellion — VR mech
- `rotationXYZ` → `orientation` (Euler recipe); `angularXYZ` →
  `bodyDynamics.angularVelocity`; `velocityXYZ` → body velocity →
  `kinematics.velocity` via orientation (recipe)
- `stompedFoot` (foot id) + `stomped` → per-leg drive points with
  `GenericState.engaged` — legs as generic drive points, exactly the
  multi-instance force case `GenericState.force` exists for
- `isFlying/isHit/weaponFired/landed/jumped/currentLean` → `mech.*` channels
- **Verdict: covers.**

### FlyDangerous — space flight racer
- `shipWorldPositionXYZ` → `kinematics.position` (direct — world position present)
- **trap**: `pitchPosition/rollPosition/yawPosition` are *control stick
  positions*, not attitude → `ctrl.*` channels, never `orientation`
- `gForce` is a magnitude (scalar) → channel; cannot feed `specificForce` (vector)
- `heightFromGround`, `altitude`, `underWater` → `env.*` channels
- **Verdict: covers; control-vs-attitude trap documented.**

### RedOut / VRaceHoverBike — antigrav racers
- `QuatX/Y/Z/W` → `orientation` (direct)
- `AccX/Y/Z` → `bodyDynamics.specificForce`; `AccWorldX/Y/Z` →
  `kinematics.acceleration` (both frames present — sender picks one per the
  dynamics rule, or alternates; receivers never need both)
- `collisionAngle` → `impact.*` channel; `angularSpeedX` → partial
  `angularVelocity` (X only)
- **Verdict: covers.**

### GravitreX — 2D balance
- `roll/RollSpeed/RollAcceleration` → `orientation` + `angularVelocity`
- `XAcceleration` (gravity-reaction variant) → `bodyDynamics.specificForce`
- **Verdict: covers.**

## Class reuse (already covered by earlier tests)

- **iRacing/ACC/AC** full-SDK MMF → test 01 class (kinematics + per-wheel)
- **EliteDangerousPlugin** `ReadProcessMemory` → test 07 class (accelerometer-grade, no pose)
- **WhitewaterVR** → test 09; **ETS2/Fernbus/FS19** truck/farm sims → car class with driver-input channels
- **Subnautica** — plugin reads a mod-written MMF (`InVehicle` + status): partial *by plugin design*; the game-side-mod pattern is the sender-side plugin OGSA-TS generalizes, not a schema matter

## Verdict

**Covers — no schema gaps across 72 games.** The batch adds coaster, mech,
space-racer, antigrav and 2D-balance domains to the validated set, and
delivers the strongest ecosystem evidence to date: quaternion-native game
outputs degraded to indexed floats, body-accel triples everywhere, and 72
bespoke readers for one consumer.

Validation set: **10 tests, 4 source classes, 80+ game outputs, zero open gaps.**
