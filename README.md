# fpchid
Use your fingerprint scanner as a HID device.

## Installing
First of all, you need to install ADB and Python.

ADB: https://developer.android.com/studio/releases/platform-tools  
Python: https://www.python.org/downloads/

After everything is installed, download fpchid repository and install the dependencies:
```
$ pip install -r requirements.txt
```

Before you run fpchid, you need to enable ADB on your phone first:
1. Go to Settings app
2. Go to "About phone"
3. Tap several times on Android version (on Xiaomi phones you should tap on MIUI version)
4. After this go to Additional settings and find Developer options menu
5. Scroll down and look for "USB debugging" and then enable it

After you enabled ADB on your phone, ensure that your phone is being detected:
```
$ adb devices
List of devices attached
1234567890ab	device
```

After this you should be able to run fpchid:
```
$ python fpchid.py
Found exact match: uinput-fpc
fpchid ready
```

## Profile mode (new)
You can use a profile mode to get a better support for your phone and use extra features:
```
$ python fpchid.py --profile profiles/redmi_note_9.toml 
Using profile mode
Profile: Redmi Note 9
```

### What you can do with profile mode
* Program any possible key on your phone to press any possible key on your keyboard
* Program touchscreen area to trigger a key on your keyboard

Currently touchscreen functionality is a bit broken and using multiple fingers at the time will break everything

## Troubleshooting
### fpchid says that it cant detect the fingerprint sensor
Either your device doesnt have one, or it wasnt detected.

Run `adb shell getevent` to see all possible devices:
```
$ adb shell getevent
add device 1: /dev/input/event6
  name:     "uinput-fpc"
add device 2: /dev/input/event1
  name:     "mysar"
add device 3: /dev/input/event5
  name:     "mtk-tpd"
add device 4: /dev/input/event3
  name:     "fpc_irq@fingerprint"
add device 5: /dev/input/event0
  name:     "ACCDET"
add device 6: /dev/input/event2
  name:     "mtk-kpd"
add device 7: /dev/input/event4
  name:     "fts_ts"
```

Try different event paths until you find one that works:
```
$ python Projects/fpchid/fpchid.py --device /dev/input/event6
fpchid ready
/dev/input/event6: 0001 0161 00000001
/dev/input/event6: 0001 0161 00000000
```

### fpchid says that it detected the exact match but it doesnt work
You can use `--ignore-known` flag, but this might not help you:
```
$ python Projects/fpchid/fpchid.py --ignore-known
Found possible match: uinput-fpc
Found possible match: fpc_irq@fingerprint
fpchid ready
/dev/input/event6: 0001 0161 00000001
/dev/input/event6: 0001 0161 00000000
```

### I want to remap the default "z" key to something else
Use `--key` flag:
```
$ python Projects/fpchid/fpchid.py --key q
Found possible match: uinput-fpc
Found possible match: fpc_irq@fingerprint
fpchid ready
/dev/input/event6: 0001 0161 00000001
/dev/input/event6: 0001 0161 00000000
```
