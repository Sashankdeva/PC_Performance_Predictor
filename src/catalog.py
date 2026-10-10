"""Component catalog for the PC builder.

Specs are manufacturer figures (cores, clocks, sockets, memory support).
`power_w` is the CPU's maximum package power (Intel PL2 / AMD PPT) or the GPU's
board power. `gpu_level` is our 0-12 tier scale matching the dataset's
GPU_Level (0 = integrated graphics, 12 = flagship). Cooler `capacity_w` values
are approximate heat-dissipation ratings.

Gaming ratings used only by the FPS estimator (approximate, relative):
  CPU `gaming_index`  - gaming performance, Ryzen 7 9800X3D = 100
  CPU `igpu_index`    - integrated graphics performance on the GPU scale
  GPU `perf_index`    - 1440p raster performance, RTX 4090 = 100
"""

def _cpu(name, cores, boost_ghz, socket, power_w, igpu, stock_cooler, gaming_index,
         igpu_index=0):
    return {"name": name, "cores": cores, "boost_ghz": boost_ghz, "socket": socket,
            "power_w": power_w, "igpu": igpu, "stock_cooler": stock_cooler,
            "gaming_index": gaming_index, "igpu_index": igpu_index if igpu else 0}


CPUS = [
    # Intel 10th gen (LGA1200, DDR4)
    _cpu("Intel Core i3-10100", 4, 4.3, "LGA1200", 90, True, True, 40, 2),
    _cpu("Intel Core i5-10400", 6, 4.3, "LGA1200", 134, True, True, 45, 2),
    _cpu("Intel Core i7-10700K", 8, 5.1, "LGA1200", 229, True, False, 52, 2),
    _cpu("Intel Core i9-10900K", 10, 5.3, "LGA1200", 250, True, False, 55, 2),
    # Intel 12th-14th gen (LGA1700, DDR4 or DDR5 depending on board)
    _cpu("Intel Core i3-12100F", 4, 4.3, "LGA1700", 89, False, True, 52),
    _cpu("Intel Core i3-12100", 4, 4.3, "LGA1700", 89, True, True, 52, 3),
    _cpu("Intel Core i5-12400F", 6, 4.4, "LGA1700", 117, False, True, 60),
    _cpu("Intel Core i5-12400", 6, 4.4, "LGA1700", 117, True, True, 60, 3),
    _cpu("Intel Core i5-12600K", 10, 4.9, "LGA1700", 150, True, False, 68, 3),
    _cpu("Intel Core i7-12700K", 12, 5.0, "LGA1700", 190, True, False, 72, 3),
    _cpu("Intel Core i9-12900K", 16, 5.2, "LGA1700", 241, True, False, 75, 3),
    _cpu("Intel Core i5-13400F", 10, 4.6, "LGA1700", 148, False, True, 63),
    _cpu("Intel Core i5-14400F", 10, 4.7, "LGA1700", 148, False, True, 65),
    _cpu("Intel Core i5-13600K", 14, 5.1, "LGA1700", 181, True, False, 75, 3),
    _cpu("Intel Core i5-14600K", 14, 5.3, "LGA1700", 181, True, False, 77, 3),
    _cpu("Intel Core i7-13700K", 16, 5.4, "LGA1700", 253, True, False, 79, 3),
    _cpu("Intel Core i7-14700K", 20, 5.6, "LGA1700", 253, True, False, 82, 3),
    _cpu("Intel Core i9-13900K", 24, 5.8, "LGA1700", 253, True, False, 83, 3),
    _cpu("Intel Core i9-14900K", 24, 6.0, "LGA1700", 253, True, False, 85, 3),
    # Intel Core Ultra 200S (LGA1851, DDR5)
    _cpu("Intel Core Ultra 5 245K", 14, 5.2, "LGA1851", 159, True, False, 73, 5),
    _cpu("Intel Core Ultra 7 265K", 20, 5.5, "LGA1851", 250, True, False, 78, 5),
    _cpu("Intel Core Ultra 9 285K", 24, 5.7, "LGA1851", 250, True, False, 80, 5),
    # AMD Ryzen 3000 / 5000 (AM4, DDR4)
    _cpu("AMD Ryzen 5 3600", 6, 4.2, "AM4", 88, False, True, 45),
    _cpu("AMD Ryzen 5 5500", 6, 4.2, "AM4", 88, False, True, 50),
    _cpu("AMD Ryzen 5 5600", 6, 4.4, "AM4", 88, False, True, 57),
    _cpu("AMD Ryzen 5 5600X", 6, 4.6, "AM4", 88, False, True, 59),
    _cpu("AMD Ryzen 5 5600G", 6, 4.4, "AM4", 88, True, True, 50, 6),
    _cpu("AMD Ryzen 7 5700X", 8, 4.6, "AM4", 88, False, False, 60),
    _cpu("AMD Ryzen 7 5700X3D", 8, 4.1, "AM4", 142, False, False, 70),
    _cpu("AMD Ryzen 7 5800X", 8, 4.7, "AM4", 142, False, False, 62),
    _cpu("AMD Ryzen 7 5800X3D", 8, 4.5, "AM4", 142, False, False, 75),
    _cpu("AMD Ryzen 9 5900X", 12, 4.8, "AM4", 142, False, False, 63),
    _cpu("AMD Ryzen 9 5950X", 16, 4.9, "AM4", 142, False, False, 64),
    # AMD Ryzen 7000 / 8000 / 9000 (AM5, DDR5)
    _cpu("AMD Ryzen 5 7600", 6, 5.1, "AM5", 88, True, True, 72, 2),
    _cpu("AMD Ryzen 5 7600X", 6, 5.3, "AM5", 142, True, False, 74, 2),
    _cpu("AMD Ryzen 5 8600G", 6, 5.0, "AM5", 88, True, True, 62, 12),
    _cpu("AMD Ryzen 5 9600X", 6, 5.4, "AM5", 88, True, False, 78, 2),
    _cpu("AMD Ryzen 7 7700X", 8, 5.4, "AM5", 142, True, False, 77, 2),
    _cpu("AMD Ryzen 7 9700X", 8, 5.5, "AM5", 88, True, False, 80, 2),
    _cpu("AMD Ryzen 7 7800X3D", 8, 5.0, "AM5", 162, True, False, 90, 2),
    _cpu("AMD Ryzen 7 9800X3D", 8, 5.2, "AM5", 162, True, False, 100, 2),
    _cpu("AMD Ryzen 9 7900X", 12, 5.6, "AM5", 230, True, False, 78, 2),
    _cpu("AMD Ryzen 9 9900X", 12, 5.6, "AM5", 162, True, False, 82, 2),
    _cpu("AMD Ryzen 9 7950X", 16, 5.7, "AM5", 230, True, False, 80, 2),
    _cpu("AMD Ryzen 9 9950X", 16, 5.7, "AM5", 230, True, False, 84, 2),
    _cpu("AMD Ryzen 9 9950X3D", 16, 5.7, "AM5", 230, True, False, 99, 2),
]


