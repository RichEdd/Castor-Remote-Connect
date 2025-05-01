# Castor Remote Connect

A high-performance remote desktop application with advanced controller support and low-latency streaming capabilities.

## Features

- Low-latency remote desktop streaming
- Advanced controller support with virtual controller switching
- Support for up to 4 players in mixed configurations (Local/LAN/Remote)
- Automatic NAT traversal and firewall handling
- Intuitive user interface
- Cross-platform support

## For End Users

### Windows
1. Download the latest release from the releases page
2. Extract the ZIP file
3. Run either:
   - `CastorRemoteConnect-Host.exe` (on the computer you want to control)
   - `CastorRemoteConnect-Client.exe` (on the computer you want to control from)

### Linux
1. Download the latest release from the releases page
2. Extract the ZIP file
3. Make the executables executable:
   ```bash
   chmod +x CastorRemoteConnect-Host
   chmod +x CastorRemoteConnect-Client
   ```
4. Run either:
   - `./CastorRemoteConnect-Host` (on the computer you want to control)
   - `./CastorRemoteConnect-Client` (on the computer you want to control from)

## For Developers

### Requirements

- Python 3.8+
- PyQt6
- OpenCV
- FFmpeg
- vJoy (for Windows virtual controller support)

### Building from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/castor-remote-connect.git
   cd castor-remote-connect
   ```

2. Install build requirements:
   ```bash
   python -m pip install -r requirements.txt
   python -m pip install pyinstaller
   ```

3. Build the executables:
   ```bash
   python build.py
   ```

4. The executables will be created in the `dist` directory.

### Project Structure

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