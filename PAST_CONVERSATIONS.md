

/



Deliberated USB port compatibility and identified necessary code modifications

Deliberated USB port compatibility and identified necessary code modifications

Which physical port

Any of the Pi's USB-A ports works — the Pi 4B has 4 total (2 black USB2, 2 blue USB3). Plug a standard USB-A-to-USB-C cable from any Pi USB-A port into the ESP32-S3's USB-C port. There's no "correct" one functionally, since USB is host/device, not a fixed lane — but I'd reserve a USB3 (blue) port for your D500 lidar if it also connects via a USB-serial adapter (rather than raw UART pins), since lidar data is higher-bandwidth. Put the ESP32 on a USB2 (black) port — it only needs to carry a tiny ASCII command line, no bandwidth concern there.



Code changes — Pi side (serial\_link.py)

Just the port string, nothing else in the file changes:



python

\# before (GPIO UART):

link = SerialLink(port="/dev/serial0", baud=115200, send\_hz=30)



\# after (USB):

link = SerialLink(port="/dev/ttyUSB0", baud=115200, send\_hz=30)

Plug the ESP32 in, then check which device node it actually got assigned — it may be /dev/ttyACM0 instead of /dev/ttyUSB0 depending on its USB-serial chip:



bash

dmesg | tail -20

ls /dev/ttyUSB\* /dev/ttyACM\* 2>/dev/null

Whatever shows up there is what you put in the port= argument. If you also have the D500 on a USB-serial adapter, you'll have two entries (e.g. ttyUSB0 and ttyUSB1) — check dmesg carefully to know which is which, since the assignment order isn't guaranteed to be consistent across reboots. If that matters for reliability, you can pin them with a udev rule later (I can write that if you want).



Code changes — ESP32 side (Arduino sketch)

Use the default Serial object instead of Serial1, since USB serial is Serial:



cpp

void setup() {

&#x20; Serial.begin(115200);

&#x20; // ... rest of your servo/motor setup

}



void loop() {

&#x20; if (Serial.available()) {

&#x20;   // read and parse the "S<angle>,<speed>\\n" line, same as before

&#x20; }

&#x20; // ... PD/slew/watchdog logic unchanged

}

That's the entire change on the ESP32 side — same baud rate, same protocol, same parsing logic, just a different Serial object.



One consequence to plan for

Since Serial now carries your live command stream, you lose it as a free debug-print channel — Serial.println("debug info") would get mixed into the same stream your parser is reading, which will break your parsing. If you want debug output during development, either:



Temporarily comment out debug prints when running for real, or

Use Serial1 on spare GPIO pins purely for debug output (keeping Serial/USB purely for Pi commands)

Want me to add that second debug-UART option into the ESP32 sketch structure, or move on to state\_machine.py now that the link is settled?



rewrite serial\_link.py to be connected via usb





Improvised text-based code presentation after tools malfunctioned

Improvised text-based code presentation after tools malfunctioned

Looks like my file tools dropped out mid-conversation — I'll just give you the full file here instead so you're not stuck.



python

