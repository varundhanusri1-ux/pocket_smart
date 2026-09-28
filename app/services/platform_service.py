"""Platform source layer — a pluggable abstraction over recommendation sources.

IMPORTANT: No real marketplace APIs are integrated. All catalog data below is
SIMULATED demo data, clearly labelled as such in the UI. The registry design
(`PlatformSource` adapters) lets real affiliate/API integrations be added later
without touching the recommendation engine.
"""
import logging
import random

logger = logging.getLogger("pocketsmart.platforms")


class PlatformSource:
    """Base adapter for a recommendation source. Subclasses implement search()."""

    name: str = "Unknown"
    homepage: str = ""

    def search(self, category: str, max_price: float, planner_type: str) -> list[dict]:
        raise NotImplementedError


class SimulatedCatalogSource(PlatformSource):
    """Mock source serving demo catalog data. Clearly NOT live platform data."""

    live = False

    def __init__(self, name: str, homepage: str, catalog: dict[str, list[tuple[str, int, int]]]):
        self.name = name
        self.homepage = homepage
        self.catalog = catalog

    def search(self, category: str, max_price: float, planner_type: str) -> list[dict]:
        items = self.catalog.get(category, [])
        matches = [
            {"name": name, "estimated_price": low, "platform": self.name, "link": self.homepage}
            for name, low, high in items
            if low <= max_price * 1.25
        ]
        return matches or [
            {"name": name, "estimated_price": low, "platform": self.name, "link": self.homepage}
            for name, low, _high in items[:2]
        ]


# --------------------------------------------------------------------------- #
# Platform registry
# --------------------------------------------------------------------------- #

HOME_CATALOG = {
    "Furniture": [
        ("Fabric 3-seater sofa with wooden legs", 18000, 32000),
        ("Engineered wood TV unit with storage", 6500, 12000),
        ("Solid sheesham coffee table", 5500, 9000),
        ("L-shaped modular sofa (6-seater)", 35000, 55000),
        ("Queen-size bed with box storage", 16000, 28000),
        ("Ergonomic mesh office chair", 4500, 8500),
        ("Wardrobe with 2 sliding doors", 18000, 30000),
    ],
    "Lighting": [
        ("LED ceiling panel light pack (4 pcs)", 1800, 3500),
        ("Wooden tripod floor lamp", 2200, 4200),
        ("Wall sconce pair with warm LEDs", 1500, 3000),
        ("Smart RGB LED strip (10 m)", 900, 2000),
        ("Antique brass pendant light", 2000, 4500),
        ("Table lamp with fabric shade", 1200, 2600),
    ],
    "Fans & Cooling": [
        ("Energy-efficient BLDC ceiling fan", 3000, 5500),
        ("Designer anti-dust ceiling fan", 2600, 4800),
        ("Slim tower fan for bedrooms", 3500, 6500),
    ],
    "Dining": [
        ("4-seater engineered wood dining set", 11000, 20000),
        ("6-seater glass-top dining table", 18000, 32000),
        ("2-seater compact dining set", 6500, 11000),
        ("Dining chair set (4 pcs)", 6000, 12000),
    ],
    "Decor": [
        ("Framed wall art set (3 panels)", 1200, 2800),
        ("Indoor potted plant combo (4 pcs)", 900, 2000),
        ("Handwoven area rug (5x8 ft)", 3500, 7000),
        ("Decorative cushion cover set (5 pcs)", 600, 1400),
        ("LED photo clip string lights", 400, 900),
        ("Ceramic vase set with dried flowers", 800, 1800),
    ],
}

PARTY_CATALOG = {
    "Food & Catering": [
        ("Veg buffet catering per plate", 350, 800),
        ("Non-veg buffet catering per plate", 550, 1100),
        ("Live chaat counter (per 50 guests)", 4000, 8000),
        ("Birthday cake (1.5 kg custom)", 1200, 2500),
        ("Mocktail & beverage package per guest", 120, 250),
        ("Snacks starter combo platter", 800, 1800),
    ],
    "Venue": [
        ("Banquet hall rental (per day)", 15000, 40000),
        ("Rooftop party space (evening)", 10000, 25000),
        ("Garden lawn for outdoor events", 12000, 30000),
        ("OYO banquet-style venue with rooms", 12000, 28000),
    ],
    "Decoration": [
        ("Balloon & drapes decor package", 2500, 6000),
        ("Fresh flower stage decoration", 5000, 12000),
        ("Fairy light & lantern setup", 1800, 4000),
        ("Theme backdrop with props", 3500, 8000),
        ("Entrance arch with florals", 2500, 5500),
    ],
    "Entertainment": [
        ("DJ with sound system (4 hours)", 8000, 18000),
        ("Acoustic band performance (2 hours)", 10000, 20000),
        ("Party games kit & prizes", 1000, 2500),
        ("Photo booth with props (per evening)", 3000, 7000),
        ("Magic show for kids (1 hour)", 3000, 6000),
    ],
    "Accommodation": [
        ("OYO standard room per night", 1500, 3000),
        ("OYO premium room per night", 2500, 5000),
        ("Guest house block booking (per room)", 1200, 2500),
    ],
}

