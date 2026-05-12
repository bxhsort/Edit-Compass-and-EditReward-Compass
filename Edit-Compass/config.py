
import os

def get_task_config(root_dir, save_root):
    return {
        # ---- Part1 General Tasks
        "ADD": {
            "json_path": [f"{root_dir}/Part1/ADD/ADD.json"],
            "save_dir": os.path.join(save_root, "Part1/ADD")
        },
        "Remove": {
            "json_path": [f"{root_dir}/Part1/Remove/Remove.json"],
            "save_dir": os.path.join(save_root, "Part1/Remove")
        },
        "Replace": {
            "json_path": [f"{root_dir}/Part1/Replace/Replace.json"],
            "save_dir": os.path.join(save_root, "Part1/Replace")
        },
        "Change_color_size": {
            "json_path": [f"{root_dir}/Part1/Change_color_size/Change_color_size.json"],
            "save_dir": os.path.join(save_root, "Part1/Change_color_size")
        },
        "Style_Transfer": {
            "json_path": [f"{root_dir}/Part1/Style_Transfer/Style_Transfer.json"],
            "save_dir": os.path.join(save_root, "Part1/Style_Transfer")
        },
        "Extract": {
            "json_path": [f"{root_dir}/Part1/Extract/Extract.json"],
            "save_dir": os.path.join(save_root, "Part1/Extract")
        },
        "Change_Material": {
            "json_path": [f"{root_dir}/Part1/Change_Material/Change_Material.json"],
            "save_dir": os.path.join(save_root, "Part1/Change_Material")
        },
        "Change_Background": {
            "json_path": [f"{root_dir}/Part1/Change_Background/Change_Background.json"],
            "save_dir": os.path.join(save_root, "Part1/Change_Background")
        },
        "Visual_Text_CN": {
            "json_path": [f"{root_dir}/Part1/Visual_Text_CN/Visual_Text_CN.json"],
            "save_dir": os.path.join(save_root, "Part1/Visual_Text_CN")
        },
        "Visual_Text_EN": {
            "json_path": [f"{root_dir}/Part1/Visual_Text_EN/Visual_Text_EN.json"],
            "save_dir": os.path.join(save_root, "Part1/Visual_Text_EN")
        },
        # ----
        # ---- Part2 Dynamic Manipulation Tasks
        "Action": {
            "json_path": [f"{root_dir}/Part2/Action/Action.json"],
            "save_dir": os.path.join(save_root, "Part2/Action")
        },
        "Move": {
            "json_path": [f"{root_dir}/Part2/Move/Move.json"],
            "save_dir": os.path.join(save_root, "Part2/Move")
        },
        "Swap": {
            "json_path": [f"{root_dir}/Part2/Swap/Swap.json"],
            "save_dir": os.path.join(save_root, "Part2/Swap")
        },
        "Object_Interaction": {
            "json_path": [f"{root_dir}/Part2/Object_Interaction/Object_Interaction.json"],
            "save_dir": os.path.join(save_root, "Part2/Object_Interaction")
        },
        "Emotion_Change": {
            "json_path": [f"{root_dir}/Part2/Emotion_Change/Emotion_Change.json"],
            "save_dir": os.path.join(save_root, "Part2/Emotion_Change")
        },
        # ----
        # ---- Part3 World Knowledge Reasoning
        "Casual": {
            "json_path": [f"{root_dir}/Part3/Casual/Casual.json"],
            "save_dir": os.path.join(save_root, "Part3/Casual")
        },
        "Temporal": {
            "json_path": [f"{root_dir}/Part3/Temporal/Temporal.json"],
            "save_dir": os.path.join(save_root, "Part3/Temporal")
        },
        "Chemical": {
            "json_path": [f"{root_dir}/Part3/Chemical/Chemical.json"],
            "save_dir": os.path.join(save_root, "Part3/Chemical")
        },
        "Math": {
            "json_path": [f"{root_dir}/Part3/Math/Math.json"],
            "save_dir": os.path.join(save_root, "Part3/Math") 
        },
        "Game": {
            "json_path": [f"{root_dir}/Part3/Game/Game.json"],
            "save_dir": os.path.join(save_root, "Part3/Game")
        },
        # ---- 
        # ---- Part4 Algorithm Visual Reasoning
        "Knapsack": {
            "json_path": [f"{root_dir}/Part4/Knapsack/Knapsack.json"],
            "save_dir": os.path.join(save_root, "Part4/Knapsack")
        },
        "Convex_Hull": {
            "json_path": [f"{root_dir}/Part4/Convex_Hull/Convex_Hull.json"],
            "save_dir": os.path.join(save_root, "Part4/Convex_Hull")
        },
        "Maximum_Submatrix": {
            "json_path": [f"{root_dir}/Part4/Maximum_Submatrix/Maximum_Submatrix.json"],
            "save_dir": os.path.join(save_root, "Part4/Maximum_Submatrix")
        },
        "Global_Longest_Word": {
            "json_path": [f"{root_dir}/Part4/Global_Longest_Word/Global_Longest_Word.json"],
            "save_dir": os.path.join(save_root, "Part4/Global_Longest_Word")
        },
        "Longest_Word": {
            "json_path": [f"{root_dir}/Part4/Longest_Word/Longest_Word.json"],
            "save_dir": os.path.join(save_root, "Part4/Longest_Word")
        },
        "Maximum_Bonus": {
            "json_path": [f"{root_dir}/Part4/Maximum_Bonus/Maximum_Bonus.json"],
            "save_dir": os.path.join(save_root, "Part4/Maximum_Bonus")
        },
        "Number_Link": {
            "json_path": [f"{root_dir}/Part4/Number_Link/Number_Link.json"],
            "save_dir": os.path.join(save_root, "Part4/Number_Link")
        },
        "Optimal_Path": {
            "json_path": [f"{root_dir}/Part4/Optimal_Path/Optimal_Path.json"],
            "save_dir": os.path.join(save_root, "Part4/Optimal_Path")
        },
        "Global_Word": {
            "json_path": [f"{root_dir}/Part4/Global_Word/Global_Word.json"],
            "save_dir": os.path.join(save_root, "Part4/Global_Word")
        },
        "Word": {
            "json_path": [f"{root_dir}/Part4/Word/Word.json"],
            "save_dir": os.path.join(save_root, "Part4/Word")
        },
        # ---- 
        # ---- Part5 Multi-Image Tasks
        "Multi_Image_Aware": {
            "json_path": [f"{root_dir}/Part5/Multi_Image_Aware/Multi_Image_Aware.json"],
            "save_dir": os.path.join(save_root, "Part5/Multi_Image_Aware")
        },
        "Multi_Image_Composition": {
            "json_path": [f"{root_dir}/Part5/Multi_Image_Composition/Multi_Image_Composition.json"],
            "save_dir": os.path.join(save_root, "Part5/Multi_Image_Composition")
        },
        "Virtual_Try_On": {
            "json_path": [f"{root_dir}/Part5/Virtual_Try_On/Virtual_Try_On.json"],
            "save_dir": os.path.join(save_root, "Part5/Virtual_Try_On")
        },
        # ---- 
        # ---- Part6 Complex Tasks
        "Complex_Instruction": {
            "json_path": [f"{root_dir}/Part6/Complex_Instruction/Complex_Instruction.json"],
            "save_dir": os.path.join(save_root, "Part6/Complex_Instruction")
        },
        "Complex_Paint_en":{
            "json_path": [ f"{root_dir}/Part6/Complex_Paint_en/Complex_Paint_en.json"],
            "save_dir": os.path.join(save_root, "Part6/Complex_Paint_en")
        },
        "Complex_Paint_cn":{
            "json_path": [f"{root_dir}/Part6/Complex_Paint_cn/Complex_Paint_cn.json"],
            "save_dir": os.path.join(save_root, "Part6/Complex_Paint_cn")
        }
        # ----
    }

