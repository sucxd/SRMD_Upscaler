import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import threading

class UpscalerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Upscaler GUI")
        
        # Input file selection
        tk.Label(root, text="Input Video File").grid(row=0, column=0, padx=10, pady=10)
        self.input_entry = tk.Entry(root, width=40)
        self.input_entry.grid(row=0, column=1, padx=10, pady=10)
        tk.Button(root, text="Browse", command=self.browse_input_file).grid(row=0, column=2, padx=10, pady=10)

        # Output file selection
        tk.Label(root, text="Output Video File").grid(row=1, column=0, padx=10, pady=10)
        self.output_entry = tk.Entry(root, width=40)
        self.output_entry.grid(row=1, column=1, padx=10, pady=10)
        tk.Button(root, text="Browse", command=self.browse_output_file).grid(row=1, column=2, padx=10, pady=10)

        # FPS setting
        tk.Label(root, text="FPS").grid(row=2, column=0, padx=10, pady=10)
        self.fps_entry = tk.Entry(root, width=10)
        self.fps_entry.insert(0, "25")  # Default value
        self.fps_entry.grid(row=2, column=1, padx=10, pady=10)

        # Scale factor setting
        tk.Label(root, text="Scale Factor").grid(row=3, column=0, padx=10, pady=10)
        self.scale_entry = tk.Entry(root, width=10)
        self.scale_entry.insert(0, "4")  # Default value
        self.scale_entry.grid(row=3, column=1, padx=10, pady=10)

        # Tile size setting
        tk.Label(root, text="Tile Size").grid(row=4, column=0, padx=10, pady=10)
        self.tile_entry = tk.Entry(root, width=10)
        self.tile_entry.insert(0, "768")  # Default value
        self.tile_entry.grid(row=4, column=1, padx=10, pady=10)

        # Bitrate setting
        tk.Label(root, text="Bitrate").grid(row=5, column=0, padx=10, pady=10)
        self.bitrate_entry = tk.Entry(root, width=10)
        self.bitrate_entry.insert(0, "10M")  # Default value
        self.bitrate_entry.grid(row=5, column=1, padx=10, pady=10)

        # FFmpeg preset
        tk.Label(root, text="FFmpeg Preset").grid(row=6, column=0, padx=10, pady=10)
        self.preset_var = tk.StringVar(root)
        self.preset_var.set("medium")  # Default value
        presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
        tk.OptionMenu(root, self.preset_var, *presets).grid(row=6, column=1, padx=10, pady=10)

        # Progress bar
        self.progress_bar = ttk.Progressbar(root, length=300, mode='determinate')
        self.progress_bar.grid(row=7, column=0, columnspan=3, pady=10)

        # Start button
        tk.Button(root, text="Start Upscaling", command=self.start_upscaling_thread).grid(row=8, column=0, columnspan=3, pady=20)

    def browse_input_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mkv *.avi")])
        if filepath:
            self.input_entry.delete(0, tk.END)
            self.input_entry.insert(0, filepath)

    def browse_output_file(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")])
        if filepath:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, filepath)

    def start_upscaling_thread(self):
        """Start the upscaling process in a separate thread to keep the GUI responsive."""
        self.progress_bar['value'] = 0  # Reset progress bar
        upscaling_thread = threading.Thread(target=self.start_upscaling)
        upscaling_thread.start()

    def start_upscaling(self):
        # Get user inputs
        input_file = self.input_entry.get()
        output_file = self.output_entry.get()
        fps = self.fps_entry.get()
        scale = self.scale_entry.get()
        tile = self.tile_entry.get()
        bitrate = self.bitrate_entry.get()
        preset = self.preset_var.get()

        # Validate inputs
        if not input_file or not output_file:
            messagebox.showerror("Error", "Please select input and output files.")
            return
        
        # Command to call the upscaler script with arguments
        command = [
            "python", "upscaler_script.py",  # Replace with the path to your main upscaler script
            "--input", input_file,
            "--output", output_file,
            "--fps", fps,
            "--scale", scale,
            "--tile", tile,
            "--bitrate", bitrate,
            "--preset", preset
        ]

        # Run the upscaler script and update the progress bar
        try:
            total_steps = 3  # Define total steps (frame extraction, upscaling, reassembly)
            for i in range(total_steps):
                self.progress_bar['value'] = ((i + 1) / total_steps) * 100
                self.root.update_idletasks()
                subprocess.run(command, check=True)  # Replace with actual subprocess logic for each step
            
            messagebox.showinfo("Success", "Upscaling completed successfully!")
        except subprocess.CalledProcessError:
            messagebox.showerror("Error", "Upscaling failed. Check the console for details.")

# Run the GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = UpscalerGUI(root)
    root.mainloop()
