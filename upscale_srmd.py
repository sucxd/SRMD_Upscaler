import os
import subprocess
from multiprocessing import Pool
import re

# Configurable parameters
input_video = 'input.mp4'  # Replace with your video file name here
output_video = 'output_upscaled_4x.mp4'
frames_dir = 'frames'
upscaled_frames_dir = 'upscaled_frames'
srmd_binary = './srmd-ncnn-vulkan.exe'  # Path to SRMD-NCNN binary

# Adjustable settings for parallelization, VRAM management, and fps
tile_size = 512  # Start with 512; increase to 768 if VRAM allows
pool_size = 4  # Limit parallel processes based on GPU and CPU usage
fps = 25  # Frames per second, easily adjustable for different video frame rates

def natural_sort_key(s):
    """Natural sorting function for filenames with numbers."""
    return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', s)]

def upscale_frame(frame):
    """Upscale a single frame with SRMD-NCNN using the specified scaling and tile size."""
    frame_path = os.path.join(frames_dir, frame)
    output_path = os.path.join(upscaled_frames_dir, frame)
    try:
        result = subprocess.run(
            [srmd_binary, '-i', frame_path, '-o', output_path, '-s', '4', '-t', str(tile_size)], 
            check=True, capture_output=True, text=True
        )
        print(f"Upscaled: {frame} | {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to upscale {frame}: {e.stderr}")

def extract_frames():
    """Extract frames from the input video at the specified fps."""
    os.makedirs(frames_dir, exist_ok=True)
    print(f"Extracting frames from video at {fps} fps...")
    try:
        subprocess.run(
            ['ffmpeg', '-i', input_video, '-vf', f'fps={fps}', f'{frames_dir}/frame_%04d.png'], 
            check=True, capture_output=True, text=True
        )
        print("Frame extraction complete.")
    except subprocess.CalledProcessError as e:
        print(f"Error during frame extraction: {e.stderr}")

def reassemble_video():
    """Reassemble upscaled frames into a final video at the specified fps using GPU acceleration."""
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
    # Step 1: Extract frames
    extract_frames()

    # Step 2: Prepare output directory and get sorted list of frames
    os.makedirs(upscaled_frames_dir, exist_ok=True)
    all_frames = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')], key=natural_sort_key)

    # Step 3: Run SRMD-NCNN in parallel on each frame with limited pool size
    print(f"Upscaling frames with SRMD-NCNN in parallel (Tile Size: {tile_size}, Pool Size: {pool_size})...")
    with Pool(pool_size) as pool:
        pool.map(upscale_frame, all_frames)

    # Step 4: Reassemble frames into a video
    reassemble_video()

    # Step 5: Cleanup temporary files
    cleanup()

if __name__ == "__main__":
    main()
