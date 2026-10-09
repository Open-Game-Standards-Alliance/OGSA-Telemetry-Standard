# Test 12: consumer documentation (FlyPT Mover — center of rotation)

Reviewed source: FlyPT Mover documentation ("Center of rotation —
Correcting the generated motion relative to the center of gravity",
operator-provided excerpt; captured in the knowledge base). First
consumer-side documentation source: the requirement is stated by rig
software, not extracted from a game.

## The requirement

Most games report motion referenced to the simulated vehicle's center of
gravity. The occupant sits at a lever arm from it (a commercial airliner
cockpit can be ~14 m ahead of the CG), so rotations about the CG produce
linear accelerations at the seat that the reported data does not contain.
Rig software corrects with the lever-arm terms:

    a_seat = a_ref + α × r + ω × (ω × r),   r = seat − reference

Today the reference point is **guessed per game by the user** (games
silently differ: CG, model origin, pilot camera). The sender cannot apply
the correction — the target point (rig pivot, head position, which seat)
is consumer-specific. The consumer cannot apply it without knowing the
sender's reference. This is exactly the class of silent-contract problem a
standard exists to fix.

## OGSA-TS mapping

| FlyPT concept | OGSA-TS destination |
|---|---|
| data referenced to CG | `ObjectDescriptor.referencePoint` (declared `NamedPoint`; default = object-local frame origin (typically the CG)) |
| occupant ~14 m ahead of CG | consumer-side: lever arm to its own pivot/head, optionally using declared `namedPoints` (`pilot`, `driverEye`, seats) |
| center-of-rotation correction math | consumer-side (cueing software's layer); OGSA-TS transports the declared reference and named points |
| per-game guessing of the reference | gone — declared once in discovery, re-sent on vehicle change |

`NamedPoint` = name + vehicle-local position (meters, orientation axes).
Conventional names: `cg`, `pilot`, `driverEye`. Discovery-level metadata:
zero per-tick cost, additive to v1.

## Verdict

**Requirement adopted** — `referencePoint` + `namedPoints` close the silent
contract; the correction itself stays consumer-side by design. No
per-frame cost.

Validation set: **12 tests, 6 source classes (formats, RE offsets,
vendor-encapsulated, game-native UDP, injection, consumer docs), 100+ game
outputs, zero open gaps.**
