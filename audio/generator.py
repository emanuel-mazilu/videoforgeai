import os
import httpx
import subprocess
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import QSettings


class AudioGenerator:
    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.api_url = "https://api.elevenlabs.io/v1"

        # Get voice ID from settings or use default
        settings = QSettings("CloudePython", "AIVideoCreator")
        self.voice_id = settings.value("elevenlabs_voice_id", "Nhs6IYoAcBwjSVy82OUS")

        # Check if ffmpeg is available
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            print("Found ffmpeg")
            self.ffmpeg_available = True
        except:
            print("ffmpeg not found")
            self.ffmpeg_available = False

    def process_audio_silence(
        self, audio_path: str, is_short: bool = False
    ) -> Optional[str]:
        """Process audio file to remove excess silence"""
        if not self.ffmpeg_available or not is_short:
            return audio_path

        try:
            audio_path = Path(audio_path)
            output_dir = audio_path.parent / "edited"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{audio_path.stem}_silenced.mp3"

            silence_filter = (
                "silenceremove="
                "stop_periods=-1:"
                "stop_duration=0.3:"
                "stop_threshold=-35dB:"
                "start_periods=-1:"
                "start_duration=0.3:"
                "start_threshold=-35dB:"
                "keep_silence=0.1"
            )

            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(audio_path),
                "-af",
                silence_filter,
                "-ac",
                "2",
                str(output_path),
            ]

            print(f"Processing audio: {audio_path}")
            print(f"Using silence filter: {silence_filter}")

            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode == 0 and output_path.exists():
                return str(output_path)
            return str(audio_path)

        except Exception as e:
            print(f"Error processing audio silence: {e}")
            return str(audio_path)

    async def generate_audio(
        self, text: str, output_path: Path, is_short: bool = False
    ) -> Optional[str]:
        """Generate audio for a single piece of text"""
        try:
            headers = {
                "Accept": "audio/mpeg",
                "xi-api-key": self.api_key,
                "Content-Type": "application/json",
            }

            data = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.5,
                    "use_speaker_boost": True,
                },
            }

            url = f"{self.api_url}/text-to-speech/{self.voice_id}"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, json=data, timeout=60.0
                )

                if response.status_code == 200:
                    # Create output directory if it doesn't exist
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    # Save the raw audio file
                    with open(output_path, "wb") as f:
                        f.write(response.content)

                    # Process the audio to remove silences (only for short videos)
                    processed_path = self.process_audio_silence(
                        str(output_path), is_short
                    )
                    if processed_path:
                        return processed_path

                    # Return original if processing fails
                    return str(output_path)
                else:
                    print(f"Audio generation failed with status {response.status_code}")
                    return None

        except Exception as e:
            print(f"Error generating audio: {e}")
            return None

    async def generate_project_audio(
        self, project_id: str, scripts: List[str], duration: int = 0
    ) -> List[str]:
        """Generate audio for all scripts in a project"""
        generated_audio = []
        is_short = duration <= 60  # Check if the video is short

        for i, script in enumerate(scripts):
            output_path = Path(f"projects/{project_id}/audio/scene{i+1}-audio.mp3")

            # Generate audio for the script
            audio_path = await self.generate_audio(script, output_path, is_short=False)

            if audio_path:
                # Apply silence processing for short videos
                if is_short:
                    processed_path = self.process_audio_silence(
                        audio_path, is_short=True
                    )
                    if processed_path:
                        generated_audio.append(processed_path)
                    else:
                        generated_audio.append(audio_path)
                else:
                    # For long videos, return the original audio
                    generated_audio.append(audio_path)
            else:
                print(f"Failed to generate audio for scene {i+1}")

        return generated_audio

    async def regenerate_audio(
        self, project_id: str, audio_index: int, script: str, duration: int = 0
    ) -> Optional[str]:
        """Regenerate audio for a specific scene"""
        try:
            is_short = duration <= 60
            print(f"Regenerating audio for {'short' if is_short else 'long'} video")

            output_path = Path(
                f"projects/{project_id}/audio/scene{audio_index+1}-audio.mp3"
            )

            # Generate audio for the script
            audio_path = await self.generate_audio(script, output_path, is_short=False)
            if not audio_path:
                return None

            # Process the audio to remove silences for short videos
            if is_short:
                processed_path = self.process_audio_silence(audio_path, is_short=True)
                if processed_path:
                    print(f"Audio processed successfully: {processed_path}")
                    return processed_path

            # For long videos, return the original audio
            return audio_path

        except Exception as e:
            print(f"Error in regenerate_audio: {e}")
            return None

    async def generate_sound_effect(
        self, effect_name: str, project_id: str, index: int
    ) -> Optional[str]:
        """Generate a sound effect"""
        output_path = Path(f"projects/{project_id}/audio/sound_effect_{index}.mp3")

        # Here we would typically use a sound effect library or AI service
        # For now, we'll just return None as this would require additional setup
        return None
