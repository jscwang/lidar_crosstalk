// Two-sensor crosstalk rig firmware: ESP32-S3 + TCA9548A + 2 x VL53L1X.
// Command protocol: PROTOCOL.md. Wiring: HARDWARE_INTERFACE.md.
// Author: Jessica
#include <Arduino.h>
#include <Wire.h>
#include <esp_system.h>

#include "diagnostics.h"
#include "hw_bank.h"
#include "int_capture.h"
#include "protocol.h"
#include "rig_config.h"
#include "run_controller.h"
#include "tca9548a.h"
#include "tof_channel.h"

namespace {

Tca9548a g_mux(Wire, cfg::kMuxAddr);
TofChannel g_tofA(Wire, g_mux, cfg::kMuxChannel[rig::kSensorA]);
TofChannel g_tofB(Wire, g_mux, cfg::kMuxChannel[rig::kSensorB]);
IntCapture g_ints;
HwSensorBank g_bank(g_tofA, g_tofB, g_ints, g_mux);
ArduinoClock g_clock;

class SerialSink : public rig::RunSink {
public:
    void onReading(const char *runId, const rig::Reading &r) override {
        char line[112];
        if (rig::formatReading(line, sizeof line, runId, r)) Serial.println(line);
    }
    void onRunEnd(const rig::RunSummary &s) override {
        char line[256];
        if (rig::formatRunEnd(line, sizeof line, s)) Serial.println(line);
    }
};

SerialSink g_sink;
rig::RunController g_runner(g_bank, g_ints, g_clock, g_sink);
Diagnostics g_diag(Wire, g_mux, g_bank, g_ints, g_clock, Serial);

rig::SensorSettings g_settings;   // last settings verified on both sensors
bool g_settingsVerified = false;

char g_line[rig::kMaxLine + 1];
size_t g_lineLen = 0;
bool g_lineOverflow = false;

const char *resetReason() {
    switch (esp_reset_reason()) {
        case ESP_RST_POWERON: return "poweron";
        case ESP_RST_SW: return "software";
        case ESP_RST_PANIC: return "panic";
        case ESP_RST_INT_WDT: case ESP_RST_TASK_WDT: case ESP_RST_WDT: return "watchdog";
        case ESP_RST_BROWNOUT: return "brownout";
        case ESP_RST_EXT: return "external";
        default: return "other";
    }
}

TofChannel &tof(uint8_t s) { return s == rig::kSensorA ? g_tofA : g_tofB; }

void replyOk(const char *cmd) { Serial.printf("OK %s\n", cmd); }
void replyErr(const char *cmd, const char *code, const char *msg) {
    Serial.printf("ERR %s code=%s msg=%s\n", cmd, code, msg);
}
void logLine(char level, const char *msg) { Serial.printf("LOG level=%c msg=%s\n", level, msg); }

// Initialises any sensor that is not yet ready. Safe to call repeatedly, so
// a re-seated cable recovers without a reset.
bool ensureSensors(char *why, size_t whyLen) {
    bool all = true;
    for (uint8_t s = 0; s < rig::kNumSensors; ++s) {
        if (tof(s).initialised()) continue;
        const char *reason = "";
        if (!tof(s).init(reason)) {
            snprintf(why, whyLen, "sensor %c: %s", rig::sensorName(s), reason);
            all = false;
            g_settingsVerified = false;
        }
    }
    return all;
}

bool applySettings(const rig::SensorSettings &s, char *why, size_t whyLen) {
    g_settingsVerified = false;
    for (uint8_t i = 0; i < rig::kNumSensors; ++i) {
        if (!g_bank.stopRanging(i)) {
            snprintf(why, whyLen, "sensor %c: stop failed", rig::sensorName(i));
            return false;
        }
    }
    for (uint8_t i = 0; i < rig::kNumSensors; ++i) {
        const char *reason = "";
        if (!tof(i).apply(s, reason)) {
            snprintf(why, whyLen, "sensor %c: %s", rig::sensorName(i), reason);
            return false;
        }
    }
    g_settings = s;
    g_settingsVerified = true;
    return true;
}

// A sensor that lost power (a reseated cable) comes back with default
// settings. Reading them back before every run costs about 2 ms.
bool settingsStillApplied(char *why, size_t whyLen) {
    for (uint8_t i = 0; i < rig::kNumSensors; ++i) {
        rig::SensorSettings back;
        if (!tof(i).readBack(back)) {
            snprintf(why, whyLen, "sensor %c: settings read-back failed", rig::sensorName(i));
            return false;
        }
        int dImp = static_cast<int>(back.interMeasurementMs) - static_cast<int>(g_settings.interMeasurementMs);
        if (back.roi != g_settings.roi || back.mode != g_settings.mode ||
            back.timingBudgetMs != g_settings.timingBudgetMs || dImp < -1 || dImp > 1) {
            snprintf(why, whyLen, "sensor %c: settings changed since CFG (power loss?); send CFG again",
                     rig::sensorName(i));
            return false;
        }
    }
    return true;
}

void printInfo() {
    char setting[48];
    rig::formatSettings(setting, sizeof setting, g_settings);
    Serial.printf(
        "INFO fw=%s board=%s proto=%d sda=%d scl=%d i2c_hz=%lu mux=0x%02X chA=%u chB=%u intA=%d intB=%d "
        "readyA=%d readyB=%d centreA=%u centreB=%u verified=%d %s\n",
        cfg::kFirmwareVersion, cfg::kBoard, rig::kProtocolVersion, cfg::kPinSda, cfg::kPinScl,
        static_cast<unsigned long>(cfg::kI2cHz), cfg::kMuxAddr, cfg::kMuxChannel[0], cfg::kMuxChannel[1],
        cfg::kPinInt[0], cfg::kPinInt[1], g_tofA.initialised(), g_tofB.initialised(), g_tofA.opticalCentre(),
        g_tofB.opticalCentre(), g_settingsVerified, setting);
}

void handleLine(const char *line) {
    rig::Command cmd;
    const char *code = nullptr;
    char why[96];
    if (!rig::parseCommand(line, cmd, code, why, sizeof why)) {
        char name[16] = "?";
        sscanf(line, "%15s", name);
        replyErr(name, code, why);
        return;
    }
    const char *name = rig::cmdName(cmd.type);

    // While a run is active only these commands are accepted, so nothing
    // else can touch the I2C bus mid-run.
    if (g_runner.running() && cmd.type != rig::CmdType::Ping && cmd.type != rig::CmdType::Abort &&
        cmd.type != rig::CmdType::Status && cmd.type != rig::CmdType::Led) {
        replyErr(name, rig::err::kBusy, "a run is in progress");
        return;
    }

    switch (cmd.type) {
        case rig::CmdType::Ping:
            replyOk(name);
            break;
        case rig::CmdType::Info:
            printInfo();
            replyOk(name);
            break;
        case rig::CmdType::Status:
            Serial.printf("STATUS state=%s run=%s buserr=%lu\n", g_runner.running() ? "running" : "idle",
                          g_runner.running() ? g_runner.runId() : "-",
                          static_cast<unsigned long>(g_bank.busErrorCount()));
            replyOk(name);
            break;
        case rig::CmdType::Trace: {
            if (!ensureSensors(why, sizeof why) || !g_settingsVerified) {
                replyErr(name, rig::err::kNotReady, g_settingsVerified ? why : "send CFG first");
                break;
            }
            // Range one sensor alone for traceMs and record both edges of its data-ready line. Each falling edge is
            // handled exactly as in a run: read the result, then clear the interrupt.
            const uint8_t s = cmd.regSensor;
            if (cmd.traceViaRun) {
                // The production path: a real run of this sensor alone (same start sequence, falling-edge capture and
                // read-and-clear as every measurement), with the pin's waveform recorded beside it. The run's READING
                // lines arrive before the TRACE lines, so the two can be compared.
                if (!settingsStillApplied(why, sizeof why)) {
                    g_settingsVerified = false;
                    replyErr(name, rig::err::kVerify, why);
                    break;
                }
                g_ints.beginTrace(s, true);
                rig::RunRequest req;
                strncpy(req.id, "edgetrace", rig::kRunIdMax);
                req.cond = s == rig::kSensorA ? rig::Condition::ASolo : rig::Condition::BSolo;
                req.durationMs = cmd.traceMs < rig::kMinRunMs ? rig::kMinRunMs : cmd.traceMs;
                uint8_t stuck = 0;
                const bool started = g_runner.start(req, g_settings, &stuck) == rig::StartResult::Ok;
                while (started && g_runner.running()) {
                    g_runner.poll();
                    delay(0);
                }
                Serial.printf("TRACE sensor=%c edges=%d reads=0 overflow=%d\n", rig::sensorName(s), g_ints.traceCount(),
                              g_ints.traceOverflowed() ? 1 : 0);
                for (int i = 0; i < g_ints.traceCount(); ++i) {
                    int lvl = 1;
                    uint64_t t = 0;
                    g_ints.traceAt(i, lvl, t);
                    Serial.printf("TRACE_E sensor=%c level=%d t=%llu\n", rig::sensorName(s), lvl,
                                  static_cast<unsigned long long>(t));
                }
                g_ints.endTrace();
                if (!started) replyErr(name, rig::err::kBus, "could not start the run");
                else replyOk(name);
                break;
            }
            struct Handled { uint64_t t; uint16_t range; uint32_t amb; uint32_t sig; };
            static Handled handled[128];
            int nHandled = 0;
            g_ints.beginTrace(s);
            g_bank.clearInterrupt(s);
            bool started = g_bank.startRanging(s);
            const uint64_t endUs = static_cast<uint64_t>(esp_timer_get_time()) + uint64_t(cmd.traceMs) * 1000u;
            int seen = 0;
            while (started && static_cast<uint64_t>(esp_timer_get_time()) < endUs) {
                int n = g_ints.traceCount();
                while (seen < n) {
                    int lvl = 1;
                    uint64_t t = 0;
                    g_ints.traceAt(seen, lvl, t);
                    ++seen;
                    if (lvl == 0 && nHandled < 128) {
                        rig::Reading r;
                        bool got = g_bank.readResult(s, r);
                        g_bank.clearInterrupt(s);
                        handled[nHandled++] = {static_cast<uint64_t>(esp_timer_get_time()), got ? r.rangeMm : uint16_t(0),
                                               got ? r.ambientKcps : 0u, got ? r.signalKcps : 0u};
                    }
                }
                delay(0);
            }
            g_bank.stopRanging(s);
            const int total = g_ints.traceCount();
            Serial.printf("TRACE sensor=%c edges=%d reads=%d overflow=%d\n", rig::sensorName(s), total, nHandled,
                          g_ints.traceOverflowed() ? 1 : 0);
            for (int i = 0; i < total; ++i) {
                int lvl = 1;
                uint64_t t = 0;
                g_ints.traceAt(i, lvl, t);
                Serial.printf("TRACE_E sensor=%c level=%d t=%llu\n", rig::sensorName(s), lvl,
                              static_cast<unsigned long long>(t));
            }
            for (int i = 0; i < nHandled; ++i)
                Serial.printf("TRACE_R sensor=%c t=%llu range=%u amb=%lu sig=%lu\n", rig::sensorName(s),
                              static_cast<unsigned long long>(handled[i].t), static_cast<unsigned>(handled[i].range),
                              static_cast<unsigned long>(handled[i].amb), static_cast<unsigned long>(handled[i].sig));
            g_ints.endTrace();
            if (!started) replyErr(name, rig::err::kBus, "could not start ranging");
            else replyOk(name);
            break;
        }
        case rig::CmdType::Reg: {
            uint8_t data[16] = {0};
            if (!g_bank.tof(cmd.regSensor).readRaw(cmd.regAddr, data, cmd.regLen)) {
                replyErr(name, rig::err::kBus, "register read failed");
                break;
            }
            char hex[33] = {0};
            for (uint8_t i = 0; i < cmd.regLen; ++i) snprintf(hex + 2 * i, 3, "%02X", data[i]);
            Serial.printf("REG sensor=%c addr=0x%04X data=%s\n", rig::sensorName(cmd.regSensor),
                          static_cast<unsigned>(cmd.regAddr), hex);
            replyOk(name);
            break;
        }
        case rig::CmdType::Led:
            digitalWrite(cfg::kPinLedOk, cmd.led == rig::LedState::Ok ? HIGH : LOW);
            digitalWrite(cfg::kPinLedBad, cmd.led == rig::LedState::Bad ? HIGH : LOW);
            replyOk(name);
            break;
        case rig::CmdType::Scan:
            g_diag.scan();
            replyOk(name);
            break;
        case rig::CmdType::StopAll: {
            bool ok = g_bank.stopRanging(rig::kSensorA) & g_bank.stopRanging(rig::kSensorB);
            if (ok) replyOk(name);
            else replyErr(name, rig::err::kBus, "stop failed on at least one sensor");
            break;
        }
        case rig::CmdType::Abort:
            g_runner.abort(rig::AbortReason::Host);
            replyOk(name);
            break;
        case rig::CmdType::Cfg: {
            // Full re-init every time (about 0.3 s): found on the bench that a
            // sensor which browned out comes back at 0x29 with its
            // configuration gone, which a settings read-back alone would miss.
            g_tofA.invalidate();
            g_tofB.invalidate();
            if (!ensureSensors(why, sizeof why)) {
                replyErr(name, rig::err::kNotReady, why);
                break;
            }
            if (!applySettings(cmd.settings, why, sizeof why)) {
                replyErr(name, rig::err::kVerify, why);
                break;
            }
            char setting[48];
            rig::formatSettings(setting, sizeof setting, g_settings);
            Serial.printf("CFG %s\n", setting);
            replyOk(name);
            break;
        }
        case rig::CmdType::SelfTest: {
            if (!ensureSensors(why, sizeof why) || !g_settingsVerified) {
                replyErr(name, rig::err::kNotReady, g_settingsVerified ? why : "send CFG first");
                break;
            }
            int failed = g_diag.selfTest(g_settings);
            Serial.printf("SELFTEST failed=%d\n", failed);
            replyOk(name);
            break;
        }
        case rig::CmdType::Run: {
            if (!g_settingsVerified) {
                replyErr(name, rig::err::kNotReady, "send CFG first");
                break;
            }
            if (!settingsStillApplied(why, sizeof why)) {
                g_settingsVerified = false;
                replyErr(name, rig::err::kVerify, why);
                break;
            }
            uint8_t stuck = 0;
            switch (g_runner.start(cmd.run, g_settings, &stuck)) {
                case rig::StartResult::Ok:
                    Serial.printf("OK RUN id=%s\n", cmd.run.id);
                    break;
                case rig::StartResult::Busy:
                    replyErr(name, rig::err::kBusy, "a run is in progress");
                    break;
                case rig::StartResult::IntStuck:
                    snprintf(why, sizeof why, "GPIO1 of sensor %c is held low after stop and clear",
                             rig::sensorName(stuck));
                    replyErr(name, rig::err::kIntStuck, why);
                    break;
                default:
                    replyErr(name, rig::err::kBus, "I2C error while starting the run");
                    break;
            }
            break;
        }
    }
}

void pollSerial() {
    while (Serial.available()) {
        char c = static_cast<char>(Serial.read());
        if (c == '\n') {
            if (g_lineOverflow) {
                replyErr("?", rig::err::kBadArgs, "line too long");
            } else {
                g_line[g_lineLen] = '\0';
                if (g_lineLen) handleLine(g_line);
            }
            g_lineLen = 0;
            g_lineOverflow = false;
        } else if (c != '\r') {
            if (g_lineLen < rig::kMaxLine) g_line[g_lineLen++] = c;
            else g_lineOverflow = true;
        }
    }
}

}  // namespace

