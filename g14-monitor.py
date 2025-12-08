#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GLib
import subprocess
import re
from datetime import datetime
import os

DEBUG_LOG = os.path.expanduser("~/g14-debug.log")

class G14Monitor:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            "g14-monitor",
            "computer",
            AppIndicator3.IndicatorCategory.HARDWARE
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        # Track fan speed for spin-up detection
        self.last_fan_speed = None
        self.last_logged_time = None
        
        # Create menu
        self.menu = Gtk.Menu()
        
        # Status items (now clickable)
        self.temp_item = Gtk.MenuItem(label="Temp: --°C")
        self.fan_item = Gtk.MenuItem(label="Fan: ---- RPM")
        self.power_item = Gtk.MenuItem(label="Power: -- W")
        self.gpu_item = Gtk.MenuItem(label="GPU: ---")
        self.policy_item = Gtk.MenuItem(label="Policy: ---")
        
        # Make items clickable
        self.gpu_item.connect("activate", self.toggle_gpu)
        self.policy_item.connect("activate", self.cycle_policy)
        
        self.menu.append(self.temp_item)
        self.menu.append(self.fan_item)
        self.menu.append(self.power_item)
        self.menu.append(self.gpu_item)
        self.menu.append(self.policy_item)
        
        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # Monitoring and debug options
        monitor_item = Gtk.MenuItem(label="📊 Open Live Monitor")
        monitor_item.connect("activate", self.open_live_monitor)
        self.menu.append(monitor_item)
        
        view_log_item = Gtk.MenuItem(label="📋 View Debug Log")
        view_log_item.connect("activate", self.view_debug_log)
        self.menu.append(view_log_item)
        
        clear_log_item = Gtk.MenuItem(label="🗑️  Clear Debug Log")
        clear_log_item.connect("activate", self.clear_debug_log)
        self.menu.append(clear_log_item)
        
        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # Manual controls
        force_quiet_item = Gtk.MenuItem(label="⚡ Force Quiet Mode")
        force_quiet_item.connect("activate", self.force_quiet)
        self.menu.append(force_quiet_item)
        
        force_gpu_sleep_item = Gtk.MenuItem(label="💤 Force GPU Sleep")
        force_gpu_sleep_item.connect("activate", self.force_gpu_sleep)
        self.menu.append(force_gpu_sleep_item)
        
        # Separator
        self.menu.append(Gtk.SeparatorMenuItem())
        
        # Quit option
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", self.quit)
        self.menu.append(quit_item)
        
        self.menu.show_all()
        self.indicator.set_menu(self.menu)
        
        # Initialize debug log
        self.init_debug_log()
        
        # Update every 2 seconds
        GLib.timeout_add_seconds(2, self.update_status)
        self.update_status()
    
    def init_debug_log(self):
        """Initialize debug log file"""
        with open(DEBUG_LOG, 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"G14 Monitor Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
    
    def log_debug(self, event, details):
        """Log debug information"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(DEBUG_LOG, 'a') as f:
            f.write(f"[{timestamp}] {event}\n")
            for key, value in details.items():
                f.write(f"  {key}: {value}\n")
            f.write("\n")
    
    def detect_fan_spinup(self, current_fan_speed):
        """Detect and log significant fan speed increases"""
        if self.last_fan_speed is None:
            self.last_fan_speed = current_fan_speed
            return
        
        # Detect spin-up (increase of 500+ RPM)
        if current_fan_speed - self.last_fan_speed >= 500:
            # Don't log too frequently (at most every 30 seconds)
            now = datetime.now()
            if self.last_logged_time is None or (now - self.last_logged_time).seconds >= 30:
                self.log_fan_event("FAN SPIN-UP DETECTED", current_fan_speed)
                self.last_logged_time = now
        
        self.last_fan_speed = current_fan_speed
    
    def log_fan_event(self, event_type, fan_speed):
        """Log detailed system state during fan event"""
        temp = self.get_temp()
        power = self.get_power_draw()
        gpu_status = self.get_gpu_status()
        gpu_control = self.get_gpu_control()
        policy = self.get_policy()
        platform = self.get_platform_profile()
        boost = self.get_cpu_boost()
        
        # Get top CPU processes
        top_procs = self.get_top_processes()
        
        details = {
            "Event": event_type,
            "Fan Speed": f"{fan_speed} RPM",
            "CPU Temp": f"{temp}°C" if temp else "N/A",
            "Power Draw": f"{power:.1f}W" if power else "N/A",
            "GPU Status": gpu_status,
            "GPU Control": gpu_control,
            "Throttle Policy": policy,
            "Platform Profile": platform,
            "CPU Boost": "Enabled" if boost else "Disabled",
            "Top Processes": top_procs
        }
        
        self.log_debug(event_type, details)
    
    def get_power_draw(self):
        """Get current power draw in watts"""
        try:
            # power_now is in microwatts, convert to watts
            with open('/sys/class/power_supply/BAT0/power_now', 'r') as f:
                microwatts = int(f.read().strip())
                return microwatts / 1000000.0
        except:
            return None
    
    def get_gpu_control(self):
        """Get GPU power control setting"""
        try:
            with open('/sys/bus/pci/devices/0000:01:00.0/power/control', 'r') as f:
                return f.read().strip()
        except:
            return "unknown"
    
    def get_platform_profile(self):
        """Get platform profile"""
        try:
            with open('/sys/firmware/acpi/platform_profile', 'r') as f:
                return f.read().strip()
        except:
            return "unknown"
    
    def get_cpu_boost(self):
        """Get CPU boost status"""
        try:
            with open('/sys/devices/system/cpu/cpu0/cpufreq/boost', 'r') as f:
                return f.read().strip() == '1'
        except:
            return None
    
    def get_top_processes(self):
        """Get top 3 CPU-using processes"""
        try:
            result = subprocess.run(
                ['ps', 'aux', '--sort=-%cpu'],
                capture_output=True,
                text=True
            )
            lines = result.stdout.split('\n')[1:4]  # Skip header, get top 3
            procs = []
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 11:
                        procs.append(f"{parts[10]} ({parts[2]}%)")
            return ', '.join(procs)
        except:
            return "N/A"
    
    def open_live_monitor(self, widget):
        """Open terminal with live system monitoring"""
        # Create a monitoring script
        monitor_script = os.path.expanduser("~/g14-live-monitor.sh")
        with open(monitor_script, 'w') as f:
            f.write("""#!/bin/bash
echo "=== G14 LIVE MONITOR ==="
echo "Press Ctrl+C to close"
echo ""

while true; do
    clear
    echo "=== G14 LIVE SYSTEM MONITOR ==="
    echo "$(date)"
    echo ""
    
    echo "--- Nuclear Fan Control Service ---"
    sudo systemctl status aggressive-fan-control.service --no-pager -n 5
    echo ""
    
    echo "--- Current Status ---"
    echo "Temperature: $(sensors | grep 'Tctl:' | awk '{print $2}')"
    echo "Fan Speed:   $(sensors | grep 'cpu_fan:' | awk '{print $2, $3}')"
    POWER_UW=$(cat /sys/class/power_supply/BAT0/power_now 2>/dev/null)
    if [ -n "$POWER_UW" ]; then
        POWER_W=$(echo "scale=2; $POWER_UW / 1000000" | bc)
        echo "Power Draw:  ${POWER_W}W"
    else
        echo "Power Draw:  N/A"
    fi
    echo "GPU Status:  $(cat /sys/bus/pci/devices/0000:01:00.0/power/runtime_status)"
    echo "GPU Control: $(cat /sys/bus/pci/devices/0000:01:00.0/power/control)"
    echo "Policy:      $(cat /sys/devices/platform/asus-nb-wmi/throttle_thermal_policy) (0=balanced, 1=perf, 2=quiet)"
    echo "Platform:    $(cat /sys/firmware/acpi/platform_profile)"
    echo "CPU Boost:   $(cat /sys/devices/system/cpu/cpu0/cpufreq/boost) (0=off, 1=on)"
    echo ""
    
    echo "--- Top CPU Processes ---"
    ps aux --sort=-%cpu | head -6
    echo ""
    
    echo "--- Recent Service Logs ---"
    sudo journalctl -u aggressive-fan-control.service -n 8 --no-pager
    echo ""
    echo "Refreshing in 3 seconds..."
    
    sleep 3
done
""")
        os.chmod(monitor_script, 0o755)
        
        # Open in terminal
        subprocess.Popen(['x-terminal-emulator', '-e', monitor_script])
        self.show_notification("Monitor", "Opening live monitor window...")
    
    def view_debug_log(self, widget):
        """Open debug log in text editor"""
        if os.path.exists(DEBUG_LOG):
            subprocess.Popen(['xdg-open', DEBUG_LOG])
            self.show_notification("Debug Log", f"Opening {DEBUG_LOG}")
        else:
            self.show_notification("Debug Log", "No debug log found")
    
    def clear_debug_log(self, widget):
        """Clear the debug log"""
        with open(DEBUG_LOG, 'w') as f:
            f.write(f"Debug log cleared: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        self.show_notification("Debug Log", "Debug log cleared")
    
    def run_command(self, cmd):
        """Run shell command with sudo"""
        try:
            subprocess.run(cmd, shell=True, check=True)
            return True
        except:
            return False
    
    def toggle_gpu(self, widget):
        """Toggle GPU power state"""
        gpu_status = self.get_gpu_status()
        if gpu_status == "active":
            self.run_command('echo auto | sudo tee /sys/bus/pci/devices/0000:01:00.0/power/control > /dev/null')
            self.show_notification("GPU", "Forcing GPU to suspend...")
            self.log_debug("USER ACTION", {"Action": "Forced GPU to auto (suspend)"})
        else:
            self.show_notification("GPU", "GPU already suspended")
    
    def cycle_policy(self, widget):
        """Cycle through thermal policies"""
        current = self.get_policy()
        policies = ['quiet', 'balanced', 'performance']
        policy_vals = {'quiet': '2', 'balanced': '0', 'performance': '1'}
        
        try:
            current_idx = policies.index(current)
            next_idx = (current_idx + 1) % len(policies)
            next_policy = policies[next_idx]
            
            self.run_command(f'echo {policy_vals[next_policy]} | sudo tee /sys/devices/platform/asus-nb-wmi/throttle_thermal_policy > /dev/null')
            self.show_notification("Policy", f"Switched to {next_policy}")
            self.log_debug("USER ACTION", {"Action": f"Changed policy to {next_policy}"})
        except:
            pass
    
    def force_quiet(self, widget):
        """Force quiet mode"""
        self.run_command('echo 2 | sudo tee /sys/devices/platform/asus-nb-wmi/throttle_thermal_policy > /dev/null')
        self.run_command('echo quiet | sudo tee /sys/firmware/acpi/platform_profile > /dev/null')
        self.show_notification("Fan Control", "Forced quiet mode")
        self.log_debug("USER ACTION", {"Action": "Forced quiet mode"})
    
    def force_gpu_sleep(self, widget):
        """Force GPU to sleep"""
        self.run_command('echo auto | sudo tee /sys/bus/pci/devices/0000:01:00.0/power/control > /dev/null')
        self.show_notification("GPU", "Forced GPU to auto (should suspend)")
        self.log_debug("USER ACTION", {"Action": "Forced GPU sleep"})
    
    def show_notification(self, title, message):
        """Show desktop notification"""
        try:
            subprocess.run(['notify-send', title, message])
        except:
            pass
    
    def get_temp(self):
        try:
            result = subprocess.run(['sensors'], capture_output=True, text=True)
            match = re.search(r'Tctl:\s+\+(\d+\.\d+)', result.stdout)
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def get_fan_speed(self):
        try:
            result = subprocess.run(['sensors'], capture_output=True, text=True)
            match = re.search(r'cpu_fan:\s+(\d+) RPM', result.stdout)
            if match:
                return int(match.group(1))
        except:
            pass
        return None
    
    def get_gpu_status(self):
        try:
            with open('/sys/bus/pci/devices/0000:01:00.0/power/runtime_status', 'r') as f:
                status = f.read().strip()
                return status
        except:
            return "unknown"
    
    def get_policy(self):
        try:
            with open('/sys/devices/platform/asus-nb-wmi/throttle_thermal_policy', 'r') as f:
                val = f.read().strip()
                policies = {
                    '0': 'balanced',
                    '1': 'performance', 
                    '2': 'quiet'
                }
                return policies.get(val, 'unknown')
        except:
            return "unknown"
    
    def get_temp_icon(self, temp):
        """Return emoji/icon based on temperature"""
        if temp is None:
            return "❓"
        elif temp < 50:
            return "🟢"
        elif temp < 65:
            return "🟡"
        elif temp < 75:
            return "🟠"
        else:
            return "🔴"
    
    def update_status(self):
        temp = self.get_temp()
        fan = self.get_fan_speed()
        power = self.get_power_draw()
        gpu = self.get_gpu_status()
        policy = self.get_policy()
        
        # Detect fan spin-ups
        if fan is not None:
            self.detect_fan_spinup(fan)
        
        # Update indicator label
        temp_icon = self.get_temp_icon(temp)
        if temp is not None:
            temp_str = f"{temp:.0f}°C"
        else:
            temp_str = "--°C"
        
        gpu_icon = "⚡" if gpu == "active" else "💤"
        
        # Main indicator text
        self.indicator.set_label(f"{temp_icon}{temp_str}", "")
        
        # Update menu items with click hints
        if temp is not None:
            self.temp_item.set_label(f"Temp: {temp:.1f}°C {temp_icon}")
        else:
            self.temp_item.set_label("Temp: --°C")
        
        if fan is not None:
            self.fan_item.set_label(f"Fan: {fan} RPM")
        else:
            self.fan_item.set_label("Fan: ---- RPM")
        
        if power is not None:
            self.power_item.set_label(f"Power: {power:.1f}W")
        else:
            self.power_item.set_label("Power: -- W")
        
        self.gpu_item.set_label(f"GPU: {gpu} {gpu_icon} (click to force sleep)")
        self.policy_item.set_label(f"Policy: {policy} (click to cycle)")
        
        return True
    
    def quit(self, widget):
        Gtk.main_quit()

if __name__ == "__main__":
    monitor = G14Monitor()
    Gtk.main()
