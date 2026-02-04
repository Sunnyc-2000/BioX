#!/usr/bin/env python3
import os
import sys
import re
import csv
import math
import shutil
import numpy as np
from datetime import datetime
from collections import defaultdict
from multiprocessing import Pool, cpu_count
import mmap
from tqdm import tqdm
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger()

def validate_percentage(value, name):
    """验证百分比值是否在50-100之间"""
    if not 50 <= value <= 100:
        print(f"错误：'{name}' 必须在50-100之间！")
        raise ValueError(f"Invalid {name} percentage")
    return value

def validate_step(value):
    """验证阶梯值是否在1-50之间"""
    if not 1 <= value <= 50:
        print("错误：'百分比阶梯' 必须在1-50之间！")
        raise ValueError("Invalid step value")
    return value

def strict_floor(total, percentage):
    """严格向下取整计算"""
    return (total * percentage) // 100

def process_csv(file_path):
    """高效处理CSV文件"""
    species_list = []
    species_set = set()  # 用于快速去重
    
    # 定义标题行的字节模式
    header_patterns = {b'species', b'name', b'id', b'minglu'}
    
    try:
        with open(file_path, 'rb') as f:
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                logger.error(f"CSV文件为空: {file_path}")
                return []
                
            # 使用内存映射提高大文件读取效率
            mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
            
            # 跳过可能的BOM
            start_pos = 3 if mm[:3] == b'\xef\xbb\xbf' else 0
            
            # 快速查找标题行 - 直接比较字节对象
            header_found = any(p in mm[start_pos:start_pos+100].lower() for p in header_patterns)
            
            if header_found:
                # 找到标题行后跳过它
                next_line = mm.find(b'\n', start_pos)
                if next_line != -1:
                    start_pos = next_line + 1
            
            # 高效处理每一行
            pos = start_pos
            while pos < len(mm):
                line_end = mm.find(b'\n', pos)
                if line_end == -1:
                    break
                
                # 直接处理字节对象，稍后解码
                line_bytes = mm[pos:line_end].strip()
                pos = line_end + 1
                
                if not line_bytes:
                    continue
                
                # 清除管道符并处理行
                try:
                    # 解码字节对象
                    line = line_bytes.decode('utf-8')
                    clean_line = re.sub(r'^\||\|$', '', line).strip()
                    
                    # 检查是否为标题行
                    if clean_line.lower() in [p.decode('utf-8') for p in header_patterns]:
                        continue
                    
                    if clean_line and clean_line not in species_set:
                        species_list.append(clean_line)
                        species_set.add(clean_line)
                except UnicodeDecodeError:
                    # 跳过无效的UTF-8行
                    continue
                    
        mm.close()
        return species_list
    except Exception as e:
        logger.error(f"CSV处理出错: {str(e)}")
        return []

