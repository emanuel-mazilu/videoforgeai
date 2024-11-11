import os
import httpx
from pathlib import Path
from typing import Optional, List, Tuple

class ImageGenerator:
    def __init__(self):
        self.api_key = os.getenv("STABILITY_API_KEY")
        self.api_url = "https://api.stability.ai/v2beta/stable-image/generate/core"

    async def generate_image(self, prompt: str, output_path: Path) -> Tuple[Optional[str], Optional[str]]:
        """Generate a single image using Stability AI"""
        try:
            if not self.api_key:
                return None, "Stability API key not found. Please check your .env file."

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "image/*"
            }

            # Verificăm dacă prompt-ul conține indicații despre format
            is_vertical = "vertical" in prompt.lower()
            is_horizontal = "horizontal" in prompt.lower()
            
            # Setăm aspect ratio bazat pe format
            aspect_ratio = "9:16" if is_vertical else "16:9" if is_horizontal else "16:9"

            data = {
                "prompt": prompt,
                "output_format": "webp",
                "aspect_ratio": aspect_ratio,
                "style_preset": "cinematic"  # Optional: add style preset for better results
            }

            # Convert data to multipart/form-data format
            files = {
                "prompt": (None, data["prompt"]),
                "output_format": (None, data["output_format"]),
                "aspect_ratio": (None, data["aspect_ratio"]),
                "style_preset": (None, data["style_preset"])
            }

            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        self.api_url,
                        headers=headers,
                        files=files,  # Use files parameter for multipart/form-data
                        timeout=60.0
                    )
                except httpx.TimeoutException:
                    return None, "Request timed out while generating image"
                except httpx.RequestError as e:
                    return None, f"Network error while generating image: {str(e)}"

                if response.status_code == 200:
                    try:
                        # Create output directory if it doesn't exist
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Save the image
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                            
                        return str(output_path), None
                    except Exception as e:
                        return None, f"Error saving generated image: {str(e)}"
                elif response.status_code == 401:
                    return None, "Invalid API key. Please check your Stability API key."
                elif response.status_code == 429:
                    return None, "Rate limit exceeded. Please try again later."
                else:
                    error_msg = f"Image generation failed with status {response.status_code}"
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict) and "message" in error_data:
                            error_msg += f": {error_data['message']}"
                    except:
                        pass
                    return None, error_msg

        except Exception as e:
            return None, f"Unexpected error generating image: {str(e)}"

    async def generate_project_images(self, project_id: str, descriptions: List[str], is_short: bool = True) -> Tuple[List[str], Optional[str]]:
        """Generate all images for a project"""
        generated_images = []
        
        # Define aspect ratio based on video type
        aspect_ratio = "9:16" if is_short else "16:9"
        orientation = "vertical" if is_short else "horizontal"
        print(f"Generating images in {aspect_ratio} format ({orientation})")
        
        for i, description in enumerate(descriptions):
            output_path = Path(f"projects/{project_id}/images/scene{i+1}-image.webp")
            
            # Add style, quality and aspect ratio prompts to the description
            enhanced_prompt = (
                f"{description}, cinematic, dramatic lighting, photorealistic, "
                f"{aspect_ratio} aspect ratio, {orientation} format, "
                "high quality"
            )
            
            image_path, error = await self.generate_image(enhanced_prompt, output_path)
            if image_path:
                generated_images.append(image_path)
            else:
                return [], f"Failed to generate image {i+1}: {error}"
                
        return generated_images, None

    async def regenerate_image(self, project_id: str, image_index: int, description: str, is_short: bool = True) -> Tuple[Optional[str], Optional[str]]:
        """Regenerate a specific image"""
        output_path = Path(f"projects/{project_id}/images/scene{image_index+1}-image.webp")
        
        # Define aspect ratio and orientation based on video type
        aspect_ratio = "9:16" if is_short else "16:9"
        orientation = "vertical" if is_short else "horizontal"
        
        enhanced_prompt = (
            f"{description}, cinematic, dramatic lighting, photorealistic, "
            f"{aspect_ratio} aspect ratio, {orientation} format, "
            "high quality"
        )
        
        return await self.generate_image(enhanced_prompt, output_path)
