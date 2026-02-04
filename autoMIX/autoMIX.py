#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
交互式BUSCO数据处理脚本（Python版本）
支持大文件处理，包含内存优化和防溢出功能
"""

import os
import sys
import shutil
import subprocess
import gc
import psutil
import threading
import time
from pathlib import Path
from typing import List, Dict, Set
import pandas as pd
import numpy as np

# 配置参数
class Config:
    THREADS = 72
    TRIMAL = "/home/insect303/tools/trimal-1.4.1/source/trimal"
    TRANSDECODER_LONGORFS = "/home/insect303/tools/TransDecoder/TransDecoder.LongOrfs"
    FASCONCAT = "/home/insect303/tools/FASconCAT-G_v1.05.1.pl"
    MAFFT = "/home/insect303/miniconda3/bin/mafft"
    
    # 内存管理参数
    MAX_MEMORY_USAGE = 0.8  # 最大内存使用率（80%）
    CHUNK_SIZE = 1000       # 分批处理的大小
    MEMORY_CHECK_INTERVAL = 5  # 内存检查间隔（秒）

class MemoryMonitor:
    """内存监控器"""
    def __init__(self, max_usage=0.8):
        self.max_usage = max_usage
        self.monitoring = False
        self.high_memory_warning = False
        
    def get_memory_usage(self):
        """获取当前内存使用率"""
        return psutil.virtual_memory().percent / 100
    
    def check_memory(self):
        """检查内存使用情况"""
        usage = self.get_memory_usage()
        if usage > self.max_usage:
            if not self.high_memory_warning:
                print(f"⚠️  内存使用率过高: {usage:.1%}，建议优化处理")
                self.high_memory_warning = True
            return False
        return True
    
    def force_garbage_collection(self):
        """强制垃圾回收"""
        gc.collect()
        print("�� 已执行垃圾回收")
    
    def monitor_memory(self):
        """后台内存监控"""
        self.monitoring = True
        while self.monitoring:
            if not self.check_memory():
                self.force_garbage_collection()
            time.sleep(Config.MEMORY_CHECK_INTERVAL)
    
    def start_monitoring(self):
        """开始内存监控"""
        thread = threading.Thread(target=self.monitor_memory)
        thread.daemon = True
        thread.start()
    
    def stop_monitoring(self):
        """停止内存监控"""
        self.monitoring = False

class Color:
    """颜色输出类"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