"""

serial\_link.py



Owns the USB-serial connection to the ESP32-S3 (connected via USB-A on

the Pi to USB-C on the ESP32 - the ESP32's native USB-serial bridge).

Takes whatever target\_angle / target\_speed the state machine last

computed and writes it as a simple ASCII command line, at a fixed rate,

on its own thread.



Protocol (must match the ESP32 sketch exactly - ESP32 side uses the

default `Serial` object since it's USB, not Serial1/GPIO UART):

&#x20;   "S<angle>,<speed>\\n"

&#x20;   e.g. "S92,180\\n"



&#x20;   angle: servo write value, 0-180 (int)

&#x20;   speed: motor PWM/speed value, -255..255 (int; sign = direction, if used)



Port note:

&#x20;   Over USB the ESP32 will show up as /dev/ttyUSB0 or /dev/ttyACM0

&#x20;   depending on its USB-serial chip - check with:

&#x20;       dmesg | tail -20

&#x20;       ls /dev/ttyUSB\* /dev/ttyACM\* 2>/dev/null

&#x20;   after plugging it in. If you also have a USB-serial lidar adapter,

&#x20;   double check dmesg carefully so you don't mix up which device node

&#x20;   is which - device assignment order isn't guaranteed across reboots.

&#x20;   Consider a udev rule to pin a stable name if this bites you.



Reconnect note:

&#x20;   Unlike a fixed GPIO UART, a USB connection can be unplugged, or the

&#x20;   ESP32 can reset/re-enumerate (e.g. after a firmware flash), which

&#x20;   changes or drops the device node. This version retries opening the

&#x20;   port if it disappears, instead of just dying silently.



Decoupling note:

&#x20;   This runs its own send-rate loop independent of how fast the state

&#x20;   machine computes new targets. If the state machine is momentarily

&#x20;   slow (e.g. a vision frame takes longer), serial\_link just re-sends

&#x20;   the last known target rather than stalling - the ESP32's own

&#x20;   watchdog handles the case where targets go stale for too long.



Usage:

&#x20;   link = SerialLink(port="/dev/ttyUSB0", baud=115200, send\_hz=30)

&#x20;   link.start()

&#x20;   ...

&#x20;   link.set\_target(angle=95, speed=150)   # called by state machine each cycle

&#x20;   ...

&#x20;   link.stop()

"""



import glob

import threading

import time



import serial





class SerialLink:

&#x20;   def \_\_init\_\_(self, port="/dev/ttyUSB0", baud=115200, send\_hz=30, log\_path=None,

&#x20;                auto\_detect=True):

&#x20;       self.port = port

&#x20;       self.baud = baud

&#x20;       self.send\_interval = 1.0 / send\_hz

&#x20;       self.auto\_detect = auto\_detect



&#x20;       self.\_ser = None

&#x20;       self.\_thread = None

&#x20;       self.\_running = False

&#x20;       self.\_connected = False



&#x20;       self.\_lock = threading.Lock()

&#x20;       self.\_target\_angle = 86   # neutral/straight, matches your servo calibration

&#x20;       self.\_target\_speed = 0    # stopped by default until state machine says otherwise



&#x20;       self.\_log\_path = log\_path

&#x20;       self.\_log\_file = None



&#x20;   def start(self):

&#x20;       if self.\_log\_path:

&#x20;           self.\_log\_file = open(self.\_log\_path, "a", buffering=1)



&#x20;       self.\_running = True

&#x20;       self.\_thread = threading.Thread(target=self.\_run, daemon=True)

&#x20;       self.\_thread.start()



&#x20;   def stop(self):

&#x20;       self.\_running = False

&#x20;       if self.\_thread:

&#x20;           self.\_thread.join(timeout=1.0)

&#x20;       if self.\_ser:

&#x20;           try:

&#x20;               self.\_ser.write(b"S86,0\\n")  # final stop command before closing

&#x20;           except serial.SerialException:

&#x20;               pass

&#x20;           self.\_ser.close()

&#x20;       if self.\_log\_file:

&#x20;           self.\_log\_file.close()



&#x20;   def set\_target(self, angle, speed):

&#x20;       """Called by the state machine every cycle with its latest computed targets."""

&#x20;       angle = int(max(0, min(180, angle)))     # clamp to valid servo range

&#x20;       speed = int(max(-255, min(255, speed)))  # clamp to valid motor range

&#x20;       with self.\_lock:

&#x20;           self.\_target\_angle = angle

&#x20;           self.\_target\_speed = speed



&#x20;   def emergency\_stop(self):

&#x20;       """Immediately zero speed, keep last steering angle. Call on fault conditions

&#x20;       (e.g. lidar/camera stale, unexpected exception in the state machine, or

&#x20;       this link being disconnected)."""

&#x20;       with self.\_lock:

&#x20;           self.\_target\_speed = 0



&#x20;   def is\_connected(self):

&#x20;       return self.\_connected



&#x20;   # -- internals --------------------------------------------------------



&#x20;   def \_find\_port(self):

&#x20;       """Best-effort auto-detect: prefer the configured port if present,

&#x20;       otherwise scan common USB-serial device node patterns."""

&#x20;       candidates = \[self.port] + sorted(glob.glob("/dev/ttyUSB\*") + glob.glob("/dev/ttyACM\*"))

