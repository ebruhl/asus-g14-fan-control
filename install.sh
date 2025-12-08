#!/bin/bash
echo "=== ASUS G14 Fan Fix Installer ==="
echo ""

if ! lspci | grep -q "TU106M"; then
    echo "WARNING: Designed for ASUS G14 2020 with RTX 2060 Max-Q"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Installing dependencies..."
sudo apt update
sudo apt install -y python3-gi gir1.2-appindicator3-0.1 gir1.2-notify-0.7 lm-sensors

echo "Installing scripts..."
cp nuclear-fan-control-v2.sh ~/
cp g14-monitor.py ~/
chmod +x ~/nuclear-fan-control-v2.sh ~/g14-monitor.py

echo "Blacklisting nouveau..."
echo "blacklist nouveau" | sudo tee /etc/modprobe.d/blacklist-nouveau.conf
echo "options nouveau modeset=0" | sudo tee -a /etc/modprobe.d/blacklist-nouveau.conf
sudo update-initramfs -u

echo "Setting up GPU power management..."
echo 'ACTION=="add", SUBSYSTEM=="pci", ATTR{vendor}=="0x10de", ATTR{class}=="0x03[0-9]*", ATTR{power/control}="auto"' | sudo tee /etc/udev/rules.d/80-nvidia-pm.rules

echo "Creating systemd service..."
sudo tee /etc/systemd/system/aggressive-fan-control.service << 'SERVICEEOF'
[Unit]
Description=Nuclear Fan Control V2 for ASUS G14
After=multi-user.target

[Service]
Type=simple
ExecStart=/home/$USER/nuclear-fan-control-v2.sh
Restart=always
User=root

[Install]
WantedBy=multi-user.target
SERVICEEOF

sudo systemctl daemon-reload
sudo systemctl enable aggressive-fan-control.service
sudo systemctl start aggressive-fan-control.service

echo "Setting up system tray monitor..."
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/g14-monitor.desktop << 'DESKTOPEOF'
[Desktop Entry]
Type=Application
Name=G14 Monitor
Comment=System tray monitor for ASUS G14
Exec=/home/$USER/g14-monitor.py
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
DESKTOPEOF

nohup ~/g14-monitor.py > /dev/null 2>&1 &

echo ""
echo "=== Installation Complete! ==="
echo "Please reboot for all changes to take effect."
echo ""
read -p "Reboot now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo reboot
fi
