# Red Light Green Light

The is the complementary repository for the [YouTube video](https://youtu.be/us6YPp9sNJM) if you'd like to build the device yourself. The 3D printed dimensions and components were just things I had already and they may need to be adjusted or measured to make sure things can fit together. This repository is not actively maintained and is for reference only.

## Components

* **Raspberry Pi 4**
* **Camera Module** MIPI cable with an M12 lens
* **Speaker** (4-8 Ohms)
* **Speaker Driver** I used [this](https://www.adafruit.com/product/1712?srsltid=AfmBOoq_AxPEJK-G3gEHl4EGK_BYMAdxlRwtLCri5BFdHOFroN6RoFGb)
* **Speaker Cable** to connect Raspberry Pi audio jack to amplifier
* **Fan and heat-sink** There's built-in holes for a standard 40mm PC fan
* **Push button** I used one from an old hoverboard
* **16 standard RGB LEDs**
* **48 resistors** for LEDs about ~1000 Ohm
* **LED driver** I used a quad H-bridge l293dne
* **Small breadboard** for the LED driver
* **USB-C right angle connector** (It was something like [this](https://www.amazon.com/dp/B07JKBKM12) but I peeled off the outer plastic to make it more compact.)
* **Standard reed switch**
* **Lots of wires** to connect everything
* **Small neodymium magnet** cylinder shape
* **4 small screws** to hold raspberry pi
* **4 small screws** to hold camera module
* **4 large M5 screws** to hold the lid
* **4 PC fan screws** to hold the fan 
* **Random nuts and bolts** for the counterweight (needs tuning)

## Software

I am using the Bookworm version of the Raspberry Pi OS.

The python application rlgl.py should be configured to run on startup. The easiest way is to add it to .bashrc. You will need to install some dependencies, these include:

* pygame
* picamera2
* Pillow
* numpy

The GPIO pins I'm using are defined in rlgl.py under "#Define GPIO". These can be changed to whatever pins you'd like to use in your configuration.