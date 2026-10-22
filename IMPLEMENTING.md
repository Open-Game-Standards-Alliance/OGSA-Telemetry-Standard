# Implementing OGSA-TS

The single path from zero to a conformant sender or receiver — for any
language, any engine (including your own). Everything normative lives in
this repo; the reference implementations and engine plugins are siblings.

## Read in this order

1. [README](README.md) — what the standard is and is not
2. [CONVENTIONS.md](CONVENTIONS.md) — units, world frame, quaternion
   policy, signs, timestamps. **Read before writing any value.** The
   world frame is left-handed, +Z forward, +Y up, metres; rotations are
   radians; channel units are SI plus a closed whitelist
3. [ogsa_telemetry.capnp](ogsa_telemetry.capnp) — the schema (single
   source of truth). It is self-contained: feed it to any Cap'n Proto
   toolchain
4. [implementation-udp.md](implementation-udp.md) — the 8-byte `OMT1`
   envelope, multicast group/port, TTL, liveness rules
5. [implementation-capnproto.md](implementation-capnproto.md) — schema
   usage and the canonical message framing note
6. [CHANNELS.md](CHANNELS.md) — ratified channel names with required
   units. Use them when the concept matches; never re-unit a ratified name

## The minimum conformant sender

1. **Discovery** — one `DiscoveryFrame` at session start, re-sent every
   ~2 s (late joiners) and whenever anything it declares changes. It must
   declare your primary object and every channel you stream, with ids
   that stay stable for the session
2. **Motion** — `MotionFrame`s at your telemetry rate (60–120 Hz
   typical): object name, position + unit quaternion in the CONVENTIONS
   world frame, channel values keyed by discovery ids
3. **Events (optional)** — `EventFrame`s on gameplay stimuli, re-carried
   ~100 ms for loss tolerance, session-monotonic ids
4. **Envelope** — every datagram is `OMT1` + frame-type byte + reserved
   zeros, then the canonical Cap'n Proto message (single segment is fine)
5. **Transport** — UDP multicast, default group `239.255.17.17:40123`,
   TTL 1 (local subnet)

That's the whole contract. Receivers additionally apply the liveness and
dedup rules in implementation-udp.md.

### Naming: gameName and object names

`gameName` identifies the session's source on receiver UIs and in
per-game state (channel mappings, profiles), so senders SHOULD use the
engine's product/project name when one is available (`Application.productName`,
`FApp::GetProjectName()`, …) rather than a process/executable name; if only
the executable is available, strip pack/build tokens ("Game-Win64-Shipping"
→ "Game"). Users can always override via sender config.

Object `name` is the identity receivers match motion frames to discovery
by — it MUST stay stable for the session. Senders that track a
runtime-discovered object (an injected mod following the local pawn)
SHOULD keep a stable role name ("player") and surface what is actually
being tracked in `typeLabel`, updated by a discovery re-send when it
changes (possession, vehicle swap). Raw instance names (UE
"BP_Foo_C_3", Unity "Player (2)") are not stable — strip the instance
suffix before putting them on the wire.

### Receiver profile selection

Motion software that lets users tune rig response selects profiles along
a three-level cascade over discovery, most to least specific:

1. `gameName` — per-game profile (channel mappings, cueing defaults)
2. the primary object's `ObjectType` — cueing preset per class (car vs
   aircraft vs watercraft vs on-foot humanoid)
3. the primary object's `typeLabel` — per-vehicle refinement, when a user
   wants one specific machine to respond differently from its class

Each level falls back to the one above it when nothing matches.
`typeLabel` is sender-chosen free text: receivers match it exactly
(case-sensitive equality), never fuzzily — an absent or unmatched label
simply keeps the `ObjectType` preset. The switch signal is discovery
itself: a vehicle swap re-sends discovery immediately (the ~2 s periodic
re-send heals a lost one), so profile swaps land in realtime while the
motion stream never changes shape.

## Game-native units (bind-path conversions)

The wire speaks C-3 units only. Games rarely do. The engine SDKs'
bind path converts game-native readings to the channel's declared unit
at bind time — a factor precomputed once, then one multiply per sample.
The shared conversion set, kept identical across the reference
implementations:

