
import moderngl
import numpy as np
import imageio.v3 as iio
from pathlib import Path
import subprocess
import os
from PIL import Image
import shutil

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

    def read_videos(self):
        self.frames1 = list(iio.imiter(self.video1_path, plugin="pyav"))
        self.frames2 = list(iio.imiter(self.video2_path, plugin="pyav"))

    def run(self):
        print(f"[INFO] Using shader: {self.shader_path}")
        self.read_videos()
        total1 = len(self.frames1)
        total2 = len(self.frames2)
        transition_frames = int(self.duration * self.frame_rate)

        if total1 < transition_frames or total2 < transition_frames:
            raise ValueError("Transition duration too long for the input videos")

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

        temp_dir = Path("temp_frames")
        temp_dir.mkdir(exist_ok=True)

        frame_idx = 0

        # 1. Pre-transition part from video1
        for frame in self.frames1[: total1 - transition_frames]:
            img = Image.fromarray(frame).resize(self.resolution)
            img.save(temp_dir / f"frame_{frame_idx:04d}.png")
            frame_idx += 1

        # 2. Transition blend
        for i in range(transition_frames):
            t = i / transition_frames
            f1 = Image.fromarray(self.frames1[total1 - transition_frames + i]).resize(self.resolution)
            f2 = Image.fromarray(self.frames2[i]).resize(self.resolution)

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
            img.save(temp_dir / f"frame_{frame_idx:04d}.png")
            frame_idx += 1

        # 3. Post-transition part from video2
        for frame in self.frames2[transition_frames:]:
            img = Image.fromarray(frame).resize(self.resolution)
            img.save(temp_dir / f"frame_{frame_idx:04d}.png")
            frame_idx += 1

        self.encode_frames(temp_dir)

    def encode_frames(self, frame_dir):
        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", str(self.frame_rate),
            "-i", str(frame_dir / "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            str(self.output_path)
        ])
        shutil.rmtree(frame_dir)