def process_fasta_file(args):
    """并行处理FASTA文件"""
    file_path, prefilter_dir, species_map = args
    filename = os.path.basename(file_path)
    output_path = os.path.join(prefilter_dir, filename)
    
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return filename, 0, 0, 0, True, "文件不存在"
    
    # 检查文件大小
    try:
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return filename, 0, 0, 0, True, "空文件"
    except Exception as e:
        return filename, 0, 0, 0, True, f"文件大小检查错误: {str(e)}"

    try:
        # 使用rb模式打开文件
        with open(file_path, 'rb') as infile:
            # 尝试内存映射
            try:
                mm = mmap.mmap(infile.fileno(), 0, access=mmap.ACCESS_READ)
            except (ValueError, PermissionError) as e:
                return filename, 0, 0, 0, True, f"内存映射错误: {str(e)}"
                
            valid_species = 0
            duplicates = 0
            unknown = 0
            
            # 尝试创建输出文件
            try:
                with open(output_path, 'w', encoding='utf-8') as outfile:
                    current_sequence = []
                    processed_species = set()
                    pos = 0
                    valid_seq_start = None

                    while pos < len(mm):
                        # 找到下一行
                        next_newline = mm.find(b'\n', pos)
                        if next_newline == -1:
                            next_newline = len(mm)
                        line = mm[pos:next_newline].decode('utf-8', errors='ignore').strip()
                        pos = next_newline + 1
                        
                        if not line:
                            continue
                        
                        # 处理序列头
                        if line.startswith('>'):
                            # 处理前一个序列
                            if valid_seq_start is not None:
                                # 直接写入序列
                                sequence = ''.join(current_sequence)
                                outfile.write(sequence + '\n')
                                current_sequence = []
                                valid_seq_start = None
                            
                            # 处理新头
                            header = line[1:].strip()
                            clean_header = re.sub(r'\s+', ' ', header)
                            
                            # 检查物种
                            if clean_header in species_map:
                                if clean_header not in processed_species:
                                    processed_species.add(clean_header)
                                    outfile.write(f">{header}\n")
                                    valid_species += 1
                                    valid_seq_start = pos
                                else:
                                    duplicates += 1
                            else:
                                unknown += 1
                        
                        # 序列数据处理
                        elif valid_seq_start is not None:
                            current_sequence.append(line)
                    
                    # 处理最后一个序列
                    if valid_seq_start is not None and current_sequence:
                        sequence = ''.join(current_sequence)
                        outfile.write(sequence + '\n')
                    
                    # 如果没有有效物种，删除文件
                    if valid_species == 0:
                        reason = f"无有效物种 (有效:0, 重复:{duplicates}, 未知:{unknown})"
                        return filename, 0, duplicates, unknown, True, reason
                        
                    return filename, valid_species, duplicates, unknown, False, "成功处理"
            except Exception as e:
                # 输出文件创建失败
                return filename, 0, 0, 0, True, f"输出文件创建失败: {str(e)}"
    except Exception as e:
        # 整个处理过程失败
        return filename, 0, 0, 0, True, f"处理错误: {str(e)}"

