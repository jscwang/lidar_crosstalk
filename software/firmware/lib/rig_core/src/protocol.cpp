// Author: Jessica
#include "protocol.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

namespace rig {

const char *conditionName(Condition c) {
    switch (c) {
        case Condition::ASolo: return "A";
        case Condition::BSolo: return "B";
        default: return "AB";
    }
}

const char *cmdName(CmdType t) {
    switch (t) {
        case CmdType::Ping: return "PING";
        case CmdType::Info: return "INFO";
        case CmdType::Scan: return "SCAN";
        case CmdType::SelfTest: return "SELFTEST";
        case CmdType::Cfg: return "CFG";
        case CmdType::Run: return "RUN";
        case CmdType::Abort: return "ABORT";
        case CmdType::StopAll: return "STOPALL";
        case CmdType::Led: return "LED";
        case CmdType::Reg: return "REG";
        case CmdType::Trace: return "TRACE";
        default: return "STATUS";
    }
}

const char *abortName(AbortReason r) {
    switch (r) {
        case AbortReason::None: return "none";
        case AbortReason::Host: return "host";
        case AbortReason::Bus: return "i2c";
        case AbortReason::Stray: return "stray";
        default: return "timeout";
    }
}

namespace {

void setWhy(char *why, size_t whyLen, const char *msg) {
    if (why && whyLen) {
        strncpy(why, msg, whyLen - 1);
        why[whyLen - 1] = '\0';
    }
}

// Strict unsigned decimal parse: digits only, no sign, no overflow.
bool parseUint(const char *s, uint32_t maxValue, uint32_t &out) {
    if (!s || !*s) return false;
    uint64_t v = 0;
    for (const char *p = s; *p; ++p) {
        if (*p < '0' || *p > '9') return false;
        v = v * 10 + static_cast<uint64_t>(*p - '0');
        if (v > maxValue) return false;
    }
    out = static_cast<uint32_t>(v);
    return true;
}

bool isTimingBudgetAllowed(uint16_t tb, DistanceMode m) {
    switch (tb) {
        case 15: return m == DistanceMode::Short;   // ULD: short mode only
        case 20: case 33: case 50: case 100: case 200: case 500: return true;
        default: return false;
    }
}

}  // namespace

const char *validateSettings(const SensorSettings &s) {
    if (s.roi < 4 || s.roi > 16) return "roi must be 4..16";
    if (s.mode != DistanceMode::Short && s.mode != DistanceMode::Long) return "mode must be short or long";
    if (!isTimingBudgetAllowed(s.timingBudgetMs, s.mode))
        return "tb must be 20,33,50,100,200,500 (15 in short mode only)";
    if (s.interMeasurementMs < s.timingBudgetMs) return "imp must be >= tb";
    if (s.interMeasurementMs > 5000) return "imp must be <= 5000";
    return nullptr;
}

bool validRunId(const char *id) {
    size_t n = strlen(id);
    if (n == 0 || n > kRunIdMax) return false;
    for (size_t i = 0; i < n; ++i) {
        char c = id[i];
        bool ok = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '_' ||
                  c == '-';
        if (!ok) return false;
    }
    return true;
}

bool parseCommand(const char *line, Command &out, const char *&code, char *why, size_t whyLen) {
    code = err::kBadArgs;
    char buf[kMaxLine + 1];
    size_t n = strlen(line);
    if (n > kMaxLine) {
        setWhy(why, whyLen, "line too long");
        return false;
    }
    memcpy(buf, line, n + 1);
    // strip CR/LF and trailing spaces
    while (n && (buf[n - 1] == '\r' || buf[n - 1] == '\n' || buf[n - 1] == ' ')) buf[--n] = '\0';

    char *tokens[8];
    int count = 0;
    for (char *p = strtok(buf, " "); p; p = strtok(nullptr, " ")) {
        if (count == 8) {
            setWhy(why, whyLen, "too many arguments");
            return false;
        }
        tokens[count++] = p;
    }
    if (count == 0) {
        code = err::kUnknownCmd;
        setWhy(why, whyLen, "empty line");
        return false;
    }

    struct Named { const char *name; CmdType type; };
    static const Named kCmds[] = {
        {"PING", CmdType::Ping},        {"INFO", CmdType::Info},   {"SCAN", CmdType::Scan},
        {"SELFTEST", CmdType::SelfTest}, {"CFG", CmdType::Cfg},     {"RUN", CmdType::Run},
        {"ABORT", CmdType::Abort},      {"STOPALL", CmdType::StopAll}, {"STATUS", CmdType::Status},
        {"LED", CmdType::Led},          {"REG", CmdType::Reg},   {"TRACE", CmdType::Trace},
    };
    bool found = false;
    for (const Named &c : kCmds) {
        if (strcmp(tokens[0], c.name) == 0) {
            out = Command();
            out.type = c.type;
            found = true;
            break;
        }
    }
    if (!found) {
        code = err::kUnknownCmd;
        setWhy(why, whyLen, "unknown command");
        return false;
    }

    // key=value arguments; each key at most once
    const char *keys[7] = {0};
    const char *vals[7] = {0};
    int nargs = count - 1;
    for (int i = 0; i < nargs; ++i) {
        char *eq = strchr(tokens[i + 1], '=');
        if (!eq || eq == tokens[i + 1] || !eq[1]) {
            setWhy(why, whyLen, "arguments must be key=value");
            return false;
        }
        *eq = '\0';
        keys[i] = tokens[i + 1];
        vals[i] = eq + 1;
        for (int j = 0; j < i; ++j) {
            if (strcmp(keys[j], keys[i]) == 0) {
                setWhy(why, whyLen, "duplicate argument");
                return false;
            }
        }
    }
    auto find = [&](const char *key) -> const char * {
        for (int i = 0; i < nargs; ++i)
            if (strcmp(keys[i], key) == 0) return vals[i];
        return nullptr;
    };
    auto onlyKeys = [&](const char *const *allowed, int nAllowed) -> bool {
        for (int i = 0; i < nargs; ++i) {
            bool ok = false;
            for (int j = 0; j < nAllowed; ++j)
                if (strcmp(keys[i], allowed[j]) == 0) ok = true;
            if (!ok) return false;
        }
        return true;
    };

    switch (out.type) {
        case CmdType::Cfg: {
            static const char *const allowed[] = {"roi", "tb", "imp", "mode"};
            if (!onlyKeys(allowed, 4) || nargs != 4) {
                setWhy(why, whyLen, "CFG needs exactly roi= tb= imp= mode=");
                return false;
            }
            uint32_t roi, tb, imp;
            if (!parseUint(find("roi"), 255, roi) || !parseUint(find("tb"), 65535, tb) ||
                !parseUint(find("imp"), 65535, imp)) {
                setWhy(why, whyLen, "roi, tb and imp must be whole numbers");
                return false;
            }
            const char *mode = find("mode");
            if (strcmp(mode, "short") == 0) out.settings.mode = DistanceMode::Short;
            else if (strcmp(mode, "long") == 0) out.settings.mode = DistanceMode::Long;
            else {
                setWhy(why, whyLen, "mode must be short or long");
                return false;
            }
            out.settings.roi = static_cast<uint8_t>(roi);
            out.settings.timingBudgetMs = static_cast<uint16_t>(tb);
            out.settings.interMeasurementMs = static_cast<uint16_t>(imp);
            if (const char *bad = validateSettings(out.settings)) {
                setWhy(why, whyLen, bad);
                return false;
            }
            return true;
        }
        case CmdType::Run: {
            static const char *const allowed[] = {"id", "cond", "dur"};
            if (!onlyKeys(allowed, 3) || nargs != 3) {
                setWhy(why, whyLen, "RUN needs exactly id= cond= dur=");
                return false;
            }
            const char *id = find("id");
            if (!validRunId(id)) {
                setWhy(why, whyLen, "id must be 1-24 chars of A-Z a-z 0-9 _ -");
                return false;
            }
            strcpy(out.run.id, id);
            const char *cond = find("cond");
            if (strcmp(cond, "A") == 0) out.run.cond = Condition::ASolo;
            else if (strcmp(cond, "B") == 0) out.run.cond = Condition::BSolo;
            else if (strcmp(cond, "AB") == 0) out.run.cond = Condition::Both;
            else {
                setWhy(why, whyLen, "cond must be A, B or AB");
                return false;
            }
            uint32_t dur;
            if (!parseUint(find("dur"), kMaxRunMs, dur) || dur < kMinRunMs) {
                setWhy(why, whyLen, "dur must be 100..3600000 ms");
                return false;
            }
            out.run.durationMs = dur;
            return true;
        }
        case CmdType::Trace: {
            static const char *const allowed[] = {"sensor", "ms", "path"};
            if (!onlyKeys(allowed, 3) || nargs < 2 || !find("sensor") || !find("ms")) {
                setWhy(why, whyLen, "TRACE needs sensor= ms= and optionally path=run");
                return false;
            }
            const char *path = find("path");
            if (path && strcmp(path, "run") != 0) {
                setWhy(why, whyLen, "path must be run");
                return false;
            }
            out.traceViaRun = path != nullptr;
            const char *sensor = find("sensor");
            if (strcmp(sensor, "A") == 0) out.regSensor = kSensorA;
            else if (strcmp(sensor, "B") == 0) out.regSensor = kSensorB;
            else {
                setWhy(why, whyLen, "sensor must be A or B");
                return false;
            }
            uint32_t ms;
            if (!parseUint(find("ms"), 3000, ms) || ms < 50) {
                setWhy(why, whyLen, "ms must be 50..3000");
                return false;
            }
            out.traceMs = static_cast<uint16_t>(ms);
            return true;
        }
        case CmdType::Reg: {
            static const char *const allowed[] = {"sensor", "addr", "len"};
            if (!onlyKeys(allowed, 3) || nargs != 3) {
                setWhy(why, whyLen, "REG needs exactly sensor= addr= len=");
                return false;
            }
            const char *sensor = find("sensor");
            if (strcmp(sensor, "A") == 0) out.regSensor = kSensorA;
            else if (strcmp(sensor, "B") == 0) out.regSensor = kSensorB;
            else {
                setWhy(why, whyLen, "sensor must be A or B");
                return false;
            }
            char *end = nullptr;
            unsigned long addr = strtoul(find("addr"), &end, 0);
            if (end == find("addr") || *end != '\0' || addr > 0xFFFF) {
                setWhy(why, whyLen, "addr must be a number up to 0xFFFF");
                return false;
            }
            uint32_t len;
            if (!parseUint(find("len"), 16, len) || len < 1) {
                setWhy(why, whyLen, "len must be 1..16");
                return false;
            }
            out.regAddr = static_cast<uint16_t>(addr);
            out.regLen = static_cast<uint8_t>(len);
            return true;
        }
        case CmdType::Led: {
            static const char *const allowed[] = {"state"};
            if (!onlyKeys(allowed, 1) || nargs != 1) {
                setWhy(why, whyLen, "LED needs exactly state=ok|bad|off");
                return false;
            }
            const char *state = find("state");
            if (strcmp(state, "ok") == 0) out.led = LedState::Ok;
            else if (strcmp(state, "bad") == 0) out.led = LedState::Bad;
            else if (strcmp(state, "off") == 0) out.led = LedState::Off;
            else {
                setWhy(why, whyLen, "state must be ok, bad or off");
                return false;
            }
            return true;
        }
        default:
            if (nargs != 0) {
                setWhy(why, whyLen, "command takes no arguments");
                return false;
            }
            return true;
    }
}

namespace {
size_t finish(int written, size_t len) {
    if (written < 0 || static_cast<size_t>(written) >= len) return 0;
    return static_cast<size_t>(written);
}
}  // namespace

size_t formatReading(char *buf, size_t len, const char *runId, const Reading &r) {
    int w = snprintf(buf, len, "D %s %c %llu %llu %u %u %lu %lu %u %u", runId, sensorName(r.sensor),
                     static_cast<unsigned long long>(r.tIntUs), static_cast<unsigned long long>(r.tReadUs),
                     static_cast<unsigned>(r.rangeMm), static_cast<unsigned>(r.status),
                     static_cast<unsigned long>(r.signalKcps), static_cast<unsigned long>(r.ambientKcps),
                     static_cast<unsigned>(r.spads), static_cast<unsigned>(r.stream));
    return finish(w, len);
}

size_t formatSettings(char *buf, size_t len, const SensorSettings &s) {
    int w = snprintf(buf, len, "roi=%u tb=%u imp=%u mode=%s", static_cast<unsigned>(s.roi),
                     static_cast<unsigned>(s.timingBudgetMs), static_cast<unsigned>(s.interMeasurementMs),
                     s.mode == DistanceMode::Short ? "short" : "long");
    return finish(w, len);
}

size_t formatRunEnd(char *buf, size_t len, const RunSummary &s) {
    int w = snprintf(buf, len,
                     "RUNEND id=%s cond=%s t0=%llu t1=%llu nA=%lu nB=%lu edgesA=%lu edgesB=%lu "
                     "overrunA=%lu overrunB=%lu rderrA=%lu rderrB=%lu buserr=%lu abort=%s",
                     s.id, conditionName(s.cond), static_cast<unsigned long long>(s.t0Us),
                     static_cast<unsigned long long>(s.t1Us), static_cast<unsigned long>(s.readings[0]),
                     static_cast<unsigned long>(s.readings[1]), static_cast<unsigned long>(s.edges[0]),
                     static_cast<unsigned long>(s.edges[1]), static_cast<unsigned long>(s.overruns[0]),
                     static_cast<unsigned long>(s.overruns[1]), static_cast<unsigned long>(s.readErrors[0]),
                     static_cast<unsigned long>(s.readErrors[1]), static_cast<unsigned long>(s.busErrors),
                     abortName(s.abort));
    return finish(w, len);
}

}  // namespace rig
