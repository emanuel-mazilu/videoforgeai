import subprocess
import shutil
from pathlib import Path
from typing import List, Optional


class VideoCombiner:
    def __init__(self):
        self.font_size = 84
        # Check for available fonts
        possible_fonts = [
            "/System/Library/Fonts/Supplemental/SFCompact-Semibold.otf",      # SF Compact
            "/System/Library/Fonts/Supplemental/HelveticaNeue.ttc",           # Helvetica Neue
            "/System/Library/Fonts/Supplemental/Montserrat-Bold.ttf",         # Montserrat
            "/System/Library/Fonts/Supplemental/OpenSans-Bold.ttf",           # Open Sans
            "/System/Library/Fonts/Helvetica.ttc",                            # Helvetica
            "/System/Library/Fonts/Supplemental/Arial.ttf",                   # Arial (fallback)
        ]

        # Use first available font
        self.font_file = next((f for f in possible_fonts if Path(f).exists()),
                              "/System/Library/Fonts/Supplemental/Arial.ttf")
        # Create assets directory if it doesn't exist
        self.assets_dir = Path("assets")
        self.assets_dir.mkdir(exist_ok=True)

    def escape_text(self, text: str) -> str:
        """Escape special characters for ffmpeg drawtext"""
        # First clean up any smart quotes and special characters
        replacements = {
            """: "'",
            """: "'",
            '"': '"',
            '"': '"',
            "′": "'",
            "″": '"',
            "„": '"',
            "‟": '"',
            "‛": "'",
            "❛": "'",
            "❜": "'",
            "❝": '"',
            "❞": '"',
            "〝": '"',
            "〞": '"',
            "＂": '"',
        }

        for old, new in replacements.items():
            text = text.replace(old, new)

        # Now escape for ffmpeg
        text = text.replace("\\", "\\\\")  # Escape backslashes
        text = text.replace(":", "\\:")     # Escape colons
        text = text.replace("'", "''")      # Double single quotes instead of escaping
        text = text.replace('"', '\\"')     # Escape double quotes

        # Ensure other special characters are properly handled
        text = text.replace("ă", "a")
        text = text.replace("â", "a")
        text = text.replace("î", "i")
        text = text.replace("ș", "s")
        text = text.replace("ț", "t")
        text = text.replace("Ă", "A")
        text = text.replace("Â", "A")
        text = text.replace("Î", "I")
        text = text.replace("Ș", "S")
        text = text.replace("Ț", "T")

        return text

    def split_text_into_lines(self, text: str, max_chars: int = 30) -> List[str]:
        """Split text into shorter, more readable lines"""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            word_length = len(word)
            # Verify if adding the next word exceeds the max_chars limit
            if current_line and (current_length + 1 + word_length > max_chars):
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = word_length
            else:
                current_line.append(word)
                current_length += word_length + (1 if current_line else 0)

        if current_line:
            lines.append(" ".join(current_line))

        # Limit to 2 lines for better balance
        if len(lines) > 2:
            text = " ".join(lines)
            words = text.split()
            mid = len(words) // 2
            lines = [
                " ".join(words[:mid]),
                " ".join(words[mid:])
            ]

        return lines

    def create_video_from_image(
        self,
        image_path: str,
        duration: float,
        output_path: str,
        subtitle: str = "",
        is_short: bool = True,
    ) -> bool:
        """Create a video clip from a single image with subtitle overlay"""
        try:
            print(f"Creating video from image: {image_path}")
            print(f"Output path: {output_path}")
            print(f"Video type: {'short/vertical' if is_short else 'long/horizontal'}")

            if is_short:
                scale_filter = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black"
                text_size = self.font_size - 16
                base_y = "h-250"
                line_spacing = 85
                max_chars = 28
                fade_duration = 0.5
            else:
                # Format landscape (16:9)
                scale_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
                text_size = self.font_size - 16
                base_y = "h-120"
                line_spacing = 75
                max_chars = 42
                fade_duration = 0.4

            # Add subtitle overlay if available
            if subtitle:
                # Split subtitle into two parts
                words = subtitle.split()
                mid_point = len(words) // 2
                first_half = " ".join(words[:mid_point])
                second_half = " ".join(words[mid_point:])

                # Calculate display timings
                half_duration = duration / 2
                fade_time = int(fade_duration * 1000)  # Convert to milliseconds

                # Create drawtext filters for each half with fade effects
                text_filters = []

                # First half of text
                lines1 = self.split_text_into_lines(first_half, max_chars)
                total_height1 = len(lines1) * line_spacing
                start_y1 = int(base_y.replace("h-", ""))

                for i, line in enumerate(reversed(lines1)):
                    y_pos = f"h-{start_y1 + (i*line_spacing)}"
                    escaped_text = self.escape_text(line)

                    filter_text = (
                        f"drawtext=fontfile={self.font_file}"
                        f":text='{escaped_text}'"
                        f":fontsize={text_size}"
                        f":fontcolor=white"
                        f":bordercolor=black@0.9"
                        f":borderw=5"
                        f":shadowcolor=black@0.8"
                        f":shadowx=3:shadowy=3"
                        f":box=1:boxcolor=black@0.4:boxborderw=8"
                        f":x=(w-text_w)/2"
                        f":y={y_pos}"
                        f":alpha='if(lt(t,{fade_duration}),t/{fade_duration},if(lt(t,{half_duration}),1,if(lt(t,{
                            half_duration}+{fade_duration}),({half_duration}+{fade_duration}-t)/{fade_duration},0)))'"
                    )
                    text_filters.append(filter_text)

                # Second half of text
                lines2 = self.split_text_into_lines(second_half, max_chars)
                total_height2 = len(lines2) * line_spacing
                start_y2 = int(base_y.replace("h-", ""))

                for i, line in enumerate(reversed(lines2)):
                    y_pos = f"h-{start_y2 + (i*line_spacing)}"
                    escaped_text = self.escape_text(line)

                    filter_text = (
                        f"drawtext=fontfile={self.font_file}"
                        f":text='{escaped_text}'"
                        f":fontsize={text_size}"
                        f":fontcolor=white"
                        f":bordercolor=black@0.9"
                        f":borderw=5"
                        f":shadowcolor=black@0.8"
                        f":shadowx=3:shadowy=3"
                        f":box=1:boxcolor=black@0.4:boxborderw=8"
                        f":x=(w-text_w)/2"
                        f":y={y_pos}"
                        f":alpha='if(lt(t,{half_duration}),0,if(lt(t,{half_duration}+{fade_duration}),((t-{half_duration})/{fade_duration}),if(lt(t,{
                            duration}),1,if(lt(t,{duration}+{fade_duration}),(({duration}+{fade_duration}-t)/{fade_duration}),0))))'"
                    )
                    text_filters.append(filter_text)

                # Filter all text lines together
                if text_filters:
                    scale_filter = scale_filter + "," + ",".join(text_filters)

            command = [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                image_path,
                "-c:v",
                "libx264",
                "-t",
                str(duration),
                "-pix_fmt",
                "yuv420p",
                "-vf",
                scale_filter,
                "-vsync",
                "cfr",  # Use constant frame rate
                "-r",
                "30",  # Set frame rate to 30fps
                output_path,
            ]

            print(f"Running command: {' '.join(command)}")
            subprocess.run(command, check=True, capture_output=True)
            print("Successfully created video from image")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Error creating video from image: {e}")
            print(f"ffmpeg stderr: {e.stderr.decode()}")
            return False

    def combine_audio_video(
        self, video_path: str, audio_path: str, output_path: str
    ) -> bool:
        """Combine video with its corresponding audio"""
        try:
            print(f"Combining video {video_path} with audio {audio_path}")
            print(f"Output path: {output_path}")

            command = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-i",
                audio_path,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-vsync",
                "cfr",  # Use constant frame rate
                output_path,
            ]

            print(f"Running command: {' '.join(command)}")
            subprocess.run(command, check=True, capture_output=True)
            print("Successfully combined audio and video")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error combining audio and video: {e}")
            print(f"ffmpeg stderr: {e.stderr.decode()}")
            return False

    def concatenate_videos(self, video_clips: List[str], output_path: str) -> bool:
        """Concatenate multiple video clips into a single video with smooth transitions"""
        try:
            print(f"Concatenating {len(video_clips)} video clips")
            print("Video clips to concatenate:")
            for i, clip in enumerate(video_clips):
                print(f"  {i+1}. {clip}")
                if not Path(clip).exists():
                    print(f"Error: Video clip not found: {clip}")
                    return False

            # Create temp directory
            temp_dir = Path(output_path).parent / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Create concat list file
            list_file = temp_dir / "concat.txt"
            with open(list_file, "w") as f:
                for clip in video_clips:
                    f.write(f"file '{Path(clip).absolute()}'\n")

            # Basic concatenation command with crossfade filter
            filter_complex = []

            # Input streams setup
            for i in range(len(video_clips)):
                filter_complex.append(f"[{i}:v][{i}:a]")

            # Add crossfade between clips
            transition_duration = 0.5
            xfade_filters = []

            for i in range(len(video_clips)-1):
                xfade_filters.append(
                    f"[{i}][{i+1}]xfade=transition=fade:duration={transition_duration}"
                )

            if xfade_filters:
                filter_complex.extend(xfade_filters)

            command = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                "-ac", "2",
                output_path
            ]

            print(f"Running command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                return False

            # Clean up
            try:
                list_file.unlink()
                temp_dir.rmdir()
            except:
                pass

            return True

        except Exception as e:
            print(f"Error in concatenate_videos: {str(e)}")
            return False

    def add_background_music(
        self, video_path: str, music_path: str, output_path: str
    ) -> bool:
        """Add background music to video with volume adjustment"""
        try:
            print(f"Adding background music to video: {video_path}")
            print(f"Music file: {music_path}")
            print(f"Output path: {output_path}")

            command = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,  # Input video with original audio
                "-stream_loop",
                "-1",  # Loop the music for entire video duration
                "-i",
                music_path,  # Input music file
                "-filter_complex",
                "[0:a]volume=1.0[a1];"  # Keep original audio at 100%
                "[1:a]volume=0.2[a2];"  # Reduce music volume to 20%
                "[a1][a2]amix=inputs=2:duration=first[aout]",  # Mix both audio streams
                "-map",
                "0:v",  # Take video from first input
                "-map",
                "[aout]",  # Use mixed audio
                "-c:v",
                "copy",  # Copy video codec
                "-c:a",
                "aac",  # Convert audio to AAC
                "-shortest",  # Match shortest duration
                "-vsync",
                "cfr",  # Use constant frame rate
                output_path,
            ]

            print(f"Running command: {' '.join(command)}")
            subprocess.run(command, check=True, capture_output=True)
            print("Successfully added background music")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error adding background music: {e}")
            print(f"ffmpeg stderr: {e.stderr.decode()}")
            return False

    async def create_final_video(
        self,
        project_id: str,
        images: List[str],
        audio_files: List[str],
        scene_duration: float = 5.0,
        scripts: List[str] = None,
    ) -> Optional[str]:
        """Create the final video by combining all components"""
        try:
            print(f"\nStarting video creation for project {project_id}")
            print(f"Number of images: {len(images)}")
            print(f"Number of audio files: {len(audio_files)}")

            project_dir = Path(f"projects/{project_id}")
            temp_dir = project_dir / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Calculate format based on total expected duration
            total_duration = len(images) * scene_duration
            is_short = total_duration <= 60

            # Get actual audio durations for all scenes
            scene_durations = []
            if audio_files:
                duration_command = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1"
                ]

                for audio_file in audio_files:
                    try:
                        result = subprocess.run(
                            duration_command + [audio_file],
                            capture_output=True,
                            text=True,
                            check=True
                        )
                        duration = float(result.stdout.strip())
                        scene_durations.append(duration)
                    except:
                        scene_durations.append(scene_duration)
            else:
                scene_durations = [scene_duration] * len(images)

            # Create video clips
            video_clips = []
            for i, image_path in enumerate(images):
                print(f"\nProcessing image {i+1}/{len(images)}: {image_path}")

                # Use exact audio duration for scene length
                current_duration = scene_durations[i] if i < len(
                    scene_durations) else scene_duration

                # Get subtitle if available
                subtitle = scripts[i] if scripts and i < len(scripts) else ""

                # Create video from image with exact audio duration
                temp_video = temp_dir / f"temp_video_{i}.mp4"
                if not self.create_video_from_image(
                    image_path,
                    current_duration,
                    str(temp_video),
                    subtitle,
                    is_short
                ):
                    print(f"Failed to create video from image {i}")
                    return None

                # Combine with audio if available
                if audio_files and i < len(audio_files):
                    temp_video_audio = temp_dir / f"temp_video_audio_{i}.mp4"
                    if not self.combine_audio_video(
                        str(temp_video),
                        audio_files[i],
                        str(temp_video_audio)
                    ):
                        print(f"Failed to combine audio for video {i}")
                        return None
                    video_clips.append(str(temp_video_audio))
                else:
                    video_clips.append(str(temp_video))

            if not video_clips:
                print("No video clips were created")
                return None

            print(f"\nCreated {len(video_clips)} video clips")

            # Concatenate all clips directly
            temp_output = project_dir / "temp" / "temp_output.mp4"
            if not self.concatenate_videos(video_clips, str(temp_output)):
                print("Failed to concatenate videos")
                return None

            # Check if we need to adjust video speed
            duration_command = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(temp_output),
            ]

            duration_result = subprocess.run(
                duration_command, capture_output=True, text=True
            )
            if duration_result.returncode == 0:
                duration = float(duration_result.stdout.strip())
                speed_adjusted_output = project_dir / "temp" / "speed_adjusted.mp4"

                # Apply speed adjustment only for short videos
                if is_short and duration > 59.5:
                    speed = duration / 59.5

                    speed_command = [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(temp_output),
                        "-filter_complex",
                        f"[0:v]setpts={1/speed}*PTS[v];[0:a]atempo={speed}[a]",
                        "-map",
                        "[v]",
                        "-map",
                        "[a]",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "medium",
                        "-crf",
                        "23",
                        "-vsync",
                        "cfr",
                        "-r",
                        "30",
                        "-g",
                        "30",
                        "-c:a",
                        "aac",
                        "-b:a",
                        "192k",
                        "-ar",
                        "44100",
                        "-ac",
                        "2",
                        str(speed_adjusted_output),
                    ]

                    print("Adjusting video speed to fit 59.5 seconds...")
                    speed_result = subprocess.run(
                        speed_command, capture_output=True, text=True
                    )
                    if speed_result.returncode == 0:
                        temp_output = speed_adjusted_output
                else:
                    print("Skipping speed adjustment for long video")

            # Add background music if exists
            final_output = project_dir / "output.mp4"
            # Check for soundtrack in multiple locations
            possible_soundtrack_paths = [
                Path("assets/soundtrack.mp3"),
                Path("soundtrack.mp3"),
                self.assets_dir / "soundtrack.mp3",
            ]

            soundtrack_path = next(
                (p for p in possible_soundtrack_paths if p.exists()), None
            )

            if soundtrack_path:
                print(f"Using soundtrack from: {soundtrack_path}")
                if not self.add_background_music(
                    str(temp_output), str(soundtrack_path), str(final_output)
                ):
                    print("Failed to add background music, using video without music")
                    shutil.copy(str(temp_output), str(final_output))
            else:
                print("No soundtrack found, using video without music")
                shutil.copy(str(temp_output), str(final_output))

            print("\nCleaning up temporary files")
            # Clean up temporary files
            for file in temp_dir.glob("*"):
                try:
                    file.unlink()
                    print(f"Deleted: {file}")
                except Exception as e:
                    print(f"Warning: Could not delete temporary file {file}: {e}")
            try:
                temp_dir.rmdir()
                print("Deleted temp directory")
            except Exception as e:
                print(f"Warning: Could not delete temporary directory: {e}")

            print(f"Successfully created final video: {final_output}")
            return str(final_output)

        except Exception as e:
            print(f"Error creating final video: {e}")
            return None
