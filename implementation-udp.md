# UDP Implementation

The LTS transport is **plain UDP multicast**. At 60–120 Hz with sub-500-byte packets on a LAN or localhost, transport latency is a few hundred microseconds at most — negligible next to the game physics tick, motion cueing filters, and actuator response. A high-performance messaging layer would add a media driver process and client library to every integration for performance this use case cannot use. Plain UDP is trivial to ship in engine plugins and supports multicast, so multiple clients (dashboards, motion rigs, haptics, loggers) receive the same stream without extra ports or proxying.

Cap'n Proto handles serialization (see [implementation-capnproto.md](implementation-capnproto.md)). An optional Aeron backend exists for extreme-rate scenarios (see the last section).

## Wire format

Each UDP datagram is an 8-byte envelope followed by one Cap'n Proto message:

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | Magic `OMT1` — protocol id + wire-format version |
| 4 | 1 | Frame type: `0x00` = `DiscoveryFrame`, `0x01` = `MotionFrame`, `0x02` = `EventFrame` |
| 5 | 3 | Reserved — send 0, ignore on receive |
| 8 | … | Cap'n Proto message (already word-aligned — readable in place) |

Receivers check the magic and silently skip foreign packets (the multicast group may be shared). Datagrams stay well under a UDP MTU (see [implementation-capnproto.md](implementation-capnproto.md)).

## Event frames

`EventFrame`s are sent on demand (irregular cadence, often bursty) and
carry discrete stimuli — impacts, gunfire, footsteps — for haptic and
cueing consumers (CONVENTIONS C-10). Because the transport is lossy and
an event must not be silently missed, senders SHOULD re-carry recent
events in subsequent `EventFrame`s for ~100 ms (or until the next frame
if quieter); receivers MUST dedup by the session-monotonic `id`. Events
are self-contained (intensity, duration, optional body-frame direction),
so a late-joined receiver misses only events from before it joined —
by design, as with motion.

Event frames are auxiliary: they do not count as the heartbeat and do
not participate in liveness detection; motion frames remain the sole
liveness signal.

## Default endpoint

| Setting | Value | Notes |
|---|---|---|
| Multicast group | `239.255.17.17` | Organization-local scope; avoids link-local reserved ranges |
| Port | `40123` | |
| TTL | 1 | Local network only |
| Unicast alternative | `127.0.0.1:40123` | Single-client setups and testing |

All values are defaults — every implementation should make endpoint and mode configurable.

## Send cadence

| Frame | When to send |
|---|---|
| `DiscoveryFrame` | session start, on any declared change (vehicle swap, channel set change, medium change), and **re-sent every 2 seconds** |
| `MotionFrame` | every telemetry tick, ~60 Hz |

The 2-second discovery re-send bounds late-joiner wait time at ~1.6 kbit/s of extra traffic — negligible, and it heals any lost discovery packet. Motion frames are fire-and-forget: receivers hold the last known pose and interpolate across occasional loss.

## Sender (game side)

```cpp
#include "open_motion_telemetry.capnp.h"
#include <capnp/message.h>
#include <capnp/serialize.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>

class UdpTelemetrySender {
public:
    UdpTelemetrySender(const char* group = "239.255.17.17", uint16_t port = 40123) {
        fd_ = socket(AF_INET, SOCK_DGRAM, 0);

        // Local network only
        unsigned char ttl = 1;
        setsockopt(fd_, IPPROTO_IP, IP_MULTICAST_TTL, &ttl, sizeof(ttl));

        // Enable loopback so dashboards on the same machine see the stream
        unsigned char loop = 1;
        setsockopt(fd_, IPPROTO_IP, IP_MULTICAST_LOOP, &loop, sizeof(loop));

        addr_.sin_family = AF_INET;
        addr_.sin_port = htons(port);
        addr_.sin_addr.s_addr = inet_addr(group);
    }

    void sendDiscovery() {
        // buildDiscovery() as shown in implementation-capnproto.md
        send(0x00, buildDiscovery());
    }

    void sendMotion(double timestampSeconds) {
        // buildMotion() as shown in implementation-capnproto.md
        send(0x01, buildMotion(timestampSeconds));
    }

private:
    void send(uint8_t frameType, kj::Array<capnp::word> words) {
        uint8_t buf[1400];
        std::memcpy(buf, "OMT1", 4);          // magic + wire version
        buf[4] = frameType;
        buf[5] = buf[6] = buf[7] = 0;         // reserved
        size_t payload = words.size() * sizeof(capnp::word);
        std::memcpy(buf + 8, words.begin(), payload);
        sendto(fd_, buf, 8 + payload, 0,
               reinterpret_cast<sockaddr*>(&addr_), sizeof(addr_));
    }

    int fd_;
    sockaddr_in addr_{};
};

int main() {
    UdpTelemetrySender sender;
    sender.sendDiscovery();

    double t = 0.0;
    int tick = 0;
    while (true) {
        sender.sendMotion(t);
        t += 1.0 / 60.0;
        if (++tick % 120 == 0)                // discovery re-send every 2 s
            sender.sendDiscovery();
        usleep(16667);                        // ~60 Hz
    }
}
```