| Quantity | Source (game-native) | Target (wire) | Factor |
|---|---|---|---|
| speed | km/h | m/s | ÷3.6 |
| speed | mph | m/s | ×0.44704 |
| speed | ft/s | m/s | ×0.3048 |
| speed | kn | m/s | ×1852/3600 |
| length | ft | m | ×0.3048 |
| angle | deg | rad | ×π/180 |
| angular rate | deg/s | rad/s | ×π/180 |
| rotation rate | rps | rpm | ×60 |
| acceleration | g | m/s² | ×9.80665 |
| acceleration | ft/s² | m/s² | ×0.3048 |
| pressure | bar | Pa | ×10⁵ |
| pressure | psi | Pa | ×6894.757293168361 |
| pressure | kPa | Pa | ×1000 |
| mass | g | kg | ×10⁻³ |
| ratio | % | (unitless) | ×10⁻² |
| temperature | °F | °C | (v−32)×5/9 |

This set is implementation guidance, not a clause: nothing here rides
the wire. Source units are never declared on a channel — a channel whose
name matches a ratified CHANNELS.md entry uses that entry's unit exactly.
Readings outside the set convert inside the getter; an unknown pair
fails the bind rather than guessing a factor onto the wire.
Implementations that extend the set keep it identical across engines —
the reference suites verify it (dotnet conversion tests; UE
`OgsaConversionTestActor` on the wire; Godot `ConformanceCheck`).

### Native angular velocity (component sense)

Engines that expose a measured angular velocity (Unity
`Rigidbody.angularVelocity`, Unreal `GetAngularVelocityRadPerSecond`,
PhysX `readAngularVelocity`) report it in the engine's *stored-Hamilton*
component sense, which differs from C-4 on two of three axes: a positive
stored rotation about +y is nose-right (matches C-4 +yaw), but about +x it
tilts the nose down and about +z it rolls left-side-down. Senders that
bind native rates instead of deriving them from pose deltas must

1. rotate the world-frame reading into the body frame (the inverse of the
   reported orientation), then
2. map components as **(−x, +y, −z)** onto C-4.

The derivation and its receiver-side anchors live in the reference
implementations' `BodyDynamicsDeriver` (dotnet/Unity/Godot share the C#
class; UE has the C++ twin). Getting this wrong inverts pitch and roll
cues silently — prefer the shared helper over hand-mapping.

## Validate against the conformance corpus

[`conformance/`](conformance/) holds golden datagrams (envelope included)
plus a semantic manifest. Two checks, either or both:

- **Decode**: parse each `.hex` and compare against the manifest — proves
  your reader
- **Encode**: build each manifest input and byte-compare with the `.hex` —
  proves your writer

All corpus floats are float32-exact, so comparisons need no epsilon.

Instant sanity check with the official tool. Note the `.hex` files are
text: the 8-byte envelope is 16 hex characters, so strip from character
17 (not byte 9):

```bash
tail -c +17 conformance/vectors/motion-pose.hex | xxd -r -p \
  | capnp decode ogsa_telemetry.capnp MotionFrame
```

(No `capnp` CLI handy? The same check in Python: `pip install pycapnp`,
then `capnp.load("ogsa_telemetry.capnp").MotionFrame.from_bytes(
bytes.fromhex(open("conformance/vectors/motion-pose.hex").read().strip()[16:]))`
— use it as a context manager.)

## Fastest paths by engine

| Situation | Start from |
|---|---|
| **Custom .NET engine** (MonoGame, Stride, FNA, bespoke) | [`ogsa-ts-dotnet`](https://github.com/Open-Game-Standards-Alliance/ogsa-ts-dotnet) — `Ogsa.Telemetry` is engine-agnostic by design; the Unity and Godot plugins are thin wrappers over it |
| **Custom C++ engine** | [`ogsa-ts-unreal/Source/OgsaTelemetryCore`](https://github.com/Open-Game-Standards-Alliance/ogsa-ts-unreal) — std-only, zero dependencies, byte-exact against the corpus; vendor it and add your socket + glue |
| **Any other language** | The schema + this page + any official capnp implementation (C++, Rust, Go, Python, Java, JS…) — the wire is canonical Cap'n Proto |
| **Unity / Unreal / Godot** | The engine plugins ([ogsa-ts-unity](https://github.com/Open-Game-Standards-Alliance/ogsa-ts-unity), [ogsa-ts-unreal](https://github.com/Open-Game-Standards-Alliance/ogsa-ts-unreal), [ogsa-ts-godot](https://github.com/Open-Game-Standards-Alliance/ogsa-ts-godot)) — wired and validated |

Reference receiver for testing your sender:
[`ogsa-ts-dotnet`](https://github.com/Open-Game-Standards-Alliance/ogsa-ts-dotnet) → `dotnet run --project src/TelemetryReceive`.
