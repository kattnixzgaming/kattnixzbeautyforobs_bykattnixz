"""Transporte local Windows para KattBeauty. No usa red ni abre la webcam."""
import ctypes
from ctypes import wintypes
import mmap
import os
import struct
import time

import cv2
import numpy as np

MAGIC = 0x374F424B
VERSION = 1
HEADER = struct.Struct("<8I3Q2I")
MAX_WIDTH, MAX_HEIGHT = 1920, 1080
CAPACITY = MAX_WIDTH * MAX_HEIGHT * 4
MAP_SIZE = HEADER.size + CAPACITY


def valid_packet(fields):
    magic, version, width, height, stride, size, sequence, flags, timestamp, tick, session, _, _ = fields
    return (magic == MAGIC and version == VERSION and 0 < width <= MAX_WIDTH
            and 0 < height <= MAX_HEIGHT and stride == width * 4
            and size == stride * height and size <= CAPACITY
            and sequence != 0 and session != 0 and flags in (0, 1))


class WindowsMutex:
    def __init__(self, name, singleton=False):
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.api.CreateMutexW.restype = wintypes.HANDLE
        self.api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.api.WaitForSingleObject.restype = wintypes.DWORD
        self.api.ReleaseMutex.argtypes = [wintypes.HANDLE]
        self.api.ReleaseMutex.restype = wintypes.BOOL
        self.api.CloseHandle.argtypes = [wintypes.HANDLE]
        self.api.CloseHandle.restype = wintypes.BOOL
        ctypes.set_last_error(0)
        self.handle = self.api.CreateMutexW(None, False, name)
        error = ctypes.get_last_error()
        if not self.handle:
            raise ctypes.WinError(error)
        if singleton and error == 183:
            self.close()
            raise RuntimeError("El motor OBS ya esta abierto. Cierra la otra ventana.")

    def acquire(self):
        return self.api.WaitForSingleObject(self.handle, 0) in (0, 0x80)

    def release(self):
        self.api.ReleaseMutex(self.handle)

    def close(self):
        if self.handle:
            self.api.CloseHandle(self.handle)
            self.handle = None


class ObsCamera:
    def __init__(self):
        if os.name != "nt":
            raise RuntimeError("El puente de OBS requiere Windows.")
        self.owner = WindowsMutex("Local\\KattBeauty_OBS7_MotorOwner", singleton=True)
        self.input_lock = self.output_lock = None
        self.input = self.output = None
        self.last = None
        self.identity = None
        self.last_heartbeat = 0
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.GetTickCount64.argtypes = []
        self.api.GetTickCount64.restype = ctypes.c_ulonglong
        try:
            self.input_lock = WindowsMutex("Local\\KattBeauty_OBS7_InputLock")
            self.output_lock = WindowsMutex("Local\\KattBeauty_OBS7_OutputLock")
            self.input = mmap.mmap(-1, MAP_SIZE, tagname="Local\\KattBeauty_OBS7_Input")
            self.output = mmap.mmap(-1, MAP_SIZE, tagname="Local\\KattBeauty_OBS7_Output")
            self.heartbeat(force=True)
        except Exception:
            self.close()
            raise

    def heartbeat(self, force=False):
        now = self.api.GetTickCount64()
        if not force and now - self.last_heartbeat < 150:
            return
        if not self.output_lock.acquire():
            return
        try:
            fields = list(HEADER.unpack_from(self.output, 0))
            if fields[0] != MAGIC or fields[1] != VERSION:
                fields = [MAGIC, VERSION, 0, 0, 0, 0, 0, 0, 0, now, 0, 0, 0]
            fields[9] = now
            HEADER.pack_into(self.output, 0, *fields)
            self.last_heartbeat = now
        finally:
            self.output_lock.release()

    def read(self):
        self.heartbeat()
        deadline = time.monotonic() + .035
        while time.monotonic() < deadline:
            fields = None
            raw = None
            if self.input_lock.acquire():
                try:
                    fields = HEADER.unpack_from(self.input, 0)
                    identity = (fields[10], fields[6])
                    now = self.api.GetTickCount64()
                    if (valid_packet(fields) and identity != self.identity
                            and now >= fields[9] and now - fields[9] < 600):
                        raw = self.input[HEADER.size:HEADER.size + fields[5]]
                finally:
                    self.input_lock.release()
            if raw is not None:
                self.last = fields
                self.identity = (fields[10], fields[6])
                bgra = np.frombuffer(raw, np.uint8).reshape(fields[3], fields[2], 4)
                frame = cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR)
                if fields[7] & 1:
                    frame = cv2.flip(frame, 0)
                return True, frame
            time.sleep(.003)
        return True, None

    def publish(self, frame):
        if self.last is None:
            return False
        fields = list(self.last)
        if frame.shape[:2] != (fields[3], fields[2]):
            return False
        if fields[7] & 1:
            frame = cv2.flip(frame, 0)
        bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        fields[9] = self.api.GetTickCount64()
        if not self.output_lock.acquire():
            return False
        try:
            self.output[HEADER.size:HEADER.size + fields[5]] = bgra.tobytes()
            HEADER.pack_into(self.output, 0, *fields)
            self.last_heartbeat = fields[9]
        finally:
            self.output_lock.release()
        return True

    def close(self):
        for name in ("input", "output"):
            mapping = getattr(self, name, None)
            if mapping is not None:
                mapping.close()
                setattr(self, name, None)
        for name in ("input_lock", "output_lock", "owner"):
            lock = getattr(self, name, None)
            if lock is not None:
                lock.close()
                setattr(self, name, None)
