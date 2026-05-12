import os
import json
import argparse
from typing import List
from tqdm import tqdm
from PIL import Image
import torch
import torch.multiprocessing as mp
from copy import deepcopy
from diffusers import LongCatImageEditPipeline
import threading
import time
import sys
import queue

sys.path.append("path/")

from EditCompass.config import get_task_config


def read_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def write_json(file_path, data):
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)



class ModelWrapper:
    def __init__(
        self,
        model_path,
        device="cuda",
        seed=42,
        think_mode=False,
        lora_path=None,
    ):
        self.model_name = model_path
        self.device = device
        self.pipeline = LongCatImageEditPipeline.from_pretrained(model_path, torch_dtype=torch.bfloat16)
        print("pipeline loaded")
        self.pipeline.to(self.device)

    def inference(self, source_image:List[str], instruction:str, save_path:str):
        source_image = Image.open(source_image[0]).convert("RGB")
        output_image = self.pipeline(
            source_image,
            instruction,
            negative_prompt='',
            guidance_scale=4.5,
            num_inference_steps=50,
            num_images_per_prompt=1,
            generator=torch.Generator("cpu").manual_seed(43)
        ).images[0]
        self.save_image(output_image, save_path)
    
    def save_image(self, image, save_path):
        image.save(save_path)


def collect_all_tasks(args, task_config):
    """
    收集所有需要处理的任务 - 正确版本
    """
    all_task_data = {}
    
    for task_name, config in task_config.items():
        json_paths = config['json_path']
        save_dir = config['save_dir']
        
        # 跳过Part5
        if 'Part5' in save_dir and not args.support_multi_image:
            print(f"  ⏭️  Skipping {task_name} (requires multi-image support)")
            continue
        
        os.makedirs(save_dir, exist_ok=True)
        
        # 检查已有结果
        final_json_path = os.path.join(save_dir, f"{task_name}.json")
        existing_results = {}
        if os.path.exists(final_json_path):
            try:
                existing_data = read_json(final_json_path)
                for item in existing_data:
                    existing_results[item['save_id']] = item
                print(f"  📂 Task {task_name}: Found {len(existing_results)} existing results")
            except Exception as e:
                print(f"  ⚠️  Failed to load {task_name}: {e}")
        
        all_items = []
        to_process_tasks = []
        
        for src_json_path in json_paths:
            if not os.path.exists(src_json_path):
                print(f"  ⚠️  Source JSON missing: {src_json_path}")
                continue
            
            data = read_json(src_json_path)
            print(f"  📂 Task {task_name}: Loaded {len(data)} items from {os.path.basename(src_json_path)}")
            
            for item in data:
                save_id = item['save_id']
                save_img_name = f'{save_id}.png'
                save_img_path = os.path.join(save_dir, save_img_name)
                
                # ✅ 创建final_item
                if save_id in existing_results:
                    # 使用已有结果(可能有status)
                    final_item = existing_results[save_id].copy()
                    final_item['output_image_path'] = save_img_path
                else:
                    # 使用原始数据(没有status)
                    final_item = item.copy()
                    final_item['output_image_path'] = save_img_path
                
                # ✅ 只在图片存在时设置status
                image_exists = os.path.exists(save_img_path)
                if image_exists:
                    # 图片存在但没有status → 标记为success
                    if 'status' not in final_item:
                        final_item['status'] = 'success'
                
                # 添加到all_items
                current_idx = len(all_items)
                all_items.append(final_item)
                
                # ✅ 跳过已完成的
                if image_exists and not args.overwrite:
                    continue
                
                # 准备推理数据
                if 'Part5' in save_dir:
                    ref_image = item['reference_image_path']
                    ref_image = [os.path.join(args.data_root, img) for img in ref_image]
                    source_image = os.path.join(args.data_root, item['source_image'])
                    source_images = [source_image] + ref_image
                    instruction = item[f'prompt_{args.language}']  
                else:
                    source_images = [os.path.join(args.data_root, item['source_image'])]
                    instruction = item[f'prompt_{args.language}']
                
                to_process_tasks.append((
                    task_name,
                    current_idx,
                    final_item,
                    save_img_path,
                    source_images,
                    instruction
                ))
        
        all_task_data[task_name] = {
            'all_items': all_items,
            'to_process': to_process_tasks,
            'json_path': final_json_path
        }
    
    return all_task_data


