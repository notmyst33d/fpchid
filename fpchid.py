import argparse
import subprocess
from typing import Optional
from dataclasses import dataclass
from pynput.keyboard import Controller


@dataclass
class Sensor:
    name: str
    path: str
    on: Optional[str]
    off: Optional[str]


known_fingerprint_sensors = {
    "uinput-fpc": ("0001 0161 00000001", "0001 0161 00000000")
}

possible_fingerprint_sensors = [
    "fpc",
    "goodix"
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Use your fingerprint scanner as a HID device")
    parser.add_argument("--device", type=str, default=None, help="Force device")
    parser.add_argument("--key", type=str, default="z", help="Key to press")
    parser.add_argument("--ignore-known", action=argparse.BooleanOptionalAction,
                        default=False, help="Ignore known devices list")
    args = parser.parse_args()

    try:
        sensors = []

        if not args.device:
            adb = subprocess.Popen(["adb", "shell", "getevent", "-i"], stdout=subprocess.PIPE)
            stdout, _ = adb.communicate()
            events = stdout.decode().replace("\r\n", "\n").split("\n")

            device = None
            scan = False
            exact = False

            for line in events:
                if exact:
                    break

                if not scan:
                    if line.startswith("add device"):
                        device = line.split(" ")
                        scan = True
                else:
                    if "name: " in line:
                        name = line.split("\"")

                        if not args.ignore_known:
                            for sensor, data in known_fingerprint_sensors.items():
                                if sensor == name[1]:
                                    sensors = [Sensor(name[1], device[3], data[0], data[1])]
                                    exact = True
                                    print(f"Found exact match: {name[1]}")
                                    break

                        if exact:
                            break

                        for sensor in possible_fingerprint_sensors:
                            if sensor in name[1]:
                                sensors.append(Sensor(name[1], device[3], None, None))
                                print(f"Found possible match: {name[1]}")
                                break

                        scan = False
        else:
            sensors.append(Sensor("fingerprint", args.device, None, None))

        if not sensors:
            print("Cannot find a fingerprint scanner")
            print("If you think this is a mistake, then run fpchid with --device")
            exit()

        adb = subprocess.Popen(["adb", "shell", "getevent"], stdout=subprocess.PIPE)
        keyboard = Controller()

        print("fpchid ready")

        for line in adb.stdout:
            line = line.decode().replace("\r\n", "").replace("\n", "")

            for sensor in sensors:
                if sensor.path in line:
                    if sensor.on and sensor.off:
                        if sensor.on in line:
                            keyboard.press(args.key)
                            print(line)
                        elif sensor.off in line:
                            keyboard.release(args.key)
                            print(line)
                    else:
                        try:
                            data = line.split(" ")

                            if (int(data[-1], 16) == 0 and
                                int(data[-2], 16) == 0 and
                                int(data[-3], 16) == 0):
                                continue

                            state = int(data[-1], 16)
                            if state == 1:
                                keyboard.press(args.key)
                                print(line)
                            elif state == 0:
                                keyboard.release(args.key)
                                print(line)
                        except:
                            pass
    except Exception as e:
        print(f"Shutting down: {e}")

        try:
            adb.kill()
        except:
            pass
