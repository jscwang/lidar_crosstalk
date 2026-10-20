// Serial protocol between the rig firmware and the host. Spec: PROTOCOL.md.
// Pure C++ so it can be unit tested on a PC.
// Author: Jessica
#pragma once

#include "rig_types.h"

namespace rig {

constexpr int kProtocolVersion = 1;
constexpr size_t kMaxLine = 160;          // longest accepted command line
constexpr uint32_t kMinRunMs = 100;
constexpr uint32_t kMaxRunMs = 3600000;   // 1 h, enough for a 10 min warm-up

enum class CmdType { Ping, Info, Scan, SelfTest, Cfg, Run, Abort, StopAll, Status, Led, Reg, Trace };

// Status lights for the person moving the target: green when the setting is right, red when it is not.
enum class LedState : uint8_t { Off, Ok, Bad };

struct RunRequest {
    char id[kRunIdMax + 1] = {0};
    Condition cond = Condition::Both;
    uint32_t durationMs = 0;
};

struct Command {
    CmdType type = CmdType::Ping;
    SensorSettings settings;   // CFG only
    RunRequest run;            // RUN only
    LedState led = LedState::Off;   // LED only
    uint8_t regSensor = 0;          // REG only: raw register read for diagnostics
    uint16_t regAddr = 0;
    uint8_t regLen = 1;
    uint16_t traceMs = 0;           // TRACE only: sensor in regSensor, length in ms
    bool traceViaRun = false;       // TRACE only: path=run starts a real run (RunController) while the pin is recorded
};

// Error codes sent in "ERR <cmd> code=<code> msg=<text>".
namespace err {
constexpr const char *kUnknownCmd = "unknown_cmd";
constexpr const char *kBadArgs = "bad_args";
constexpr const char *kBusy = "busy";
constexpr const char *kNotReady = "not_ready";
constexpr const char *kBus = "i2c";
constexpr const char *kVerify = "verify";
constexpr const char *kIntStuck = "int_stuck";
}  // namespace err

// Parses one command line (no trailing newline required). On failure returns
// false and writes a short human-readable reason into `why`; `code` receives
// err::kUnknownCmd or err::kBadArgs.
bool parseCommand(const char *line, Command &out, const char *&code, char *why, size_t whyLen);

// Checks settings against the VL53L1X/ULD limits. Returns nullptr when valid,
// otherwise a static string naming the problem.
const char *validateSettings(const SensorSettings &s);

bool validRunId(const char *id);
const char *cmdName(CmdType t);

// ---- device -> host lines. Each returns the number of characters written
// (excluding the terminator), or 0 if the buffer was too small.
size_t formatReading(char *buf, size_t len, const char *runId, const Reading &r);
size_t formatSettings(char *buf, size_t len, const SensorSettings &s);

enum class AbortReason : uint8_t { None, Host, Bus, Stray, Timeout };
const char *abortName(AbortReason r);

struct RunSummary {
    char id[kRunIdMax + 1] = {0};
    Condition cond = Condition::Both;
    uint64_t t0Us = 0;
    uint64_t t1Us = 0;
    uint32_t readings[kNumSensors] = {0, 0};
    uint32_t edges[kNumSensors] = {0, 0};
    uint32_t overruns[kNumSensors] = {0, 0};
    uint32_t readErrors[kNumSensors] = {0, 0};
    uint32_t busErrors = 0;
    AbortReason abort = AbortReason::None;
};

size_t formatRunEnd(char *buf, size_t len, const RunSummary &s);

}  // namespace rig
