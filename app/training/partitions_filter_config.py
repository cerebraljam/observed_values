partitions = [
    {
        "label": "worst",
        "maximum": 99999999,
        "minimum": 10000,
        "bitsize": 19,
    },
    {
        "label": "suck",
        "maximum": 10000,
        "minimum": 1000,
        "bitsize": 23
    },
    {
        "label": "bad",
        "maximum": 1000,
        "minimum": 100,
        "bitsize": 26
    },
    {
        "label": "common",
        "maximum": 100,
        "minimum": 10,
        "bitsize": 29
    },
    {
        "label": "observed",
        "maximum": 10,
        "minimum": 1,
        "bitsize": 31
    }
]

def config_partitions():
    return partitions
