// Author: Jessica
#include "diagnostics.h"

#include <stdio.h>
#include <string.h>

#include "run_stats.h"

namespace {

// Collects per-sensor statistics during a self-test run instead of printing.
class StatsSink : public rig::RunSink {
public:
    rig::RunStatsAccumulator acc[rig::kNumSensors];
    rig::RunSummary summary;
    bool ended = false;
    void onReading(const char *, const rig::Reading &r) override { acc[r.sensor].add(r); }
    void onRunEnd(const rig::RunSummary &s) override {
        summary = s;
        ended = true;
    }
};

constexpr uint32_t kTestRunMs = 1000;

}  // namespace

void Diagnostics::report(const char *name, bool pass, const char *detail) {
    if (!pass) failures_++;
    out_.printf("TEST name=%s result=%s detail=%s\n", name, pass ? "PASS" : "FAIL", detail);
}

void Diagnostics::info(const char *name, const char *detail) {
    out_.printf("TEST name=%s result=INFO detail=%s\n", name, detail);
}

void Diagnostics::scanInto(char *list, size_t len, uint8_t skip) {
    list[0] = '\0';
    size_t used = 0;
    for (uint8_t a = 0x08; a < 0x78; ++a) {
        if (a == skip) continue;
        wire_.beginTransmission(a);
        if (wire_.endTransmission() == 0) {
            int w = snprintf(list + used, len - used, "%s%02x", used ? "," : "", a);
            if (w > 0 && static_cast<size_t>(w) < len - used) used += static_cast<size_t>(w);
        }
    }
    if (!used) snprintf(list, len, "none");
}

void Diagnostics::scan() {
    char list[96];
    // With every channel off, only the mux itself should answer on Main.
    bool muxOk = mux_.disableAll();
    scanInto(list, sizeof list, 0);
    out_.printf("SCAN bus=main addrs=%s%s\n", list, muxOk ? "" : " mux=unresponsive");
    for (uint8_t ch = 0; ch < 8; ++ch) {
        if (!mux_.select(ch, true)) {
            out_.printf("SCAN ch=%u addrs=error\n", ch);
            continue;
        }
        // The mux answers on every channel, so it is not listed downstream.
        scanInto(list, sizeof list, mux_.address());
        out_.printf("SCAN ch=%u addrs=%s\n", ch, list);
    }
    mux_.disableAll();
    mux_.invalidate();
}