def _board(name, socket, ram_type, form_factor, ram_slots):
    return {"name": name, "socket": socket, "ram_type": ram_type,
            "form_factor": form_factor, "ram_slots": ram_slots}


MOTHERBOARDS = [
    # LGA1200
    _board("MSI B460M-A PRO", "LGA1200", "DDR4", "Micro-ATX", 2),
    _board("Gigabyte B560M DS3H", "LGA1200", "DDR4", "Micro-ATX", 4),
    _board("ASUS PRIME B560-PLUS", "LGA1200", "DDR4", "ATX", 4),
    _board("ASUS ROG STRIX Z490-E GAMING", "LGA1200", "DDR4", "ATX", 4),
    # LGA1700 DDR4
    _board("Gigabyte B660M DS3H DDR4", "LGA1700", "DDR4", "Micro-ATX", 4),
    _board("MSI PRO B760M-A WIFI DDR4", "LGA1700", "DDR4", "Micro-ATX", 4),
    _board("ASUS TUF GAMING B760-PLUS WIFI D4", "LGA1700", "DDR4", "ATX", 4),
    # LGA1700 DDR5
    _board("ASUS PRIME B760M-A WIFI (DDR5)", "LGA1700", "DDR5", "Micro-ATX", 4),
    _board("Gigabyte B760 AORUS ELITE AX (DDR5)", "LGA1700", "DDR5", "ATX", 4),
    _board("MSI PRO Z790-P WIFI (DDR5)", "LGA1700", "DDR5", "ATX", 4),
    _board("MSI MAG Z790 TOMAHAWK WIFI (DDR5)", "LGA1700", "DDR5", "ATX", 4),
    _board("ASUS ROG STRIX Z790-E GAMING WIFI", "LGA1700", "DDR5", "ATX", 4),
    _board("ASUS ROG STRIX B760-I GAMING WIFI", "LGA1700", "DDR5", "Mini-ITX", 2),
    # LGA1851
    _board("MSI PRO B860M-A WIFI", "LGA1851", "DDR5", "Micro-ATX", 4),
    _board("ASUS PRIME Z890-P WIFI", "LGA1851", "DDR5", "ATX", 4),
    _board("MSI MAG Z890 TOMAHAWK WIFI", "LGA1851", "DDR5", "ATX", 4),
    _board("Gigabyte Z890 AORUS ELITE WIFI7", "LGA1851", "DDR5", "ATX", 4),
    # AM4
    _board("ASUS PRIME A520M-A", "AM4", "DDR4", "Micro-ATX", 4),
    _board("ASRock B450M Steel Legend", "AM4", "DDR4", "Micro-ATX", 4),
    _board("Gigabyte B550M DS3H", "AM4", "DDR4", "Micro-ATX", 4),
    _board("MSI B450 TOMAHAWK MAX", "AM4", "DDR4", "ATX", 4),
    _board("MSI MAG B550 TOMAHAWK", "AM4", "DDR4", "ATX", 4),
    _board("ASUS ROG STRIX B550-F GAMING", "AM4", "DDR4", "ATX", 4),
    _board("MSI MPG B550I GAMING EDGE WIFI", "AM4", "DDR4", "Mini-ITX", 2),
    # AM5
    _board("MSI PRO B650M-A WIFI", "AM5", "DDR5", "Micro-ATX", 4),
    _board("ASUS TUF GAMING B650-PLUS WIFI", "AM5", "DDR5", "ATX", 4),
    _board("MSI MAG B650 TOMAHAWK WIFI", "AM5", "DDR5", "ATX", 4),
    _board("Gigabyte B650 AORUS ELITE AX", "AM5", "DDR5", "ATX", 4),
    _board("MSI MAG X870 TOMAHAWK WIFI", "AM5", "DDR5", "ATX", 4),
    _board("ASUS ROG STRIX X670E-E GAMING WIFI", "AM5", "DDR5", "ATX", 4),
    _board("ASUS ROG STRIX X870E-E GAMING WIFI", "AM5", "DDR5", "ATX", 4),
    _board("ASRock B650I Lightning WiFi", "AM5", "DDR5", "Mini-ITX", 2),
    _board("ASUS ROG STRIX B650E-I GAMING WIFI", "AM5", "DDR5", "Mini-ITX", 2),
]


