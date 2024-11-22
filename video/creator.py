from pathlib import Path
from typing import Optional, Dict, List

from project.project import Project
from script.generator import ScriptGenerator
from image.generator import ImageGenerator
from audio.generator import AudioGenerator
from video.combiner import VideoCombiner

class VideoCreator:
    def __init__(self):
        self.script_generator = ScriptGenerator()
        self.image_generator = ImageGenerator()
        self.audio_generator = AudioGenerator()
        self.video_combiner = VideoCombiner()
        self._last_progress = 0
        self._last_message = ""

    def _update_progress(self, progress_callback, message: str, value: int):
        """Helper to update progress only when there's a change"""
        if progress_callback and (value != self._last_progress or message != self._last_message):
            self._last_progress = value
            self._last_message = message
            progress_callback(message, value)
        
    async def create_video(self, project: Project, progress_callback=None, skip_audio=False) -> bool:
        """Create a complete video from start to finish"""
        try:
            # Calculate video format based on duration
            is_short = project.duration <= 60
            print(f"Creating {'short/vertical' if is_short else 'long/horizontal'} video")

            # Script generation (0-20%)
            self._update_progress(progress_callback, "Generating script...", 0)
            script_data = await self.script_generator.generate_script(project.subject, project.duration)
            if not script_data or not self.script_generator.validate_script(script_data):
                self._update_progress(progress_callback, "Error: Failed to generate or validate script", 0)
                return False
            
            # Update project data (20%)
            self._update_progress(progress_callback, "Updating project data...", 20)
            project.set_title(script_data["title"])
            project.scripts = script_data["script"]
            project.add_metadata("youtube_title", script_data["youtube_title"])
            project.add_metadata("youtube_description", script_data["youtube_description"])
            project.add_metadata("background_music", script_data["music"])
            project.add_metadata("sound_effects", script_data["sounds"])
            project.add_metadata("image_descriptions", script_data["descriptions"])

            # Image generation (20-50%)
            self._update_progress(progress_callback, "Generating images...", 25)
            images, error = await self.image_generator.generate_project_images(
                project.id,
                script_data["descriptions"],
                is_short=is_short  # Pass correct format
            )
            if error:
                self._update_progress(progress_callback, f"Error: {error}", 25)
                return False
            if not images or len(images) != len(script_data["script"]):
                self._update_progress(progress_callback, "Error: Failed to generate all required images", 25)
                return False
            project.images = images
            
            # Audio generation (50-80%)
            if not skip_audio:
                self._update_progress(progress_callback, "Generating voiceover...", 50)
                audio_files = await self.audio_generator.generate_project_audio(
                    project.id,
                    script_data["script"],
                    project.duration
                )
                if not audio_files or len(audio_files) != len(script_data["script"]):
                    self._update_progress(progress_callback, "Error: Failed to generate voiceover", 50)
                    return False
                project.audio_files = audio_files
            else:
                project.audio_files = []
            
            # Final video creation (80-100%)
            self._update_progress(progress_callback, "Creating final video with voiceover...", 80)
            output_path = await self.video_combiner.create_final_video(
                project.id,
                project.images,
                project.audio_files if not skip_audio else [],
                scripts=project.scripts,
                scene_duration=project.duration / len(project.scripts) if project.scripts else 5.0
            )
            if not output_path:
                self._update_progress(progress_callback, "Error: Failed to create final video", 80)
                return False
            
            project.output_path = output_path
            project.update()
            
            self._update_progress(progress_callback, "Video creation complete!", 100)
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error creating video: {error_msg}")
            self._update_progress(progress_callback, f"Error: {error_msg}", 0)
            return False

    async def recreate_video(self, project: Project, progress_callback=None) -> bool:
        """Recreate video using existing project assets"""
        try:
            print(f"Starting video recreation for project {project.id}")
            print(f"Project duration: {project.duration} seconds")
            
            # Calculate scene duration and format
            num_scenes = len(project.scripts)
            scene_duration = project.duration / num_scenes if num_scenes > 0 else 5.0
            is_short = project.duration <= 60
            print(f"Scene duration: {scene_duration} seconds")
            print(f"Video format: {'SHORT/VERTICAL' if is_short else 'LONG/HORIZONTAL'}")

            # Verify all image files exist and regenerate if necessary
            all_images_exist = True
            for img in project.images:
                if not Path(img).exists():
                    all_images_exist = False
                    break

            # Regenerate images if they don't exist
            if not all_images_exist and project.metadata and 'image_descriptions' in project.metadata:
                if progress_callback:
                    progress_callback("Regenerating images...", 25)
                
                images, error = await self.image_generator.generate_project_images(
                    project.id, 
                    project.metadata['image_descriptions'],
                    is_short=is_short  # Pass format based on duration
                )
                if error:
                    if progress_callback:
                        progress_callback(f"Error: {error}", 25)
                    return False
                project.images = images
                project.update()

            # Check and generate missing audio files
            if not project.audio_files or len(project.audio_files) != len(project.scripts):
                if progress_callback:
                    progress_callback("Generating missing audio files...", 25)
                print("Generating missing audio files...")
                
                # Generate audio for scenes that don't have audio
                new_audio_files = []
                for i, script in enumerate(project.scripts):
                    if i >= len(project.audio_files) or not Path(project.audio_files[i]).exists():
                        print(f"Generating audio for scene {i+1}")
                        audio_path = await self.audio_generator.generate_audio(
                            script,
                            Path(f"projects/{project.id}/audio/scene{i+1}-audio.mp3"),
                            is_short=is_short
                        )
                        if audio_path:
                            new_audio_files.append(audio_path)
                        else:
                            print(f"Failed to generate audio for scene {i+1}")
                            if progress_callback:
                                progress_callback(f"Error: Failed to generate audio for scene {i+1}", 0)
                            return False
                    else:
                        new_audio_files.append(project.audio_files[i])
                
                project.audio_files = new_audio_files
                project.update()

            # Update audio processing to match video type
            if project.audio_files:
                if progress_callback:
                    progress_callback("Processing audio files...", 25)
                    
                processed_audio = []
                for audio_file in project.audio_files:
                    processed_path = self.audio_generator.process_audio_silence(
                        audio_file, 
                        is_short=is_short  # Pass correct format
                    )
                    if processed_path:
                        processed_audio.append(processed_path)
                    else:
                        processed_audio.append(audio_file)
                project.audio_files = processed_audio

            # If no images exist but we have descriptions, generate them
            if (not project.images and 
                project.metadata and 
                'image_descriptions' in project.metadata and 
                project.metadata['image_descriptions']):
                
                if progress_callback:
                    progress_callback("Generating missing images...", 25)
                print("Generating missing images from stored descriptions")
                
                images, error = await self.image_generator.generate_project_images(
                    project.id, project.metadata['image_descriptions']
                )
                if error:
                    error_msg = f"Failed to generate images: {error}"
                    print(error_msg)
                    if progress_callback:
                        progress_callback(f"Error: {error_msg}", 25)
                    return False
                    
                project.images = images
                project.update()
                print(f"Generated {len(images)} images")

            if not project.images:
                error_msg = "No images found in project and no image descriptions available"
                print(error_msg)
                if progress_callback:
                    progress_callback(f"Error: {error_msg}", 0)
                return False

            if progress_callback:
                progress_callback("Creating video from assets...", 50)
                
            # Verify all image files exist
            for img in project.images:
                if not Path(img).exists():
                    error_msg = f"Image file not found: {img}"
                    print(error_msg)
                    if progress_callback:
                        progress_callback(f"Error: {error_msg}", 50)
                    return False

            print("All image files verified")
                
            # Combine existing assets into final video with scripts
            output_path = await self.video_combiner.create_final_video(
                project.id, 
                project.images, 
                project.audio_files,
                scene_duration=scene_duration,  # Pass the calculated scene duration
                scripts=project.scripts
            )
            
            if not output_path:
                error_msg = "Failed to create final video"
                print(error_msg)
                if progress_callback:
                    progress_callback(f"Error: {error_msg}", 75)
                return False
            
            print(f"Video created successfully at: {output_path}")
            
            project.output_path = output_path
            project.update()
            
            if progress_callback:
                progress_callback("Video recreation complete!", 100)
                
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error recreating video: {error_msg}")
            if progress_callback:
                progress_callback(f"Error: {error_msg}", 0)
            return False

    async def regenerate_scene(self, project: Project, scene_index: int, progress_callback=None, skip_audio=True) -> bool:
        """Regenerate a specific scene (image and audio) without recreating video"""
        try:
            # Calculate if this is a short video
            is_short = project.duration <= 60
            
            self._update_progress(progress_callback, f"Regenerating scene {scene_index + 1}...", 0)
                
            # Regenerate image with correct format (0-50%)
            self._update_progress(progress_callback, "Generating new image...", 25)
            new_image, error = await self.image_generator.regenerate_image(
                project.id,
                scene_index,
                project.metadata.get("image_descriptions", [])[scene_index],
                is_short=is_short
            )
            if error:
                self._update_progress(progress_callback, f"Error regenerating image: {error}", 0)
                return False
            if new_image:
                project.images[scene_index] = new_image
                
            # Skip audio regeneration if specified (50-100%)
            if not skip_audio:
                self._update_progress(progress_callback, "Generating new audio...", 50)
                new_audio = await self.audio_generator.regenerate_audio(
                    project.id,
                    scene_index,
                    project.scripts[scene_index],
                    project.duration
                )
                if new_audio:
                    project.audio_files[scene_index] = new_audio
            
            # Update project to save changes
            project.update()
            self._update_progress(progress_callback, f"Scene {scene_index + 1} updated successfully!", 100)
            return True
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error regenerating scene: {error_msg}")
            self._update_progress(progress_callback, f"Error: {error_msg}", 0)
            return False
