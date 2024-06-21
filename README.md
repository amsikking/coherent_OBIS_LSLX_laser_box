# coherent_OBIS_LSLX_laser_box
Python device adaptor: Coherent OBIS LS/LX laser box.
## Quick start:
- Install the 'Coherent Connection' GUI (includes USB driver).
  - Edit the 'device exclusion list' in the GUI to stop it from spamming all the COM ports (which can upset other devices).
- ***Shutter lasers (or otherwise make safe for laser emission)***
- Run either the main script or the 'analog' control example.

![social_preview](https://github.com/amsikking/coherent_OBIS_LSLX_laser_box/blob/main/social_preview.png)

## Details:
This adaptor was tested with the following system:
  * OBIS LX/LS laser box, (2KΩ and 50Ω input impedance versions), 5 bay with power supply (SKU 1343229)
  * OBIS Galaxy 8 laser combiner, single fiber output, 405, 445, 488, 514, 532, 561, 594, 640 nm (SKU 1363484)
  * OBIS LX 405 nm 100 mW laser, fiber pigtail, UFC, Galaxy (SKU 1236439)
  * OBIS LX 445 nm 045 mW laser, fiber pigtail, UFC, Galaxy (SKU 1236441)
  * OBIS LX 488 nm 100 mW laser, fiber pigtail, UFC, Galaxy (SKU 1236444)
  * OBIS LS 561 nm 080 mW laser, fiber pigtail, UFC, Galaxy (SKU 1275608)
  * OBIS LX 640 nm 075 mW laser, fiber pigtail, UFC, Galaxy (SKU 1236445)
