import logging

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib
from panels.menu import Panel as MenuPanel
from ks_includes.widgets.heatergraph import HeaterGraph
from ks_includes.widgets.keypad import Keypad
from ks_includes.KlippyGtk import find_widget


class Panel(MenuPanel):
    def __init__(self, screen, title, items=None):
        super().__init__(screen, title, items)
        self.left_panel = None
        self.devices = {}
        #self.graph_update = None
        self.active_heater = None
        self.h = self.f = 0
        self.main_menu = Gtk.Grid(row_homogeneous=True, column_homogeneous=True, hexpand=True, vexpand=True)
        self.main_menu.set_hexpand(True)
        self.main_menu.set_vexpand(True)
        scroll = self._gtk.ScrolledWindow()
        self.numpad_visible = False

        logging.info("### Making MainMenu")

        # Build new top row live extruder temp, bed temp, and fan buttons.  Buttons are defined here
        # rather than in create_top_panel so they can be seen by the update routine
        self.ext_temp = self._gtk.Button('extruder', "°C", "colorless", self.bts * 1.5, Gtk.PositionType.LEFT, 1)
        self.bed_temp = self._gtk.Button('bed', "°C", "colorless", self.bts * 1.3, Gtk.PositionType.LEFT, 1)
        self.chamber_temp = self._gtk.Button('printer', "°C", "colorless", self.bts * 1.5, Gtk.PositionType.LEFT, 1)
        self.fan_spd = self._gtk.Button('fan', "%", "colorless", self.bts * 1.5, Gtk.PositionType.LEFT, 1)
        self.top_panel = self.create_top_panel()
        self.main_menu.attach(self.top_panel, 0, 0, 4, 1)

        self.labels['menu'] = self.arrangeMenuItems(items, 3, True)
        scroll.add(self.labels['menu'])
        self.main_menu.attach(scroll, 0, 1, 4, 4)

        self.content.add(self.main_menu)

    def create_top_panel(self):
        # Buttons are defined in the init so they can be seen by the update routine
        self.ext_temp.connect("clicked", self.show_numpad, "ext")
        self.bed_temp.connect("clicked", self.show_numpad, "bed")
        #self.chamber_temp.connect("clicked", self.menu_item_clicked, {"name": "Temperature", "panel": "temperature"})
        self.fan_spd.connect("clicked", self.show_numpad, "fan")

        self.ext_temp.get_style_context().add_class("temp_off")
        self.bed_temp.get_style_context().add_class("temp_off")
        self.chamber_temp.get_style_context().add_class("temp_off")
        self.fan_spd.get_style_context().add_class("temp_off")

        top = Gtk.Grid(row_homogeneous=True, column_homogeneous=True)
        top.set_property("height-request", 80)
        top.set_vexpand(False)
        top.set_margin_bottom(10)
        top.attach(self.ext_temp, 0, 0, 1, 1)
        top.attach(self.bed_temp, 1, 0, 1, 1)
        top.attach(self.chamber_temp, 2, 0, 1, 1)
        top.attach(self.fan_spd, 3, 0, 1, 1)

        return top

    def set_heating_color(self,button,heating):
        if heating >0:
            button.get_style_context().remove_class("temp_off")
            button.get_style_context().add_class("temp_on")
        else:
            button.get_style_context().remove_class("temp_on")
            button.get_style_context().add_class("temp_off")

    def set_active(self,button,active):
        if active :
            button.get_style_context().remove_class("temp_on")
            button.get_style_context().remove_class("temp_off")
            button.get_style_context().add_class("select")
        else:
            button.get_style_context().remove_class("temp_on")
            button.get_style_context().add_class("temp_off")
            button.get_style_context().remove_class("select")

    def update_top_panel(self):
        ext_temp = self._printer.get_stat("extruder", "temperature")
        ext_target = self._printer.get_stat("extruder", "target")
        ext_label = f"{int(round(ext_temp))} / {int(round(ext_target))}°C"

        bed_temp = self._printer.get_stat("heater_bed", "temperature")
        bed_target = self._printer.get_stat("heater_bed", "target")
        bed_label = f" {int(round(bed_temp))} / {int(round(bed_target))}°C"

        try:
            chamber_temp = self._printer.get_stat("temperature_sensor Chamber", "temperature")
            chamber_label = f" {int(round(chamber_temp))} °C"
        except:
            chamber_temp = self._printer.get_stat("temperature_fan Chamber", "temperature")
            chamber_label = f" {int(round(chamber_temp))} °C"

        fs = self._printer.get_fan_speed("fan")
        fan_label = f" {float(fs) * 100:.0f}%"

        self.set_heating_color(self.ext_temp,ext_target)
        self.set_heating_color(self.bed_temp,bed_target)
        self.set_heating_color(self.fan_spd,fs)

        self.ext_temp.set_label(ext_label)
        self.bed_temp.set_label(bed_label)
        self.chamber_temp.set_label(chamber_label)
        self.fan_spd.set_label(fan_label)
        return


    def activate(self):
        if not self._printer.tempstore:
            self._screen.init_tempstore()

    def deactivate(self):
        if self.active_heater is not None:
            self.hide_numpad()

    def add_device(self, device):
        logging.info(f"Adding device: {device}")

        temperature = self._printer.get_stat(device, "temperature")
        if temperature is None:
            return False

        devname = device.split()[1] if len(device.split()) > 1 else device
        # Support for hiding devices by name
        if devname.startswith("_"):
            return False

        if device.startswith("extruder"):
            if self._printer.extrudercount > 1:
                image = f"extruder-{device[8:]}" if device[8:] else "extruder-0"
            else:
                image = "extruder"
            class_name = f"graph_label_{device}"
            dev_type = "extruder"
        elif device == "heater_bed":
            image = "bed"
            devname = "Heater Bed"
            class_name = "graph_label_heater_bed"
            dev_type = "bed"
        elif device.startswith("heater_generic"):
            self.h += 1
            image = "heater"
            class_name = f"graph_label_sensor_{self.h}"
            dev_type = "sensor"
        elif device.startswith("temperature_fan"):
            self.f += 1
            image = "fan"
            class_name = f"graph_label_fan_{self.f}"
            dev_type = "fan"
        elif self._config.get_main_config().getboolean("only_heaters", False):
            return False
        else:
            self.h += 1
            image = "heat-up"
            class_name = f"graph_label_sensor_{self.h}"
            dev_type = "sensor"

        rgb = self._gtk.get_temp_color(dev_type)

        can_target = self._printer.device_has_target(device)
        #self.labels['da'].add_object(device, "temperatures", rgb, False, False)
        #if can_target:
        #    self.labels['da'].add_object(device, "targets", rgb, False, True)
        #if self._show_heater_power and self._printer.device_has_power(device):
        #    self.labels['da'].add_object(device, "powers", rgb, True, False)

        name = self._gtk.Button(image, self.prettify(devname), None, self.bts, Gtk.PositionType.LEFT, 1)
        name.connect("clicked", self.toggle_visibility, device)
        name.set_alignment(0, .5)
        name.get_style_context().add_class(class_name)
        visible = self._config.get_config().getboolean(f"graph {self._screen.connected_printer}", device, fallback=True)
        if visible:
            name.get_style_context().add_class("graph_label")
        #self.labels['da'].set_showing(device, visible)

        temp = self._gtk.Button(label="", lines=1)
        find_widget(temp, Gtk.Label).set_ellipsize(False)
        if can_target:
            temp.connect("clicked", self.show_numpad, device)

        self.devices[device] = {
            "class": class_name,
            "name": name,
            "temp": temp,
            "can_target": can_target,
            "visible": visible
        }

        devices = sorted(self.devices)
        pos = devices.index(device) + 1

        self.labels['devices'].insert_row(pos)
        self.labels['devices'].attach(name, 0, pos, 1, 1)
        self.labels['devices'].attach(temp, 1, pos, 1, 1)
        self.labels['devices'].show_all()
        return True

    def toggle_visibility(self, widget, device):
        self.devices[device]['visible'] ^= True
        #logging.info(f"Graph show {self.devices[device]['visible']}: {device}")

        #section = f"graph {self._screen.connected_printer}"
        if section not in self._config.get_config().sections():
            self._config.get_config().add_section(section)
        self._config.set(section, f"{device}", f"{self.devices[device]['visible']}")
        self._config.save_user_config_options()

        #self.update_graph_visibility()

    def pid_calibrate(self, temp):
        heater = self.active_heater.split(' ', maxsplit=1)[-1]
        if self.verify_max_temp(temp):
            script = {"script": f"PID_CALIBRATE HEATER={heater} TARGET={temp}"}
            self._screen._confirm_send_action(
                None,
                _("Initiate a PID calibration for:")
                + f" {heater} @ {temp} ºC"
                + "\n\n"
                + _("It may take more than 5 minutes depending on the heater power."),
                "printer.gcode.script",
                script
            )

    def create_left_panel(self):

        self.labels['devices'] = Gtk.Grid(vexpand=False)
        self.labels['devices'].get_style_context().add_class('heater-grid')

        name = Gtk.Label()
        temp = Gtk.Label(label=_("Temp (°C)"))

        self.labels['devices'].attach(name, 0, 0, 1, 1)
        self.labels['devices'].attach(temp, 1, 0, 1, 1)

        #self.labels['da'] = HeaterGraph(self._screen, self._printer, self._gtk.font_size)

        scroll = self._gtk.ScrolledWindow(steppers=False)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.get_style_context().add_class('heater-list')
        scroll.add(self.labels['devices'])

        self.left_panel = Gtk.Grid(row_homogeneous=True, column_homogeneous=True, hexpand=True, vexpand=True)

        #self.left_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.left_panel.add(scroll)

        for d in self._printer.get_temp_devices():
            self.add_device(d)

        return self.left_panel

    def process_update(self, action, data):
        #if action != "notify_status_update":
        #    return
        #for x in self._printer.get_temp_devices():
        #    if x in data:
        #        self.update_temp(
        #            x,
        #            self._printer.get_stat(x, "temperature"),
        #            self._printer.get_stat(x, "target"),
        #            self._printer.get_stat(x, "power"),
        #        )
        if action != "notify_status_update":
            return
        self.update_top_panel()

    def verify_value(self, temp,top):
        temp = int(temp)
        logging.debug(f"{temp}/{top}")
        if temp > top:
            self._screen.show_popup_message(_("Can't set above the maximum:") + f' {top}')
            return False
        return max(temp, 0)

    def change_target_temp(self, temp):
        if temp is False:
            return

        if self.active_heater == "ext":
            self._screen._ws.klippy.set_tool_temp(0, self.verify_value(temp,500))
        elif self.active_heater == "bed":
            self._screen._ws.klippy.set_bed_temp(self.verify_value(temp,120))
        elif self.active_heater == "fan":
            self._screen._ws.klippy.gcode_script(f"M106 S{self.verify_value(temp,100) * 2.55:.0f}")
        
        #self._printer.set_stat(name, {"target": temp})
        if self.numpad_visible:
            self.hide_numpad()


    def show_numpad(self, widget, device):
        if (device == "ext"):
            self.set_active(self.ext_temp,True)
            self.set_active(self.bed_temp,False)
            self.set_active(self.fan_spd,False)
        elif (device == "bed"):
            self.set_active(self.ext_temp,False)
            self.set_active(self.bed_temp,True)
            self.set_active(self.fan_spd,False)
        elif (device == "fan"):
            self.set_active(self.ext_temp,False)
            self.set_active(self.bed_temp,False)
            self.set_active(self.fan_spd,True)

        self.active_heater = device

        self.labels["keypad"] = Keypad(self._screen, self.change_target_temp, self.pid_calibrate, self.hide_numpad)
        self.labels["keypad"].clear()

        #self.main_menu.set_vexpand(False)
        out = self.main_menu.get_child_at(0, 1)
        self.main_menu.remove(out)
        self.main_menu.attach(self.labels["keypad"], 0, 1, 4, 4)
        self.main_menu.show_all()
        self.numpad_visible = True
        self._screen.base_panel.set_control_sensitive(True, control='back')

    def hide_numpad(self, widget=None):
        self.set_active(self.ext_temp,False)
        self.set_active(self.bed_temp,False)
        self.set_active(self.fan_spd,False)
        self.active_heater = None

        out = self.main_menu.get_child_at(0, 1)
        self.main_menu.remove(out)
        self.main_menu.attach(self.labels['menu'], 0, 1, 4, 4)

        #self.main_menu.show_all()
        self.numpad_visible = False
        self._screen.base_panel.set_control_sensitive(False, control='back')


    def back(self):
        if self.numpad_visible:
            self.hide_numpad()
            return True
        return False
