import json
import os
import re
import argparse
import sys

sys.path.append("/Users/baixuehai/Downloads/EditCompass/")

from EditCompass.config import get_task_config



def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


def write_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)



def Get_Score(IA_List, VC_List, VQ_List, Part, task_name):
    '''
    Calculate the score for a given part based on the provided lists.
    Role:
      min_score = Min(IA_List, VQ_List, VQ_List )
      if min_score <= 1:
        overall = min_score
      else:
         Style_Transfer:  overall = IF ** 0.7 * VQ ** 0.3
         General, Dynamic Manipulation, Multi-Image: Complex overall = IF ** 0.4 * VC ** 0.4 * VQ ** 0.2
         World Knowledge Reasoning: overall = IF ** 0.5 * VC ** 0.3 * VQ ** 0.2
         Algorithm Visual Reasoning: overall = IF ** 0.6 * VC ** 0.2 * VQ ** 0.2

    '''
    if task_name != 'Style_Transfer' and not VC_List:
        return None

    scores = IA_List + VQ_List if task_name == 'Style_Transfer' else IA_List + VC_List + VQ_List
    assert scores, "Score lists must not all be empty."

    min_score = min(scores)
    if min_score <= 1:
        return min_score

    avg = lambda x: sum(x) / len(x)
    weights = {
        'Style_Transfer': (0.7, 0, 0.3),
        'Part1': (0.4, 0.4, 0.2),
        'Part2': (0.4, 0.4, 0.2),
        'Part3': (0.5, 0.3, 0.2),
        'Part4': (0.6, 0.2, 0.2),
        'Part5': (0.4, 0.4, 0.2),
        'Part6': (0.4, 0.4, 0.2),
    }
    key = 'Style_Transfer' if task_name == 'Style_Transfer' else Part
    assert key in weights, f"Invalid Part: {Part}"

    if_w, vc_w, vq_w = weights[key]
    return avg(IA_List) ** if_w * (avg(VC_List) ** vc_w if vc_w else 1) * avg(VQ_List) ** vq_w


def summarize_language(args, language):
    language_save_dir = os.path.join(args.save_dir, language)
    config = get_task_config(root_dir=args.source_dir, save_root=language_save_dir)

    ## now paper
    Metric_sets = ['IF', 'WA', 'URC', 'IC', 'VQ']
    Mertic_dict = {
        "IC": "Identity_Consistency",
        "IF": "Instrcution_Following",
        "VQ": "Visual_Quality",
        "URC":"Unedited_Region_Consistency",
        "WA":"World_Awareness"
    }   

    results_dict = {}
    for task_name in config:
        save_dir = config[task_name]['save_dir']
        part_name = os.path.relpath(save_dir, language_save_dir).split(os.sep)[0]
        if part_name not in args.summary_Part:
            continue
        # 1. task_name 需要 那些Metirc
        data_metric_dict = {}

        task_overall_sum = 0
        task_overall_count = 0


        # find should be evaluated metric for each task
        # 默认 -1 这种状态是没有填充的。

        data = []
        for json_apth in config[task_name]['json_path']:
            print(f"Reading data from {json_apth} for task {task_name}...")
            data.extend(read_json(json_apth))
        for item in data:
            item_save_id = item['save_id']
            if item_save_id not in data_metric_dict:
                data_metric_dict[item_save_id] = {}
            for m in Metric_sets:
                if item[m] == True:
                    data_metric_dict[item_save_id][m] = -1

        for m in Metric_sets:
            sub_dim_path = os.path.join(save_dir, f'{task_name}_{m}.json')
            if not os.path.exists(sub_dim_path):
                print(f"Warning: Sub-dimension file {sub_dim_path} does not exist for task {task_name} and metric {m}. Skipping this metric.")
                continue

            sub_dim_data = read_json(sub_dim_path)

            for item in sub_dim_data:
                item_save_id = item['save_id']
                if item_save_id not in data_metric_dict:
                    data_metric_dict[item_save_id] = {}
                data_metric_dict[item_save_id][m] = item[Mertic_dict[m]]['score']
        
        # 2. 计算每个task的score
        for save_id in data_metric_dict:
            item = data_metric_dict[save_id]
            ok = True
            IA_List, VC_List, VQ_List = [], [], []
            for m in item:
                if item[m] == -1:
                    # print(f"Warning: Missing score for {task_name} - {save_id} - {m}")
                    item[m] = None
                    ok = False
                else:
                    if m == 'IF' or m == 'WA':
                        IA_List.append(item[m])
                    elif m == 'VC' or m == 'IC':
                        VC_List.append(item[m])
                    elif m == 'VQ':
                        VQ_List.append(item[m])
            if ok:
                print(f"Calculating score for {task_name} - {save_id} with IF: {IA_List}, VC: {VC_List}, VQ: {VQ_List}")
                item_overall = Get_Score(IA_List, VC_List, VQ_List, Part=part_name, task_name=task_name)
                task_overall_count += 1
                task_overall_sum += item_overall
        
        results_dict[task_name] = {
            'overall': task_overall_sum / task_overall_count if task_overall_count > 0 else None,
            'eval_count': task_overall_count,
            'eval_overall_sum': task_overall_sum,
            'total_count': len(data)
        }
    for task_name in results_dict:
        overall = results_dict[task_name]['overall']
        overall_text = f"{overall:.2f}" if overall is not None else "N/A"
        print(f"[{language}] Task: {task_name}, Overall Score: {overall_text}, Evaluated: {results_dict[task_name]['eval_count']}/{results_dict[task_name]['total_count']}")

    write_json(os.path.join(language_save_dir, "summary.json"), results_dict)
    return results_dict


# Paramaters
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_dir", type=str, default="/Users/baixuehai/Downloads/EditCompass_json", help="Root directory for input JSON files.")
    parser.add_argument('--save_dir', type=str, default="/Users/baixuehai/Downloads/RM_EVAL/EditCompass_Main_Results/Edit-R1-Qwen-Image-Edit-2509", help="Directory containing language result folders.")
    parser.add_argument('--summary_Part', type=str, nargs='+', default=['Part1', 'Part2', 'Part3', 'Part4', 'Part5', 'Part6'], help='Parts to summarize (e.g., Part1 Part2)')
    parser.add_argument('--support_language', type=str, nargs='+', default=['en'], help='Languages to summarize (e.g., en cn)')
    args = parser.parse_args()

    for language in args.support_language:
        summarize_language(args, language)



            





