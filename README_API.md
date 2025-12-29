# SAM3 Video Segmentation API

A FastAPI backend for video segmentation using Meta's Segment Anything Model 3 (SAM3). This API allows you to upload a video and extract specific objects (like dogs) while removing the background.

## Features

- **Text-based Object Segmentation**: Describe what you want to keep (e.g., "dog", "cat", "person")
- **Multiple Background Modes**:
  - `transparent`: RGBA with transparent background (WebM format)
  - `black`: Solid black background
  - `white`: Solid white background
  - `blur`: Blurred version of the original background
- **Multiple Output Formats**: MP4, WebM (with alpha), MOV
- **REST API**: Easy integration with any application
- **Automatic Model Loading**: SAM3 model loads on startup
- **GPU Acceleration**: Utilizes CUDA for fast processing

## Requirements

- Python 3.8+
- CUDA-capable GPU with 16GB+ VRAM recommended
- FFmpeg (for alpha channel video encoding)

## Installation

1. **Install SAM3** (if not already installed):
   ```bash
   cd sam3-dev
   pip install -e .
   ```

2. **Install API dependencies**:
   ```bash
   pip install -r requirements-api.txt
   ```

3. **Install FFmpeg** (required for transparent video output):
   - Windows: `winget install ffmpeg` or download from https://ffmpeg.org/
   - Linux: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

## Running the API

### Quick Start

```bash
python run_api.py
```

The server will start at `http://localhost:8000`

### With Options

```bash
python run_api.py --host 0.0.0.0 --port 8000 --log-level debug
```

### Available Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind the server |
| `--port` | `8000` | Port to run the server |
| `--reload` | `False` | Enable auto-reload for development |
| `--log-level` | `info` | Logging level (debug, info, warning, error) |

## API Endpoints

### Health Check
```
GET /health
```
Check API health, GPU availability, and model status.

### Segment Dog from Video
```
POST /segment/dog
```
Extract only dogs from a video, removing the background.

**Parameters:**
- `video`: Video file (required)
- `background_mode`: transparent, black, white, blur (default: transparent)
- `output_format`: mp4, webm, mov (default: mp4)
- `include_overlay`: Include visualization video (default: false)

### Segment with Custom Prompt
```
POST /segment
```
Extract any object described by text.

**Parameters:**
- `video`: Video file (required)
- `prompt`: Text description of object to segment (default: "dog")
- `background_mode`: transparent, black, white, blur
- `output_format`: mp4, webm, mov
- `include_overlay`: Include visualization video

### Download Processed Video
```
GET /download/{task_id}/{filename}
```
Download a processed video file.

### Cleanup Task
```
DELETE /cleanup/{task_id}
```
Remove files for a completed task.

### List Tasks
```
GET /tasks
```
List all task directories and files.

## Usage Examples

### Using cURL

**Segment a dog from video with black background:**
```bash
curl -X POST "http://localhost:8000/segment/dog" \
  -F "video=@my_dog_video.mp4" \
  -F "background_mode=black" \
  -F "output_format=mp4"
```

**Segment any object with transparent background:**
```bash
curl -X POST "http://localhost:8000/segment" \
  -F "video=@video.mp4" \
  -F "prompt=cat" \
  -F "background_mode=transparent" \
  -F "output_format=webm"
```

### Using Python

```python
import requests

# Upload video and segment dogs
with open("dog_video.mp4", "rb") as f:
    response = requests.post(
        "http://localhost:8000/segment/dog",
        files={"video": f},
        data={
            "background_mode": "black",
            "output_format": "mp4",
        }
    )

result = response.json()
print(f"Success: {result['success']}")
print(f"Objects detected: {result['objects_detected']}")
print(f"Output: {result['output_video_path']}")

# Download the result
if result['output_video_path']:
    download_url = f"http://localhost:8000{result['output_video_path']}"
    video_response = requests.get(download_url)
    with open("output.mp4", "wb") as f:
        f.write(video_response.content)
```

### Using JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append('video', videoFile);
formData.append('prompt', 'dog');
formData.append('background_mode', 'transparent');

const response = await fetch('http://localhost:8000/segment', {
    method: 'POST',
    body: formData,
});

const result = await response.json();
console.log('Output video:', result.output_video_path);
```

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Response Format

### Success Response
```json
{
    "success": true,
    "message": "Successfully segmented 2 object(s) matching 'dog'",
    "output_video_path": "/outputs/abc123/segmented.mp4",
    "overlay_video_path": null,
    "total_frames": 150,
    "objects_detected": 2,
    "processing_time_seconds": 45.2
}
```

### Error Response
```json
{
    "detail": "No objects matching 'cat' detected in the video"
}
```

## Project Structure

```
sam3-dev/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   └── sam3_service.py  # SAM3 video processing
│   └── utils/
│       ├── __init__.py
│       └── video_utils.py   # Video processing utilities
├── outputs/                  # Processed videos (auto-created)
├── requirements-api.txt      # API dependencies
├── run_api.py               # Server runner script
└── README_API.md            # This file
```

## Performance Tips

1. **GPU Memory**: SAM3 requires significant GPU memory. 16GB+ VRAM recommended.
2. **Video Length**: Longer videos take more time. Consider trimming videos if possible.
3. **Resolution**: Higher resolution = more processing time. Consider downscaling if needed.
4. **Single Worker**: The API runs with a single worker to manage GPU memory properly.

## Troubleshooting

### "CUDA out of memory"
- Reduce video resolution or length
- Close other GPU applications
- Restart the server to clear GPU memory

### "No objects detected"
- Try a more specific prompt (e.g., "golden retriever" instead of "dog")
- Ensure the object is clearly visible in the video
- Check if the video has good lighting

### Model loading fails
- Ensure CUDA is properly installed
- Check GPU memory availability
- Verify SAM3 is correctly installed

## License

This project follows the SAM3 license. See the main LICENSE file for details.

