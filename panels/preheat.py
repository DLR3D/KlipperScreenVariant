import logging

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango
from contextlib import suppress
from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.keypad import Keypad
from ks_includes.KlippyGtk import find_widget


class Panel(ScreenPanel):
    active_heater = None

    def __init__(self, screen, title, **kwargs):
        title = title or _("| Preheat")
        super().__init__(screen, title)
        self.left_panel = None
        self.devices = {}
        self.popover = Gtk.Popover(position=Gtk.PositionType.BOTTOM)
        self.popover_buttons = {}
        self.long_press = {}
        self.popover_device = None
        self.h = self.f = 0
        self.grid = Gtk.Grid(row_homogeneous=False, column_homogeneous=True)
        self._gtk.reset_temp_color()
        self.preheat_options = self._screen._config.get_preheat_options()

        self.grid.attach(self.create_panel(), 0, 0, 1, 1)

        self.content.add(self.grid)

    def create_panel(self):
        self.preheat_grid = Gtk.Grid(
            row_homogeneous=True, column_homogeneous=True
        )
        i = 0
        for option in self.preheat_options:
            if option != "cooldown":
                temp_ext = self.preheat_options[option]["extruder"]
                temp_bed = self.preheat_options[option]["bed"]
                temp=[temp_ext,temp_bed]
                name = f"{option} - Hotend:{int(temp[0])}ºC Bed:{int(temp[1])}ºC"
                self.labels[option] = self._gtk.Button(
                    label=name, style=f"color{(i % 4) + 1}"
                )
                self.labels[option].connect("clicked", self.set_temperature, temp)
                self.preheat_grid.attach(
                    self.labels[option], (i % 2), int(i / 2), 1, 1
                )
                i += 1
        scroll = self._gtk.ScrolledWindow()
        scroll.add(self.preheat_grid)
        scroll.set_margin_bottom(10)
        return scroll
    
    def set_temperature(self, widget, temp):
        self._screen._ws.klippy.gcode_script(f"M104 S{int(temp[0])}")
        self._screen._ws.klippy.gcode_script(f"M140 S{int(temp[1])}")

    def process_update(self, action, data):
        if action != "notify_status_update":
            return