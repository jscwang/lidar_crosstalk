// Native (PC) unit tests for the pure-C++ firmware core: protocol parsing and
// formatting, result decoding and the run state machine.
// Build and run: python run_native_tests.py
// Author: Jessica
#include <stdio.h>
#include <string.h>

#include <string>
#include <vector>

#include "protocol.h"
#include "run_controller.h"
#include "run_stats.h"
#include "uld_decode.h"

using namespace rig;

static int g_fail = 0, g_pass = 0;
#define CHECK(cond)                                                            \
    do {                                                                       \
        if (cond) ++g_pass;                                                    \
        else { ++g_fail; printf("FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); } \
    } while (0)

static bool parse(const char *line, Command &c, std::string *code = nullptr) {
    const char *cd = nullptr;
    char why[80];
    bool ok = parseCommand(line, c, cd, why, sizeof why);
    if (code) *code = ok ? "" : cd;
    return ok;
}

// ------------------------------------------------------------------ protocol
static void testParseSimple() {
    Command c;
    CHECK(parse("PING", c) && c.type == CmdType::Ping);
    CHECK(parse("INFO\r\n", c) && c.type == CmdType::Info);
    CHECK(parse("SELFTEST ", c) && c.type == CmdType::SelfTest);
    CHECK(parse("STOPALL", c) && c.type == CmdType::StopAll);
    std::string code;
    CHECK(!parse("ping", c, &code) && code == err::kUnknownCmd);   // case sensitive
    CHECK(!parse("", c, &code) && code == err::kUnknownCmd);
    CHECK(!parse("PING x=1", c, &code) && code == err::kBadArgs);
}

static void testParseReg() {
    Command c;
    CHECK(parse("REG sensor=A addr=0x00DE len=2", c) && c.type == CmdType::Reg && c.regSensor == kSensorA &&
          c.regAddr == 0x00DE && c.regLen == 2);
    CHECK(parse("REG sensor=B addr=108 len=4", c) && c.regSensor == kSensorB && c.regAddr == 108 && c.regLen == 4);
    std::string code;
    CHECK(!parse("REG sensor=C addr=0x00DE len=2", c, &code) && code == err::kBadArgs);
    CHECK(!parse("REG sensor=A addr=zz len=2", c, &code) && code == err::kBadArgs);
    CHECK(!parse("REG sensor=A addr=0x10000 len=2", c, &code) && code == err::kBadArgs);
    CHECK(!parse("REG sensor=A addr=0x00DE len=0", c, &code) && code == err::kBadArgs);
    CHECK(!parse("REG sensor=A addr=0x00DE len=17", c, &code) && code == err::kBadArgs);
    CHECK(!parse("REG sensor=A addr=0x00DE", c, &code) && code == err::kBadArgs);
}

static void testParseTrace() {
    Command c;
    CHECK(parse("TRACE sensor=B ms=300", c) && c.type == CmdType::Trace && c.regSensor == kSensorB && c.traceMs == 300);
    std::string code;
    CHECK(!parse("TRACE sensor=C ms=300", c, &code) && code == err::kBadArgs);
    CHECK(!parse("TRACE sensor=A ms=10", c, &code) && code == err::kBadArgs);
    CHECK(!parse("TRACE sensor=A ms=3001", c, &code) && code == err::kBadArgs);
    CHECK(!parse("TRACE sensor=A", c, &code) && code == err::kBadArgs);
    CHECK(parse("TRACE sensor=A ms=300", c) && !c.traceViaRun);
    CHECK(parse("TRACE sensor=B ms=300 path=run", c) && c.traceViaRun && c.regSensor == kSensorB);
    CHECK(!parse("TRACE sensor=A ms=300 path=own", c, &code) && code == err::kBadArgs);
    CHECK(!parse("TRACE sensor=A path=run", c, &code) && code == err::kBadArgs);
}

static void testParseLed() {
    Command c;
    CHECK(parse("LED state=ok", c) && c.type == CmdType::Led && c.led == LedState::Ok);
    CHECK(parse("LED state=bad", c) && c.led == LedState::Bad);
    CHECK(parse("LED state=off", c) && c.led == LedState::Off);
    std::string code;
    CHECK(!parse("LED", c, &code) && code == err::kBadArgs);
    CHECK(!parse("LED state=green", c, &code) && code == err::kBadArgs);
    CHECK(!parse("LED colour=ok", c, &code) && code == err::kBadArgs);
    CHECK(!parse("LED state=ok state=bad", c, &code) && code == err::kBadArgs);
}

static void testParseCfg() {
    Command c;
    CHECK(parse("CFG roi=4 tb=33 imp=40 mode=short", c));
    CHECK(c.type == CmdType::Cfg && c.settings.roi == 4 && c.settings.timingBudgetMs == 33 &&
          c.settings.interMeasurementMs == 40 && c.settings.mode == DistanceMode::Short);
    CHECK(parse("CFG mode=long imp=100 tb=100 roi=16", c) && c.settings.mode == DistanceMode::Long);
    CHECK(!parse("CFG roi=3 tb=33 imp=40 mode=short", c));      // ROI below 4
    CHECK(!parse("CFG roi=17 tb=33 imp=40 mode=short", c));
    CHECK(!parse("CFG roi=16 tb=34 imp=40 mode=short", c));     // not a ULD budget
    CHECK(!parse("CFG roi=16 tb=15 imp=40 mode=long", c));      // 15 ms is short-only
    CHECK(parse("CFG roi=16 tb=15 imp=40 mode=short", c));
    CHECK(!parse("CFG roi=16 tb=50 imp=40 mode=short", c));     // imp < tb
    CHECK(!parse("CFG roi=16 tb=33 imp=40", c));                // missing key
    CHECK(!parse("CFG roi=16 tb=33 imp=40 mode=short roi=4", c));
    CHECK(!parse("CFG roi=16 tb=33 imp=-40 mode=short", c));
    CHECK(!parse("CFG roi=16 tb=33 imp=40 mode=medium", c));
    CHECK(!parse("CFG roi=16 tb=33 imp=40 mode=short x=1", c));
    CHECK(!parse("CFG roi= tb=33 imp=40 mode=short", c));
    CHECK(!parse("CFG roi=99999999999 tb=33 imp=40 mode=short", c));
}

static void testParseRun() {
    Command c;
    CHECK(parse("RUN id=d03-t10-r1-full-AB cond=AB dur=30000", c));
    CHECK(c.type == CmdType::Run && strcmp(c.run.id, "d03-t10-r1-full-AB") == 0 &&
          c.run.cond == Condition::Both && c.run.durationMs == 30000);
    CHECK(parse("RUN id=x cond=A dur=100", c) && c.run.cond == Condition::ASolo);
    CHECK(parse("RUN id=x cond=B dur=3600000", c) && c.run.cond == Condition::BSolo);
    CHECK(!parse("RUN id=x cond=C dur=1000", c));
    CHECK(!parse("RUN id=x cond=A dur=99", c));
    CHECK(!parse("RUN id=x cond=A dur=3600001", c));
    CHECK(!parse("RUN id=bad.id cond=A dur=1000", c));
    CHECK(!parse("RUN id=abcdefghijklmnopqrstuvwxy cond=A dur=1000", c));   // 25 chars
    CHECK(parse("RUN id=abcdefghijklmnopqrstuvwx cond=A dur=1000", c));     // 24 chars
    CHECK(!parse("RUN cond=A dur=1000", c));
    std::string longLine = "RUN id=x cond=A dur=1000 " + std::string(200, 'z');
    CHECK(!parse(longLine.c_str(), c));
}

static void testFormat() {
    Reading r;
    r.sensor = kSensorB;
    r.tIntUs = 12345678901ULL;
    r.tReadUs = 12345679900ULL;
    r.rangeMm = 301;
    r.status = 0;
    r.signalKcps = 600000;   // above 16 bits: must not wrap
    r.ambientKcps = 1234;
    r.spads = 44;
    r.stream = 200;
    char buf[128];
    size_t n = formatReading(buf, sizeof buf, "run1", r);
    CHECK(n > 0);
    CHECK(strcmp(buf, "D run1 B 12345678901 12345679900 301 0 600000 1234 44 200") == 0);
    CHECK(formatReading(buf, 10, "run1", r) == 0);   // too small: reported, not truncated silently

    SensorSettings s;
    s.roi = 4;
    formatSettings(buf, sizeof buf, s);
    CHECK(strcmp(buf, "roi=4 tb=33 imp=40 mode=short") == 0);

    RunSummary sum;
    strcpy(sum.id, "r7");
    sum.cond = Condition::ASolo;
    sum.t0Us = 1;
    sum.t1Us = 2;
    sum.readings[0] = 750;
    sum.edges[0] = 751;
    sum.abort = AbortReason::Stray;
    char line[256];
    CHECK(formatRunEnd(line, sizeof line, sum) > 0);
    CHECK(strcmp(line, "RUNEND id=r7 cond=A t0=1 t1=2 nA=750 nB=0 edgesA=751 edgesB=0 overrunA=0 overrunB=0 "
                       "rderrA=0 rderrB=0 buserr=0 abort=stray") == 0);
}

// ------------------------------------------------------------------ decode
static void testDecode() {
    CHECK(mapRangeStatus(9) == 0);
    CHECK(mapRangeStatus(0x20 | 9) == 0);   // upper bits ignored
    CHECK(mapRangeStatus(6) == 1);
    CHECK(mapRangeStatus(4) == 2);
    CHECK(mapRangeStatus(7) == 7);
    CHECK(mapRangeStatus(13) == 13);
    CHECK(mapRangeStatus(0) == 255);
    CHECK(mapRangeStatus(31) == 255);

    uint8_t b[kResultBlockLen] = {0};
    b[0] = 9;                    // valid
    b[3] = 0xC4; b[4] = 0x00;    // 196 SPADs
    b[7] = 0x01; b[8] = 0x02;    // ambient 0x0102 * 8 = 2064
    b[2] = 131;                  // stream count (0x008B)
    b[12] = 77;                  // phase low byte: must not be taken as the stream count
    b[13] = 0x01; b[14] = 0x2C;  // 300 mm
    b[15] = 0xFF; b[16] = 0xFF;  // signal 65535 * 8, needs 32 bits
    Reading r;
    decodeResultBlock(b, r);
    CHECK(r.status == 0);
    CHECK(r.spads == 196);
    CHECK(r.ambientKcps == 2064);
    CHECK(r.stream == 131);
    CHECK(r.rangeMm == 300);
    CHECK(r.signalKcps == 524280u);
}

// ------------------------------------------------------------------ run controller
struct FakeClock : Clock {
    uint64_t t = 1000000;
    uint64_t nowUs() const override { return t; }
    void delayMs(uint32_t ms) override { t += static_cast<uint64_t>(ms) * 1000; }
};

struct FakeEdges : EdgeSource {
    std::vector<uint64_t> pending[kNumSensors];
    uint32_t edges[kNumSensors] = {0, 0};
    void push(uint8_t s, uint64_t t) {
        edges[s]++;
        pending[s].push_back(t);
    }
    bool takeEdge(uint8_t s, uint64_t &t) override {
        if (pending[s].empty()) return false;
        t = pending[s].front();
        pending[s].erase(pending[s].begin());
        return true;
    }
    uint32_t edgeCount(uint8_t s) const override { return edges[s]; }
    uint32_t overrunCount(uint8_t) const override { return 0; }
    void reset() override {
        for (auto &p : pending) p.clear();
        edges[0] = edges[1] = 0;
    }
};

struct FakeBank : SensorBank {
    FakeClock *clock = nullptr;
    bool ranging[kNumSensors] = {true, true};   // as if left running by an MCU reset
    bool idle[kNumSensors] = {true, true};
    bool failStart = false;
    int failReadsFrom = -1;   // read index from which reads fail
    int reads = 0;
    uint32_t busErrors = 0;
    std::vector<std::string> log;
    bool stopRanging(uint8_t s) override {
        ranging[s] = false;
        log.push_back(std::string("stop") + sensorName(s));
        return true;
    }
    bool clearInterrupt(uint8_t) override { return true; }
    bool startRanging(uint8_t s) override {
        if (failStart) return false;
        ranging[s] = true;
        log.push_back(std::string("start") + sensorName(s));
        return true;
    }
    bool readResult(uint8_t s, Reading &r) override {
        int i = reads++;
        if (failReadsFrom >= 0 && i >= failReadsFrom) {
            busErrors++;
            return false;
        }
        r.rangeMm = static_cast<uint16_t>(300 + s);
        r.status = 0;
        r.tReadUs = clock->t;
        return true;
    }
    bool interruptIdle(uint8_t s) override { return idle[s]; }
    uint32_t busErrorCount() const override { return busErrors; }
};

struct FakeSink : RunSink {
    std::vector<Reading> readings;
    std::vector<RunSummary> ends;
    void onReading(const char *, const Reading &r) override { readings.push_back(r); }
    void onRunEnd(const RunSummary &s) override { ends.push_back(s); }
};

struct Rig {
    FakeClock clock;
    FakeEdges edges;
    FakeBank bank;
    FakeSink sink;
    RunController rc{bank, edges, clock, sink};
    SensorSettings settings;
    Rig() { bank.clock = &clock; }

    // Advance virtual time in 1 ms steps; ranging sensors raise an edge every
    // inter-measurement period (first after one timing budget).
    void simulate(uint32_t ms, uint32_t periodUsA = 0, uint32_t periodUsB = 0) {
        uint64_t period[2] = {periodUsA ? periodUsA : settings.interMeasurementMs * 1000u,
                              periodUsB ? periodUsB : settings.interMeasurementMs * 1000u};
        uint64_t next[2] = {clock.t + settings.timingBudgetMs * 1000u, clock.t + settings.timingBudgetMs * 1000u};
        for (uint32_t i = 0; i < ms && rc.running(); ++i) {
            clock.t += 1000;
            for (uint8_t s = 0; s < 2; ++s) {
                if (bank.ranging[s] && clock.t >= next[s]) {
                    edges.push(s, clock.t);
                    next[s] += period[s];
                }
            }
            rc.poll();
        }
    }
};

static RunRequest req(const char *id, Condition c, uint32_t ms) {
    RunRequest r;
    strcpy(r.id, id);
    r.cond = c;
    r.durationMs = ms;
    return r;
}

static void testRunBothNormal() {
    Rig g;
    CHECK(g.rc.start(req("r1", Condition::Both, 1000), g.settings) == StartResult::Ok);
    CHECK(g.bank.log[0] == "stopA" && g.bank.log[1] == "stopB");   // stop both first
    CHECK(g.bank.ranging[0] && g.bank.ranging[1]);
    g.simulate(2000);
    CHECK(!g.rc.running());
    CHECK(g.sink.ends.size() == 1);
    const RunSummary &s = g.sink.ends[0];
    CHECK(s.abort == AbortReason::None);
    // 1000 ms run, 40 ms period, first at 33 ms: 25 edges each
    CHECK(s.readings[0] == 25 && s.readings[1] == 25);
    CHECK(s.edges[0] == 25 && s.edges[1] == 25);
    CHECK(s.t1Us - s.t0Us >= 1000000);
    CHECK(!g.bank.ranging[0] && !g.bank.ranging[1]);   // both stopped at the end
    CHECK(strcmp(s.id, "r1") == 0);
}

static void testRunSoloKeepsOtherStopped() {
    Rig g;
    CHECK(g.rc.start(req("r2", Condition::ASolo, 500), g.settings) == StartResult::Ok);
    CHECK(g.bank.ranging[0] && !g.bank.ranging[1]);
    g.simulate(1000);
    const RunSummary &s = g.sink.ends.at(0);
    CHECK(s.abort == AbortReason::None && s.readings[0] > 0 && s.readings[1] == 0 && s.edges[1] == 0);
    for (const Reading &r : g.sink.readings) CHECK(r.sensor == kSensorA);
}

static void testStrayEdgeAborts() {
    Rig g;
    CHECK(g.rc.start(req("r3", Condition::BSolo, 5000), g.settings) == StartResult::Ok);
    g.simulate(100);
    g.edges.push(kSensorA, g.clock.t);   // A should be stopped but fires
    g.rc.poll();
    CHECK(!g.rc.running());
    CHECK(g.sink.ends.at(0).abort == AbortReason::Stray);
    CHECK(!g.bank.ranging[0] && !g.bank.ranging[1]);
}

static void testSilentSensorTimesOut() {
    Rig g;
    CHECK(g.rc.start(req("r4", Condition::Both, 5000), g.settings) == StartResult::Ok);
    g.bank.ranging[1] = false;   // B's interrupt wire is off: no edges
    g.simulate(5000);
    CHECK(g.sink.ends.at(0).abort == AbortReason::Timeout);
    uint64_t dur = g.sink.ends[0].t1Us - g.sink.ends[0].t0Us;
    CHECK(dur > 200000 && dur < 260000);   // 5 x 40 ms, give or take one period
}

static void testReadErrorsAbort() {
    Rig g;
    g.bank.failReadsFrom = 4;
    CHECK(g.rc.start(req("r5", Condition::Both, 5000), g.settings) == StartResult::Ok);
    g.simulate(5000);
    const RunSummary &s = g.sink.ends.at(0);
    CHECK(s.abort == AbortReason::Bus);
    CHECK(s.readErrors[0] + s.readErrors[1] == RunController::kMaxConsecutiveReadErrors);
    CHECK(s.busErrors == RunController::kMaxConsecutiveReadErrors);
}

static void testStartRefusals() {
    Rig g;
    uint8_t stuck = 99;
    g.bank.idle[1] = false;
    CHECK(g.rc.start(req("r6", Condition::Both, 1000), g.settings, &stuck) == StartResult::IntStuck);
    CHECK(stuck == 1 && !g.rc.running());
    g.bank.idle[1] = true;
    g.bank.failStart = true;
    CHECK(g.rc.start(req("r6", Condition::Both, 1000), g.settings) == StartResult::Bus);
    CHECK(!g.bank.ranging[0] && !g.bank.ranging[1]);
    g.bank.failStart = false;
    CHECK(g.rc.start(req("r6", Condition::Both, 1000), g.settings) == StartResult::Ok);
    CHECK(g.rc.start(req("r7", Condition::Both, 1000), g.settings) == StartResult::Busy);
    g.rc.abort(AbortReason::Host);
    CHECK(!g.rc.running() && g.sink.ends.back().abort == AbortReason::Host);
    g.rc.abort(AbortReason::Host);   // idle: no second summary
    CHECK(g.sink.ends.size() == 1);
}

static void testEdgesBeforeStartAreDiscarded() {
    Rig g;
    g.edges.push(kSensorA, g.clock.t);   // left over from before the run
    CHECK(g.rc.start(req("r8", Condition::BSolo, 200), g.settings) == StartResult::Ok);
    g.simulate(500);
    CHECK(g.sink.ends.at(0).abort == AbortReason::None);   // not counted as stray
}


// ------------------------------------------------------------------ run stats
static Reading at(uint64_t tUs, uint8_t stream, uint16_t mm = 300, uint8_t status = 0) {
    Reading r;
    r.tIntUs = tUs;
    r.stream = stream;
    r.rangeMm = mm;
    r.status = status;
    return r;
}

static void testRunStats() {
    RunStatsAccumulator acc;
    uint8_t stream = 250;
    for (int i = 0; i < 25; ++i) {
        acc.add(at(1000000 + static_cast<uint64_t>(i) * 40000, stream, static_cast<uint16_t>(300 + (i % 3)),
                   i == 5 ? 7 : 0));
        stream = stream == 255 ? 128 : stream + 1;
    }
    RunStats s = acc.result();
    CHECK(s.n == 25 && s.valid == 24);
    CHECK(s.meanPeriodMs > 39.99 && s.meanPeriodMs < 40.01);
    CHECK(s.maxPeriodMs > 39.99 && s.maxPeriodMs < 40.01);
    CHECK(s.medianRangeMm == 301);
    CHECK(checkTiming(s, 1000, 33, 40) == nullptr);
    CHECK(checkTiming(s, 2000, 33, 40) != nullptr);   // expected about 50

    RunStatsAccumulator gap;
    for (int i = 0; i < 25; ++i) {
        uint64_t t = static_cast<uint64_t>(i) * 40000 + (i >= 10 ? 40000 : 0);   // one missed
        gap.add(at(t, static_cast<uint8_t>(i + (i >= 10 ? 1 : 0))));
    }
    RunStats g = gap.result();
    CHECK(g.maxPeriodMs > 79.9 && g.maxPeriodMs < 80.1);   // the gap left by the missed reading
    CHECK(checkTiming(g, 1000, 33, 40) != nullptr);

    RunStatsAccumulator slow;
    for (int i = 0; i < 25; ++i) slow.add(at(static_cast<uint64_t>(i) * 46000, static_cast<uint8_t>(i)));
    CHECK(checkTiming(slow.result(), 1000, 33, 40) != nullptr);   // 15% slow

    RunStatsAccumulator empty;
    CHECK(checkTiming(empty.result(), 1000, 33, 40) != nullptr);
}

int main() {
    testParseSimple();
    testParseLed();
    testParseReg();
    testParseTrace();
    testParseCfg();
    testParseRun();
    testFormat();
    testDecode();
    testRunBothNormal();
    testRunSoloKeepsOtherStopped();
    testStrayEdgeAborts();
    testSilentSensorTimesOut();
    testReadErrorsAbort();
    testStartRefusals();
    testEdgesBeforeStartAreDiscarded();
    testRunStats();
    printf("%d passed, %d failed\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
