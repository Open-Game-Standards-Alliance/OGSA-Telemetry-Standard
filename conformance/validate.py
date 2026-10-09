#!/usr/bin/env python3
"""validate.py — decode every conformance vector and assert the
manifest-declared semantics, independently of any reference SDK.

Uses pycapnp (official capnproto bindings) against ogsa_telemetry.capnp:
the schema and the corpus are validated by a third implementation, not
by the code that generated them. Exit 0 = all vectors verified.

Usage: python conformance/validate.py   (from the repo root)
"""
import json
import pathlib
import sys

import capnp  # pycapnp

HERE = pathlib.Path(__file__).parent
SCHEMA = HERE.parent / "ogsa_telemetry.capnp"
MANIFEST = HERE / "manifest.json"

PASS = FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    PASS, FAIL = PASS + ok, FAIL + (not ok)
    suffix = f" — {detail}" if (detail and not ok) else ""
    print(f"{'PASS' if ok else 'FAIL'} {name}{suffix}")


def load(vec_id):
    hex_ = "".join((HERE / "vectors" / f"{vec_id}.hex").read_text().split())
    blob = bytes.fromhex(hex_)
    assert blob[:4] == b"OMT1", "envelope magic"
    return blob[4], blob[8:]


frame_type_names = {0: "DiscoveryFrame", 1: "MotionFrame", 2: "EventFrame"}


def main():
    schema = capnp.load(str(SCHEMA))
    manifest = json.loads(MANIFEST.read_text())
    check("manifest schemaVersion 1", manifest["schemaVersion"] == 1)
    ids = [v["id"] for v in manifest["vectors"]]
    check("six known vectors", ids == [
        "discovery-minimal", "discovery-channels", "motion-pose",
        "motion-channels", "motion-multi", "event-impact"], str(ids))

    for vec_id in ids:
        ft, payload = load(vec_id)
        check(f"{vec_id} envelope",
              ft == expected_type[vec_id], f"frame type {ft}")
        cls = getattr(schema, frame_type_names[ft])
        with cls.from_bytes(payload) as msg:  # pycapnp wants a context manager
            check(f"{vec_id} semantics",
                  globals()["check_" + vec_id.replace("-", "_")](msg))


def check_discovery_minimal(d):
    return (d.schemaVersion == 1 and d.gameName == "conformance"
            and d.sessionStartUnixUs == 1_730_000_000_000_000
            and len(d.objects) == 1 and d.objects[0].name == "obj"
            and d.objects[0].primary
            and d.environment.airDensity == 1.25
            and d.environment.medium == "asphalt")


def check_discovery_channels(d):
    ch = list(d.objects[0].channels)
    return (d.objects[0].name == "demo_car"
            and d.objects[0].typeLabel == "conformance car"
            and len(ch) == 3
            and ch[0].name == "engine.rpm" and ch[0].unit == "rpm"
            and ch[0].range.min == 0 and ch[0].range.max == 9000
            and ch[1].name == "vehicle.speed" and ch[1].unit == "m/s"
            and ch[1].range.max == 30
            and ch[2].name == "lights.headlights" and ch[2].unit == "")


def check_motion_pose(m):
    o = m.objects[0]
    return (m.timestamp == 1.25 and o.name == "obj"
            and (o.position.x, o.position.y, o.position.z) == (1.5, 0.25, -3.75)
            and o.orientation.w == 1 and o.orientation.x == 0)


def check_motion_channels(m):
    o = m.objects[0]
    cv = {c.id: c.number for c in o.channels if c.which == "number"}
    return (m.timestamp == 2.5 and o.name == "demo_car"
            and o.orientation.y == 1
            and cv.get(0) == 3250.5 and cv.get(1) == 8
            and any(c.which == "boolean" and c.boolean for c in o.channels))


def check_motion_multi(m):
    return (m.timestamp == 3.75 and len(m.objects) == 2
            and m.objects[0].name == "player_car"
            and m.objects[0].position.x == 1
            and m.objects[1].name == "wingman"
            and (m.objects[1].position.y, m.objects[1].position.z) == (0.5, 2.5))


def check_event_impact(e):
    ev = e.events[0]
    return (e.timestamp == 0.125 and len(e.events) == 1
            and ev.id == 7 and ev.name == "body.impact"
            and ev.intensity == 0.75 and ev.duration == 0.25
            and ev.which == "direction"
            and (ev.direction.x, ev.direction.y, ev.direction.z) == (-1, 0, 0))


expected_type = {
    "discovery-minimal": 0, "discovery-channels": 0,
    "motion-pose": 1, "motion-channels": 1, "motion-multi": 1,
    "event-impact": 2,
}


if __name__ == "__main__":
    main()
    print(f"conformance: {PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
