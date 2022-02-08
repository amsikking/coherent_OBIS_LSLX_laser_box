import serial

class Controller:
    '''
    ***WARNING: THIS SCRIPT CAN FIRE LASER EMISSION! SHUTTER LASERS FIRST***
    Basic device adaptor for a Coherent OBIS LS/LX laser box (populated with
    OBIS LX/LS lasers). Many more commands are available and have not been
    implemented.
    '''
    def __init__(self,
                 which_port,            # COM port for laser box
                 control_mode='USB',    # 'USB' or 'analog'
                 name='OBIS_laser_box', # optional name
                 name2channel=None,     # optional dict -> name to SCPI channel
                 verbose=True,          # False for max speed
                 very_verbose=False):   # True for debug
        self.name = name
        self.verbose = verbose
        self.very_verbose = very_verbose
        if self.verbose: print('%s: opening...'%name, end='')
        try:
            self.port = serial.Serial(port=which_port, baudrate=115200)
        except serial.serialutil.SerialException:
            raise IOError('%s: No connection on port %s'%(name, which_port))
        if self.verbose: print(" done.")
        # Find devices:
        self.device_identities = {}
        self.name2channel = {}
        for ch in range(6): # max devices -> 1 box + 5 lasers = 6
            try:
                self.device_identities[ch] = self._get_device_id(ch) # all
                # wavelength call ejects laser box USB hub (it has no wavelenth)
                wavelength = self._send('SYSTem%i:INFormation:WAVelength?'%ch)
                self.name2channel[wavelength.split('.')[0]] = ch # lasers only
            except OSError as e:
                if e.args[0] not in (
                    'Controller error: Device unavailable',
                    'Controller error: Unrecognized command/query'):
                    raise
        if name2channel is not None: # use nicknames if provided
            for nickname, channel in name2channel.items():
                assert channel != 0, (
                    '%s: channel 0 is reserved for the laser box USB'%name)
                assert channel in self.device_identities.keys(), (
                    '%s: channel %s not available'%(name, channel))
                assert type(nickname) is str
            self.name2channel = name2channel
        self.lasers = tuple(self.name2channel.keys())
        # Configure lasers:
        self.wavelength,        self.device_type        =   {}, {}
        self.min_power_w,       self.max_power_w        =   {}, {}
        self.CDRH_delay,        self.autostart          =   {}, {}
        self.power_setpoint_w,  self.power_setpoint_pct =   {}, {}
        self.control_mode,      self.enable             =   {}, {}
        self.min_power_pct = {} # OPSL lasers can't go to zero (e.g. 561)
        for name in self.lasers:
            self._get_wavelength(name)                  # set attribute
            self._get_device_type(name)                 # determines options
            self._get_min_power(name)                   # set attribute
            self._get_max_power(name)                   # set attribute
            self.min_power_pct[name] = round(
                (100 * self.min_power_w[name] / self.max_power_w[name]), 2)
            self._set_CDRH_delay('OFF', name)           # needed for enable
            self._set_autostart('OFF', name)            # safety
            self.set_enable('OFF', name)                # safety
            self.set_control_mode(control_mode, name)   # default 'USB'     
            self.set_power_setpoint(                    # safety
                self.min_power_pct[name], name)         

    def _send(self, cmd, reply=True):
        assert isinstance(cmd, str)
        cmd = bytes(cmd + '\r', 'ascii')
        if self.very_verbose: print("%s: sending cmd = "%self.name, cmd)
        self.port.write(cmd)
        response = None
        if reply:
            response = self.port.readline().decode('ascii').strip('\r\n')
            self._check_error(response)
        handshake = self.port.readline()
        if handshake != b'OK\r\n':
            raise OSError('Unexpected handshake:', self._check_error(handshake))
        assert self.port.in_waiting == 0
        if self.very_verbose: print("%s: -> response = "%self.name, response)
        return response

    def _check_error(self, response):
        if response[:3] == 'ERR':
            error_codes = {
                'ERR-400':'Query unavailable',
                'ERR-350':'Queue overflow',
                'ERR-321':'Out of memory',
                'ERR-310':'System error',
                'ERR-257':'File to open not named',
                'ERR-256':'File does not exist',
                'ERR-241':'Device unavailable',
                'ERR-221':'Settings conflict',
                'ERR-220':'Invalid parameter',
                'ERR-203':'Command protected',
                'ERR-200':'Execution error',
                'ERR-109':'Parameter missing',
                'ERR-102':'Syntax error',
                'ERR-100':'Unrecognized command/query',
                'ERR-000':'No error',
                'ERR-500':'CCB fault',
                'ERR-510':'I2C bus fault',
                'ERR-520':'Controller time out',
                'ERR-900':'CCB message timed out',
                }
            raise OSError('Controller error: ' + error_codes[response])
        return None

    def _get_device_id(self, channel):
        if self.verbose:
            print("%s(ch%i): getting device id"%(self.name, channel))
        device_id = self._send('*IDN%i?'%channel)
        if self.verbose:
            print("%s(ch%i): -> device id = %s"%(self.name, channel, device_id))
        return device_id

    def _get_wavelength(self, name):
        if self.verbose:
            print("%s(%s): getting wavelength"%(self.name, name))        
        ch = self.name2channel[name]
        self.wavelength[name] = self._send(
            'SYSTem%i:INFormation:WAVelength?'%ch)
        if self.verbose:
            print("%s(%s): -> wavelength (nm) = %s"%(
                self.name, name, self.wavelength[name]))
        return self.wavelength[name]

    def _get_device_type(self, name):
        if self.verbose:
            print("%s(%s): getting device type"%(self.name, name))
        ch = self.name2channel[name]
        self.device_type[name] = self._send('SYSTem%i:INFormation:TYPe?'%ch)
        if self.verbose:
            print("%s(%s): -> device type = %s"%(
                self.name, name, self.device_type[name]))
        return self.device_type[name]

    def _get_min_power(self, name):
        if self.verbose:
            print("%s(%s): getting min power (W)"%(self.name, name))
        ch = self.name2channel[name]
        self.min_power_w[name] = float(
            self._send('SOURce%i:POWer:LIMit:LOW?'%ch))
        if self.verbose:
            print("%s(%s): -> min power (W) = %0.3f"%(
                self.name, name, self.min_power_w[name]))
        return self.min_power_w[name]

    def _get_max_power(self, name):
        if self.verbose:
            print("%s(%s): getting max power (W)"%(self.name, name))
        ch = self.name2channel[name]
        self.max_power_w[name] = float(
            self._send('SYSTem%i:INFormation:POWer?'%ch))
        if self.verbose:
            print("%s(%s): -> max power (W) = %0.3f"%(
                self.name, name, self.max_power_w[name]))
        return self.max_power_w[name]

    def _get_CDRH_delay(self, name):
        if self.verbose:
            print("%s(%s): getting CDRH delay"%(self.name, name))
        ch = self.name2channel[name]
        self.CDRH_delay[name] = self._send('SYSTem%i:CDRH?'%ch)
        if self.verbose:
            print("%s(%s): -> CDRH delay = %s"%(
                self.name, name, self.CDRH_delay[name]))
        return self.CDRH_delay[name]

    def _set_CDRH_delay(self, mode, name):
        if self.verbose:
            print("%s(%s): setting CDRH delay = %s"%(self.name, name, mode))        
        ch = self.name2channel[name]
        assert mode in ('OFF', 'ON')
        self._send('SYSTem%i:CDRH '%ch + mode, reply=False)
        assert self._get_CDRH_delay(name) == mode
        if self.verbose:
            print("%s(%s): -> done setting CDRH delay."%(self.name, name))
        return None

    def _get_autostart(self, name):
        if self.verbose:
            print("%s(%s): getting autostart"%(self.name, name))
        ch = self.name2channel[name]
        self.autostart[name] = self._send('SYSTem%i:AUTostart?'%ch)
        if self.verbose:
            print("%s(%s): -> autostart = %s"%(
                self.name, name, self.autostart[name]))
        return self.autostart[name]

    def _set_autostart(self, mode, name):
        if self.verbose:
            print("%s(%s): setting autostart = %s"%(self.name, name, mode))
        ch = self.name2channel[name]
        assert mode in ('OFF', 'ON')
        self._send('SYSTem%i:AUTostart '%ch + mode, reply=False)
        assert self._get_autostart(name) == mode
        if self.verbose:
            print("%s(%s): -> done setting autostart."%(self.name, name))
        return None

    def get_control_mode(self, name):
        """
        CWP = continuous wave, constant power
        CWC = continuous wave, constant current
        DIGITAL = CW with external digital modulation
        ANALOG = CW with external analog modulation
        MIXED = CW with external digital + analog modulation
        DIGSO = External digital modulation with power feedback
        MIXSO = External mixed modulation with power feedback
        """
        if self.verbose:
            print("%s(%s): getting control mode"%(self.name, name))
        ch = self.name2channel[name]
        control_mode = self._send('SOURce%i:AM:SOURce?'%ch)
        if control_mode == 'CWP':
            self.control_mode[name] = 'USB'
        elif control_mode in ('MIXED','MIXSO'):
            self.control_mode[name] = 'analog'
        else:
            raise Exception('%s(%s): unsupported control mode %s'%(
                self.name, name, control_mode))
        if self.verbose:
            print("%s(%s): -> control mode = %s"%(
                self.name, name, self.control_mode[name]))
        return self.control_mode[name]

    def set_control_mode(self, mode, name):
        if self.verbose:
            print("%s(%s): setting control mode = %s"%(self.name, name, mode))
        assert mode in ('USB', 'analog')
        re_enable = False
        if self.enable[name] == 'ON':
            self.set_enable('OFF', name)
            re_enable = True
        ch = self.name2channel[name]
        if mode == 'USB': # power feedback with closed light-loop
            self._send('SOURce%i:AM:INTernal CWP'%ch, reply=False)
        if mode == 'analog': # power feedback with closed light-loop
            assert self.device_type[name] in ('DDL', 'OPSL')
            if self.device_type[name] == 'DDL':
                self._send('SOURce%i:AM:EXTernal MIXSO'%ch, reply=False)
            if self.device_type[name] == 'OPSL':
                self._send('SOURce%i:AM:EXTernal MIXed'%ch, reply=False)
        assert self.get_control_mode(name) == mode
        if re_enable: self.set_enable('ON', name)
        if self.verbose:
            print("%s(%s): -> done setting control mode."%(self.name, name))
        return None

    def get_power_setpoint(self, name):
        if self.verbose:
            print("%s(%s): getting power setpoint"%(self.name, name))
        ch = self.name2channel[name]
        self.power_setpoint_w[name] = float(self._send(
            'SOURce%i:POWer:LEVel:IMMediate:AMPLitude?'%ch))
        self.power_setpoint_pct[name] = round( # max .dp
            (100 * self.power_setpoint_w[name] / self.max_power_w[name]), 2)
        if self.verbose:
            print("%s(%s): -> power setpoint (%%) = %0.1f (%0.3fW)"%(
                self.name, name,
                self.power_setpoint_pct[name], self.power_setpoint_w[name]))
        return self.power_setpoint_pct[name]

    def set_power_setpoint(self, power_setpoint_pct, name):
        if self.verbose:
            print("%s(%s): setting power setpoint (%%) = %s"%(
                self.name, name, power_setpoint_pct))
        if power_setpoint_pct == 'min':
            power_setpoint_pct = self.min_power_pct[name]
        if power_setpoint_pct == 'max':
            power_setpoint_pct = 100 # to match 'min' option
        power_setpoint_pct = round(power_setpoint_pct, 2) # max .dp
        assert self.min_power_pct[name] <= power_setpoint_pct <= 100
        ch = self.name2channel[name]
        power_w = (self.max_power_w[name] * power_setpoint_pct / 100)
        self._send('SOURce%i:POWer:LEVel:IMMediate:AMPLitude %f'%(
            ch, power_w), reply=False)
        assert self.get_power_setpoint(name) == power_setpoint_pct
        if self.verbose:
            print("%s(%s): -> done setting power setpoint."%(self.name, name))
        return None

    def get_enable(self, name):
        if self.verbose:
            print("%s(%s): getting enable"%(self.name, name))
        ch = self.name2channel[name]
        self.enable[name] = self._send('SOURce%i:AM:STATe?'%ch)
        if self.verbose:
            print("%s(%s): -> enable = %s"%(
                self.name, name, self.enable[name]))
        return self.enable[name]
    
    def set_enable(self, mode, name): # ***Turns laser ON!***
        if self.verbose:
            print("%s(%s): setting enable = %s"%(self.name, name, mode))
        assert mode in ('ON','OFF')
        assert self.CDRH_delay[name] == 'OFF' # No 5 second delay!
        ch = self.name2channel[name]
        self._send('SOURce%i:AM:STATe '%ch + mode, reply=False)
        assert self.get_enable(name) == mode
        if self.verbose:
            print("%s(%s): -> done setting enable."%(self.name, name))
        return None

    def get_power(self, name, wait_s=1):  # measures power (may need to wait)
        if self.verbose:
            print("%s(%s): getting power (W)"%(self.name, name))        
        if wait_s is not None:
            assert type(wait_s) is int or type(wait_s) is float
            print("%s(%s): waiting %0.3fs for laser to settle..."%(
                self.name, name, wait_s))
            from time import sleep
            sleep(wait_s)
        ch = self.name2channel[name]
        power_w = float(self._send('SOURce%i:POWer:LEVel?'%ch))
        if self.verbose:
            print("%s(%s): -> power (W) = %s"%(self.name, name, power_w))
        return power_w

    def close(self):
        if self.verbose: print("%s: closing..."%self.name)
        verbose = self.verbose
        self.verbose = False
        for name in self.lasers: # Safety
            self.set_enable('OFF', name)
            self.set_control_mode('USB', name) # USB to avoid 'checksum' error
            self._set_autostart('OFF', name)
            self.set_power_setpoint(self.min_power_pct[name], name)
        self.port.close()
        self.verbose = verbose
        if self.verbose: print("%s: closed."%self.name)
        return None

if __name__ == '__main__':
    nick_names = {'405':1, '445':2, '488':3, '561':4, '640':5}
    laser_box = Controller(which_port='COM11',
                           name2channel=nick_names,   # optional
                           control_mode='USB',        # optional init to 'analog'
                           verbose=False,
                           very_verbose=False)
    laser_box.verbose = True

    # USB control:
    for laser in laser_box.lasers:
        laser_box.set_power_setpoint(2, laser)
        laser_box.set_enable('ON', laser)
        laser_box.get_power(laser)
        laser_box.set_enable('OFF', laser)

    # USB control:
    for laser in laser_box.lasers:
        laser_box.set_control_mode('analog', laser)

    laser_box.close()