def main():
    print("===== 基因文件过滤工具 (高效增强版) =====")
    
    # 获取用户输入
    input_dir = input("请输入基因文件存储路径: ").strip()
    species_list_file = input("请输入物种名录CSV文件路径: ").strip()
    prefilter_dir = input("请输入预筛选文件存储路径: ").strip()
    output_base_dir = input("请输入最终结果输出路径: ").strip()
    
    try:
        lower_percent = validate_percentage(int(input("请输入物种百分比下阈值(50-100): ")), "下阈值")
        upper_percent = validate_percentage(int(input("请输入物种百分比上阈值(50-100): ")), "上阈值")
        step = validate_step(int(input("请输入百分比阶梯(1-50): ")))
    except ValueError:
        sys.exit(1)

    # 创建目录
    os.makedirs(prefilter_dir, exist_ok=True)
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 创建跳过文件日志
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    skip_log_file = os.path.join(output_base_dir, f"skipped_files_{timestamp}.csv")
    skip_log = open(skip_log_file, 'w', encoding='utf-8')
    skip_log.write("文件名,跳过原因\n")
    
    # 创建主日志文件
    main_log_file = os.path.join(output_base_dir, f"filter_process_{timestamp}.log")
    log_handle = open(main_log_file, 'w', encoding='utf-8')
    
    def log(message, to_console=True):
        timestamp = datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')
        full_msg = f"{timestamp} {message}"
        log_handle.write(full_msg + '\n')
        log_handle.flush()
        if to_console:
            print(full_msg)
    
    start_time = datetime.now()
    log("处理开始")
    log(f"跳过记录文件: {skip_log_file}")
    log("==============")

    # ===== 步骤1: 物种名录处理 =====
    log("")
    log("===== 步骤1/4: 处理物种名录 =====")
    try:
        species_list = process_csv(species_list_file)
        species_count = len(species_list)
        if species_count == 0:
            log("错误：没有加载任何物种！请检查物种名录CSV格式", True)
            sys.exit(1)
        species_map = frozenset(species_list)
        log(f"有效物种总数: {species_count}")
        log("物种名录处理完成")
    except Exception as e:
        log(f"处理物种名录时出错: {str(e)}", True)
        sys.exit(1)

    # ===== 步骤2: 基因文件预筛选 =====
    log("")
    log("===== 步骤2/4: 并行基因文件预筛选 =====")
    
    # 支持的扩展名列表
    supported_extensions = ('.fas', '.faa', '.fna', '.fasta')
    fasta_files = []
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if any(file.endswith(ext) for ext in supported_extensions):
                fasta_files.append(os.path.join(root, file))
    
    total_files = len(fasta_files)
    skipped_files = 0
    processed_files = 0
    prefilter_species_count = {}
    
    if not fasta_files:
        log("错误: 未找到任何支持的基因文件(.fas, .faa, .fna, .fasta)", True)
        sys.exit(1)
    
    # 准备多进程处理
    pool_args = [(file, prefilter_dir, species_map) for file in fasta_files]
    
    # 使用进程池并行处理
    with Pool(processes=min(cpu_count(), 8)) as pool:
        # 使用tqdm创建进度条
        with tqdm(total=total_files, desc="处理文件", unit="file", dynamic_ncols=True) as pbar:
            for result in pool.imap_unordered(process_fasta_file, pool_args):
                filename, valid_species, duplicates, unknown, deleted, reason = result
                
                # 处理结果
                if deleted:
                    # 被跳过文件
                    log(f"文件 [{filename}]: 跳过 - {reason}")
                    skip_log.write(f"{filename},{reason}\n")
                    skip_log.flush()
                    skipped_files += 1
                else:
                    # 成功处理
                    prefilter_species_count[filename] = valid_species
                    log(f"文件 [{filename}]: 有效物种: {valid_species}, 重复: {duplicates}, 未知: {unknown}")
                    processed_files += 1
                
                pbar.update(1)
                pbar.set_postfix({
                    '完成': f"{pbar.n}/{total_files}", 
                    '跳过': skipped_files,
                    '成功': processed_files
                })
    
    skip_log.close()
    log(f"预筛选完成! 处理文件数: {processed_files}, 跳过文件数: {skipped_files}")
    log(f"有效文件保存在: {prefilter_dir}")

    # ===== 步骤3: 阈值文件夹计算 =====
    log("")
    log("===== 步骤3/4: 计算阈值文件夹 =====")
    
    # 预计算所有可能的阈值
    thresholds = {}
    current_percent = lower_percent
    last_threshold = -1
    
    while current_percent <= upper_percent:
        min_species = strict_floor(species_count, current_percent)
        if min_species != last_threshold:
            folder_name = f"{current_percent}%"
            thresholds[folder_name] = min_species
            last_threshold = min_species
            os.makedirs(os.path.join(output_base_dir, folder_name), exist_ok=True)
        
        # 更新百分比
        next_percent = current_percent + step
        if next_percent > 100:
            current_percent = 100
        elif next_percent > upper_percent:
            current_percent = upper_percent + 1  # 退出循环
        else:
            current_percent = next_percent
    
    # 优化文件夹顺序
    threshold_folders = sorted(thresholds.items(), key=lambda x: float(x[0].rstrip('%')))
    
    log(f"创建 {len(threshold_folders)} 个阈值文件夹")
    log(f"阈值范围: {lower_percent}% ~ {upper_percent}%, 阶梯: {step}%")
    
    # 如果没有有效的基因文件
    if not prefilter_species_count:
        log("错误: 没有找到任何包含有效物种的基因文件", True)
        log("请检查物种名录是否与基因文件中的物种名称匹配")
        sys.exit(1)

    # ===== 步骤4: 分层筛选文件 =====
    log("")
    log("===== 步骤4/4: 分层筛选文件 =====")
    
    # 第一轮筛选
    first_folder, first_min = threshold_folders[0]
    first_output_dir = os.path.join(output_base_dir, first_folder)
    files_to_copy = []
    
    for filename, count in prefilter_species_count.items():
        if count >= first_min:
            files_to_copy.append((
                os.path.join(prefilter_dir, filename),
                os.path.join(first_output_dir, filename)
            ))
    
    # 批量复制文件
    if files_to_copy:
        log(f"复制 {len(files_to_copy)} 个文件到 {first_folder}")
        with tqdm(total=len(files_to_copy), desc=f"复制到{first_folder}") as pbar:
            for src, dst in files_to_copy:
                shutil.copy2(src, dst)
                pbar.update(1)
        
        # 为第一文件夹创建摘要文件
        summary_lines = [
            f"{filename} - {prefilter_species_count[filename]} 物种" 
            for filename in prefilter_species_count 
            if prefilter_species_count[filename] >= first_min
        ]
        
        with open(os.path.join(first_output_dir, "summary.txt"), 'w') as f:
            f.write("\n".join(summary_lines))
        
        total_processed = len(files_to_copy)
    else:
        total_processed = 0
        log(f"警告: 没有文件满足 {first_folder} 的最低阈值")
    
    # 后续阈值处理
    for i in range(1, len(threshold_folders)):
        current_folder, current_min = threshold_folders[i]
        prev_folder, _ = threshold_folders[i-1]
        prev_dir = os.path.join(output_base_dir, prev_folder)
        current_dir = os.path.join(output_base_dir, current_folder)
        
        # 收集满足条件的文件
        files_to_move = []
        for filename, count in prefilter_species_count.items():
            if count >= current_min:
                prev_file = os.path.join(prev_dir, filename)
                if os.path.exists(prev_file):
                    files_to_move.append((
                        prev_file,
                        os.path.join(current_dir, filename)
                    ))
        
        # 批量复制文件
        if files_to_move:
            log(f"移动 {len(files_to_move)} 个文件到 {current_folder}")
            with tqdm(total=len(files_to_move), desc=f"复制到{current_folder}") as pbar:
                for src, dst in files_to_move:
                    shutil.copy2(src, dst)
                    pbar.update(1)
            
            # 创建摘要文件
            summary_lines = [
                f"{filename} - {count} 物种" 
                for filename, count in prefilter_species_count.items() 
                if count >= current_min
            ]
            
            with open(os.path.join(current_dir, "summary.txt"), 'w') as f:
                f.write("\n".join(summary_lines))
            
            total_processed += len(files_to_move)
        else:
            log(f"警告: 没有文件满足 {current_folder} 的最低阈值")
    
    # 最终汇总
    log("")
    log("===== 处理完成 =====")
    log(f"总物种数量: {species_count}")
    log(f"总基因文件数: {total_files}")
    log(f"处理文件数: {processed_files}")
    log(f"跳过文件数: {skipped_files}")
    log(f"总处理时间: {datetime.now() - start_time}")
    log(f"最终结果保存在: {output_base_dir}")
    log(f"跳过记录文件: {skip_log_file}")
    
    log("各阈值文件夹统计:")
    for folder, min_species in threshold_folders:
        folder_path = os.path.join(output_base_dir, folder)
        try:
            file_count = len([
                f for f in os.listdir(folder_path) 
                if any(f.endswith(ext) for ext in supported_extensions)
                and os.path.isfile(os.path.join(folder_path, f))
            ])
        except:
            file_count = 0
        log(f"- {folder}: {file_count} 个文件 (≥{min_species} 物种)")
    
    log(f"总筛选文件数: {total_processed}")
    log(f"详细日志保存在: {main_log_file}")
    
    log_handle.close()

if __name__ == "__main__":
    main()