class BUSCOProcessor:
    """BUSCO数据处理主类"""
    
    def __init__(self):
        self.memory_monitor = MemoryMonitor(Config.MAX_MEMORY_USAGE)
        self.base_dir = ""
        self.output_dir = ""
        self.species_list = []
        self.loci_list = []
        
    def print_color(self, message, color=Color.RESET, bold=False):
        """彩色打印"""
        prefix = Color.BOLD if bold else ""
        print(f"{prefix}{color}{message}{Color.RESET}")
    
    def print_info(self, message):
        """信息打印"""
        self.print_color(f"[INFO] {message}", Color.BLUE)
    
    def print_success(self, message):
        """成功打印"""
        self.print_color(f"[SUCCESS] {message}", Color.GREEN, bold=True)
    
    def print_warning(self, message):
        """警告打印"""
        self.print_color(f"[WARNING] {message}", Color.YELLOW)
    
    def print_error(self, message):
        """错误打印"""
        self.print_color(f"[ERROR] {message}", Color.RED, bold=True)
    
    def get_user_input(self):
        """获取用户输入"""
        print("=" * 80)
        print("    BUSCO数据处理脚本（Python版本 - 内存优化版）")
        print("=" * 80)
        print()
        
        # 输入基础路径
        while True:
            base_dir = input("请输入包含所有busco_result_exercise文件夹的根路径: ").strip()
            if not base_dir:
                self.print_error("路径不能为空")
                continue
                
            base_path = Path(base_dir)
            if not base_path.exists():
                self.print_error(f"路径不存在: {base_dir}")
                continue
                
            self.base_dir = base_path
            break
        
        # 输入输出路径
        while True:
            output_dir = input("请输入输出结果的目录路径: ").strip()
            if not output_dir:
                self.print_error("输出路径不能为空")
                continue
                
            output_path = Path(output_dir)
            if not output_path.exists():
                create = input("输出目录不存在，是否创建? (y/n): ").lower()
                if create == 'y':
                    output_path.mkdir(parents=True, exist_ok=True)
                    self.print_success(f"已创建输出目录: {output_dir}")
                else:
                    self.print_error("输出目录不存在，脚本终止")
                    sys.exit(1)
            
            self.output_dir = output_path
            break
    
    def find_busco_folders(self) -> List[Path]:
        """查找所有busco_result_exercise文件夹"""
        self.print_info("正在查找busco_result_exercise文件夹...")
        
        busco_folders = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and item.name.endswith('_busco_result_exercise'):
                busco_folders.append(item)
        
        if not busco_folders:
            self.print_error(f"在 {self.base_dir} 中未找到任何busco_result_exercise文件夹")
            sys.exit(1)
        
        self.print_success(f"找到 {len(busco_folders)} 个busco_result_exercise文件夹")
        
        # 显示找到的文件夹
        self.print_info("找到的文件夹列表:")
        for folder in busco_folders:
            species_name = folder.name.replace('_busco_result_exercise', '')
            self.print_info(f"  - {folder.name} -> 物种标识: {species_name}")
        
        return busco_folders
    
    def create_directory_structure(self):
        """创建输出目录结构"""
        self.print_info("创建输出目录结构...")
        
        directories = [
            "0-raw_busco",
            "1-raw_loci/fna",
            "1-raw_loci/faa", 
            "2-loci_filter/fna",
            "2-loci_filter/faa",
            "3-align/faa",
            "3-align/fna"
        ]
        
        for dir_path in directories:
            full_path = self.output_dir / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
    
    def copy_sequence_files(self, busco_folders: List[Path]):
        """复制序列文件（内存优化版本）"""
        self.print_info("开始复制序列文件（单拷贝+片段化基因）...")
        
        total_species = len(busco_folders)
        processed_species = 0
        
        for busco_folder in busco_folders:
            # 定期检查内存
            if not self.memory_monitor.check_memory():
                self.memory_monitor.force_garbage_collection()
            
            folder_name = busco_folder.name
            species_name = folder_name.replace('_busco_result_exercise', '')
            run_folder = self.output_dir / "0-raw_busco" / f"run_{species_name}"
            
            # 创建物种目录
            run_folder.mkdir(parents=True, exist_ok=True)
            
            # 定义源文件路径
            single_copy_dir = busco_folder / "run_endopterygota_odb10" / "busco_sequences" / "single_copy_busco_sequences"
            fragmented_dir = busco_folder / "run_endopterygota_odb10" / "busco_sequences" / "fragmented_busco_sequences"
            
            files_copied = 0
            
            # 复制单拷贝基因序列（分批处理）
            if single_copy_dir.exists():
                files = list(single_copy_dir.glob("*.fna")) + list(single_copy_dir.glob("*.faa"))
                for file_path in files:
                    try:
                        shutil.copy2(file_path, run_folder / file_path.name)
                        files_copied += 1
                    except Exception as e:
                        self.print_warning(f"复制文件失败 {file_path}: {e}")
            else:
                self.print_warning(f"单拷贝基因目录不存在: {single_copy_dir}")
            
            # 复制片段化基因序列（分批处理）
            if fragmented_dir.exists():
                files = list(fragmented_dir.glob("*.fna")) + list(fragmented_dir.glob("*.faa"))
                for file_path in files:
                    try:
                        shutil.copy2(file_path, run_folder / file_path.name)
                        files_copied += 1
                    except Exception as e:
                        self.print_warning(f"复制文件失败 {file_path}: {e}")
            else:
                self.print_warning(f"片段化基因目录不存在: {fragmented_dir}")
            
            processed_species += 1
            
            if files_copied > 0:
                self.print_success(f"({processed_species}/{total_species}) {species_name}: 已复制 {files_copied} 个基因文件")
            else:
                self.print_warning(f"({processed_species}/{total_species}) {species_name}: 未找到任何基因文件")
        
        # 检查是否成功复制了文件
        raw_busco_dir = self.output_dir / "0-raw_busco"
        if not any(raw_busco_dir.iterdir()):
            self.print_error("没有成功复制任何序列文件，请检查路径结构")
            sys.exit(1)
    
    def generate_species_list(self):
        """生成物种列表"""
        self.print_info("生成物种列表...")
        
        raw_busco_dir = self.output_dir / "0-raw_busco"
        species_dirs = [d for d in raw_busco_dir.iterdir() if d.is_dir() and d.name.startswith('run_')]
        
        if not species_dirs:
            self.print_error("没有找到任何物种，请检查文件复制步骤")
            sys.exit(1)
        
        self.species_list = [d.name.replace('run_', '') for d in species_dirs]
        
        # 保存物种列表到文件
        species_file = self.output_dir / "species.list"
        with open(species_file, 'w') as f:
            for species in self.species_list:
                f.write(species + '\n')
        
        self.print_success(f"找到 {len(self.species_list)} 个物种")
    
    def generate_loci_list(self):
        """生成基因位点列表（内存优化版本）"""
        self.print_info("生成基因位点列表...")
        
        loci_set = set()
        
        # 分批处理物种，避免内存溢出
        for i in range(0, len(self.species_list), Config.CHUNK_SIZE):
            chunk_species = self.species_list[i:i + Config.CHUNK_SIZE]
            
            for species in chunk_species:
                species_dir = self.output_dir / "0-raw_busco" / f"run_{species}"
                if species_dir.exists():
                    for file_path in species_dir.iterdir():
                        if file_path.is_file():
                            locus_name = file_path.stem  # 去除扩展名
                            loci_set.add(locus_name)
            
            # 检查内存使用情况
            if not self.memory_monitor.check_memory():
                self.memory_monitor.force_garbage_collection()
        
        self.loci_list = sorted(list(loci_set))
        
        # 保存基因位点列表到文件
        loci_file = self.output_dir / "loci.list"
        with open(loci_file, 'w') as f:
            for locus in self.loci_list:
                f.write(locus + '\n')
        
        self.print_success(f"找到 {len(self.loci_list)} 个基因位点")
    
    def process_locus_chunk(self, chunk_loci: List[str], chunk_id: int):
        """处理基因位点分块（避免内存溢出）"""
        for i, locus in enumerate(chunk_loci):
            locus_num = chunk_id * Config.CHUNK_SIZE + i + 1
            total_loci = len(self.loci_list)
            
            self.print_info(f"处理基因位点 {locus_num}/{total_loci}: {locus}")
            
            # 合并每个基因位点的序列（使用生成器避免内存溢出）
            self.merge_locus_sequences(locus)
            
            # 比对序列
            self.align_sequences(locus)
            
            # 定期垃圾回收
            if (i + 1) % 10 == 0:  # 每处理10个位点清理一次
                self.memory_monitor.force_garbage_collection()
    
    def merge_locus_sequences(self, locus: str):
        """合并基因位点序列（流式处理，避免内存溢出）"""
        # 合并FNA文件
        fna_output = self.output_dir / "1-raw_loci" / "fna" / f"{locus}.fna"
        with open(fna_output, 'w') as outfile:
            for species in self.species_list:
                fna_file = self.output_dir / "0-raw_busco" / f"run_{species}" / f"{locus}.fna"
                if fna_file.exists():
                    with open(fna_file, 'r') as infile:
                        shutil.copyfileobj(infile, outfile)
        
        # 合并FAA文件
        faa_output = self.output_dir / "1-raw_loci" / "faa" / f"{locus}.faa"
        with open(faa_output, 'w') as outfile:
            for species in self.species_list:
                faa_file = self.output_dir / "0-raw_busco" / f"run_{species}" / f"{locus}.faa"
                if faa_file.exists():
                    with open(faa_file, 'r') as infile:
                        shutil.copyfileobj(infile, outfile)
    
    def align_sequences(self, locus: str):
        """比对序列（使用外部进程）"""
        faa_input = self.output_dir / "1-raw_loci" / "faa" / f"{locus}.faa"
        faa_output = self.output_dir / "3-align" / "faa" / f"{locus}.faa"
        
        fna_input = self.output_dir / "1-raw_loci" / "fna" / f"{locus}.fna"
        fna_output = self.output_dir / "3-align" / "fna" / f"{locus}.fna"
        
        # 比对氨基酸序列
        if faa_input.exists() and faa_input.stat().st_size > 0:
            try:
                cmd = [
                    Config.MAFFT,
                    "--thread", str(Config.THREADS),
                    "--ep", "0",
                    "--genafpair",
                    "--maxiterate", "1000",
                    str(faa_input)
                ]
                
                with open(faa_output, 'w') as outfile:
                    subprocess.run(cmd, stdout=outfile, check=True, stderr=subprocess.DEVNULL)
                
                self.print_success("  - 氨基酸比对完成")
            except subprocess.CalledProcessError as e:
                self.print_warning(f"  - 氨基酸比对失败: {e}")
        else:
            self.print_warning("  - 跳过空氨基酸文件")
        
        # 比对核苷酸序列
        if fna_input.exists() and fna_input.stat().st_size > 0:
            try:
                cmd = [
                    Config.MAFFT,
                    "--thread", str(Config.THREADS),
                    "--ep", "0", 
                    "--genafpair",
                    "--maxiterate", "1000",
                    str(fna_input)
                ]
                
                with open(fna_output, 'w') as outfile:
                    subprocess.run(cmd, stdout=outfile, check=True, stderr=subprocess.DEVNULL)
                
                self.print_success("  - 核苷酸比对完成")
            except subprocess.CalledProcessError as e:
                self.print_warning(f"  - 核苷酸比对失败: {e}")
        else:
            self.print_warning("  - 跳过空核苷酸文件")
    
    def process_sequences(self):
        """处理序列（分批处理防止内存溢出）"""
        self.print_info("开始处理基因序列...")
        
        total_loci = len(self.loci_list)
        
        # 分批处理基因位点
        for i in range(0, total_loci, Config.CHUNK_SIZE):
            chunk_loci = self.loci_list[i:i + Config.CHUNK_SIZE]
            chunk_id = i // Config.CHUNK_SIZE
            
            self.print_info(f"处理第 {chunk_id + 1} 批基因位点 ({len(chunk_loci)} 个)")
            self.process_locus_chunk(chunk_loci, chunk_id)
            
            # 批次间强制垃圾回收
            self.memory_monitor.force_garbage_collection()
    
    def show_statistics(self):
        """显示统计信息"""
        self.print_success("脚本执行完成!")
        print()
        print("=" * 80)
        print("                处理结果统计")
        print("=" * 80)
        print(f"输入目录: {self.base_dir}")
        print(f"输出目录: {self.output_dir}")
        print(f"处理物种数量: {len(self.species_list)}")
        print(f"处理基因位点: {len(self.loci_list)}")
        print()
        
        # 统计生成的文件
        faa_dir = self.output_dir / "3-align" / "faa"
        fna_dir = self.output_dir / "3-align" / "fna"
        
        faa_count = len(list(faa_dir.glob("*.faa"))) if faa_dir.exists() else 0
        fna_count = len(list(fna_dir.glob("*.fna"))) if fna_dir.exists() else 0
        
        print("生成的比对文件:")
        print(f"  - 氨基酸比对: {faa_dir}/ (共 {faa_count} 个文件)")
        print(f"  - 核苷酸比对: {fna_dir}/ (共 {fna_count} 个文件)")
        print()
        
        # 内存使用统计
        memory_usage = self.memory_monitor.get_memory_usage()
        print(f"最终内存使用率: {memory_usage:.1%}")
        print()
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        cleanup = input("是否清理临时文件? (y/n, 默认n): ").lower()
        if cleanup == 'y':
            self.print_info("清理临时文件...")
            
            temp_dirs = [
                self.output_dir / "0-raw_busco",
                self.output_dir / "1-raw_loci"
            ]
            
            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
            
            self.print_success("临时文件已清理")
        else:
            self.print_info("保留临时文件")
    
    def run(self):
        """主运行函数"""
        try:
            # 开始内存监控
            self.memory_monitor.start_monitoring()
            
            # 获取用户输入
            self.get_user_input()
            
            # 查找BUSCO文件夹
            busco_folders = self.find_busco_folders()
            
            # 创建目录结构
            self.create_directory_structure()
            
            # 复制序列文件
            self.copy_sequence_files(busco_folders)
            
            # 生成物种列表
            self.generate_species_list()
            
            # 生成基因位点列表
            self.generate_loci_list()
            
            # 处理序列
            self.process_sequences()
            
            # 显示统计信息
            self.show_statistics()
            
            # 清理临时文件
            self.cleanup_temp_files()
            
            self.print_success("所有处理已完成!")
            
        except KeyboardInterrupt:
            self.print_info("用户中断执行")
        except Exception as e:
            self.print_error(f"执行过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 停止内存监控
            self.memory_monitor.stop_monitoring()

def main():
    """主函数"""
    # 检查Python版本
    if sys.version_info < (3, 7):
        print("错误: 需要Python 3.7或更高版本")
        sys.exit(1)
    
    # 检查依赖
    try:
        import psutil
    except ImportError:
        print("错误: 需要安装psutil库")
        print("安装命令: pip install psutil")
        sys.exit(1)
    
    # 运行处理器
    processor = BUSCOProcessor()
    processor.run()

if __name__ == "__main__":
    main()