def _ram(name, capacity_gb, sticks, ram_type):
    return {"name": name, "capacity_gb": capacity_gb, "sticks": sticks, "ram_type": ram_type}


RAM_KITS = [
    # DDR4
    _ram("Kingston FURY Beast 4GB (1x4GB) DDR4-2666", 4, 1, "DDR4"),
    _ram("Corsair Vengeance LPX 8GB (1x8GB) DDR4-3200", 8, 1, "DDR4"),
    _ram("Corsair Vengeance LPX 16GB (1x16GB) DDR4-3200", 16, 1, "DDR4"),
    _ram("Corsair Vengeance LPX 16GB (2x8GB) DDR4-3200", 16, 2, "DDR4"),
    _ram("G.Skill Ripjaws V 16GB (2x8GB) DDR4-3600", 16, 2, "DDR4"),
    _ram("Corsair Vengeance LPX 32GB (2x16GB) DDR4-3200", 32, 2, "DDR4"),
    _ram("G.Skill Ripjaws V 32GB (2x16GB) DDR4-3600", 32, 2, "DDR4"),
    _ram("Kingston FURY Beast 64GB (2x32GB) DDR4-3200", 64, 2, "DDR4"),
    _ram("G.Skill Ripjaws V 64GB (4x16GB) DDR4-3600", 64, 4, "DDR4"),
    _ram("Corsair Vengeance LPX 128GB (4x32GB) DDR4-3200", 128, 4, "DDR4"),
    # DDR5
    _ram("Kingston FURY Beast 8GB (1x8GB) DDR5-4800", 8, 1, "DDR5"),
    _ram("Crucial 16GB (1x16GB) DDR5-5600", 16, 1, "DDR5"),
    _ram("Kingston FURY Beast 16GB (2x8GB) DDR5-5600", 16, 2, "DDR5"),
    _ram("Corsair Vengeance 32GB (2x16GB) DDR5-5600", 32, 2, "DDR5"),
    _ram("G.Skill Flare X5 32GB (2x16GB) DDR5-6000", 32, 2, "DDR5"),
    _ram("G.Skill Trident Z5 RGB 32GB (2x16GB) DDR5-6400", 32, 2, "DDR5"),
    _ram("Corsair Vengeance 48GB (2x24GB) DDR5-6000", 48, 2, "DDR5"),
    _ram("G.Skill Trident Z5 Neo 64GB (2x32GB) DDR5-6000", 64, 2, "DDR5"),
    _ram("Kingston FURY Beast 64GB (2x32GB) DDR5-6400", 64, 2, "DDR5"),
    _ram("Corsair Vengeance 96GB (2x48GB) DDR5-6000", 96, 2, "DDR5"),
    _ram("Kingston FURY Beast 128GB (4x32GB) DDR5-5600", 128, 4, "DDR5"),
]


