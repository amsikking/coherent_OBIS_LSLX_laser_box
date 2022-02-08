import numpy as np
import coherent_OBIS_LSLX_laser_box
import ni_PCIe_6738

# initialize:
lb = coherent_OBIS_LSLX_laser_box.Controller(
    'COM11', control_mode='analog', verbose=False)
ao = ni_PCIe_6738.DAQ(num_channels=10, rate=1e5, verbose=False)

# set max voltages, pulse options and channels:
ttl_high_v = 3
max_pwr_v = 4.5
num_pulses = 5
pwr_inc_v = max_pwr_v/num_pulses
pulse_s = 0.1
duty_cycle = 0.5    # Fraction of period to be high (range 0 to 1)
ao_channels = {'ttl405' :0, 'pwr405' :1,
               'ttl445' :2, 'pwr445' :3,
               'ttl488' :4, 'pwr488' :5,
               'ttl561' :6, 'pwr561' :7,
               'ttl640' :8, 'pwr640' :9,}

# calculate voltages:
pulse_px = ao.s2p(pulse_s)
pulse_high_px = ao.s2p(pulse_s * duty_cycle)
names = list(ao_channels.keys())
voltage_series = []
for num_lasers in range(int(len(ao_channels)/2)):
    for i in range(num_pulses):
        name_index = 2 * num_lasers
        v = np.zeros((pulse_px, ao.num_channels), 'float64')
        v[pulse_high_px:, ao_channels[names[name_index]]] = ttl_high_v
        v[pulse_high_px:, ao_channels[names[name_index + 1]]] = i * pwr_inc_v
        voltage_series.append(v)
voltages = np.concatenate(voltage_series)

print('enabling lasers!')
for laser in lb.lasers:
    lb.set_enable('ON', laser)

print('playing laser pulse train...')
ao.play_voltages(voltages, block=True)
print('done!')

ao.close()
lb.close()
