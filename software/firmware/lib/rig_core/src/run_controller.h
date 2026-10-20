// Run state machine: one timed run of one condition (A solo, B solo, A + B).
// Hardware is reached only through the interfaces below, so the logic is
// unit tested on a PC against fakes.
// Author: Jessica
#pragma once

#include "protocol.h"
#include "rig_types.h"

namespace rig {

class SensorBank {
public:
    virtual ~SensorBank() = default;
    virtual bool stopRanging(uint8_t s) = 0;               // stop, then clear the interrupt
    virtual bool clearInterrupt(uint8_t s) = 0;
    virtual bool startRanging(uint8_t s) = 0;              // clear the interrupt, then start
    virtual bool readResult(uint8_t s, Reading &r) = 0;    // read, clear interrupt, set tReadUs
    virtual bool interruptIdle(uint8_t s) = 0;             // GPIO1 line at its inactive level
    virtual uint32_t busErrorCount() const = 0;            // monotonically increasing
};

class EdgeSource {
public:
    virtual ~EdgeSource() = default;
    virtual bool takeEdge(uint8_t s, uint64_t &tUs) = 0;   // pop a pending edge
    virtual uint32_t edgeCount(uint8_t s) const = 0;       // since reset()
    virtual uint32_t overrunCount(uint8_t s) const = 0;    // edge while one was pending
    virtual void reset() = 0;
};

class Clock {
public:
    virtual ~Clock() = default;
    virtual uint64_t nowUs() const = 0;
    virtual void delayMs(uint32_t ms) = 0;
};

class RunSink {
public:
    virtual ~RunSink() = default;
    virtual void onReading(const char *runId, const Reading &r) = 0;
    virtual void onRunEnd(const RunSummary &s) = 0;
};

enum class StartResult { Ok, Busy, Bus, IntStuck };

class RunController {
public:
    // A participating sensor that stays silent this many inter-measurement
    // periods aborts the run: its interrupt wire or the sensor has failed.
    static constexpr uint32_t kSilentPeriods = 5;
    // Consecutive failed result reads before the run is aborted.
    static constexpr uint32_t kMaxConsecutiveReadErrors = 3;

    RunController(SensorBank &bank, EdgeSource &edges, Clock &clock, RunSink &sink)
        : bank_(bank), edges_(edges), clock_(clock), sink_(sink) {}

    // Stops everything, checks the interrupt lines are idle, then starts the
    // sensors that take part. `stuckSensor` names the offending sensor on
    // IntStuck. The caller has already applied `settings` to both sensors.
    StartResult start(const RunRequest &req, const SensorSettings &settings, uint8_t *stuckSensor = nullptr);

    void poll();                       // service edges, enforce checks, end on time
    void abort(AbortReason reason);    // no-op when idle
    bool running() const { return running_; }
    const char *runId() const { return summary_.id; }

private:
    void finish(AbortReason reason);
    bool stopAll();

    SensorBank &bank_;
    EdgeSource &edges_;
    Clock &clock_;
    RunSink &sink_;

    bool running_ = false;
    RunSummary summary_;
    uint64_t endUs_ = 0;
    uint64_t silentLimitUs_ = 0;
    uint64_t lastEdgeUs_[kNumSensors] = {0, 0};
    uint32_t consecutiveReadErrors_ = 0;
    uint32_t busErrors0_ = 0;
};

}  // namespace rig