def _drive(name, capacity_gb, drive_type):
    return {"name": name, "capacity_gb": capacity_gb, "type": drive_type}


# capacity_gb uses binary sizes (1TB -> 1024) to match the dataset's Storage_GB values
STORAGE = [
    # NVMe SSDs
    _drive("Kingston NV2 250GB (NVMe SSD)", 256, "NVMe SSD"),
    _drive("Kingston NV2 500GB (NVMe SSD)", 512, "NVMe SSD"),
    _drive("Crucial P3 500GB (NVMe SSD)", 512, "NVMe SSD"),
    _drive("Kingston NV2 1TB (NVMe SSD)", 1024, "NVMe SSD"),
    _drive("Crucial P3 1TB (NVMe SSD)", 1024, "NVMe SSD"),
    _drive("Crucial P3 Plus 1TB (NVMe SSD)", 1024, "NVMe SSD"),
    _drive("WD Blue SN580 1TB (NVMe SSD)", 1024, "NVMe SSD"),
    _drive("Samsung 990 EVO Plus 1TB (NVMe SSD)", 1024, "NVMe SSD"),
    _drive("Crucial T500 1TB (NVMe SSD)", 1024, "NVMe SSD"),
    _drive("Samsung 990 PRO 1TB (NVMe SSD)", 1024, "NVMe SSD"),
    _drive("WD Black SN850X 1TB (NVMe SSD)", 1024, "NVMe SSD"),
    _drive("Kingston NV2 2TB (NVMe SSD)", 2048, "NVMe SSD"),
    _drive("Crucial P3 Plus 2TB (NVMe SSD)", 2048, "NVMe SSD"),
    _drive("WD Blue SN580 2TB (NVMe SSD)", 2048, "NVMe SSD"),
    _drive("Samsung 990 EVO Plus 2TB (NVMe SSD)", 2048, "NVMe SSD"),
    _drive("Crucial T500 2TB (NVMe SSD)", 2048, "NVMe SSD"),
    _drive("Samsung 990 PRO 2TB (NVMe SSD)", 2048, "NVMe SSD"),
    _drive("WD Black SN850X 2TB (NVMe SSD)", 2048, "NVMe SSD"),
    _drive("Crucial T705 2TB (PCIe 5.0 NVMe SSD)", 2048, "NVMe SSD"),
    _drive("Samsung 990 PRO 4TB (NVMe SSD)", 4096, "NVMe SSD"),
    _drive("WD Black SN850X 4TB (NVMe SSD)", 4096, "NVMe SSD"),
    # SATA SSDs
    _drive("Crucial BX500 240GB (SATA SSD)", 256, "SATA SSD"),
    _drive("Samsung 870 EVO 250GB (SATA SSD)", 256, "SATA SSD"),
    _drive("Samsung 870 EVO 500GB (SATA SSD)", 512, "SATA SSD"),
    _drive("Crucial MX500 500GB (SATA SSD)", 512, "SATA SSD"),
    _drive("Samsung 870 EVO 1TB (SATA SSD)", 1024, "SATA SSD"),
    _drive("Crucial MX500 1TB (SATA SSD)", 1024, "SATA SSD"),
    _drive("Samsung 870 EVO 2TB (SATA SSD)", 2048, "SATA SSD"),
    _drive("Crucial MX500 2TB (SATA SSD)", 2048, "SATA SSD"),
    # Hard drives
    _drive("WD Blue 1TB 7200 RPM (HDD)", 1024, "HDD"),
    _drive("Seagate BarraCuda 1TB (HDD)", 1024, "HDD"),
    _drive("Seagate BarraCuda 2TB (HDD)", 2048, "HDD"),
    _drive("Toshiba P300 2TB (HDD)", 2048, "HDD"),
    _drive("Seagate BarraCuda 4TB (HDD)", 4096, "HDD"),
]


