import toml
import argparse
import subprocess
from enum import Enum
from typing import Optional
from dataclasses import dataclass
from pynput.keyboard import Controller

known_fingerprint_sensors = {
    "uinput-fpc": ("0001 0161 00000001", "0001 0161 00000000")
}

possible_fingerprint_sensors = [
    "fpc",
    "goodix"
]


class EventType(Enum):
    EV_SYN = 0
    EV_KEY = 1
    EV_ABS = 3


class AbsEventAction(Enum):
    ABS_MT_POSITION_X = 53
    ABS_MT_POSITION_Y = 54
    ABS_MT_TRACKING_ID = 57


class KeyEventAction(Enum):
    BTN_TOUCH = 330


@dataclass
class Sensor:
    name: str
    path: str
    on: Optional[str]
    off: Optional[str]


@dataclass
class Key:
    key: str
    action: int

    @classmethod
    def from_dict(cls, data):
        if data["type"] == "key":
            return cls(
                key=data["key"],
                action=data["action"]
            )
        elif data["type"] == "abs":
            return Abs(
                key=data["key"],
                x=data["x"],
                y=data["y"]
            )
        else:
            raise Exception(f"Unsupported key type: {data['type']}")


@dataclass
class Abs:
    key: str
    x: list[int]
    y: list[int]


@dataclass
class Profile:
    name: str
    keys: list[Key | Abs]

    @classmethod
    def from_toml(cls, data):
        return cls(
            name=data["profile"]["name"],
            keys=[Key.from_dict(key) for key in data["keys"]]
        )


@dataclass
class Event:
    type: EventType
    action: int | AbsEventAction
    data: int

    @classmethod
    def from_raw(cls, data):
        if EventType(int(data[-3], 16)) == EventType.EV_ABS:
            action = AbsEventAction(int(data[-2], 16))
        else:
            action = int(data[-2], 16)

        return cls(
            type=EventType(int(data[-3], 16)),
            action=action,
            data=int(data[-1], 16)
        )


@dataclass
class PressedKey:
    key: str
    type: str


def find_sensors():
    adb = subprocess.Popen(["adb", "shell", "getevent", "-i"], stdout=subprocess.PIPE)
    stdout, _ = adb.communicate()
    events = stdout.decode().replace("\r\n", "\n").split("\n")

    sensors = []
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

    return sensors


def profile_mode():
    print("Using profile mode")

    with open(args.profile, "r") as f:
        profile = Profile.from_toml(toml.load(f))

    print(f"Profile: {profile.name}")

    adb = subprocess.Popen(["adb", "shell", "getevent"], stdout=subprocess.PIPE)
    keyboard = Controller()
    pressed = []
    pos_x = None
    pos_y = None

    for line in adb.stdout:
        line = line.decode().replace("\r\n", "").replace("\n", "")

        try:
            event = Event.from_raw(line.split(" "))
        except:
            continue

        if event.type == EventType.EV_SYN:
            continue

        if event.type == EventType.EV_ABS and event.action == AbsEventAction.ABS_MT_TRACKING_ID:
            continue

        if event.action == KeyEventAction.BTN_TOUCH.value and event.data == 0:
            pos_x = None
            pos_y = None

            for key in pressed:
                if key.type == "abs":
                    pressed.remove(key)
                    keyboard.release(key.key)

        for key in profile.keys:
            if event.type == EventType.EV_KEY and isinstance(key, Key):
                pressed_key = PressedKey(key.key, "key")

                if event.action == key.action and event.data == 1:
                    if key.key not in pressed:
                        pressed.append(key.key)
                        keyboard.press(key.key)
                elif event.action == key.action and event.data == 0:
                    if key.key in pressed:
                        pressed.remove(key.key)
                        keyboard.release(key.key)
            elif event.type == EventType.EV_ABS and isinstance(key, Abs):
                pressed_key = PressedKey(key.key, "abs")

                if event.action == AbsEventAction.ABS_MT_POSITION_X:
                    pos_x = event.data
                elif event.action == AbsEventAction.ABS_MT_POSITION_Y:
                    pos_y = event.data

                if not pos_x or not pos_y:
                    continue

                x = False
                y = False

                if key.x != "ignore":
                    if pos_x > key.x[0] and pos_x < key.x[1]:
                        x = True

                if key.y != "ignore":
                    if pos_y > key.y[0] and pos_y < key.y[1]:
                        y = True

                if key.x == "ignore":
                    x = True

                if key.y == "ignore":
                    y = True

                if x and y:
                    if pressed_key not in pressed:
                        pressed.append(pressed_key)
                        keyboard.press(key.key)
                else:
                    if pressed_key in pressed:
                        pressed.remove(pressed_key)
                        keyboard.release(key.key)


def normal_mode(sensors):
    print("Using normal mode")

    adb = subprocess.Popen(["adb", "shell", "getevent"], stdout=subprocess.PIPE)
    keyboard = Controller()

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Use your fingerprint scanner(and more) as a HID device")
    parser.add_argument("--device", type=str, default=None, help="Force device")
    parser.add_argument("--profile", type=str, default=None, help="Use a profile")
    parser.add_argument("--key", type=str, default="z", help="Key to press")
    parser.add_argument("--ignore-known", action=argparse.BooleanOptionalAction, default=False, help="Ignore known devices list")
    args = parser.parse_args()

    if args.profile:
        profile_mode()
    else:
        if not args.device:
            sensors = find_sensors()
        else:
            sensors = [Sensor("fingerprint", args.device, None, None)]

        if not sensors:
            print("Cannot find a fingerprint scanner")
            print("If you think this is a mistake, then run fpchid with --device")
            exit()

        print("fpchid ready")
        normal_mode(sensors)
