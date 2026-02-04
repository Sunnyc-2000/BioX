#!/bin/bash

# 激活getorganelle环境
source activate getorganelle
if [ $? -ne 0 ]; then
    echo "错误：环境激活失败，请检查conda环境配置"
    exit 1
fi
echo "环境已成功激活"

# 获取输入参数
read -p "请输入总文件夹路径（示例：/1/2/3）：" main_dir
read -p "请输入处理文件名目录（示例：C1T1 C1M1 G1 G2 G3）：" samples_str
read -p "请输入seed路径（示例：/home/insect303/data/AAAzyc/novofile/seed.fasta）：" seed_path

# 转换为数组并检查输入
IFS=' ' read -ra samples <<< "$samples_str"
if [ -z "$main_dir" ] || [ ${#samples[@]} -eq 0 ] || [ ! -f "$seed_path" ]; then
    echo "错误：输入无效！请检查路径是否存在"
    exit 1
fi

total=${#samples[@]}
completed=0
pending=$total

echo "================================================"
echo "文件路径: $main_dir"
echo "处理样本: ${samples[*]}"
echo "Seed路径: $seed_path"
echo "总任务数: $total"
echo "================================================"

# 主处理循环
for sample in "${samples[@]}"; do
    ((pending--))
    echo "当前运行: $sample"
    echo "已完成: $completed, 待处理: $pending"
    echo "正在运行..."
    
    sample_dir="${main_dir}/${sample}"
    in1="${sample_dir}/${sample}_1.clean.fq.gz"
    in2="${sample_dir}/${sample}_2.clean.fq.gz"
    out_dir="${sample_dir}/geto${sample}mito"
    
    # 检查输入文件是否存在
    if [ ! -f "$in1" ] || [ ! -f "$in2" ]; then
        echo "错误：文件缺失！跳过样本 $sample"
        continue
    fi
    
    # 删除已有输出目录
    if [ -d "$out_dir" ]; then
        echo "检测到已有输出目录，正在删除..."
        rm -rf "$out_dir"
    fi
    
    # 执行get_organelle命令
    get_organelle_from_reads.py \
        -1 "$in1" \
        -2 "$in2" \
        -o "$out_dir" \
        -R 10 \
        -k 21,45,65,85,105 \
        -t 72 \
        -F animal_mt \
        -s "$seed_path"
    
    # 检查命令执行状态
    if [ $? -eq 0 ]; then
        echo "样本 $sample 处理完成！"
    else
        echo "警告：$sample 处理过程中出现错误"
    fi
    
    ((completed++))
    echo "-----------------------------------------"
done

echo "所有任务已完成！"
echo "总处理样本数: $completed"
echo "错误样本数: $((total - completed))"
