# Bio-Inspired Nuclear Donut Cooling Prototype - Materials List

## Core Components

### Heating System

- 1x Ceramic heating element (50-100W, soldering iron type)
- 1x PWM controller (DC motor/LED controller 12-24V)
- 1x K-type thermocouple with digital display, OR
- 6x DS18B20 digital temperature sensors (for full system feedback)

### Structure and Frame

- Aluminum extrusion 30x30mm (~2m total length)
- Fasteners, brackets, T-nuts
- Acrylic side panels (optional)
- 3D printed mounts and fan ducts

### Fractal Fin System (Lung/Gill Style)

- 1-2mm thick copper sheet (20x20 cm minimum)
- CNC or hand-cut fractal fin shapes
- Thermal paste or epoxy for fin bonding

### Heat Pipe Network (Circulatory Style)

- 4-6x 6mm x 150mm heat pipes (copper, sealed with water or acetone)
- Thermal epoxy or clamp system for attachment

### Phase Change Buffer (Sweat Gland Style)

- Paraffin wax (~500g)
- Aluminum container (small tray with lid)
- Clear acrylic window or cap
- Overflow tray and absorbent cloth

### Radiative Cooling Panel (Elephant Ear Style)

- 1x Flat copper panel (20cm x 30cm)
- Black anodized or painted matte black
- Vertical stand or back mounting plate

### Ventilation System (Respiratory Rhythm)

- 4x 40mm 12V cooling fans
- N-channel MOSFETs for PWM control
- Arduino Uno or Nano (controller brain)
- DHT22 (humidity + temp sensor)
- Hall-effect sensor (optional, for RPM feedback)

---

## Electrical and Monitoring

- Arduino Uno/Nano
- 1x SD card module (for data logging, optional)
- 1x LCD display (I2C 16x2 or 20x4)
- Breadboard or custom PCB
- 1x ACS712 current sensor
- Jumper wires, resistors (4.7k ohm for DS18B20), screw terminals
- Thermal fuse (180-250 C)
- 12V power supply (5A or more recommended)
- Buck converter (step down 12V to 5V for sensors)

---

## Safety and Extras

- Ceramic fiber blanket or insulation wrap
- Heat-resistant silicone wires
- Emergency shutdown button (momentary switch)
- LED + buzzer for overheat alarm
- Thermal paste and/or thermal pads
- Electrical tape, zip ties, hot glue

---

## Estimated Total Cost (USD)

| Category | Estimate |
|----------|----------|
| Electronics | ~$125 |
| Thermal system | ~$120 |
| Mechanical + Frame | ~$90 |
| Misc materials | ~$60 |
| **Total** | **~$395-$450** |

*Expand as needed based on build scope.*