void setup() {
    Serial.setTxBufferSize(8192);   // a full run never blocks on the UART
    Serial.begin(cfg::kSerialBaud);
    Serial.printf("BOOT fw=%s board=%s proto=%d reset=%s\n", cfg::kFirmwareVersion, cfg::kBoard,
                  rig::kProtocolVersion, resetReason());

    if (!Wire.begin(cfg::kPinSda, cfg::kPinScl, cfg::kI2cHz)) logLine('E', "I2C init failed");
    Wire.setTimeOut(cfg::kI2cTimeoutMs);
    g_ints.begin(cfg::kPinInt);
    pinMode(cfg::kPinLedOk, OUTPUT);
    pinMode(cfg::kPinLedBad, OUTPUT);
    digitalWrite(cfg::kPinLedOk, LOW);
    digitalWrite(cfg::kPinLedBad, LOW);

    if (!g_mux.present()) logLine('E', "TCA9548A not found at 0x70: check the Qwiic cable to Main");

    char why[96];
    if (!ensureSensors(why, sizeof why)) {
        logLine('E', why);
    } else {
        rig::SensorSettings defaults;
        defaults.roi = cfg::kDefaultRoi;
        defaults.timingBudgetMs = cfg::kDefaultTimingBudgetMs;
        defaults.interMeasurementMs = cfg::kDefaultInterMeasurementMs;
        if (!applySettings(defaults, why, sizeof why)) logLine('E', why);
    }
    Serial.println("READY");
}

void loop() {
    pollSerial();
    g_runner.poll();
}
