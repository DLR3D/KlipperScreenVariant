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
        title = title or _("| Filament")
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

        # Extruder temperature must be defined first so its value can be acessed by the update routine
        self.ext_temp = self._gtk.Button('extruder', "°C", "color1", self.bts * 1.5, Gtk.PositionType.LEFT, 1)
        
        self.grid.attach(self.create_top_panel(), 0, 0, 1, 1)
        self.grid.attach(self.create_mid_panel(), 0, 1, 1, 1)
        self.grid.attach(self.create_bottom_panel(), 0, 2, 1, 1)

        if(self._printer.get_filament_sensors()):
            self.grid.attach(self.create_filament_sensor_panel(),0,3,1,1)

        self.content.add(self.grid)

    def create_top_panel(self):
        self.park_button = self._gtk.Button('park', "Park extruder", "color1", self.bts * 1.5, Gtk.PositionType.LEFT, 1)
        self.park_button.connect("clicked", self.park)

        self.cooldown_button = self._gtk.Button('cool-down', "Cooldown extruder", "color2", self.bts * 1.5, Gtk.PositionType.LEFT, 1)
        self.cooldown_button.connect("clicked", self.cooldown)

        top = Gtk.Grid(row_homogeneous=True, column_homogeneous=True)
        top.set_property("height-request", 80)
        top.set_vexpand(False)
        top.set_margin_bottom(10)
        top.attach(self.ext_temp, 0, 0, 1, 1)
        top.attach(self.park_button, 1, 0, 1, 1)
        top.attach(self.cooldown_button, 2, 0, 1, 1)

        return top

    def update_top_panel(self):
        ext_temp = self._printer.get_stat("extruder", "temperature")
        ext_target = self._printer.get_stat("extruder", "target")
        ext_label = f"{int(ext_temp)} / {int(ext_target)}°C"

        self.ext_temp.set_label(ext_label)
        return

    def cooldown(self,widget):
        self._screen._ws.klippy.gcode_script(f"M104 S0")

    def park(self,widget):
        self._screen._ws.klippy.gcode_script(f"WIPE_NOZZLE_PARK")

    def create_mid_panel(self):
        self.preheat_grid = Gtk.Grid(
            row_homogeneous=True, column_homogeneous=True
        )
        i = 0
        for option in self.preheat_options:
            if option != "cooldown":
                temp = self.preheat_options[option]["extruder"]
                name = f"{option} {int(temp)}ºC"
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
        self._screen._ws.klippy.gcode_script(f"M104 S{int(temp)}")

    def create_bottom_panel(self):
        self.load_button = self._gtk.Button('arrow-down', "Load extruder", "color1", self.bts * 1.5, Gtk.PositionType.LEFT, 1)
        self.unload_button = self._gtk.Button('arrow-up', "Unload extruder", "color2", self.bts * 1.5, Gtk.PositionType.LEFT, 1)

        self.load_button.connect("clicked", self.load)
        self.unload_button.connect("clicked", self.unload)

        bottom = Gtk.Grid(row_homogeneous=True, column_homogeneous=True)
        bottom.set_property("height-request", 80)
        bottom.set_vexpand(False)
        bottom.attach(self.load_button, 0, 0, 1, 1)
        bottom.attach(self.unload_button, 1, 0, 1, 1)

        bottom.set_margin_bottom(10)

        return bottom

    def update_bottom_panel(self):
        ext_temp = self._printer.get_stat("extruder", "temperature")
        
        if (ext_temp < 180):
            self.load_button.set_sensitive(False)
            self.unload_button.set_sensitive(False)
        else:
            self.load_button.set_sensitive(True)
            self.unload_button.set_sensitive(True)
        return

        self.load_button.set_relief(GTK_RELIEF_NORMAL)
    
    def create_filament_sensor_panel(self):
        filament_sensors = self._printer.get_filament_sensors()
        sensors = Gtk.Grid(valign=Gtk.Align.CENTER, row_spacing=0, column_spacing=0)
        sensors.set_property("height-request", 40)
        sensors.set_margin_bottom(10)
        sensors.set_vexpand(False)
        for s, x in enumerate(filament_sensors):
            if s > 8:
                break
            name = x.split(" ", 1)[1].strip()
            self.labels[x] = {
                'label': Gtk.Label(
                    label=self.prettify(name), hexpand=True, vexpand=False, halign=Gtk.Align.CENTER,
                    ellipsize=Pango.EllipsizeMode.START),
                'box': Gtk.Box()
            }
            self.labels[x]['box'].pack_start(self.labels[x]['label'], True, True, 0)
            
            self.labels[x]['switch'] = Gtk.Switch()
            handler_id = self.labels[x]['switch'].connect("notify::active", self.enable_disable_fs, name, x)
            self.labels[x]['handler_id'] = handler_id
            self.labels[x]['box'].pack_start(self.labels[x]['switch'], False, False, 0)

            self.labels[x]['box'].get_style_context().add_class("filament_sensor")
            self.labels[x]['box'].get_style_context().add_class("filament_sensor_empty")
            sensors.attach(self.labels[x]['box'], s, 0, 1, 1)

        return sensors

    def update_filament_sensor_panel(self):
        for x in self._printer.get_filament_sensors():
            if x in data and x in self.labels:
                if 'enabled' in data[x] and 'switch' in self.labels[x]:
                    switch = self.labels[x]['switch']
                    handler_id = self.labels[x].get('handler_id')
                    if handler_id is not None:
                        switch.handler_block(handler_id)
                        switch.set_active(data[x]['enabled'])
                        switch.handler_unblock(handler_id)
                    else:
                        switch.set_active(data[x]['enabled'])
                if 'filament_detected' in data[x] and self._printer.get_stat(x, "enabled"):
                    if data[x]['filament_detected']:
                        self.labels[x]['box'].get_style_context().remove_class("filament_sensor_empty")
                        self.labels[x]['box'].get_style_context().add_class("filament_sensor_detected")
                    else:
                        self.labels[x]['box'].get_style_context().remove_class("filament_sensor_detected")
                        self.labels[x]['box'].get_style_context().add_class("filament_sensor_empty")

    def enable_disable_fs(self, switch, gparams, name, x):
        if switch.get_active():
            self._screen._ws.klippy.gcode_script(f"SET_FILAMENT_SENSOR SENSOR={name} ENABLE=1")
            if self._printer.get_stat(x, "filament_detected"):
                self.labels[x]['box'].get_style_context().add_class("filament_sensor_detected")
            else:
                self.labels[x]['box'].get_style_context().add_class("filament_sensor_empty")
        else:
            self._screen._ws.klippy.gcode_script(f"SET_FILAMENT_SENSOR SENSOR={name} ENABLE=0")
            self.labels[x]['box'].get_style_context().remove_class("filament_sensor_empty")
            self.labels[x]['box'].get_style_context().remove_class("filament_sensor_detected")


    def load(self,widget):
        self._screen._ws.klippy.gcode_script(f"M83\n G1 E150 F500\nM82")

    def unload(self,widget):
        self._screen._ws.klippy.gcode_script(f"M83\n G1 E30 F500\nG1 E-300 F1500\nM82")

    def create_right_panel(self):
        right.attach(self.preheat(), 0, 1, 3, 2)

    def process_update(self, action, data):
        if action != "notify_status_update":
            return
        self.update_top_panel()
        self.update_bottom_panel()