import openai
import base64
from openai import OpenAI
import json
from tqdm import tqdm
import os
import ast
import io
from typing import List
from google import genai
from PIL import Image
 

class EVALWrapper_Model:
    def __init__(self, model_name, api_key=None,api_base=None, temperature=0.0):
        self.api_key = api_key
        self.api_base = api_base
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
        self.temperature = temperature
        self.model_name = model_name
    
    def encode_image(self, path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"

    def create_message(self, text, image_urls):
        text_splits = text.split("<image>")
        
        assert len(text_splits) == len(image_urls) + 1

        content_parts = []
        
        content_parts.append({
            "type": "text",
            "text": text_splits[0]
        })
        for t, im in zip(text_splits[1:], image_urls):
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": im
                }
            })
            content_parts.append({
                "type": "text", 
                "text": t 
            })

        # 2. Construct messages
        messages = [
            {
                "role": "user",
                "content": content_parts
            }
        ]
        return messages
    def get_answer(self, prompt, image_list):
        #  Ecoder image and create message
        image_list = [self.encode_image(img) for img in image_list]
        messages = self.create_message(prompt, image_list) 
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages, 
            temperature=self.temperature
        )
        return response.choices[0].message.content
    def parse_stage(self, text: str) -> str:
        import re
        pattern = r"### RESULT ###\s*(\[.*?\])"
        
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1)
        else:
            return ""
    def inference(self, images_input:List[str], instruction:str, Edit_Image: str, pure_image: str = None, system_prompt: str = "", Metric = "", first_stage_sys="",hints="") -> str:
        input_images = images_input
        if Metric == "VQ":
            return self.get_answer(prompt=system_prompt, image_list=[Edit_Image])
        elif Metric == 'URC':
            first_stage_prompt = first_stage_sys + "<image> <image>"
            if pure_image is not None:
                first_stage_compare_images = [pure_image, Edit_Image]
            else:
                first_stage_compare_images = [input_images[0], Edit_Image]
                
            first_stage_response = self.get_answer(prompt=first_stage_prompt, image_list=first_stage_compare_images)
            image_difference = self.parse_stage(first_stage_response)

            if pure_image is not None:
                prompt = f"""
                1. Source Image: <image>,
                2. Annotated Instruction(with visual markers): <image>,
                3. Edited Image: <image>.
                4. Image Difference between Source Image and Edited Image: {image_difference}.
                """
                if hints != "":
                    prompt += f"5. Hints: {hints}."
                input_images = [pure_image, input_images[0], Edit_Image]
            elif len(input_images) == 1:
                prompt = f"""
                1. Edit Instruction: {instruction},
                2. Source Image: <image>.
                3. Edited Image: <image>,
                4. Image Difference between Source Image and Edited Image: {image_difference}.   
                """
                if hints != "":
                    prompt += f"5. Hints: {hints}."
                input_images.append(Edit_Image)
            else:
                 prompt = f"""
                    1. Edit Instruction: {instruction},
                    2. Source Image: <image>,
                    3. Edited Image: <image>,
                    4. Reference Images: <image>{', <image>' * (len(input_images) - 2)}, 
                    5. Image Difference between Source Image and Edited Image: {image_difference}.
            """
                 if hints != "":
                    prompt += f"6. Hints: {hints}."
                 input_images = [input_images[0], Edit_Image, *input_images[1:]]
            
            prompt = system_prompt + prompt
            response = self.get_answer(prompt=prompt, image_list=input_images)
            return response

        if pure_image is not None:
            input_images = [pure_image, Edit_Image, input_images[0]]
            prompt = """
                1. Source Image: <image>,
                2. Edited Image: <image>,
                3. Annotated Instruction(with visual markers): <image>.
            """
            prompt = system_prompt + prompt
            response = self.get_answer(prompt=prompt, image_list=input_images)
        elif len(input_images) == 1:
            prompt = f"""
                1. Edit Instruction: {instruction},
                2. Source Image: <image>,
                3. Edited Image: <image>.
                """
            if hints != "":
                prompt += f"4. Hints: {hints}."
            input_images.append(Edit_Image)
            prompt = system_prompt + prompt
            response = self.get_answer(prompt=prompt, image_list=input_images)
        else:
            prompt = f"""
            1. Edit Instruction: {instruction},
            2. Source Image: <image>.
            3. Reference Images: <image>{', <image>' * (len(input_images) - 2)},
            4. Edited Image: <image>.
            """
            input_images.append(Edit_Image)
            prompt = system_prompt + prompt
            response = self.get_answer(prompt=prompt, image_list=input_images)
        return response

    
# --- 使用示例 ---
if __name__ == "__main__":
    model = EVALWrapper_Model(model_name=" ",api_key=" ", api_base="")
    image = ["Image_Path"]
    instruction = "<image> Could you please describe what is shown in the image?"
    response = model.get_answer(prompt=instruction, image_list=image)
    print("Model Response:", response)