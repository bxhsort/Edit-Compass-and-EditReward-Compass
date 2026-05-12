import os
import json
import argparse
from typing import List
from tqdm import tqdm
from PIL import Image
import os
import json
import re
import math
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import sys

sys.path.append("path/EditCompass")  # 将上级目录添加到 sys.path，以便导入 config 和 model 模块
from EditCompass.config import get_task_config
from EditCompass.model import EVALWrapper_Model
 

def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def write_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def parse(response: str) -> dict | None:
    if not response:
        return None
    try:
        return json.loads(response.strip())
    except Exception:
        pass
    cleaned = re.sub(r"```(?:json)?\s*", "", response).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", cleaned)
    if m:
        s = re.sub(r",\s*([\]}])", r"\1", m.group())
        try:
            return json.loads(s)
        except Exception:
            pass
    return None

def EVAL_Single_Metric(args, current_metric, task_config, GPT_Model):
     
    overall_task_metrics = {}
     
    data_lock = threading.Lock()
    
    for task_name, config in task_config.items():
        save_dir = config['save_dir']
        save_json_eval_path = os.path.join(save_dir, f"{task_name}_{current_metric}.json")
        if 'Part5' in save_dir and not args.support_multi_image:
            continue  
      
        json_files = os.path.join(save_dir, f"{task_name}.json")
        data = read_json(json_files) 
        
       
        # --- Resume 逻辑 ---
        save_data = []
        cumulative_score = 0
        processed_images = set()  
        Metric_dict = {
            "IC": "Identity_Consistency",
            "IF": "Instrcution_Following",
            "VQ": "Visual_Quality",
            "URC":"Unedited_Region_Consistency",
            "WA":"World_Awareness"
        }        
        if os.path.exists(save_json_eval_path):
            existing_data = read_json(save_json_eval_path)
            existing_data = [x for x in existing_data if x[current_metric] == True]   
            
            
            save_data = [d for d in existing_data if d.get(f'eval_{current_metric}_status') == 'Success' ]
            processed_images = {d['save_id'] for d in save_data}
            cumulative_score = sum(int(item[Metric_dict[current_metric]].get('score', 0)) for item in save_data)
            print(f"🔄 Resuming {task_name}: {len(save_data)} items already processed.")

         
        remaining_data = [item for item in data if item['save_id'] not in processed_images and item[current_metric] == True]
        print('length of remaining_data:', len(remaining_data))
        
        if not remaining_data:
            print(f"✅ Task {task_name} already fully evaluated.")
            overall_task_metrics[task_name] = cumulative_score / len(save_data) if save_data else 0
            continue

        print(f"\n🚀 Processing Task: {task_name} with {args.num_workers} threads. Remaining: {len(remaining_data)}")
        
        # 进度条显示
        pbar = tqdm(total=len(data), initial=len(save_data), desc=f"  Evaluating {task_name}", dynamic_ncols=True, colour="green")


        # --- 定义线程执行的 worker 函数 ---
        def worker(item):
            nonlocal cumulative_score
            current_response = None
            parsed_res = None
            system_prompt_key = f'{current_metric}_System_Prompt'
            hints = item.get('hints', '')
            if current_metric == "URC":
                from Prompt.Unedited_Region_Consistency import first_stage_prompt
            else:
                first_stage_prompt = ""
            try: 
                if 'Part5' in save_dir:
                    prompt = item[f'prompt_{args.language}_2']
                    ref_paths = [os.path.join(args.data_root, img) for img in item['reference_image_path']]
                    src_path = os.path.join(args.data_root, item['source_image'])
                    imgs = [src_path] + ref_paths
                    if not os.path.exists(edited_path): return
                    System_prompt = task_config[task_name][system_prompt_key][0]
                    current_response = GPT_Model.inference(images_input=imgs, instruction=prompt, Edit_Image=edited_path, system_prompt=System_prompt, Metric=current_metric,hints=hints)
                    parsed_res = parse(current_response)

                elif 'Part6' in save_dir and 'Complex' in save_dir and item.get('edit_type', '') != "Complex_paint":
                    prompt = item[f'prompt_{args.language}']
                    src_path = os.path.join(args.data_root, item['source_image'])
                    System_prompt = task_config[task_name][system_prompt_key][1]
                    current_response = GPT_Model.inference(images_input=[src_path], instruction=prompt, Edit_Image=edited_path, system_prompt=System_prompt, Metric=current_metric,hints=hints)
                    parsed_res = parse(current_response)
                    
                elif item.get('edit_type', '') == "Complex_paint":
                    prompt = item[f'prompt_{args.language}']
                    pure_suffix = 'CN' if ('sub_type' in item and item['sub_type'] == 'Complex_paint_cn') else 'EN'
                    pure_image = item['source_image'].replace(pure_suffix, 'image')
                    src_path = os.path.join(args.data_root, item['source_image'])
                    pure_path = os.path.join(args.data_root, pure_image)
                    System_prompt = task_config[task_name][system_prompt_key][0]
                    current_response = GPT_Model.inference(images_input=[src_path], instruction=prompt, Edit_Image=edited_path, pure_image=pure_path, system_prompt=System_prompt, Metric=current_metric,hints=hints)
                    parsed_res = parse(current_response)
                else:
                    prompt = item[f'prompt_{args.language}']
                    src_path = os.path.join(args.data_root, item['source_image'])
                    System_prompt = task_config[task_name][system_prompt_key][0]
                    current_response = GPT_Model.inference(images_input=[src_path], instruction=prompt, Edit_Image=edited_path, system_prompt=System_prompt,first_stage_sys=first_stage_prompt, Metric=current_metric,hints=hints)
                    parsed_res = parse(current_response)   
                    

                 
                if parsed_res and isinstance(parsed_res, dict) and 'score' in parsed_res:
                    with data_lock:
                        item[f'eval_{current_metric}_status'] = 'Success'
                        item[Metric_dict[current_metric]] = parsed_res
                        save_data.append(item)
                        cumulative_score += parsed_res['score']
                        pbar.set_postfix({'Task_Avg': f"{cumulative_score / len(save_data):.2f}"})
                        write_json(save_json_eval_path, save_data)
                
            except Exception as e:
                print(f"❌ Error during inference/parsing for item with source_image {item['source_image']}: {e}")
                
            finally:
                pbar.update(1)

         
        with ThreadPoolExecutor(max_workers=args.num_workers) as executor:
            executor.map(worker, remaining_data)

         
        write_json(save_json_eval_path, save_data)
        print('length of save_data:', len(save_data))
        task_final_avg = cumulative_score / len(save_data) if save_data else 0
        overall_task_metrics[task_name] = task_final_avg
        pbar.close()

     
    summary_path = os.path.join(args.save_root, f"overall_{current_metric}.json")
    write_json(summary_path, overall_task_metrics)
    print(f"📊 All tasks completed. Overall scores saved to {summary_path}")


