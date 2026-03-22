# Controller Overview

**Goal:** Python + Arduino system for managing cooling modes based on temperature, humidity, sensor status, and time.

---

## System Architecture

### Controller Board

- Arduino Uno (or Nano for compact build)
- 12V Power input (buck converter to 5V for logic)

### Sensors

- DS18B20 - 6x digital temp sensors
- DHT22 - for ambient humidity
- ACS712 current sensor - for load monitoring
- ThermalSpike switch (normally closed thermal fuse)

### Actuators

- 4x 40mm Fans - PWM control via N-channel MOSFETs
- Heating element - via relay (or solid-state relay)
- Emergency buzzer + LED (status indicator)

---

## Wiring Plan

### Power Wiring

```
12V Input
├──> Buck Converter (5V logic)
├──> Fans (through MOSFETs)
└──> Relay → Heating Element
```

### Sensor Wiring

```
DS18B20: Digital (D2-D7) + shared pull-up resistor
DHT22:   Digital pin D8
ACS712:  Analog A0
Thermal Spike: Digital pin D9 (input w/ pull-down)
```

### Output Wiring

```
Fan 1 → D10 (PWM via MOSFET)
Fan 2 → D11
Fan 3 → D3
Fan 4 → D5
Relay → D6
Buzzer/LED → D12
```

---

## Mode Logic (Arduino C)

```c
// Mode Logic Trigger Definitions
enum Mode { IDLE, PULSE, EVAP, GEO, MAX, ADAPTIVE, EMERGENCY };
Mode currentMode = IDLE;

void updateMode() {
  float temp = readAverageTemp();
  float humidity = readHumidity();
  bool spike = digitalRead(THERMAL_SPIKE_PIN) == HIGH;

  if (spike) currentMode = EMERGENCY;
  else if (temp > 80 && humidity > 40) currentMode = EVAP;
  else if (temp > 85) currentMode = MAX;
  else if (temp > 60 && humidity < 20) currentMode = GEO;
  else if (temp > 40) currentMode = PULSE;
  else currentMode = IDLE;
}

// Fan Control Patterns
void applyFanPattern(Mode m) {
  switch (m) {
    case IDLE:
      setAllFans(0);
      break;
    case PULSE:
      pulseFansRhythmically();
      break;
    case EVAP:
      setAllFans(200);
      break;
    case GEO:
      fanVentCycle(150);
      break;
    case MAX:
      setAllFans(255);
      break;
    case ADAPTIVE:
      smartControl();
      break;
    case EMERGENCY:
      setAllFans(255);
      buzzAlert();
      break;
  }
}

void loop() {
  updateMode();
  applyFanPattern(currentMode);
  delay(500);
}
```

---

## Mode Summary

| Mode | Trigger | Bio-Inspiration |
|------|---------|-----------------|
| `idle()` | Low temp, nighttime, no load | Night cycle |
| `pulse_cooling()` | Rhythmic fan pulses | Respiration |
| `evaporative()` | High humidity + heat | Termite logic |
| `geothermal()` | Dry + heat | Moist coil circulation |
| `max_cooling()` | Spike or overload | Fight-or-flight |
| `adaptive()` | Blend of sensor logic | Homeostasis |
| `emergency()` | Hibernate or shut down | Survival mode |

*Note: Made on notes on cellphone - not production code.*