def _gpu(name, gpu_level, power_w, perf_index):
    return {"name": name, "gpu_level": gpu_level, "power_w": power_w, "perf_index": perf_index}


GPUS = [
    _gpu("None (use CPU integrated graphics)", 0, 0, 0),
    _gpu("NVIDIA GeForce GTX 1650", 1, 75, 11),
    _gpu("AMD Radeon RX 6500 XT", 2, 107, 13),
    _gpu("NVIDIA GeForce GTX 1660 SUPER", 2, 125, 18),
    _gpu("NVIDIA GeForce RTX 3050 8GB", 3, 130, 19),
    _gpu("NVIDIA GeForce RTX 2060", 3, 160, 21),
    _gpu("AMD Radeon RX 6600", 4, 132, 25),
    _gpu("Intel Arc A750", 4, 225, 27),
    _gpu("AMD Radeon RX 6650 XT", 4, 180, 29),
    _gpu("NVIDIA GeForce RTX 3060 12GB", 5, 170, 28),
    _gpu("AMD Radeon RX 7600", 5, 165, 30),
    _gpu("NVIDIA GeForce RTX 4060", 5, 115, 31),
    _gpu("Intel Arc B580", 5, 190, 33),
    _gpu("NVIDIA GeForce RTX 5060", 5, 145, 35),
    _gpu("NVIDIA GeForce RTX 3060 Ti", 6, 200, 36),
    _gpu("NVIDIA GeForce RTX 4060 Ti", 6, 160, 37),
    _gpu("AMD Radeon RX 6700 XT", 6, 230, 38),
    _gpu("NVIDIA GeForce RTX 5060 Ti 16GB", 6, 180, 42),
    _gpu("NVIDIA GeForce RTX 3070", 7, 220, 42),
    _gpu("AMD Radeon RX 7700 XT", 7, 245, 45),
    _gpu("NVIDIA GeForce RTX 4070", 8, 200, 50),
    _gpu("AMD Radeon RX 7800 XT", 8, 263, 53),
    _gpu("AMD Radeon RX 7900 GRE", 9, 260, 57),
    _gpu("NVIDIA GeForce RTX 4070 SUPER", 9, 220, 58),
    _gpu("NVIDIA GeForce RTX 5070", 9, 250, 60),
    _gpu("AMD Radeon RX 9070", 9, 220, 64),
    _gpu("NVIDIA GeForce RTX 4070 Ti SUPER", 10, 285, 67),
    _gpu("AMD Radeon RX 7900 XT", 10, 315, 69),
    _gpu("AMD Radeon RX 9070 XT", 10, 304, 72),
    _gpu("NVIDIA GeForce RTX 5070 Ti", 10, 300, 74),
    _gpu("NVIDIA GeForce RTX 4080 SUPER", 11, 320, 78),
    _gpu("AMD Radeon RX 7900 XTX", 11, 355, 80),
    _gpu("NVIDIA GeForce RTX 5080", 11, 360, 84),
    _gpu("NVIDIA GeForce RTX 4090", 12, 450, 100),
    _gpu("NVIDIA GeForce RTX 5090", 12, 575, 128),
]

