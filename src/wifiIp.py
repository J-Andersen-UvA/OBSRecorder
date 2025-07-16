import psutil, socket

def get_ip_from_wifi():
    names_to_try = ['Wi-Fi', 'wlan0', 'wlp2s0', 'wlan1', 'WiFi']
    for iface_name in names_to_try:
        try:
            return get_ip_by_interface(iface_name)
        except RuntimeError:
            continue

def get_ip_by_interface(iface_name):
    addrs = psutil.net_if_addrs().get(iface_name, [])
    for snic in addrs:
        if snic.family == socket.AF_INET:
            return snic.address
    raise RuntimeError(f"{iface_name!r} has no IPv4 address")
