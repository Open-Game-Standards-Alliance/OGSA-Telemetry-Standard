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

## Validate against the conformance corpus

[`conformance/`](conformance/) holds golden datagrams (envelope included)
plus a semantic manifest. Two checks, either or both:

- **Decode**: parse each `.hex` and compare against the manifest — proves
  your reader
- **Encode**: build each manifest input and byte-compare with the `.hex` —
  proves your writer

All corpus floats are float32-exact, so comparisons need no epsilon.

Instant sanity check with the official tool (strip the 8-byte envelope
first):

```bash
tail -c +9 conformance/vectors/motion-pose.hex | xxd -r -p \
  | capnp decode -s ogsa_telemetry.capnp MotionFrame
```

## Fastest paths by engine

| Situation | Start from |
|---|---|
| **Custom .NET engine** (MonoGame, Stride, FNA, bespoke) | [`ogsa-ts-dotnet`](../ogsa-ts-dotnet) — `Ogsa.Telemetry` is engine-agnostic by design; the Unity and Godot plugins are thin wrappers over it |
| **Custom C++ engine** | [`ogsa-ts-unreal/Source/OgsaTelemetryCore`](../ogsa-ts-unreal) — std-only, zero dependencies, byte-exact against the corpus; vendor it and add your socket + glue |
| **Any other language** | The schema + this page + any official capnp implementation (C++, Rust, Go, Python, Java, JS…) — the wire is canonical Cap'n Proto |
| **Unity / Unreal / Godot** | The engine plugins ([ogsa-ts-unity](../ogsa-ts-unity), [ogsa-ts-unreal](../ogsa-ts-unreal), [ogsa-ts-godot](../ogsa-ts-godot)) — wired and validated |

Reference receiver for testing your sender:
`ogsa-ts-dotnet` → `dotnet run --project src/TelemetryReceive`.
