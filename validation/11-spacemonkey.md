# Test 11: middleware survey (SpaceMonkey, injected providers + Dirt-4 carrier)

Reviewed source: SpaceMonkey (PHARTGAMES), an open-source telemetry provider
for ~24 games with no native telemetry support. Code is not kept in this
org; evidence is captured in the knowledge base. This is a survey-class test
of a new source class and two architectural findings.

## New source class: injected providers (5th class)

Extraction happens by **code injection**: Unity games get a MonoBehaviour
exporter DLL injected via SharpMonoInjector; any Unreal game can ride UEVR
(praydog's universal injector) for camera-derived motion; native formats
(BeamNG, DCS, WRC, IL-2 …) are read directly; Squadrons is offset-scanned
and currently **broken** ("requires pointer change") — the maintenance tax
of offset-scanning, confirming test 07. The Overload exporter reads the
player `transform.position` and native Unity `Quaternion rotation`, sends
UDP to the host, and **derives velocity by finite differences** — the
derive-kinematics-from-pose recipe, running in the wild.

## Finding: de-facto carrier (Dirt 4 custom UDP)

SpaceMonkey's output layer *emulates the Codemasters Dirt 4 custom UDP
packet* so that "any software that already supports Dirt 4" can consume it
(Sim Racing Studio, SimCommander 4, SimFeedback listed as tested). The
ecosystem already converged on the one-standard-everyone-speaks solution —
but chose a **game's car-shaped format** as the carrier
(`suspension_position/velocity` per wheel, `pitchDeg/yawDeg/rollDeg`,
rpm/gear), so every non-car game (VTOL VR, Squadrons, IL-2, Overload's 6DoF
ship, Cyberpunk via UEVR) is squeezed through a car's wire shape. That is
the compatibility-fakery pattern from test 09, elevated to an
architecture: OGSA-TS is the neutral carrier the ecosystem converged toward
without designing.

## Finding: fwd/up precedent and the OpenMotion name

SpaceMonkey's internal frame (`SpaceMonkeyTelemetryFrameData` /
`OpenMotionAPI`) is `world position + fwd/up vector pair + idleRPM/maxRPM/
rpm/gear/inputs`. Two consequences:

- the forward/up orientation design exists in the wild, but alongside
  mandatory car fields — the car-shaped-mandatory-core anti-pattern OGSA-TS
  avoids (optionality via union, not required engine fields); engine data
  rides channels. The quaternion decision stands (engine-native rotations
  are quaternions — Unity here; NoLimits2/RedOut in test 10; consumers are
  quaternion-native).
- **naming collision**: an "OpenMotionAPI" already exists in this exact
  domain. The OGSA-TS public name needs a distinctness check before v1.0.

## Mapping

| SpaceMonkey element | OGSA-TS destination | Class |
|---|---|---|
| internal `pos` + `fwd/up` pair | `kinematics.position` + `orientation` (basis→quaternion recipe) | direct/recipe |
| exporter-derived velocity | `kinematics.velocity` (already their method) | direct |
| CM carrier `pitchDeg/yawDeg/rollDeg` | `orientation` (Euler→quat) | recipe |
| CM carrier per-wheel suspension pos/vel | `WheelState.compression/velocity` ×4 | direct |
| `rpm/gear/inputs` | `engine.rpm`, `gear`, `ctrl.*` channels | direct |
| Kalman/median/high-pass/noise/smooth filters | consumer-side middleware — **not OGSA-TS's layer** (transport stays thin; filters are exactly the kind of consumer that reads OGSA-TS) | note |
| MMF output alternative | OGSA-TS UDP multicast is the transport analog | note |

## Verdict

**Covers — no schema gaps; one naming risk raised** (OpenMotionAPI
collision → check public name before v1.0). Adds the 5th source class
(injected providers incl. universal engine injection) and the strongest
architectural evidence yet: the ecosystem converged on a single carrier by
emulating a car game's format.

Validation set: **11 tests, 5 source classes, 100+ game outputs, zero open
gaps.**
