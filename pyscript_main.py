import asyncio
import math
import sys
import time

from pyweb import pydom
from pyscript import when, document, window
from pyodide.ffi import to_js, create_proxy
from js import (
    CanvasRenderingContext2D as Context2d,
    ImageData,
    Uint8ClampedArray,
    console,
    document,
)


def monkey_patch_micropython():
    class FakeMicropython:
        @staticmethod
        def const(x):
            return x

    sys.modules["micropython"] = FakeMicropython
    print("Implementation: " + sys.implementation.name)
    sys.implementation.name = "micropython"
    print("Implementation is now: " + sys.implementation.name)


def patch_filesystem():
    # New apps are downloaded to /apps and /backgrounds
    # It's hardcoded. We need to make sure files out of those
    # directories are importable.
    import os

    os.mkdir("/apps")
    os.symlink("/apps", "/home/pyodide/apps")

    os.mkdir("/backgrounds")
    os.symlink("/backgrounds", "/home/pyodide/backgrounds")


async def monkey_patch_http():
    # requests doesn't work in pyscript without this voodoo

    import micropip

    await micropip.install("pyodide-http")
    await micropip.install("requests")

    import pyodide_http

    pyodide_http.patch_all()

    import requests

    # We rewrite requests via a CORS proxy because otherwise we can't fetch
    # tarballs from github/etc
    def get(url, *args, **kwargs):
        print("Requests.get(", url, args, kwargs, ")")
        url = "https://api.codetabs.com/v1/proxy?quest=" + url
        print("Request rewritten to", url)
        try:
            return requests.real_get(url, *args, **kwargs)
        except Exception as e:
            print("Exception in requests.get:", e)
            raise

    requests.real_get = requests.get
    requests.get = get


def monkey_patch_sys():
    if not hasattr(sys, "print_exception"):

        def print_exception(e, file):
            print("Exception:", e, file=file)

        sys.print_exception = print_exception


def monkey_patch_tildagon_helpers():
    class FakeHelpers:
        @staticmethod
        def esp_wifi_set_max_tx_power(*args, **kwargs):
            pass

        @staticmethod
        def esp_wifi_sta_wpa2_ent_set_identity(*args, **kwargs):
            pass

        @staticmethod
        def esp_wifi_sta_wpa2_ent_set_username(*args, **kwargs):
            pass

        @staticmethod
        def esp_wifi_sta_wpa2_ent_set_password(*args, **kwargs):
            pass

    sys.modules["tildagon_helpers"] = FakeHelpers


def monkey_patch_network():
    class FakeNetwork:
        STA_IF = 0
        AP_IF = 1

        class FakeWLAN:
            def __init__(self, interface):
                self.interface = interface
                self._active = True
                self._connected = True

            def active(self, is_active=None):
                if is_active is None:
                    return self._active
                else:
                    self._active = is_active

            def connect(self, ssid, password):
                print(f"Fake connect to SSID {ssid} with password {password}")
                self._connected = True

            def disconnect(self):
                print("Fake disconnect")
                self._connected = False

            def isconnected(self):
                return self._connected

            def status(self):
                if not self._active:
                    return 0

        def __init__(self):
            pass

        def WLAN(self, interface):
            return self.FakeWLAN(interface)

    sys.modules["network"] = FakeNetwork()


def monkey_patch_time():
    if not hasattr(time, "ticks_us"):
        time.ticks_us = lambda: int(time.time_ns() / 1000)

    if not hasattr(time, "ticks_diff"):
        time.ticks_diff = lambda a, b: a - b

    if not hasattr(time, "ticks_ms"):
        time.ticks_ms = lambda: int(time.time_ns() / 1_000_000)

    if not hasattr(time, "ticks_add"):
        time.ticks_add = lambda a, b: a + b