int Diagnostics::selfTest(const rig::SensorSettings &settings) {
    failures_ = 0;
    char d[112];
    uint32_t busErr0 = bank_.busErrorCount();

    report("mux_present", mux_.present(), "TCA9548A answers at 0x70");
    for (uint8_t s = 0; s < rig::kNumSensors; ++s) {
        char name[24];
        snprintf(name, sizeof name, "mux_select_%c", rig::sensorName(s));
        bool ok = mux_.select(bank_.tof(s).muxChannel(), true);
        report(name, ok, ok ? "channel mask read back correctly" : "mask write or read-back failed");
    }

    for (uint8_t s = 0; s < rig::kNumSensors; ++s) {
        TofChannel &t = bank_.tof(s);
        char name[24];
        uint16_t id = 0;
        bool ok = t.readModelId(id);
        snprintf(d, sizeof d, "model_id=0x%04X expected=0xEACC", id);
        snprintf(name, sizeof name, "sensor_id_%c", rig::sensorName(s));
        report(name, ok && id == 0xEACC, ok ? d : "no answer at 0x29");

        uint8_t boot = 0;
        ok = t.readBootState(boot);
        snprintf(d, sizeof d, "firmware_system_status=%u", boot);
        snprintf(name, sizeof name, "boot_%c", rig::sensorName(s));
        report(name, ok && boot != 0, d);

        rig::SensorSettings back;
        ok = t.readBack(back);
        char setting[48];
        rig::formatSettings(setting, sizeof setting, back);
        snprintf(name, sizeof name, "settings_%c", rig::sensorName(s));
        bool same = ok && back.roi == settings.roi && back.mode == settings.mode &&
                    back.timingBudgetMs == settings.timingBudgetMs &&
                    (back.interMeasurementMs + 1 >= settings.interMeasurementMs) &&
                    (back.interMeasurementMs <= settings.interMeasurementMs + 1);
        report(name, same, ok ? setting : "read-back failed");

        snprintf(d, sizeof d, "optical_centre_spad=%u", t.opticalCentre());
        snprintf(name, sizeof name, "roi_centre_%c", rig::sensorName(s));
        info(name, d);
    }

    // Timed runs through the real run controller.
    struct Case { const char *name; rig::Condition cond; };
    const Case cases[] = {{"run_A", rig::Condition::ASolo}, {"run_B", rig::Condition::BSolo},
                          {"run_AB", rig::Condition::Both}};
    for (const Case &c : cases) {
        StatsSink sink;
        rig::RunController rc(bank_, ints_, clock_, sink);
        rig::RunRequest req;
        strncpy(req.id, "selftest", rig::kRunIdMax);
        req.cond = c.cond;
        req.durationMs = kTestRunMs;
        uint8_t stuck = 0;
        rig::StartResult sr = rc.start(req, settings, &stuck);
        if (sr != rig::StartResult::Ok) {
            snprintf(d, sizeof d, "start failed: %s%c",
                     sr == rig::StartResult::IntStuck ? "GPIO1 line held low on sensor " : "I2C error",
                     sr == rig::StartResult::IntStuck ? rig::sensorName(stuck) : ' ');
            report(c.name, false, d);
            continue;
        }
        while (rc.running()) {
            rc.poll();
            delay(1);
        }
        if (sink.summary.abort != rig::AbortReason::None) {
            snprintf(d, sizeof d, "run aborted: %s (edgesA=%lu edgesB=%lu)", rig::abortName(sink.summary.abort),
                     static_cast<unsigned long>(sink.summary.edges[0]),
                     static_cast<unsigned long>(sink.summary.edges[1]));
            report(c.name, false, d);
            continue;
        }
        for (uint8_t s = 0; s < rig::kNumSensors; ++s) {
            if (!rig::participates(c.cond, s)) continue;
            rig::RunStats st = sink.acc[s].result();
            const char *problem =
                rig::checkTiming(st, kTestRunMs, settings.timingBudgetMs, settings.interMeasurementMs);
            char name[24];
            snprintf(name, sizeof name, "%s_%c", c.name, rig::sensorName(s));
            snprintf(d, sizeof d, "n=%lu period_ms=%.2f max_ms=%.2f%s%s",
                     static_cast<unsigned long>(st.n), st.meanPeriodMs, st.maxPeriodMs,
                     problem ? " problem=" : "", problem ? problem : "");
            report(name, problem == nullptr, d);
            snprintf(name, sizeof name, "%s_%c_range", c.name, rig::sensorName(s));
            snprintf(d, sizeof d, "median_mm=%u valid=%lu/%lu", st.medianRangeMm,
                     static_cast<unsigned long>(st.valid), static_cast<unsigned long>(st.n));
            info(name, d);
        }
    }

    // After a stop, neither sensor may raise another interrupt.
    for (uint8_t s = 0; s < rig::kNumSensors; ++s) bank_.stopRanging(s);
    clock_.delayMs(settings.timingBudgetMs + 5u);
    for (uint8_t s = 0; s < rig::kNumSensors; ++s) bank_.clearInterrupt(s);
    ints_.reset();
    clock_.delayMs(3u * settings.interMeasurementMs);
    snprintf(d, sizeof d, "edges after stop: A=%lu B=%lu", static_cast<unsigned long>(ints_.edgeCount(0)),
             static_cast<unsigned long>(ints_.edgeCount(1)));
    report("stop_quiet", ints_.edgeCount(0) == 0 && ints_.edgeCount(1) == 0, d);
    for (uint8_t s = 0; s < rig::kNumSensors; ++s) {
        char name[24];
        snprintf(name, sizeof name, "int_idle_%c", rig::sensorName(s));
        snprintf(d, sizeof d, "GPIO%d level=%d expected=1", ints_.pin(s), ints_.level(s));
        report(name, ints_.level(s) == 1, d);
    }

    uint32_t busErr = bank_.busErrorCount() - busErr0;
    snprintf(d, sizeof d, "failed I2C transactions during self-test=%lu", static_cast<unsigned long>(busErr));
    report("i2c_errors", busErr == 0, d);
    return failures_;
}