## Receiver (motion software side)

```cpp
#include "open_motion_telemetry.capnp.h"
#include <capnp/message.h>
#include <capnp/serialize.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unordered_map>

class UdpTelemetryReceiver {
public:
    UdpTelemetryReceiver(const char* group = "239.255.17.17",
                         uint16_t port = 40123) {
        fd_ = socket(AF_INET, SOCK_DGRAM, 0);

        // Multiple subscribers may live on the same host
        int reuse = 1;
        setsockopt(fd_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
#ifdef SO_REUSEPORT
        setsockopt(fd_, SOL_SOCKET, SO_REUSEPORT, &reuse, sizeof(reuse));
#endif

        sockaddr_in local{};
        local.sin_family = AF_INET;
        local.sin_port = htons(port);
        local.sin_addr.s_addr = htonl(INADDR_ANY);
        bind(fd_, reinterpret_cast<sockaddr*>(&local), sizeof(local));

        ip_mreq mreq{};
        mreq.imr_multiaddr.s_addr = inet_addr(group);
        mreq.imr_interface.s_addr = htonl(INADDR_ANY);
        setsockopt(fd_, IPPROTO_IP, IP_ADD_MEMBERSHIP, &mreq, sizeof(mreq));
    }

    // Call from your main loop; returns true when a frame was processed.
    bool poll() {
        uint8_t buf[1400];
        ssize_t n = recv(fd_, buf, sizeof(buf), MSG_DONTWAIT);
        if (n < 9) return false;                          // nothing / runt
        if (std::memcmp(buf, "OMT1", 4) != 0) return false; // foreign packet

        // Payload starts at offset 8 — already word-aligned, readable in place
        size_t wordCount = (n - 8 + 7) / 8;
        kj::ArrayPtr<const capnp::word> words(
            reinterpret_cast<const capnp::word*>(buf + 8), wordCount);
        ::capnp::FlatArrayMessageReader message(words);

        switch (buf[4]) {
            case 0x00: return onDiscovery(message.getRoot<DiscoveryFrame>());
            case 0x01: return onMotion(message.getRoot<MotionFrame>());
        }
        return false;
    }

private:
    bool onDiscovery(DiscoveryFrame::Reader d) {
        // (Re)build the id -> descriptor tables: channel names/units/ranges,
        // drive-point geometry, environment. Idempotent — a re-sent
        // discovery simply overwrites. If the primary object's ObjectType
        // changed (player entered a vehicle/aircraft), switch the cueing
        // preset — discovery re-sends are the within-game auto-switching
        // signal.
        channelNames_.clear();
        for (ObjectDescriptor::Reader obj : d.getObjects())
            for (ChannelDescriptor::Reader ch : obj.getChannels())
                channelNames_[ch.getId()] = ch.getName().cStr();
        return true;
    }

    bool onMotion(MotionFrame::Reader f) {
        for (MotionObject::Reader obj : f.getObjects()) {
            // obj.getPosition(), obj.getOrientation() …
            // Derive velocity/acceleration from pose deltas when absent.
            // If a descriptor declared a range, drop out-of-range values.
        }
        return true;
    }

    int fd_;
    std::unordered_map<uint16_t, std::string> channelNames_;
};
```

## Liveness and session end

The sender gives no explicit goodbye, so receivers detect liveness from
the stream itself:

- Motion frames are the heartbeat. If no motion frame arrives for ~5×
  the expected tick interval (or 1 s when the rate is unknown), mark the
  session stale: hold the last pose, stop driving actuators toward new
  targets, and surface the state in UI.
- Discovery re-sends (every 2 s) confirm session identity; a discovery
  frame with a new `sessionStartUnixUs` is a new session — reset state.
- After 10 s with no frame of any type, treat the session as ended and
  release per-sender resources.

## Engine integration (Unity / Unreal / Godot)

The schema and wire format are engine-agnostic; the integration path is a
small plugin embedding the C API below. Language support: **C++** (Unreal,
Godot GDExtension) is first-class for Cap'n Proto; **C#** (Unity, Godot) is
usable via Cap'n Proto C# bindings or by binding the C API in a native
plugin; **GDScript** should call the exposed plugin API rather than
re-implement serialization.

- **Unreal (C++)**: pre-generated Cap'n Proto sources compile into a module;
  wrap the C API in Blueprint-callable functions (e.g. a Blueprint Function
  Library) so visual scripting can set pose, drive points, and channels.
- **Unity (C#)**: bind the C API in a native plugin (or use Cap'n Proto C#
  bindings) and expose a manager component; the UDP sender is a plain
  `UdpClient`.
