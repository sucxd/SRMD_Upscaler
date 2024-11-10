import os
import subprocess
from multiprocessing import Pool, cpu_count
import re
from io import BytesIO
from PIL import Image

# Configuration Parameters
input_video = 'input.mp4'  # Input video file name
output_video = 'output_upscaled.mp4'  # Output video file name
fps = 25  # Frames per second for extraction and assembly
scale_factor = 2  # Scaling factor (e.g., 2 for 2x upscaling, 4 for 4x)
tile_size = 512  # Tile size for processing, adjust based on VRAM
pool_size = min(6, cpu_count())  # Dynamic pool size based on CPU count
srmd_binary = './srmd-ncnn-vulkan.exe'  # Path to SRMD-NCNN binary

# Directories for frame handling
frames_dir = 'frames'
upscaled_frames_dir = 'upscaled_frames'

def natural_sort_key(s):
    """Natural sorting function for filenames with numbers."""
    return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', s)]

def upscale_frame(frame_data):
    """Upscale a single frame in memory with SRMD-NCNN."""
    frame_name, frame_bytes = frame_data
    output_path = os.path.join(upscaled_frames_dir, frame_name)
    
    with open(f'{frames_dir}/{frame_name}', 'wb') as f:  # Temporarily save for SRMD binary
        f.write(frame_bytes.getbuffer())

    # Run SRMD on the saved frame and output the result to upscaled directory
    try:
        subprocess.run(
            [srmd_binary, '-i', f'{frames_dir}/{frame_name}', '-o', output_path, '-s', str(scale_factor), '-t', str(tile_size)],
            check=True, capture_output=True, text=True
        )
        print(f"Upscaled: {frame_name}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to upscale {frame_name}: {e.stderr}")
    
    # Cleanup temporary saved frame
    os.remove(f'{frames_dir}/{frame_name}')

def extract_frames():
    """Extract frames from the input video and load them into memory as (name, BytesIO) pairs."""
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(upscaled_frames_dir, exist_ok=True)
    frame_data = []

    print(f"Extracting frames from video at {fps} fps...")
    try:
        # Use FFmpeg to extract frames directly
        result = subprocess.run(
            ['ffmpeg', '-i', input_video, '-vf', f'fps={fps}', f'{frames_dir}/frame_%04d.png'],
            check=True, capture_output=True, text=True
        )
        print("Frame extraction complete.")
        
        # Load frames into memory as BytesIO objects
        for frame_name in sorted(os.listdir(frames_dir), key=natural_sort_key):
            with open(os.path.join(frames_dir, frame_name), 'rb') as f:
                frame_data.append((frame_name, BytesIO(f.read())))
        
        # Clear temporary disk frames
        for frame_name in os.listdir(frames_dir):
            os.remove(os.path.join(frames_dir, frame_name))

    except subprocess.CalledProcessError as e:
        print(f"Error during frame extraction: {e.stderr}")
    
    return frame_data

def reassemble_video():
    """Reassemble upscaled frames into the output video at specified fps using GPU acceleration."""
    print(f"Reassembling upscaled frames into video at {fps} fps using GPU encoding...")
    try:
        subprocess.run(
            [
                'ffmpeg', '-r', str(fps), '-i', f'{upscaled_frames_dir}/frame_%04d.png',
                '-c:v', 'h264_nvenc', '-preset', 'fast', '-pix_fmt', 'yuv420p', output_video
            ],
            check=True, capture_output=True, text=True
        )
        print(f"Video reassembly complete! Output saved as {output_video}")
    except subprocess.CalledProcessError as e:
        print(f"Error during video reassembly: {e.stderr}")

def cleanup():
    """Clean up temporary frame files and directories."""
    print("Cleaning up temporary files...")
    for folder in [frames_dir, upscaled_frames_dir]:
        for file in os.listdir(folder):
            os.remove(os.path.join(folder, file))
        os.rmdir(folder)
    print("Cleanup complete.")

def main():
    # Step 1: Extract frames and load into memory
    frame_data = extract_frames()

    # Step 2: Upscale frames in memory using parallel processing
    print(f"Upscaling frames with SRMD-NCNN in parallel (Tile Size: {tile_size}, Pool Size: {pool_size})...")
    with Pool(pool_size) as pool:
        pool.map(upscale_frame, frame_data)

    # Step 3: Reassemble frames into a video
    reassemble_video()

    # Step 4: Cleanup temporary files
    cleanup()

if __name__ == "__main__":
    main()
