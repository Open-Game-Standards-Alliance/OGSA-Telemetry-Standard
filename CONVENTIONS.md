# OGSA-TS Conventions (normative)

One closed set of conventions for every value on the wire. Schema field
comments, `CHANNELS.md` families, and per-game references cite these clauses
by number (`C-3`); nothing may contradict them. Adding or changing a clause
is a spec change (see DESIGN.md, Evolution).

## C-1 Frames

- **World frame** — left-handed, +Z forward, +Y up, +X right, meters,
  seconds.
- **Body frame** — the world frame rotated by the object's quaternion:
  x +right (sway), y +up (heave), z +forward (surge).
- **Object-local frame** — one sender-chosen origin per object (typically
  the CG), used by drive-point offsets and named points; declared via
  `referencePoint` + `namedPoints`.

## C-2 Orientation

Orientation is a unit quaternion (x/y/z/w). Senders normalize; receivers may
renormalize defensively. Either sign is the same rotation — receivers must
not prefer one sign. The quaternion rotates **world axes into body axes**.

## C-3 Units

SI base units everywhere, with one closed whitelist of declared exceptions:

| Quantity | Unit | Status |
|---|---|---|
| length, velocity, acceleration, force, pressure | m, m/s, m/s², N, **Pa** | SI |
| angles, angular rates | **rad**, **rad/s** | SI — never degrees |
| temperature | **°C** | declared exception |
| rotational speed | **rpm** | declared exception |
| normalized quantities | 0..1 (unipolar), −1..1 (bipolar) | unitless (`""`) |

Extending the whitelist is a spec change; a unit outside this table never
rides the wire. Channel `unit` strings use exactly these spellings
(`degC`, `rpm`, `Pa`, …). Receivers trust the declaration and never guess
units onto the wire.

## C-4 Rotation sign

Rotations follow the body axes of C-1: **+pitch = nose-up (about x),
+yaw = nose-right (about y), +roll = right-wing/ right-side down (about
z)**. In this left-handed frame, a positive rotation about an axis appears
clockwise when viewed looking along that axis. Every angular quantity on
the wire (angular velocity, Euler-derived angles, steering angles) uses
this same sense — positive steering turns the same direction as +yaw:
**positive = right**. Symmetric-pair deflections (wing flap) are positive
= tip up on either side.

## C-5 Control inputs

Driver/control input channels (`ctrl.*`) follow the same rule as C-4: a
positive input produces the positive rotation about the corresponding body
axis — `ctrl.elevator` + = nose-up, `ctrl.rudder` + = nose-right,
`ctrl.aileron` + = roll right-down, `ctrl.steering.angle` + = steering
right. Pedals/levers are 0..1 (C-3). Control inputs describe what the
*driver* did; effects on the vehicle live in schema fields or other
channels (C-6).

## C-6 Identity — what a value measures

A value lives on the physical object it is named for. Schema fields in a
`WheelState` describe that road wheel; `steerAngle` is the angle of that
wheel about its steer axis, **not** the handwheel (that is
`ctrl.steering.angle`). Anything measuring the driver's input is a `ctrl.*`
channel; anything measuring the vehicle's state is a schema field or
object/channel state. When a source mixes these (stick position vs.
orientation), senders resolve the identity before naming the value.

## C-7 Wind

`wind.*Direction` is the meteorological **from** convention, radians, in
the world frame of C-1 (direction from which the wind blows, measured as
yaw about +Y). Apparent-wind angles are relative to the object's nose,
**positive = from the right**. Wind vector components (`wind.x/y/z`) point
**toward** where the air moves, world frame (a vector, not a bearing).

## C-8 Timestamps

`MotionFrame.timestamp` is seconds since the session anchor
(`sessionStartUnixUs`, µs wall clock, from discovery). Timestamps are
monotonic within a session; a new anchor value declares a new session.

## C-9 Precision

All wire floats are Float32. World `position` assumes a session-stable
local origin: large-world senders re-origin on teleport/session start
rather than emitting absolute planetary coordinates. Geographic lat/lon
rides channels, where Float32 gives ~1 m precision at Earth magnitudes —
display-grade, not navigation-grade; senders needing more split degrees
from fractional degrees.

## C-10 Events

`EventFrame` carries discrete stimuli (impacts, gunfire, footsteps) for
haptic and cueing consumers. Each event carries a session-monotonic `id`;
the transport is lossy, so senders SHOULD re-carry recent events (~100 ms
window) and receivers MUST dedup by id. `intensity` is 0..1 normalized
(C-3). `duration` is seconds: 0 = momentary impulse, >0 = a sustain
window the consumer may render continuously. `direction` is optional,
in the body frame (C-1) of the associated object, and points **toward the
source** of the stimulus — a hit from the left has −x. Event names use
dot-namespaced strings ratified like channel names (CHANNELS.md).