def get_metric_components(metric):
    if metric == 'IF':
        from Prompt.Instruction_Following import Single_image_prompt, Multi_image_prompt, Complex_Instructions_Prompt, Complex_painting_prompt
    elif metric == 'IC':
        from Prompt.Identify_Consistecy import Single_image_prompt, Multi_image_prompt, Complex_Instructions_Prompt, Complex_painting_prompt
    elif metric == 'WA':
        from Prompt.World_Knowledge_Aware import Single_image_prompt, Multi_image_prompt, Complex_Instructions_Prompt, Complex_painting_prompt
    elif metric == 'URC':
        from Prompt.Unedited_Region_Consistency import Single_image_prompt, Multi_image_prompt, Complex_Instructions_Prompt, Complex_painting_prompt
    elif metric == 'VQ':
        from Prompt.Visual_Quality import Single_image_prompt, Multi_image_prompt, Complex_Instructions_Prompt, Complex_painting_prompt
    else:
        raise ValueError(f"Unknown metric: {metric}")
    
    return {
        'Single_image_prompt': Single_image_prompt,
        'Multi_image_prompt': Multi_image_prompt,
        'Complex_Instructions_Prompt': Complex_Instructions_Prompt,
        'Complex_painting_prompt': Complex_painting_prompt
    }
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_root", type=str, required=True, help="Path to input datasets")
    parser.add_argument("--save_root", type=str, default="OmniBench_EVAL", help="Base path for saving results")
    parser.add_argument("--language", type=str, default="en", help="Language for prompts")
    parser.add_argument('--support_multi_image',action='store_true', help='Whether the model supports multi-image input')
    parser.add_argument("--num_workers", type=int, default=8, help="并发线程数，建议根据 API 配额设置 2-8")
    parser.add_argument("--api_key", type=str, default="", help="API Key for GPT models")
    parser.add_argument("--api_base", type=str, default="", help="API Base URL for GPT models")
    parser.add_argument("--Metric", type=str, nargs='+', default=["IF"], 
                        choices=['IF', 'IC', 'WA', 'URC', 'VQ'], 
                        help="Evaluation Metric(s). You can specify multiple metrics separated by space, e.g., --Metric IF IC WA")

    args = parser.parse_args()
    data_root = args.data_root
    args.save_root = os.path.join(args.save_root, f"{args.language}")
    save_root = args.save_root


    for metric in args.Metric:
        print(f"✅ Currently testing metric: {metric}")
        components = get_metric_components(metric)
        task_config = get_task_config(data_root, save_root)

        for task_name, config in task_config.items():
            save_dir = config['save_dir']
            if 'Part5' in save_dir:
                task_config[task_name][f'{metric}_System_Prompt'] = [components['Multi_image_prompt']]
            elif 'Part6' in save_dir and 'Complex' in save_dir:
                task_config[task_name][f'{metric}_System_Prompt'] = [components['Complex_painting_prompt'], 
                                                                     components['Complex_Instructions_Prompt']]
            else:
                task_config[task_name][f'{metric}_System_Prompt'] = [components['Single_image_prompt']]

        model_name = "gemini-3.1-pro-preview"
        Model = EVALWrapper_Model(model_name=model_name, api_key=args.api_key, api_base=args.api_base)
        EVAL_Single_Metric(args, metric, task_config, Model)
        
    print("All metrics have been evaluated. Please check the saved JSON files for results.")