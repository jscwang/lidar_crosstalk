// Author: Jessica
#include "run_controller.h"

#include <string.h>

namespace rig {

bool RunController::stopAll() {
    bool ok = true;
    for (uint8_t s = 0; s < kNumSensors; ++s) ok &= bank_.stopRanging(s);
    return ok;
}

StartResult RunController::start(const RunRequest &req, const SensorSettings &settings, uint8_t *stuckSensor) {
    if (running_) return StartResult::Busy;

    // A sensor that is still ranging keeps emitting even if deselected on the
    // mux, so both are stopped explicitly. A measurement already in flight
    // may still complete, so wait one timing budget before clearing.
    if (!stopAll()) return StartResult::Bus;
    clock_.delayMs(settings.timingBudgetMs + 5u);
    for (uint8_t s = 0; s < kNumSensors; ++s)
        if (!bank_.clearInterrupt(s)) return StartResult::Bus;
    clock_.delayMs(1);
    edges_.reset();

    for (uint8_t s = 0; s < kNumSensors; ++s) {
        if (!bank_.interruptIdle(s)) {
            if (stuckSensor) *stuckSensor = s;
            return StartResult::IntStuck;
        }
    }

    summary_ = RunSummary();
    strncpy(summary_.id, req.id, kRunIdMax);
    summary_.cond = req.cond;
    busErrors0_ = bank_.busErrorCount();
    consecutiveReadErrors_ = 0;

    for (uint8_t s = 0; s < kNumSensors; ++s) {
        if (participates(req.cond, s) && !bank_.startRanging(s)) {
            stopAll();
            return StartResult::Bus;
        }
    }

    summary_.t0Us = clock_.nowUs();
    endUs_ = summary_.t0Us + static_cast<uint64_t>(req.durationMs) * 1000u;
    // First result arrives after about one timing budget; later ones every
    // inter-measurement period.
    silentLimitUs_ = static_cast<uint64_t>(settings.interMeasurementMs) * 1000u * kSilentPeriods;
    for (uint8_t s = 0; s < kNumSensors; ++s) lastEdgeUs_[s] = summary_.t0Us;
    running_ = true;
    return StartResult::Ok;
}

void RunController::poll() {
    if (!running_) return;

    for (uint8_t s = 0; s < kNumSensors; ++s) {
        uint64_t t;
        while (edges_.takeEdge(s, t)) {
            if (!participates(summary_.cond, s)) {
                // The stopped sensor is still ranging: the run cannot be
                // called "solo", so abort now rather than log bad data.
                finish(AbortReason::Stray);
                return;
            }
            lastEdgeUs_[s] = t;
            Reading r;
            r.sensor = s;
            r.tIntUs = t;
            if (bank_.readResult(s, r)) {
                consecutiveReadErrors_ = 0;
                summary_.readings[s]++;
                sink_.onReading(summary_.id, r);
            } else {
                summary_.readErrors[s]++;
                if (++consecutiveReadErrors_ >= kMaxConsecutiveReadErrors) {
                    finish(AbortReason::Bus);
                    return;
                }
            }
        }
    }

    uint64_t now = clock_.nowUs();
    for (uint8_t s = 0; s < kNumSensors; ++s) {
        if (participates(summary_.cond, s) && now - lastEdgeUs_[s] > silentLimitUs_) {
            finish(AbortReason::Timeout);
            return;
        }
    }
    if (now >= endUs_) finish(AbortReason::None);
}

void RunController::abort(AbortReason reason) {
    if (running_) finish(reason);
}

void RunController::finish(AbortReason reason) {
    running_ = false;
    summary_.t1Us = clock_.nowUs();
    stopAll();
    for (uint8_t s = 0; s < kNumSensors; ++s) {
        summary_.edges[s] = edges_.edgeCount(s);
        summary_.overruns[s] = edges_.overrunCount(s);
    }
    summary_.busErrors = bank_.busErrorCount() - busErrors0_;
    summary_.abort = reason;
    sink_.onRunEnd(summary_);
}

}  // namespace rig