def worker_process(rank, gpu_id, task_queue, args, result_queue, error_log_path):
    """
    每个GPU上的worker进程
    """
    try:
        device = f"cuda:{gpu_id}"
        torch.cuda.set_device(gpu_id)
        
        print(f"[Worker {rank}] Loading model on {device}...")
        model = ModelWrapper(
            model_path=args.model_path,
            device=device,
            think_mode=args.think_mode,
            lora_path=args.lora_path,
        )
        print(f"[Worker {rank}] Model loaded on {device}")

        processed = 0
        while True:
            try:
                task_name, idx, item, save_img_path, source_images, instruction = task_queue.get_nowait()
            except queue.Empty:
                break

            try:
                # 运行推理
                model.inference(source_images, instruction, save_img_path)
                
                # 标记成功
                item['status'] = "success"
                
                # 发送保存消息
                result_queue.put(("save", task_name, idx, item))
                
            except Exception as e:
                error_msg = f"[Worker {rank}] [Task:{task_name}] [ID:{item['save_id']}] Error: {str(e)}"
                with open(error_log_path, "a") as ef:
                    ef.write(error_msg + "\n")
                print(f"\n{error_msg}")
                
                item['status'] = "failed"
                item['error'] = str(e)
                
                # 失败也保存
                result_queue.put(("save", task_name, idx, item))

            processed += 1
            if args.worker_log_interval > 0 and processed % args.worker_log_interval == 0:
                print(f"[Worker {rank}] Processed {processed} tasks on GPU:{gpu_id}")
    
    except Exception as e:
        print(f"[Worker {rank}] Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Worker完成后通知主进程
        print(f"\n[Worker {rank}] Finished, sending done signal")
        result_queue.put(("done", rank))


def saver_thread(result_queue, all_task_data, task_config, save_interval, stop_event, progress_callback=None):
    """
    专门负责保存的线程 - 完全修复版
    """
    last_save_time = {task: time.time() for task in all_task_data.keys()}
    pending_updates = {task: 0 for task in all_task_data.keys()}
    completed_workers = 0
    total_workers = None
    total_processed = 0
    
    print(f"💾 Saver thread started (interval: {save_interval}s)")
    
    while True:
        try:
            # 使用 timeout 避免阻塞
            try:
                msg = result_queue.get(timeout=0.5)
            except:
                msg = None
            
            if msg:
                if msg[0] == "save":
                    _, task_name, idx, updated_item = msg
                    # 更新内存
                    all_task_data[task_name]['all_items'][idx] = updated_item
                    pending_updates[task_name] += 1
                    total_processed += 1
                    
                    # 通知主进程更新进度条
                    if progress_callback:
                        progress_callback()
                    
                    # 定期保存
                    if time.time() - last_save_time[task_name] >= save_interval:
                        save_dir = task_config[task_name]['save_dir']
                        final_json_path = os.path.join(save_dir, f"{task_name}.json")
                        write_json(final_json_path, all_task_data[task_name]['all_items'])
                        
                        print(f"\n  💾 [Periodic] Saved {task_name} ({pending_updates[task_name]} updates)")
                        last_save_time[task_name] = time.time()
                        pending_updates[task_name] = 0
                
                elif msg[0] == "done":
                    worker_id = msg[1]
                    completed_workers += 1
                    print(f"\n  ✅ Worker {worker_id} completed ({completed_workers}/{total_workers})")
                    
                elif msg[0] == "init":
                    total_workers = msg[1]
                    print(f"  📊 Total workers: {total_workers}")
            
            # 检查是否所有worker都完成
            if total_workers and completed_workers >= total_workers:
                print(f"\n  🎉 All {total_workers} workers completed")
                break
            
            # 检查stop_event(备用退出机制)
            if stop_event.is_set():
                print(f"\n  ⚠️  Stop event received")
                break
                
        except Exception as e:
            print(f"\n⚠️  Saver error: {e}")
            import traceback
            traceback.print_exc()
    
    # 最终保存所有待保存的数据
    print("\n💾 Final save (all tasks)...")
    for task_name in all_task_data.keys():
        if pending_updates[task_name] > 0:
            save_dir = task_config[task_name]['save_dir']
            final_json_path = os.path.join(save_dir, f"{task_name}.json")
            write_json(final_json_path, all_task_data[task_name]['all_items'])
            print(f"  ✅ Saved {task_name} ({pending_updates[task_name]} pending updates)")
    
    print("💾 Saver thread finished")
    print(f"📊 Total processed: {total_processed}")


def print_statistics(all_task_data):
    """打印统计信息"""
    print("\n" + "="*70)
    print("📊 Final Statistics")
    print("="*70)
    print(f"{'Task Name':<25} | {'Total':>6} | {'Success':>7} | {'Failed':>6} | {'Pending':>7}")
    print("-"*70)
    
    total_sum = {'total': 0, 'success': 0, 'failed': 0, 'pending': 0}
    
    for task_name, data in all_task_data.items():
        items = data['all_items']
        total = len(items)
        success = sum(1 for item in items if item.get('status') == 'success')
        failed = sum(1 for item in items if item.get('status') == 'failed')
        pending = sum(1 for item in items if 'status' not in item)
        
        print(f"{task_name:<25} | {total:>6} | {success:>7} | {failed:>6} | {pending:>7}")
        
        total_sum['total'] += total
        total_sum['success'] += success
        total_sum['failed'] += failed
        total_sum['pending'] += pending
    
    print("-"*70)
    print(f"{'TOTAL':<25} | {total_sum['total']:>6} | {total_sum['success']:>7} | "
          f"{total_sum['failed']:>6} | {total_sum['pending']:>7}")
    print("="*70)


def run_multi_gpu_evaluation(args, task_config):
    """
    多GPU并行推理主函数 - 完全修复版
    """
    if args.gpu_ids:
        gpu_ids = args.gpu_ids
    else:
        gpu_ids = list(range(torch.cuda.device_count()))
    
    num_gpus = len(gpu_ids)
    print(f"🚀 Using {num_gpus} GPUs: {gpu_ids}")
    
    # 收集所有任务
    print("📋 Collecting all tasks...")
    all_task_data = collect_all_tasks(args, task_config)
    
    # 展平任务
    flat_tasks = []
    for task_name, data in all_task_data.items():
        flat_tasks.extend(data['to_process'])
    
    total_tasks = len(flat_tasks)
    total_all = sum(len(data['all_items']) for data in all_task_data.values())
    
    print(f"📊 Total items: {total_all}")
    print(f"   - To process: {total_tasks}")
    print(f"   - Skipped: {total_all - total_tasks}")
    
    if total_tasks == 0:
        print("✅ No tasks to process.")
        # 仍然需要保存 (确保所有item都有正确的status)
        for task_name, data in all_task_data.items():
            save_dir = task_config[task_name]['save_dir']
            final_json_path = os.path.join(save_dir, f"{task_name}.json")
            write_json(final_json_path, data['all_items'])
        print_statistics(all_task_data)
        return
    
    # 启动多进程
    mp.set_start_method('spawn', force=True)
    manager = mp.Manager()
    task_queue = manager.Queue()
    result_queue = manager.Queue()
    error_log_path = os.path.join(args.save_root, f"{args.model_name}_error_log.txt")

    for task in flat_tasks:
        task_queue.put(task)

    print(f"📦 Dynamic task queue initialized with {total_tasks} tasks")
    
    # 创建进度条
    pbar = tqdm(total=total_tasks, desc="Overall Progress", position=num_gpus)
    
    def update_progress():
        """进度条更新回调"""
        pbar.update(1)
    
    # 启动保存线程
    stop_event = threading.Event()
    saver = threading.Thread(
        target=saver_thread,
        args=(result_queue, all_task_data, task_config, args.save_interval, stop_event, update_progress),
        daemon=False
    )
    saver.start()
    
    # 通知saver总worker数
    result_queue.put(("init", num_gpus))
    
    # 启动worker进程
    print("📥 Starting workers...")
    processes = []
    for rank, gpu_id in enumerate(gpu_ids):
        p = mp.Process(
            target=worker_process,
            args=(rank, gpu_id, task_queue, args, result_queue, error_log_path)
        )
        p.start()
        processes.append(p)
    
    # 等待所有进程结束
    print("⏳ Waiting for workers to complete...")
    for i, p in enumerate(processes):
        p.join()
        print(f"  ✅ Worker {i} joined")
    
    # 等待saver线程完成
    print("⏳ Waiting for saver thread...")
    saver.join(timeout=60)
    
    if saver.is_alive():
        print("⚠️  Saver thread timeout, forcing stop...")
        stop_event.set()
        saver.join(timeout=10)
    
    pbar.close()
    
    print("\n🎉 All tasks completed!")
    
    # 打印统计
    print_statistics(all_task_data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="IP2P", help="Model name")
    parser.add_argument("--data_root", type=str, required=True, help="Path to input datasets")
    parser.add_argument("--save_root", type=str, default="OmniBench_EVAL", help="Base path for saving results")
    parser.add_argument("--language", type=str, default="en", help="Language for prompts")
    parser.add_argument("--overwrite", type=bool, default=False, help="Whether to overwrite existing results")
    parser.add_argument('--model_path', type=str, default='', help='Path to the model checkpoint')
    parser.add_argument('--support_multi_image', action='store_true', help='Whether the model supports multi-image input')
    parser.add_argument('--think_mode', action='store_true', help='Whether the model is think model')
    parser.add_argument('--lora_path', type=str, default='', help='Path to the LoRA checkpoint')
    parser.add_argument('--gpu_ids', type=int, nargs='+', default=None, help='List of GPU IDs to use')
    parser.add_argument('--save_interval', type=int, default=1, help='Save JSON every N seconds (default: 30)')
    parser.add_argument('--worker_log_interval', type=int, default=20, help='Print one worker log every N processed tasks')
    
    args = parser.parse_args()
    
    model_save_root = os.path.join(args.save_root, args.model_name, args.language)
    os.makedirs(model_save_root, exist_ok=True)
    args.save_root = model_save_root
    
    task_config = get_task_config(root_dir=args.data_root, save_root=model_save_root)
    
    run_multi_gpu_evaluation(args, task_config)
