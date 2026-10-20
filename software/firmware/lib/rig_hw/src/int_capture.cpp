// Author: Jessica
#include "int_capture.h"

#include <Arduino.h>
#include <esp_timer.h>

namespace {

struct Slot {
    volatile uint64_t stamp = 0;
    volatile bool pending = false;
    volatile uint32_t edges = 0;
    volatile uint32_t overruns = 0;
};

Slot g_slot[rig::kNumSensors];
portMUX_TYPE g_lock = portMUX_INITIALIZER_UNLOCKED;

// esp_timer_get_time() is IRAM-resident and safe to call from an ISR; it is
// the same 1 us time base the rest of the firmware uses.
void IRAM_ATTR onEdge(Slot &slot) {
    uint64_t t = static_cast<uint64_t>(esp_timer_get_time());
    portENTER_CRITICAL_ISR(&g_lock);
    slot.edges = slot.edges + 1;
    if (slot.pending) slot.overruns = slot.overruns + 1;   // keep the newest stamp
    slot.stamp = t;
    slot.pending = true;
    portEXIT_CRITICAL_ISR(&g_lock);
}

// The capture listens to both edges and counts a data-ready event only when the pin reads low in the ISR. A
// falling-edge-only interrupt counted some falling edges twice on one DevKitC-1 (every second reading a repeat), while
// this form, checked against the pin level, counted each fall once. The low pulse lasts about 0.7 ms, far longer than
// the ISR latency, so no real event is missed.
volatile int g_pin[rig::kNumSensors] = {-1, -1};

void IRAM_ATTR onChange(uint8_t s) {
    if (gpio_get_level(static_cast<gpio_num_t>(g_pin[s])) == 0) onEdge(g_slot[s]);
}
void IRAM_ATTR isrA() { onChange(rig::kSensorA); }
void IRAM_ATTR isrB() { onChange(rig::kSensorB); }

// ---- trace ring (both edges of one pin)
struct TraceEntry {
    uint64_t t;
    uint8_t level;
};
TraceEntry g_trace[IntCapture::kTraceMax];
volatile int g_traceN = 0;
volatile bool g_traceOver = false;
volatile int g_tracePin = -1;
volatile int g_traceSlot = -1;   // >= 0: also feed the normal capture of this sensor on each falling level

void IRAM_ATTR onTrace() {
    uint64_t t = static_cast<uint64_t>(esp_timer_get_time());
    int lvl = gpio_get_level(static_cast<gpio_num_t>(g_tracePin));
    portENTER_CRITICAL_ISR(&g_lock);
    if (g_traceSlot >= 0 && lvl == 0) {
        Slot &slot = g_slot[g_traceSlot];
        slot.edges = slot.edges + 1;
        if (slot.pending) slot.overruns = slot.overruns + 1;
        slot.stamp = t;
        slot.pending = true;
    }
    if (g_traceN < IntCapture::kTraceMax) {
        g_trace[g_traceN].t = t;
        g_trace[g_traceN].level = static_cast<uint8_t>(lvl);
        g_traceN = g_traceN + 1;
    } else {
        g_traceOver = true;
    }
    portEXIT_CRITICAL_ISR(&g_lock);
}

}  // namespace

void IntCapture::begin(const int pins[rig::kNumSensors]) {
    for (uint8_t s = 0; s < rig::kNumSensors; ++s) {
        pins_[s] = pins[s];
        g_pin[s] = pins[s];
        pinMode(pins[s], INPUT);
    }
    reset();
    // GPIO1 is configured active low: data ready = pin low (see onChange).
    attachInterrupt(digitalPinToInterrupt(pins[rig::kSensorA]), isrA, CHANGE);
    attachInterrupt(digitalPinToInterrupt(pins[rig::kSensorB]), isrB, CHANGE);
}

void IntCapture::beginTrace(uint8_t s, bool alsoCapture) {
    detachInterrupt(digitalPinToInterrupt(pins_[s]));
    portENTER_CRITICAL(&g_lock);
    g_traceN = 0;
    g_traceOver = false;
    g_traceSlot = alsoCapture ? s : -1;
    g_tracePin = pins_[s];
    portEXIT_CRITICAL(&g_lock);
    attachInterrupt(digitalPinToInterrupt(pins_[s]), onTrace, CHANGE);
}

void IntCapture::endTrace() {
    if (g_tracePin < 0) return;
    detachInterrupt(digitalPinToInterrupt(g_tracePin));
    // back to the normal falling-edge capture on both pins
    detachInterrupt(digitalPinToInterrupt(pins_[rig::kSensorA]));
    detachInterrupt(digitalPinToInterrupt(pins_[rig::kSensorB]));
    reset();
    attachInterrupt(digitalPinToInterrupt(pins_[rig::kSensorA]), isrA, CHANGE);
    attachInterrupt(digitalPinToInterrupt(pins_[rig::kSensorB]), isrB, CHANGE);
    g_tracePin = -1;
    g_traceSlot = -1;
}

int IntCapture::traceCount() const { return g_traceN; }
bool IntCapture::traceOverflowed() const { return g_traceOver; }

bool IntCapture::traceAt(int i, int &level, uint64_t &tUs) const {
    if (i < 0 || i >= g_traceN) return false;
    level = g_trace[i].level;
    tUs = g_trace[i].t;
    return true;
}

bool IntCapture::takeEdge(uint8_t s, uint64_t &tUs) {
    bool had = false;
    portENTER_CRITICAL(&g_lock);
    if (g_slot[s].pending) {
        tUs = g_slot[s].stamp;
        g_slot[s].pending = false;
        had = true;
    }
    portEXIT_CRITICAL(&g_lock);
    return had;
}

uint32_t IntCapture::edgeCount(uint8_t s) const { return g_slot[s].edges; }
uint32_t IntCapture::overrunCount(uint8_t s) const { return g_slot[s].overruns; }

void IntCapture::reset() {
    portENTER_CRITICAL(&g_lock);
    for (Slot &slot : g_slot) {
        slot.pending = false;
        slot.edges = 0;
        slot.overruns = 0;
    }
    portEXIT_CRITICAL(&g_lock);
}

int IntCapture::level(uint8_t s) const { return digitalRead(pins_[s]); }
