# Gl-Transitions web V1.0

Gl-Transitions web is a video and webpage driven version of https://gl-transitions.com/ for videos. It leverages FastAPI, Uvicorn, ModernGL, and shaders to merge two videos via GPU-accelerated transitions.

## Features

- Select from dozens of shader transitions sourced from gl-transitions.com
- Merge two MP4 videos using GPU-accelerated shaders
- Web-based UI served by FastAPI
- Easy installation via install.bat

## Installation

Run install.bat to set up a Python virtual environment and install dependencies:

```
install.bat
```

## Usage

1. After installation, run `start.bat` to launch the server and open your browser.
2. In the web UI, upload `Video1.mp4` and `Video2.mp4`.
3. Select a shader from the list.
4. Click "Merge" and download the resulting `merged_output.mp4`.

## Adding Shaders

Add or modify `.glsl` files in the `shaders/` directory. The UI automatically detects new shaders.

## Credits

Based on shaders from https://gl-transitions.com/.

## Follow

Follow me on X: @OneHung