PSUS = [
    {"name": "EVGA 500 W1 (500W, 80+ White)", "watts": 500},
    {"name": "Thermaltake Smart 500W (80+ White)", "watts": 500},
    {"name": "Corsair CV550 (550W, 80+ Bronze)", "watts": 550},
    {"name": "Corsair CX650 (650W, 80+ Bronze)", "watts": 650},
    {"name": "MSI MAG A650BN (650W, 80+ Bronze)", "watts": 650},
    {"name": "Corsair RM650 (650W, 80+ Gold)", "watts": 650},
    {"name": "Cooler Master MWE 750 Bronze V2 (750W, 80+ Bronze)", "watts": 750},
    {"name": "Corsair RM750e (750W, 80+ Gold)", "watts": 750},
    {"name": "MSI MAG A750GL (750W, 80+ Gold)", "watts": 750},
    {"name": "Seasonic FOCUS GX-750 (750W, 80+ Gold)", "watts": 750},
    {"name": "Corsair RM850x (850W, 80+ Gold)", "watts": 850},
    {"name": "Seasonic FOCUS GX-850 (850W, 80+ Gold)", "watts": 850},
    {"name": "MSI MAG A850GL (850W, 80+ Gold)", "watts": 850},
    {"name": "Corsair RM1000x (1000W, 80+ Gold)", "watts": 1000},
    {"name": "be quiet! Pure Power 12 M 1000W (80+ Gold)", "watts": 1000},
    {"name": "Seasonic FOCUS GX-1000 (1000W, 80+ Gold)", "watts": 1000},
    {"name": "Corsair RM1200x SHIFT (1200W, 80+ Gold)", "watts": 1200},
    {"name": "ASUS ROG THOR 1200P2 (1200W, 80+ Platinum)", "watts": 1200},
    {"name": "Corsair HX1500i (1500W, 80+ Platinum)", "watts": 1500},
    {"name": "Seasonic PRIME TX-1600 (1600W, 80+ Titanium)", "watts": 1600},
]

