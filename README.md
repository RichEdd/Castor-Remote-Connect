# Castor Remote Connect

A high-performance remote desktop application with advanced controller support and low-latency streaming capabilities.

## Features

- Low-latency remote desktop streaming
- Advanced controller support with virtual controller switching
- Support for up to 4 players in mixed configurations (Local/LAN/Remote)
- Automatic NAT traversal and firewall handling
- Intuitive user interface
- Cross-platform support

## Requirements

- Python 3.8+
- PyQt6
- OpenCV
- FFmpeg
- vJoy (for Windows virtual controller support)

## Installation

### Host Application
```bash
pip install -r requirements.txt
python host_app.py
```

### Client Application
```bash
pip install -r requirements.txt
python client_app.py
```

## Project Structure

```
castor-remote-connect/
├── host/                 # Host application
│   ├── core/            # Core streaming and input handling
│   ├── controllers/     # Controller management
│   └── network/         # Network optimization and NAT traversal
├── client/              # Client application
│   ├── ui/             # User interface
│   ├── streaming/      # Stream receiving and display
│   └── input/          # Input handling
├── common/              # Shared code between host and client
└── tests/              # Test suite
```

## Development Status

This project is currently in active development. Features are being implemented in the following order:

1. Basic remote desktop streaming
2. Controller input handling
3. Virtual controller switching
4. Network optimization
5. User interface
6. Multi-player support

## License

MIT License 