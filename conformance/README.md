# Conformance corpus

Golden OGSA-TS datagrams + a semantic manifest, generated deterministically
by the reference implementation (`ogsa-ts-dotnet`, `src/ConformanceGen`).
Every engine implementation (Unity, Godot, UE, …) validates against this
corpus so their encoders provably agree on the wire.

## Files

- `manifest.json` — per-vector semantics: frame type, description, and the
  `input` object (the semantic content; serves as encode source **and**
  decode expectation)
- `vectors/<id>.hex` — the raw datagram **including the 8-byte `OMT1`
  envelope**, lowercase hex wrapped at 64 characters

All floats in the corpus are **float32-exact** — implementations compare
exactly, no epsilon.

## Vectors

| id | covers |
|---|---|
| `discovery-minimal` | smallest valid DiscoveryFrame (one primary object) |
| `discovery-channels` | channels with units, ranges, unitless boolean |
| `motion-pose` | pose core: position + identity quaternion |
| `motion-channels` | pose + number/boolean channel values by discovery id |
| `motion-multi` | two objects, primary first |
| `event-impact` | `body.impact` with intensity, duration, direction |

## Using the corpus

- **Decode direction (receivers)**: parse each `.hex`, decode, compare
  against the manifest `input`. Guarded continuously by
  `Ogsa.Telemetry.Tests.ConformanceVectorTests`.
- **Encode direction (senders)**: build each frame from the manifest
  `input` and byte-compare with the `.hex` file.

## Regeneration

```bash
cd ogsa-ts-dotnet
dotnet run --project src/ConformanceGen [outputDir]
```

Regeneration is **deterministic**: with unchanged schema and serializer,
`git diff` after regenerating must be empty. If bytes change, the change
is a wire-format change — review it as such, then regenerate as part of
that change. Schema evolution rules (unknown-field skipping) mean additions
usually alter vectors legitimately: regenerate, review the diff, and note
the corpus version bump.