def monkey_patch_display():
    # In Tildagon OS, display is a module with a set of functions.
    # In PyScript, we will make display a class then patch it into the modules

    class FakeDisplay:
        @staticmethod
        def gfx_init():
            print("Fake gfx_init()")

        @staticmethod
        def hexagon(ctx, x, y, dim):
            print("Not implemented: FakeDisplay: hexagon(%s, %s, %s)" % (x, y, dim))

        @staticmethod
        def get_ctx():
            return Context()

        @staticmethod
        def end_frame(ctx):
            canvas = pydom["#screen canvas"][0]
            ctx2d = canvas._js.getContext("2d")
            data = Uint8ClampedArray.new(ctx._js.framebuffer)

            ctx.ctx_render_ctx(ctx._ctx,  DUNCAN

            img = ImageData.new(data, ctx._js.width, ctx._js.height)
            ctx2d.putImageData(img, 0, 0)

    sys.modules["display"] = FakeDisplay

    class FakeGC9A01PY:
        pass

    sys.modules["gc9a01py"] = FakeGC9A01PY


def monkey_patch_machine():
    class FakePin:
        IN = 1
        OUT = 2

        def __init__(self, pin, mode=None):
            self.pin = pin
            self.mode = mode

        def value(self):
            return 0

    class FakeI2C:
        pass

    class FakeSPI:
        pass

    from types import ModuleType

    m = ModuleType("machine")
    sys.modules[m.__name__] = m

    sys.modules["machine.I2C"] = FakeI2C
    sys.modules["machine.SPI"] = FakeSPI
    sys.modules["machine.Pin"] = FakePin


def monkey_patch_tildagon():
    from types import ModuleType

    m = ModuleType("tildagon")
    sys.modules[m.__name__] = m

    class FakeEPin:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            pass

    class FakePin:
        def __init__(self, *args, **kwargs):
            pass

        def __call__(self, *args, **kwargs):
            pass

    sys.modules["tildagon.ePin"] = FakeEPin
    sys.modules["tildagon.Pin"] = FakePin


def monkey_patch_ePin():
    from types import ModuleType

    m = ModuleType("egpio")
    sys.modules[m.__name__] = m

    class FakeEPin:
        def __init__(self, pin):
            self.IN = 1
            self.OUT = 3
            self.PWM = 8
            self.pin = pin
            self.IRQ_RISING = 1
            self.IRQ_FALLING = 2

        def init(self, mode):
            pass

        def on(self):
            pass

        def off(self):
            pass

        def duty(self, duty):
            pass

        def value(self, value=None):
            return 1

        def irq(self, handler, trigger):
            pass

        def __call__(self, *args, **kwargs):
            pass

    sys.modules["egpio.ePin"] = FakeEPin


def monkey_patch_neopixel():
    class FakeNeoPixel:
        def __init__(self, *args, **kwargs):
            self.length = 12
            self.rgb = [(0, 0, 0)] * self.length

        def write(self):
            for led in range(self.length):
                canvas = pydom[f"#led{led} canvas"][0]
                ctx = canvas._js.getContext("2d")
                style = f"rgb({self.rgb[led][0]} {self.rgb[led][1]} {self.rgb[led][2]})"
                ctx.fillStyle = style
                ctx.beginPath()
                ctx.arc(10, 10, 10, 0, 2 * math.pi)
                ctx.fill()
                ctx.closePath()
                canvas.style["display"] = "block"

        def fill(self, color):
            print("Not yet implemented: FakeNeoPixel: fill", color)

        def __setitem__(self, item, value):
            if item > self.length:
                print("FakeNeoPixel: Ignoring setitem out of range", item)
            else:
                self.rgb[item - 1] = value

    class FakeNeoPixelModule:
        NeoPixel = FakeNeoPixel

    sys.modules["neopixel"] = FakeNeoPixelModule


async def badge():
    resolution_x = 240
    resolution_y = 240
    border = 10

    # FIXME: for now draw leds as a grey circle
    #        - we need to lay them out properly in the HTML
    #        - we need to hook them up to the code
    for led in range(6):
        canvas = pydom[f"#led{led} canvas"][0]
        ctx = canvas._js.getContext("2d")
        ctx.fillStyle = "rgb(100 100 100)"
        ctx.beginPath()
        ctx.arc(10, 10, 5, 0, 2 * math.pi)
        ctx.fill()
        ctx.closePath()
        canvas.style["display"] = "block"

    canvas = pydom["#screen canvas"][0]
    ctx = canvas._js.getContext("2d")

    # Set the canvas size
    width = 3 * resolution_x + 2 * border
    height = 3 * resolution_y + 2 * border

    canvas.style["width"] = f"{width}px"
    canvas.style["height"] = f"{height}px"
    canvas._js.width = width
    canvas._js.height = height

    # Draw a green circle for the screen border
    ctx.fillStyle = "rgb(0 100 0)"
    ctx.beginPath()
    ctx.arc(
        (3 * resolution_x + 2 * border) / 2,
        (3 * resolution_y + 2 * border) / 2,
        (3 * resolution_x + 2 * border) / 2,
        0,
        2 * math.pi,
    )
    ctx.fill()
    ctx.closePath()

    # Draw a black circle for the screen
    ctx.fillStyle = "rgb(0 0 0)"
    ctx.beginPath()
    ctx.arc(
        (3 * resolution_x + 2 * border) / 2,
        (3 * resolution_y + 2 * border) / 2,
        (3 * resolution_x) / 2,
        0,
        2 * math.pi,
    )
    ctx.fill()
    ctx.closePath()

    # Show the canvas
    canvas.style["display"] = "block"

    await start_tildagon_os()


async def button_handler(event):
    print("Button pressed:", event.target.id)

    from system.eventbus import eventbus
    from frontboards.twentyfour import BUTTONS
    from events.input import ButtonDownEvent, ButtonUpEvent

    print("Emitting ButtonDownEvent for button", BUTTONS[event.target.id])
    await eventbus.emit_async(ButtonDownEvent(button=BUTTONS[event.target.id]))


@create_proxy
async def on_key_down(event):

    from system.eventbus import eventbus
    from frontboards.twentyfour import BUTTONS
    from events.input import ButtonDownEvent, ButtonUpEvent

    match event.key:
        case "ArrowUp":
            print("Emitting ButtonDownEvent for button A")
            await eventbus.emit_async(ButtonDownEvent(button=BUTTONS["A"]))
        case "ArrowDown":
            print("Emitting ButtonDownEvent for button D")
            await eventbus.emit_async(ButtonDownEvent(button=BUTTONS["D"]))
        case "ArrowLeft":
            print("Emitting ButtonDownEvent for button F")
            await eventbus.emit_async(ButtonDownEvent(button=BUTTONS["F"]))
        case "ArrowRight":
            print("Emitting ButtonDownEvent for button C")
            await eventbus.emit_async(ButtonDownEvent(button=BUTTONS["C"]))
        case _:
            print("Key down:", event.key, "code:", event.code)


class Wasm:
    def __init__(self):
        self.wasm_exports = window.wasm_exports

    def malloc(self, size):
        return self.wasm_exports.malloc(size)

    def free(self, ptr):
        self.wasm_exports.free(ptr)

    def ctx_parse(self, p):
        s = s.encode("utf-8")
        slen = len(s) + 1
        p = self.malloc(slen)
        mem = self.wasm_exports.memory.unit8_view(p)
        m[0 : slen - 1] = s
        m[slen - 1] = 0
        r = self.wasm_exports.ctx_parse(p)
        self.free(p)

    def ctx_new_for_framebuffer(self, width, height, stride, fmt):
        """
        Call ctx_new_for_framebuffer, but also first allocate the underlying
        framebuffer and return it alongside the Ctx*.
        """
        fb = self.malloc(stride * height)
        return fb, self.wasm_exports.ctx_new_for_framebuffer(
            fb, width, height, stride, fmt
        )

    def ctx_new_drawlist(self, width, height):
        return self.wasm_xports.ctx_new_drawlist(width, height)

    def ctx_apply_transform(self, ctx, *args):
        args = [float(a) for a in args]
        return self.wasm_exports.ctx_apply_transform(ctx, *args)

    def ctx_define_texture(self, ctx, eid, *args):
        s = eid.encode("utf-8")
        slen = len(s) + 1
        p = self.malloc(slen)
        mem = self.wasm_exports.memory.uint8_view(p)
        mem[0 : slen - 1] = s
        mem[slen - 1] = 0
        res = self.wasm_exports.ctx_define_texture(ctx, p, *args)
        self.free(p)
        return res

    def ctx_draw_texture(self, ctx, eid, *args):
        s = eid.encode("utf-8")
        slen = len(s) + 1
        p = self.malloc(slen)
        mem = self.wasm_exports.memory.uint8_view(p)
        mem[0 : slen - 1] = s
        mem[slen - 1] = 0
        args = [float(a) for a in args]
        res = self.wasm_exports.ctx_draw_texture(ctx, p, *args)
        self.free(p)
        return res

    def ctx_text_width(self, ctx, text):
        s = text.encode("utf-8")
        slen = len(s) + 1
        p = self.malloc(slen)
        mem = self.wasm_exports.memory.uint8_view(p)
        mem[0 : slen - 1] = s
        mem[slen - 1] = 0
        res = self.wasm_exports.ctx_text_width(ctx, p)
        self.free(p)
        return res

    def ctx_x(self, ctx):
        return self.wasm_exports.ctx_x(ctx)

    def ctx_y(self, ctx):
        return self.wasm_exports.ctx_y(ctx)

    def ctx_logo(self, ctx, *args):
        args = [float(a) for a in args]
        return self.wasm_exports.ctx_logo(ctx, *args)

    def ctx_destroy(self, ctx):
        return self.wasm_exports.ctx_destroy(ctx)

    def ctx_render_ctx(self, ctx, dctx):
        return self.wasm_exports.ctx_render_ctx(ctx, dctx)

    def stbi_load_from_memory(self, buf):
        p = self.malloc(len(buf))
        mem = self.wasm_exports.memory.uint8_view(p)
        mem[0 : len(buf)] = buf
        wh = self.malloc(4 * 3)
        res = self.wasm_exports.stbi_load_from_memory(
            p, len(buf), wh, wh + 4, wh + 8, 4
        )
        whmem = self.wasm_exports.memory.uint32_view(wh // 4)
        r = (res, whmem[0], whmem[1], whmem[2])
        self.free(p)
        self.free(wh)

        res, w, h, c = r
        b = self.wasm_exports.memory.uint8_view(res)
        if c == 3:
            return r
        for j in range(h):
            for i in range(w):
                b[i * 4 + j * w * 4 + 0] = int(
                    b[i * 4 + j * w * 4 + 0] * b[i * 4 + j * w * 4 + 3] / 255
                )
                b[i * 4 + j * w * 4 + 1] = int(
                    b[i * 4 + j * w * 4 + 1] * b[i * 4 + j * w * 4 + 3] / 255
                )
                b[i * 4 + j * w * 4 + 2] = int(
                    b[i * 4 + j * w * 4 + 2] * b[i * 4 + j * w * 4 + 3] / 255
                )
        return r

class Context:
    """
    Ctx implements a subset of uctx [1]. It should be extended as needed as we
    make use of more and more uctx features in the badge code.

    [1] - https://ctx.graphics/uctx/
    """

    LEFT = "left"
    RIGHT = "right"
    CENTER = "center"
    HANGING = "hanging"
    CLEAR = "clear"
    END = "end"
    MIDDLE = "middle"
    BEVEL = "bevel"
    NONE = "none"
    COPY = "copy"

    def __init__(self):
        self._font_size = 0
        self._line_width = 0

    @property
    def image_smoothing(self):
        return 0

    @image_smoothing.setter
    def image_smoothing(self, v):
        self._emit(f"imageSmoothing {v}")

    @property
    def text_align(self):
        return None

    @text_align.setter
    def text_align(self, v):
        self._emit(f"textAlign {v}")

    @property
    def text_baseline(self):
        return None

    @text_baseline.setter
    def text_baseline(self, v):
        self._emit(f"textBaseline {v}")

    @property
    def compositing_mode(self):
        return Context.NONE

    @compositing_mode.setter
    def compositing_mode(self, v):
        self._emit(f"compositingMode {v}")

    @property
    def line_width(self):
        return self._line_width

    @line_width.setter
    def line_width(self, v):
        self._line_width = v
        self._emit(f"lineWidth {v:.3f}")

    @property
    def font(self):
        return None

    @font.setter
    def font(self, v):
        self._emit(f'font "{v}"')

    @property
    def font_size(self):
        return self._font_size

    @font_size.setter
    def font_size(self, v):
        self._font_size = v
        self._emit(f"fontSize {v:.3f}")

    @property
    def global_alpha(self):
        return None

    @global_alpha.setter
    def global_alpha(self, v):
        self._emit(f"globalAlpha {v:.3f}")

    @property
    def x(self):
        return _wasm.ctx_x(self._ctx)

    @property
    def y(self):
        return _wasm.ctx_y(self._ctx)

    def _emit(self, text):
        _wasm.ctx_parse(self._ctx, text)

    def logo(self, x, y, dim):
        _wasm.ctx_logo(self._ctx, x, y, dim)
        return self

    def move_to(self, x, y):
        self._emit(f"moveTo {x:.3f} {y:.3f}")
        return self

    def curve_to(self, a, b, c, d, e, f):
        self._emit(f"curveTo {a:.3f} {b:.3f} {c:.3f} {d:.3f} {e:.3f} {f:.3f}")
        return self

    def quad_to(self, a, b, c, d):
        self._emit(f"quadTo {a:.3f} {b:.3f} {c:.3f} {d:.3f}")
        return self

    def rel_move_to(self, x, y):
        self._emit(f"relMoveTo {x:.3f} {y:.3f}")
        return self

    def rel_curve_to(self, a, b, c, d, e, f):
        self._emit(f"relCurveTo {a:.3f} {b:.3f} {c:.3f} {d:.3f} {e:.3f} {f:.3f}")
        return self

    def rel_quad_to(self, a, b, c, d):
        self._emit(f"relQuadTo {a:.3f} {b:.3f} {c:.3f} {d:.3f}")
        return self

    def close_path(self):
        self._emit(f"closePath")
        return self

    def translate(self, x, y):
        self._emit(f"translate {x:.3f} {y:.3f}")
        return self

    def scale(self, x, y):
        self._emit(f"scale {x:.3f} {y:.3f}")
        return self

    def line_to(self, x, y):
        self._emit(f"lineTo {x:.3f} {y:.3f}")
        return self

    def rel_line_to(self, x, y):
        self._emit(f"relLineTo {x:.3f} {y:.3f}")
        return self

    def rotate(self, v):
        self._emit(f"rotate {v:.3f}")
        return self

    def gray(self, v):
        self._emit(f"gray {v:.3f}")
        return self

    def _value_range_rgb(self, value, value_str, low_limit, high_limit):
        if value > high_limit:
            print(
                "{name} value should be below {limit}, this is an error in the real uctx library. Setting to {limit}.".format(name=value_str, limit=high_limit),
                file=sys.stderr,
            )
            return high_limit
        if value < low_limit:
            print(
                "{name} value should be above {limit}, this is an error in the real uctx library. Setting to {limit}.".format(name=value_str, limit=low_limit),
                file=sys.stderr,
            )
            return low_limit
        return value

    def rgba(self, r, g, b, a):
        r = self._value_range_rgb(r, "r", 0.0, 255.0)
        g = self._value_range_rgb(g, "g", 0.0, 255.0)
        b = self._value_range_rgb(b, "b", 0.0, 255.0)
        a = self._value_range_rgb(a, "a", 0.0, 1.0)

        # if one value is a float between 0 and 1, check that no value is above 1
        if (r > 0.0 and r < 1.0) or (g > 0.0 and g < 1.0) or (b > 0.0 and b < 1.0):
            if r > 1.0 or g > 1.0 or b > 1.0:
                print(
                    "r, g, and b values are using mixed ranges (0.0 to 1.0) and (0 - 255), this may result in undesired colours.",
                    file=sys.stderr,
                )
        if r > 1.0 or g > 1.0 or b > 1.0:
            r /= 255.0
            g /= 255.0
            b /= 255.0

        self._emit(f"rgba {r:.3f} {g:.3f} {b:.3f} {a:.3f}")
        return self


    def rgb(self, r, g, b):
        r = self._value_range_rgb(r, "r", 0.0, 255.0)
        g = self._value_range_rgb(g, "g", 0.0, 255.0)
        b = self._value_range_rgb(b, "b", 0.0, 255.0)

        # if one value is a float between 0 and 1, check that no value is above 1
        if (r > 0.0 and r < 1.0) or (g > 0.0 and g < 1.0) or (b > 0.0 and b < 1.0):
            if r > 1.0 or g > 1.0 or b > 1.0:
                print(
                    "r, g, and b values are using mixed ranges (0.0 to 1.0) and (0 - 255), this may result in undesired colours.",
                    file=sys.stderr,
                )
        if r > 1.0 or g > 1.0 or b > 1.0:
            r /= 255.0
            g /= 255.0
            b /= 255.0
        self._emit(f"rgb {r:.3f} {g:.3f} {b:.3f}")
        return self

    def text(self, s):
        self._emit(f'text "{s}"')
        return self

    def round_rectangle(self, x, y, width, height, radius):
        self._emit(
            f"roundRectangle {x:.3f} {y:.3f} {width:.3f} {height:.3f} {radius:.3f}"
        )
        return self

    def image(self, path, x, y, w, h):
        if not path in _img_cache:
            buf = open(path, "rb").read()
            _img_cache[path] = _wasm.stbi_load_from_memory(buf)
        img, width, height, components = _img_cache[path]
        _wasm.ctx_define_texture(
            self._ctx, path, width, height, width * components, RGBA8, img, 0
        )
        _wasm.ctx_draw_texture(self._ctx, path, x, y, w, h)
        return self

    def rectangle(self, x, y, width, height):
        self._emit(f"rectangle {x} {y} {width} {height}")
        return self

    def stroke(self):
        self._emit(f"stroke")
        return self

    def save(self):
        self._emit(f"save")
        return self

    def restore(self):
        self._emit(f"restore")
        return self

    def fill(self):
        self._emit(f"fill")
        return self

    def radial_gradient(self, x0, y0, r0, x1, y1, r1):
        self._emit(
            f"radialGradient {x0:.3f} {y0:.3f} {r0:.3f} {x1:.3f} {y1:.3f} {r1:.3f}"
        )
        return self

    def linear_gradient(self, x0, y0, x1, y1):
        self._emit(f"linearGradient {x0:.3f} {y0:.3f} {x1:.3f} {y1:.3f}")
        return self

    def add_stop(self, pos, color, alpha):
        red, green, blue = color
        if red > 1.0 or green > 1.0 or blue > 1.0:
            red /= 255.0
            green /= 255.0
            blue /= 255.0
        if alpha > 1.0:
            # Should never happen, since alpha must be a float < 1.0, see line 711 in uctx.c
            alpha = 1.0
            print(
                "alpha > 1.0, this is an error in the real uctx library.",
                file=sys.stderr,
            )
        if alpha < 0.0:
            alpha = 0.0
            print(
                "alpha < 0.0, this is an error in the real uctx library.",
                file=sys.stderr,
            )
        self._emit(
            f"gradientAddStop {pos:.3f} {red:.3f} {green:.3f} {blue:.3f} {alpha:.3f} "
        )
        return self

    def begin_path(self):
        self._emit(f"beginPath")
        return self

    def arc(self, x, y, radius, arc_from, arc_to, direction):
        self._emit(
            f"arc {x:.3f} {y:.3f} {radius:.3f} {arc_from:.4f} {arc_to:.4f} {1 if direction else 0}"
        )
        return self

    def text_width(self, text):
        return _wasm.ctx_text_width(self._ctx, text)

    def clip(self):
        self._emit(f"clip")
        return self

    def get_font_name(self, i):
        return [
            "Arimo Regular",
            "Arimo Bold",
            "Arimo Italic",
            "Arimo Bold Italic",
            "Camp Font 1",
            "Camp Font 2",
            "Camp Font 3",
            "Material Icons",
            "Comic Mono",
        ][i]

    def scope(self):
        x = -120
        self.move_to(x, 0)
        for i in range(240):
            x2 = x + i
            y2 = math.sin(i / 10) * 60
            self.line_to(x2, y2)
        self.stroke()
        return self


_wasm = Wasm()
_img_cache = {}

async def start_tildagon_os():
    # Fix up differences between MicroPython and PyScript
    monkey_patch_time()
    monkey_patch_display()
    monkey_patch_machine()
    monkey_patch_tildagon()
    monkey_patch_neopixel()
    monkey_patch_ePin()
    monkey_patch_sys()
    monkey_patch_network()
    monkey_patch_tildagon_helpers()
    monkey_patch_micropython()
    await monkey_patch_http()
    patch_filesystem()

    document.addEventListener("keydown", on_key_down)

    import main

    # Everything gets started on the import above


async def main():
    _ = await asyncio.gather(badge())


asyncio.ensure_future(main())
