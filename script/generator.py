import os
import json
import httpx
import re
from pathlib import Path
from typing import Dict, Optional, List


class ScriptGenerator:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "anthropic/claude-3.5-sonnet:beta"
        self.prompt_template = Path("assets/prompts/prompt.txt").read_text()
        self.language = "Romanian"  # Default language

    async def generate_script(self, subject: str, duration: int) -> Optional[Dict]:
        """Generate a video script using Claude AI"""
        try:
            # Prepare the prompt by replacing placeholders
            prompt = self.prompt_template.replace("<<TOPIC>>", subject)
            prompt = prompt.replace("<<VIDEO LENGTH>>", f"{duration} seconds")
            prompt = prompt.replace(
                "<<IGNORED TOPICS>>", "violence, explicit content, controversial topics"
            )

            # Replace language in prompt template
            prompt = prompt.replace("<<LANGUAGE>>", f"{self.language}")

            # Calculate number of images needed (1 per 5 seconds)
            num_images = duration // 5
            prompt = prompt.replace("<<NUMBER_OF_IMAGES>>", str(num_images))

            # Prepare the API request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a professional video script writer specializing in creating engaging educational content.",
                    },
                    {"role": "user", "content": prompt},
                ],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url, headers=headers, json=data, timeout=60.0
                )

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]

                    try:
                        # Clean the content before parsing JSON
                        # Remove any potential control characters
                        content = "".join(
                            char
                            for char in content
                            if ord(char) >= 32 or char in "\n\r\t"
                        )

                        # Find the start of the JSON content (first '{')
                        json_start = content.find("{")
                        if json_start != -1:
                            content = content[json_start:]

                            # Find the end of the JSON content (last '}')
                            json_end = content.rfind("}")
                            if json_end != -1:
                                content = content[: json_end + 1]

                        # Replace newlines in youtube_description with \n
                        content = re.sub(
                            r'("youtube_description":\s*")(.*?)(")',
                            lambda m: m.group(1)
                            + m.group(2).replace("\n", "\\n")
                            + m.group(3),
                            content,
                            flags=re.DOTALL,
                        )

                        # Fix missing commas between elements
                        content = re.sub(
                            r'"\n"', '",\n"', content
                        )  # Add commas between array elements
                        content = re.sub(
                            r'"\n}', '"\n}', content
                        )  # Don't add comma before closing brace
                        content = re.sub(
                            r'"\n([a-z"])', '",\n\\1', content, flags=re.IGNORECASE
                        )  # Add commas between fields

                        # Parse the cleaned JSON response
                        script_data = json.loads(content)
                        return script_data
                    except json.JSONDecodeError as e:
                        print(f"Error parsing script JSON: {e}")
                        print(f"Content causing error: {content}")
                        return None
                else:
                    print(f"API request failed with status {response.status_code}")
                    return None

        except Exception as e:
            print(f"Error generating script: {e}")
            return None

    def validate_script(self, script_data: Dict) -> bool:
        """Validate the generated script data"""
        required_fields = [
            "title",
            "script",
            "music",
            "sounds",
            "descriptions",
            "youtube_title",
            "youtube_description",
        ]

        # Check if all required fields are present
        if not all(field in script_data for field in required_fields):
            return False

        # Check if we have matching number of scripts and descriptions
        if len(script_data["script"]) != len(script_data["descriptions"]):
            return False

        return True

    @staticmethod
    def get_topic_suggestions(
        category: str, exclude_topics: List[str] = None
    ) -> List[str]:
        """Generate topic suggestions based on category"""
        suggestions = {
            "Istorie românească": [
                "Dacia și civilizația dacică",
                "Formarea primelor state medievale românești",
                "Primul Război Mondial și România",
                "Revoluția de la 1848",
                "România în perioada comunistă",
                "Revoluția din 1989",
            ],
            "Legende și mituri": [
                "Legenda Meșterului Manole",
                "Povestea Babei Dochia",
                "Legenda Vrâncioaiei",
                "Legenda Lacului Roșu",
                "Mitul Zburătorului",
                "Legenda Fetei din Dafin",
            ],
            "Personalități istorice": [
                "Mihai Viteazul și unirea principatelor",
                "Ștefan cel Mare și Moldova medievală",
                "Alexandru Ioan Cuza și reformele sale",
                "Regina Maria în Primul Război Mondial",
                "Vlad Țepeș și domnia sa",
                "Mircea cel Bătrân",
            ],
            "Tradiții și obiceiuri": [
                "Obiceiuri de Crăciun în România",
                "Tradiții de Paște în diferite regiuni",
                "Sânzienele și tradițiile verii",
                "Mărțișorul și venirea primăverii",
                "Călușarii și dansurile tradiționale",
                "Obiceiuri de nuntă tradițională",
            ],
            "Locuri fascinante din România": [
                "Castelul Bran și misterele sale",
                "Delta Dunării și biodiversitatea",
                "Mănăstirile din Bucovina",
                "Sarmizegetusa Regia",
                "Transfăgărășanul",
                "Peștera Scărișoara",
            ],
            "Evenimente istorice importante": [
                "Marea Unire din 1918",
                "Războiul de Independență",
                "Lupta de la Posada",
                "Intrarea României în NATO",
                "Aderarea la Uniunea Europeană",
                "Revoluția din Decembrie 1989",
            ],
            "Povești populare": [
                "Greuceanu și balaurii",
                "Prâslea cel Voinic",
                "Făt-Frumos din lacrimă",
                "Tinerețe fără bătrânețe",
                "Ileana Cosânzeana",
                "Harap Alb",
            ],
            "Artă și cultură românească": [
                "Constantin Brâncuși și opera sa",
                "George Enescu și muzica românească",
                "Nicolae Grigorescu și pictura",
                "Poezia lui Mihai Eminescu",
                "Sculptura lui Ion Jalea",
                "Teatrul românesc interbelic",
            ],
        }

        # Get suggestions for category
        topics = suggestions.get(category, [])

        # Remove already used topics
        if exclude_topics:
            topics = [t for t in topics if t not in exclude_topics]

        return topics