&#x20;       for c in candidates:

&#x20;           if c and glob.glob(c):

&#x20;               return c

&#x20;       return None



&#x20;   def \_try\_connect(self):

&#x20;       port = self.\_find\_port() if self.auto\_detect else self.port

&#x20;       if not port:

&#x20;           return False

&#x20;       try:

&#x20;           self.\_ser = serial.Serial(port, self.baud, timeout=0.1)

&#x20;           time.sleep(1.5)  # ESP32-S3 USB-CDC typically resets on port open

&#x20;           self.\_connected = True

&#x20;           self.port = port  # remember whichever one actually worked

&#x20;           return True

&#x20;       except serial.SerialException:

&#x20;           self.\_ser = None

&#x20;           self.\_connected = False

&#x20;           return False



&#x20;   def \_run(self):

&#x20;       next\_send = time.time()

&#x20;       while self.\_running:

&#x20;           if not self.\_connected:

&#x20;               if not self.\_try\_connect():

&#x20;                   time.sleep(0.5)  # USB not present yet / ESP32 not plugged in

&#x20;                   continue



&#x20;           now = time.time()

&#x20;           if now >= next\_send:

&#x20;               with self.\_lock:

&#x20;                   angle = self.\_target\_angle

&#x20;                   speed = self.\_target\_speed



&#x20;               line = f"S{angle},{speed}\\n"

&#x20;               try:

&#x20;                   self.\_ser.write(line.encode("ascii"))

&#x20;               except serial.SerialException:

&#x20;                   # cable unplugged or ESP32 re-enumerated (e.g. after reflash)

&#x20;                   self.\_connected = False

&#x20;                   self.\_ser = None



&#x20;               if self.\_log\_file:

&#x20;                   self.\_log\_file.write(f"{now:.3f},{angle},{speed}\\n")



&#x20;               next\_send += self.send\_interval

&#x20;               if next\_send < now:  # fell behind, resync instead of burst-sending

&#x20;                   next\_send = now + self.send\_interval

&#x20;           else:

&#x20;               time.sleep(min(0.002, next\_send - now))





if \_\_name\_\_ == "\_\_main\_\_":

&#x20;   # Quick standalone test: sweep the servo target back and forth, speed=0

&#x20;   link = SerialLink(baud=115200, send\_hz=30, auto\_detect=True)

&#x20;   link.start()

&#x20;   try:

&#x20;       angle = 86

&#x20;       direction = 1

&#x20;       while True:

&#x20;           angle += direction \* 2

&#x20;           if angle >= 115 or angle <= 50:

&#x20;               direction \*= -1

&#x20;           link.set\_target(angle=angle, speed=0)

&#x20;           print(f"sent angle={angle} speed=0 connected={link.is\_connected()} port={link.port}")

&#x20;           time.sleep(0.1)

&#x20;   except KeyboardInterrupt:

&#x20;       pass

&#x20;   finally:

&#x20;       link.stop()

What changed from the GPIO-UART version, and why:



port defaults to /dev/ttyUSB0 instead of /dev/serial0, and there's an auto\_detect option that scans for ttyUSB\*/ttyACM\* if the configured one isn't present — since USB device names aren't as fixed as GPIO ports.

\_try\_connect() / reconnect loop — a USB cable can get bumped loose mid-run, or the ESP32 can re-enumerate after you reflash it. Instead of the whole thing crashing, the send loop just keeps retrying to reconnect every 0.5s and picks back up once the device reappears.

is\_connected() — useful in main.py to show a status indicator or trigger emergency\_stop() elsewhere if the link drops.

Longer settle delay (1.5s vs 0.5s) after opening the port — ESP32-S3 boards commonly reset their USB-CDC connection when the port opens, so it needs a beat to come back up before you start writing to it.

Everything else — the protocol, the clamping, the fixed send-rate loop, the final stop-on-close — is unchanged from the GPIO version.



Try running the standalone test block at the bottom first (python serial\_link.py) once wired up — it'll print whether it connected and which port it landed on, which answers the ttyUSB0 vs ttyACM0 question for your specific board without you needing to dig through dmesg by hand.







