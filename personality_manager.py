# personality_manager.py
import os
import glob
import json

class PersonalityManager:
    def __init__(self, directory="my-personality"):
        self.directory = directory

    def load_personality(self):
        """
        Reads all .txt files in the personality directory and combines them into one string.
        """
        personality_parts = []
        for file_path in glob.glob(os.path.join(self.directory, "*.txt")):
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read().strip()
                    file_name = os.path.basename(file_path).rsplit(".", 1)[0].replace("-", " ")
                    personality_parts.append(f"{file_name}: {content}")
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
        return " ".join(personality_parts)

    def get_filenames(self):
        """
        Returns a list of filenames (without extension) in the personality directory.
        """
        return [
            os.path.splitext(os.path.basename(file_path))[0]
            for file_path in glob.glob(os.path.join(self.directory, "*.txt"))
        ]

    def check_and_summarize_files(self, client):
        """
        Checks if any personality file is too large and, if so, asks the OpenAI API to summarize it.
        """
        for file_path in glob.glob(os.path.join(self.directory, "*.txt")):
            try:
                if os.path.getsize(file_path) > 500:  # If file exceeds 500 bytes
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()

                    system_prompt = (
                        "You are a helpful assistant. Summarize the following text into a more concise version: "
                    )
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": content}
                            ]
                        )
                        summarized_content = response.choices[0].message.content.strip()
                        print(summarized_content)

                        # Write the summarized content back to the file
                        with open(file_path, "w", encoding="utf-8") as file:
                            file.write(summarized_content)
                        print(f"Summarized content for {file_path}")
                    except Exception as e:
                        print(f"Error summarizing file {file_path}: {e}")
            except Exception as e:
                print(f"Error checking file size for {file_path}: {e}")

    def update_personality_files(self, chat_history_string, client):
        """
        Uses the chat history to update personality files.
        """
        filenames = self.get_filenames()
        filename_list_str = ", ".join(f'"{filename}"' for filename in filenames)
        system_prompt = (
            f"Categorize the following chat history string into a JSON object. "
            f"Keys should be one of the following categories: {filename_list_str}. "
            f"The values should be the related text. Example format: "
            f'{{"my-hobbies": "painting", "my-mood": "happy"}}.'
        )

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": chat_history_string}
                ]
            )
            print("Raw API Response:", response)  # Debug
            content = response.choices[0].message.content.strip()
            print("API Content:", content)  # Debug

            categorized_content = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return
        except Exception as e:
            print(f"Error during API call or parsing response: {e}")
            return

        for category, text in categorized_content.items():
            file_path = os.path.join(self.directory, f"{category}.txt")
            try:
                with open(file_path, "a", encoding="utf-8") as file:
                    file.write(f"\n{text.strip()}")
                    print(f"Updated personality module: {category}.txt successfully.")
            except Exception as e:
                print(f"Error writing to file {file_path}: {e}")

        self.check_and_summarize_files(client)

    def clean_personality(self, client, batch_size=5):
        """
        Processes personality files in batches and summarizes them to remove redundancy.
        """
        filenames = self.get_filenames()
        
        # Process files in batches
        for i in range(0, len(filenames), batch_size):
            batch = filenames[i:i + batch_size]
            file_data = []

            for filename in batch:
                file_name = filename + ".txt"
                file_path = os.path.join(self.directory, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as file:
                        file_contents = file.read().strip()
                    if not file_contents:
                        print(f"Skipping empty file: {file_name}")
                        continue
                    file_data.append(f"### {file_name}\n{file_contents}")
                except Exception as e:
                    print(f"Error reading file {file_name}: {e}")
            
            if not file_data:
                continue

            batch_input = "\n\n".join(file_data)
            system_prompt = (
                "You are a helpful assistant. You will be provided with multiple lists of personality attributes, each labeled with a filename. "
                "Your task is to summarize each list separately while keeping the core meaning intact.\n\n"
                "**Instructions:**\n"
                "- Remove duplicates and redundant phrases.\n"
                "- Group similar interests together under broader categories (e.g., 'Movies & TV', 'Hobbies', 'Languages & Learning').\n"
                "- Maintain readability and keep the summaries concise.\n"
                "- Return each summary under the same filename header.\n\n"
                "**Example Output:**\n"
                "### file1.txt\n"
                "- **Movies & TV:** Loves films, especially *Inception*. Enjoys Netflix.\n"
                "- **Hobbies:** Enjoys dancing and golfing.\n\n"
                "### file2.txt\n"
                "- **Creative Arts:** Likes drawing landscapes.\n"
                "- **Languages & Learning:** Speaks basic Chinese and German.\n\n"
                "Now, summarize the following lists:\n\n"
                f"{batch_input}"
            )

            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": batch_input}
                    ]
                )
                summarized_text = response.choices[0].message.content.strip()
                summaries = summarized_text.split("### ")
                for summary in summaries:
                    if not summary.strip():
                        continue
                    lines = summary.split("\n", 1)
                    if len(lines) < 2:
                        continue
                    filename = lines[0].strip()
                    content = lines[1].strip()
                    file_path = os.path.join(self.directory, filename)
                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(content)
                    print(f"Successfully summarized: {filename}")
            except Exception as e:
                print(f"Error processing batch {i // batch_size + 1}: {e}")

    def update_from_response(self, response_text: str, client):
        """
        Uses the ChatGPT API to analyze the chatbot's response text and extract personality updates dynamically.
        It only extracts self-descriptive statements about the chatbot's personality. Any mention of the user's
        preferences is ignored.
        
        The personality attributes to consider are determined dynamically based on the files in the personality directory.
        """
        # Dynamically get the personality keys from the files in the directory.
        personality_keys = self.get_filenames()  # e.g., ['what-i-like', 'how-i-feel', 'my-hobbies', ...]
        keys_string = ", ".join([f"'{key}'" for key in personality_keys])

        system_prompt = (
            "You are a personality extraction assistant. Analyze the following chatbot response (written in the first person) "
            "and extract any updates to the chatbot's own personality attributes. "
            f"The personality attributes to consider are: {keys_string}. "
            "IMPORTANT: Only extract information that the chatbot is explicitly describing about itself. "
            "Do not extract or update any information that refers to the user's preferences or opinions. "
            "For example, if the chatbot states 'I love Interstellar', that should be extracted under the appropriate attribute "
            "(e.g., 'what-i-like'). If the chatbot says something like 'Contact is a fantastic choice, Rob!', ignore that part. "
            "Return a valid JSON object containing only the keys that have new updates for the chatbot's personality. "
            "Do not include any extra explanation."
        )

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": response_text}
                ]
            )
            content = response.choices[0].message.content.strip()
            updates = json.loads(content)
        except Exception as e:
            print(f"Error extracting personality updates: {e}")
            return

        # Update each corresponding personality file with the new information
        for key, text in updates.items():
            file_path = os.path.join(self.directory, f"{key}.txt")
            try:
                with open(file_path, "a", encoding="utf-8") as file:
                    file.write(f"\n{text.strip()}")
                    print(f"Updated personality module: {key}.txt with text: {text.strip()}")
            except Exception as e:
                print(f"Error writing to file {file_path}: {e}")

        # Update each corresponding personality file with the new information
        for key, text in updates.items():
            file_path = os.path.join(self.directory, f"{key}.txt")
            try:
                with open(file_path, "a", encoding="utf-8") as file:
                    file.write(f"\n{text.strip()}")
                    print(f"Updated personality module: {key}.txt with text: {text.strip()}")
            except Exception as e:
                print(f"Error writing to file {file_path}: {e}")