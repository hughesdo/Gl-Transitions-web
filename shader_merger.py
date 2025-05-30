import moderngl
import numpy as np
import imageio.v3 as iio
from pathlib import Path
import subprocess
import os
from PIL import Image
import shutil
import tempfile

class ShaderVideoMerger:
    def __init__(self, video1_path, video2_path, shader_path, duration_sec=1.1, output_path="output.mp4", extra_uniforms=None):
        self.video1_path = Path(video1_path)
        self.video2_path = Path(video2_path)
        self.shader_path = Path(shader_path)
        self.duration = duration_sec
        self.output_path = Path(output_path)
        self.frame_rate = 30
        self.resolution = (1280, 720)
        self.ctx = moderngl.create_standalone_context()
        self.extra_uniforms = extra_uniforms or {}

    def get_video_info(self, video_path):
        """Get video frame count and duration using ffprobe"""
        try:
            # Get frame count
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-select_streams", "v:0",
                "-count_frames", "-show_entries", "stream=nb_frames",
                "-of", "csv=p=0", str(video_path)
            ], capture_output=True, text=True, check=True)
            frame_count = int(result.stdout.strip())
            
            # Get frame rate
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-select_streams", "v:0",
                "-show_entries", "stream=r_frame_rate",
                "-of", "csv=p=0", str(video_path)
            ], capture_output=True, text=True, check=True)
            
            fps_str = result.stdout.strip()
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den)
            else:
                fps = float(fps_str)
                
            return frame_count, fps
        except subprocess.CalledProcessError:
            # Fallback to imageio if ffprobe fails
            print("[WARNING] ffprobe failed, using imageio (slower)")
            frames = list(iio.imiter(video_path, plugin="pyav"))
            return len(frames), 30.0  # assume 30fps

    def extract_video_segment(self, video_path, start_frame, frame_count, output_path):
        """Extract specific frames from video using ffmpeg"""
        start_time = start_frame / self.frame_rate
        duration = frame_count / self.frame_rate

        subprocess.run([
            "ffmpeg", "-y", "-i", str(video_path),
            "-ss", str(start_time),
            "-t", str(duration),
            "-vf", f"scale={self.resolution[0]}:{self.resolution[1]}",  # 🔧 Apply scaling
            "-c:v", "libx264", "-crf", "18",
            "-pix_fmt", "yuv420p",
            str(output_path)
        ], check=True)

    def extract_frames_for_transition(self, video_path, start_frame, frame_count):
        """Extract specific frames from video for shader processing"""
        frames = []
        
        # Use ffmpeg to extract frames to temporary directory
        temp_extract_dir = Path(tempfile.mkdtemp(prefix="extract_"))
        
        try:
            start_time = start_frame / self.frame_rate
            duration = frame_count / self.frame_rate
            
            subprocess.run([
                "ffmpeg", "-y", "-i", str(video_path),
                "-ss", str(start_time),
                "-t", str(duration),
                "-vf", f"scale={self.resolution[0]}:{self.resolution[1]}",
                str(temp_extract_dir / "frame_%04d.png")
            ], check=True)
            
            # Load extracted frames
            for i in range(frame_count):
                frame_path = temp_extract_dir / f"frame_{i+1:04d}.png"
                if frame_path.exists():
                    img = Image.open(frame_path)
                    frames.append(np.array(img))
                    
        finally:
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
            
        return frames

    def load_shader(self):
        with open(self.shader_path, 'r') as f:
            frag_shader = f.read()

        vert_shader = """
        #version 330
        in vec2 in_vert;
        out vec2 v_text;
        void main() {
            v_text = in_vert * 0.5 + 0.5;
            gl_Position = vec4(in_vert, 0.0, 1.0);
        }
        """

        prog = self.ctx.program(vertex_shader=vert_shader, fragment_shader=frag_shader)
        return prog

    def run(self):
        print(f"[INFO] Using shader: {self.shader_path}")
        
        # Get video information
        total1, fps1 = self.get_video_info(self.video1_path)
        total2, fps2 = self.get_video_info(self.video2_path)
        
        # Use the frame rate from first video (or average them)
        self.frame_rate = fps1
        transition_frames = int(self.duration * self.frame_rate)
        
        print(f"[INFO] Video1: {total1} frames, Video2: {total2} frames")
        print(f"[INFO] Transition: {transition_frames} frames at {self.frame_rate} fps")

        if total1 < transition_frames or total2 < transition_frames:
            raise ValueError("Transition duration too long for the input videos")

        # Create temporary directory for processing
        temp_dir = Path(tempfile.mkdtemp(prefix="video_merge_"))
        
        try:
            # Step 1: Extract pre-transition segment from video1
            pre_transition_frames = total1 - transition_frames
            if pre_transition_frames > 0:
                print("[INFO] Extracting pre-transition segment...")
                pre_segment_path = temp_dir / "pre_transition.mp4"
                self.extract_video_segment(self.video1_path, 0, pre_transition_frames, pre_segment_path)
            else:
                pre_segment_path = None

            # Step 2: Extract frames needed for transition
            print("[INFO] Extracting transition frames...")
            frames1_for_transition = self.extract_frames_for_transition(
                self.video1_path, total1 - transition_frames, transition_frames
            )
            frames2_for_transition = self.extract_frames_for_transition(
                self.video2_path, 0, transition_frames
            )

            # Step 3: Render transition frames
            print("[INFO] Rendering transition...")
            transition_frames_dir = temp_dir / "transition_frames"
            transition_frames_dir.mkdir(exist_ok=True)
            
            prog = self.load_shader()
            vbo = self.ctx.buffer(np.array([
                -1.0, -1.0,
                 1.0, -1.0,
                -1.0,  1.0,
                -1.0,  1.0,
                 1.0, -1.0,
                 1.0,  1.0,
            ], dtype='f4'))

            vao = self.ctx.simple_vertex_array(prog, vbo, 'in_vert')
            fbo = self.ctx.simple_framebuffer(self.resolution)
            fbo.use()

            for i in range(transition_frames):
                t = i / transition_frames
                f1 = Image.fromarray(frames1_for_transition[i])
                f2 = Image.fromarray(frames2_for_transition[i])

                tex1 = self.ctx.texture(self.resolution, 3, f1.tobytes())
                tex2 = self.ctx.texture(self.resolution, 3, f2.tobytes())
                tex1.use(0)
                tex2.use(1)

                prog['from'].value = 0
                prog['to'].value = 1
                if 'progress' in prog:
                    prog['progress'].value = t

                if 'resolution' in prog:
                    prog['resolution'].value = self.resolution

                for name, val in self.extra_uniforms.items():
                    if name in prog:
                        prog[name].value = val

                vao.render()
                data = fbo.read(components=3)
                img = Image.frombytes('RGB', self.resolution, data)
                img.save(transition_frames_dir / f"frame_{i:04d}.png")

            # Step 4: Convert transition frames to video
            print("[INFO] Encoding transition segment...")
            transition_segment_path = temp_dir / "transition.mp4"
            subprocess.run([
                "ffmpeg", "-y",
                "-framerate", str(self.frame_rate),
                "-i", str(transition_frames_dir / "frame_%04d.png"),
                "-c:v", "libx264", "-crf", "18",
                "-pix_fmt", "yuv420p",
                str(transition_segment_path)
            ], check=True)

            # Step 5: Extract post-transition segment from video2
            post_transition_frames = total2 - transition_frames
            if post_transition_frames > 0:
                print("[INFO] Extracting post-transition segment...")
                post_segment_path = temp_dir / "post_transition.mp4"
                self.extract_video_segment(self.video2_path, transition_frames, post_transition_frames, post_segment_path)
            else:
                post_segment_path = None

            # Step 6: Concatenate all segments
            print("[INFO] Concatenating final video...")
            concat_list_path = temp_dir / "concat_list.txt"
            
            with open(concat_list_path, 'w') as f:
                if pre_segment_path and pre_segment_path.exists():
                    f.write(f"file '{pre_segment_path.absolute()}'\n")
                f.write(f"file '{transition_segment_path.absolute()}'\n")
                if post_segment_path and post_segment_path.exists():
                    f.write(f"file '{post_segment_path.absolute()}'\n")

            subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_list_path),
                "-c", "copy",
                str(self.output_path)
            ], check=True)

            print(f"[INFO] Merge complete: {self.output_path}")

        finally:
            # Cleanup temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
