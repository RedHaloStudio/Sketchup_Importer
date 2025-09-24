# slapi_rs

Rust bindings for the official SketchUp API (SLAPI).

## Prerequisites

- Rust toolchain (cargo, rustc)
- SketchUp SDK (https://extensions.sketchup.com/sketchup-sdk)

## Setup

1. Download the SketchUp SDK
2. Extract the SDK and copy the `SketchUpAPI.framework` (macOS) or SketchUp API libraries (Windows/Linux) to an accessible location
3. Set the environment variable `SKETCHUP_SDK_PATH` to the directory containing the SketchUp SDK frameworks/libraries

## Building

```bash
cargo build
```

## Usage

```rust
use slapi_rs::prelude::*;

fn main() {
    // Initialize the SketchUp API
    let result = slapi_rs::initialize();
    
    // Create or open a model
    let mut model = SUModelRef::default();
    
    // Work with the model
    
    // Release resources
    slapi_rs::terminate();
}
```

## Platform Support

- macOS
- Windows
- Linux (limited support, based on SDK availability)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 