COOLERS = [
    {"name": "Stock cooler (bundled with CPU)", "capacity_w": 95, "stock": True},
    {"name": "Cooler Master Hyper 212 (air)", "capacity_w": 150, "stock": False},
    {"name": "Noctua NH-U12S redux (air)", "capacity_w": 180, "stock": False},
    {"name": "ARCTIC Freezer 36 (air)", "capacity_w": 200, "stock": False},
    {"name": "DeepCool AK400 (air)", "capacity_w": 220, "stock": False},
    {"name": "Thermalright Peerless Assassin 120 SE (air)", "capacity_w": 245, "stock": False},
    {"name": "Noctua NH-D15 (air)", "capacity_w": 250, "stock": False},
    {"name": "DeepCool AK620 (air)", "capacity_w": 260, "stock": False},
    {"name": "Thermalright Phantom Spirit 120 SE (air)", "capacity_w": 265, "stock": False},
    {"name": "be quiet! Dark Rock Pro 5 (air)", "capacity_w": 270, "stock": False},
    {"name": "NZXT Kraken 240 (AIO liquid)", "capacity_w": 260, "stock": False},
    {"name": "Corsair iCUE H100i ELITE (240mm AIO)", "capacity_w": 270, "stock": False},
    {"name": "Arctic Liquid Freezer III 240 (AIO liquid)", "capacity_w": 280, "stock": False},
    {"name": "NZXT Kraken 360 (AIO liquid)", "capacity_w": 300, "stock": False},
    {"name": "Lian Li Galahad II Trinity 360 (AIO liquid)", "capacity_w": 320, "stock": False},
    {"name": "Arctic Liquid Freezer III 360 (AIO liquid)", "capacity_w": 330, "stock": False},
    {"name": "Corsair iCUE H150i ELITE (360mm AIO)", "capacity_w": 330, "stock": False},
]

# max_form_factor: largest motherboard the case accepts
CASES = [
    {"name": "Generic budget Micro-ATX case", "max_form_factor": "Micro-ATX", "airflow": "Low"},
    {"name": "Thermaltake Versa H18", "max_form_factor": "Micro-ATX", "airflow": "Low"},
    {"name": "Jonsbo D31", "max_form_factor": "Micro-ATX", "airflow": "Medium"},
    {"name": "Fractal Design Pop Mini Air", "max_form_factor": "Micro-ATX", "airflow": "High"},
    {"name": "Cooler Master NR200P", "max_form_factor": "Mini-ITX", "airflow": "Medium"},
    {"name": "Lian Li A4-H2O", "max_form_factor": "Mini-ITX", "airflow": "Medium"},
    {"name": "Generic budget ATX case (solid front)", "max_form_factor": "ATX", "airflow": "Low"},
    {"name": "Fractal Design North", "max_form_factor": "ATX", "airflow": "Medium"},
    {"name": "Lian Li O11 Dynamic EVO", "max_form_factor": "ATX", "airflow": "Medium"},
    {"name": "NZXT H5 Flow", "max_form_factor": "ATX", "airflow": "High"},
    {"name": "NZXT H6 Flow", "max_form_factor": "ATX", "airflow": "High"},
    {"name": "Corsair 4000D Airflow", "max_form_factor": "ATX", "airflow": "High"},
    {"name": "Corsair 5000D Airflow", "max_form_factor": "ATX", "airflow": "High"},
    {"name": "Lian Li Lancool 216", "max_form_factor": "ATX", "airflow": "High"},
    {"name": "Fractal Design Meshify 2", "max_form_factor": "ATX", "airflow": "High"},
    {"name": "DeepCool CH560", "max_form_factor": "ATX", "airflow": "High"},
    {"name": "Montech AIR 903 MAX", "max_form_factor": "ATX", "airflow": "High"},
]

EXTRA_CASE_FANS = [0, 1, 2, 3, 4, 6]

OPERATING_SYSTEMS = {
    "Windows 11": "Windows",
    "Windows 10": "Windows",
    "Ubuntu 24.04 LTS": "Linux",
    "Linux Mint": "Linux",
    "Fedora": "Linux",
    "Pop!_OS": "Linux",
    "Arch Linux": "Linux",
}
