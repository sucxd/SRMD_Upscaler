import os
import subprocess
from multiprocessing import Pool, cpu_count
import re
from io import BytesIO
import time

# ========== CONFIGURATION PARAMETERS ==========
input_video = 'input.mp4'  # Input video file name
output_video = 'output_upscaled_hevc.mp4'  # Output video file name

# Video parameters
fps = 30  # Frames per second for extraction and assembly
scale_factor = 4  # Scaling factor (e.g., 2 for 2x upscaling, 4 for 4x)
tile_size = 512  # Tile size for processing; adjust based on VRAM
pool_size = min(8, cpu_count())  # Pool size based on CPU count and performance needs

# Upscaling binary configuration
srmd_binary = './srmd-ncnn-vulkan.exe'  # Path to SRMD-NCNN binary

# FFmpeg encoding settings
bitrate = '15M'  # Video bitrate for FFmpeg encoding (e.g., '10M' for 10 Mbps)
ffmpeg_preset = 'fast'  # Preset for FFmpeg encoding ('fast', 'medium', 'slow')
# ========== END OF CONFIGURATION ==========

# Directories for frame handling
upscaled_frames_dir = 'upscaled_frames'
os.makedirs(upscaled_frames_dir, exist_ok=True)

def natural_sort_key(s):
    """Natural sorting function for filenames with numbers."""
    return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', s)]

def upscale_frame(frame_data):
    """Upscale a single frame with SRMD-NCNN."""
    frame_name, frame_bytes = frame_data
    input_path = f'tmp_{frame_name}'  # Temporary filename for SRMD compatibility
    output_path = os.path.join(upscaled_frames_dir, frame_name)

    # Write frame to a temporary file if SRMD requires it to read from disk
    with open(input_path, 'wb') as f:
        f.write(frame_bytes.getbuffer())

    # Run SRMD with GPU acceleration on this frame
    try:
        subprocess.run(
            [srmd_binary, '-i', input_path, '-o', output_path, '-s', str(scale_factor), '-t', str(tile_size)],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        print(f"Upscaled: {frame_name}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to upscale {frame_name}: {e.stderr}")
    finally:
        # Clean up temporary file
        os.remove(input_path)

def extract_frames():
    """Extract frames from the input video and load them into memory as (name, BytesIO) pairs."""
    frame_data = []
    print(f"Extracting frames from video at {fps} fps...")
    try:
        # Extract frames to stdout and capture in memory
        result = subprocess.run(
            ['ffmpeg', '-i', input_video, '-vf', f'fps={fps}', '-f', 'image2pipe', '-vcodec', 'png', '-'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )

        # Parse the stdout into frames
        i = 1
        for chunk in result.stdout.split(b'\x89PNG\r\n\x1a\n'):
            if not chunk:
                continue
            frame_data.append((f"frame_{i:04d}.png", BytesIO(b'\x89PNG\r\n\x1a\n' + chunk)))
            i += 1

        print("Frame extraction complete.")
    except subprocess.CalledProcessError as e:
        print(f"Error during frame extraction: {e.stderr}")
    
    return frame_data

def reassemble_video():
    """Reassemble upscaled frames into the output video at specified fps using H.265 GPU encoding."""
    print(f"Reassembling upscaled frames into video at {fps} fps using H.265 GPU encoding (hevc_nvenc)...")
    start_time = time.time()  # Start timing for reassembly
    try:
        subprocess.run(
            [
                'ffmpeg', '-r', str(fps), '-i', f'{upscaled_frames_dir}/frame_%04d.png',
                '-c:v', 'hevc_nvenc', '-preset', ffmpeg_preset, '-b:v', bitrate, '-pix_fmt', 'yuv420p', output_video
            ],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        print(f"Video reassembly complete! Output saved as {output_video}")
    except subprocess.CalledProcessError as e:
        print(f"Error during video reassembly: {e.stderr}")
    
    # Display reassembly time
    end_time = time.time()
    print(f"Time taken to reassemble video: {end_time - start_time:.2f} seconds")

def cleanup():
    """Clean up temporary frame files and directories."""
    print("Cleaning up temporary files...")
    for file in os.listdir(upscaled_frames_dir):
        os.remove(os.path.join(upscaled_frames_dir, file))
    os.rmdir(upscaled_frames_dir)
    print("Cleanup complete.")

def main():
    # Step 1: Extract frames and load into memory
    frame_data = extract_frames()

    # Step 2: Upscale frames in memory using parallel processing
    print(f"Upscaling frames with SRMD-NCNN in parallel (Tile Size: {tile_size}, Pool Size: {pool_size})...")
    start_upscale_time = time.time()  # Start timing for upscaling
    with Pool(pool_size) as pool:
        pool.map(upscale_frame, frame_data)
    end_upscale_time = time.time()  # End timing for upscaling
    print(f"Time taken to upscale all frames: {end_upscale_time - start_upscale_time:.2f} seconds")

    # Step 3: Reassemble frames into a video
    reassemble_video()

    # Step 4: Cleanup temporary files
    cleanup()

if __name__ == "__main__":
    main()