JEWELRY_CATALOG = {
    "Primary Piece": [
        ("Gold-plated kundan choker necklace set", 2500, 6000),
        ("Sterling silver jhumka earrings", 1200, 3200),
        ("American diamond pendant set", 1500, 4000),
        ("Pearl strand necklace with earrings", 2000, 5000),
        ("Antique gold-plated bangle set (4 pcs)", 1800, 4500),
        ("Meenakari statement ring", 800, 2200),
        ("Temple-design long haram necklace", 3000, 7000),
    ],
    "Matching Accessories": [
        ("Gold-plated maang tikka", 700, 1800),
        ("Crystal-studded bracelet", 900, 2400),
        ("Enamel toe-ring & anklet set", 600, 1500),
        ("Silk-thread jhumkas (lightweight)", 400, 1000),
        ("Oxidised silver nose pin", 300, 800),
    ],
    "Finishing Touches": [
        ("Velvet jewelry gift box", 300, 800),
        ("Anti-tarnish polishing cloth", 150, 400),
        ("Jewelry organizer pouch", 250, 600),
    ],
}

# planner_type -> category -> SimulatedCatalogSource
_SOURCES: dict[str, dict[str, list[PlatformSource]]] = {
    "home": {
        "Furniture": [SimulatedCatalogSource("IKEA", "https://www.ikea.com/in/en/", HOME_CATALOG),
                      SimulatedCatalogSource("Amazon", "https://www.amazon.in", HOME_CATALOG)],
        "Lighting": [SimulatedCatalogSource("Amazon", "https://www.amazon.in", HOME_CATALOG),
                     SimulatedCatalogSource("IKEA", "https://www.ikea.com/in/en/", HOME_CATALOG)],
        "Fans & Cooling": [SimulatedCatalogSource("Amazon", "https://www.amazon.in", HOME_CATALOG),
                           SimulatedCatalogSource("Flipkart", "https://www.flipkart.com", HOME_CATALOG)],
        "Dining": [SimulatedCatalogSource("IKEA", "https://www.ikea.com/in/en/", HOME_CATALOG),
                   SimulatedCatalogSource("Flipkart", "https://www.flipkart.com", HOME_CATALOG)],
        "Decor": [SimulatedCatalogSource("Flipkart", "https://www.flipkart.com", HOME_CATALOG),
                  SimulatedCatalogSource("Amazon", "https://www.amazon.in", HOME_CATALOG)],
    },
    "party": {
        "Food & Catering": [SimulatedCatalogSource("Swiggy", "https://www.swiggy.com", PARTY_CATALOG),
                            SimulatedCatalogSource("Zomato", "https://www.zomato.com", PARTY_CATALOG)],
        "Venue": [SimulatedCatalogSource("OYO", "https://www.oyorooms.com", PARTY_CATALOG)],
        "Decoration": [SimulatedCatalogSource("Amazon", "https://www.amazon.in", PARTY_CATALOG),
                       SimulatedCatalogSource("Flipkart", "https://www.flipkart.com", PARTY_CATALOG)],
        "Entertainment": [SimulatedCatalogSource("Local Vendor", "", PARTY_CATALOG),
                          SimulatedCatalogSource("Amazon", "https://www.amazon.in", PARTY_CATALOG)],
        "Accommodation": [SimulatedCatalogSource("OYO", "https://www.oyorooms.com", PARTY_CATALOG)],
    },
    "jewelry": {
        "Primary Piece": [SimulatedCatalogSource("Amazon", "https://www.amazon.in", JEWELRY_CATALOG),
                          SimulatedCatalogSource("Flipkart", "https://www.flipkart.com", JEWELRY_CATALOG)],
        "Matching Accessories": [SimulatedCatalogSource("Flipkart", "https://www.flipkart.com", JEWELRY_CATALOG),
                                 SimulatedCatalogSource("Amazon", "https://www.amazon.in", JEWELRY_CATALOG)],
        "Finishing Touches": [SimulatedCatalogSource("Local Retailer", "", JEWELRY_CATALOG)],
    },
}

PLATFORM_LABELS = ("Amazon", "Flipkart", "IKEA", "Swiggy", "Zomato", "OYO",
                   "Urban Company", "Local Vendor", "Local Retailer")


def known_platform(platform: str) -> str:
    """Coerce an AI-supplied platform label onto the known list."""
    if not platform:
        return "Local Vendor"
    cleaned = platform.strip().title()
    for known in PLATFORM_LABELS:
        if known.lower() in cleaned.lower():
            return known
    return "Local Vendor"


def platform_homepage(platform: str) -> str:
    for category_sources in _SOURCES.values():
        for sources in category_sources.values():
            for source in sources:
                if source.name == platform and source.homepage:
                    return source.homepage
    return ""


def demo_items_for_category(planner_type: str, category: str, max_price: float,
                            count: int = 2) -> list[dict]:
    """Fetch demo items from the simulated catalog for one category."""
    sources = _SOURCES.get(planner_type, {}).get(category)
    if not sources:
        return []
    picked: list[dict] = []
    source = random.choice(sources)
    for match in source.search(category, max_price, planner_type):
        if len(picked) >= count:
            break
        item = dict(match)
        item["source_kind"] = "simulated"
        picked.append(item)
    return picked


def planner_categories(planner_type: str) -> list[str]:
    return list(_SOURCES.get(planner_type, {}).keys())