- **Godot**: a GDExtension (C++) wraps the C API natively; C# builds can use
  the same bindings as Unity.

Every reference plugin ships with:

1. **Pre-generated Cap'n Proto code** — no schema compiler step at game-dev
   time; the plugin is drop-in.
2. **A thin UDP sender** — endpoint, port, and send rate configurable;
   sensible defaults (see [Default endpoint](#default-endpoint)).
3. **Field-level toggles** — games start with the pose core only and enable
   drive points/channels as needed.
4. **Blueprint / visual-scripting friendly wrappers** — setting position or
   a channel is one node call.

Start minimal: a game streaming position/orientation per tick is fully
compliant and useful (~68 bytes/frame) — see "The minimal sender" in
[implementation-capnproto.md](implementation-capnproto.md).

Operational notes:

- **Socket hygiene**: send from one dedicated thread or the engine's network
  tick; never block the render or physics thread on socket calls.
- **Windows Firewall**: the first multicast send may prompt — document it for
  end users.

## Transport abstraction and the high-level C API

For game integration, the transport is abstracted behind a C++ `Transport` base class (`UdpTransport` is the reference implementation), and the whole system — discovery bookkeeping, serialization, envelope framing, derived values — is exposed through a simple C API in `motion_telemetry.h`.

```cpp
class Transport {
public:
    virtual ~Transport() = default;
    virtual void publishDiscovery() = 0;   // builds + sends the DiscoveryFrame
    virtual void send() = 0;               // sends one MotionFrame tick
    virtual void registerCallback(TelemetryCallback callback) = 0;
    virtual void startReceiving() = 0;
    // … per-field setters for pose, drive points, and channels
};
```

The C API hides both layers from game code:

```c
typedef struct MotionTelemetryHandle MotionTelemetryHandle;
typedef void (*TelemetryCallback)(void* userData);

// Lifecycle — transportType: "udp" (default) or "aeron"
MotionTelemetryHandle* motion_telemetry_create_sender(const char* transportType, const char* endpoint, int port);
MotionTelemetryHandle* motion_telemetry_create_receiver(const char* transportType, const char* endpoint, int port);
void motion_telemetry_destroy(MotionTelemetryHandle* handle);

// Declaring the session (feeds the DiscoveryFrame; call before send loop)
void motion_telemetry_set_game_name(MotionTelemetryHandle* handle, const char* name);
int  motion_telemetry_declare_drive_point(MotionTelemetryHandle* handle, const char* objectName, const char* pointName, const char* type);
int  motion_telemetry_declare_channel(MotionTelemetryHandle* handle, const char* objectName, const char* channelName, const char* unit, double min, double max);
void motion_telemetry_publish_discovery(MotionTelemetryHandle* handle);   // also re-sends on change; periodic re-send is automatic

// Per-tick data (feeds the MotionFrame)
void motion_telemetry_set_position(MotionTelemetryHandle* handle, float x, float y, float z);
void motion_telemetry_set_orientation(MotionTelemetryHandle* handle, float fx, float fy, float fz, float ux, float uy, float uz);
void motion_telemetry_set_drive_point_number(MotionTelemetryHandle* handle, const char* pointName, const char* field, float value);
void motion_telemetry_set_channel_number(MotionTelemetryHandle* handle, const char* channelName, float value);
void motion_telemetry_set_channel_boolean(MotionTelemetryHandle* handle, const char* channelName, int value);
void motion_telemetry_send(MotionTelemetryHandle* handle);

// Receiving (callback fires on new motion frames; discovery is handled internally)
void motion_telemetry_register_callback(MotionTelemetryHandle* handle, TelemetryCallback callback, void* userData);
void motion_telemetry_start_receiving(MotionTelemetryHandle* handle);

// Getters, including derived values the library computes from pose deltas
float motion_telemetry_get_velocity_x(MotionTelemetryHandle* handle);   // …_y, …_z
float motion_telemetry_get_acceleration_x(MotionTelemetryHandle* handle); // …_y, …_z
const char* motion_telemetry_get_channel_unit(MotionTelemetryHandle* handle, const char* channelName);
```

A sender loop is then just: declare once → `publish_discovery()` → set fields → `send()` at 60 Hz. Receivers register a callback and read raw and derived values through getters; channel names, units, and ranges arrive via discovery and are queryable by name.

## Optional Aeron backend

An `AeronTransport` implementing the same `Transport` interface sends the identical envelope bytes on two Aeron streams (`1000` discovery, `1001` motion) of a single channel, so receiver-side parsing is unchanged. It pulls ahead of plain UDP only when you need extreme message rates, strict ordering under heavy load, or back-pressure management across many subscribers — none of which are typical for game → motion software telemetry. See the [Aeron project](https://github.com/real-logic/aeron) if your deployment needs it; the default UDP path needs nothing beyond a socket.
