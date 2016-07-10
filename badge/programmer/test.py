#!/usr/bin/env python

import telnetlib
import subprocess
import threading
import time

OPENOCD_DIR = '/Applications/gnuarmeclipse/OpenOCD/0.10.0-201601101000-dev/'

cmd = [OPENOCD_DIR + 'bin/openocd']
cmd += ['-f', OPENOCD_DIR + 'scripts/interface/stlink-v2.cfg']
cmd += ['-f', OPENOCD_DIR + 'scripts/target/stm32f1x.cfg']

class openOCDThread(threading.Thread):
    ''' Run openocd as subprocess and read output in separate thread
    '''
    def __init__(self, verbose=False):
        super(openOCDThread, self).__init__()
        self.proc = None
        self.ready = False
        self.verbose = verbose

    def run(self):
        self.proc = subprocess.Popen(cmd, stderr=subprocess.PIPE)

        while self.proc.poll() is None:

            l = self.proc.stderr.readline() # This blocks until it receives a newline.
            if 'stm32f1x.cpu: hardware has 6 breakpoints, 4 watchpoints' in l:
                self.ready = True

            if self.verbose:
                print(l.strip())
 
        if self.verbose:
            print self.proc.stderr.read()

    def kill(self):
        self.proc.terminate()


class flashProgrammer(object):
    def __init__(self):

        self.connected = False

        # Start openOCD as daemon so it will automatically close on program exit
        self.openOCD = openOCDThread()
        self.openOCD.daemon = True
        self.openOCD.start()

        timeout = 500

        # Don't connect telnet until openOCD is ready
        while (timeout > 0) and (self.openOCD.ready is False):
            time.sleep(0.01)
            timeout -= 1

        if self.openOCD.ready is True:
            self.telnet = telnetlib.Telnet('127.0.0.1', 4444)
            self.telnet.read_until('\r>', timeout=1)  # Wait until prompt read
            self.connected = True
        else:
            print('Unable to connect to openOCD server')

    def _sendCmd(self, cmd, timeout=10):
        ''' Send command over telnet and capture output
            return list of output lines without command echo
        '''

        print cmd

        self.telnet.write(cmd + '\n')

        lines = self.telnet.read_until('\n\r>', timeout=timeout)

         # Remove prompt and split into lines
        lines = lines.strip('\n\r>').split('\r\n')

        # Remove command echo
        lines.pop(0)

        return lines

    def readMem(self, address, size):
        ''' Returns list of bytes at address
        '''
        lines = self._sendCmd('mdb ' + str(address) + ' ' + str(size))

        data = []

        for line in lines:
            addr_str, data_str = line.split(': ')
            addr = int(addr_str, 16)

            for byte in data_str.strip().split(' '):
                data.append(int(byte, 16))

        return data

    def erase(self, address, size):
        lines = self._sendCmd('flash erase_address ' + str(address) + ' ' + str(size))
        # TODO - verify output
        print(lines)

    def flashFile(self, filename, address, bank=0):
        lines = self._sendCmd('flash write_bank ' + str(bank) + 
                    ' ' + filename + ' ' + str(address), timeout=60)
        # TODO - verify output
        print(lines)

    def dumpImage(self, filename, address, size):
        lines = self._sendCmd('dump_image ' + filename + ' ' + str(address) + ' ' + str(size))
        # TODO - verify output
        print(lines)

    def kill(self):
        self.openOCD.kill()


# 
# Quick example of reading UID, erasing flash, programming flash, and reading back flash 
# 
flasher = flashProgrammer()

if flasher.connected is True:
    flasher._sendCmd('reset halt')

    # Read device unique ID
    uid = flasher.readMem(0x1FFFF7E8, 12)
    print('uid:')
    print(uid)

    flasher.erase(0x800d400, 0x400)

    flasher.flashFile('/Users/alvaro/Desktop/test.bin', 0xd400)

    flasher.dumpImage('/Users/alvaro/Desktop/flash.bin', 0x800d400, 0x400)

flasher.kill()
