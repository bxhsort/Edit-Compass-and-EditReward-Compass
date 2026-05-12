import json
import argparse
import os
import re
from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
import torch
from tqdm import tqdm


def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def write_json(file_path, data):
    output_dir = os.path.dirname(file_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)





class Reward_Model:
    def __init__(self, model_path, temperature=0.7, top_k=20, top_p=0.8, max_tokens=128):
        if not model_path:
            raise ValueError("model_path is required to load the reward model.")


        self.model_path = model_path
        self.temperature = temperature
        self.top_k = top_k
        self.top_p = top_p
        self.max_tokens = max_tokens
        

        self.processor = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            model_path,
            dtype="auto",
            device_map="auto",
            trust_remote_code=True,
        )
        self.model.eval()

    def _build_messages(self, source_image, prompt, candidate_image):

        system_prompt = "" + prompt
        return [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": source_image},
                    {"type": "image", "image": candidate_image},
                    {"type": "text", "text": system_prompt},
                ],
            }
        ]


    def inference(self, source_image, prompt, candidate_image):
        messages = self._build_messages(source_image, prompt, candidate_image)
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.model.device)

        generate_kwargs = {
            "max_new_tokens": self.max_tokens,
            "do_sample": self.temperature > 0,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
        }

        with torch.inference_mode():
            generated_ids = self.model.generate(**inputs, **generate_kwargs)

        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self.processor.batch_decode(
            generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0].strip()

        return output_text


def evaluate_dimension(model, data, eval_dim):
    dim_data = [item for item in data if item["dimension"] == eval_dim]
    correct = 0

    for item in tqdm(dim_data, desc=f"Evaluating {eval_dim}", colour='green'):
        source_image = item['source_image']
        prompt = item['prompt']
        winner = item['winner']
        loser = item['loser']
        label = item['label']

        winner_response = model.inference(source_image, prompt, winner)
        loser_response = model.inference(source_image, prompt, loser)

        if label == 'preference' and winner_response['score'] > loser_response['score']:
            correct += 1
        elif label == 'tie' and abs(winner_response['score'] - loser_response['score']) < 1e-5:
            correct += 1

    total = len(dim_data)
    return {
        'accuracy': correct / total if total else 0,
        'total': total,
        'correct': correct
    }


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source_json', type=str, required=True, help='Path to the source JSON file containing evaluation data.')
    parser.add_argument('--output_json', type=str, required=True, help='Path to save the output JSON file with scores.')
    parser.add_argument('--model_path', type=str, default='Qwen/Qwen3-VL-8B-Instruct', help='Path to the reward model checkpoint')
    parser.add_argument('--dim', type=str, nargs='+', default=['IA', 'VC', 'VQ'], help='Dimensions to evaluate (e.g., IA VC VQ)')
    parser.add_argument('--temperature', type=float, default=0.7, help='Temperature for evaluation (if applicable)')
    parser.add_argument('--top_k', type=int, default=20, help='Top-k for evaluation (if applicable)')
    parser.add_argument('--top_p', type=float, default=0.8, help='Top-p for evaluation (if applicable)')
    parser.add_argument('--max_tokens', type=int, default=4096, help='Maximum tokens for evaluation (if applicable)')
    return parser.parse_args()


def main():
    args = parse_args()
    data = read_json(args.source_json)
    model = Reward_Model(
        args.model_path,
        temperature=args.temperature,
        top_k=args.top_k,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
    )

    accuracy_results = {
        eval_dim: evaluate_dimension(model, data, eval_dim)
        for eval_dim in args.dim
    }

    write_json(args.output_json, accuracy_results)

    for eval_dim, result in accuracy_results.items():
        print(
            f"Dimension: {eval_dim}, "
            f"Accuracy: {result['accuracy']:.4f} "
            f"({result['correct']}/{result['total']})"
        )


if __name__ == "__main__":
    main()
